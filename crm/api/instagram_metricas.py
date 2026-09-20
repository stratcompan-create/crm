# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Métricas do Instagram (alcance, visualizações, visitas, interações, seguidores e
# desempenho dos posts), lidas da mesma conexão usada para as mensagens.

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import time

import requests

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

from crm.api.instagram import GRAPH_BASE, TIMEOUT, _get_settings, _managers_only

CACHE_MINUTES = 30
PERIODS = (7, 14, 30)
TOTAL_METRICS = (
	"reach,views,profile_views,accounts_engaged,total_interactions,likes,comments,shares,saves,website_clicks"
)
MEDIA_METRICS = "reach,views,likes,comments,shares,saved,total_interactions"
MEDIA_METRICS_BASIC = "reach,likes,comments,shares,saved"
POSTS_LIMIT = 12


class InstagramAPIError(Exception):
	def __init__(self, message: str, code: int | None = None):
		super().__init__(message)
		self.code = code


def _token() -> str:
	settings = _get_settings()
	token = settings.get_password("access_token", raise_exception=False)
	if not settings.enabled or not token:
		frappe.throw(_("Conecte o Instagram em Configurações → Instagram para ver as métricas."))
	return token


def _get(path: str, token: str, **params):
	params["access_token"] = token
	resp = requests.get(f"{GRAPH_BASE}{path}", params=params, timeout=TIMEOUT)
	try:
		data = resp.json()
	except ValueError:
		data = {}
	if resp.status_code >= 400 or (isinstance(data, dict) and "error" in data):
		err = data.get("error", {}) if isinstance(data, dict) else {}
		raise InstagramAPIError(err.get("message", resp.text[:200]), err.get("code"))
	return data


def _friendly(exc: InstagramAPIError) -> str:
	if exc.code == 190:
		return _("O token do Instagram venceu ou foi recusado. Gere um novo em Configurações → Instagram.")
	if exc.code in (10, 200, 3):
		return _("O token não tem a permissão de métricas. Gere um novo token no painel da Meta e cole em Configurações → Instagram.")
	return _("O Instagram não devolveu as métricas agora. Tente de novo em alguns minutos.")


# ------------------------------------------------------------------ blocos

def _totals(token: str, since: int, until: int) -> dict:
	data = _get(
		"/me/insights", token, metric=TOTAL_METRICS, period="day", metric_type="total_value", since=since, until=until
	)
	return {m["name"]: (m.get("total_value") or {}).get("value", 0) for m in data.get("data", [])}


def _reach_series(token: str, since: int, until: int) -> list[dict]:
	data = _get("/me/insights", token, metric="reach", period="day", since=since, until=until)
	values = (data.get("data") or [{}])[0].get("values", [])
	out = []
	for v in values:
		# o "end_time" é o fim do dia (fuso da Meta): o dia medido é o anterior
		end = datetime.strptime(v["end_time"][:10], "%Y-%m-%d") - timedelta(days=1)
		out.append({"date": end.strftime("%Y-%m-%d"), "value": v.get("value", 0)})
	return out


def _media_insights(token: str, media_id: str) -> dict:
	for metrics in (MEDIA_METRICS, MEDIA_METRICS_BASIC):
		try:
			data = _get(f"/{media_id}/insights", token, metric=metrics)
			return {m["name"]: (m.get("values") or [{}])[0].get("value", 0) for m in data.get("data", [])}
		except InstagramAPIError:
			continue
	return {}


def _type_label(media: dict) -> str:
	if media.get("media_product_type") == "REELS":
		return "Reel"
	kind = media.get("media_type")
	if kind == "CAROUSEL_ALBUM":
		return "Carrossel"
	if kind == "VIDEO":
		return "Vídeo"
	return "Foto"


def _posts(token: str) -> list[dict]:
	data = _get(
		"/me/media",
		token,
		fields="id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp,like_count,comments_count",
		limit=POSTS_LIMIT,
	)
	items = data.get("data", [])[:POSTS_LIMIT]
	with ThreadPoolExecutor(max_workers=6) as pool:
		insights = list(pool.map(lambda m: _media_insights(token, m["id"]), items))

	posts = []
	for media, ins in zip(items, insights):
		reach = ins.get("reach", 0) or 0
		interactions = ins.get("total_interactions")
		if interactions is None:
			interactions = sum(ins.get(k, 0) or 0 for k in ("likes", "comments", "shares", "saved"))
		caption = (media.get("caption") or "").strip().replace("\n", " ")
		posts.append(
			{
				"id": media["id"],
				"tipo": _type_label(media),
				"data": (media.get("timestamp") or "")[:10],
				"legenda": caption[:110],
				"link": media.get("permalink"),
				"imagem": media.get("thumbnail_url") or media.get("media_url") or "",
				"alcance": reach,
				"visualizacoes": ins.get("views", 0) or 0,
				"curtidas": ins.get("likes", media.get("like_count", 0)) or 0,
				"comentarios": ins.get("comments", media.get("comments_count", 0)) or 0,
				"salvos": ins.get("saved", 0) or 0,
				"compartilhamentos": ins.get("shares", 0) or 0,
				"interacoes": interactions or 0,
				"taxa": round((interactions or 0) / reach * 100, 1) if reach else 0,
			}
		)
	return posts


