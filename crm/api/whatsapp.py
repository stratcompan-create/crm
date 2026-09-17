import json

import frappe
from frappe import _

from crm.api.doc import get_assigned_users
from crm.fcrm.doctype.crm_notification.crm_notification import notify_user
from crm.integrations.api import get_contact_lead_or_deal_from_number

ALLOWED_WHATSAPP_ROLES = ["System Manager", "Sales Manager", "Sales User"]

# Adapter layer: the installed `whatsapp` app (github.com/frappe/whatsapp) uses a
# different schema than what this file and the CRM frontend were originally built
# against (e.g. `direction` instead of `type`, `reference_docname` instead of
# `reference_name`, `to` is a WhatsApp Profile link instead of a raw phone number,
# reactions/replies/templates are resolved server-side by the app itself). Rather
# than rewrite the Vue components, every function here delegates to the app's own
# whitelisted API and translates the result back into the shape the CRM frontend
# already understands.


def validate_access(reference_doctype=None, reference_name=None, permtype="read"):
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if reference_doctype and reference_name:
		if not frappe.db.exists(reference_doctype, reference_name):
			frappe.throw(
				_("Reference document {0} {1} does not exist.").format(reference_doctype, reference_name),
				frappe.DoesNotExistError,
			)
		reference_doc = frappe.get_doc(reference_doctype, reference_name)
		if not reference_doc.has_permission(permtype):
			frappe.throw(
				_("Not permitted to access reference document {0} {1}.").format(
					reference_doctype, reference_name
				),
				frappe.PermissionError,
			)
		return reference_doc

	return None


def validate(doc, method):
	if doc.reference_doctype and doc.reference_docname:
		return

	if doc.direction == "Incoming":
		phone_number = doc.get("from")
	else:
		phone_number = doc.to and frappe.db.get_value("WhatsApp Profile", doc.to, "phone_number")

	if not phone_number:
		return

	try:
		name, doctype = get_contact_lead_or_deal_from_number(phone_number)
		if doctype and name is not None:
			doc.reference_doctype = doctype
			doc.reference_docname = name
	except Exception:
		frappe.log_error(frappe.get_traceback(), "CRM WhatsApp: failed to resolve contact from number")


def on_update(doc, method):
	frappe.publish_realtime(
		"whatsapp_message",
		{
			"reference_doctype": doc.reference_doctype,
			# frontend socket handler matches on `reference_name`, not `reference_docname`
			"reference_name": doc.reference_docname,
		},
	)

	notify_agent(doc)


def notify_agent(doc):
	if doc.direction != "Incoming":
		return
	if not doc.reference_doctype or not doc.reference_docname:
		return
	doctype = doc.reference_doctype
	if doctype and doctype.startswith("CRM "):
		doctype = doctype[4:].lower()
	safe_reference_name = frappe.utils.escape_html(doc.reference_docname)
	notification_text = f"""
            <div class="mb-2 leading-5 text-ink-gray-5">
                <span class="font-medium text-ink-gray-9">{_("You")}</span>
                <span>{_("received a whatsapp message in {0}").format(doctype)}</span>
                <span class="font-medium text-ink-gray-9">{safe_reference_name}</span>
            </div>
        """
	assigned_users = get_assigned_users(doc.reference_doctype, doc.reference_docname)
	for user in assigned_users:
		notify_user(
			{
				"owner": doc.owner,
				"assigned_to": user,
				"notification_type": "WhatsApp",
				"message": doc.message,
				"notification_text": notification_text,
				"reference_doctype": "WhatsApp Message",
				"reference_docname": doc.name,
				"redirect_to_doctype": doc.reference_doctype,
				"redirect_to_docname": doc.reference_docname,
			}
		)


@frappe.whitelist()
def is_whatsapp_enabled():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	default_account = frappe.db.get_single_value("WhatsApp Settings", "default_account")
	if not default_account:
		return False
	status = frappe.get_cached_value("WhatsApp Account", default_account, "status")
	return status == "Active"


@frappe.whitelist()
def is_whatsapp_installed():
	if not frappe.db.exists("DocType", "WhatsApp Settings"):
		return False
	return True


@frappe.whitelist()
def get_whatsapp_messages(reference_doctype: str, reference_name: str):
	reference_doc = validate_access(reference_doctype, reference_name)
	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []

	from whatsapp.whatsapp.api.messages import get_messages as wa_get_messages

	references = [[reference_doctype, reference_name]]

	if reference_doctype == "CRM Deal":
		lead = reference_doc.get("lead")
		if lead:
			validate_access("CRM Lead", lead)
			references.append(["CRM Lead", lead])

	messages = wa_get_messages(json.dumps(references))
	return _adapt_messages_for_crm_ui(messages)


