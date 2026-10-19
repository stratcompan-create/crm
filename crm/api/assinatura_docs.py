# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Assinatura eletrônica de documentos gerados (contrato de honorários, procuração, declaração...).
# O cliente abre um link, lê o PDF, confirma nome, CPF e e-mail e assina. O CRM guarda data, hora,
# IP, navegador e o código SHA-256 do arquivo, e gera o PDF assinado (documento + página de
# registro). É assinatura eletrônica simples (Lei 14.063/2020): onde a lei ou o juízo exigir
# certificado ICP-Brasil ou gov.br, use essa via.

import hashlib
import io
import re
import secrets

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_url, getdate, now_datetime, nowdate
from werkzeug.wrappers import Response


def _conteudo(file_name: str) -> bytes:
	return frappe.get_doc("File", file_name).get_content()


def _hash(b: bytes) -> str:
	return hashlib.sha256(b).hexdigest()


def cpf_cnpj_valido(doc: str) -> bool:
	d = re.sub(r"\D", "", doc or "")
	if len(d) == 11 and len(set(d)) > 1:
		for n in (9, 10):
			s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
			if (s * 10 % 11) % 10 != int(d[n]):
				return False
		return True
	if len(d) == 14 and len(set(d)) > 1:
		for n in (12, 13):
			pesos = ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if n == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
			r = sum(int(d[i]) * pesos[i] for i in range(n)) % 11
			if (0 if r < 2 else 11 - r) != int(d[n]):
				return False
		return True
	return False


# ------------------------------------------------------------------ escritório

@frappe.whitelist()
def enviar_para_assinatura(deal: str, arquivo: str, dias: int = 15, avisar=1) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("write")
	f = frappe.get_doc("File", arquivo)
	if f.attached_to_doctype != "CRM Deal" or f.attached_to_name != deal:
		frappe.throw(_("Este arquivo não é deste caso."))
	if not (f.file_name or "").lower().endswith(".pdf"):
		frappe.throw(_("Só dá para enviar PDF para assinatura."))
	existente = frappe.db.get_value("CRM Assinatura", {"arquivo": arquivo, "status": "Aguardando"}, ["name", "token"], as_dict=True)
	if existente:
		return {"name": existente.name, "link": get_url(f"/assinar?t={existente.token}")}
	a = frappe.get_doc({
		"doctype": "CRM Assinatura", "deal": deal, "arquivo": arquivo, "nome_arquivo": f.file_name, "status": "Aguardando",
		"token": secrets.token_urlsafe(24), "hash_original": _hash(_conteudo(arquivo)),
		"expira_em": add_days(nowdate(), max(1, min(60, cint(dias) or 15))),
	}).insert(ignore_permissions=True)
	link = get_url(f"/assinar?t={a.token}")
	if cint(avisar):
		try:
			from crm.api.automacoes import _notify_client

			_notify_client(deal, _("Documento para assinar: {0}").format(f.file_name),
						   _("Olá! Seu documento está pronto para assinatura. Leia com calma e assine pelo celular: {0}").format(link),
						   _("Enviar ao cliente o link de assinatura: {0}").format(link))
		except Exception:
			frappe.log_error("Assinatura: aviso ao cliente falhou", frappe.get_traceback())
	return {"name": a.name, "link": link}


@frappe.whitelist()
def listar(deal: str) -> list[dict]:
	frappe.get_doc("CRM Deal", deal).check_permission("read")
	out = frappe.get_all("CRM Assinatura", filters={"deal": deal},
						 fields=["name", "nome_arquivo", "status", "token", "expira_em", "assinante_nome", "assinado_em", "arquivo_assinado"],
						 order_by="creation desc")
	for a in out:
		a["link"] = get_url(f"/assinar?t={a.token}") if a.status == "Aguardando" else ""
		a["url_assinado"] = frappe.db.get_value("File", a.arquivo_assinado, "file_url") if a.arquivo_assinado else ""
		a.pop("token", None)
	return out


@frappe.whitelist()
def cancelar(name: str) -> dict:
	a = frappe.get_doc("CRM Assinatura", name)
	frappe.get_doc("CRM Deal", a.deal).check_permission("write")
	if a.status == "Assinado":
		frappe.throw(_("Documento já assinado não pode ser cancelado."))
	a.db_set("status", "Cancelado")
	return {"ok": True}


# ------------------------------------------------------------------ página pública

def _por_token(t: str, para_assinar=False):
	if not t or len(t) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value("CRM Assinatura", {"token": t})
	if not name:
		frappe.throw(_("Link inválido."))
	a = frappe.get_doc("CRM Assinatura", name)
	if a.status == "Cancelado":
		frappe.throw(_("Este pedido de assinatura foi cancelado pelo escritório."))
	if para_assinar and a.status == "Aguardando" and a.expira_em and getdate(a.expira_em) < getdate(nowdate()):
		frappe.throw(_("Este link expirou. Peça um novo ao escritório."))
	return a


