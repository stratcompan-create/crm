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
from frappe.utils import add_days, flt, getdate, nowdate

MANAGER_ROLES = ("System Manager", "Sales Manager")

STATUS_ENCERRADOS = ("Entregue", "Cancelada")
PRAZO_AVISO_DIAS = 3


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


# ------------------------------------------------------------------ influenciadoras

@frappe.whitelist()
def listar_influenciadoras() -> list:
	influenciadoras = frappe.get_all(
		"CRM Influenciadora",
		fields=["name", "foto", "nome", "instagram", "nicho", "seguidores_aprox", "telefone", "email", "observacoes"],
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
def criar_influenciadora(
	nome: str,
	instagram: str | None = None,
	nicho: str | None = None,
	seguidores_aprox=None,
	telefone: str | None = None,
	email: str | None = None,
	foto: str | None = None,
	observacoes: str | None = None,
) -> dict:
	if not (nome or "").strip():
		frappe.throw(_("Informe o nome da influenciadora."))
	doc = frappe.get_doc(
		{
			"doctype": "CRM Influenciadora",
			"nome": nome.strip(),
			"instagram": (instagram or "").strip(),
			"nicho": (nicho or "").strip(),
			"seguidores_aprox": seguidores_aprox or 0,
			"telefone": (telefone or "").strip(),
			"email": (email or "").strip(),
			"foto": foto or "",
			"observacoes": observacoes or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def atualizar_influenciadora(name: str, nome=None, instagram=None, nicho=None, seguidores_aprox=None, telefone=None, email=None, foto=None, observacoes=None) -> dict:
	doc = frappe.get_doc("CRM Influenciadora", name)
	for campo, valor in (
		("nome", nome), ("instagram", instagram), ("nicho", nicho), ("seguidores_aprox", seguidores_aprox),
		("telefone", telefone), ("email", email), ("foto", foto), ("observacoes", observacoes),
	):
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
		fields=[
			"name", "marca", "status", "valor", "valor_pago", "data_pagamento",
			"data_gravacao", "prazo_entrega", "briefing", "observacoes",
			"comissao_modelo", "comissao_pct", "comissao_valor_fixo", "comissao_calculada",
		],
		order_by="prazo_entrega asc, creation desc",
	)


@frappe.whitelist()
def criar_parceria(
	influenciadora: str,
	marca: str,
	status: str | None = None,
	valor=None,
	valor_pago=None,
	data_pagamento=None,
	data_gravacao=None,
	prazo_entrega=None,
	comissao_modelo: str | None = None,
	comissao_pct=None,
	comissao_valor_fixo=None,
	briefing: str | None = None,
	observacoes: str | None = None,
) -> dict:
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
			"valor_pago": valor_pago or 0,
			"data_pagamento": data_pagamento or None,
			"data_gravacao": data_gravacao or None,
			"prazo_entrega": prazo_entrega or None,
			"comissao_modelo": comissao_modelo or "",
			"comissao_pct": comissao_pct or 0,
			"comissao_valor_fixo": comissao_valor_fixo or 0,
			"briefing": briefing or "",
			"observacoes": observacoes or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def atualizar_parceria(
	name: str, marca=None, status=None, valor=None, valor_pago=None, data_pagamento=None,
	data_gravacao=None, prazo_entrega=None, comissao_modelo=None, comissao_pct=None,
	comissao_valor_fixo=None, briefing=None, observacoes=None,
) -> dict:
	doc = frappe.get_doc("CRM Parceria", name)
	for campo, valor_novo in (
		("marca", marca), ("status", status), ("valor", valor),
		("valor_pago", valor_pago), ("data_pagamento", data_pagamento),
		("data_gravacao", data_gravacao), ("prazo_entrega", prazo_entrega),
		("comissao_modelo", comissao_modelo), ("comissao_pct", comissao_pct), ("comissao_valor_fixo", comissao_valor_fixo),
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


@frappe.whitelist()
def listar_anexos_parceria(parceria: str) -> list:
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "CRM Parceria", "attached_to_name": parceria},
		fields=["name", "file_name", "file_url", "file_type", "file_size", "is_private", "creation"],
		order_by="creation desc",
	)


# ------------------------------------------------------------------ painel geral + prazos de entrega

def _parcerias_a_vencer(dias: int = PRAZO_AVISO_DIAS) -> dict:
	"""Parcerias com prazo de entrega já vencido ou perto de vencer (até N dias),
	que ainda não foram entregues nem canceladas."""
	hoje = getdate(nowdate())
	limite = add_days(hoje, dias)
	rows = frappe.get_all(
		"CRM Parceria",
		filters={"status": ["not in", STATUS_ENCERRADOS], "prazo_entrega": ["is", "set"]},
		fields=["name", "influenciadora", "marca", "status", "prazo_entrega", "valor"],
	)
	nomes = {
		i.name: i.nome
		for i in frappe.get_all("CRM Influenciadora", filters={"name": ["in", [r.influenciadora for r in rows]]}, fields=["name", "nome"])
	}
	atrasadas, proximas = [], []
	for r in rows:
		prazo = getdate(r.prazo_entrega)
		item = {
			"name": r.name,
			"influenciadora": nomes.get(r.influenciadora, r.influenciadora),
			"marca": r.marca,
			"status": r.status,
			"prazo_entrega": r.prazo_entrega,
			"valor": r.valor,
			"dias": (prazo - hoje).days,
		}
		if prazo < hoje:
			atrasadas.append(item)
		elif prazo <= limite:
			proximas.append(item)
	atrasadas.sort(key=lambda x: x["dias"])
	proximas.sort(key=lambda x: x["dias"])
	return {"atrasadas": atrasadas, "proximas": proximas}


@frappe.whitelist()
def get_painel_influenciadoras() -> dict:
	"""Resumo geral pra tela inicial de Influenciadoras: quantas tem, quanto já
	entrou, ranking de quem rendeu mais, e o que está pra vencer ou já venceu."""
	parcerias = frappe.get_all("CRM Parceria", fields=["name", "influenciadora", "status", "valor", "valor_pago", "comissao_calculada"])
	influenciadoras = frappe.get_all("CRM Influenciadora", fields=["name", "nome", "foto"])
	por_influenciadora = {}
	for p in parcerias:
		b = por_influenciadora.setdefault(
			p.influenciadora, {"total_negociado": 0, "total_recebido": 0, "parcerias": 0}
		)
		b["total_negociado"] += flt(p.valor)
		b["total_recebido"] += flt(p.valor_pago)
		b["parcerias"] += 1

	ranking = []
	for i in influenciadoras:
		b = por_influenciadora.get(i.name)
		if not b or not b["total_recebido"]:
			continue
		ranking.append({"name": i.name, "nome": i.nome, "foto": i.foto, **b})
	ranking.sort(key=lambda x: -x["total_recebido"])

	vencer = _parcerias_a_vencer()
	return {
		"total_influenciadoras": len(influenciadoras),
		"total_parcerias_ativas": len([p for p in parcerias if p.status not in STATUS_ENCERRADOS]),
		"receita_total": sum(flt(p.valor_pago) for p in parcerias),
		"comissao_total": sum(flt(p.comissao_calculada) for p in parcerias),
		"ranking": ranking[:5],
		"atrasadas": vencer["atrasadas"],
		"proximas": vencer["proximas"],
	}


def avisar_prazos_entrega():
	"""Job diário: se tiver parceria vencida ou perto de vencer, manda um resumo
	por e-mail pros gestores (mesmos destinatários do relatório semanal). Um
	e-mail só por dia com tudo junto, não um por parceria."""
	vencer = _parcerias_a_vencer()
	if not vencer["atrasadas"] and not vencer["proximas"]:
		return

	from crm.api.automacoes import _brand, _report_recipients, get_config

	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		return
	recipients = _report_recipients(get_config())
	if not recipients:
		return

	def linhas(items, cor):
		return "".join(
			f"<li style='margin-bottom:4px'><b>{frappe.utils.escape_html(i['influenciadora'])}</b> × "
			f"{frappe.utils.escape_html(i['marca'])} — {'atrasada há' if i['dias'] < 0 else 'vence em'} "
			f"{abs(i['dias'])} dia(s)</li>"
			for i in items
		)

	partes = []
	if vencer["atrasadas"]:
		partes.append(f"<p style='color:#c0392b'><b>Atrasadas:</b></p><ul>{linhas(vencer['atrasadas'], 'red')}</ul>")
	if vencer["proximas"]:
		partes.append(f"<p><b>Vencendo em breve:</b></p><ul>{linhas(vencer['proximas'], 'amber')}</ul>")

	brand = _brand() or "CRM"
	total = len(vencer["atrasadas"]) + len(vencer["proximas"])
	subject = f"{brand}: {total} parceria(s) de influenciadora com prazo próximo"
	body = f"<div style='font-family:Arial,sans-serif;max-width:560px'>{''.join(partes)}</div>"
	frappe.sendmail(recipients=recipients, subject=subject, message=body, delayed=False)
