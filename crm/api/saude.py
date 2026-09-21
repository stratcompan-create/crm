# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Painel de saúde do negócio (Visão Geral): o que precisa da atenção da pessoa hoje,
# reunindo o que já existe no CRM. Vendedor vê só o que é dele; o financeiro é do gestor.

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from crm.api.followup import OPEN_TASK


def _is_manager() -> bool:
	return bool(set(frappe.get_roles()) & {"System Manager", "Sales Manager"})


def _count(doctype, filters) -> int:
	return len(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=1000))


@frappe.whitelist()
def get_business_health() -> dict:
	today = getdate(nowdate())
	manager = _is_manager()
	open_task = ["in", ["Backlog", "Todo", "In Progress"]]
	items = []

	def add(key, label, count, route, tone="warn", detail=""):
		items.append({"key": key, "label": label, "count": count, "route": route, "tone": tone, "detail": detail})

	# tarefas e follow-ups
	late_tasks = _count("CRM Task", {"status": open_task, "due_date": ["<", f"{today} 00:00:00"]})
	add("tarefas_atrasadas", "Tarefas atrasadas", late_tasks, "Tasks", "bad" if late_tasks else "ok")
	followups = _count("CRM Task", {"reference_doctype": "CRM Lead", "title": ["like", "Follow-up:%"], "status": OPEN_TASK})
	add("followups", "Follow-ups para enviar", followups, "Tasks", "warn" if followups else "ok")

	# negócios parados (sem movimento há mais de 5 dias, ainda em andamento)
	open_status = frappe.get_all("CRM Deal Status", filters={"type": ["in", ["Open", "Ongoing"]]}, pluck="name")
	stalled = _count(
		"CRM Deal", {"status": ["in", open_status], "modified": ["<", f"{add_days(today, -5)} 00:00:00"]}
	) if open_status else 0
	add("negocios_parados", "Negócios parados há 5 dias ou mais", stalled, "Deals", "warn" if stalled else "ok")

	# leads sem responsável (só o gestor enxerga todos)
	if manager:
		no_owner = _count("CRM Lead", {"lead_owner": ["is", "not set"], "converted": 0})
		add("leads_sem_dono", "Leads sem responsável", no_owner, "Leads", "warn" if no_owner else "ok")

	# reuniões de hoje
	meetings = frappe.get_list(
		"CRM Reuniao",
		filters={"status": "Agendada", "inicio": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]},
		fields=["nome", "inicio"],
		order_by="inicio asc",
	)
	add(
		"reunioes_hoje",
		"Reuniões hoje",
		len(meetings),
		"Tasks",
		"info" if meetings else "ok",
		", ".join(f"{m.inicio.strftime('%H:%M')} {m.nome}" for m in meetings[:3]),
	)

	# financeiro (só gestor)
	money = {}
	if manager:
		overdue = frappe.get_all("CRM Honorario", filters={"status": "Atrasado"}, fields=["count(name) as n", "sum(valor) as t"])[0]
		week = frappe.get_all(
			"CRM Honorario",
			filters={"status": "Pendente", "data_vencimento": ["between", [today, add_days(today, 7)]]},
			fields=["count(name) as n", "sum(valor) as t"],
		)[0]
		add("atrasados", "Cobranças em atraso", overdue.n, "Financeiro", "bad" if overdue.n else "ok")
		add("a_vencer", "Vencem nos próximos 7 dias", week.n, "Financeiro", "warn" if week.n else "ok")
		money = {"atrasado": flt(overdue.t), "a_vencer": flt(week.t)}

	problems = sum(1 for i in items if i["tone"] in ("bad", "warn") and i["count"])
	return {"itens": items, "valores": money, "pendencias": problems, "gestor": manager}
