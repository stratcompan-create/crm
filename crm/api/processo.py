# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Aba "Processo" do caso: nº do processo (CNJ), partes envolvidas, checagem de conflito de
# interesses, andamentos em linguagem simples para o cliente e encerramento do caso.
# O CRM NÃO controla prazos processuais: isso continua no software jurídico do escritório.
# O andamento aqui é só o que o cliente precisa saber.

import base64
import re
import unicodedata

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

TIPOS_PARTE = ["Parte contrária", "Testemunha", "Outro envolvido", "Cliente adicional"]
MOTIVOS = ["Êxito", "Acordo", "Improcedente", "Desistência do cliente", "Substabelecido", "Outro"]


def _norm(texto) -> str:
	t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
	t = re.sub(r"[^a-z0-9 ]+", " ", t)
	t = re.sub(r"\b(ltda|me|epp|eireli|s a|sa|cia|do|da|de|dos|das|e)\b", " ", t)
	return re.sub(r"\s+", " ", t).strip()


def _digitos(texto) -> str:
	return re.sub(r"\D", "", str(texto or ""))


def _doc(deal: str, ptype: str = "read"):
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission(ptype)
	return d


# ------------------------------------------------------------------ nº do processo (CNJ)

def validar_cnj(numero: str) -> tuple[bool, str]:
	"""Confere o dígito verificador do número único (Resolução CNJ 65/2008)."""
	dig = _digitos(numero)
	if not dig:
		return True, ""
	if len(dig) != 20:
		return False, _("O número CNJ tem 20 dígitos (NNNNNNN-DD.AAAA.J.TR.OOOO).")
	n, dv, ano, j, tr, orig = dig[:7], dig[7:9], dig[9:13], dig[13], dig[14:16], dig[16:]
	calc = 98 - (int(n + ano + j + tr + orig + "00") % 97)
	if int(dv) != calc:
		return False, _("O dígito verificador do número não confere. Confira se foi digitado certo.")
	return True, ""


def formatar_cnj(numero: str) -> str:
	dig = _digitos(numero)
	if len(dig) != 20:
		return (numero or "").strip()
	return f"{dig[:7]}-{dig[7:9]}.{dig[9:13]}.{dig[13]}.{dig[14:16]}.{dig[16:]}"


# ------------------------------------------------------------------ conflito de interesses

def _clientes() -> list[dict]:
	"""Quem é ou foi cliente (casos) e quem já procurou o escritório (atendimentos)."""
	from crm.api.modelos_documentos import _client_data

	out = []
	for d in frappe.get_all("CRM Deal", fields=["name", "lead_name", "first_name", "last_name", "organization", "dados_cliente"], limit=20000):
		nomes = {x for x in (d.lead_name, f"{d.first_name or ''} {d.last_name or ''}".strip(), d.organization) if x}
		doc = _digitos(_client_data(d).get("cpf_cnpj", "")) if d.dados_cliente else ""
		for n in nomes:
			out.append({"tipo": "cliente", "deal": d.name, "nome": n, "doc": doc})
	for l in frappe.get_all("CRM Lead", fields=["name", "lead_name", "first_name", "last_name"], filters={"converted": 0}, limit=20000):
		nome = l.lead_name or f"{l.first_name or ''} {l.last_name or ''}".strip()
		if nome:
			out.append({"tipo": "atendimento", "lead": l.name, "nome": nome, "doc": ""})
	return out


