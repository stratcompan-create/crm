# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# WhatsApp pela API oficial, via YCloud (parceira credenciada da Meta), em modo
# coexistência: o mesmo número continua no app WhatsApp Business do celular e passa a
# aparecer aqui no CRM.
#
# Não depende do app `whatsapp` do Frappe (que não está instalado em produção): as
# conversas ficam em CRM WhatsApp Contato (uma por telefone) e CRM WhatsApp Mensagem.
#
# Configuração do servidor (site_config, nunca no navegador):
#   ycloud_api_key         chave da API (painel da YCloud)
#   ycloud_webhook_secret  segredo do webhook (gravado sozinho por configurar_webhook)
#   ycloud_numero          número conectado em E.164 (descoberto sozinho se faltar)
#
# Webhook: https://<site>/api/method/crm.api.ycloud.webhook
#
# Como o número também é usado para conversas pessoais, ninguém vira lead sozinho:
# quem já é lead (mesmo telefone) é ligado automaticamente; o resto aparece na caixa de
# entrada com o botão "Criar lead", e conversas marcadas como pessoais ficam escondidas.

import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.installer import update_site_config
from frappe.utils import cint, now_datetime

API = "https://api.ycloud.com/v2"
TIMEOUT = 30
CONTATO = "CRM WhatsApp Contato"
MENSAGEM = "CRM WhatsApp Mensagem"
ORIGEM = "WhatsApp"
MAX_MIDIA = 16 * 1024 * 1024
EVENTOS = (
	"whatsapp.inbound_message.received",
	"whatsapp.message.updated",
	"whatsapp.smb.message.echoes",
	"whatsapp.smb.message.created",
)
# duas mensagens quase juntas disputam a mesma conversa no banco: tenta de novo antes de desistir
TENTATIVAS = 4
ROTULO_MIDIA = {
	"image": "📷 Foto",
	"audio": "🎤 Áudio",
	"video": "🎬 Vídeo",
	"document": "📄 Documento",
	"sticker": "Figurinha",
}
# erros da Meta quando a janela de 24h já fechou
ERROS_JANELA = ("131047", "131026", "re-engagement")


# ------------------------------------------------------------------ utilidades

def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _chave() -> str:
	return frappe.conf.get("ycloud_api_key") or ""


def _headers() -> dict:
	return {"X-API-Key": _chave(), "Content-Type": "application/json"}


def _digitos(valor) -> str:
	return re.sub(r"\D", "", str(valor or ""))


def _variantes(telefone: str) -> set[str]:
	"""O mesmo celular brasileiro pode aparecer com ou sem o 9 e com ou sem o 55."""
	d = _digitos(telefone)
	if not d:
		return set()
	if len(d) in (10, 11) and not d.startswith("55"):
		d = "55" + d
	out = {d}
	if d.startswith("55"):
		if len(d) == 12:  # 55 + DDD + 8 dígitos: acrescenta o 9
			out.add(d[:4] + "9" + d[4:])
		elif len(d) == 13 and d[4] == "9":  # tira o 9
			out.add(d[:4] + d[5:])
	return out


def _mesmo_telefone(a: str, b: str) -> bool:
	return bool(_variantes(a) & _variantes(b))


def _numero() -> str:
	"""Número conectado na YCloud, em E.164. Guardado no site_config depois da 1a consulta."""
	numero = frappe.conf.get("ycloud_numero")
	if numero:
		return numero
	if not _chave():
		return ""
	try:
		r = requests.get(f"{API}/whatsapp/phoneNumbers", headers=_headers(), timeout=TIMEOUT)
		itens = r.json().get("items", []) if r.ok else []
	except (requests.RequestException, ValueError):
		itens = []
	for item in itens:
		if item.get("status") == "CONNECTED" and item.get("phoneNumber"):
			numero = "+" + _digitos(item["phoneNumber"])
			update_site_config("ycloud_numero", numero)
			return numero
	return ""


def _hora(valor) -> datetime:
	"""Datas da YCloud vêm em RFC 3339 (UTC). Guardamos no fuso do sistema, sem tz."""
	if not valor:
		return now_datetime()
	try:
		utc = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
		from frappe.utils.data import convert_utc_to_system_timezone

		return convert_utc_to_system_timezone(utc.replace(tzinfo=None)).replace(tzinfo=None)
	except Exception:
		return now_datetime()


# ------------------------------------------------------------------ webhook

