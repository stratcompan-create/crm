"""Teste de fumaca: favicon da marca nas paginas publicas (login, /documentos, /agendar).

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

	before_website = frappe.db.get_single_value("Website Settings", "favicon")
	before_fcrm = frappe.db.get_single_value("FCRM Settings", "favicon")
	try:
		favicon = before_fcrm
		ck("marca tem um favicon configurado (pre-condicao)", bool(favicon), favicon)

		frappe.db.set_single_value("Website Settings", "favicon", None)
		estilo.sync_website_favicon()
		ck("sincroniza a marca para o Website Settings", frappe.db.get_single_value("Website Settings", "favicon") == favicon)

		frappe.db.set_single_value("Website Settings", "favicon", "/files/outro.png")
		estilo.sync_website_favicon()
		ck("corrige quando o Website Settings ficou diferente da marca", frappe.db.get_single_value("Website Settings", "favicon") == favicon)

		# sem favicon proprio (cliente novo, sem logo ainda): cai no icone da agencia,
		# nunca no padrao do Frappe/Frappe Cloud
		frappe.db.set_single_value("FCRM Settings", "favicon", "")
		frappe.db.set_single_value("Website Settings", "favicon", "/files/outro.png")
		estilo.sync_website_favicon()
		ck(
			"sem favicon proprio, usa o icone da agencia",
			frappe.db.get_single_value("Website Settings", "favicon") == estilo.AGENCIA_FAVICON,
		)

		frappe.db.set_single_value("FCRM Settings", "favicon", favicon)
		estilo.sync_website_favicon()

		import crm.www.documentos as doc_ctx
		import crm.www.agendar as ag_ctx

		ck("pagina de documentos usa o favicon da marca", doc_ctx.get_context(frappe._dict())["favicon"] == favicon)
		ck("pagina de agendamento usa o favicon da marca", ag_ctx.get_context(frappe._dict())["favicon"] == favicon)
	finally:
		frappe.db.set_single_value("FCRM Settings", "favicon", before_fcrm)
		frappe.db.set_single_value("Website Settings", "favicon", before_website)
		frappe.db.commit()
	return res
