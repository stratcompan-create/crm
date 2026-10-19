"""Teste de fumaça: manifesto do aplicativo por site (crm.api.pwa)."""

import json

import frappe

from crm.api import pwa


def run():
	frappe.set_user("Guest")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	try:
		r = pwa.manifest()
		m = json.loads(r.get_data(as_text=True))
		marca = frappe.db.get_single_value("FCRM Settings", "brand_name") or "CRM"
		ck("manifesto abre sem login (o celular precisa ler antes de entrar)", r.status_code == 200)
		ck("tipo correto do manifesto", r.mimetype == "application/manifest+json")
		ck("nome do aplicativo é o do escritório", m["name"] == marca, m["name"])
		ck("nome curto cabe no ícone (até 12 letras)", len(m["short_name"]) <= 12, m["short_name"])
		ck("abre direto no CRM, em tela cheia", m["start_url"] == "/crm" and m["display"] == "standalone")
		ck("tem ícones de 192 e 512 (instalável no Android)", {"192x192", "512x512"} <= {i["sizes"] for i in m["icons"]})
		logo = frappe.db.get_single_value("FCRM Settings", "favicon") or frappe.db.get_single_value("FCRM Settings", "brand_logo")
		ck("usa a marca do escritório como ícone quando existe", (not logo) or m["icons"][0]["src"] == logo)
	finally:
		frappe.set_user("Administrator")
	return res
