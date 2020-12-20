# Copyright (c) 2013, Ahmed Mohammed Alkuhlani and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt,cstr
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	if not filters.get("employee"):
		#frappe.msgprint("Employee is Mandatory")
		return [], []

	if not filters.get("payroll_entry") and not filters.get("salary_slip"):
		#frappe.msgprint("on of these (Payroll Entry, Salary Slip) Shoud to be filled")
		return [], []
	if filters.get("salary_slip"):
		ss=frappe.db.sql("""SELECT net_pay FROM `tabSalary Slip` where name=%(ss)s limit 1""",
				{"ss":filters.get("salary_slip")})	
		if ss:
			filters["net_pay"]=ss[0][0]

	if not filters.get("salary_slip") and filters.get("payroll_entry"):
		ss=frappe.db.sql("""SELECT name,net_pay FROM `tabSalary Slip` where employee=%(employee)s
				and payroll_entry=%(payroll_entry)s and docstatus=1 limit 1""",
				{"employee":filters.get("employee"),"payroll_entry":filters.get("payroll_entry")})	
		if ss:
			filters["salary_slip"]=ss[0][0]
			filters["net_pay"]=ss[0][1]
		else:
			#frappe.msgprint("there is no salary slip for specific payroll entry")
			return [], []
	#frappe.msgprint("net = {0}".format(filters["net_pay"]))

	columns=[]
	activities_map = get_activities(filters)
	columns.append(""+"Account:Link/Account:150")
	columns.append(""+"Component:Link/Salary Component:150")
	columns.append(""+"Total:Currency:150")

	su=0.0
	if activities_map:
		for activities in activities_map :
			columns.append(""+"%"+cstr(activities.project_percentage)+"/"+activities.parent+":Currency:150")
			su+=activities.project_percentage
	else:
		#frappe.msgprint("No Activities for current employee")
		return [], []
	columns.append(""+"Different:Currency:100")

	if su>100.0:
		frappe.msgprint("Total of Activities more than %100 {0}".format(su))


	##
	#comp_map = get_get_comp_activities(filters)
	#for comp in comp_map:
	
	data = []
	row = []
	data.append(row)
	for ss in get_salary_slip(filters,True):
		if ss.salary_component:
			row = []
			row += [ss.account]
			row += [ss.salary_component]
			row += [ss.amount]
			summ=0.0;
			for activities in activities_map :
				if ss.salary_component in get_com_from_act(activities.parent):
					row += [ss.amount*activities.project_percentage/100]
					summ+=ss.amount*activities.project_percentage/100
				else:
					row += [0.0]
			row += [ss.amount-summ]
			data.append(row)
	row = []
	data.append(row)
	for ss in get_salary_slip(filters,False):
		if ss.salary_component:
			row = []
			row += [ss.account]
			row += [ss.salary_component]
			row += [ss.amount]
			summ=0.0;
			for activities in activities_map :
				if ss.salary_component in get_com_from_act(activities.parent):
					row += [ss.amount*activities.project_percentage/100]
					summ+=ss.amount*activities.project_percentage/100
				else:
					row += [0.0]
			row += [ss.amount-summ]
			data.append(row)
	row = []
	data.append(row)
	row = []
	row += ["","Net Pay"]
	#for activities in activities_map :
	#	row += [""]
	row += [flt(filters.get("net_pay")) if filters.get("net_pay") else 0.0]
	data.append(row)

	return columns, data
def get_activities(filters):
	activities_map = frappe._dict()
	activities_list = frappe.db.sql("""SELECT parent,project_percentage FROM `tabProject Activity Payroll` where employee=%(employee)s and status='active' order by project_percentage DESC""",{"employee":filters["employee"]}, as_dict=1)
	if(activities_list):
		filters["activities"]=[]
		for activities in activities_list:
			if activities:
				activities_map.setdefault(activities.parent, activities)
				filters["activities"].append([activities.parent])
	return activities_list

def get_comp_activities(filters):
	comp_activities_map = frappe._dict()
	comp_activities_list = frappe.db.sql("""SELECT salary_component FROM `tabProject Activity Payroll` where parent in (%s) """ %
		(', '.join(['%s']*len(filters['activities']))), tuple([d.name for d in filters['activities']]), as_dict=1)
	for comp_activities in comp_activities_list:
		if comp_activities:
			comp_activities_map.setdefault(comp_activities.parent, comp_activities)
	return comp_activities_map

def get_conditions(filters,is_earning=True):
	conditions = []
	if is_earning:conditions.append("parentfield = 'earnings'")
	else:conditions.append("parentfield = 'deductions'")
	conditions.append("parent = %(salary_slip)s")
	return "where {}".format(" and ".join(conditions)) if conditions else ""

def get_salary_slip(filters,is_earning=True):
	slip_map = frappe._dict()
	slip_list = frappe.db.sql("""SELECT (select default_account from `tabSalary Component Account` where parent=salary_component) as account, salary_component, amount
		FROM `tabSalary Detail`
		{conditions} 
		""".format(
			conditions=get_conditions(filters,is_earning),
		),
		filters, as_dict=True)
	return slip_list

def get_com_from_act(act):	
	com_map = frappe._dict()
	com_list = frappe.db.sql("""SELECT salary_component FROM `tabProject Activity Salary Component` where parent=%(parent)s """,{"parent":act}, as_dict=1)
	if(com_list):
		for com in com_list:
			if com:
				com_map.setdefault(com.salary_component, com)
	return com_map