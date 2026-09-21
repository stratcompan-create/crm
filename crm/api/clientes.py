# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Pasta do cliente e recebimento de documentos.
#  - cada negócio ganha uma pasta em Arquivos > Clientes > <nome do cliente>;
#  - tudo que é anexado ao negócio (ou chega por e-mail) vai para essa pasta;
#  - o cliente pode enviar documentos por um link seguro (/documentos?t=...), direto para a pasta.
# O WhatsApp entra depois, só pela API oficial: o número do cliente identifica o negócio.

import json
import re
import secrets

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_url, nowdate, now_datetime

ROOT = "Clientes"
MAX_BYTES = 15 * 1024 * 1024
MAX_FILES_PER_LINK = 40
ALLOWED = {
	".pdf": (b"%PDF",),
	".jpg": (b"\xff\xd8\xff",),
	".jpeg": (b"\xff\xd8\xff",),
	".png": (b"\x89PNG",),
	".heic": (),
	".heif": (),
	".webp": (b"RIFF",),
	".doc": (b"\xd0\xcf\x11\xe0",),
	".docx": (b"PK",),
}

DEFAULT_ITEMS = {
	"agencia": ["Contrato assinado", "Documento com CNPJ", "Logo e identidade visual", "Acessos e materiais do projeto"],
	"escritorio": ["RG ou CNH", "CPF", "Comprovante de residência", "Procuração assinada"],
	"escritorio_empresarial": ["Contrato social", "Cartão CNPJ", "RG ou CNH do sócio", "Comprovante de endereço da empresa"],
}


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


# ------------------------------------------------------------------ pasta do cliente

def _clean(name: str) -> str:
	name = re.sub(r"[\\/:*?\"<>|]+", " ", name or "").strip()
	return re.sub(r"\s+", " ", name)[:80] or "Cliente"


def _make_folder(name: str, parent: str) -> str:
	path = f"{parent}/{name}"
	if frappe.db.exists("File", path):
		return path
	frappe.get_doc({"doctype": "File", "file_name": name, "is_folder": 1, "folder": parent}).insert(
		ignore_permissions=True
	)
	return path


def client_label(deal) -> str:
	return _clean(
		deal.get("organization_name")
		or deal.get("organization")
		or " ".join(filter(None, [deal.get("first_name"), deal.get("last_name")]))
		or deal.name
	)


def ensure_client_folder(deal_name: str) -> str | None:
	"""Cria (uma vez) Clientes/<nome> e guarda o caminho no negócio."""
	deal = frappe.get_doc("CRM Deal", deal_name)
	current = deal.get("pasta_cliente")
	if current and frappe.db.exists("File", current):
		return current
	root = _make_folder(ROOT, "Home")
	label = client_label(deal)
	# mesmo cliente, mesma pasta (vários negócios do mesmo cliente compartilham os documentos)
	folder = _make_folder(label, root)
	frappe.db.set_value("CRM Deal", deal.name, "pasta_cliente", folder, update_modified=False)
	return folder


def on_deal_insert(doc, method=None):
	try:
		ensure_client_folder(doc.name)
	except Exception:
		frappe.log_error("Clientes: falha ao criar a pasta do cliente", frappe.get_traceback())


def ensure_all_folders():
	for name in frappe.get_all("CRM Deal", filters={"pasta_cliente": ["is", "not set"]}, pluck="name"):
		try:
			ensure_client_folder(name)
		except Exception:
			frappe.log_error("Clientes: falha ao criar a pasta do cliente", frappe.get_traceback())


def on_file_insert(doc, method=None):
	"""Anexo do negócio (ou e-mail do negócio) vai para a pasta do cliente."""
	try:
		if doc.is_folder or not doc.attached_to_doctype:
			return
		deal = None
		if doc.attached_to_doctype == "CRM Deal":
			deal = doc.attached_to_name
		elif doc.attached_to_doctype == "Communication":
			ref = frappe.db.get_value("Communication", doc.attached_to_name, ["reference_doctype", "reference_name"], as_dict=True)
			if ref and ref.reference_doctype == "CRM Deal":
				deal = ref.reference_name
		if not deal or not frappe.db.exists("CRM Deal", deal):
			return
		if (doc.folder or "").startswith(f"Home/{ROOT}/"):
			return
		folder = ensure_client_folder(deal)
		if folder:
			frappe.db.set_value("File", doc.name, "folder", folder, update_modified=False)
	except Exception:
		frappe.log_error("Clientes: falha ao mover anexo para a pasta do cliente", frappe.get_traceback())


