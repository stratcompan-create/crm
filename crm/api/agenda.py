# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Agendamento online: página pública (/agendar) onde a pessoa escolhe um horário livre.
# A reunião vira lead (ou atualiza o que já existe), tarefa para o responsável e e-mail de
# confirmação com o botão "Adicionar ao Google Agenda". Um lembrete sai 24h antes.

import re
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime, nowdate

from crm.api.automacoes import _brand, _first_manager, get_config

SOURCE = "Agendamento online"
MAX_PER_HOUR = 6


def _week_days(cfg) -> set[int]:
	days = {int(x) for x in str(cfg.agenda_dias or "").replace(" ", "").split(",") if x.isdigit()}
	return {d for d in days if 1 <= d <= 7} or {1, 2, 3, 4, 5}


def _hm(value: str, fallback: str) -> tuple[int, int]:
	m = re.match(r"^(\d{1,2}):(\d{2})$", (value or "").strip())
	if not m:
		m = re.match(r"^(\d{1,2}):(\d{2})$", fallback)
	return int(m.group(1)), int(m.group(2))


def _busy(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
	rows = frappe.get_all(
		"CRM Reuniao",
		filters={"status": "Agendada", "inicio": ["<", end], "fim": [">", start]},
		fields=["inicio", "fim"],
	)
	return [(get_datetime(r.inicio), get_datetime(r.fim)) for r in rows]


def _slots_for(day, cfg) -> list[datetime]:
	if day.isoweekday() not in _week_days(cfg):
		return []
	duration = max(10, cint(cfg.agenda_duracao) or 30)
	sh, sm = _hm(cfg.agenda_inicio, "09:00")
	eh, em = _hm(cfg.agenda_fim, "18:00")
	cursor = datetime(day.year, day.month, day.day, sh, sm)
	limit = datetime(day.year, day.month, day.day, eh, em)
	earliest = now_datetime() + timedelta(hours=cint(cfg.agenda_antecedencia))
	busy = _busy(cursor, limit)
	out = []
	while cursor + timedelta(minutes=duration) <= limit:
		end = cursor + timedelta(minutes=duration)
		if cursor >= earliest and not any(b0 < end and b1 > cursor for b0, b1 in busy):
			out.append(cursor)
		cursor = end
	return out


@frappe.whitelist(allow_guest=True)
def get_public_info() -> dict:
	cfg = get_config()
	if not cint(cfg.agenda_ativa):
		return {"ativa": 0}
	ahead = min(60, max(1, cint(cfg.agenda_dias_a_frente) or 14))
	today = get_datetime(nowdate()).date()
	days = []
	for i in range(ahead + 1):
		day = today + timedelta(days=i)
		slots = _slots_for(day, cfg)
		if slots:
			days.append({"data": str(day), "horarios": [s.strftime("%H:%M") for s in slots]})
	return {
		"ativa": 1,
		"marca": _brand(),
		"logo": frappe.db.get_single_value("FCRM Settings", "brand_logo") or "",
		"titulo": cfg.agenda_titulo or "Conversa inicial",
		"duracao": cint(cfg.agenda_duracao) or 30,
		"mensagem": cfg.agenda_mensagem or "",
		"dias": days,
	}


def _rate_limit():
	cache = frappe.cache()
	key = f"agenda_{frappe.local.request_ip}"
	count = cint(cache.get_value(key))
	if count >= MAX_PER_HOUR:
		frappe.throw(_("Muitas tentativas. Tente de novo mais tarde."), frappe.RateLimitExceededError)
	cache.set_value(key, count + 1, expires_in_sec=3600)


@frappe.whitelist(allow_guest=True)
def book(nome: str, email: str, telefone: str, data: str, horario: str, mensagem: str = ""):
	cfg = get_config()
	if not cint(cfg.agenda_ativa):
		frappe.throw(_("O agendamento online não está disponível."))
	_rate_limit()
	nome, email, telefone = (nome or "").strip(), (email or "").strip().lower(), (telefone or "").strip()
	if len(nome) < 2:
		frappe.throw(_("Informe o seu nome."))
	if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
		frappe.throw(_("Informe um e-mail válido."))
	if len(re.sub(r"\D", "", telefone)) < 10:
		frappe.throw(_("Informe um telefone com DDD."))
	try:
		start = datetime.strptime(f"{data} {horario}", "%Y-%m-%d %H:%M")
	except ValueError:
		frappe.throw(_("Horário inválido."))
	if start not in _slots_for(start.date(), cfg):
		frappe.throw(_("Esse horário acabou de ser ocupado. Escolha outro."))
	end = start + timedelta(minutes=max(10, cint(cfg.agenda_duracao) or 30))
	responsavel = cfg.agenda_responsavel or _first_manager()

	lead = _lead_for(nome, email, telefone, responsavel)
	meeting = frappe.get_doc(
		{
			"doctype": "CRM Reuniao",
			"lead": lead,
			"nome": nome,
			"email": email,
			"telefone": telefone,
			"inicio": start,
			"fim": end,
			"status": "Agendada",
			"responsavel": responsavel,
			"observacoes": (mensagem or "").strip()[:500],
		}
	)
	meeting.insert(ignore_permissions=True)
	title = f"{cfg.agenda_titulo or 'Reunião'}: {nome}"
	frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": title,
			"description": (mensagem or "").strip()[:500] or telefone,
			"status": "Todo",
			"priority": "High",
			"assigned_to": responsavel,
			"due_date": start,
			"reference_doctype": "CRM Lead",
			"reference_docname": lead,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "CRM Lead",
			"reference_name": lead,
			"content": f"Reunião agendada online para {start.strftime('%d/%m/%Y às %H:%M')}.",
		}
	).insert(ignore_permissions=True)
	_add_to_calendar(meeting, lead, title, start, end, responsavel)
	if frappe.db.get_value("CRM Lead", lead, "status") == "New" and frappe.db.exists("CRM Lead Status", "Contacted"):
		frappe.db.set_value("CRM Lead", lead, "status", "Contacted")
	_confirm_by_email(meeting, cfg, start, end)
	frappe.db.commit()
	return {"ok": True, "inicio": start.strftime("%d/%m/%Y às %H:%M")}


