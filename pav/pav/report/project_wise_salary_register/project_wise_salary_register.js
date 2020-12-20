// Copyright (c) 2016, Ahmed Mohammed Alkuhlani and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Project-wise Salary Register"] = {
	"filters": [
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"reqd": 1
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"project_activity",
			"label": __("Project Activities"),
			"fieldtype": "Link",
			"options": "Project Activities"
		},
		{
			"fieldname":"payroll_entry",
			"label": __("Payroll Entry"),
			"fieldtype": "Link",
			"options": "Payroll Entry"
		},
		{
			"fieldname":"salary_slip",
			"label": __("Salary Slip"),
			"fieldtype": "Link",
			"options": "Salary Slip"
		}
	]
}
