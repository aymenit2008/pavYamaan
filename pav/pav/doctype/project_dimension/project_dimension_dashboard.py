from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This Form Developed By Partner Team'),
		'fieldname': 'project_dimension',
		'transactions': [
			{
				'label': _('Project Activities'),
				'items': ['Project Activities']
			},
			{
				'label': _('Material'),
				'items': ['Material Request', 'Stock Entry']
			},
			{
				'label': _('Sales'),
				'items': ['Sales Order', 'Delivery Note', 'Sales Invoice']
			},
			{
				'label': _('Purchase'),
				'items': ['Purchase Order', 'Purchase Receipt', 'Purchase Invoice']
			},
                        {
				'label': _('Accounts'),
				'items': ['Budget']
			},

		]
	}
