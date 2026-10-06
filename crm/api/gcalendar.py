# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Integração com o Google Agenda (Calendar). Reaproveita o mesmo app OAuth do Google
# Drive (gdrive_client_id/gdrive_client_secret na configuração do servidor) com um
# escopo próprio e mais restrito - só eventos e disponibilidade, nunca o calendário
# inteiro. Cada site guarda apenas o token do próprio escritório.
#
# Duas coisas usam essa conexão (ambas em crm.api.agenda, best-effort - se a conta
# não estiver conectada, ou a chamada ao Google falhar, o agendamento continua
# funcionando normalmente, só sem o cruzamento com o Google Agenda):
#   - obter_ocupado(): soma os horários já ocupados no Google Agenda aos horários
#     indisponíveis para marcar pelo /agendar (evita marcar em cima de um
#     compromisso que só existe no Google, não no CRM);
#   - criar_evento(): ao confirmar uma reunião pelo /agendar, cria o evento também
#     no Google Agenda de verdade (não só no calendário interno do CRM).

import json
import secrets
from datetime import datetime
from urllib.parse import urlencode

import requests

import frappe
from frappe import _
from frappe.utils import cint, get_datetime

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_URL = "https://www.googleapis.com/calendar/v3"
SCOPES = (
	"openid email "
	"https://www.googleapis.com/auth/calendar.events "
	"https://www.googleapis.com/auth/calendar.freebusy"
)
DOCTYPE = "CRM Google Calendar"
TIMEOUT = 30


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _config() -> dict:
	# mesmo app OAuth do Google Drive - um só cadastro no Google Cloud pro
	# escritório, não dois. Ver crm.api.gdrive._config().
	client_id = frappe.conf.get("gdrive_client_id")
	secret = frappe.conf.get("gdrive_client_secret")
	if not client_id or not secret:
		frappe.throw(_("O Google Agenda ainda não foi habilitado neste servidor. Fale com o suporte."))
	redirect = frappe.conf.get("gcal_redirect_uri") or (
		frappe.utils.get_url() + "/api/method/crm.api.gcalendar.callback"
	)
	return {"client_id": client_id, "client_secret": secret, "redirect_uri": redirect}


def _settings():
	return frappe.get_single(DOCTYPE)


def _configured() -> bool:
	return bool(frappe.conf.get("gdrive_client_id") and frappe.conf.get("gdrive_client_secret"))


# ------------------------------------------------------------------ conexão

@frappe.whitelist()
def get_status() -> dict:
	"""Estado da conexão. Qualquer usuário do CRM pode consultar (não expõe token)."""
	s = _settings()
	return {
		"habilitado": _configured(),
		"conectado": bool(s.conectado),
		"email": s.email or "",
		"criar_eventos": bool(s.criar_eventos),
		"bloquear_ocupado": bool(s.bloquear_ocupado),
	}


@frappe.whitelist()
def start_auth() -> dict:
	_managers_only()
	cfg = _config()
	state = secrets.token_urlsafe(24)
	frappe.cache().set_value(
		f"gcal_state:{state}", {"user": frappe.session.user}, expires_in_sec=600
	)
	params = {
		"client_id": cfg["client_id"],
		"redirect_uri": cfg["redirect_uri"],
		"response_type": "code",
		"scope": SCOPES,
		"access_type": "offline",
		"prompt": "consent",
		"state": state,
	}
	return {"url": f"{AUTH_URL}?{urlencode(params)}"}


@frappe.whitelist(allow_guest=True)
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
	"""Volta do Google. A identidade vem do `state` (aleatório, de uso único e válido por 10 minutos)."""
	destino_ok = "/crm?gcal=ok"
	destino_erro = "/crm?gcal=erro"

	def ir(url):
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = url

	if error or not code or not state:
		return ir(destino_erro)

	key = f"gcal_state:{state}"
	info = frappe.cache().get_value(key)
	if not info:
		return ir(destino_erro)
	frappe.cache().delete_value(key)

	try:
		cfg = _config()
		resp = requests.post(
			TOKEN_URL,
			data={
				"code": code,
				"client_id": cfg["client_id"],
				"client_secret": cfg["client_secret"],
				"redirect_uri": cfg["redirect_uri"],
				"grant_type": "authorization_code",
			},
			timeout=TIMEOUT,
		)
		tokens = resp.json()
		if resp.status_code != 200 or not tokens.get("refresh_token"):
			frappe.log_error("Google Agenda: falha na troca do código", json.dumps({k: v for k, v in tokens.items() if "token" not in k}))
			return ir(destino_erro)

		email = ""
		try:
			info_resp = requests.get(
				"https://openidconnect.googleapis.com/v1/userinfo",
				headers={"Authorization": f"Bearer {tokens['access_token']}"},
				timeout=TIMEOUT,
			)
			email = info_resp.json().get("email", "")
		except Exception:
			pass

		previous_user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			doc = _settings()
			doc.conectado = 1
			doc.email = email
			doc.refresh_token = tokens["refresh_token"]
			doc.calendario_id = doc.calendario_id or "primary"
			doc.flags.ignore_permissions = True
			doc.save()
			frappe.db.commit()
		finally:
			frappe.set_user(previous_user)
		frappe.cache().delete_value("gcal_access_token")
		return ir(destino_ok)
	except Exception:
		frappe.log_error("Google Agenda: falha ao conectar", frappe.get_traceback())
		return ir(destino_erro)


