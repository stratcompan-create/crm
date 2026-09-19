# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, nowdate


class CRMDespesa(Document):
	def before_save(self):
		if self.status == "Pago" and not self.data_pagamento:
			self.data_pagamento = nowdate()

	def on_update(self):
		if self.recorrente and self.status == "Pago" and self.has_value_changed("status"):
			self.create_next_month()

	def create_next_month(self):
		"""Despesa recorrente paga gera sozinha a do mês seguinte."""
		if frappe.db.exists(
			"CRM Despesa",
			{
				"descricao": self.descricao,
				"recorrente": 1,
				"data_vencimento": [">", self.data_vencimento],
			},
		):
			return
		frappe.get_doc(
			{
				"doctype": "CRM Despesa",
				"descricao": self.descricao,
				"categoria": self.categoria,
				"valor": self.valor,
				"fornecedor": self.fornecedor,
				"deal": self.deal,
				"recorrente": 1,
				"status": "Pendente",
				"data_vencimento": add_months(self.data_vencimento, 1),
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def default_list_data():
		columns = [
			{"label": "Descrição", "type": "Data", "key": "descricao", "width": "14rem"},
			{"label": "Categoria", "type": "Select", "key": "categoria", "width": "10rem"},
			{"label": "Status", "type": "Select", "key": "status", "width": "8rem"},
			{"label": "Valor", "type": "Currency", "key": "valor", "width": "8rem"},
			{"label": "Data de Vencimento", "type": "Date", "key": "data_vencimento", "width": "9rem"},
			{"label": "Fornecedor / Pago a", "type": "Data", "key": "fornecedor", "width": "10rem"},
		]
		rows = [
			"name",
			"descricao",
			"categoria",
			"status",
			"valor",
			"data_vencimento",
			"data_pagamento",
			"fornecedor",
			"recorrente",
			"deal",
			"observacoes",
			"modified",
		]
		return {"columns": columns, "rows": rows}
