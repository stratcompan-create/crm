# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Opções de listas que mudam conforme o perfil do site (o escritório tem as suas categorias de
# horas e de despesas). As telas pedem a lista aqui em vez de ter a lista fixa no código.

import frappe

PERMITIDOS = {
	("CRM Horas", "frente"),
	("CRM Despesa", "categoria"),
	("CRM Honorario", "servico"),
	("CRM Honorario", "tipo_honorario"),
}


@frappe.whitelist()
def opcoes(doctype: str, campo: str) -> list[str]:
	if (doctype, campo) not in PERMITIDOS:
		frappe.throw(frappe._("Lista não disponível."))
	field = frappe.get_meta(doctype).get_field(campo)
	return [o for o in (field.options or "").split("\n") if o.strip()] if field else []
