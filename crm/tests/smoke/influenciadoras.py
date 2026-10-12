"""Teste de fumaça: carteira de influenciadoras e parcerias (crm.api.influenciadoras).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe
from frappe.utils import add_days, nowdate

from crm.api import automacoes as au
from crm.api import financeiro
from crm.api import influenciadoras as inf


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	i1 = None
	try:
		r1 = inf.criar_influenciadora("Zz Teste Influenciadora", instagram="@zzteste", nicho="Moda", seguidores_aprox=1000)
		i1 = r1["name"]
		ck("criar_influenciadora devolve o nome", bool(i1))

		p1 = inf.criar_parceria(i1, "Marca A", status="Negociando", valor=1000, prazo_entrega="2026-11-01")
		p2 = inf.criar_parceria(i1, "Marca B", valor=2000)
		ck("criar_parceria aceita status explícito", bool(p1.get("name")))
		ck("criar_parceria usa 'Negociando' como padrão quando não informado", frappe.db.get_value("CRM Parceria", p2["name"], "status") == "Negociando")

		erro_sem_influenciadora = None
		try:
			inf.criar_parceria("influenciadora-que-nao-existe", "Marca X")
		except frappe.ValidationError as e:
			erro_sem_influenciadora = str(e)
		ck("criar_parceria recusa influenciadora inexistente", bool(erro_sem_influenciadora))

		lst = inf.listar_influenciadoras()
		encontrada = next((x for x in lst if x["name"] == i1), None)
		ck("listar_influenciadoras encontra a criada", encontrada is not None)
		ck("listar_influenciadoras conta as 2 parcerias dela", encontrada and encontrada["parcerias"] == 2)

		parcerias = inf.listar_parcerias(i1)
		ck("listar_parcerias traz as 2 parcerias", len(parcerias) == 2)

		inf.atualizar_parceria(p1["name"], status="Fechada", valor=1200)
		depois = frappe.db.get_value("CRM Parceria", p1["name"], ["status", "valor"], as_dict=True)
		ck("atualizar_parceria muda status e valor", depois.status == "Fechada" and depois.valor == 1200)
		inf.atualizar_parceria(p1["name"], valor_pago=1200, data_pagamento=nowdate())

		# comissao por %: 1200 pago, 10% -> 120, dividido pelos percentuais do Financeiro (60/15/15/10 por padrao)
		inf.atualizar_parceria(p1["name"], comissao_modelo="Comissão (%)", comissao_pct=10)
		p1_doc = frappe.get_doc("CRM Parceria", p1["name"])
		ck("comissao por % calcula sobre o valor PAGO, nao o negociado", p1_doc.comissao_calculada == 120, p1_doc.comissao_calculada)
		pct_cfg = au.get_config()
		esperado_prolabore = round(120 * frappe.utils.flt(pct_cfg.get("divisao_prolabore_pct")) / 100, 2)
		ck("parceria tambem recebe a divisao de caixa (pro-labore)", p1_doc.divisao_prolabore == esperado_prolabore, (p1_doc.divisao_prolabore, esperado_prolabore))

		# comissao por valor fixo: independe do %, so olha se ja foi pago algo
		inf.atualizar_parceria(p2["name"], valor_pago=500, data_pagamento=nowdate(), comissao_modelo="Valor fixo", comissao_valor_fixo=300)
		p2_doc = frappe.get_doc("CRM Parceria", p2["name"])
		ck("comissao por valor fixo usa o valor fixo (nao calcula %)", p2_doc.comissao_calculada == 300, p2_doc.comissao_calculada)

		painel_antes = inf.get_painel_influenciadoras()
		ck("get_painel_influenciadoras soma as comissoes das duas parcerias", painel_antes["comissao_total"] >= 420, painel_antes["comissao_total"])

		fd, td = nowdate(), nowdate()
		divisao = financeiro.get_divisao_periodo(fd, td)
		ck(
			"get_divisao_periodo do Financeiro inclui a comissao das parcerias de influenciadoras",
			divisao["comissoes_influenciadoras"] >= 420,
			divisao,
		)

		painel = inf.get_painel_influenciadoras()
		linha = next((r for r in painel["ranking"] if r["name"] == i1), None)
		ck("get_painel_influenciadoras traz a influenciadora no ranking depois de receber", linha is not None, painel["ranking"])
		ck("ranking soma o valor_pago certo (so a parceria paga conta)", linha and linha["total_recebido"] == 1700, linha)
		ck("get_painel_influenciadoras conta parcerias ativas (so p2, p1 esta Fechada que nao fecha)", painel["total_parcerias_ativas"] >= 1)

		# prazos: uma atrasada (2 dias atras), uma proxima (1 dia), uma longe (30 dias - nao deve aparecer)
		p_atrasada = inf.criar_parceria(i1, "Marca Atrasada", prazo_entrega=add_days(nowdate(), -2))
		p_proxima = inf.criar_parceria(i1, "Marca Proxima", prazo_entrega=add_days(nowdate(), 1))
		p_longe = inf.criar_parceria(i1, "Marca Longe", prazo_entrega=add_days(nowdate(), 30))
		vencer = inf._parcerias_a_vencer()
		nomes_atrasadas = [v["name"] for v in vencer["atrasadas"]]
		nomes_proximas = [v["name"] for v in vencer["proximas"]]
		todos_nomes = nomes_atrasadas + nomes_proximas
		ck("_parcerias_a_vencer classifica a atrasada certo", p_atrasada["name"] in nomes_atrasadas)
		ck("_parcerias_a_vencer classifica a proxima certo", p_proxima["name"] in nomes_proximas)
		ck("_parcerias_a_vencer nao traz a que esta longe (30 dias)", p_longe["name"] not in todos_nomes)

		try:
			inf.avisar_prazos_entrega()
			ck("avisar_prazos_entrega roda sem quebrar (sem Email Account, sai cedo)", True)
		except Exception as e:
			ck("avisar_prazos_entrega roda sem quebrar (sem Email Account, sai cedo)", False, e)

		for p in (p_atrasada, p_proxima, p_longe):
			frappe.delete_doc("CRM Parceria", p["name"], force=True, ignore_permissions=True)

		inf.atualizar_influenciadora(i1, nicho="Moda e Beleza")
		ck("atualizar_influenciadora muda o nicho", frappe.db.get_value("CRM Influenciadora", i1, "nicho") == "Moda e Beleza")

		inf.excluir_parceria(p2["name"])
		ck("excluir_parceria remove de verdade", not frappe.db.exists("CRM Parceria", p2["name"]))
		ck("excluir_parceria não mexe na outra parceria", frappe.db.exists("CRM Parceria", p1["name"]))

		inf.excluir_influenciadora(i1)
		ck("excluir_influenciadora remove a influenciadora", not frappe.db.exists("CRM Influenciadora", i1))
		ck("excluir_influenciadora apaga as parcerias dela junto", not frappe.db.exists("CRM Parceria", p1["name"]))
		i1 = None
	finally:
		if i1:
			for p in frappe.get_all("CRM Parceria", filters={"influenciadora": i1}, pluck="name"):
				frappe.delete_doc("CRM Parceria", p, force=True, ignore_permissions=True)
			frappe.delete_doc("CRM Influenciadora", i1, force=True, ignore_permissions=True)
		frappe.db.commit()

	return res
