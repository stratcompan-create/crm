import frappe


def get_context(context):
	"""Página pública de confirmação de audiência. O token do link é a credencial;
	nada é carregado aqui no servidor — a página busca pelo token via API."""
	context.favicon = frappe.db.get_single_value("FCRM Settings", "favicon") or context.get("favicon")
	context.no_cache = 1
	return context
