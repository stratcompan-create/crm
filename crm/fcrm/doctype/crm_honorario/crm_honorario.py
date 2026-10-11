# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, flt, nowdate

DIVISAO_CAMPOS = {
	"divisao_prolabore": "divisao_prolabore_pct",
	"divisao_impostos": "divisao_impostos_pct",
	"divisao_crescimento": "divisao_crescimento_pct",
	"divisao_custos": "divisao_custos_pct",
}


class CRMHonorario(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data_pagamento: DF.Date | None
		data_vencimento: DF.Date | None
		deal: DF.Link
		servico: DF.Literal["", "Audiovisual", "Sites", "Tráfego Pago", "CRM Jurídico", "Outros"]
		forma_pagamento: DF.Literal["", "PIX", "Boleto", "Cartão", "Transferência"]
		observacoes: DF.SmallText | None
		parcelas: DF.Int
		status: DF.Literal["Pendente", "Pago", "Atrasado"]
		tipo_honorario: DF.Literal["Fixo", "Êxito", "Consultivo Mensal", "Por Ato"]
		valor: DF.Currency
	# end: auto-generated types

	def before_save(self):
		if self.status == "Pago" and not self.data_pagamento:
			self.data_pagamento = nowdate()
		self._calcular_divisao()

	def _calcular_divisao(self):
		"""Divide o valor que sobra (depois de tirar repasse e custo direto, que são
		valores reais e conhecidos na hora) pelos percentuais configurados em
		Configurações → Automações. Roda em todo save, não só quando paga, pra já
		mostrar a divisão na hora que o pagamento é registrado/fechado."""
		liquido = max(0, flt(self.valor) - flt(self.repasse) - flt(self.custo_direto))
		self.valor_liquido = liquido
		try:
			from crm.api.automacoes import get_config

			cfg = get_config()
		except Exception:
			cfg = {}
		for campo, chave_pct in DIVISAO_CAMPOS.items():
			self.set(campo, round(liquido * flt(cfg.get(chave_pct)) / 100, 2))

	def on_update(self):
		if self.tipo_honorario == "Consultivo Mensal" and self.status == "Pago" and self.has_value_changed("status"):
			self.create_next_month()

	def create_next_month(self):
		"""Mensalidade paga gera sozinha a cobrança do mês seguinte (base do MRR)."""
		if not self.data_vencimento or frappe.db.exists(
			"CRM Honorario",
			{
				"deal": self.deal,
				"tipo_honorario": "Consultivo Mensal",
				"data_vencimento": [">", self.data_vencimento],
			},
		):
			return
		frappe.get_doc(
			{
				"doctype": "CRM Honorario",
				"deal": self.deal,
				"tipo_honorario": "Consultivo Mensal",
				"servico": self.servico,
				"valor": self.valor,
				"repasse": self.repasse,
				"custo_direto": self.custo_direto,
				"forma_pagamento": self.forma_pagamento,
				"status": "Pendente",
				"data_vencimento": add_months(self.data_vencimento, 1),
			}
		).insert(ignore_permissions=True)

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
				"label": "Serviço",
				"type": "Select",
				"key": "servico",
				"width": "9rem",
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
			"servico",
			"valor",
			"forma_pagamento",
			"parcelas",
			"data_vencimento",
			"data_pagamento",
			"observacoes",
			"modified",
		]
		return {"columns": columns, "rows": rows}
