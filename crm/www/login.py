import re

import frappe
from frappe.www.login import get_context as _core_get_context

from crm.api.estilo import AGENCIA_FAVICON, mix, valid_hex

no_cache = True


def get_context(context):
	"""Reuse Frappe core's login page context (OAuth providers, LDAP, signup,
	email-link login, redirect handling - all of it) and just add our own
	brand logo and colors on top, read from FCRM Settings instead of the generic
	Navbar Settings app_logo (which is unconfigured and unrelated to the
	CRM's own branding)."""
	context = _core_get_context(context)
	settings = frappe.db.get_singles_dict("FCRM Settings") or {}

	# sem logo proprio, usa o icone da agencia - nunca o logo generico do Frappe
	context["crm_logo"] = settings.get("brand_logo") or AGENCIA_FAVICON
	context["crm_name"] = short_name(settings.get("brand_name") or "")
	# a tela de entrada so tem e-mail e senha
	context["login_with_email_link"] = False

	# mesmas cores da marca usadas nas propostas (Configuracoes > Marca), pra cada
	# cliente ter a tela de entrada na cor dele em vez da navy fixa da Stratcompany
	cor = valid_hex(settings.get("brand_color"), "#042d3c")
	destaque = valid_hex(settings.get("brand_accent"), "#8aa1a9")
	context["crm_cor"] = cor
	context["crm_destaque"] = destaque
	context["crm_cor_clara_rgb"] = _rgb(mix(cor, "#ffffff", 0.35))
	context["crm_cor_rgb"] = _rgb(cor)
	context["crm_destaque_rgb"] = _rgb(destaque)
	return context


def _rgb(hex_color: str) -> str:
	h = hex_color.lstrip("#")
	return ", ".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))


def short_name(name: str) -> str:
	"""Nome enxuto para o titulo da tela de entrada: sem o sufixo "company" e com
	"Escritorio de Advocacia" abreviado para "Escritorio"."""
	name = re.sub(r"(?i)\s*company$", "", name.strip())
	name = re.sub(r"(?i)escrit[\u00f3o]rio de advocacia", "Escrit\u00f3rio", name)
	return name.strip()