# ------------------------------------------------------------------ o que o cliente já enviou

@frappe.whitelist()
def get_documents(deal: str) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("read")
	folder = ensure_client_folder(deal)
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "CRM Deal", "attached_to_name": deal, "is_folder": 0},
		fields=["name", "file_name", "file_url", "file_size", "creation", "is_private"],
		order_by="creation desc",
	)
	# arquivos já dentro da pasta, mesmo sem anexo ao negócio
	if folder:
		extra = frappe.get_all(
			"File",
			filters={"folder": folder, "is_folder": 0, "name": ["not in", [f.name for f in files] or [""]]},
			fields=["name", "file_name", "file_url", "file_size", "creation", "is_private"],
			order_by="creation desc",
		)
		files += extra
	pedidos = frappe.get_all(
		"CRM Pedido Documentos",
		filters={"deal": deal},
		fields=["name", "token", "itens", "recebidos", "expira_em", "ativo", "creation"],
		order_by="creation desc",
		limit=5,
	)
	for p in pedidos:
		p["itens"] = json.loads(p.itens or "[]")
		p["recebidos"] = json.loads(p.recebidos or "[]")
		p["link"] = _link(p.token)
	from crm.api.automacoes import _client

	client = _client(deal)
	phone = doc.get("mobile_no") or (frappe.db.get_value("CRM Lead", doc.lead, "mobile_no") if doc.get("lead") else "")
	return {
		"pasta": folder,
		"arquivos": files,
		"pedidos": pedidos,
		"sugestao": _default_items(),
		"nome": client.nome,
		"tem_email": bool(client.email),
		"telefone": re.sub(r"\D", "", phone or ""),
	}


def _default_items() -> list[str]:
	profile = frappe.db.get_default("crm_profile") or "agencia"
	return DEFAULT_ITEMS.get(profile, DEFAULT_ITEMS["agencia"])


def _link(token: str) -> str:
	return get_url(f"/documentos?t={token}")


# ------------------------------------------------------------------ pedido de documentos por link

@frappe.whitelist()
def create_request(deal: str, itens, mensagem: str = "", dias: int = 14) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("write")
	itens = [str(i).strip()[:80] for i in (frappe.parse_json(itens) or []) if str(i).strip()][:20]
	if not itens:
		frappe.throw(_("Escolha pelo menos um documento para pedir."))
	ensure_client_folder(deal)
	pedido = frappe.get_doc(
		{
			"doctype": "CRM Pedido Documentos",
			"deal": deal,
			"token": secrets.token_urlsafe(24),
			"itens": json.dumps(itens, ensure_ascii=False),
			"recebidos": "[]",
			"mensagem": (mensagem or "").strip()[:600],
			"expira_em": add_days(nowdate(), min(60, max(1, cint(dias) or 14))),
			"ativo": 1,
		}
	).insert(ignore_permissions=True)
	return {"name": pedido.name, "link": _link(pedido.token)}


@frappe.whitelist()
def close_request(pedido: str):
	doc = frappe.get_doc("CRM Pedido Documentos", pedido)
	frappe.get_doc("CRM Deal", doc.deal).check_permission("write")
	doc.db_set("ativo", 0)
	return {"ok": True}


@frappe.whitelist()
def send_request_email(pedido: str):
	from frappe.core.doctype.communication.email import make

	doc = frappe.get_doc("CRM Pedido Documentos", pedido)
	deal = frappe.get_doc("CRM Deal", doc.deal)
	deal.check_permission("write")
	from crm.api.automacoes import _client

	client = _client(deal.name)
	if not client.email:
		frappe.throw(_("Este negócio não tem e-mail cadastrado."))
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		frappe.throw(_("Configure o e-mail de envio em Configurações → E-mail antes de enviar."))
	brand = frappe.db.get_single_value("FCRM Settings", "brand_name") or ""
	itens = json.loads(doc.itens or "[]")
	text = (
		f"Olá, {client.nome}!\n\n"
		+ (doc.mensagem + "\n\n" if doc.mensagem else "Para darmos andamento, precisamos de alguns documentos.\n\n")
		+ "Você pode enviar tudo pelo celular, pelo link abaixo (é seguro e leva menos de 2 minutos):\n"
		+ _link(doc.token)
		+ "\n\nDocumentos pedidos:\n"
		+ "\n".join(f"- {i}" for i in itens)
		+ f"\n\nO link vale até {doc.expira_em.strftime('%d/%m/%Y') if doc.expira_em else ''}.\n{brand}"
	)
	make(
		doctype="CRM Deal",
		name=deal.name,
		content=frappe.utils.escape_html(text).replace("\n", "<br>"),
		subject=("Documentos para o seu atendimento" + (f" — {brand}" if brand else "")),
		recipients=client.email,
		communication_medium="Email",
		send_email=True,
	)
	return {"ok": True}