def _add_to_calendar(meeting, lead, title, start, end, owner):
	"""A reunião também vira evento no Calendário do CRM (o que a pessoa vê no dia a dia)."""
	try:
		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": title,
				"starts_on": start,
				"ends_on": end,
				"event_type": "Public",
				"status": "Open",
				"description": meeting.observacoes or "",
				"event_participants": [
					{"reference_doctype": "CRM Lead", "reference_docname": lead, "email": meeting.email}
				],
			}
		)
		event.insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("Event", event.name, "owner", owner, update_modified=False)
	except Exception:
		frappe.log_error("Agenda: falha ao criar o evento no calendário", frappe.get_traceback())


def _lead_for(nome: str, email: str, telefone: str, responsavel: str) -> str:
	existing = frappe.db.get_value("CRM Lead", {"email": email}) or frappe.db.get_value(
		"CRM Lead", {"mobile_no": telefone}
	)
	if existing:
		return existing
	if not frappe.db.exists("CRM Lead Source", SOURCE):
		frappe.get_doc({"doctype": "CRM Lead Source", "source_name": SOURCE}).insert(ignore_permissions=True)
	first, _sep, last = nome.partition(" ")
	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first,
			"last_name": last,
			"email": email,
			"mobile_no": telefone,
			"source": SOURCE,
			"lead_owner": responsavel,
		}
	)
	lead.insert(ignore_permissions=True)
	return lead.name


def _google_calendar_link(title: str, start: datetime, end: datetime) -> str:
	fmt = "%Y%m%dT%H%M%S"
	from urllib.parse import quote

	return (
		"https://calendar.google.com/calendar/render?action=TEMPLATE"
		f"&text={quote(title)}&dates={start.strftime(fmt)}/{end.strftime(fmt)}&ctz=America/Sao_Paulo"
	)


def _confirm_by_email(meeting, cfg, start, end, reminder: bool = False):
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		return
	title = cfg.agenda_titulo or "Reunião"
	brand = _brand()
	when = start.strftime("%d/%m/%Y às %H:%M")
	first = (meeting.nome or "").split(" ")[0]
	link = f"<p>Link da reunião: <a href='{cfg.agenda_link}'>{cfg.agenda_link}</a></p>" if cfg.agenda_link else ""
	intro = "Lembrete: nossa reunião é amanhã." if reminder else "Sua reunião está confirmada."
	html = (
		f"<div style='font-family:Arial,sans-serif;max-width:520px'>"
		f"<p>Olá, {frappe.utils.escape_html(first)}! {intro}</p>"
		f"<p><b>{frappe.utils.escape_html(title)}</b><br>{when} (horário de Brasília)</p>{link}"
		f"<p><a href='{_google_calendar_link(title + (' — ' + brand if brand else ''), start, end)}'>"
		f"Adicionar ao Google Agenda</a></p>"
		f"<p style='color:#777;font-size:13px'>{frappe.utils.escape_html(brand)}</p></div>"
	)
	frappe.sendmail(
		recipients=[meeting.email],
		subject=("Lembrete: " if reminder else "Reunião confirmada: ") + f"{title} em {when}",
		message=html,
		delayed=False,
	)


def send_meeting_reminders():
	"""Job de hora em hora: avisa quem tem reunião nas próximas 24h."""
	now = now_datetime()
	cfg = get_config()
	for r in frappe.get_all(
		"CRM Reuniao",
		filters={"status": "Agendada", "lembrete_enviado": 0, "inicio": ["between", [now, now + timedelta(hours=24)]]},
		pluck="name",
	):
		m = frappe.get_doc("CRM Reuniao", r)
		try:
			if m.email:
				_confirm_by_email(m, cfg, get_datetime(m.inicio), get_datetime(m.fim), reminder=True)
			frappe.db.set_value("CRM Reuniao", r, "lembrete_enviado", 1, update_modified=False)
		except Exception:
			frappe.log_error("Agenda: falha no lembrete", frappe.get_traceback())
	frappe.db.commit()
