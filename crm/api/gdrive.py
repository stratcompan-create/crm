"""Integração com o Google Drive.

Escopo pedido ao Google: só `drive.file` (o CRM enxerga apenas as pastas e arquivos que ele mesmo criou).
O ID e o segredo do app OAuth ficam na configuração do servidor (gdrive_client_id / gdrive_client_secret),
nunca no código nem no banco. Cada site guarda apenas o token do próprio escritório.
"""

import json
import secrets
from urllib.parse import urlencode

import requests

import frappe
from frappe import _
from frappe.utils import cint

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
DRIVE_URL = "https://www.googleapis.com/drive/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
SCOPES = "openid email https://www.googleapis.com/auth/drive.file"
DOCTYPE = "CRM Google Drive"
TIMEOUT = 60


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _config() -> dict:
	client_id = frappe.conf.get("gdrive_client_id")
	secret = frappe.conf.get("gdrive_client_secret")
	if not client_id or not secret:
		frappe.throw(_("O Google Drive ainda não foi habilitado neste servidor. Fale com o suporte."))
	redirect = frappe.conf.get("gdrive_redirect_uri") or (
		frappe.utils.get_url() + "/api/method/crm.api.gdrive.callback"
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
		"pasta": s.pasta_nome or "",
		"envio_automatico": bool(s.envio_automatico),
	}


@frappe.whitelist()
def start_auth() -> dict:
	_managers_only()
	cfg = _config()
	state = secrets.token_urlsafe(24)
	frappe.cache().set_value(
		f"gdrive_state:{state}", {"user": frappe.session.user}, expires_in_sec=600
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
	destino_ok = "/crm?gdrive=ok"
	destino_erro = "/crm?gdrive=erro"

	def ir(url):
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = url

	if error or not code or not state:
		return ir(destino_erro)

	key = f"gdrive_state:{state}"
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
			frappe.log_error("Google Drive: falha na troca do código", json.dumps({k: v for k, v in tokens.items() if "token" not in k}))
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
			doc.pasta_id = ""
			doc.pastas = "{}"
			if cint(doc.envio_automatico) == 0 and not doc.pasta_nome:
				doc.envio_automatico = 1
			doc.flags.ignore_permissions = True
			doc.save()
			frappe.db.commit()
		finally:
			frappe.set_user(previous_user)
		frappe.cache().delete_value("gdrive_access_token")
		return ir(destino_ok)
	except Exception:
		frappe.log_error("Google Drive: falha ao conectar", frappe.get_traceback())
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
	doc.pasta_id = ""
	doc.pastas = "{}"
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.cache().delete_value("gdrive_access_token")
	return {"ok": True}


@frappe.whitelist()
def save_options(envio_automatico=None, pasta_nome=None):
	_managers_only()
	doc = _settings()
	if envio_automatico is not None:
		doc.envio_automatico = cint(envio_automatico)
	if pasta_nome is not None and pasta_nome.strip() and pasta_nome.strip() != doc.pasta_nome:
		doc.pasta_nome = pasta_nome.strip()
		# nova pasta raiz: as ids antigas deixam de valer
		doc.pasta_id = ""
		doc.pastas = "{}"
	doc.flags.ignore_permissions = True
	doc.save()
	return {"ok": True}


# ------------------------------------------------------------------ Google API

def _access_token() -> str:
	cached = frappe.cache().get_value("gdrive_access_token")
	if cached:
		return cached
	doc = _settings()
	if not doc.conectado:
		frappe.throw(_("O Google Drive não está conectado. Conecte em Configurações → Integrações."))
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
			frappe.throw(_("A conexão com o Google Drive expirou. Conecte de novo em Configurações → Integrações."))
		frappe.throw(_("Não foi possível falar com o Google Drive agora."))
	frappe.cache().set_value(
		"gdrive_access_token", data["access_token"], expires_in_sec=max(60, cint(data.get("expires_in", 3600)) - 120)
	)
	return data["access_token"]


def _headers() -> dict:
	return {"Authorization": f"Bearer {_access_token()}"}


def _drive_call(method: str, url: str, **kwargs):
	resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kwargs)
	if resp.status_code == 401:
		# token vencido antes do previsto: renova uma vez
		frappe.cache().delete_value("gdrive_access_token")
		resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kwargs)
	if resp.status_code >= 400:
		frappe.log_error("Google Drive: erro na API", f"{method} {url}\n{resp.text[:1500]}")
		frappe.throw(_("O Google Drive recusou a operação."))
	return resp.json()


def _esc(value: str) -> str:
	return value.replace("\\", "\\\\").replace("'", "\\'")


def _find_or_create_folder(name: str, parent_id: str | None) -> str:
	q = f"mimeType='application/vnd.google-apps.folder' and name='{_esc(name)}' and trashed=false"
	q += f" and '{parent_id}' in parents" if parent_id else " and 'root' in parents"
	found = _drive_call("GET", f"{DRIVE_URL}/files", params={"q": q, "fields": "files(id)", "pageSize": 1})
	if found.get("files"):
		return found["files"][0]["id"]
	body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
	if parent_id:
		body["parents"] = [parent_id]
	return _drive_call("POST", f"{DRIVE_URL}/files", json=body, params={"fields": "id"})["id"]


