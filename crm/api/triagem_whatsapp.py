# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Triagem no WhatsApp (API oficial da Meta, app `whatsapp` instalado).
# Quem escreve pela primeira vez vira Atendimento e recebe perguntas FIXAS, escritas pelo
# escritório (nome, o que aconteceu, prazo, cidade). O robô nunca responde dúvida jurídica:
# a IA só lê as respostas por dentro e organiza área, urgência e resumo para o advogado.
# Quando alguém da equipe responde à mão, o robô para naquela conversa.
# Fica pronto para ligar: basta a conta do WhatsApp Business estar configurada (Meta).

import json
import re

import frappe
import requests
from frappe import _
from frappe.utils import add_days, cint, now_datetime, nowdate

ORIGEM = "WhatsApp"
EXPIRA_HORAS = 48  # conversa parada há mais tempo que isso recomeça do zero

BOAS_VINDAS = (
	"Olá! Aqui é o atendimento do escritório. Vou fazer algumas perguntas rápidas para "
	"organizar o seu contato e um advogado vai retornar. Por aqui não damos orientação jurídica."
)
PERGUNTAS = (
	"Qual é o seu nome completo?\n"
	"Em poucas palavras, o que aconteceu e em que podemos ajudar?\n"
	"Existe algum prazo ou data marcada (audiência, notificação, intimação)? Se sim, qual?\n"
	"Em qual cidade você está?"
)
ENCERRAMENTO = (
	"Obrigado! Suas informações foram registradas e um advogado do escritório vai entrar em "
	"contato. Se for urgente, escreva URGENTE aqui."
)

# sinais de urgência que dispensam a IA (o advogado é avisado na hora)
URGENTE = re.compile(
	r"\b(urgente|pres[oa]|pris[aã]o|flagrante|audi[eê]ncia (hoje|amanh[aã])|liminar|despejo|"
	r"intima[cç][aã]o|prazo (vence|acaba) (hoje|amanh[aã]))\b",
	re.I,
)


def _cfg():
	from crm.api.automacoes import get_config

	return get_config()


def _perguntas(cfg) -> list[str]:
	return [p.strip() for p in (cfg.get("triagem_perguntas") or PERGUNTAS).splitlines() if p.strip()]


def _responsavel(cfg) -> str:
	user = cfg.get("triagem_responsavel") or cfg.get("agenda_responsavel")
	if user:
		return user
	gestores = frappe.get_all(
		"Has Role", filters={"role": "Sales Manager", "parenttype": "User", "parent": ["not in", ["Administrator", "Guest"]]},
		pluck="parent", limit=1,
	)
	return gestores[0] if gestores else "Administrator"


def _enviar(telefone: str, lead: str, texto: str):
	"""Manda pela API oficial, marcado como mensagem do robô (não conta como 'equipe assumiu')."""
	from whatsapp.whatsapp.api.messages import send_message

	frappe.flags.triagem_enviando = True
	try:
		send_message(to=telefone, message=texto, reference_doctype="CRM Lead", reference_docname=lead)
	finally:
		frappe.flags.triagem_enviando = False


def _novo_atendimento(telefone: str, nome: str, cfg) -> str:
	if not frappe.db.exists("CRM Lead Source", ORIGEM):
		frappe.get_doc({"doctype": "CRM Lead Source", "source_name": ORIGEM}).insert(ignore_permissions=True)
	first, _sep, last = (nome or "WhatsApp " + telefone[-4:]).partition(" ")
	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first,
			"last_name": last,
			"mobile_no": telefone,
			"source": ORIGEM,
			"lead_owner": _responsavel(cfg),
		}
	)
	lead.insert(ignore_permissions=True)
	return lead.name


def _triagem_aberta(telefone: str):
	nome = frappe.db.get_value(
		"CRM Triagem", {"telefone": telefone, "status": "Em andamento"}, "name", order_by="creation desc"
	)
	if not nome:
		return None
	t = frappe.get_doc("CRM Triagem", nome)
	if (now_datetime() - t.modified).total_seconds() > EXPIRA_HORAS * 3600:
		t.db_set("status", "Expirada")
		return None
	return t


# ------------------------------------------------------------------ ganchos do WhatsApp Message

