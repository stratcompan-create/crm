# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, getdate, nowdate

MONTHLY_TYPE = "Consultivo Mensal"

MANAGER_ROLES = ("System Manager", "Sales Manager")


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


@frappe.whitelist()
def get_report_summary():
	"""Soma o valor dos Honorários agrupado por status (Pago, Pendente, Atrasado)."""
	_managers_only()
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
	_managers_only()
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
	_managers_only()
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
		"expenses_month": flt(frappe.db.sql(
			"""select sum(valor) from `tabCRM Despesa`
			where status = 'Pago' and date_format(data_pagamento, '%%Y-%%m') = date_format(curdate(), '%%Y-%%m')"""
		)[0][0]),
		"expenses_pending": flt(frappe.db.get_value("CRM Despesa", {"status": ["in", ["Pendente", "Atrasado"]]}, "sum(valor)")),
	}


def _client_label(deal: str) -> str:
	row = frappe.db.get_value("CRM Deal", deal, ["organization", "first_name", "last_name"], as_dict=True) or {}
	return row.get("organization") or " ".join(filter(None, [row.get("first_name"), row.get("last_name")])) or deal


@frappe.whitelist()
def get_mrr():
	"""Receita recorrente mensal: última mensalidade de cada cliente ainda ativa."""
	_managers_only()
	today = getdate(nowdate())
	rows = frappe.get_all(
		"CRM Honorario",
		filters={"tipo_honorario": MONTHLY_TYPE},
		fields=["name", "deal", "valor", "status", "data_vencimento"],
		order_by="data_vencimento desc",
	)
	latest = {}
	for row in rows:
		latest.setdefault(row.deal, row)
	active = [r for r in latest.values() if r.data_vencimento and r.data_vencimento >= add_days(today, -45)]

	late, upcoming = [], []
	for r in rows:
		if not r.data_vencimento:
			continue
		if r.status == "Atrasado" or (r.status == "Pendente" and r.data_vencimento < today):
			late.append({"cliente": _client_label(r.deal), "valor": r.valor, "vencimento": r.data_vencimento, "dias": (today - r.data_vencimento).days, "name": r.name})
		elif r.status == "Pendente" and today <= r.data_vencimento <= add_days(today, 30):
			upcoming.append({"cliente": _client_label(r.deal), "valor": r.valor, "vencimento": r.data_vencimento, "dias": (r.data_vencimento - today).days, "name": r.name})

	series = frappe.db.sql(
		"""select date_format(data_vencimento, '%%Y-%%m') as month, sum(valor) as total
		from `tabCRM Honorario` where tipo_honorario = %s and data_vencimento is not null
		group by month order by month desc limit 6""",
		(MONTHLY_TYPE,),
		as_dict=True,
	)
	series.reverse()

	goals = frappe.db.get_singles_dict("CRM Financial Goals") or {}
	return {
		"mrr": sum(flt(r.valor) for r in active),
		"clientes": len(active),
		"meta_mrr": flt(goals.get("meta_mrr")),
		"atrasadas": sorted(late, key=lambda x: -x["dias"])[:20],
		"proximas": sorted(upcoming, key=lambda x: x["dias"])[:20],
		"series": series,
	}


@frappe.whitelist()
def get_cashflow(months: int = 6):
	"""Entradas (receitas pagas) x saídas (despesas pagas) por mês, mais o previsto (pendente)."""
	_managers_only()
	months = int(months)
	start = getdate(add_months(nowdate().rsplit("-", 1)[0] + "-01", -(months - 1)))
	end_month = add_months(nowdate().rsplit("-", 1)[0] + "-01", 2)

	def by_month(doctype, status_in, date_field):
		rows = frappe.db.sql(
			f"""select date_format({date_field}, '%%Y-%%m') as month, sum(valor) as total
			from `tab{doctype}` where status in %s and {date_field} is not null and {date_field} >= %s
			group by month""",
			(status_in, start),
			as_dict=True,
		)
		return {r.month: flt(r.total) for r in rows}

	entradas = by_month("CRM Honorario", ("Pago",), "data_pagamento")
	saidas = by_month("CRM Despesa", ("Pago",), "data_pagamento")
	prev_e = by_month("CRM Honorario", ("Pendente", "Atrasado"), "data_vencimento")
	prev_s = by_month("CRM Despesa", ("Pendente", "Atrasado"), "data_vencimento")

	out, cursor, acumulado = [], start, 0
	while cursor <= getdate(end_month):
		key = cursor.strftime("%Y-%m")
		e, s = entradas.get(key, 0), saidas.get(key, 0)
		acumulado += e - s
		out.append({
			"month": key,
			"entradas": e,
			"saidas": s,
			"saldo": e - s,
			"acumulado": acumulado,
			"prev_entradas": prev_e.get(key, 0),
			"prev_saidas": prev_s.get(key, 0),
		})
		cursor = getdate(add_months(cursor, 1))
	return out