def _assinatura_valida(corpo: bytes, cabecalho: str | None, segredo: str) -> bool:
	"""YCloud-Signature: t={timestamp},s={assinatura}; HMAC-SHA256 de "{t}.{corpo}"."""
	if not cabecalho:
		return False
	partes = dict(p.split("=", 1) for p in cabecalho.split(",") if "=" in p)
	t, s = partes.get("t"), partes.get("s")
	if not t or not s:
		return False
	digest = hmac.new(segredo.encode(), f"{t}.".encode() + corpo, hashlib.sha256).digest()
	return hmac.compare_digest(digest.hex(), s) or hmac.compare_digest(base64.b64encode(digest).decode(), s)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook():
	segredo = frappe.conf.get("ycloud_webhook_secret")
	if not segredo:
		# sem segredo não dá para confirmar que veio da YCloud: não processa nada
		return {"status": "ignored", "reason": "webhook not configured"}

	corpo = frappe.request.get_data() or b""
	if not _assinatura_valida(corpo, frappe.get_request_header("YCloud-Signature"), segredo):
		frappe.local.response.http_status_code = 401
		return {"status": "error", "reason": "invalid signature"}

	try:
		evento = json.loads(corpo.decode("utf-8", "replace"))
	except ValueError:
		return {"status": "ignored", "reason": "invalid json"}

	# a YCloud reenvia se não receber 2xx a tempo: não processa o mesmo evento duas vezes
	chave_evento = f"ycloud_evento:{evento.get('id')}"
	if evento.get("id") and frappe.cache.get_value(chave_evento):
		return {"status": "duplicate"}

	try:
		_processar_com_novas_tentativas(evento)
		if evento.get("id"):
			frappe.cache.set_value(chave_evento, 1, expires_in_sec=2 * 24 * 3600)
	except Exception:
		frappe.db.rollback()
		frappe.log_error("WhatsApp (YCloud): falha ao processar evento", frappe.get_traceback())
		# sem 2xx a YCloud reenvia o evento; o wamid impede duplicar o que já tiver entrado
		frappe.local.response.http_status_code = 500
		return {"status": "error", "reason": "processing failed"}
	return {"status": "ok"}


def _processar_com_novas_tentativas(evento: dict):
	for tentativa in range(1, TENTATIVAS + 1):
		try:
			return processar_evento(evento)
		except (frappe.QueryDeadlockError, frappe.DuplicateEntryError, frappe.UniqueValidationError):
			frappe.db.rollback()
			if tentativa == TENTATIVAS:
				raise
			time.sleep(0.2 * tentativa)


def processar_evento(evento: dict):
	tipo = evento.get("type")
	if tipo == "whatsapp.inbound_message.received":
		receber(evento.get("whatsappInboundMessage") or {})
	elif tipo in ("whatsapp.smb.message.echoes", "whatsapp.smb.message.created"):
		eco_do_celular(evento.get("whatsappMessage") or {})
	elif tipo == "whatsapp.message.updated":
		atualizar_status(evento.get("whatsappMessage") or {})


# ------------------------------------------------------------------ contatos e leads

def achar_lead(telefone: str) -> str | None:
	"""Lead com o mesmo celular (aceita com/sem 9, com/sem 55, com máscara)."""
	d = _digitos(telefone)
	if len(d) < 8:
		return None
	limpo = "replace(replace(replace(replace(replace(ifnull({0}, ''), ' ', ''), '-', ''), '(', ''), ')', ''), '+', '')"
	for fim in sorted({v[-8:] for v in _variantes(d)}):
		candidatos = frappe.db.sql(
			f"""select name, mobile_no, phone from `tabCRM Lead`
			where {limpo.format('mobile_no')} like %(fim)s or {limpo.format('phone')} like %(fim)s
			order by creation desc limit 20""",
			{"fim": "%" + fim},
			as_dict=True,
		)
		for c in candidatos:
			if _mesmo_telefone(c.mobile_no, d) or _mesmo_telefone(c.phone, d):
				return c.name
	return None


def garantir_contato(telefone: str, nome: str = "") -> str:
	tel = _digitos(telefone)
	if frappe.db.exists(CONTATO, tel):
		if nome and not frappe.db.get_value(CONTATO, tel, "nome"):
			frappe.db.set_value(CONTATO, tel, "nome", nome, update_modified=False)
		if not frappe.db.get_value(CONTATO, tel, "lead"):
			lead = achar_lead(tel)
			if lead:
				frappe.db.set_value(CONTATO, tel, "lead", lead, update_modified=False)
		return tel
	frappe.get_doc(
		{"doctype": CONTATO, "telefone": tel, "nome": nome or "", "lead": achar_lead(tel)}
	).insert(ignore_permissions=True)
	return tel


