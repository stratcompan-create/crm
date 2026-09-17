# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_report_summary():
	"""Soma o valor dos Honorários agrupado por status (Pago, Pendente, Atrasado)."""
	rows = frappe.db.get_all(
		"CRM Honorario",
		fields=["status", "sum(valor) as total"],
		group_by="status",
	)

	summary = {"Pago": 0, "Pendente": 0, "Atrasado": 0}
	for row in rows:
		if row.status in summary:
			summary[row.status] = row.total or 0

	summary["total_geral"] = sum(summary.values())
	return summary


@frappe.whitelist()
def get_monthly_series(months: int = 6):
	"""Total recebido (Pago) por mes, para os ultimos N meses."""
	months = int(months)
	rows = frappe.db.sql(
		"""
		select
			date_format(data_pagamento, '%%Y-%%m') as month,
			sum(valor) as total
		from `tabCRM Honorario`
		where status = 'Pago' and data_pagamento is not null
		group by month
		order by month desc
		limit %s
		""",
		(months,),
		as_dict=True,
	)
	rows.reverse()
	return rows


@frappe.whitelist()
def get_financial_health():
	"""Compara receita real (honorarios pagos) com receita perdida (negocios
	perdidos), e traz o teto de despesa/metas cadastrados para referencia."""
	received = frappe.db.get_value(
		"CRM Honorario", {"status": "Pago"}, "sum(valor)"
	) or 0
	pending = frappe.db.get_value(
		"CRM Honorario", {"status": ["in", ["Pendente", "Atrasado"]]}, "sum(valor)"
	) or 0

	lost_value = frappe.db.sql(
		"""
		select sum(deal.deal_value) as total
		from `tabCRM Deal` deal
		inner join `tabCRM Deal Status` st on st.name = deal.status
		where st.type = 'Lost'
		""",
		as_dict=True,
	)
	lost_value = (lost_value[0].total if lost_value else 0) or 0

	won_count = frappe.db.count(
		"CRM Deal",
		filters={"status": ["in", frappe.db.get_all(
			"CRM Deal Status", {"type": "Won"}, pluck="name"
		)]},
	)
	lost_count = frappe.db.count(
		"CRM Deal",
		filters={"status": ["in", frappe.db.get_all(
			"CRM Deal Status", {"type": "Lost"}, pluck="name"
		)]},
	)

	goals = frappe.db.get_singles_dict("CRM Financial Goals") or {}

	return {
		"received": received,
		"pending": pending,
		"lost_value": lost_value,
		"won_count": won_count,
		"lost_count": lost_count,
		"meta_trimestral": goals.get("meta_trimestral") or 0,
		"teto_despesa": goals.get("teto_despesa") or 0,
		"meta_mrr": goals.get("meta_mrr") or 0,
	}