@frappe.whitelist()
def verificar_conflito(nome: str, documento: str | None = None, papel: str = "Parte contrária", deal: str | None = None) -> list[dict]:
	"""papel = 'Parte contrária': procura a pessoa entre clientes e atendimentos do escritório.
	papel = 'Cliente': procura a pessoa entre as partes contrárias de outros casos."""
	alvo, doc = _norm(nome), _digitos(documento)
	if not alvo and not doc:
		return []
	achados = []
	if papel == "Cliente":
		for p in frappe.get_all("CRM Parte", filters={"tipo": "Parte contrária"}, fields=["name", "deal", "nome", "documento"]):
			if deal and p.deal == deal:
				continue
			if (alvo and _norm(p.nome) == alvo) or (doc and _digitos(p.documento) == doc):
				achados.append({"motivo": _("é parte contrária no caso {0}").format(_rotulo_caso(p.deal)), "deal": p.deal})
	else:
		vistos = set()
		for c in _clientes():
			if c.get("deal") == deal:
				continue
			if (alvo and _norm(c["nome"]) == alvo) or (doc and c["doc"] and c["doc"] == doc):
				chave = c.get("deal") or c.get("lead")
				if chave in vistos:
					continue
				vistos.add(chave)
				if c["tipo"] == "cliente":
					achados.append({"motivo": _("é ou foi cliente do escritório ({0})").format(_rotulo_caso(c["deal"])), "deal": c["deal"]})
				else:
					achados.append({"motivo": _("já procurou o escritório como atendimento"), "lead": c["lead"]})
	return achados


def _rotulo_caso(deal: str) -> str:
	v = frappe.db.get_value("CRM Deal", deal, ["lead_name", "organization", "first_name", "last_name"], as_dict=True) or {}
	nome = v.get("lead_name") or v.get("organization") or f"{v.get('first_name') or ''} {v.get('last_name') or ''}".strip()
	return f"{nome} · {deal}" if nome else deal


