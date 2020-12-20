// Copyright (c) 2020, Ahmed Mohammed Alkuhlani and contributors
// For license information, please see license.txt

frappe.ui.form.on('Advance Request', {
	setup: function(frm) {
		frm.add_fetch("employee", "company", "company");
	},
	refresh: function(frm) {
		if (frm.doc.docstatus===1
			&& (flt(frm.doc.paid_amount) < flt(frm.doc.advance_amount))
			&& frappe.model.can_create("Payment Entry")) {
//			frm.add_custom_button(__('Payment'),
//			function() { frm.events.make_payment_entry(frm); }, __('Create'));

//
	    frm.add_custom_button(__('Payment Entry'), function(){
	            frappe.route_options = {"payment_type": "Internal Transfer",
	                                    "paid_to": frm.doc.account,
	                                    "advance_request": frm.doc.name,
	                                    "mode_of_payment":frm.doc.mode_of_payment_from,
	                                    "paid_amount": frm.doc.advance_amount,
	                                    "base_paid_amount": frm.doc.advance_amount,
	                                    "base_received_amount": frm.doc.advance_amount,
	                                    "received_amount": frm.doc.advance_amount
	            },
	        	frappe.set_route("Form", "Payment Entry", "New Payment Entry 1");                       
            }, __("Create"));
//
		}
		else if (
			frm.doc.docstatus === 1
			&& flt(frm.doc.claimed_amount) < flt(frm.doc.paid_amount) - flt(frm.doc.return_amount)
			&& frappe.model.can_create("Expense Entry")
		) {
			frm.add_custom_button(
				__("Expense Entry"),
				function() {
					frm.events.make_expense_claim(frm);
				},
				__('Create')
			);
		}

		if (frm.doc.docstatus === 1
			&& (flt(frm.doc.claimed_amount) + flt(frm.doc.return_amount) < flt(frm.doc.paid_amount))
			&& frappe.model.can_create("Journal Entry")) {

			frm.add_custom_button(__("Return"),  function() {
				frm.trigger('make_return_entry');
			}, __('Create'));
		}
	},

	make_payment_entry: function(frm) {
		var method = "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry";
		if(frm.doc.__onload && frm.doc.__onload.make_payment_via_journal_entry) {
			method = "pav.pav.doctype.advance_request.advance_request.make_bank_entry"
		}
		return frappe.call({
			method: method,
			args: {
				"dt": frm.doc.doctype,
				"dn": frm.doc.name
			},
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_expense_claim: function(frm) {
		return frappe.call({
			method: "erpnext.hr.doctype.expense_claim.expense_claim.get_expense_claim",
			args: {
				"employee_name": frm.doc.employee,
				"company": frm.doc.company,
				"employee_advance_name": frm.doc.name,
				"posting_date": frm.doc.posting_date,
				"paid_amount": frm.doc.paid_amount,
				"claimed_amount": frm.doc.claimed_amount
			},
			callback: function(r) {
				const doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_return_entry: function(frm) {
		frappe.call({
			method: 'erpnext.hr.doctype.employee_advance.employee_advance.make_return_entry',
			args: {
				'employee': frm.doc.employee,
				'company': frm.doc.company,
				'employee_advance_name': frm.doc.name,
				'return_amount': flt(frm.doc.paid_amount - frm.doc.claimed_amount),
				'advance_account': frm.doc.advance_account,
				'mode_of_payment': frm.doc.mode_of_payment
			},
			callback: function(r) {
				const doclist = frappe.model.sync(r.message);
				frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
			}
		});
	},
    mode_of_payment: function (frm) {
        frappe.call({
            method: "pav.pav.doctype.expense_entry.expense_entry.get_payment_account",
            args: {
                "mode_of_payment": frm.doc.mode_of_payment,
                "company": frm.doc.company
            },
            callback: function (r) {
                if (r.message) {
			if(r.message.account){
				cur_frm.set_value("account", r.message.account);
			}			
			if(r.message.currency){
				cur_frm.set_value("currency", r.message.currency);
			}
                    frm.refresh_fields();
                    cur_frm.refresh_field('account');

                } else {
                    console.log("yyyyyyyy")
                    frm.set_value("account", "");
                    frm.set_value("currency", "");
                    frm.set_value("mode_of_payment", "");
                    frm.refresh_fields();
                    return;
                }
                    frm.refresh_fields();

            }
        });
        console.log(frm.doc.account)
    }

/*
	employee: function (frm) {
		if (frm.doc.employee) {
			return frappe.call({
				method: "erpnext.hr.doctype.employee_advance.employee_advance.get_due_advance_amount",
				args: {
					"employee": frm.doc.employee,
					"posting_date": frm.doc.posting_date
				},
				callback: function(r) {
					frm.set_value("due_advance_amount",r.message);
				}
			});
		}
	}
*/
});
