from frappe.model.document import Document


class CRMClientAccount(Document):
	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Cliente",
				"type": "Data",
				"key": "client_name",
				"width": "16rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Endereço do CRM",
				"type": "Data",
				"key": "url",
				"width": "16rem",
			},
			{
				"label": "Última modificação",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]

		rows = ["name", "client_name", "status", "url", "notes", "modified"]
		return {"columns": columns, "rows": rows}