@frappe.whitelist()
def get_revenue_breakdown():
	"""Receita por cliente e por serviço (pago + a receber)."""
	_managers_only()
	rows = frappe.get_all("CRM Honorario", fields=["deal", "servico", "valor", "status"])
	clients, services = {}, {}
	for r in rows:
		bucket = "pago" if r.status == "Pago" else "pendente"
		c = clients.setdefault(r.deal, {"cliente": None, "pago": 0, "pendente": 0})
		c[bucket] += flt(r.valor)
		s = services.setdefault(r.servico or "Não informado", {"servico": r.servico or "Não informado", "pago": 0, "pendente": 0})
		s[bucket] += flt(r.valor)
	for deal, c in clients.items():
		c["cliente"] = _client_label(deal)
	by_total = lambda x: -(x["pago"] + x["pendente"])
	return {
		"clientes": sorted(clients.values(), key=by_total)[:10],
		"servicos": sorted(services.values(), key=by_total),
	}


def mark_overdue():
	"""Diário: receitas e despesas pendentes vencidas viram 'Atrasado' sozinhas."""
	today = nowdate()
	for doctype in ("CRM Honorario", "CRM Despesa"):
		for name in frappe.get_all(doctype, filters={"status": "Pendente", "data_vencimento": ["<", today]}, pluck="name"):
			frappe.db.set_value(doctype, name, "status", "Atrasado", update_modified=False)


