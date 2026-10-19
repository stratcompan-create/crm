"""Teste de fumaça: central de ajuda (crm.api.ajuda)."""

import frappe

from crm.api import ajuda


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	antes = frappe.db.get_default("crm_profile")
	try:
		frappe.db.set_default("crm_profile", "escritorio")
		g = ajuda.guias("Deal")
		ck("na tela do caso, os guias do caso vêm primeiro", g["desta_tela"] and all("Deal" in x["telas"] for x in g["desta_tela"]))
		ck("todos os guias têm título e passos", all(x["titulo"] and x["passos"] for x in g["desta_tela"] + g["outros"]))
		ck("escritório vê o guia de prestação de contas", any(x["chave"] == "caso_prestacao" for x in g["desta_tela"]))
		frappe.db.set_default("crm_profile", "agencia")
		g = ajuda.guias("Deal")
		ck("agência não vê guias só de escritório", not any(x["chave"] in ajuda.SO_ESCRITORIO for x in g["desta_tela"] + g["outros"]))
	finally:
		frappe.db.set_default("crm_profile", antes or "agencia")
		frappe.db.commit()
	return res
