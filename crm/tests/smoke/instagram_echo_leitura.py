"""Teste de fumaça: eco de mensagem mandada direto pelo app do Instagram, recibo de
leitura, e o follow-up automático de quem leu e não respondeu.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import uuid
from datetime import datetime, timedelta

import frappe

from crm.api import followup as fu
from crm.api import instagram as ig

U = uuid.uuid4().hex[:6]


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	settings = frappe.get_single("CRM Instagram Settings")
	old = (settings.enabled, settings.instagram_business_account_id)
	frappe.db.set_single_value("CRM Instagram Settings", "enabled", 1)
	frappe.db.set_single_value("CRM Instagram Settings", "instagram_business_account_id", "NOSSACONTA" + U)

	cfg_old = frappe.db.get_singles_dict("CRM Follow-up Config").get("ativado")
	frappe.db.set_single_value("CRM Follow-up Config", "ativado", 1)

	made = []
	try:
		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"first_name": "Zz Echo",
				"last_name": "Teste",
				"instagram_sender_id": "TECHO" + U,
				"instagram_username": "zzecho" + U,
				"lead_owner": "Administrator",
			}
		).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))

		# eco de mensagem mandada pelo próprio CRM (send_reply já gravou o mesmo mid) - não duplica
		ig_msg = frappe.get_doc(
			{
				"doctype": "CRM Instagram Message",
				"lead": lead.name,
				"sender_id": lead.instagram_sender_id,
				"direction": "Sent",
				"message": "Mensagem mandada pelo CRM",
				"mid": "MIDCRM" + U,
				"timestamp": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		made.append(("CRM Instagram Message", ig_msg.name))

		ig._process_outgoing_echo(lead.instagram_sender_id, "MIDCRM" + U, "Mensagem mandada pelo CRM")
		ck(
			"eco de mensagem já logada pelo CRM não duplica",
			frappe.db.count("CRM Instagram Message", {"lead": lead.name, "direction": "Sent"}) == 1,
		)

		# eco de mensagem mandada direto pelo app (mid novo) - grava
		ig._process_outgoing_echo(lead.instagram_sender_id, "MIDAPP" + U, "Respondi direto pelo app")
		nova = frappe.db.get_value("CRM Instagram Message", {"mid": "MIDAPP" + U}, ["name", "direction", "lead"], as_dict=True)
		made.append(("CRM Instagram Message", nova.name)) if nova else None
		ck(
			"eco de mensagem mandada pelo app é gravada como Sent",
			nova and nova.direction == "Sent" and nova.lead == lead.name,
		)

		# eco de mensagem para um lead desconhecido não quebra nem cria nada
		ig._process_outgoing_echo("SEMLEAD" + U, "MIDX" + U, "texto qualquer")
		ck("eco pra destinatário sem lead vinculado não quebra", not frappe.db.exists("CRM Instagram Message", {"mid": "MIDX" + U}))

		# recibo de leitura (watermark) marca lida_em nas mensagens enviadas até aquele horário
		watermark_ms = int(frappe.utils.now_datetime().timestamp() * 1000) + 5000
		ig._process_read_receipt(lead.instagram_sender_id, {"watermark": watermark_ms})
		lida_em_1 = frappe.db.get_value("CRM Instagram Message", ig_msg.name, "lida_em")
		lida_em_2 = frappe.db.get_value("CRM Instagram Message", nova.name, "lida_em")
		ck("recibo de leitura marca lida_em nas mensagens enviadas", bool(lida_em_1) and bool(lida_em_2))

		# recibo de leitura pra sender sem lead vinculado não quebra
		ig._process_read_receipt("SEMLEAD" + U, {"watermark": watermark_ms})

		# ---------------- follow-up automático de quem leu e não respondeu ----------------

		# lida há 21h (passou da janela) e sem resposta desde então -> cria follow-up
		frappe.db.set_value(
			"CRM Instagram Message", nova.name, "lida_em", frappe.utils.now_datetime() - timedelta(hours=21), update_modified=False
		)
		criados = fu.run_read_followups()
		task = frappe.db.get_value(
			"CRM Task", {"reference_doctype": "CRM Lead", "reference_docname": lead.name, "title": ["like", "Follow-up:%"]}, "name"
		)
		if task:
			made.append(("CRM Task", task))
		ck("cria follow-up de quem leu há mais de 20h e não respondeu", criados == 1 and bool(task))

		# rodar de novo não duplica (já existe task em aberto)
		criados2 = fu.run_read_followups()
		ck("não duplica follow-up se já existe um em aberto", criados2 == 0)

		frappe.delete_doc("CRM Task", task, force=True, ignore_permissions=True)

		# lida há só 2h (dentro da janela) -> não cria
		frappe.db.set_value(
			"CRM Instagram Message", nova.name, "lida_em", frappe.utils.now_datetime() - timedelta(hours=2), update_modified=False
		)
		criados3 = fu.run_read_followups()
		ck("não cria follow-up se a leitura foi recente", criados3 == 0)

		# respondeu depois de ler -> não cria, mesmo com leitura antiga
		frappe.db.set_value(
			"CRM Instagram Message", nova.name, "lida_em", frappe.utils.now_datetime() - timedelta(hours=21), update_modified=False
		)
		resposta = frappe.get_doc(
			{
				"doctype": "CRM Instagram Message",
				"lead": lead.name,
				"sender_id": lead.instagram_sender_id,
				"direction": "Received",
				"message": "Ah, oi! desculpa a demora",
				"timestamp": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)
		made.append(("CRM Instagram Message", resposta.name))
		criados4 = fu.run_read_followups()
		ck("não cria follow-up se a pessoa já respondeu depois de ler", criados4 == 0)
	finally:
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.set_single_value("CRM Instagram Settings", "enabled", old[0])
		frappe.db.set_single_value("CRM Instagram Settings", "instagram_business_account_id", old[1] or "")
		if cfg_old is not None:
			frappe.db.set_single_value("CRM Follow-up Config", "ativado", cfg_old)
		frappe.db.commit()

	return res