def checar_cliente_novo(doc, method=None):
	"""Ao criar um caso, avisa (com uma tarefa) se o cliente já aparece como parte contrária em outro."""
	from crm.provision import PERFIS_JURIDICOS, get_profile

	if get_profile() not in PERFIS_JURIDICOS:
		return
	try:
		nome = doc.get("lead_name") or doc.get("organization") or f"{doc.get('first_name') or ''} {doc.get('last_name') or ''}".strip()
		achados = verificar_conflito(nome, None, "Cliente", doc.name)
		if not achados:
			return
		motivos = "; ".join(a["motivo"] for a in achados[:5])
		frappe.get_doc({
			"doctype": "CRM Task",
			"title": _("Atenção: possível conflito de interesses — {0}").format(nome),
			"description": _("Este cliente {0}. Confira antes de aceitar o caso.").format(motivos),
			"status": "Todo", "priority": "High", "assigned_to": doc.get("deal_owner"),
			"due_date": nowdate(), "reference_doctype": "CRM Deal", "reference_docname": doc.name,
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error("Processo: falha ao checar conflito do cliente novo", frappe.get_traceback())


# ------------------------------------------------------------------ leitura

def _pendencias(deal: str) -> list[str]:
	pend = []
	abertos = frappe.get_all("CRM Honorario", filters={"deal": deal, "status": ["in", ["Pendente", "Atrasado"]]}, pluck="valor")
	if abertos:
		pend.append(_("{0} honorário(s) em aberto (R$ {1})").format(len(abertos), f"{sum(flt(v) for v in abertos):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")))
	if frappe.db.exists("DocType", "CRM Recebimento"):
		repasses = frappe.db.count("CRM Recebimento", {"deal": deal, "repasse_status": "A repassar"})
		if repasses:
			pend.append(_("{0} repasse(s) ao cliente ainda não feito(s)").format(repasses))
	tarefas = frappe.db.count("CRM Task", {"reference_doctype": "CRM Deal", "reference_docname": deal, "status": ["in", ["Backlog", "Todo", "In Progress"]]})
	if tarefas:
		pend.append(_("{0} tarefa(s) em aberto").format(tarefas))
	return pend


@frappe.whitelist()
def dados(deal: str) -> dict:
	d = _doc(deal)
	partes = frappe.get_all("CRM Parte", filters={"deal": deal}, fields=["name", "tipo", "nome", "documento", "observacoes"], order_by="creation asc")
	for p in partes:
		p["conflitos"] = verificar_conflito(p.nome, p.documento, "Parte contrária", deal) if p.tipo == "Parte contrária" else []
	andamentos = frappe.get_all("CRM Andamento", filters={"deal": deal}, fields=["name", "data", "texto", "visivel_cliente"], order_by="data desc, creation desc")
	ok, aviso = validar_cnj(d.get("numero_processo"))
	return {
		"numero_processo": d.get("numero_processo") or "",
		"numero_valido": ok,
		"aviso_numero": aviso,
		"tribunal": d.get("tribunal") or "",
		"partes": partes,
		"tipos_parte": TIPOS_PARTE,
		"andamentos": [{**a, "data": str(a.data)} for a in andamentos],
		"encerrado": cint(d.get("encerrado")),
		"encerrado_em": str(d.get("encerrado_em") or ""),
		"motivo_encerramento": d.get("motivo_encerramento") or "",
		"documentos_devolvidos": cint(d.get("documentos_devolvidos")),
		"observacoes_encerramento": d.get("observacoes_encerramento") or "",
		"motivos": MOTIVOS,
		"pendencias": _pendencias(deal),
		"tem_portal": bool(d.get("portal_token")),
		"pesquisa": (frappe.get_all("CRM Pesquisa", filters={"deal": deal}, fields=["nota", "comentario", "respondida_em", "indicaria"],
									order_by="creation desc", limit=1) or [None])[0] if frappe.db.exists("DocType", "CRM Pesquisa") else None,
	}


@frappe.whitelist()
def status_para_cliente(deal: str) -> dict:
	"""O que o cliente vê: último andamento marcado como visível (usado pelo portal e pela assistente)."""
	_doc(deal)
	a = frappe.get_all("CRM Andamento", filters={"deal": deal, "visivel_cliente": 1}, fields=["data", "texto"], order_by="data desc, creation desc", limit=1)
	if not a:
		return {"tem": False, "texto": _("Ainda não há atualização registrada. O escritório vai avisar assim que houver novidade.")}
	return {"tem": True, "data": str(a[0].data), "texto": a[0].texto}


# ------------------------------------------------------------------ gravação

@frappe.whitelist()
def salvar_processo(deal: str, numero_processo: str = "", tribunal: str = "") -> dict:
	_doc(deal, "write")
	ok, aviso = validar_cnj(numero_processo)
	frappe.db.set_value("CRM Deal", deal, {"numero_processo": formatar_cnj(numero_processo) or None, "tribunal": (tribunal or "").strip()[:140] or None})
	return {"ok": True, "numero_valido": ok, "aviso": aviso, "numero_processo": formatar_cnj(numero_processo)}


@frappe.whitelist()
def adicionar_parte(deal: str, nome: str, tipo: str = "Parte contrária", documento: str = "", observacoes: str = "") -> dict:
	_doc(deal, "write")
	if not (nome or "").strip():
		frappe.throw(_("Informe o nome."))
	if tipo not in TIPOS_PARTE:
		tipo = "Outro envolvido"
	p = frappe.get_doc({"doctype": "CRM Parte", "deal": deal, "tipo": tipo, "nome": nome.strip()[:140],
						"documento": (documento or "").strip()[:30] or None, "observacoes": (observacoes or "").strip()[:500] or None}).insert()
	conflitos = verificar_conflito(p.nome, p.documento, "Parte contrária", deal) if tipo == "Parte contrária" else []
	if conflitos:
		frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal", "reference_name": deal,
						"content": _("Possível conflito de interesses: a parte contrária {0} {1}.").format(p.nome, "; ".join(c["motivo"] for c in conflitos))}).insert(ignore_permissions=True)
	return {"name": p.name, "conflitos": conflitos}


@frappe.whitelist()
def remover_parte(parte: str) -> dict:
	deal = frappe.db.get_value("CRM Parte", parte, "deal")
	_doc(deal, "write")
	frappe.delete_doc("CRM Parte", parte)
	return {"ok": True}


