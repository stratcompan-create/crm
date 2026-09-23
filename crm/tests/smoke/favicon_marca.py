"""Teste de fumaça: favicon da marca nas páginas públicas (login, /documentos, /agendar).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe

from crm.api import estilo


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    before = frappe.db.get_single_value("Website Settings", "favicon")
    try:
        favicon = frappe.db.get_single_value("FCRM Settings", "favicon")
        ck("marca tem um favicon configurado (pré-condição)", bool(favicon), favicon)

        frappe.db.set_single_value("Website Settings", "favicon", None)
        estilo.sync_website_favicon()
        ck("sincroniza a marca para o Website Settings", frappe.db.get_single_value("Website Settings", "favicon") == favicon)

        frappe.db.set_single_value("Website Settings", "favicon", "/files/outro.png")
        estilo.sync_website_favicon()
        ck("corrige quando o Website Settings ficou diferente da marca", frappe.db.get_single_value("Website Settings", "favicon") == favicon)

        import crm.www.documentos as doc_ctx
        import crm.www.agendar as ag_ctx

        ck("página de documentos usa o favicon da marca", doc_ctx.get_context(frappe._dict())["favicon"] == favicon)
        ck("página de agendamento usa o favicon da marca", ag_ctx.get_context(frappe._dict())["favicon"] == favicon)
    finally:
        frappe.db.set_single_value("Website Settings", "favicon", before)
        frappe.db.commit()
    return res
