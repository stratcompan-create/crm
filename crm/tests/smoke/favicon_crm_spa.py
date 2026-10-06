"""Teste de fumaça: o favicon da marca já vem no primeiro HTML da tela do CRM (/crm), não só
depois do JavaScript carregar (o iPad não respeita a troca feita por JS nos favoritos/atalhos).

`get_context()` normalmente só roda dentro de uma requisição web de verdade (usa a sessão para
gerar o token CSRF); aqui substituímos só essa parte (`get_boot`) para testar, sem rede, a lógica
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
    ck("marca tem um favicon configurado (pré-condição)", bool(favicon), favicon)

    with mock.patch.object(crm_page, "get_boot", lambda: {}):
        ctx = crm_page.get_context()
    ck("contexto da tela do CRM traz o favicon da marca", ctx.favicon == favicon, ctx.get("favicon"))

    before = frappe.db.get_single_value("FCRM Settings", "favicon")
    try:
        frappe.db.set_single_value("FCRM Settings", "favicon", "")
        with mock.patch.object(crm_page, "get_boot", lambda: {}):
            ctx2 = crm_page.get_context()
        ck("sem favicon configurado, o contexto não quebra (vazio, não None)", ctx2.favicon == "")
    finally:
        frappe.db.set_single_value("FCRM Settings", "favicon", before)
        frappe.db.commit()

    html = open(frappe.get_app_path("crm", "www", "crm.html"), encoding="utf8").read()
    ck(
        "o HTML publicado usa {{ favicon }} com reserva, não mais o ícone fixo do modelo",
        html.count("{{ favicon or '/assets/crm/manifest/apple-icon-180.png' }}") == 2,
    )
    return res
