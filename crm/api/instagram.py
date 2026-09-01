# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Instagram DM -> CRM Lead capture, and replying to that lead from the CRM.
#
# Webhook URL to register in the Meta App (Instagram product -> Webhooks):
#   https://<your-site>/api/method/crm.api.instagram.webhook
#
# Meta calls this URL with GET once, to verify ownership (hub.challenge
# handshake), then with POST for every incoming event afterwards.

import hashlib
import hmac
import json

import frappe
import requests

GRAPH_API_VERSION = "v21.0"


def _get_settings():
	return frappe.get_single("CRM Instagram Settings")


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
			"timestamp": frappe.utils.now_datetime(),
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


@frappe.whitelist()
def send_reply(lead: str, message: str):
	"""Send a text reply to the Instagram user linked to this lead."""
	sender_id = frappe.db.get_value("CRM Lead", lead, "instagram_sender_id")
	if not sender_id:
		frappe.throw("This lead has no linked Instagram conversation")

	settings = _get_settings()
	if not settings.enabled:
		frappe.throw("Instagram integration is disabled in CRM Instagram Settings")

	url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.instagram_business_account_id}/messages"
	response = requests.post(
		url,
		params={"access_token": settings.get_password("access_token")},
		json={"recipient": {"id": sender_id}, "message": {"text": message}},
		timeout=15,
	)

	if not response.ok:
		frappe.throw(f"Failed to send Instagram message: {response.text}")

	frappe.get_doc(
		{
			"doctype": "CRM Instagram Message",
			"lead": lead,
			"sender_id": sender_id,
			"direction": "Sent",
			"message": message,
			"timestamp": frappe.utils.now_datetime(),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "sent"}
