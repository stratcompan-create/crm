# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import add_days, cint, getdate, nowdate

COUNT_FIELDS = ("abordados", "agendadas", "realizadas", "propostas", "fechamentos")

MANAGER_ROLES = ("System Manager", "Sales Manager")


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


def _lines(value: str | None) -> list[str]:
	return [line.strip() for line in (value or "").split("\n") if line.strip()]


def _json(value) -> dict:
	if isinstance(value, dict):
		return value
	try:
		return json.loads(value or "{}") or {}
	except Exception:
		return {}


def _config() -> dict:
	cfg = frappe.get_single("CRM Prospecao Config")
	return {
		"meta_diaria": cint(cfg.meta_diaria) or 20,
		"canais": _lines(cfg.canais),
		"objecoes": _lines(cfg.objecoes),
	}


def _ensure_lead_sources(canais: list[str]):
	"""Todo canal vira uma origem de lead, para o CRM contar sozinho as respostas dele."""
	existing = frappe.get_all("CRM Lead Source", pluck="name")
	known = set(existing) | {frappe._(name) for name in existing}
	for canal in canais:
		if canal not in known:
			frappe.get_doc({"doctype": "CRM Lead Source", "source_name": canal}).insert(ignore_permissions=True)


def _automatic(start) -> dict:
	"""O que o CRM já sabe sozinho: negócios ganhos e leads criados (por origem) em cada dia."""
	auto: dict = {}

	won = frappe.db.sql(
		"""select deal.closed_date as d, count(*) as n from `tabCRM Deal` deal
		inner join `tabCRM Deal Status` st on st.name = deal.status
		where st.type = 'Won' and deal.closed_date >= %s group by deal.closed_date""",
		(start,),
		as_dict=True,
	)
	for row in won:
		auto.setdefault(str(row.d), {"fechamentos": 0, "respostas": {}})["fechamentos"] = cint(row.n)

	leads = frappe.db.sql(
		"""select date(creation) as d, source, count(*) as n from `tabCRM Lead`
		where creation >= %s and source is not null and source != '' group by d, source""",
		(start,),
		as_dict=True,
	)
	for row in leads:
		day = auto.setdefault(str(row.d), {"fechamentos": 0, "respostas": {}})
		# usa o nome traduzido (ex: Reference -> Indicação) para casar com os canais do painel
		day["respostas"][frappe._(row.source)] = cint(row.n)
	return auto


@frappe.whitelist()
def get_overview(days_back: int = 400):
	_managers_only()
	start = add_days(nowdate(), -cint(days_back))
	rows = frappe.get_all(
		"CRM Prospecao Dia",
		filters={"data": [">=", start]},
		fields=["data", *COUNT_FIELDS, "respostas", "objecoes"],
	)
	days = {}
	for row in rows:
		days[str(row.data)] = {
			**{field: cint(row.get(field)) for field in COUNT_FIELDS},
			"respostas": _json(row.respostas),
			"objecoes": _json(row.objecoes),
		}
	return {"config": _config(), "days": days, "auto": _automatic(start)}


@frappe.whitelist(methods=["POST"])
def save_day(date: str, abordados=0, agendadas=0, realizadas=0, propostas=0, fechamentos=0, respostas=None, objecoes=None):
	_managers_only()
	date = str(getdate(date))
	values = {
		"abordados": cint(abordados),
		"agendadas": cint(agendadas),
		"realizadas": cint(realizadas),
		"propostas": cint(propostas),
		"fechamentos": cint(fechamentos),
		"respostas": json.dumps(_json(respostas), ensure_ascii=False),
		"objecoes": json.dumps(_json(objecoes), ensure_ascii=False),
	}
	if frappe.db.exists("CRM Prospecao Dia", date):
		doc = frappe.get_doc("CRM Prospecao Dia", date)
		doc.update(values)
		doc.save()
	else:
		frappe.get_doc({"doctype": "CRM Prospecao Dia", "data": date, **values}).insert()
	return True


@frappe.whitelist(methods=["POST"])
def save_config(meta_diaria=20, canais=None, objecoes=None):
	_managers_only()
	frappe.db.set_single_value("CRM Prospecao Config", "meta_diaria", cint(meta_diaria) or 20)
	if canais is not None:
		canais = _lines("\n".join(canais) if isinstance(canais, list) else canais)
		frappe.db.set_single_value("CRM Prospecao Config", "canais", "\n".join(canais))
		_ensure_lead_sources(canais)
	if objecoes is not None:
		frappe.db.set_single_value("CRM Prospecao Config", "objecoes", "\n".join(_lines("\n".join(objecoes) if isinstance(objecoes, list) else objecoes)))
	return _config()
