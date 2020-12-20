# -*- coding: utf-8 -*-
# Copyright (c) 2020, Ahmed Mohammed Alkuhlani and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, flt
from frappe import _

class PayrollEntryTool(Document):
	def on_submit(self):
		self.make_accrual_jv_entry()

	def get_default_payroll_payable_account(self):
		if self.direct_to_bank:
			if self.payment_account:
				return self.payment_account
			else:
				frappe.throw(_("Please set Company Account for Bank Account"))

		payroll_payable_account=None
		if self.is_payable==1:		
			payroll_payable_account = self.payroll_payable_account
		else:
			payroll_payable_account = self.payroll_account
		if not payroll_payable_account:
			frappe.throw(_("Please set Payroll - Payable - Account in Current Document")
				.format(self.company))
		return payroll_payable_account

	def get_default_round_off_account(self):
		round_off_account=None
		if self.round_off_account:		
			round_off_account = self.round_off_account
		else:
			round_off_account = frappe.get_cached_value('Company',{"company_name": self.company},  "round_off_account")

		if not round_off_account:
			frappe.throw(_("Please set Round Off Account in Current Document").format(self.company))
		return round_off_account

	def get_loan_details(self,employee=None):
		"""
			Get loan details from submitted salary slip based on selected criteria
		"""
		cond = self.get_filter_condition(employee=employee)
		return frappe.db.sql(""" select eld.loan_account, eld.loan,
				eld.interest_income_account, eld.principal_amount, eld.interest_amount, eld.total_payment,t1.employee
			from
				`tabSalary Slip` t1, `tabSalary Slip Loan` eld
			where
				t1.docstatus = 1 and t1.name = eld.parent and start_date >= %s and end_date <= %s %s
			""" % ('%s', '%s', cond), (self.start_date, self.end_date), as_dict=True) or []


	def get_salary_component_account(self, salary_component):
		account = frappe.db.get_value("Salary Component Account",
			{"parent": salary_component, "company": self.company}, "default_account")

		if not account:
			frappe.throw(_("Please set default account in Salary Component {0}")
				.format(salary_component))

		return account

	def get_filter_condition(self,employee=None):
		##self.check_mandatory()

		cond = ''
		for f in ['company', 'payroll_entry']:
			if self.get(f):
				cond += " and t1." + f + " = '" + self.get(f).replace("'", "\'") + "'"
				if employee:
					cond += " and t1.employee = '" + employee + "'"

		return cond

	def get_sal_slip_list(self, ss_status, as_dict=False, employee=None):
		"""
			Returns list of salary slips based on selected criteria
		"""
		cond = self.get_filter_condition(employee=employee)

		ss_list = frappe.db.sql("""
			select t1.name, t1.employee, t1.net_pay, t1.designation from `tabSalary Slip` t1
			where t1.docstatus = %s and t1.start_date >= %s and t1.end_date <= %s
			and (t1.journal_entry is null or t1.journal_entry = "") %s
		""" % ('%s', '%s', '%s', cond), (ss_status, self.start_date, self.end_date), as_dict=as_dict)
		return ss_list

	def get_salary_components(self, component_type, employee=None):
		salary_slips = self.get_sal_slip_list(ss_status = 1, as_dict = True, employee=employee)
		if salary_slips:
			salary_components = frappe.db.sql("""select salary_component, amount, parentfield
				from `tabSalary Detail` where parentfield = '%s' and parent in (%s)""" %
				(component_type, ', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=True)
			return salary_components

	def get_salary_component_total(self, component_type = None, employee=None):
		salary_components = self.get_salary_components(component_type, employee=employee)
		if salary_components:
			component_dict = {}
			for item in salary_components:
				add_component_to_accrual_jv_entry = True
				if component_type == "earnings":
					is_flexible_benefit, only_tax_impact = frappe.db.get_value("Salary Component", item['salary_component'], ['is_flexible_benefit', 'only_tax_impact'])
					if is_flexible_benefit == 1 and only_tax_impact ==1:
						add_component_to_accrual_jv_entry = False
				if add_component_to_accrual_jv_entry:
					component_dict[item['salary_component']] = component_dict.get(item['salary_component'], 0) + item['amount']
			account_details = self.get_account(component_dict = component_dict,component_type=component_type,employee=employee)
			return account_details

	def get_account(self, component_dict = None,component_type=None,employee=None):
		account_dict = {}
		for s, a in component_dict.items():
			account = self.get_salary_component_account(s)
			if not account_dict.get(account):
				account_dict[s] = {}
				account_dict[s]['account']=account
				account_dict[s]['salary_component']=s
				account_dict[s]['scd']=frappe.db.get_value("Salary Component",{"name": s}, "description")
				account_dict[s]['amount'] = flt(account_dict[s].get('amount', 0.0) + a)

		if account_dict and component_type == "earnings":
			scc=frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center")
			account_dict2 = {}
			num=0
			for ac in account_dict:
				pa = frappe.db.sql("""select DISTINCT pa.name as project_activities, 
					pa.project as project, IFNULL(pap.project_percentage,0.0) as project_percentage,
					pap.is_inter_company_account as iica, pap.inter_company_account as ica, pap.internal_project as internal_project,
					pap.cost_center as cost_center, cc.sun_cost_center as sun_cost_center
					from `tabProject Activities` pa 
					LEFT JOIN `tabSalary Component` sc ON sc.name = '%(sc)s'
					INNER JOIN `tabProject Activity Payroll` pap ON pap.parent = pa.name
					INNER JOIN `tabCost Center` cc ON cc.name = pap.cost_center
					LEFT JOIN `tabProject Activity Salary Component` pasc ON pasc.parent = pa.name
					where (pasc.salary_component = '%(sc)s' or sc.depends_on_pa_sc = 1)
					and pap.employee = '%(employee)s' and pap.status= 'Active'""" %
					{"sc": ac,"employee":employee}, as_dict=True)

				if pa:
					percentage_count=0.0
					for item in pa:
						percentage_count+=item.project_percentage
						account_dict2[num]={}
						account_dict2[num]['scd']= _('{0} - {1}%').format(account_dict[ac].get('scd'),item.project_percentage)
						account_dict2[num]['account']=account_dict[ac].get('account') if item.iica==0 else item.ica
						account_dict2[num]['amount']=flt(account_dict[ac].get('amount'))*flt(item.project_percentage)/100
						account_dict2[num]['project_activities']=item.project_activities
						account_dict2[num]['project']=item.project
						account_dict2[num]['cost_center']=item.cost_center or self.cost_center
						account_dict2[num]['sun_cost_center']=item.sun_cost_center or scc
						account_dict2[num]['internal_project']=item.internal_project or ''
						num+=1
					if percentage_count<100:
						percentage_count=100-percentage_count
						account_dict2[num]={}
						account_dict2[num]['scd']= _('{0} - {1}%').format(account_dict[ac].get('scd'),percentage_count)
						account_dict2[num]['account']=account_dict[ac].get('account')
						account_dict2[num]['amount']=account_dict[ac].get('amount')*percentage_count/100
						account_dict2[num]['project_activities']=self.project_activities
						account_dict2[num]['project']=self.project
						account_dict2[num]['cost_center']=self.cost_center
						account_dict2[num]['sun_cost_center']=scc
						account_dict2[num]['customer']=self.customer
						num+=1
					elif percentage_count>100:
						frappe.throw(_("Total Percentage of {0} is {1}")
						.format(employee,percentage_count))

				else:
					account_dict2[num]={}
					account_dict2[num]['scd']=account_dict[ac].get('scd')
					account_dict2[num]['account']=account_dict[ac].get('account')
					account_dict2[num]['amount']=account_dict[ac].get('amount')
					account_dict2[num]['project_activities']=self.project_activities
					account_dict2[num]['project']=self.project
					account_dict2[num]['cost_center']=self.cost_center
					account_dict2[num]['sun_cost_center']=scc
					account_dict2[num]['customer']=self.customer
					num+=1
			return account_dict2
		return account_dict

	def make_accrual_jv_entry(self):
		scc=frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center")
		submitted_ss = []
		scc=1 if self.currency==frappe.db.get_value("Company", {'name':self.company}, "default_currency") else 0
		self.check_permission('write')
		deductions = self.get_salary_component_total(component_type = "deductions") or {}
		default_payroll_payable_account = self.get_default_payroll_payable_account()
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
		##precision = 20
		##frappe.msgprint(_("precision= {0}")
		##	.format(precision))

		ss_list = self.get_sal_slip_list(ss_status=1)
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Journal Entry'
		journal_entry.user_remark = _('Accrual Journal Entry for salaries from {0} to {1}')\
			.format(self.start_date, self.end_date)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		accounts = []
		earn=0.0
		ded=0.0
		loa=0.0
		pay=0.0
		paycc=0.0

		for ss in ss_list:
			submitted_ss.append(ss[0])
			designation=frappe.get_cached_value('Employee',{"name": ss[1]},  "designation")
			earnings = self.get_salary_component_total(component_type = "earnings",employee=ss[1]) or {}
			# Earnings
			for ear in sorted(earnings):
				accounts.append({
						"account": earnings[ear].get('account'),
						"user_remark": _('{0} - {1} - {2}').format(designation,earnings[ear].get('scd'),ss[1]),
						"debit_in_account_currency": flt(earnings[ear].get('amount'), precision),
						"debit": flt(((flt(earnings[ear].get('amount'), precision))*(1 if scc else self.conversion_rate)), precision),
						"conversion_rate": 1 if scc else self.conversion_rate,
						"sun_cost_center": earnings[ear].get('sun_cost_center',scc),
						"cost_center": earnings[ear].get('cost_center',self.cost_center),
						"project": earnings[ear].get('project',self.project),
						"project_activities": earnings[ear].get('project_activities',self.project_activities),
						"customer": earnings[ear].get('customer',self.customer),
						"internal_project":earnings[ear].get('internal_project','')
					})
				earn+=flt(((flt(earnings[ear].get('amount'), precision))*(1 if scc else self.conversion_rate)), precision)
			# Loan
			eee=frappe.db.get_value("Company",{"name": self.company}, "default_employee_payable_account_mc_pav")
			eee2=frappe.db.get_value("Account",{"parent_account": eee,"account_currency":self.currency}, "name")
			##frappe.msgprint(_("eee={0} - eee2={1}").format(eee,eee2))

			loan_details = self.get_loan_details(employee=ss[1])
			for data in loan_details:
				accounts.append({
					"account": eee2,
					"user_remark": _('{0}').format(frappe.db.get_value("Employee", {'name':ss[1]}, "employee_name")),
					"credit_in_account_currency": data.principal_amount,
					#"credit": flt(data.principal_amount if scc else (data.principal_amount*self.conversion_rate),precision),
					"conversion_rate": 1 if scc else self.conversion_rate,
					"party_type": "Employee Account",
					"party": frappe.db.get_value("Employee Account",{"employee": data.employee,"currency":self.currency}, "name"),
					"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
					"cost_center": self.cost_center,
					"project": self.project,
					"project_activities": self.project_activities,
					"customer": self.customer

				})
				loa+=flt(data.principal_amount if scc else (data.principal_amount*self.conversion_rate),precision)

				if data.interest_amount and not data.interest_income_account:
					frappe.throw(_("Select interest income account in loan {0}").format(data.loan))

				if data.interest_income_account and data.interest_amount:
					accounts.append({
						"account": data.interest_income_account,
						"credit_in_account_currency": data.interest_amount,
						"party_type": "Employee",
						"party": data.employee
					})
			# Payroll Payable amount
			if self.is_payable==1:
				accounts.append({
					"account": default_payroll_payable_account,
					"credit_in_account_currency": ss[2],
					"credit": flt(ss[2] if scc else (ss[2]*self.conversion_rate),precision),
					"conversion_rate": 1 if scc else self.conversion_rate,
					"party_type": "Employee Account",
					"party": frappe.db.get_value("Employee Account",{"employee": ss[1],"currency":self.currency}, "name"),
					"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
					"cost_center": self.cost_center,
					"project": self.project,
					"project_activities": self.project_activities,
					"customer": self.customer
				})
			pay+=flt(ss[2], precision)
			paycc+=flt(ss[2] if scc else (ss[2]*self.conversion_rate),precision)

		##frappe.msgprint(_("earning={0}").format(1))

		# Deductions
		if deductions:
			for dede in deductions:				
				acc=frappe.db.get_value("Account",{"name": deductions[dede].get('account')}, "account_currency")
				er_account,er=frappe.db.get_value("Salary Component Account",{"parent": deductions[dede].get('salary_component')}, ["er_account","er"])
			

				if acc!=self.currency:
					accounts.append({
						"account": deductions[dede].get('account'),
						"user_remark": _('{0}').format(deductions[dede].get('scd')),
						"credit_in_account_currency": flt(deductions[dede].get('amount')*er, precision),
						"credit": flt(deductions[dede].get('amount')*er, precision),
						"conversion_rate": 1 ,
						"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
						"cost_center": self.cost_center,
						"project": self.project,
						"project_activities": self.project_activities,
						"customer": self.customer
					})
					accounts.append({
						"account": frappe.db.get_value("Account",{"parent_account": er_account,"account_currency":self.currency}, "name"),
						"user_remark": _('{0}').format(deductions[dede].get('scd')),
						"credit_in_account_currency": flt(deductions[dede].get('amount'), precision),
						"credit": flt(deductions[dede].get('amount')*er, precision),
						"conversion_rate": er,
						"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
						"cost_center": self.cost_center,
						"project": self.project,
						"project_activities": self.project_activities,
						"customer": self.customer
					})
					accounts.append({
						"account": frappe.db.get_value("Account",{"parent_account": er_account,"account_currency":'YER'}, "name") ,
						"user_remark": _('{0}').format(deductions[dede].get('scd')),
						"debit_in_account_currency": flt(deductions[dede].get('amount')*er, precision),
						"debit": flt(deductions[dede].get('amount')*er, precision),
						"conversion_rate": 1 ,
						"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
						"cost_center": self.cost_center,
						"project": self.project,
						"project_activities": self.project_activities,
						"customer": self.customer
					})					
				else:
					accounts.append({
						"account": deductions[dede].get('account'),
						"user_remark": _('{0}').format(deductions[dede].get('scd')),
						"credit_in_account_currency": flt(deductions[dede].get('amount'), precision),
						"credit": flt((flt(deductions[dede].get('amount'), precision)*(1 if scc else self.conversion_rate)),precision),
						"conversion_rate": 1 if scc else self.conversion_rate,
						"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
						"cost_center": self.cost_center,
						"project": self.project,
						"project_activities": self.project_activities,
						"customer": self.customer
					})

				##ded+=flt(deductions[dede].get('amount') if scc else (deductions[dede].get('amount')*self.conversion_rate),precision)
				ded+=flt((flt(deductions[dede].get('amount'), precision)*(1 if scc else self.conversion_rate)),precision)
		##(_("Deductions={0}").format(2))


		# Payroll amount
		ppp=frappe.db.get_value("Company",{"name": self.company}, "default_payroll_payable_account")
		ppp2=frappe.db.get_value("Account",{"parent_account": ppp,"account_currency":self.currency}, "name")
		##frappe.msgprint(_("ppp={0} - ppp2={1}").format(ppp,ppp2))
		if self.is_payable==0:
			accounts.append({
				"account": ppp2,
				"credit_in_account_currency": flt(pay,precision),
				"credit": flt((flt(pay,precision)*(1 if scc else self.conversion_rate)),precision),
				"conversion_rate": 1 if scc else self.conversion_rate,
				"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
				"cost_center": self.cost_center,
				"project": self.project,
				"project_activities": self.project_activities,
				"customer": self.customer
			})
			paycc=flt((flt(pay,precision)*(1 if scc else self.conversion_rate)),precision)
		##frappe.msgprint(_("Payroll ={0}").format(3))

		# Writeoff
		if self.difference>0:
			##frappe.msgprint(_("Not Equal = {0}").format(flt((earn-(loa+paycc+ded)), precision)))
			accounts.append({
				"account": self.get_default_round_off_account(),
				"credit_in_account_currency": flt(self.difference, precision),
				"credit": flt(self.difference, precision),
				"conversion_rate": 1,
				"sun_cost_center": frappe.db.get_value("Cost Center", {'name':self.cost_center}, "sun_cost_center"),
				"cost_center": self.cost_center,
				"project": self.project,
				"project_activities": self.project_activities,
				"customer": self.customer
			})
		##frappe.msgprint(_("Writeoff={0}").format(4))

		if not accounts:
			frappe.msgprint(_("There is no Submitted Salary Slip or may be its Acrrualed")
				.format(earn,ded,loa,pay))
		#frappe.msgprint(_("earn={0},ded={1},loa={2},pay={3},diff={4}")
		#	.format(flt(earn, precision),flt(ded, precision),flt(loa, precision),flt(paycc, precision),flt((earn-(loa+paycc+ded)), precision)))
		##frappe.msgprint(_("accounts={0}").format(accounts))

		journal_entry.set("accounts", accounts)
		journal_entry.title = self.title

		journal_entry.save()
		self.accrual_jv=journal_entry.name
		self.save()
		try:
			#journal_entry.submit()
			jv_name = journal_entry.name
			self.update_salary_slip_status(jv_name = jv_name)

		except Exception as e:
			frappe.msgprint(e)

		frappe.msgprint(_("Journal Entry submitted for Payroll Entry period from {0} to {1}")
			.format(self.start_date, self.end_date))

		##email_salary_slip(submitted_ss)

	def update_salary_slip_status(self, jv_name = None):
		ss_list = self.get_sal_slip_list(ss_status=1)
		for ss in ss_list:
			ss_obj = frappe.get_doc("Salary Slip",ss[0])
			frappe.db.set_value("Salary Slip", ss_obj.name, "journal_entry", jv_name)

	def email_salary_slip(self, submitted_ss):
		if frappe.db.get_single_value("HR Settings", "email_salary_slip_to_employee"):
			for ss in submitted_ss:
				ss.email_salary_slip()