@frappe.whitelist()
def adicionar_andamento(deal: str, texto: str, visivel_cliente=1, data: str | None = None) -> dict:
	_doc(deal, "write")
	if not (texto or "").strip():
		frappe.throw(_("Escreva o andamento."))
	a = frappe.get_doc({"doctype": "CRM Andamento", "deal": deal, "texto": texto.strip()[:2000],
						"visivel_cliente": cint(visivel_cliente), "data": data or nowdate()}).insert()
	return {"name": a.name}


@frappe.whitelist()
def remover_andamento(andamento: str) -> dict:
	deal = frappe.db.get_value("CRM Andamento", andamento, "deal")
	_doc(deal, "write")
	frappe.delete_doc("CRM Andamento", andamento)
	return {"ok": True}


@frappe.whitelist()
def encerrar(deal: str, motivo: str, documentos_devolvidos=0, observacoes: str = "", mesmo_com_pendencias=0) -> dict:
	_doc(deal, "write")
	if motivo not in MOTIVOS:
		frappe.throw(_("Escolha como o caso terminou."))
	pend = _pendencias(deal)
	if pend and not cint(mesmo_com_pendencias):
		return {"ok": False, "pendencias": pend}
	frappe.db.set_value("CRM Deal", deal, {
		"encerrado": 1, "encerrado_em": nowdate(), "motivo_encerramento": motivo,
		"documentos_devolvidos": cint(documentos_devolvidos), "observacoes_encerramento": (observacoes or "").strip()[:1000] or None,
	})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal", "reference_name": deal,
					"content": _("Caso encerrado ({0}).").format(motivo) + (" " + _("Encerrado com pendências: {0}.").format("; ".join(pend)) if pend else "")}).insert(ignore_permissions=True)
	if frappe.db.exists("DocType", "CRM Pesquisa"):
		from crm.api.portal import criar_pesquisa

		criar_pesquisa(deal)
	return {"ok": True, "pendencias": pend}


@frappe.whitelist()
def reabrir(deal: str) -> dict:
	_doc(deal, "write")
	frappe.db.set_value("CRM Deal", deal, {"encerrado": 0, "encerrado_em": None, "motivo_encerramento": None})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal", "reference_name": deal,
					"content": _("Caso reaberto.")}).insert(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def termo_encerramento_pdf(deal: str) -> dict:
	d = _doc(deal)
	from crm.api.automacoes import _client
	from crm.api.modelos_documentos import _build, _client_data, _date_long

	cliente = _client(deal).completo or deal
	dados_cli = _client_data(d)
	escritorio = frappe.db.get_single_value("FCRM Settings", "brand_name") or ""
	linhas = [
		"# TERMO DE ENCERRAMENTO",
		"",
		f"**Cliente:** {cliente}" + (f", CPF/CNPJ {dados_cli['cpf_cnpj']}" if dados_cli.get("cpf_cnpj") else ""),
		"",
		f"**Serviço:** {d.get('servico') or '—'}" + (f" — processo nº {d.numero_processo}" if d.get("numero_processo") else ""),
		"",
		f"Declaramos encerrada a prestação de serviços advocatícios referente ao serviço acima"
		+ (f" ({(d.get('motivo_encerramento') or '').lower()})" if d.get("motivo_encerramento") else "") + ".",
		"",
	]
	if cint(d.get("documentos_devolvidos")):
		linhas += ["Os documentos originais entregues pelo cliente foram devolvidos nesta data.", ""]
	if d.get("observacoes_encerramento"):
		linhas += [d.observacoes_encerramento, ""]
	linhas += [f"{d.get('cidade_estado') or ''}{', ' if d.get('cidade_estado') else ''}{_date_long()}.", "", "",
			   "______________________________", cliente, "", "", "______________________________", escritorio]
	pdf = _build("\n".join(linhas), {}, "Outro", "Termo de encerramento", "", False)
	return {"pdf": base64.b64encode(pdf).decode(), "nome": f"Termo de encerramento - {cliente}.pdf"}