@frappe.whitelist(allow_guest=True)
def dados_publicos(t: str = "") -> dict:
	frappe.local.no_cache = 1
	a = _por_token(t)
	from crm.api.automacoes import _client

	g = frappe.db.get_single_value
	return {
		"marca": g("FCRM Settings", "brand_name") or "", "logo": g("FCRM Settings", "brand_logo") or "",
		"cor": g("FCRM Settings", "brand_color") or "", "destaque": g("FCRM Settings", "brand_accent") or "",
		"cliente": _client(a.deal).completo, "documento": a.nome_arquivo, "status": a.status,
		"assinante_nome": a.assinante_nome or "", "assinado_em": str(a.assinado_em or ""), "codigo": a.hash_original[:16],
	}


@frappe.whitelist(allow_guest=True)
def pdf_publico(t: str = ""):
	a = _por_token(t)
	f = a.arquivo_assinado if a.status == "Assinado" and a.arquivo_assinado else a.arquivo
	return Response(_conteudo(f), mimetype="application/pdf",
					headers={"Content-Disposition": f'inline; filename="{(a.nome_arquivo or "documento.pdf")}"', "Cache-Control": "no-store"})


@frappe.whitelist(allow_guest=True, methods=["POST"])
def assinar(t: str = "", nome: str = "", documento: str = "", email: str = "", aceite=0) -> dict:
	a = _por_token(t, para_assinar=True)
	if a.status == "Assinado":
		return {"ok": True, "assinante_nome": a.assinante_nome, "assinado_em": str(a.assinado_em)}
	nome = (nome or "").strip()
	email = (email or "").strip().lower()
	if len(nome.split()) < 2:
		frappe.throw(_("Informe o nome completo."))
	if not cpf_cnpj_valido(documento):
		frappe.throw(_("CPF ou CNPJ inválido. Confira os números."))
	if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", email):
		frappe.throw(_("Informe um e-mail válido."))
	if not cint(aceite):
		frappe.throw(_("Marque que leu e concorda com o documento."))
	original = _conteudo(a.arquivo)
	if _hash(original) != a.hash_original:
		frappe.throw(_("O documento foi alterado depois do envio. Peça um novo link ao escritório."))

	agora = now_datetime()
	ip = frappe.local.request_ip or ""
	req = getattr(frappe.local, "request", None)
	navegador = ((req.headers.get("User-Agent") if req is not None else "") or "")[:300]
	doc_fmt = re.sub(r"\D", "", documento)
	assinado = _pdf_assinado(original, a, nome, doc_fmt, email, agora, ip)
	nome_final = re.sub(r"\.pdf$", "", a.nome_arquivo or "Documento", flags=re.I) + " - assinado.pdf"
	frappe.set_user("Administrator")
	f = frappe.get_doc({"doctype": "File", "file_name": nome_final, "attached_to_doctype": "CRM Deal", "attached_to_name": a.deal,
						"is_private": 1, "content": assinado}).insert(ignore_permissions=True)
	a.db_set({"status": "Assinado", "assinante_nome": nome, "assinante_documento": doc_fmt, "assinante_email": email,
			  "assinado_em": agora, "assinado_ip": ip, "navegador": navegador, "arquivo_assinado": f.name})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal", "reference_name": a.deal,
					"content": _("{0} assinado eletronicamente por {1} em {2}.").format(a.nome_arquivo, nome, agora.strftime("%d/%m/%Y %H:%M"))}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "assinante_nome": nome, "assinado_em": str(agora)}


def _pdf_assinado(original: bytes, a, nome, doc, email, agora, ip) -> bytes:
	"""Documento original + página de registro da assinatura."""
	from pypdf import PdfReader, PdfWriter

	from crm.api.modelos_documentos import _build

	doc_mask = (f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}" if len(doc) == 11 else
				f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}")
	registro = "\n".join([
		"# REGISTRO DE ASSINATURA ELETRÔNICA",
		"",
		f"**Documento:** {a.nome_arquivo}",
		"",
		f"**Código do documento original (SHA-256):** {a.hash_original}",
		"",
		f"**Assinado por:** {nome} — CPF/CNPJ {doc_mask}",
		"",
		f"**E-mail informado:** {email}",
		"",
		f"**Data e hora:** {agora.strftime('%d/%m/%Y às %H:%M:%S')} (horário de Brasília)",
		"",
		f"**Endereço IP:** {ip or 'não identificado'}",
		"",
		"O signatário declarou ter lido o documento acima e concordar com o seu conteúdo, por meio do link exclusivo enviado pelo escritório.",
		"",
		"Assinatura eletrônica simples, nos termos da Lei nº 14.063/2020 e do art. 10, § 2º, da MP nº 2.200-2/2001. "
		"Qualquer alteração no documento original muda o código SHA-256 acima.",
	])
	pagina = _build(registro, {}, "Outro", "Registro de assinatura", "", False)
	w = PdfWriter()
	for fonte in (original, pagina):
		for p in PdfReader(io.BytesIO(fonte)).pages:
			w.add_page(p)
	w.add_metadata({"/Subject": f"Assinado eletronicamente por {nome} em {agora.strftime('%d/%m/%Y %H:%M')}"})
	buf = io.BytesIO()
	w.write(buf)
	return buf.getvalue()