# ------------------------------------------------------------------ página pública

def _pedido_by_token(token: str):
	if not token or len(token) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value("CRM Pedido Documentos", {"token": token})
	if not name:
		frappe.throw(_("Link inválido."))
	doc = frappe.get_doc("CRM Pedido Documentos", name)
	if not doc.ativo or (doc.expira_em and frappe.utils.getdate(doc.expira_em) < frappe.utils.getdate(nowdate())):
		frappe.throw(_("Este link expirou. Peça um novo ao escritório."))
	return doc


@frappe.whitelist(allow_guest=True)
def get_public_request(t: str = "") -> dict:
	doc = _pedido_by_token(t)
	from crm.api.automacoes import _client

	client = _client(doc.deal)
	done = {}
	for r in json.loads(doc.recebidos or "[]"):
		done[r["item"]] = done.get(r["item"], 0) + 1
	return {
		"marca": frappe.db.get_single_value("FCRM Settings", "brand_name") or "",
		"logo": frappe.db.get_single_value("FCRM Settings", "brand_logo") or "",
		"nome": client.nome,
		"mensagem": doc.mensagem or "",
		"itens": [{"nome": i, "enviados": done.get(i, 0)} for i in json.loads(doc.itens or "[]")],
		"expira_em": str(doc.expira_em or ""),
	}


@frappe.whitelist(allow_guest=True)
def upload_public_document(t: str = "", item: str = ""):
	doc = _pedido_by_token(t)
	itens = json.loads(doc.itens or "[]")
	if item not in itens:
		frappe.throw(_("Documento não pedido."))
	log = json.loads(doc.recebidos or "[]")
	if len(log) >= MAX_FILES_PER_LINK:
		frappe.throw(_("Limite de arquivos deste link atingido. Fale com o escritório."))
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload:
		frappe.throw(_("Nenhum arquivo enviado."))
	content = upload.stream.read(MAX_BYTES + 1)
	if len(content) > MAX_BYTES:
		frappe.throw(_("Arquivo maior que 15 MB."))
	if not content:
		frappe.throw(_("O arquivo está vazio."))
	original = (upload.filename or "arquivo").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
	ext = "." + original.rsplit(".", 1)[-1].lower() if "." in original else ""
	if ext not in ALLOWED:
		frappe.throw(_("Tipo de arquivo não aceito. Envie PDF, foto (JPG, PNG, HEIC) ou documento Word."))
	magic = ALLOWED[ext]
	if magic and not any(content.startswith(m) for m in magic):
		frappe.throw(_("O arquivo parece estar corrompido ou não é do tipo informado."))
	folder = ensure_client_folder(doc.deal)
	stamp = now_datetime().strftime("%Y%m%d-%H%M%S")
	name = f"{_clean(item)} - {stamp}{ext}"
	frappe.set_user("Administrator")
	try:
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": name,
				"attached_to_doctype": "CRM Deal",
				"attached_to_name": doc.deal,
				"folder": folder,
				"is_private": 1,
				"content": content,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Clientes: arquivo recebido não pôde ser salvo", frappe.get_traceback())
		frappe.throw(_("Não foi possível salvar este arquivo. Tire outra foto ou envie em PDF."))
	log.append({"item": item, "arquivo": file.name, "nome": name, "em": str(now_datetime())})
	frappe.db.set_value("CRM Pedido Documentos", doc.name, "recebidos", json.dumps(log, ensure_ascii=False), update_modified=False)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "CRM Deal",
			"reference_name": doc.deal,
			"content": f"Documento recebido pelo link: {item}.",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "enviados": sum(1 for r in log if r["item"] == item)}
