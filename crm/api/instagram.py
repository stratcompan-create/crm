# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Instagram DM -> CRM Lead capture, and replying to that lead from the CRM.
#
# Built for the "Instagram API with Instagram Login" product (no Facebook Page
# required — the app connects straight to the Instagram professional account).
# Everything talks to graph.instagram.com, not graph.facebook.com (that's the
# older, Page-based product).
#
# Webhook URL to register in the Meta App (Instagram product -> Webhooks):
#   https://<your-site>/api/method/crm.api.instagram.webhook

import hashlib
import hmac
import json

import frappe
import requests
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, nowdate

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"
TIMEOUT = 20

# um token novo dura ~60 dias; renovamos com folga bem antes disso
REFRESH_WHEN_DAYS_LEFT = 20
# a Meta só deixa renovar um token com mais de 24h de vida
MIN_TOKEN_AGE_DAYS = 2


def _get_settings():
	return frappe.get_single("CRM Instagram Settings")


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


# ------------------------------------------------------------------ webhook

@frappe.whitelist(allow_guest=True)
def webhook():
	if frappe.request.method == "GET":
		return _handle_verification()
	return _handle_incoming_event()


def _handle_verification():
	settings = _get_settings()
	args = frappe.local.form_dict
	mode = args.get("hub.mode")
	token = args.get("hub.verify_token")
	challenge = args.get("hub.challenge")

	if mode == "subscribe" and token and settings.verify_token and token == settings.verify_token:
		frappe.response["type"] = "page"
		frappe.local.response_data = challenge
		return challenge

	frappe.local.response.http_status_code = 403
	return "Verification failed"


def _handle_incoming_event():
	settings = _get_settings()
	if not settings.enabled:
		return {"status": "ignored", "reason": "Instagram integration disabled"}

	raw_body = frappe.request.get_data()
	if settings.app_secret:
		if not _is_valid_signature(raw_body, frappe.get_request_header("X-Hub-Signature-256"), settings.get_password("app_secret")):
			frappe.local.response.http_status_code = 403
			return {"status": "error", "reason": "Invalid signature"}

	payload = json.loads(raw_body or "{}")

	for entry in payload.get("entry", []):
		for event in entry.get("messaging", []):
			_process_message_event(event)

	return {"status": "ok"}


def _is_valid_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
	if not signature_header or not signature_header.startswith("sha256="):
		return False
	expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
	return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def _process_message_event(event: dict):
	sender_id = event.get("sender", {}).get("id")
	message = event.get("message", {})
	text = message.get("text")

	# Ignore echoes of our own outgoing messages and non-text events (likes,
	# attachments-only, read receipts) for this first version.
	if not sender_id or not text or message.get("is_echo"):
		return

	lead_name = _get_or_create_lead(sender_id)

	frappe.get_doc(
		{
			"doctype": "CRM Instagram Message",
			"lead": lead_name,
			"sender_id": sender_id,
			"direction": "Received",
			"message": text,
			"timestamp": now_datetime(),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()


def _get_or_create_lead(sender_id: str) -> str:
	existing = frappe.db.get_value("CRM Lead", {"instagram_sender_id": sender_id})
	if existing:
		return existing

	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"lead_name": f"Instagram - {sender_id}",
			"instagram_sender_id": sender_id,
			"source": "Instagram",
		}
	)
	lead.insert(ignore_permissions=True)
	frappe.db.commit()
	return lead.name


# ------------------------------------------------------------------ enviar

@frappe.whitelist()
def send_reply(lead: str, message: str):
	"""Send a text reply to the Instagram user linked to this lead."""
	sender_id = frappe.db.get_value("CRM Lead", lead, "instagram_sender_id")
	if not sender_id:
		frappe.throw(_("This lead has no linked Instagram conversation"))

	settings = _get_settings()
	if not settings.enabled:
		frappe.throw(_("Instagram integration is disabled in CRM Instagram Settings"))

	token = settings.get_password("access_token", raise_exception=False)
	if not token:
		frappe.throw(_("Instagram integration is disabled in CRM Instagram Settings"))

	response = requests.post(
		f"{GRAPH_BASE}/me/messages",
		params={"access_token": token},
		json={"recipient": {"id": sender_id}, "message": {"text": message}},
		timeout=TIMEOUT,
	)

	if not response.ok:
		frappe.throw(_("Failed to send Instagram message: {0}").format(response.text))

	frappe.get_doc(
		{
			"doctype": "CRM Instagram Message",
			"lead": lead,
			"sender_id": sender_id,
			"direction": "Sent",
			"message": message,
			"timestamp": now_datetime(),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "sent"}


# ------------------------------------------------------------------ conexão / token

def fetch_profile(token: str) -> dict | None:
	"""Confirma que o token funciona e devolve {id, username} da conta conectada."""
	try:
		resp = requests.get(
			f"{GRAPH_BASE}/me",
			params={"fields": "id,username", "access_token": token},
			timeout=TIMEOUT,
		)
		if resp.ok:
			return resp.json()
		frappe.log_error("Instagram: token inválido", resp.text[:1500])
	except requests.RequestException:
		frappe.log_error("Instagram: falha ao validar token", frappe.get_traceback())
	return None


@frappe.whitelist()
def test_connection():
	"""Usado pelo botão "Testar conexão" nas Configurações do Instagram."""
	_managers_only()
	settings = _get_settings()
	token = settings.get_password("access_token", raise_exception=False)
	if not token:
		return {"ok": False, "message": _("Nenhum token cadastrado ainda.")}

	profile = fetch_profile(token)
	if not profile:
		return {"ok": False, "message": _("O Instagram recusou o token. Gere um novo token no painel da Meta e cole aqui.")}

	dias = None
	if settings.token_expires_on:
		dias = (getdate(settings.token_expires_on) - getdate(nowdate())).days

	return {
		"ok": True,
		"username": profile.get("username"),
		"account_id": profile.get("id"),
		"dias_para_expirar": dias,
	}


def _refresh_token(current_token: str) -> dict | None:
	try:
		resp = requests.get(
			"https://graph.instagram.com/refresh_access_token",
			params={"grant_type": "ig_refresh_token", "access_token": current_token},
			timeout=TIMEOUT,
		)
		if resp.ok:
			return resp.json()
		frappe.log_error("Instagram: falha ao renovar o token", resp.text[:1500])
	except requests.RequestException:
		frappe.log_error("Instagram: falha ao renovar o token", frappe.get_traceback())
	return None


def refresh_token_if_needed():
	"""Job diário: renova o token do Instagram antes que ele vença (dura ~60 dias)."""
	settings = _get_settings()
	if not settings.enabled:
		return
	token = settings.get_password("access_token", raise_exception=False)
	if not token:
		return

	# nunca tentamos renovar ainda: deixa o token amadurecer 2 dias (a Meta exige
	# ao menos 24h) antes da primeira tentativa
	if not settings.token_expires_on:
		frappe.db.set_value(
			"CRM Instagram Settings", None, "token_expires_on", add_days(nowdate(), 60 - MIN_TOKEN_AGE_DAYS)
		)
		return

	days_left = (getdate(settings.token_expires_on) - getdate(nowdate())).days
	if days_left > REFRESH_WHEN_DAYS_LEFT:
		return

	data = _refresh_token(token)
	if not data or not data.get("access_token"):
		return

	frappe.db.set_value("CRM Instagram Settings", None, "access_token", data["access_token"])
	frappe.db.set_value(
		"CRM Instagram Settings",
		None,
		"token_expires_on",
		add_days(nowdate(), max(1, cint(data.get("expires_in", 5184000)) // 86400)),
	)
	frappe.db.commit()