def _resumo(contato: str, texto: str, direcao: str, quando, nova_recebida: bool):
	valores = {"ultima_mensagem": (texto or "")[:280], "ultima_direcao": direcao, "ultima_em": quando}
	if nova_recebida:
		valores["nao_lidas"] = cint(frappe.db.get_value(CONTATO, contato, "nao_lidas")) + 1
	frappe.db.set_value(CONTATO, contato, valores, update_modified=False)


# ------------------------------------------------------------------ conteúdo e mídia

def _conteudo(m: dict) -> tuple[str, dict | None]:
	"""Texto para mostrar na conversa + objeto de mídia (se houver) para baixar."""
	tipo = m.get("type") or ""
	if tipo == "text":
		return (m.get("text") or {}).get("body") or "", None
	if tipo in ROTULO_MIDIA:
		midia = m.get(tipo) or {}
		legenda = midia.get("caption") or midia.get("filename") or ""
		return (f"{ROTULO_MIDIA[tipo]}: {legenda}" if legenda else ROTULO_MIDIA[tipo]), midia
	if tipo == "location":
		loc = m.get("location") or {}
		return f"📍 Localização: {loc.get('name') or ''} {loc.get('latitude', '')},{loc.get('longitude', '')}".strip(), None
	if tipo == "reaction":
		return f"Reagiu com {(m.get('reaction') or {}).get('emoji') or ''}".strip(), None
	if tipo == "button":
		return (m.get("button") or {}).get("text") or "[Botão]", None
	if tipo == "interactive":
		inter = m.get("interactive") or {}
		escolha = inter.get("button_reply") or inter.get("list_reply") or {}
		return escolha.get("title") or "[Resposta]", None
	if tipo == "contacts":
		return "👤 Contato compartilhado", None
	if tipo == "revoke":
		return "🚫 Mensagem apagada", None
	if tipo == "edit":
		edicao = m.get("edit") or {}
		corpo = ((edicao.get("message") or edicao).get("text") or {}).get("body")
		return (f"✏️ Mensagem editada: {corpo}" if corpo else "✏️ Mensagem editada (veja no celular)"), None
	return "[Mensagem que o CRM ainda não mostra; veja no celular]", None


def _baixar_midia(midia: dict, mensagem: str, tipo: str) -> str:
	"""Baixa o arquivo e anexa à mensagem como arquivo privado. Falhar aqui não perde a mensagem."""
	link = midia.get("link")
	if not link:
		return ""
	try:
		host = requests.utils.urlparse(link).hostname or ""
		# a chave só vai para a própria YCloud, nunca para outro endereço
		headers = {"X-API-Key": _chave()} if host.endswith("ycloud.com") else {}
		r = requests.get(link, headers=headers, timeout=60, stream=True)
		if not r.ok:
			return ""
		conteudo = r.raw.read(MAX_MIDIA + 1, decode_content=True)
		if len(conteudo) > MAX_MIDIA:
			return ""
		mime = (midia.get("mime_type") or r.headers.get("Content-Type") or "").split(";")[0]
		extensao = {
			"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "aac",
			"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
			"video/mp4": "mp4", "application/pdf": "pdf",
		}.get(mime, "bin")
		nome = midia.get("filename") or f"whatsapp-{tipo}-{mensagem[:8]}.{extensao}"
		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": nome,
				"content": conteudo,
				"is_private": 1,
				"attached_to_doctype": MENSAGEM,
				"attached_to_name": mensagem,
			}
		).insert(ignore_permissions=True)
		return arquivo.file_url
	except Exception:
		frappe.log_error("WhatsApp (YCloud): falha ao baixar mídia", frappe.get_traceback())
		return ""


def _gravar(contato: str, direcao: str, m: dict, pelo_celular: bool = False, status: str = "") -> str | None:
	wamid, yid = m.get("wamid") or "", m.get("id") or ""
	if wamid and frappe.db.exists(MENSAGEM, {"wamid": wamid}):
		return None
	if yid and frappe.db.exists(MENSAGEM, {"ycloud_id": yid}):
		return None
	texto, midia = _conteudo(m)
	quando = _hora(m.get("sendTime") or m.get("createTime"))
	doc = frappe.get_doc(
		{
			"doctype": MENSAGEM,
			"contato": contato,
			"lead": frappe.db.get_value(CONTATO, contato, "lead"),
			"direction": direcao,
			"tipo": m.get("type") or "",
			"message": texto or "-",
			"pelo_celular": 1 if pelo_celular else 0,
			"status": status or m.get("status") or "",
			"wamid": wamid,
			"ycloud_id": yid,
			"timestamp": quando,
		}
	).insert(ignore_permissions=True)
	if midia:
		url = _baixar_midia(midia, doc.name, m.get("type") or "")
		if url:
			frappe.db.set_value(MENSAGEM, doc.name, "anexo", url, update_modified=False)
	_resumo(contato, texto, direcao, quando, nova_recebida=direcao == "Received")
	frappe.db.commit()
	frappe.publish_realtime("whatsapp_ycloud", {"contato": contato})
	return doc.name


