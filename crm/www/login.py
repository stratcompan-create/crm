import re

import frappe
from frappe.www.login import get_context as _core_get_context

no_cache = True


def get_context(context):
	"""Reuse Frappe core's login page context (OAuth providers, LDAP, signup,
	email-link login, redirect handling — all of it) and just add our own
	brand logo on top, read from FCRM Settings instead of the generic
	Navbar Settings app_logo (which is unconfigured and unrelated to the
	CRM's own branding)."""
	context = _core_get_context(context)
	context["crm_logo"] = (
		frappe.db.get_single_value("FCRM Settings", "brand_logo") or context.get("logo")
	)
	context["crm_name"] = short_name(frappe.db.get_single_value("FCRM Settings", "brand_name") or "")
	# a tela de entrada só tem e-mail e senha
	context["login_with_email_link"] = False
	return context


def short_name(name: str) -> str:
	"""Nome enxuto para o título da tela de entrada: sem o sufixo "company" e com
	"Escritório de Advocacia" abreviado para "Escritório"."""
	name = re.sub(r"(?i)\s*company$", "", name.strip())
	name = re.sub(r"(?i)escrit[óo]rio de advocacia", "Escritório", name)
	return name.strip()
