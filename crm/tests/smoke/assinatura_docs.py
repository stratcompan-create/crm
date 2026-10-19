"""Teste de fumaça: assinatura eletrônica de documentos (crm.api.assinatura_docs)."""

import io

import frappe

from crm.api import assinatura_docs as ad


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	from crm.api.modelos_documentos import _build
	from pypdf import PdfReader

	d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": "Cliente", "last_name": "Assina Teste", "lead_name": "Cliente Assina Teste"})
	d.flags.sem_cobranca_automatica = True
	d.insert(ignore_permissions=True)
	try:
		pdf = _build("# PROCURAÇÃO\n\nOutorgo poderes ao escritório.", {}, "Procuração", "Procuração", "", False)
		f = frappe.get_doc({"doctype": "File", "file_name": "Procuração - teste v1.pdf", "attached_to_doctype": "CRM Deal",
							"attached_to_name": d.name, "is_private": 1, "content": pdf}).insert(ignore_permissions=True)
		ck("CPF válido é aceito e inválido não", ad.cpf_cnpj_valido("529.982.247-25") and not ad.cpf_cnpj_valido("111.111.111-11")
		   and not ad.cpf_cnpj_valido("529.982.247-24"))
		ck("CNPJ válido é aceito", ad.cpf_cnpj_valido("11.222.333/0001-81"))

		r = ad.enviar_para_assinatura(d.name, f.name, avisar=0)
		token = r["link"].split("t=")[1]
		ck("cria o link de assinatura", "/assinar?t=" in r["link"])
		ck("pedir de novo devolve o mesmo link", ad.enviar_para_assinatura(d.name, f.name, avisar=0)["link"] == r["link"])

		frappe.set_user("Guest")
		pub = ad.dados_publicos(token)
		ck("página pública mostra o documento sem login", pub["documento"] == f.file_name and pub["status"] == "Aguardando")
		resp = ad.pdf_publico(token)
		ck("cliente consegue ler o PDF pelo link", resp.mimetype == "application/pdf" and resp.get_data()[:4] == b"%PDF")
		erro = None
		try:
			ad.assinar(token, "Cliente Assina Teste", "111.111.111-11", "cliente@example.com", 1)
		except frappe.ValidationError as e:
			erro = str(e)
		ck("recusa CPF inválido", erro and "CPF" in erro)
		erro = None
		try:
			ad.assinar(token, "Cliente Assina Teste", "529.982.247-25", "cliente@example.com", 0)
		except frappe.ValidationError as e:
			erro = str(e)
		ck("exige marcar que leu e concorda", erro and "concorda" in erro)
		ok = ad.assinar(token, "Cliente Assina Teste", "529.982.247-25", "cliente@example.com", 1)
		frappe.set_user("Administrator")
		a = frappe.get_doc("CRM Assinatura", {"token": token})
		ck("assina e registra nome, CPF, data e IP", ok["ok"] and a.status == "Assinado" and a.assinante_documento == "52998224725" and a.assinado_em)
		assinado = frappe.get_doc("File", a.arquivo_assinado).get_content()
		paginas = len(PdfReader(io.BytesIO(assinado)).pages)
		ck("gera o PDF assinado: documento + página de registro", paginas == len(PdfReader(io.BytesIO(pdf)).pages) + 1, str(paginas))
		texto = PdfReader(io.BytesIO(assinado)).pages[-1].extract_text()
		ck("página de registro traz o código SHA-256 e a lei", a.hash_original[:20] in texto.replace("\n", "") and "14.063" in texto)
		frappe.set_user("Guest")
		ck("assinar de novo não duplica", ad.assinar(token, "Outra Pessoa", "529.982.247-25", "x@example.com", 1)["assinante_nome"] == "Cliente Assina Teste")
		frappe.set_user("Administrator")

		f2 = frappe.get_doc({"doctype": "File", "file_name": "Contrato - teste v1.pdf", "attached_to_doctype": "CRM Deal",
							 "attached_to_name": d.name, "is_private": 1, "content": pdf}).insert(ignore_permissions=True)
		t2 = ad.enviar_para_assinatura(d.name, f2.name, avisar=0)["link"].split("t=")[1]
		with open(frappe.get_site_path(f2.file_url.lstrip("/")), "wb") as fh:
			fh.write(pdf + b"\n% alterado")
		frappe.set_user("Guest")
		erro = None
		try:
			ad.assinar(t2, "Cliente Assina Teste", "529.982.247-25", "cliente@example.com", 1)
		except frappe.ValidationError as e:
			erro = str(e)
		frappe.set_user("Administrator")
		ck("recusa assinar documento alterado depois do envio", erro and "alterado" in erro)
		ck("lista as assinaturas do caso", len(ad.listar(d.name)) == 2)
	finally:
		frappe.set_user("Administrator")
		frappe.db.delete("CRM Assinatura", {"deal": d.name})
		for fl in frappe.get_all("File", filters={"attached_to_doctype": "CRM Deal", "attached_to_name": d.name}, pluck="name"):
			frappe.delete_doc("File", fl, force=True, ignore_permissions=True)
		frappe.delete_doc("CRM Deal", d.name, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res
