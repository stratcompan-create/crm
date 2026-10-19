# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Relação com o cliente:
# - Portal do cliente: um link por caso (sem senha, com código longo) onde o cliente vê o andamento,
#   os documentos que faltam, os pagamentos em aberto e a próxima consulta.
# - Lembrete automático dos documentos que ainda não chegaram.
# - Pesquisa de satisfação no fim do caso.
# - Ranking de quem mais indica clientes.

import json
import secrets

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_url, getdate, now_datetime, nowdate

LEMBRETE_A_CADA = 3  # dias entre um lembrete e outro
LEMBRETES_MAX = 3


def _marca() -> dict:
	g = frappe.db.get_single_value
	return {
		"marca": g("FCRM Settings", "brand_name") or "",
		"logo": g("FCRM Settings", "brand_logo") or "",
		"cor": g("FCRM Settings", "brand_color") or "",
		"destaque": g("FCRM Settings", "brand_accent") or "",
	}


# ------------------------------------------------------------------ portal do cliente

@frappe.whitelist()
def link_portal(deal: str, novo=0) -> dict:
	"""Link do portal do caso. novo=1 troca o código (o link antigo para de funcionar)."""
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("write")
	token = doc.get("portal_token")
	if not token or cint(novo):
		token = secrets.token_urlsafe(24)
		frappe.db.set_value("CRM Deal", deal, "portal_token", token, update_modified=False)
	return {"link": get_url(f"/portal?t={token}")}


def _deal_por_token(t: str):
	if not t or len(t) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value("CRM Deal", {"portal_token": t})
	if not name:
		frappe.throw(_("Link inválido ou trocado. Peça um novo ao escritório."))
	return frappe.get_doc("CRM Deal", name)


@frappe.whitelist(allow_guest=True)
def get_portal(t: str = "") -> dict:
	frappe.local.no_cache = 1
	doc = _deal_por_token(t)
	from crm.api.automacoes import _client

	cli = _client(doc.name)
	andamentos = frappe.get_all("CRM Andamento", filters={"deal": doc.name, "visivel_cliente": 1},
								fields=["data", "texto"], order_by="data desc, creation desc", limit=5) if frappe.db.exists("DocType", "CRM Andamento") else []
	documentos = []
	for p in frappe.get_all("CRM Pedido Documentos", filters={"deal": doc.name, "ativo": 1}, fields=["token", "itens", "recebidos", "expira_em"]):
		if p.expira_em and getdate(p.expira_em) < getdate(nowdate()):
			continue
		recebidos = {r["item"] for r in json.loads(p.recebidos or "[]")}
		faltando = [i for i in json.loads(p.itens or "[]") if i not in recebidos]
		if faltando:
			documentos.append({"faltando": faltando, "link": f"/documentos?t={p.token}"})
	pagamentos = [
		{"valor": flt(h.valor), "vencimento": str(h.data_vencimento or ""), "atrasado": h.status == "Atrasado",
		 "link": h.link_pagamento if (h.link_pagamento or "").startswith("http") else "", "descricao": h.observacoes or ""}
		for h in frappe.get_all("CRM Honorario", filters={"deal": doc.name, "status": ["in", ["Pendente", "Atrasado"]]},
								fields=["valor", "data_vencimento", "status", "link_pagamento", "observacoes"], order_by="data_vencimento asc")
	]
	consulta = None
	if doc.get("lead"):
		r = frappe.get_all("CRM Reuniao", filters={"lead": doc.lead, "status": "Agendada", "inicio": [">=", now_datetime()]},
						   fields=["inicio"], order_by="inicio asc", limit=1)
		if r:
			consulta = r[0].inicio.strftime("%d/%m/%Y às %H:%M")
	pesquisa = None
	if cint(doc.get("encerrado")):
		ps = frappe.get_all("CRM Pesquisa", filters={"deal": doc.name, "respondida_em": ["is", "not set"]}, pluck="token", limit=1)
		if ps:
			pesquisa = f"/pesquisa?t={ps[0]}"
	return {
		**_marca(),
		"nome": cli.nome,
		"servico": doc.get("servico") or "",
		"numero_processo": doc.get("numero_processo") or "",
		"encerrado": cint(doc.get("encerrado")),
		"andamentos": [{"data": str(a.data), "texto": a.texto} for a in andamentos],
		"documentos": documentos,
		"pagamentos": pagamentos,
		"consulta": consulta,
		"pesquisa": pesquisa,
	}


# ------------------------------------------------------------------ lembrete de documentos

def lembrar_documentos():
	"""Diário: cobra os documentos que ainda não chegaram (a cada 3 dias, no máximo 3 vezes)."""
	from crm.api.automacoes import _notify_client

	hoje = getdate(nowdate())
	for p in frappe.get_all("CRM Pedido Documentos", filters={"ativo": 1},
							fields=["name", "deal", "token", "itens", "recebidos", "expira_em", "creation", "lembretes_enviados", "ultimo_lembrete"]):
		try:
			if p.expira_em and getdate(p.expira_em) < hoje:
				continue
			if cint(p.lembretes_enviados) >= LEMBRETES_MAX:
				continue
			ultimo = getdate(p.ultimo_lembrete) if p.ultimo_lembrete else getdate(p.creation)
			if (hoje - ultimo).days < LEMBRETE_A_CADA:
				continue
			recebidos = {r["item"] for r in json.loads(p.recebidos or "[]")}
			faltando = [i for i in json.loads(p.itens or "[]") if i not in recebidos]
			if not faltando:
				continue
			link = get_url(f"/documentos?t={p.token}")
			msg = (_("Olá! Ainda faltam estes documentos para darmos andamento ao seu caso:") + "\n"
				   + "\n".join(f"- {i}" for i in faltando) + "\n\n" + _("Envie pelo link (pode ser foto do celular): {0}").format(link))
			_notify_client(p.deal, _("Lembrete: documentos pendentes"), msg, _("Cobrar documentos pendentes do cliente"))
			frappe.db.set_value("CRM Pedido Documentos", p.name, {"lembretes_enviados": cint(p.lembretes_enviados) + 1,
																  "ultimo_lembrete": nowdate()}, update_modified=False)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error("Lembrete de documentos falhou", frappe.get_traceback())