def ao_receber(doc, method=None):
	"""after_insert de WhatsApp Message: entrada → triagem; saída manual → equipe assumiu."""
	if doc.direction == "Outgoing":
		if not frappe.flags.triagem_enviando and doc.reference_doctype == "CRM Lead" and doc.reference_docname:
			for nome in frappe.get_all("CRM Triagem", {"lead": doc.reference_docname, "status": "Em andamento"}, pluck="name"):
				frappe.db.set_value("CRM Triagem", nome, "status", "Assumida pela equipe")
		return
	from crm.provision import PERFIS_JURIDICOS, get_profile

	if get_profile() not in PERFIS_JURIDICOS or not cint(_cfg().get("triagem_ativa")):
		return
	frappe.enqueue(
		"crm.api.triagem_whatsapp.processar", queue="short", mensagem=doc.name, enqueue_after_commit=True
	)


def _nome_do_perfil(telefone: str) -> str:
	return frappe.db.get_value("WhatsApp Profile", {"phone_number": telefone}, "profile_name") or ""


def processar(mensagem: str):
	frappe.set_user("Administrator")
	try:
		_processar(frappe.get_doc("WhatsApp Message", mensagem))
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Triagem WhatsApp: falha", frappe.get_traceback())


def _processar(msg):
	cfg = _cfg()
	telefone = msg.get("from")
	texto = (msg.message or "").strip()
	if not telefone:
		return
	t = _triagem_aberta(telefone)
	if not t:
		# já é contato conhecido (cliente, caso ou atendimento em curso): quem atende é a equipe
		if msg.reference_doctype and msg.reference_docname:
			return
		lead = _novo_atendimento(telefone, _nome_do_perfil(telefone), cfg)
		msg.db_set({"reference_doctype": "CRM Lead", "reference_docname": lead}, update_modified=False)
		t = frappe.get_doc(
			{"doctype": "CRM Triagem", "lead": lead, "telefone": telefone, "etapa": 0, "status": "Em andamento",
			 "respostas": json.dumps([{"pergunta": "Primeira mensagem", "resposta": texto}], ensure_ascii=False)}
		).insert(ignore_permissions=True)
		if URGENTE.search(texto):
			_avisar_urgente(t, texto, cfg)
		perguntas = _perguntas(cfg)
		_enviar(telefone, lead, (cfg.get("triagem_boas_vindas") or BOAS_VINDAS) + "\n\n" + perguntas[0])
		return

	perguntas = _perguntas(cfg)
	respostas = json.loads(t.respostas or "[]")
	etapa = cint(t.etapa)
	respostas.append({"pergunta": perguntas[etapa] if etapa < len(perguntas) else "", "resposta": texto})
	t.respostas = json.dumps(respostas, ensure_ascii=False)
	if etapa == 0 and texto and len(texto) <= 80 and not any(c.isdigit() for c in texto):
		# primeira pergunta é o nome: corrige o atendimento com o nome que a pessoa informou
		first, _sep, last = texto.partition(" ")
		frappe.db.set_value("CRM Lead", t.lead, {"first_name": first[:140], "last_name": last[:140]})
	if URGENTE.search(texto) and t.urgencia != "Alta":
		_avisar_urgente(t, texto, cfg)
	etapa += 1
	t.etapa = etapa
	if etapa < len(perguntas):
		t.save(ignore_permissions=True)
		_enviar(telefone, t.lead, perguntas[etapa])
		return
	t.status = "Concluída"
	t.concluida_em = now_datetime()
	t.save(ignore_permissions=True)
	_enviar(telefone, t.lead, cfg.get("triagem_encerramento") or ENCERRAMENTO)
	_concluir(t, cfg)


def _avisar_urgente(t, texto: str, cfg):
	t.urgencia = "Alta"
	t.save(ignore_permissions=True)
	_tarefa(t, cfg, _("URGENTE: retornar atendimento pelo WhatsApp"), _("Mensagem recebida: {0}").format(texto[:500]), "High", 0)


def _tarefa(t, cfg, titulo: str, descricao: str, prioridade: str, dias: int):
	frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": titulo,
			"description": frappe.utils.escape_html(descricao).replace("\n", "<br>"),
			"status": "Todo",
			"priority": prioridade,
			"assigned_to": frappe.db.get_value("CRM Lead", t.lead, "lead_owner") or _responsavel(cfg),
			"due_date": add_days(nowdate(), dias),
			"reference_doctype": "CRM Lead",
			"reference_docname": t.lead,
		}
	).insert(ignore_permissions=True)


