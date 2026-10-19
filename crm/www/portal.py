import frappe


def get_context(context):
	"""Favicon da marca (a mesma de Configurações → Marca), para não cair no ícone
	padrão do Frappe nesta página pública."""
	context.favicon = frappe.db.get_single_value("FCRM Settings", "favicon") or context.get("favicon")
	context.no_cache = 1
	return context
