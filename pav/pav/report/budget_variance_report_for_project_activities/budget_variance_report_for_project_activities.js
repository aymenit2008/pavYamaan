// Copyright (c) 2016, Ahmed Mohammed Alkuhlani and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Budget Variance Report for Project Activities"] = {
	"filters": [
		{
			fieldname: "from_fiscal_year",
			label: __("From Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: frappe.sys_defaults.fiscal_year,
			reqd: 1
		},
		{
			fieldname: "to_fiscal_year",
			label: __("To Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: frappe.sys_defaults.fiscal_year,
			reqd: 1
		},
		{
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			default: "Yearly",
			reqd: 1
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "project_dimension",
			label: __("Project Dimension"),
			fieldtype: "Link",
			options: "Project Dimension",
		},
		{
			fieldname: "budget_against",
			label: __("Budget Against"),
			fieldtype: "Data",
			default: "Project Activities",
			reqd: 1,
			reqd: 1,
			on_change: function() {
				frappe.query_report.set_filter_value("budget_against_filter", []);
				frappe.query_report.refresh();
			}
		},
		{
			fieldname:"budget_against_filter",
			label: __('Dimension Filter'),
			fieldtype: "MultiSelectList",
			get_data: function(txt) {
				if (!frappe.query_report.filters) return;

				let budget_against = frappe.query_report.get_filter_value('budget_against');
				if (!budget_against) return;

				return frappe.db.get_link_options(budget_against, txt);
			}
		},
		{
			fieldname:"show_cumulative",
			label: __("Show Cumulative Amount"),
			fieldtype: "Check",
			default: 0,
		},
	]
}

erpnext.dimension_filters.forEach((dimension) => {
	frappe.query_reports["Budget Variance Report for Project Activities"].filters[5].options.push(dimension["document_type"]);
});

