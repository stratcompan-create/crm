# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Valor recebido em nome do cliente (alvará, acordo, RPV, precatório...). Ao salvar, o CRM faz a
# prestação de contas: honorário de êxito pelo percentual do caso, desconto das custas que o
# escritório adiantou (marcadas para cobrar do cliente) e o valor que tem de ser repassado.
# O honorário entra sozinho no Financeiro como "Êxito" pago.

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


def _despesas_do_recebimento(deal: str, recebimento: str | None) -> list:
	"""Custas adiantadas do caso ainda não descontadas (ou já presas a este recebimento)."""
	filtros = {"deal": deal, "reembolsavel": 1}
	todas = frappe.get_all("CRM Despesa", filters=filtros, fields=["name", "valor", "recebimento"], order_by="data_vencimento asc")
	return [d for d in todas if not d.recebimento or d.recebimento == recebimento]


class CRMRecebimento(Document):
	def validate(self):
		bruto = flt(self.valor_bruto)
		if bruto <= 0:
			frappe.throw(_("Informe o valor recebido."))
		if self.is_new() and not flt(self.percentual_honorarios) and not flt(self.valor_honorarios):
			self.percentual_honorarios = flt(frappe.db.get_value("CRM Deal", self.deal, "percentual_exito"))
		pct = flt(self.percentual_honorarios)
		if pct < 0 or pct > 100:
			frappe.throw(_("O percentual de honorários precisa estar entre 0 e 100."))
		if pct and (self.is_new() or self.has_value_changed("percentual_honorarios") or self.has_value_changed("valor_bruto")
					or not flt(self.valor_honorarios)):
			self.valor_honorarios = round(bruto * pct / 100, 2)
		honorarios = flt(self.valor_honorarios)

		self.despesas_reembolsadas = round(sum(flt(d.valor) for d in _despesas_do_recebimento(self.deal, self.name)), 2)

		parceiros = 0
		for p in self.get("parceiros") or []:
			if flt(p.percentual):
				p.valor = round(honorarios * flt(p.percentual) / 100, 2)
			parceiros += flt(p.valor)
		if parceiros > honorarios + 0.01:
			frappe.throw(_("A divisão com parceiros (R$ {0}) passa dos honorários do escritório.").format(f"{parceiros:.2f}"))
		self.valor_parceiros = round(parceiros, 2)

		repasse = round(bruto - honorarios - flt(self.despesas_reembolsadas), 2)
		if repasse < 0:
			frappe.throw(_("Honorários e custas passam do valor recebido. Confira o percentual e as custas marcadas para cobrar do cliente."))
		self.valor_repasse = repasse
		if self.repasse_status == "Repassado" and not self.repasse_data:
			self.repasse_data = frappe.utils.nowdate()

	def on_update(self):
		# prende as custas descontadas a este recebimento
		for d in _despesas_do_recebimento(self.deal, self.name):
			if d.recebimento != self.name:
				frappe.db.set_value("CRM Despesa", d.name, {"recebimento": self.name, "reembolsado": 1}, update_modified=False)
		self._sincronizar_honorario()

	def _sincronizar_honorario(self):
		valor = flt(self.valor_honorarios)
		dados = {
			"deal": self.deal,
			"status": "Pago",
			"tipo_honorario": "Êxito",
			"valor": valor,
			"repasse": flt(self.valor_repasse),
			"data_vencimento": self.data,
			"data_pagamento": self.data,
			"observacoes": _("Êxito sobre {0} de R$ {1}").format((self.origem or "").lower(), f"{flt(self.valor_bruto):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
		}
		if self.honorario and frappe.db.exists("CRM Honorario", self.honorario):
			if valor <= 0:
				frappe.delete_doc("CRM Honorario", self.honorario, force=True, ignore_permissions=True)
				self.db_set("honorario", None, update_modified=False)
				return
			h = frappe.get_doc("CRM Honorario", self.honorario)
			h.update(dados)
			h.save(ignore_permissions=True)
		elif valor > 0:
			servico = frappe.db.get_value("CRM Deal", self.deal, "servico")
			opcoes = (frappe.get_meta("CRM Honorario").get_field("servico").options or "").split("\n")
			dados["servico"] = servico if servico in opcoes else None
			h = frappe.get_doc({"doctype": "CRM Honorario", **dados}).insert(ignore_permissions=True)
			self.db_set("honorario", h.name, update_modified=False)

	def on_trash(self):
		for d in frappe.get_all("CRM Despesa", filters={"recebimento": self.name}, pluck="name"):
			frappe.db.set_value("CRM Despesa", d, {"recebimento": None, "reembolsado": 0}, update_modified=False)
		if self.honorario and frappe.db.exists("CRM Honorario", self.honorario):
			frappe.db.set_value("CRM Recebimento", self.name, "honorario", None, update_modified=False)
			frappe.delete_doc("CRM Honorario", self.honorario, force=True, ignore_permissions=True)
