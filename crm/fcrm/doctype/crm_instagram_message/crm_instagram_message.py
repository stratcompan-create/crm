# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CRMInstagramMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		direction: DF.Literal["Received", "Sent"]
		lead: DF.Link
		message: DF.SmallText
		sender_id: DF.Data | None
		timestamp: DF.Datetime | None
	# end: auto-generated types

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Lead",
				"type": "Link",
				"key": "lead",
				"width": "12rem",
			},
			{
				"label": "Direction",
				"type": "Select",
				"key": "direction",
				"width": "8rem",
			},
			{
				"label": "Message",
				"type": "Small Text",
				"key": "message",
				"width": "20rem",
			},
			{
				"label": "Timestamp",
				"type": "Datetime",
				"key": "timestamp",
				"width": "10rem",
			},
		]

		rows = ["name", "lead", "sender_id", "direction", "message", "timestamp"]
		return {"columns": columns, "rows": rows}
