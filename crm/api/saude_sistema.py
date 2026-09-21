# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Saúde do sistema: confere de hora em hora se as automações estão funcionando (agendador, e-mails,
# Drive, Instagram, backups, disco) e avisa o gestor por e-mail quando algo dá errado.
# Hoje as falhas só apareciam se alguém fosse procurar nos registros.

import os
import shutil
from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, nowdate

# erros de ruído que não pedem ação (registrados pelo próprio Frappe em situações normais)
IGNORED_ERROR_PREFIXES = ("frappe.core.doctype.user.user.create_contact",)
LAST_SIG = "crm_health_last_sig"
LAST_SENT = "crm_health_last_sent"
LAST_CHECK = "crm_health_last_check"


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _check_errors(since) -> tuple[bool, str]:
	rows = frappe.get_all("Error Log", filters={"creation": [">=", since]}, fields=["method", "creation"], limit=200)
	rows = [r for r in rows if not (r.method or "").startswith(IGNORED_ERROR_PREFIXES)]
	if not rows:
		return True, "Nenhum erro nas últimas horas."
	counts: dict = {}
	for r in rows:
		key = (r.method or "erro sem título")[:70]
		counts[key] = counts.get(key, 0) + 1
	top = ", ".join(f"{k} ({n}x)" for k, n in sorted(counts.items(), key=lambda x: -x[1])[:3])
	return False, f"{len(rows)} erro(s) registrados: {top}"


def _check_scheduler() -> tuple[bool, str]:
	last = frappe.db.sql("select max(creation) from `tabScheduled Job Log`")[0][0]
	if not last:
		return False, "O agendador nunca rodou."
	minutes = (now_datetime() - get_datetime(last)).total_seconds() / 60
	if minutes > 45:
		return False, f"O agendador parou há {int(minutes)} minutos."
	return True, "Agendador rodando."


def _check_email() -> tuple[bool, str]:
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		return False, "Nenhuma conta de e-mail de envio configurada."
	failed = frappe.db.count("Email Queue", {"status": "Error", "creation": [">=", add_days(nowdate(), -1)]})
	stuck = frappe.db.count(
		"Email Queue", {"status": "Not Sent", "creation": ["<", now_datetime() - timedelta(minutes=45)]}
	)
	if failed or stuck:
		return False, f"E-mails com problema: {failed} com erro e {stuck} parados na fila."
	return True, "E-mails saindo normalmente."


def _check_drive() -> tuple[bool, str]:
	try:
		s = frappe.get_single("CRM Google Drive")
	except Exception:
		return True, "Google Drive não usado."
	if s.get("conectado"):
		return True, "Google Drive conectado."
	if s.get("email") or s.get("pasta_nome"):
		return False, "O Google Drive foi desconectado. Conecte de novo em Configurações → Google Drive."
	return True, "Google Drive não conectado (opcional)."


def _check_instagram() -> tuple[bool, str]:
	s = frappe.get_single("CRM Instagram Settings")
	if not s.get("enabled"):
		return True, "Instagram desligado (opcional)."
	if not s.get_password("access_token", raise_exception=False):
		return False, "Instagram ligado, mas sem token."
	if s.get("token_expires_on"):
		days = (getdate(s.token_expires_on) - getdate(nowdate())).days
		if days < 10:
			return False, f"O token do Instagram vence em {days} dia(s). Gere um novo token."
	return True, "Instagram conectado."


def _check_backup() -> tuple[bool, str]:
	folder = frappe.get_site_path("private", "backups")
	if not os.path.isdir(folder):
		return False, "Nenhum backup encontrado."
	newest = max((os.path.getmtime(os.path.join(folder, f)) for f in os.listdir(folder)), default=0)
	if not newest:
		return False, "Nenhum backup encontrado."
	hours = (now_datetime().timestamp() - newest) / 3600
	if hours > 30:
		return False, f"O último backup tem {int(hours)} horas."
	return True, "Backup em dia."


def _check_disk() -> tuple[bool, str]:
	usage = shutil.disk_usage(frappe.get_site_path())
	free = usage.free / usage.total * 100
	if free < 15:
		return False, f"Pouco espaço em disco: {free:.0f}% livre."
	return True, f"Disco com {free:.0f}% livre."


