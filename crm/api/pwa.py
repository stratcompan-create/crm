# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Manifesto do aplicativo por site: quem instala o CRM no celular ("Adicionar à tela inicial")
# vê o nome, o ícone e a cor do próprio escritório, e não um "CRM" genérico.

import json

import frappe
from werkzeug.wrappers import Response

ICONES_PADRAO = [
	{"src": "/assets/crm/manifest/manifest-icon-192.maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
	{"src": "/assets/crm/manifest/manifest-icon-512.maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
]


def _tipo(url: str) -> str:
	u = (url or "").lower()
	return "image/svg+xml" if u.endswith(".svg") else "image/jpeg" if u.endswith((".jpg", ".jpeg")) else "image/png"


def dados_manifesto() -> dict:
	g = frappe.db.get_single_value
	marca = (g("FCRM Settings", "brand_name") or "CRM").strip()
	cor = g("FCRM Settings", "brand_color") or "#042d3c"
	icones = []
	for url in dict.fromkeys(filter(None, [g("FCRM Settings", "favicon"), g("FCRM Settings", "brand_logo")])):
		icones.append({"src": url, "sizes": "any", "type": _tipo(url), "purpose": "any"})
	return {
		"name": marca,
		"short_name": marca if len(marca) <= 12 else marca.split(" ")[0][:12],
		"description": f"Sistema de gestão — {marca}",
		"start_url": "/crm",
		"scope": "/",
		"display": "standalone",
		"background_color": "#ffffff",
		"theme_color": cor if str(cor).startswith("#") else "#042d3c",
		"lang": "pt-BR",
		"icons": icones + ICONES_PADRAO,
	}


@frappe.whitelist(allow_guest=True)
def manifest():
	return Response(json.dumps(dados_manifesto(), ensure_ascii=False), mimetype="application/manifest+json",
					headers={"Cache-Control": "public, max-age=3600"})