@frappe.whitelist()
def disconnect():
	_managers_only()
	doc = _settings()
	token = doc.get_password("refresh_token", raise_exception=False)
	if token:
		try:
			requests.post(REVOKE_URL, params={"token": token}, timeout=TIMEOUT)
		except Exception:
			pass
	doc.conectado = 0
	doc.email = ""
	doc.refresh_token = ""
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.cache().delete_value("gcal_access_token")
	return {"ok": True}


@frappe.whitelist()
def save_options(criar_eventos=None, bloquear_ocupado=None):
	_managers_only()
	doc = _settings()
	if criar_eventos is not None:
		doc.criar_eventos = cint(criar_eventos)
	if bloquear_ocupado is not None:
		doc.bloquear_ocupado = cint(bloquear_ocupado)
	doc.flags.ignore_permissions = True
	doc.save()
	return {"ok": True}


# ------------------------------------------------------------------ Google API

def _access_token() -> str:
	cached = frappe.cache().get_value("gcal_access_token")
	if cached:
		return cached
	doc = _settings()
	if not doc.conectado:
		frappe.throw(_("O Google Agenda não está conectado. Conecte em Configurações → Integrações."))
	refresh = doc.get_password("refresh_token", raise_exception=False)
	cfg = _config()
	resp = requests.post(
		TOKEN_URL,
		data={
			"client_id": cfg["client_id"],
			"client_secret": cfg["client_secret"],
			"refresh_token": refresh,
			"grant_type": "refresh_token",
		},
		timeout=TIMEOUT,
	)
	data = resp.json()
	if resp.status_code != 200 or not data.get("access_token"):
		if data.get("error") == "invalid_grant":
			frappe.db.set_single_value(DOCTYPE, "conectado", 0)
			frappe.db.commit()
			frappe.throw(_("A conexão com o Google Agenda expirou. Conecte de novo em Configurações → Integrações."))
		frappe.throw(_("Não foi possível falar com o Google Agenda agora."))
	frappe.cache().set_value(
		"gcal_access_token", data["access_token"], expires_in_sec=max(60, cint(data.get("expires_in", 3600)) - 120)
	)
	return data["access_token"]


def _headers() -> dict:
	return {"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"}


def _call(method: str, url: str, **kwargs):
	resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kwargs)
	if resp.status_code == 401:
		# token vencido antes do previsto: renova uma vez
		frappe.cache().delete_value("gcal_access_token")
		resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kwargs)
	if resp.status_code >= 400:
		frappe.log_error("Google Agenda: erro na API", f"{method} {url}\n{resp.text[:1500]}")
		frappe.throw(_("O Google Agenda recusou a operação."))
	return resp.json()


def _iso(dt: datetime) -> str:
	return dt.strftime("%Y-%m-%dT%H:%M:%S")


def obter_ocupado(inicio: datetime, fim: datetime) -> list[tuple[datetime, datetime]]:
	"""Períodos ocupados no Google Agenda conectado, dentro da janela pedida.

	Nunca lança exceção: se não estiver conectado, a opção estiver desligada, ou o
	Google não responder, devolve lista vazia (o agendamento simplesmente não
	cruza com o Google Agenda nessa tentativa, em vez de quebrar a página pública)."""
	try:
		doc = _settings()
		if not doc.conectado or not cint(doc.bloquear_ocupado):
			return []
		body = {
			"timeMin": _iso(inicio) + "Z",
			"timeMax": _iso(fim) + "Z",
			"items": [{"id": doc.calendario_id or "primary"}],
		}
		data = _call("POST", f"{CALENDAR_URL}/freeBusy", json=body)
		busy = data.get("calendars", {}).get(doc.calendario_id or "primary", {}).get("busy", [])
		out = []
		for b in busy:
			try:
				out.append((get_datetime(b["start"].replace("Z", "")), get_datetime(b["end"].replace("Z", ""))))
			except Exception:
				continue
		return out
	except Exception:
		frappe.log_error("Google Agenda: falha ao consultar disponibilidade", frappe.get_traceback())
		return []


def criar_evento(titulo: str, inicio: datetime, fim: datetime, descricao: str = "", convidado_email: str = "") -> None:
	"""Cria o evento no Google Agenda conectado. Nunca lança exceção - best-effort,
	igual ao evento interno do CRM (ver crm.api.agenda._add_to_calendar): se o Google
	recusar ou a conta não estiver conectada, a reunião já confirmada no CRM continua
	valendo, só não aparece no Google Agenda do escritório."""
	try:
		doc = _settings()
		if not doc.conectado or not cint(doc.criar_eventos):
			return
		body = {
			"summary": titulo,
			"description": descricao or "",
			"start": {"dateTime": _iso(inicio), "timeZone": "America/Sao_Paulo"},
			"end": {"dateTime": _iso(fim), "timeZone": "America/Sao_Paulo"},
		}
		if convidado_email:
			body["attendees"] = [{"email": convidado_email}]
		_call(
			"POST",
			f"{CALENDAR_URL}/calendars/{doc.calendario_id or 'primary'}/events",
			json=body,
		)
	except Exception:
		frappe.log_error("Google Agenda: falha ao criar evento", frappe.get_traceback())
