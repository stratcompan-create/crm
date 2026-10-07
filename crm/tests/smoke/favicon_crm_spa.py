"""Teste de fumaca: o favicon da marca ja vem no primeiro HTML da tela do CRM (/crm), nao so
depois do JavaScript carregar (o iPad nao respeita a troca feita por JS nos favoritos/atalhos).

`get_context()` normalmente so roda dentro de uma requisicao web de verdade (usa a sessao para
gerar o token CSRF); aqui substituimos so essa parte (`get_boot`) para testar, sem rede, a logica
que realmente mudamos: a leitura do favicon.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from unittest import mock

import frappe

import crm.www.crm as crm_page


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	favicon = frappe.db.get_single_value("FCRM Settings", "favicon")
	ck("marca tem um favicon configurado (pre-condicao)", bool(favicon), favicon)

	with mock.patch.object(crm_page, "get_boot", lambda: {}):
		ctx = crm_page.get_context()
	ck("contexto da tela do CRM traz o favicon da marca", ctx.favicon == favicon, ctx.get("favicon"))

	before = frappe.db.get_single_value("FCRM Settings", "favicon")
	try:
		frappe.db.set_single_value("FCRM Settings", "favicon", "")
		with mock.patch.object(crm_page, "get_boot", lambda: {}):
			ctx2 = crm_page.get_context()
		ck("sem favicon configurado, o contexto nao quebra (vazio, nao None)", ctx2.favicon == "")
	finally:
		frappe.db.set_single_value("FCRM Settings", "favicon", before)
		frappe.db.commit()

	html = open(frappe.get_app_path("crm", "www", "crm.html"), encoding="utf8").read()
	ck(
		"o HTML publicado usa {{ favicon }} com reserva no icone da agencia, nao mais o da CRM generico",
		html.count("{{ favicon or '/assets/crm/images/marca-agencia.png' }}") == 2,
	)
	return res