def receber(m: dict):
	if not m or m.get("type") == "system":
		return
	telefone = _digitos(m.get("from"))
	if not telefone:
		return
	contato = garantir_contato(telefone, (m.get("customerProfile") or {}).get("name") or "")
	_gravar(contato, "Received", m, status="received")


def eco_do_celular(m: dict):
	"""Mensagem que o dono mandou pelo app do celular: aparece aqui também."""
	telefone = _digitos(m.get("to"))
	if not telefone:
		return
	contato = garantir_contato(telefone)
	_gravar(contato, "Sent", m, pelo_celular=True)


def atualizar_status(m: dict):
	filtros = {"ycloud_id": m.get("id")} if m.get("id") else {"wamid": m.get("wamid")}
	if not any(filtros.values()):
		return
	nome = frappe.db.get_value(MENSAGEM, filtros)
	if not nome:
		return
	valores = {"status": m.get("status") or ""}
	if m.get("wamid"):
		valores["wamid"] = m["wamid"]
	if m.get("errorMessage") or m.get("errorCode"):
		valores["erro"] = f"{m.get('errorCode') or ''} {m.get('errorMessage') or ''}".strip()[:500]
	frappe.db.set_value(MENSAGEM, nome, valores, update_modified=False)
	frappe.db.commit()


# ------------------------------------------------------------------ caixa de entrada

@frappe.whitelist()
def get_status() -> dict:
	_managers_only()
	return {
		"chave": bool(_chave()),
		"webhook": bool(frappe.conf.get("ycloud_webhook_secret")),
		"numero": _numero(),
	}


@frappe.whitelist()
def get_conversations(pessoais: int = 0) -> list[dict]:
	_managers_only()
	contatos = frappe.get_all(
		CONTATO,
		filters={"pessoal": cint(pessoais), "ultima_em": ["is", "set"]},
		fields=["name", "nome", "lead", "pessoal", "ultima_mensagem", "ultima_direcao", "ultima_em", "nao_lidas"],
		order_by="ultima_em desc",
		limit_page_length=300,
	)
	nomes_lead = {}
	leads = [c.lead for c in contatos if c.lead]
	if leads:
		for lead in frappe.get_all("CRM Lead", filters={"name": ["in", leads]}, fields=["name", "first_name", "last_name"]):
			nomes_lead[lead.name] = " ".join(filter(None, [lead.first_name, lead.last_name]))
	for c in contatos:
		c["telefone"] = c.name
		c["titulo"] = nomes_lead.get(c.lead) or c.nome or ("+" + c.name)
	return contatos


@frappe.whitelist()
def get_messages(telefone: str) -> list[dict]:
	_managers_only()
	telefone = _digitos(telefone)
	if cint(frappe.db.get_value(CONTATO, telefone, "nao_lidas")):
		frappe.db.set_value(CONTATO, telefone, "nao_lidas", 0, update_modified=False)
	return frappe.get_all(
		MENSAGEM,
		filters={"contato": telefone},
		fields=["name", "direction", "tipo", "message", "anexo", "pelo_celular", "status", "erro", "timestamp"],
		order_by="timestamp asc",
		limit_page_length=500,
	)


def _erro_amigavel(resposta: dict | str) -> str:
	texto = json.dumps(resposta, ensure_ascii=False) if isinstance(resposta, dict) else str(resposta)
	if any(e in texto for e in ERROS_JANELA):
		return _(
			"Já passaram 24 horas desde a última mensagem dessa pessoa, e a Meta só deixa responder "
			"por aqui dentro desse prazo. Responda pelo celular ou espere a pessoa escrever de novo."
		)
	return _("O WhatsApp não aceitou a mensagem: {0}").format(texto[:300])


