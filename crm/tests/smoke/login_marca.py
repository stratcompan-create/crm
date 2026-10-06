"""Teste de fumaca: tela de login usa a cor e o logo da marca de cada site (FCRM Settings),
caindo no icone da agencia e nas cores padrao quando o cliente ainda nao configurou os dele.

`get_context()` normalmente precisa de uma requisicao web de verdade (o core do Frappe usa a
sessao pra token CSRF, provedores de login social etc.); aqui substituimos so essa parte
(`_core_get_context`) pra testar, sem rede, a logica que realmente mudamos: logo e cores.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from unittest import mock

import frappe

import crm.www.login as login_page
from crm.api.estilo import AGENCIA_FAVICON


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	def get_context():
		with mock.patch.object(login_page, "_core_get_context", lambda context: context):
			return login_page.get_context(frappe._dict())

	fields = ["brand_logo", "brand_color", "brand_accent", "brand_name"]
	before = {f: frappe.db.get_single_value("FCRM Settings", f) for f in fields}
	try:
		# marca sem logo/cores proprias (ex.: cliente recem-ativado)
		for f in fields:
			frappe.db.set_single_value("FCRM Settings", f, "")
		frappe.db.commit()

		ctx = get_context()
		ck("sem logo proprio, usa o icone da agencia", ctx["crm_logo"] == AGENCIA_FAVICON, ctx["crm_logo"])
		ck("sem cor propria, cai na navy padrao", ctx["crm_cor"] == "#042d3c", ctx["crm_cor"])
		ck("sem destaque proprio, cai no sage padrao", ctx["crm_destaque"] == "#8aa1a9", ctx["crm_destaque"])
		ck("rgb da cor de fundo vem preenchido", ctx["crm_cor_rgb"] == "4, 45, 60", ctx["crm_cor_rgb"])

		# marca com logo e cores proprias (ex.: Macedo Fotografia - cinza chumbo)
		frappe.db.set_single_value("FCRM Settings", "brand_logo", "/files/logo-macedo.png")
		frappe.db.set_single_value("FCRM Settings", "brand_color", "#18181b")
		frappe.db.set_single_value("FCRM Settings", "brand_accent", "#71717a")
		frappe.db.set_single_value("FCRM Settings", "brand_name", "Macedo Fotografia")
		frappe.db.commit()

		ctx2 = get_context()
		ck("com logo proprio, usa o logo do cliente", ctx2["crm_logo"] == "/files/logo-macedo.png", ctx2["crm_logo"])
		ck("usa a cor propria do cliente", ctx2["crm_cor"] == "#18181b", ctx2["crm_cor"])
		ck("usa o destaque proprio do cliente", ctx2["crm_destaque"] == "#71717a", ctx2["crm_destaque"])
		ck("titulo usa o nome da marca", ctx2["crm_name"] == "Macedo Fotografia", ctx2["crm_name"])

		# cor invalida (campo vazio ou lixo) nunca quebra o contexto - cai no padrao
		frappe.db.set_single_value("FCRM Settings", "brand_color", "nao e um hex")
		frappe.db.commit()
		ctx3 = get_context()
		ck("cor invalida cai no padrao em vez de quebrar", ctx3["crm_cor"] == "#042d3c", ctx3["crm_cor"])
	finally:
		for f, v in before.items():
			frappe.db.set_single_value("FCRM Settings", f, v)
		frappe.db.commit()
	return res