def _check_weekly() -> tuple[bool, str]:
	from crm.api.automacoes import _week_bounds, get_config

	if not cint(get_config().relatorio_ativo):
		return True, "Resumo semanal desligado."
	start, _end = _week_bounds()
	if frappe.db.exists("CRM Relatorio Semanal", {"inicio": start}):
		return True, "Resumo semanal em dia."
	now = now_datetime()
	if now.weekday() == 0 and now.hour < 10:
		return True, "Resumo semanal em dia (sai às 8h de segunda)."
	return False, "O resumo semanal da semana passada não foi gerado."


def run_checks(since: str | None = None) -> list[dict]:
	since = since or frappe.db.get_default(LAST_CHECK) or str(now_datetime() - timedelta(hours=2))
	checks = [
		("erros", "Erros do sistema", lambda: _check_errors(since)),
		("agendador", "Agendador de tarefas", _check_scheduler),
		("email", "Envio de e-mails", _check_email),
		("drive", "Google Drive", _check_drive),
		("instagram", "Instagram", _check_instagram),
		("backup", "Backup", _check_backup),
		("disco", "Espaço em disco", _check_disk),
		("resumo", "Resumo semanal", _check_weekly),
	]
	out = []
	for key, label, fn in checks:
		try:
			ok, msg = fn()
		except Exception as e:
			ok, msg = False, f"Não foi possível verificar: {str(e)[:120]}"
		out.append({"key": key, "label": label, "ok": bool(ok), "mensagem": msg})
	return out


@frappe.whitelist()
def get_system_health() -> dict:
	_managers_only()
	# na tela mostramos as últimas 24h de erros, não só desde a última checagem
	items = run_checks(str(now_datetime() - timedelta(hours=24)))
	return {"itens": items, "ok": all(i["ok"] for i in items), "verificado_em": str(now_datetime())}


def check_and_alert():
	"""Job de hora em hora. Avisa por e-mail quando aparece um problema novo (no máximo 1 aviso por dia
	para o mesmo problema) e quando tudo volta ao normal."""
	items = run_checks()
	frappe.db.set_default(LAST_CHECK, str(now_datetime()))
	problems = [i for i in items if not i["ok"]]
	signature = "|".join(sorted(i["key"] for i in problems))
	last_sig = frappe.db.get_default(LAST_SIG) or ""
	last_sent = frappe.db.get_default(LAST_SENT) or ""
	# "voltou ao normal" só vale para problemas que persistem (erros pontuais não têm "volta")
	persistent = [k for k in signature.split("|") if k and k != "erros"]
	last_persistent = [k for k in last_sig.split("|") if k and k != "erros"]
	recovered = bool(last_persistent) and not persistent
	stale = last_sent and (now_datetime() - get_datetime(last_sent)) > timedelta(hours=24)
	if problems and (signature != last_sig or stale):
		_send(problems, recovered=False)
	elif recovered:
		_send([], recovered=True)
	frappe.db.set_default(LAST_SIG, signature)
	frappe.db.commit()


def _send(problems: list[dict], recovered: bool):
	from crm.api.automacoes import _brand, _report_recipients, get_config

	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		return
	recipients = _report_recipients(get_config())
	if not recipients:
		return
	brand = _brand() or "CRM"
	if recovered:
		subject, body = f"{brand}: tudo voltou ao normal", "<p>Os problemas avisados antes foram resolvidos. Tudo está funcionando.</p>"
	else:
		subject = f"{brand}: atenção — {len(problems)} ponto(s) com problema"
		rows = "".join(
			f"<li style='margin-bottom:6px'><b>{frappe.utils.escape_html(p['label'])}:</b> {frappe.utils.escape_html(p['mensagem'])}</li>"
			for p in problems
		)
		body = (
			"<div style='font-family:Arial,sans-serif;max-width:560px'>"
			"<p>O CRM detectou algo que precisa de atenção:</p>"
			f"<ul>{rows}</ul>"
			"<p style='color:#777;font-size:13px'>Você recebe este aviso quando surge um problema novo e, se ele continuar, uma vez por dia.</p></div>"
		)
	frappe.sendmail(recipients=recipients, subject=subject, message=body, delayed=False)
	frappe.db.set_default(LAST_SENT, str(now_datetime()))