def _folder_for(path: list[str]) -> str:
	"""Garante a pasta raiz do CRM e as subpastas do caminho; guarda os ids para não procurar de novo.
	Só grava a configuração quando algo mudou, e sem regravar o documento inteiro."""
	doc = _settings()
	mapa = json.loads(doc.pastas or "{}")
	root_name = doc.pasta_nome or _default_root_name()
	pasta_id, changed = doc.pasta_id, False
	if not pasta_id:
		pasta_id = _find_or_create_folder(root_name, None)
		mapa, changed = {}, True
	parent = pasta_id
	acumulado = ""
	for part in [p for p in path if p]:
		acumulado += "/" + part
		if acumulado not in mapa:
			mapa[acumulado] = _find_or_create_folder(part, parent)
			changed = True
		parent = mapa[acumulado]
	if changed:
		frappe.db.set_single_value(
			DOCTYPE,
			{"pasta_id": pasta_id, "pasta_nome": root_name, "pastas": json.dumps(mapa, ensure_ascii=False)},
		)
		frappe.db.commit()
	return parent


def _default_root_name() -> str:
	brand = frappe.db.get_single_value("FCRM Settings", "brand_name") or ""
	return f"{brand} CRM".strip() if brand else "CRM"


def upload_bytes(filename: str, content: bytes, mime: str = "application/octet-stream", path: list[str] | None = None) -> dict:
	"""Envia um arquivo ao Drive do escritório e devolve {id, link}. Levanta erro se não estiver conectado."""
	folder = _folder_for(path or [])
	meta = json.dumps({"name": filename, "parents": [folder]})
	files = {
		"metadata": ("metadata", meta, "application/json; charset=UTF-8"),
		"file": (filename, content, mime),
	}
	resp = requests.post(
		f"{UPLOAD_URL}?uploadType=multipart&fields=id,webViewLink",
		headers=_headers(),
		files=files,
		timeout=120,
	)
	if resp.status_code == 401:
		frappe.cache().delete_value("gdrive_access_token")
		resp = requests.post(
			f"{UPLOAD_URL}?uploadType=multipart&fields=id,webViewLink", headers=_headers(), files=files, timeout=120
		)
	if resp.status_code >= 400:
		frappe.log_error("Google Drive: falha no envio do arquivo", resp.text[:1500])
		frappe.throw(_("Não foi possível enviar o arquivo para o Google Drive."))
	data = resp.json()
	return {"id": data.get("id"), "link": data.get("webViewLink")}


def is_connected() -> bool:
	try:
		return _configured() and bool(frappe.db.get_single_value(DOCTYPE, "conectado"))
	except Exception:
		return False


# ------------------------------------------------------------------ uso pelo CRM

@frappe.whitelist()
def save_deal_document(deal: str, doc_type: str = "proposta"):
	"""Gera o documento do negócio (proposta, orçamento ou contrato) e guarda no Drive."""
	from crm.api.budget import build_document

	if not is_connected():
		frappe.throw(_("Conecte o Google Drive em Configurações → Integrações."))
	filename, content, doc = build_document(deal, doc_type)
	from crm.api.budget import _get_client_name

	client = _get_client_name(doc)
	res = upload_bytes(filename, content, "application/pdf", ["Propostas", client])
	return {"ok": True, "arquivo": filename, "link": res["link"]}


def _path_for_file(file_doc) -> list[str]:
	folder = (file_doc.folder or "").replace("Home/", "").replace("Home", "")
	# documentos do cliente (RG, contratos assinados, fotos...) espelham a pasta Clientes/<nome>
	proposal_like = (file_doc.file_name or "").startswith(("Proposta", "Orçamento", "Contrato"))
	if (file_doc.folder or "").startswith("Home/Clientes/") and not proposal_like:
		return [p for p in folder.split("/") if p]
	if file_doc.attached_to_doctype == "CRM Deal" and file_doc.attached_to_name:
		from crm.api.budget import _get_client_name

		try:
			deal = frappe.get_doc("CRM Deal", file_doc.attached_to_name)
			return ["Propostas", _get_client_name(deal)]
		except Exception:
			return ["Propostas"]
	if folder:
		return [p for p in folder.split("/") if p]
	return ["Outros"]


def on_file_insert(doc, method=None):
	"""Copia sozinho para o Drive os arquivos gerados no CRM (se o envio automático estiver ligado)."""
	try:
		if doc.is_folder or not is_connected():
			return
		# get_single traz o padrão (ligado) mesmo quando a configuração ainda não foi salva
		if not cint(_settings().envio_automatico):
			return
		if not (
			(doc.attached_to_doctype or "").startswith("CRM ")
			or (doc.folder or "").startswith("Home/")
		):
			return
		frappe.enqueue(
			"crm.api.gdrive.upload_file_doc",
			name=doc.name,
			queue="short",
			enqueue_after_commit=True,
		)
	except Exception:
		frappe.log_error("Google Drive: falha ao agendar o envio", frappe.get_traceback())


def upload_file_doc(name: str):
	"""Vários arquivos ao mesmo tempo disputam a configuração do Drive; nesse caso tenta de novo."""
	import time

	from frappe.utils.synchronization import filelock

	for attempt in range(4):
		try:
			# um envio por vez: vários arquivos juntos disputavam a configuração do Drive
			with filelock("gdrive_upload", timeout=300):
				return _upload_file_doc(name)
		except (frappe.QueryDeadlockError, frappe.TimestampMismatchError):
			frappe.db.rollback()
			if attempt == 3:
				raise
			time.sleep(2 + attempt * 2)


def _upload_file_doc(name: str):
	import mimetypes

	doc = frappe.get_doc("File", name)
	content = doc.get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")
	mime = mimetypes.guess_type(doc.file_name or "")[0] or "application/octet-stream"
	upload_bytes(doc.file_name, content, mime, _path_for_file(doc))