def _texto_respostas(t) -> str:
	return "\n\n".join(f"{r['pergunta']}\n→ {r['resposta']}" for r in json.loads(t.respostas or "[]"))


def _concluir(t, cfg):
	classe = _classificar(t)
	t.area = classe.get("area") or ""
	if t.urgencia != "Alta":
		t.urgencia = classe.get("urgencia") or ""
	t.resumo = classe.get("resumo") or ""
	t.save(ignore_permissions=True)
	partes = [_("Triagem pelo WhatsApp concluída.")]
	if t.area:
		partes.append(_("Área provável: {0}").format(t.area))
	if t.urgencia:
		partes.append(_("Urgência: {0}").format(t.urgencia))
	if t.resumo:
		partes.append(_("Resumo: {0}").format(t.resumo))
	cabeca = "\n".join(partes)
	frappe.get_doc(
		{
			"doctype": "FCRM Note",
			"title": _("Triagem pelo WhatsApp"),
			"content": frappe.utils.escape_html(cabeca + "\n\n" + _texto_respostas(t)).replace("\n", "<br>"),
			"reference_doctype": "CRM Lead",
			"reference_docname": t.lead,
		}
	).insert(ignore_permissions=True)
	if t.urgencia != "Alta":
		prioridade = "Medium" if t.urgencia == "Média" else "Low"
		_tarefa(t, cfg, _("Retornar atendimento do WhatsApp"), cabeca, prioridade, 1)


# ------------------------------------------------------------------ IA (só por dentro, nunca fala com o cliente)

def _classificar(t) -> dict:
	from crm.api import credito_ia
	from crm.api.ficha import API_URL, MODEL, _api_key

	key = _api_key()
	if not key or not credito_ia.saldo_suficiente():
		return {}
	areas = frappe.get_all("CRM Modelo Area", pluck="area") or []
	sistema = (
		"Você organiza a triagem de um escritório de advocacia. Leia as respostas do cliente e devolva "
		"SOMENTE um JSON com: \"area\" (uma destas, ou \"Outra\": " + ", ".join(areas) + "), "
		"\"urgencia\" (\"Alta\", \"Média\" ou \"Baixa\": Alta se houver prisão, audiência ou prazo em até 5 dias), "
		"\"resumo\" (até 3 frases objetivas, sem opinar sobre o mérito nem sobre chances de êxito). "
		"Não invente fatos que não estejam nas respostas."
	)
	try:
		resp = requests.post(
			API_URL,
			headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
			json={"model": MODEL, "max_tokens": 600, "system": sistema,
				  "messages": [{"role": "user", "content": f"<respostas>\n{_texto_respostas(t)[:6000]}\n</respostas>"}]},
			timeout=60,
		)
		if not resp.ok:
			frappe.log_error("Triagem WhatsApp: IA com erro", resp.text[:1500])
			return {}
		data = resp.json()
		credito_ia.registrar_uso(data.get("usage"))
		texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
		m = re.search(r"\{.*\}", texto, re.S)
		out = json.loads(m.group(0)) if m else {}
	except (requests.RequestException, ValueError):
		frappe.log_error("Triagem WhatsApp: falha na IA", frappe.get_traceback())
		return {}
	urg = out.get("urgencia") if out.get("urgencia") in ("Alta", "Média", "Baixa") else ""
	return {"area": str(out.get("area") or "")[:140], "urgencia": urg, "resumo": str(out.get("resumo") or "")[:1000]}


# ------------------------------------------------------------------ tela de Configurações

@frappe.whitelist()
def estado() -> dict:
	frappe.only_for(("System Manager", "Sales Manager"))
	conectado = "whatsapp" in frappe.get_installed_apps() and bool(
		frappe.db.count("WhatsApp Account", {"status": ["!=", "Inactive"]})
	)
	cfg = _cfg()
	return {
		"conectado": conectado,
		"padrao": {"boas_vindas": BOAS_VINDAS, "perguntas": PERGUNTAS, "encerramento": ENCERRAMENTO},
		"ultimas": frappe.get_all(
			"CRM Triagem", fields=["name", "lead", "status", "area", "urgencia", "creation"],
			order_by="creation desc", limit=10,
		),
		"ativa": cint(cfg.get("triagem_ativa")),
	}
