# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Métricas de prospecção e conversão: o que aconteceu com as conversas e os leads que
# chegaram (ou foram abordados) pelo Instagram, cruzando o CRM com a Prospecção.

import frappe
from frappe.utils import add_days, cint, get_datetime, now_datetime, nowdate

from crm.api import prospeccao
from crm.api.followup import OPEN_TASK, analyze_lead, replied_since

PERIODS = (7, 14, 30)


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _sum(days: dict, key: str) -> int:
	return sum(cint(d.get(key)) for d in days.values())


def _sum_canal(days: dict, canal: str) -> int:
	return sum(cint((d.get("respostas") or {}).get(canal)) for d in days.values())


def _objections(days: dict) -> list[dict]:
	total: dict = {}
	for d in days.values():
		for name, n in (d.get("objecoes") or {}).items():
			total[name] = total.get(name, 0) + cint(n)
	return [{"nome": k, "total": v} for k, v in sorted(total.items(), key=lambda x: -x[1]) if v]


def _first_response_hours(lead_names: list[str]) -> float | None:
	"""Tempo médio entre a primeira mensagem recebida e a nossa primeira resposta."""
	gaps = []
	for lead in lead_names:
		msgs = frappe.get_all(
			"CRM Instagram Message",
			filters={"lead": lead},
			fields=["direction", "timestamp"],
			order_by="timestamp asc",
		)
		first_in = next((m for m in msgs if m.direction == "Received"), None)
		if not first_in:
			continue
		reply = next((m for m in msgs if m.direction == "Sent" and m.timestamp > first_in.timestamp), None)
		if reply:
			gaps.append((get_datetime(reply.timestamp) - get_datetime(first_in.timestamp)).total_seconds() / 3600)
	return round(sum(gaps) / len(gaps), 1) if gaps else None


def _person(lead) -> dict:
	return {
		"lead": lead.name,
		"nome": " ".join(filter(None, [lead.first_name, lead.last_name])),
		"usuario": lead.get("instagram_username") or "",
	}


def _waiting_for_us() -> list[dict]:
	"""Conversas em que a última mensagem foi da pessoa e ainda não respondemos."""
	leads = frappe.get_all(
		"CRM Lead",
		filters={"instagram_sender_id": ["is", "set"]},
		fields=["name", "first_name", "last_name", "instagram_username"],
		limit_page_length=300,
	)
	now = now_datetime()
	out = []
	for lead in leads:
		last = frappe.get_all(
			"CRM Instagram Message",
			filters={"lead": lead.name},
			fields=["direction", "timestamp"],
			order_by="timestamp desc",
			limit=1,
		)
		if not last or last[0].direction != "Received":
			continue
		hours = (now - get_datetime(last[0].timestamp)).total_seconds() / 3600
		info = analyze_lead(lead.name)
		out.append(
			{
				**_person(lead),
				"espera_horas": round(hours, 1),
				"dentro_de_24h": hours < 24,
				"temperatura": info["temperatura"],
				"objecao": info["objecao"],
				"proxima": info["proxima"],
			}
		)
	return sorted(out, key=lambda x: -x["espera_horas"])[:15]


def _approached_without_reply(start: str) -> tuple[list[dict], dict]:
	"""Abordados que não responderam, e a taxa de resposta por tipo de abordagem."""
	leads = frappe.get_all(
		"CRM Lead",
		filters={"abordado_em": ["is", "set"]},
		fields=["name", "first_name", "last_name", "instagram_username", "source", "abordagem", "abordado_em", "followups_feitos"],
		limit_page_length=500,
	)
	now = now_datetime()
	silent, by_type = [], {}
	for lead in leads:
		replied = replied_since(lead.name, lead.abordado_em)
		if not replied:
			silent.append(
				{
					**_person(lead),
					"canal": lead.source,
					"abordagem": lead.abordagem or "",
					"dias": (now - get_datetime(lead.abordado_em)).days,
					"followups": cint(lead.followups_feitos),
				}
			)
		if str(lead.abordado_em)[:10] >= start:
			key = lead.abordagem or "Sem tipo definido"
			row = by_type.setdefault(key, {"abordagem": key, "abordados": 0, "responderam": 0})
			row["abordados"] += 1
			row["responderam"] += 1 if replied else 0
	for row in by_type.values():
		row["taxa"] = round(row["responderam"] / row["abordados"] * 100) if row["abordados"] else 0
	return sorted(silent, key=lambda x: -x["dias"])[:15], by_type


@frappe.whitelist()
def get_conversation_metrics(days: int = 30) -> dict:
	_managers_only()
	days = int(days)
	if days not in PERIODS:
		days = 30
	today = nowdate()
	start = add_days(today, -days)
	prev_start = add_days(start, -days)

	current = prospeccao._effective_days(start, today)
	previous = prospeccao._effective_days(prev_start, add_days(start, -1))

	def block(d):
		return {
			"abordados": _sum(d, "abordados"),
			"respostas": _sum_canal(d, "Instagram"),
			"agendadas": _sum(d, "agendadas"),
			"realizadas": _sum(d, "realizadas"),
			"propostas": _sum(d, "propostas"),
			"fechamentos": _sum(d, "fechamentos"),
		}

	cur, prev = block(current), block(previous)
	start_dt = f"{start} 00:00:00"

	ig_leads = frappe.get_all(
		"CRM Lead", filters={"source": "Instagram", "creation": [">=", start_dt]}, pluck="name"
	)
	conversas = frappe.db.sql(
		"""select count(distinct lead) from `tabCRM Instagram Message`
		where direction = 'Received' and timestamp >= %s""",
		(start_dt,),
	)[0][0]
	funil_status = frappe.db.sql(
		"""select status, count(*) as n from `tabCRM Lead`
		where source = 'Instagram' and creation >= %s group by status order by n desc""",
		(start_dt,),
		as_dict=True,
	)
	negocios = won = 0
	if ig_leads:
		negocios = frappe.db.count("CRM Deal", {"lead": ["in", ig_leads]})
		won_status = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")
		won = frappe.db.count("CRM Deal", {"lead": ["in", ig_leads], "status": ["in", won_status]}) if won_status else 0

	silent, by_type = _approached_without_reply(start)
	return {
		"dias": days,
		"atual": cur,
		"anterior": prev,
		"taxa_resposta": round(cur["respostas"] / cur["abordados"] * 100) if cur["abordados"] else None,
		"leads_novos": len(ig_leads),
		"conversas": conversas,
		"tempo_primeira_resposta_h": _first_response_hours(
			frappe.get_all(
				"CRM Instagram Message",
				filters={"direction": "Received", "timestamp": [">=", start_dt]},
				pluck="lead",
				distinct=True,
			)
		),
		"funil_status": funil_status,
		"negocios": negocios,
		"ganhos": won,
		"objecoes": _objections(current),
		"aguardando_nos": _waiting_for_us(),
		"sem_resposta": silent,
		"por_abordagem": sorted(by_type.values(), key=lambda x: -x["abordados"]),
		"followups_abertos": frappe.db.count(
			"CRM Task", {"reference_doctype": "CRM Lead", "title": ["like", "Follow-up:%"], "status": OPEN_TASK}
		),
		"followups_criados": frappe.db.count(
			"CRM Task", {"reference_doctype": "CRM Lead", "title": ["like", "Follow-up:%"], "creation": [">=", start_dt]}
		),
	}