# ------------------------------------------------------------------ seguidores (histórico próprio)

def _save_snapshot(followers: int):
	today = nowdate()
	if frappe.db.exists("CRM Instagram Snapshot", today):
		frappe.db.set_value("CRM Instagram Snapshot", today, "seguidores", followers)
	else:
		frappe.get_doc({"doctype": "CRM Instagram Snapshot", "data": today, "seguidores": followers}).insert(
			ignore_permissions=True
		)


def _followers_delta(days: int, current: int) -> dict:
	limit = add_days(nowdate(), -days)
	rows = frappe.get_all(
		"CRM Instagram Snapshot",
		filters={"data": [">=", limit], "seguidores": ["is", "set"]},
		fields=["data", "seguidores"],
		order_by="data asc",
		limit=1,
	)
	if not rows or str(rows[0].data) >= nowdate():
		return {"delta": None, "desde": None}
	return {"delta": current - rows[0].seguidores, "desde": str(rows[0].data)}


def daily_snapshot():
	"""Job diário: guarda o número de seguidores para mostrar o crescimento depois."""
	settings = _get_settings()
	token = settings.get_password("access_token", raise_exception=False)
	if not settings.enabled or not token:
		return
	try:
		me = _get("/me", token, fields="followers_count")
		_save_snapshot(int(me.get("followers_count") or 0))
		frappe.db.commit()
	except Exception:
		frappe.log_error("Instagram: falha ao guardar o número de seguidores", frappe.get_traceback())


# ------------------------------------------------------------------ CRM

def _crm_numbers(days: int) -> dict:
	start = f"{add_days(nowdate(), -days)} 00:00:00"
	leads = frappe.db.count("CRM Lead", {"source": "Instagram", "creation": [">=", start]})
	received = frappe.db.count("CRM Instagram Message", {"direction": "Received", "timestamp": [">=", start]})
	conversas = frappe.db.sql(
		"""select count(distinct lead) from `tabCRM Instagram Message`
		where direction = 'Received' and timestamp >= %s""",
		(start,),
	)[0][0]
	return {"leads_novos": leads, "mensagens_recebidas": received, "conversas": conversas}


# ------------------------------------------------------------------ API

@frappe.whitelist()
def get_insights(days: int = 30, refresh: int = 0) -> dict:
	_managers_only()
	days = int(days)
	if days not in PERIODS:
		days = 30

	key = f"ig_insights:{days}"
	if not int(refresh):
		cached = frappe.cache().get_value(key)
		if cached:
			cached["crm"] = _crm_numbers(days)
			return cached

	token = _token()
	now = int(time.time())
	since = now - days * 86400
	try:
		me = _get(
			"/me", token, fields="username,name,account_type,followers_count,follows_count,media_count"
		)
		current = _totals(token, since, now)
		previous = _totals(token, since - days * 86400, since)
		series = _reach_series(token, since, now)
		posts = _posts(token)
	except InstagramAPIError as exc:
		frappe.log_error("Instagram: falha ao buscar métricas", f"{exc.code}: {exc}")
		frappe.throw(_friendly(exc))

	followers = int(me.get("followers_count") or 0)
	_save_snapshot(followers)
	frappe.db.commit()

	result = {
		"dias": days,
		"perfil": {
			"usuario": me.get("username"),
			"nome": me.get("name"),
			"seguidores": followers,
			"seguindo": me.get("follows_count"),
			"publicacoes": me.get("media_count"),
		},
		"seguidores_variacao": _followers_delta(days, followers),
		"atual": current,
		"anterior": previous,
		"serie_alcance": series,
		"posts": posts,
		"atualizado_em": frappe.utils.now(),
	}
	frappe.cache().set_value(key, {k: v for k, v in result.items()}, expires_in_sec=CACHE_MINUTES * 60)
	result["crm"] = _crm_numbers(days)
	return result
