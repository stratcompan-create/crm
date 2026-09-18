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
	return context