@frappe.whitelist()
def get_whatsapp_conversations():
	"""One row per lead/deal/contact that has WhatsApp messages, most recent first.

	Powers the dedicated WhatsApp inbox page, which lists conversations rather
	than a single reference document's thread.
	"""
	if not any(role in ALLOWED_WHATSAPP_ROLES for role in frappe.get_roles()):
		frappe.throw(_("Only sales users can access WhatsApp features."), frappe.PermissionError)

	if not frappe.db.exists("DocType", "WhatsApp Message"):
		return []

	groups = frappe.db.sql(
		"""
		select reference_doctype, reference_docname, max(creation) as last_message_at
		from `tabWhatsApp Message`
		where reference_doctype is not null and reference_docname is not null
		group by reference_doctype, reference_docname
		order by last_message_at desc
		limit 200
		""",
		as_dict=True,
	)

	conversations = []
	for group in groups:
		if not frappe.db.exists(group.reference_doctype, group.reference_docname):
			continue
		reference_doc = frappe.get_doc(group.reference_doctype, group.reference_docname)
		if not reference_doc.has_permission("read"):
			continue

		last_message = frappe.db.get_value(
			"WhatsApp Message",
			{
				"reference_doctype": group.reference_doctype,
				"reference_docname": group.reference_docname,
			},
			["message", "direction", "status", "is_template", "creation", "to"],
			order_by="creation desc",
			as_dict=True,
		)
		if not last_message:
			continue

		title = get_from_name(
			{
				"reference_doctype": group.reference_doctype,
				"reference_docname": group.reference_docname,
			}
		) or group.reference_docname

		conversations.append(
			{
				"reference_doctype": group.reference_doctype,
				"reference_name": group.reference_docname,
				"title": title,
				"whatsapp_to": last_message.to,
				"last_message": _("Mensagem de modelo") if last_message.is_template else last_message.message,
				"last_message_at": group.last_message_at,
				"last_message_direction": "Incoming" if last_message.direction == "Incoming" else "Outgoing",
				"last_message_status": (last_message.status or "").lower(),
			}
		)

	return conversations


@frappe.whitelist()
def create_whatsapp_message(
	reference_doctype: str,
	reference_name: str,
	message: str,
	to: str,
	attach: str = "",
	reply_to: str = "",
	content_type: str = "text",
):
	validate_access(reference_doctype, reference_name)

	from whatsapp.whatsapp.api.messages import send_message

	return send_message(
		to=to,
		message=message,
		attach=attach or None,
		content_type=content_type,
		reply_to=reply_to or None,
		reference_doctype=reference_doctype,
		reference_docname=reference_name,
	)


@frappe.whitelist()
def send_whatsapp_template(reference_doctype: str, reference_name: str, template: str, to: str):
	validate_access(reference_doctype, reference_name)

	from whatsapp.whatsapp.api.messages import send_template

	return send_template(
		template=template,
		to=to,
		reference_doctype=reference_doctype,
		reference_docname=reference_name,
	)


@frappe.whitelist()
def react_on_whatsapp_message(emoji: str, reply_to_name: str):
	validate_access()

	from whatsapp.whatsapp.api.messages import react_to_message

	return react_to_message(message=reply_to_name, emoji=emoji)


def _infer_content_type(message):
	mime_type = message.get("mime_type") or ""
	if not message.get("media_url"):
		return "text"
	if mime_type.startswith("image/"):
		return "image"
	if mime_type.startswith("video/"):
		return "video"
	if mime_type.startswith("audio/"):
		return "audio"
	return "document"


def _adapt_messages_for_crm_ui(messages):
	"""Translate the whatsapp app's message shape into the shape WhatsAppArea.vue,
	WhatsAppBox.vue and Activities.vue already know how to render, so those
	components don't need to change."""
	by_name = {m["name"]: m for m in messages}

	for m in messages:
		m["type"] = "Incoming" if m.get("direction") == "Incoming" else "Outgoing"
		m["reference_name"] = m.get("reference_docname")
		m["status"] = (m.get("status") or "").lower()
		m["attach"] = m.get("media_url") or ""
		m["content_type"] = _infer_content_type(m)
		m["message_type"] = "Template" if m.get("is_template") else None

		reactions = m.get("reactions") or []
		m["reaction"] = reactions[0]["emoji"] if reactions else None

		m["is_reply"] = bool(m.get("reply_to"))
		if m.get("reply_to_direction"):
			m["reply_to_type"] = "Incoming" if m["reply_to_direction"] == "Incoming" else "Outgoing"

		m["from_name"] = get_from_name(m) if m.get("from") else _("You")

	for m in messages:
		target = by_name.get(m.get("reply_to"))
		if target:
			m["reply_to_from"] = target["from_name"]

	return messages


def get_from_name(message):
	reference_doctype = message.get("reference_doctype")
	reference_name = message.get("reference_docname")
	if not reference_doctype or not reference_name or not frappe.db.exists(reference_doctype, reference_name):
		return ""

	doc = frappe.get_doc(reference_doctype, reference_name)
	from_name = ""
	if reference_doctype == "CRM Deal":
		if doc.get("contacts"):
			for c in doc.get("contacts"):
				if c.is_primary:
					from_name = c.full_name or c.mobile_no
					break
		else:
			from_name = doc.get("lead_name")
	else:
		from_name = " ".join(name for name in [doc.get("first_name"), doc.get("last_name")] if name)
	return from_name


def add_roles():
	if "whatsapp" not in frappe.get_installed_apps():
		return

	from frappe.permissions import add_permission, update_permission_property

	role_list = ["Sales Manager", "Sales User"]
	doctypes = ["WhatsApp Message", "WhatsApp Template", "WhatsApp Settings"]
	for doctype in doctypes:
		for role in role_list:
			if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				continue
			add_permission(doctype, role, 0, "write")
			update_permission_property(doctype, role, 0, "create", 1)
			update_permission_property(doctype, role, 0, "delete", 1)
			update_permission_property(doctype, role, 0, "share", 1)
			update_permission_property(doctype, role, 0, "email", 1)
			update_permission_property(doctype, role, 0, "print", 1)
			update_permission_property(doctype, role, 0, "report", 1)
			update_permission_property(doctype, role, 0, "export", 1)
