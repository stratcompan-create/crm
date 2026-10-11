"""Teste de fumaca: divisao automatica do caixa de cada honorario (pro-labore,
impostos, crescimento, custos da empresa), com repasse a terceiros e custo
direto do servico descontados antes da divisao percentual.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe
from frappe.utils import add_days, get_first_day, get_last_day, nowdate

from crm.api import automacoes as au
from crm.api import financeiro


def run():
	frappe.set_user("Administrator")
	res = []
	made = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	pct_originais = {k: frappe.db.get_single_value("CRM Automacoes Config", k) for k in au.DIVISAO_CHAVES}
	try:
		frappe.db.set_single_value("CRM Automacoes Config", "divisao_prolabore_pct", 60)
		frappe.db.set_single_value("CRM Automacoes Config", "divisao_impostos_pct", 15)
		frappe.db.set_single_value("CRM Automacoes Config", "divisao_crescimento_pct", 15)
		frappe.db.set_single_value("CRM Automacoes Config", "divisao_custos_pct", 10)
		frappe.db.commit()

		lead = frappe.get_doc({
			"doctype": "CRM Lead", "first_name": "Zz Divisao", "last_name": "Caixa",
			"email": "zz.divisao.caixa@example.com", "lead_owner": "Administrator",
		}).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))
		deal = frappe.get_doc({
			"doctype": "CRM Deal", "first_name": "Zz Divisao", "last_name": "Caixa",
			"email": "zz.divisao.caixa@example.com", "lead": lead.name, "deal_owner": "Administrator",
			"deal_value": 9000, "status": "Qualification",
		}).insert(ignore_permissions=True)
		made.append(("CRM Deal", deal.name))

		# 9000 sem repasse/custo direto -> divide tudo certinho
		h1 = frappe.get_doc({
			"doctype": "CRM Honorario", "deal": deal.name, "tipo_honorario": "Fixo",
			"servico": "Outros", "valor": 9000, "status": "Pendente",
		}).insert(ignore_permissions=True)
		made.append(("CRM Honorario", h1.name))
		ck("valor_liquido sem repasse/custo direto = valor cheio", h1.valor_liquido == 9000, h1.valor_liquido)
		ck("pro-labore calcula 60% do liquido", h1.divisao_prolabore == 5400, h1.divisao_prolabore)
		ck("impostos calcula 15% do liquido", h1.divisao_impostos == 1350, h1.divisao_impostos)
		ck("crescimento calcula 15% do liquido", h1.divisao_crescimento == 1350, h1.divisao_crescimento)
		ck("custos calcula 10% do liquido", h1.divisao_custos == 900, h1.divisao_custos)
		ck(
			"os 4 baldes somam de volta o valor liquido",
			h1.divisao_prolabore + h1.divisao_impostos + h1.divisao_crescimento + h1.divisao_custos == h1.valor_liquido,
		)

		# 800 de trafego pago com 500 de repasse -> so 300 liquido pra dividir
		h2 = frappe.get_doc({
			"doctype": "CRM Honorario", "deal": deal.name, "tipo_honorario": "Consultivo Mensal",
			"servico": "Tráfego Pago", "valor": 800, "repasse": 500, "status": "Pendente",
			"data_vencimento": nowdate(),
		}).insert(ignore_permissions=True)
		made.append(("CRM Honorario", h2.name))
		ck("repasse eh descontado antes da divisao", h2.valor_liquido == 300, h2.valor_liquido)
		ck("pro-labore sobre o liquido (300), nao sobre o valor cheio (800)", h2.divisao_prolabore == 180, h2.divisao_prolabore)

		# custo direto tambem desconta (audiovisual: edicao + transporte)
		h3 = frappe.get_doc({
			"doctype": "CRM Honorario", "deal": deal.name, "tipo_honorario": "Fixo",
			"servico": "Audiovisual", "valor": 2000, "custo_direto": 500, "status": "Pendente",
		}).insert(ignore_permissions=True)
		made.append(("CRM Honorario", h3.name))
		ck("custo direto eh descontado antes da divisao", h3.valor_liquido == 1500, h3.valor_liquido)

		# mensalidade recorrente paga carrega repasse/custo_direto pro mes seguinte
		h2.status = "Pago"
		h2.data_pagamento = nowdate()
		h2.save(ignore_permissions=True)
		proximo = frappe.get_all(
			"CRM Honorario",
			filters={"deal": deal.name, "tipo_honorario": "Consultivo Mensal", "name": ["!=", h2.name]},
			fields=["name", "repasse", "valor"],
		)
		made.extend(("CRM Honorario", p.name) for p in proximo)
		ck("mensalidade paga gera a do mes seguinte", len(proximo) == 1, proximo)
		if proximo:
			ck("mes seguinte carrega o mesmo repasse", proximo[0].repasse == 500, proximo[0].repasse)

		# get_divisao_periodo: agrega so o que foi PAGO, soma as colunas prontas
		fd, td = str(get_first_day(nowdate())), str(get_last_day(nowdate()))
		agregado = financeiro.get_divisao_periodo(fd, td)
		ck(
			"get_divisao_periodo soma so os honorarios pagos do periodo (so h2 esta pago aqui)",
			agregado["valor"] == 800 and agregado["valor_liquido"] == 300 and agregado["divisao_prolabore"] == 180,
			agregado,
		)

		# save_settings recusa percentuais que nao somam 100
		try:
			au.save_settings('{"divisao_prolabore_pct": 50}')
			ck("save_settings recusa divisao que nao soma 100%", False)
		except frappe.ValidationError:
			ck("save_settings recusa divisao que nao soma 100%", True)

		# e aceita quando soma 100
		au.save_settings('{"divisao_prolabore_pct": 55, "divisao_impostos_pct": 15, "divisao_crescimento_pct": 20, "divisao_custos_pct": 10}')
		ck(
			"save_settings aceita quando os 4 somam 100%",
			int(au.get_config().get("divisao_prolabore_pct")) == 55,
		)
	finally:
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		for k, v in pct_originais.items():
			frappe.db.set_single_value("CRM Automacoes Config", k, v)
		frappe.db.commit()

	return res
