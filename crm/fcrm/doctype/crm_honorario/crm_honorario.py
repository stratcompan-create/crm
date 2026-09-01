# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CRMHonorario(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data_pagamento: DF.Date | None
		data_vencimento: DF.Date | None
		deal: DF.Link
		forma_pagamento: DF.Literal["", "PIX", "Boleto", "Cartão", "Transferência"]
		observacoes: DF.SmallText | None
		parcelas: DF.Int
		status: DF.Literal["Pendente", "Pago", "Atrasado"]
		tipo_honorario: DF.Literal["Fixo", "Êxito", "Consultivo Mensal", "Por Ato"]
		valor: DF.Currency
	# end: auto-generated types

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Cliente / Deal",
				"type": "Link",
				"key": "deal",
				"width": "12rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Tipo de Honorário",
				"type": "Select",
				"key": "tipo_honorario",
				"width": "10rem",
			},
			{
				"label": "Valor",
				"type": "Currency",
				"key": "valor",
				"width": "8rem",
			},
			{
				"label": "Forma de Pagamento",
				"type": "Select",
				"key": "forma_pagamento",
				"width": "10rem",
			},
			{
				"label": "Data de Vencimento",
				"type": "Date",
				"key": "data_vencimento",
				"width": "8rem",
			},
		]

		rows = [
			"name",
			"deal",
			"status",
			"tipo_honorario",
			"valor",
			"forma_pagamento",
			"parcelas",
			"data_vencimento",
			"data_pagamento",
			"observacoes",
			"modified",
		]
		return {"columns": columns, "rows": rows}
