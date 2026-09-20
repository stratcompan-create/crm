# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Automações do Instagram:
#  - boas-vindas: quem escreve pela primeira vez recebe uma resposta na hora;
#  - palavra-chave: quem comenta uma palavra (a chamada para ação do vídeo) recebe uma
#    mensagem no direct, e já vira lead no CRM.
# As duas usam só o que a API oficial permite (responder a quem escreveu ou comentou).

import re
import unicodedata

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from crm.api import instagram as ig

DEFAULT_WELCOME = (
	"Oi, {nome}! Obrigado pelo contato. Já recebi sua mensagem e em breve te respondo por aqui. "
	"Se puder, me conta em uma frase o que você procura."
)
DEFAULT_TRIGGER = "Oi, {nome}! Vi seu comentário e já te chamo por aqui. Em instantes te envio o que você pediu."
COMMENT_TTL = 7 * 24 * 3600


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _norm(text: str) -> str:
	text = unicodedata.normalize("NFKD", text or "")
	text = "".join(c for c in text if not unicodedata.combining(c))
	return re.sub(r"\s+", " ", text.casefold()).strip()


def _first_name(lead: str) -> str:
	name = frappe.db.get_value("CRM Lead", lead, "first_name") or ""
	return name.split(" ")[0] if name and not name.startswith("Instagram") else ""


def _fill(template: str, lead: str) -> str:
	nome = _first_name(lead)
	text = (template or "").replace("{nome}", nome)
	# sem nome conhecido: tira o espaço/vírgula que sobra ("Oi, !")
	return re.sub(r"\s+([,!.?])", r"\1", re.sub(r",\s*([!.?])", r"\1", text)).replace("  ", " ").strip()


def _log_message(lead: str, sender_id: str, direction: str, text: str, comment_id: str = ""):
	frappe.get_doc(
		{
			"doctype": "CRM Instagram Message",
			"lead": lead,
			"sender_id": sender_id,
			"direction": direction,
			"message": text,
			"comment_id": comment_id,
			"timestamp": now_datetime(),
		}
	).insert(ignore_permissions=True)


def _post_message(recipient: dict, text: str) -> bool:
	settings = ig._get_settings()
	token = settings.get_password("access_token", raise_exception=False)
	if not settings.enabled or not token:
		return False
	resp = requests.post(
		f"{ig.GRAPH_BASE}/me/messages",
		params={"access_token": token},
		json={"recipient": recipient, "message": {"text": text}},
		timeout=ig.TIMEOUT,
	)
	if not resp.ok:
		frappe.log_error("Instagram: mensagem automática recusada", resp.text[:1500])
	return resp.ok


# ------------------------------------------------------------------ boas-vindas

def maybe_send_welcome(lead: str, sender_id: str):
	"""Chamada logo depois de registrar uma mensagem recebida. Só responde na primeira conversa."""
	try:
		settings = ig._get_settings()
		if not cint(settings.get("boas_vindas_ativa")):
			return
		template = (settings.get("boas_vindas_mensagem") or "").strip() or DEFAULT_WELCOME
		# só quando é a primeira mensagem da conversa (a que acabou de chegar)
		if frappe.db.count("CRM Instagram Message", {"lead": lead}) != 1:
			return
		# quem foi abordado por nós já está numa conversa: não faz sentido dar boas-vindas
		if frappe.db.get_value("CRM Lead", lead, "abordado_em"):
			return
		text = _fill(template, lead)
		if text and _post_message({"id": sender_id}, text):
			_log_message(lead, sender_id, "Sent", text)
			frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Instagram: falha nas boas-vindas", frappe.get_traceback())


# ------------------------------------------------------------------ palavra-chave em comentário

def process_comment_change(value: dict):
	"""Evento 'comments' do webhook: comentário novo em um post ou vídeo."""
	comment_id = value.get("id")
	text = value.get("text") or ""
	author = value.get("from") or {}
	author_id, username = author.get("id"), author.get("username")
	if not comment_id or not author_id or not text:
		return
	if author_id == (ig._get_settings().instagram_business_account_id or ""):
		return

	if frappe.db.exists("CRM Instagram Message", {"comment_id": comment_id}):
		return

	cleaned = re.sub(r"[^\w\s]", " ", text)
	normalized = f" {_norm(cleaned)} "
	trigger = None
	for g in frappe.get_all("CRM Instagram Gatilho", filters={"ativa": 1}, fields=["palavra", "mensagem"]):
		word = _norm(g.palavra)
		if word and f" {word} " in normalized:
			trigger = g
			break
	if not trigger:
		return

	lead = ig._get_or_create_lead(author_id, fallback={"username": username or ""})
	# uma mensagem por pessoa e palavra a cada 24h, mesmo que ela comente de novo
	dm = _fill(trigger.mensagem, lead)
	if not dm:
		return
	if frappe.db.exists(
		"CRM Instagram Message",
		{"lead": lead, "direction": "Sent", "message": dm, "comment_id": ["!=", ""], "creation": [">", add_to_date(now_datetime(), hours=-24)]},
	):
		_log_message(lead, author_id, "Received", f"Comentou no post: {text}", comment_id)
		frappe.db.commit()
		return
	_log_message(lead, author_id, "Received", f"Comentou no post: {text}", comment_id)
	if _post_message({"comment_id": comment_id}, dm):
		_log_message(lead, author_id, "Sent", dm, comment_id)
	frappe.db.commit()


# ------------------------------------------------------------------ configuração (gestor)

@frappe.whitelist()
def get_automation_settings() -> dict:
	_managers_only()
	s = ig._get_settings()
	return {
		"boas_vindas_ativa": cint(s.get("boas_vindas_ativa")),
		"boas_vindas_mensagem": s.get("boas_vindas_mensagem") or DEFAULT_WELCOME,
		"gatilhos": frappe.get_all(
			"CRM Instagram Gatilho", fields=["palavra", "mensagem", "ativa"], order_by="creation asc"
		),
		"mensagem_exemplo": DEFAULT_TRIGGER,
	}


@frappe.whitelist()
def save_welcome(ativa=0, mensagem: str = ""):
	_managers_only()
	frappe.db.set_single_value("CRM Instagram Settings", "boas_vindas_ativa", cint(ativa))
	frappe.db.set_single_value("CRM Instagram Settings", "boas_vindas_mensagem", (mensagem or "").strip())
	return {"ok": True}


@frappe.whitelist()
def save_gatilho(palavra: str, mensagem: str, ativa=1):
	_managers_only()
	palavra = (palavra or "").strip()
	mensagem = (mensagem or "").strip()
	if not palavra or not mensagem:
		frappe.throw(_("Preencha a palavra-chave e a mensagem."))
	if frappe.db.exists("CRM Instagram Gatilho", palavra):
		frappe.db.set_value("CRM Instagram Gatilho", palavra, {"mensagem": mensagem, "ativa": cint(ativa)})
	else:
		frappe.get_doc(
			{"doctype": "CRM Instagram Gatilho", "palavra": palavra, "mensagem": mensagem, "ativa": cint(ativa)}
		).insert()
	return {"ok": True}


@frappe.whitelist()
def delete_gatilho(palavra: str):
	_managers_only()
	frappe.delete_doc("CRM Instagram Gatilho", palavra)
	return {"ok": True}
