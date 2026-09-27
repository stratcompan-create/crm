"""Teste de fumaça: gráficos do Financeiro no dashboard nativo (Visão Geral -> Edit -> Chart).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, nowdate

from crm.api import dashboard as db


def run():
	frappe.set_user("Administrator")
	res = []
	made = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	fd, td = str(get_first_day(nowdate())), str(get_last_day(nowdate()))
	meio_do_mes = add_days(fd, 5)

	meta_original = frappe.db.get_singles_dict("CRM Financial Goals").get("meta_mrr")
	try:
		lead = frappe.get_doc({
			"doctype": "CRM Lead", "first_name": "Zz Dashboard", "last_name": "Fin",
			"email": "zz.dashboard.fin@example.com", "lead_owner": "Administrator",
		}).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))
		deal = frappe.get_doc({
			"doctype": "CRM Deal", "first_name": "Zz Dashboard", "last_name": "Fin",
			"email": "zz.dashboard.fin@example.com", "lead": lead.name, "deal_owner": "Administrator",
			"deal_value": 1000, "status": "Qualification",
		}).insert(ignore_permissions=True)
		made.append(("CRM Deal", deal.name))

		for valor in (600, 400):
			h = frappe.get_doc({
				"doctype": "CRM Honorario", "deal": deal.name, "tipo_honorario": "Fixo",
				"servico": "Outros", "valor": valor, "status": "Pago", "data_pagamento": meio_do_mes,
			}).insert(ignore_permissions=True)
			made.append(("CRM Honorario", h.name))

		r1 = db.get_receita_recebida(fd, td, None)
		ck("receita_recebida soma os honorários pagos do período", r1["value"] == 1000, r1)

		frappe.db.set_single_value("CRM Financial Goals", "meta_mrr", 2000)
		r2 = db.get_meta_mensal(fd, td, None)
		ck("meta_mensal calcula o percentual certo (1000/2000)", r2["value"] == 50, r2)

		r3 = db.get_receita_trend(fd, td, None)
		total_trend = sum(d["recebido"] for d in r3["data"])
		ck("receita_trend soma o mesmo total, por dia", total_trend == 1000, r3)
	finally:
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.set_single_value("CRM Financial Goals", "meta_mrr", meta_original or 0)
		frappe.db.commit()

	return res
