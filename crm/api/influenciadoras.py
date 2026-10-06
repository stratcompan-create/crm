# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Gestao de carteira de influenciadoras - uso interno da agencia. Diferente de
# lead/negocio: uma influenciadora nao e cliente nem prospect, e talento sob
# gestao/assessoria. Cada "CRM Parceria" e uma negociacao/contrato com uma
# marca especifica, com status, briefing, data de gravacao e prazo de entrega -
# cobre negociacao, fechamento, direcionamento de conteudo e acompanhamento de
# entregas, do jeito que a agencia realmente trabalha com elas.

import frappe
from frappe import _

MANAGER_ROLES = ("System Manager", "Sales Manager")


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


# ------------------------------------------------------------------ influenciadoras

@frappe.whitelist()
def listar_influenciadoras() -> list:
	influenciadoras = frappe.get_all(
		"CRM Influenciadora",
		fields=["name", "nome", "instagram", "nicho", "seguidores_aprox", "observacoes"],
		order_by="nome asc",
	)
	if influenciadoras:
		contagem = frappe.get_all(
			"CRM Parceria",
			filters={"influenciadora": ["in", [i["name"] for i in influenciadoras]]},
			fields=["influenciadora", "count(name) as total"],
			group_by="influenciadora",
		)
		mapa = {c["influenciadora"]: c["total"] for c in contagem}
		for i in influenciadoras:
			i["parcerias"] = mapa.get(i["name"], 0)
	return influenciadoras


@frappe.whitelist()
def criar_influenciadora(nome: str, instagram: str | None = None, nicho: str | None = None, seguidores_aprox=None, observacoes: str | None = None) -> dict:
	if not (nome or "").strip():
		frappe.throw(_("Informe o nome da influenciadora."))
	doc = frappe.get_doc(
		{
			"doctype": "CRM Influenciadora",
			"nome": nome.strip(),
			"instagram": (instagram or "").strip(),
			"nicho": (nicho or "").strip(),
			"seguidores_aprox": seguidores_aprox or 0,
			"observacoes": observacoes or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def atualizar_influenciadora(name: str, nome=None, instagram=None, nicho=None, seguidores_aprox=None, observacoes=None) -> dict:
	doc = frappe.get_doc("CRM Influenciadora", name)
	for campo, valor in (("nome", nome), ("instagram", instagram), ("nicho", nicho), ("seguidores_aprox", seguidores_aprox), ("observacoes", observacoes)):
		if valor is not None:
			doc.set(campo, valor)
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def excluir_influenciadora(name: str) -> dict:
	"""Apaga a influenciadora e todas as parcerias dela junto - so gestor,
	porque some com o historico todo."""
	_managers_only()
	for p in frappe.get_all("CRM Parceria", filters={"influenciadora": name}, pluck="name"):
		frappe.delete_doc("CRM Parceria", p, force=True, ignore_permissions=True)
	frappe.delete_doc("CRM Influenciadora", name, force=True, ignore_permissions=True)
	return {"ok": True}


# ------------------------------------------------------------------ parcerias

@frappe.whitelist()
def listar_parcerias(influenciadora: str) -> list:
	return frappe.get_all(
		"CRM Parceria",
		filters={"influenciadora": influenciadora},
		fields=["name", "marca", "status", "valor", "data_gravacao", "prazo_entrega", "briefing", "observacoes"],
		order_by="prazo_entrega asc, creation desc",
	)


@frappe.whitelist()
def criar_parceria(influenciadora: str, marca: str, status: str | None = None, valor=None, data_gravacao=None, prazo_entrega=None, briefing: str | None = None, observacoes: str | None = None) -> dict:
	if not frappe.db.exists("CRM Influenciadora", influenciadora):
		frappe.throw(_("Influenciadora não encontrada."))
	if not (marca or "").strip():
		frappe.throw(_("Informe a marca/empresa parceira."))
	doc = frappe.get_doc(
		{
			"doctype": "CRM Parceria",
			"influenciadora": influenciadora,
			"marca": marca.strip(),
			"status": status or "Negociando",
			"valor": valor or 0,
			"data_gravacao": data_gravacao or None,
			"prazo_entrega": prazo_entrega or None,
			"briefing": briefing or "",
			"observacoes": observacoes or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def atualizar_parceria(name: str, marca=None, status=None, valor=None, data_gravacao=None, prazo_entrega=None, briefing=None, observacoes=None) -> dict:
	doc = frappe.get_doc("CRM Parceria", name)
	for campo, valor_novo in (
		("marca", marca), ("status", status), ("valor", valor),
		("data_gravacao", data_gravacao), ("prazo_entrega", prazo_entrega),
		("briefing", briefing), ("observacoes", observacoes),
	):
		if valor_novo is not None:
			doc.set(campo, valor_novo)
	doc.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def excluir_parceria(name: str) -> dict:
	doc = frappe.get_doc("CRM Parceria", name)
	doc.delete(ignore_permissions=True)
	return {"ok": True}