# ------------------------------------------------------------------ pesquisa de satisfação

def criar_pesquisa(deal: str, avisar=True) -> str:
	existente = frappe.db.get_value("CRM Pesquisa", {"deal": deal, "respondida_em": ["is", "not set"]}, "token")
	if existente:
		return existente
	token = secrets.token_urlsafe(20)
	frappe.get_doc({"doctype": "CRM Pesquisa", "deal": deal, "token": token, "enviada_em": nowdate()}).insert(ignore_permissions=True)
	if avisar:
		try:
			from crm.api.automacoes import _notify_client

			link = get_url(f"/pesquisa?t={token}")
			_notify_client(deal, _("Como foi o nosso atendimento?"),
						   _("Olá! Seu caso foi concluído. Leva 30 segundos: como você avalia o nosso atendimento? {0}").format(link),
						   _("Enviar a pesquisa de satisfação ao cliente: {0}").format(link))
		except Exception:
			frappe.log_error("Pesquisa de satisfação: aviso ao cliente falhou", frappe.get_traceback())
	return token


@frappe.whitelist(allow_guest=True)
def get_pesquisa(t: str = "") -> dict:
	frappe.local.no_cache = 1
	p = _pesquisa(t)
	from crm.api.automacoes import _client

	return {**_marca(), "nome": _client(p.deal).nome, "respondida": bool(p.respondida_em)}


def _pesquisa(t: str):
	if not t or len(t) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value("CRM Pesquisa", {"token": t})
	if not name:
		frappe.throw(_("Link inválido."))
	return frappe.get_doc("CRM Pesquisa", name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def responder_pesquisa(t: str = "", nota=None, comentario: str = "", indicaria=0) -> dict:
	p = _pesquisa(t)
	if p.respondida_em:
		frappe.throw(_("Esta pesquisa já foi respondida. Obrigado!"))
	n = cint(nota)
	if nota in (None, "") or n < 0 or n > 10:
		frappe.throw(_("Escolha uma nota de 0 a 10."))
	frappe.db.set_value("CRM Pesquisa", p.name, {"nota": n, "comentario": (comentario or "").strip()[:1000],
												 "indicaria": cint(indicaria), "respondida_em": now_datetime()})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal", "reference_name": p.deal,
					"content": _("Pesquisa de satisfação respondida: nota {0}/10.").format(n) + (f" “{comentario.strip()[:300]}”" if comentario else "")}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def resumo_pesquisas(dias: int = 365) -> dict:
	"""Satisfação dos clientes (NPS): promotores (9-10) menos detratores (0-6)."""
	notas = frappe.get_all("CRM Pesquisa", filters={"respondida_em": [">=", add_days(nowdate(), -cint(dias))]}, pluck="nota")
	if not notas:
		return {"respostas": 0}
	prom = sum(1 for n in notas if n >= 9)
	detr = sum(1 for n in notas if n <= 6)
	return {"respostas": len(notas), "media": round(sum(notas) / len(notas), 1), "nps": round((prom - detr) * 100 / len(notas)),
			"enviadas": frappe.db.count("CRM Pesquisa", {"enviada_em": [">=", add_days(nowdate(), -cint(dias))]})}


# ------------------------------------------------------------------ indicações

@frappe.whitelist()
def ranking_indicacoes(dias: int = 365) -> list[dict]:
	"""Quem mais indica: atendimentos e casos trazidos e quanto isso já rendeu em honorários pagos."""
	desde = add_days(nowdate(), -cint(dias))
	from crm.api.importacao import _norm

	ranking = {}

	def item(nome):
		chave = _norm(nome)
		if chave not in ranking:
			ranking[chave] = {"nome": nome.strip(), "atendimentos": 0, "casos": 0, "fechados": 0, "honorarios": 0.0}
		return ranking[chave]

	for l in frappe.get_all("CRM Lead", filters={"indicado_por": ["is", "set"], "creation": [">=", desde], "converted": 0}, pluck="indicado_por"):
		item(l)["atendimentos"] += 1
	won = set(frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name"))
	for d in frappe.get_all("CRM Deal", filters={"indicado_por": ["is", "set"], "creation": [">=", desde]}, fields=["name", "indicado_por", "status"]):
		r = item(d.indicado_por)
		r["casos"] += 1
		if d.status in won:
			r["fechados"] += 1
			r["honorarios"] += flt(frappe.db.sql("select coalesce(sum(valor),0) from `tabCRM Honorario` where deal=%s and status='Pago'", d.name)[0][0])
	out = sorted(ranking.values(), key=lambda x: (x["honorarios"], x["fechados"], x["casos"] + x["atendimentos"]), reverse=True)
	for r in out:
		r["honorarios"] = round(r["honorarios"], 2)
	return out[:20]