@frappe.whitelist(methods=["POST"])
def send_message(telefone: str, message: str) -> dict:
	_managers_only()
	telefone, texto = _digitos(telefone), (message or "").strip()
	if not telefone or not texto:
		frappe.throw(_("Escreva a mensagem antes de enviar."))
	numero = _numero()
	if not _chave() or not numero:
		frappe.throw(_("O WhatsApp ainda não está conectado neste CRM."))

	try:
		r = requests.post(
			f"{API}/whatsapp/messages/sendDirectly",
			headers=_headers(),
			json={"from": numero, "to": "+" + telefone, "type": "text", "text": {"body": texto}},
			timeout=TIMEOUT,
		)
	except requests.RequestException:
		frappe.throw(_("Não foi possível falar com o WhatsApp agora. Tente de novo em instantes."))
	try:
		dados = r.json()
	except ValueError:
		dados = {"erro": r.text[:300]}
	if not r.ok or dados.get("status") == "failed":
		frappe.throw(_erro_amigavel(dados))

	contato = garantir_contato(telefone)
	dados.setdefault("type", "text")
	dados.setdefault("text", {"body": texto})
	_gravar(contato, "Sent", dados, status=dados.get("status") or "accepted")
	return {"status": dados.get("status") or "accepted"}


@frappe.whitelist(methods=["POST"])
def criar_lead(telefone: str) -> str:
	_managers_only()
	telefone = _digitos(telefone)
	contato = frappe.get_doc(CONTATO, telefone)
	if contato.lead:
		return contato.lead
	existente = achar_lead(telefone)
	if existente:
		lead = existente
	else:
		if not frappe.db.exists("CRM Lead Source", ORIGEM):
			frappe.get_doc({"doctype": "CRM Lead Source", "source_name": ORIGEM}).insert(ignore_permissions=True)
		primeiro, _sep, resto = (contato.nome or f"WhatsApp {telefone[-4:]}").partition(" ")
		lead = (
			frappe.get_doc(
				{
					"doctype": "CRM Lead",
					"first_name": primeiro,
					"last_name": resto,
					"mobile_no": "+" + telefone,
					"source": ORIGEM,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	frappe.db.set_value(CONTATO, telefone, "lead", lead, update_modified=False)
	frappe.db.sql(f"update `tab{MENSAGEM}` set lead = %s where contato = %s", (lead, telefone))
	frappe.db.commit()
	return lead


@frappe.whitelist(methods=["POST"])
def marcar_pessoal(telefone: str, pessoal: int = 1):
	_managers_only()
	frappe.db.set_value(CONTATO, _digitos(telefone), "pessoal", 1 if cint(pessoal) else 0, update_modified=False)
	frappe.db.commit()
	return {"ok": True}


# ------------------------------------------------------------------ instalação

def atualizar_eventos() -> dict:
	"""Passa a lista EVENTOS para o webhook que já existe. O segredo continua o mesmo."""
	url = frappe.utils.get_url("/api/method/crm.api.ycloud.webhook")
	r = requests.get(f"{API}/webhookEndpoints", headers=_headers(), timeout=TIMEOUT)
	r.raise_for_status()
	alvo = next((i for i in r.json().get("items", []) if i.get("url") == url), None)
	if not alvo:
		frappe.throw(f"Webhook não encontrado na YCloud: {url}")
	r = requests.patch(
		f"{API}/webhookEndpoints/{alvo['id']}",
		headers=_headers(),
		json={"enabledEvents": list(EVENTOS)},
		timeout=TIMEOUT,
	)
	if not r.ok:
		frappe.throw(f"YCloud recusou a atualização: {r.status_code} {r.text[:300]}")
	dados = r.json()
	return {"status": dados.get("status"), "eventos": dados.get("enabledEvents")}


def configurar_webhook(url: str | None = None) -> dict:
	"""Cria o endereço de webhook na YCloud e guarda o segredo no site_config.
	Rodar uma vez por site: bench --site X execute crm.api.ycloud.configurar_webhook"""
	if not _chave():
		frappe.throw("Falta ycloud_api_key no site_config.")
	url = url or frappe.utils.get_url("/api/method/crm.api.ycloud.webhook")
	r = requests.post(
		f"{API}/webhookEndpoints",
		headers=_headers(),
		json={"url": url, "enabledEvents": list(EVENTOS), "description": "CRM Stratcompany"},
		timeout=TIMEOUT,
	)
	dados = r.json() if r.content else {}
	if not r.ok or not dados.get("secret"):
		frappe.throw(f"YCloud recusou o webhook: {r.status_code} {str(dados)[:300]}")
	update_site_config("ycloud_webhook_secret", dados["secret"])
	_numero()
	return {"id": dados.get("id"), "url": dados.get("url"), "status": dados.get("status"), "eventos": dados.get("enabledEvents")}