@frappe.whitelist(methods=["POST"])
def export_goals_pdf():
	"""PDF com as metas financeiras e o quanto já foi atingido. Guarda em Arquivos > Financeiro
	(e, com o Google Drive conectado e o envio automático ligado, a cópia vai sozinha para o Drive)."""
	import glob
	import os

	from frappe.utils.pdf import get_pdf

	from crm.api.prospeccao import _ensure_folder
	from crm.api.proposta import _valid_color, _fmt_currency

	_managers_only()
	settings = frappe.get_single("FCRM Settings")
	color = _valid_color(settings.get("brand_color"), "#042d3c")
	accent = _valid_color(settings.get("brand_accent"), "#8aa1a9")
	today = getdate(nowdate())
	q_start = getdate(f"{today.year}-{3 * ((today.month - 1) // 3) + 1:02d}-01")

	health = get_financial_health()
	mrr = get_mrr()
	received_q = flt(
		frappe.db.get_value("CRM Honorario", {"status": "Pago", "data_pagamento": [">=", q_start]}, "sum(valor)")
	)
	linhas = [
		(_("Receita do trimestre"), received_q, flt(health.get("meta_trimestral")), False),
		(_("Despesas pagas no mês"), flt(health.get("expenses_month")), flt(health.get("teto_despesa")), True),
		(_("Receita recorrente mensal (MRR)"), flt(mrr.get("mrr")), flt(mrr.get("meta_mrr")), False),
	]

	def barra(atual, meta, invertida):
		if not meta:
			return "<td class='r' colspan='2' style='color:#999'>" + _("Meta não definida") + "</td>"
		pct = round(atual / meta * 100)
		largura = min(100, max(0, pct))
		cor = "#c0392b" if (invertida and pct > 100) else color
		return (
			f"<td style='width:38%'><table style='width:100%;border-collapse:collapse'><tr>"
			f"<td style='background:{cor};width:{largura}%;height:9px;padding:0'></td>"
			f"<td style='background:#e6eaeb;height:9px;padding:0'></td></tr></table></td>"
			f"<td class='r'>{pct}%</td>"
		)

	rows = "".join(
		f"<tr><td>{frappe.utils.escape_html(t)}</td><td class='r'>{_fmt_currency(a)}</td>"
		f"<td class='r'>{_fmt_currency(m) if m else '—'}</td>{barra(a, m, inv)}</tr>"
		for t, a, m, inv in linhas
	)
	html = f"""<html><head><meta charset="utf-8"><style>
		body {{ font-family: Arial, Helvetica, sans-serif; color:#1a1a1a; padding:32px; }}
		h1 {{ color:{color}; font-size:24px; margin:0 0 4px 0; }}
		.sub {{ color:#666; font-size:12px; margin-bottom:24px; }}
		table.t {{ width:100%; border-collapse:collapse; }}
		table.t th {{ text-align:left; font-size:11px; text-transform:uppercase; color:#666; border-bottom:2px solid {accent}; padding:8px 4px; }}
		table.t td {{ padding:12px 4px; border-bottom:1px solid #eee; font-size:13px; }}
		.r {{ text-align:right; }}
	</style></head><body>
		<h1>{_("Metas financeiras")}</h1>
		<div class="sub">{frappe.utils.escape_html(settings.get("brand_name") or "")} · {today.strftime("%d/%m/%Y")}</div>
		<table class="t"><tr><th>{_("Indicador")}</th><th class="r">{_("Realizado")}</th><th class="r">{_("Meta / teto")}</th><th>{_("Progresso")}</th><th class="r">%</th></tr>{rows}</table>
	</body></html>"""

	pdf = get_pdf(html)
	folder = _ensure_folder("Financeiro")
	base = f"Metas financeiras - {today.isoformat()}"
	for old in frappe.get_all("File", filters={"folder": folder, "file_name": ["like", f"{base}%"]}, pluck="name"):
		frappe.delete_doc("File", old, ignore_permissions=True, force=True)
	for stale in glob.glob(frappe.get_site_path("private", "files", f"{base}*.pdf")):
		os.remove(stale)
	file_doc = frappe.get_doc(
		{"doctype": "File", "file_name": f"{base}.pdf", "folder": folder, "is_private": 1, "content": pdf}
	)
	file_doc.insert(ignore_permissions=True)
	return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}


@frappe.whitelist()
def get_revenue_nature(months: int = 6):
	"""Faturamento recebido por mês, separando o que é recorrente (mensalidades, que se repetem
	todo mês) do que é pontual (projetos e serviços avulsos, como a implantação de um CRM ou a
	criação de um site). O pontual entra no faturamento do mês, mas não se repete."""
	_managers_only()
	months = max(1, min(int(months), 24))
	current = nowdate().rsplit("-", 1)[0] + "-01"
	start = getdate(add_months(current, -(months - 1)))

	def by_month(status_in, date_field):
		rows = frappe.db.sql(
			f"""select date_format({date_field}, '%%Y-%%m') as month,
				if(tipo_honorario = %s, 'recorrente', 'pontual') as natureza, sum(valor) as total
			from `tabCRM Honorario` where status in %s and {date_field} is not null and {date_field} >= %s
			group by month, natureza""",
			(MONTHLY_TYPE, status_in, start),
			as_dict=True,
		)
		out = {}
		for r in rows:
			out.setdefault(r.month, {"recorrente": 0, "pontual": 0})[r.natureza] = flt(r.total)
		return out

	recebido = by_month(("Pago",), "data_pagamento")
	previsto = by_month(("Pendente", "Atrasado"), "data_vencimento")

	out, cursor = [], start
	while cursor <= getdate(current):
		key = cursor.strftime("%Y-%m")
		r = recebido.get(key, {"recorrente": 0, "pontual": 0})
		p = previsto.get(key, {"recorrente": 0, "pontual": 0})
		total = r["recorrente"] + r["pontual"]
		out.append({
			"month": key,
			"recorrente": r["recorrente"],
			"pontual": r["pontual"],
			"total": total,
			"pct_recorrente": round(r["recorrente"] / total * 100) if total else 0,
			"previsto_recorrente": p["recorrente"],
			"previsto_pontual": p["pontual"],
		})
		cursor = getdate(add_months(cursor, 1))
	return out
