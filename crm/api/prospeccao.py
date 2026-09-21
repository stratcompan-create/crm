# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt

import glob
import json
import os

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
		where st.type = 'Won' and deal.closed_date >= %s and ifnull(deal.lancamento_antigo, 0) = 0
		group by deal.closed_date""",
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
	def bump(day, key, n):
		auto.setdefault(str(day), {"fechamentos": 0, "respostas": {}})[key] = cint(n)

	# reuniões marcadas (no dia em que foram marcadas) e realizadas (no dia em que aconteceram)
	for row in frappe.db.sql(
		"""select date(creation) as d, count(*) as n from `tabCRM Reuniao`
		where creation >= %s and status != 'Cancelada' group by d""",
		(start,),
		as_dict=True,
	):
		bump(row.d, "agendadas", row.n)
	for row in frappe.db.sql(
		"""select date(inicio) as d, count(*) as n from `tabCRM Reuniao`
		where inicio >= %s and status = 'Realizada' group by d""",
		(start,),
		as_dict=True,
	):
		bump(row.d, "realizadas", row.n)
	# propostas enviadas (um PDF de proposta por negócio a cada dia)
	for row in frappe.db.sql(
		"""select date(creation) as d, count(distinct attached_to_name) as n from `tabFile`
		where attached_to_doctype = 'CRM Deal' and file_name like 'Proposta Comercial%%' and creation >= %s group by d""",
		(start,),
		as_dict=True,
	):
		bump(row.d, "propostas", row.n)
	# abordagens registradas pelo botão "Nova abordagem"
	for row in frappe.db.sql(
		"""select date(abordado_em) as d, count(*) as n from `tabCRM Lead`
		where abordado_em >= %s group by d""",
		(start,),
		as_dict=True,
	):
		bump(row.d, "abordados", row.n)
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


def _week_bounds(ref=None):
	ref = getdate(ref or nowdate())
	monday = add_days(ref, -ref.weekday())
	return getdate(monday), getdate(add_days(monday, 6))


def _effective_days(start, end) -> dict:
	"""Dia a dia: o que foi registrado ou o que o CRM já sabia sozinho (o maior)."""
	canais = _config()["canais"]
	rows = frappe.get_all(
		"CRM Prospecao Dia",
		filters={"data": ["between", [start, end]]},
		fields=["data", *COUNT_FIELDS, "respostas", "objecoes"],
	)
	manual = {str(r.data): r for r in rows}
	auto = _automatic(start)

	out, day = {}, getdate(start)
	while day <= getdate(end):
		key = str(day)
		m = manual.get(key)
		a = auto.get(key, {})
		respostas = dict(_json(m.respostas)) if m else {}
		for canal, n in (a.get("respostas") or {}).items():
			if canal in canais:
				respostas[canal] = max(cint(respostas.get(canal)), n)
		out[key] = {
			**{field: cint(m.get(field)) if m else 0 for field in COUNT_FIELDS},
			"respostas": respostas,
			"objecoes": _json(m.objecoes) if m else {},
		}
		for field in COUNT_FIELDS:
			out[key][field] = max(out[key][field], cint(a.get(field)))
		day = getdate(add_days(day, 1))
	return out


def _clean(text) -> str:
	return str(text).replace(",", " ").replace("\n", " ")


def _build_csv(days: dict) -> str:
	"""Mesmo formato que a skill do relatório semanal lê (FUNIL DIARIO / RESPOSTAS / OBJECOES)."""
	active = [
		k
		for k in sorted(days)
		if any(days[k][f] for f in COUNT_FIELDS) or days[k]["respostas"] or days[k]["objecoes"]
	]
	out = "FUNIL DIARIO\nData,abordados,agendadas,realizadas,propostas,fechamentos\n"
	for k in active:
		out += k + "," + ",".join(str(days[k][f]) for f in COUNT_FIELDS) + "\n"
	out += "\nRESPOSTAS POSITIVAS POR FONTE\nData,Fonte,Quantidade\n"
	for k in active:
		for canal in sorted(days[k]["respostas"]):
			if days[k]["respostas"][canal] > 0:
				out += f"{k},{_clean(canal)},{days[k]['respostas'][canal]}\n"
	out += "\nOBJECOES\nData,Tipo\n"
	for k in active:
		for tipo in sorted(days[k]["objecoes"]):
			out += "".join(f"{k},{_clean(tipo)}\n" for _ in range(cint(days[k]["objecoes"][tipo])))
	return out


def _ensure_folder(name: str) -> str:
	path = f"Home/{name}"
	if not frappe.db.exists("File", path):
		frappe.get_doc(
			{"doctype": "File", "file_name": name, "is_folder": 1, "folder": "Home"}
		).insert(ignore_permissions=True)
	return path


@frappe.whitelist(methods=["POST"])
def save_weekly_report(week_start=None):
	"""Gera o CSV da semana (mais a anterior, para o comparativo) e guarda em Arquivos > Prospecção."""
	_managers_only()
	monday, sunday = _week_bounds(week_start)
	previous_monday = getdate(add_days(monday, -7))
	csv_text = _build_csv(_effective_days(previous_monday, sunday))

	folder = _ensure_folder("Prospecção")
	file_name = f"prospeccao_semana_{monday}_a_{sunday}.csv"
	# Substitui o relatório da mesma semana (o Frappe põe um sufixo aleatório se o nome já existir).
	base = file_name.rsplit(".", 1)[0]
	for old in frappe.get_all("File", filters={"folder": folder, "file_name": ["like", f"{base}%"]}, pluck="name"):
		frappe.delete_doc("File", old, ignore_permissions=True, force=True)
	# o Frappe não apaga o arquivo físico junto com o registro; sobrando um com o mesmo nome,
	# o novo ganharia um sufixo aleatório
	for stale in glob.glob(frappe.get_site_path("private", "files", f"{base}*.csv")):
		os.remove(stale)
	# Criado direto (o helper save_file do Frappe grava duas vezes e acrescenta um sufixo ao nome)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"folder": folder,
			"is_private": 1,
			"content": csv_text.encode("utf-8"),
		}
	)
	file_doc.insert(ignore_permissions=True)
	return {
		"file_name": file_name,
		"file_url": file_doc.file_url,
		"folder": "Prospecção",
		"semana": [str(monday), str(sunday)],
		"content": csv_text,
	}
