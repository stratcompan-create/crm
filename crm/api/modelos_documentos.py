# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Modelos de documentos: contrato de honorários, procuração, declaração, recibo...
# O TEXTO é sempre do escritório (colado uma vez). O CRM só preenche os campos com os dados do
# negócio ({nome_cliente}, {valor}...) e monta o PDF com a marca e o estilo de cor escolhidos.
# O CRM não cria nem altera cláusulas.

import base64
import html as html_lib
import json
import re
import subprocess

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from crm.api import estilo

TIPOS = ["Contrato", "Procuração", "Declaração", "Recibo", "Outro"]
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
CLIENT_FIELDS = ["cpf_cnpj", "rg", "estado_civil", "profissao", "nacionalidade", "endereco"]

# chave -> (descrição, de onde vem)
VARIABLES = {
	"nome_cliente": "Nome completo do cliente",
	"primeiro_nome": "Primeiro nome",
	"empresa": "Empresa do cliente",
	"cpf_cnpj": "CPF ou CNPJ (preencher na hora)",
	"rg": "RG (preencher na hora)",
	"nacionalidade": "Nacionalidade (preencher na hora)",
	"estado_civil": "Estado civil (preencher na hora)",
	"profissao": "Profissão (preencher na hora)",
	"endereco": "Endereço completo (preencher na hora)",
	"cidade_estado": "Cidade / Estado",
	"email": "E-mail do cliente",
	"telefone": "Telefone do cliente",
	"servico": "Serviço contratado",
	"objeto": "Escopo combinado (da ficha da reunião) ou itens do orçamento",
	"prazo": "Prazo combinado (da ficha da reunião)",
	"valor": "Valor total, em reais",
	"valor_extenso": "Valor total por extenso",
	"valor_mensal": "Valor mensal, em reais (negócio recorrente)",
	"valor_mensal_extenso": "Valor mensal por extenso",
	"forma_pagamento": "Forma de pagamento (da cobrança)",
	"parcelas": "Parcelamento em texto (ex.: em 3 parcelas de R$ 500,00)",
	"data": "Data de hoje por extenso",
	"data_curta": "Data de hoje (dd/mm/aaaa)",
	"escritorio": "Nome do escritório",
	"responsavel": "Responsável pelo negócio",
	"numero_negocio": "Código do negócio",
}

EXAMPLE_NAME = "Exemplo de contrato (substitua pelo texto do seu escritório)"
EXAMPLE_BODY = """# CONTRATO DE PRESTAÇÃO DE SERVIÇOS

*Este é só um exemplo de como montar o modelo. Apague este texto e cole o modelo aprovado pelo seu escritório, marcando os dados variáveis com campos entre chaves.*

**CONTRATANTE:** {nome_cliente}, {nacionalidade}, {estado_civil}, {profissao}, inscrito(a) sob o CPF/CNPJ {cpf_cnpj}, RG {rg}, com endereço em {endereco}.

**CONTRATADO:** {escritorio}.

## Objeto
{objeto}

## Valor e forma de pagamento
O valor total é de {valor} ({valor_extenso}), {forma_pagamento}.

## Prazo
{prazo}

{data}

______________________________
{nome_cliente}

______________________________
{escritorio}
"""


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


# ------------------------------------------------------------------ modelos

@frappe.whitelist()
def get_variables() -> list:
	return [{"chave": k, "descricao": v} for k, v in VARIABLES.items()]


@frappe.whitelist()
def list_models() -> list:
	return frappe.get_all(
		"CRM Modelo Documento",
		filters={"ativo": 1},
		fields=["name", "tipo", "titulo"],
		order_by="tipo asc, name asc",
	)


@frappe.whitelist()
def get_model(nome: str) -> dict:
	_managers_only()
	doc = frappe.get_doc("CRM Modelo Documento", nome)
	return {"nome": doc.name, "tipo": doc.tipo, "titulo": doc.titulo or "", "corpo": doc.corpo or "", "ativo": cint(doc.ativo)}


@frappe.whitelist()
def save_model(nome: str, tipo: str, corpo: str, titulo: str = "", ativo=1, original: str = ""):
	_managers_only()
	nome = (nome or "").strip()[:120]
	if not nome or not (corpo or "").strip():
		frappe.throw(_("Informe o nome e o texto do modelo."))
	if tipo not in TIPOS:
		tipo = "Outro"
	unknown = sorted(set(re.findall(r"\{(\w+)\}", corpo)) - set(VARIABLES))
	values = {"tipo": tipo, "corpo": corpo, "titulo": (titulo or "").strip()[:140], "ativo": cint(ativo)}
	if original and original != nome and frappe.db.exists("CRM Modelo Documento", original):
		frappe.rename_doc("CRM Modelo Documento", original, nome, force=True)
	if frappe.db.exists("CRM Modelo Documento", nome):
		frappe.db.set_value("CRM Modelo Documento", nome, values)
	else:
		frappe.get_doc({"doctype": "CRM Modelo Documento", "nome": nome, **values}).insert()
	return {"ok": True, "campos_desconhecidos": unknown}


@frappe.whitelist()
def delete_model(nome: str):
	_managers_only()
	frappe.delete_doc("CRM Modelo Documento", nome)
	return {"ok": True}


def ensure_example():
	"""Um modelo de exemplo, só para mostrar como funciona. O advogado troca pelo texto dele."""
	if frappe.db.count("CRM Modelo Documento"):
		return
	frappe.get_doc(
		{"doctype": "CRM Modelo Documento", "nome": EXAMPLE_NAME, "tipo": "Contrato", "corpo": EXAMPLE_BODY, "ativo": 1}
	).insert(ignore_permissions=True)


# ------------------------------------------------------------------ dados do cliente e valores

def _extenso(value: float) -> str:
	from num2words import num2words

	return num2words(round(flt(value), 2), lang="pt_BR", to="currency")


def _brl(value) -> str:
	text = f"{flt(value):,.2f}"
	return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def _date_long(day=None) -> str:
	d = getdate(day or nowdate())
	return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def _client_data(deal) -> dict:
	try:
		data = json.loads(deal.get("dados_cliente") or "{}")
	except ValueError:
		data = {}
	return {k: str(data.get(k) or "").strip() for k in CLIENT_FIELDS}


@frappe.whitelist()
def get_client_data(deal: str) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("read")
	return _client_data(doc)


@frappe.whitelist()
def save_client_data(deal: str, dados):
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("write")
	dados = frappe.parse_json(dados) or {}
	clean = {k: str(dados.get(k) or "").strip()[:300] for k in CLIENT_FIELDS}
	frappe.db.set_value("CRM Deal", deal, "dados_cliente", json.dumps(clean, ensure_ascii=False), update_modified=False)
	return {"ok": True}


def _ficha(deal) -> dict:
	try:
		return json.loads(deal.get("ficha") or "{}")
	except ValueError:
		return {}


def _values(deal) -> dict:
	"""Todos os campos que um modelo pode usar, já resolvidos a partir do negócio."""
	from crm.api.automacoes import _client

	client = _client(deal.name)
	dados = _client_data(deal)
	ficha = _ficha(deal)
	settings = frappe.get_single("FCRM Settings")
	honor = frappe.get_all(
		"CRM Honorario",
		filters={"deal": deal.name},
		fields=["valor", "forma_pagamento", "tipo_honorario", "parcelas"],
		order_by="data_vencimento asc",
	)
	pontuais = [h for h in honor if h.tipo_honorario != "Consultivo Mensal"]
	total = flt(deal.get("deal_value")) or sum(flt(h.valor) for h in pontuais)
	mensal = flt(deal.get("valor_recorrente")) or sum(flt(h.valor) for h in honor if h.tipo_honorario == "Consultivo Mensal")
	n = len(pontuais)
	forma = next((h.forma_pagamento for h in honor if h.forma_pagamento), "")
	if n > 1 and total:
		parcelas = f"em {n} parcelas de {_brl(total / n)}"
	elif n == 1:
		parcelas = "em parcela única"
	else:
		parcelas = ""
	objeto = (ficha.get("escopo") or "").strip() or "; ".join(
		i.description.strip() for i in (deal.get("budget_items") or []) if (i.description or "").strip()
	)
	owner = frappe.db.get_value("User", deal.get("deal_owner"), "full_name") if deal.get("deal_owner") else ""
	nome = " ".join(filter(None, [deal.get("first_name"), deal.get("last_name")])) or client.completo
	values = {
		"nome_cliente": nome,
		"primeiro_nome": client.nome or nome.split(" ")[0],
		"empresa": deal.get("organization_name") or deal.get("organization") or "",
		**dados,
		"cidade_estado": deal.get("cidade_estado") or "",
		"email": client.email,
		"telefone": deal.get("mobile_no") or "",
		"servico": deal.get("servico") or "",
		"objeto": objeto,
		"prazo": (ficha.get("prazo") or "").strip(),
		"valor": _brl(total) if total else "",
		"valor_extenso": _extenso(total) if total else "",
		"valor_mensal": _brl(mensal) if mensal else "",
		"valor_mensal_extenso": _extenso(mensal) if mensal else "",
		"forma_pagamento": forma,
		"parcelas": parcelas,
		"data": _date_long(),
		"data_curta": getdate(nowdate()).strftime("%d/%m/%Y"),
		"escritorio": settings.get("brand_name") or "",
		"responsavel": owner or "",
		"numero_negocio": deal.name,
	}
	return {k: str(v or "").strip() for k, v in values.items()}


def _used_fields(body: str) -> list[str]:
	return list(dict.fromkeys(re.findall(r"\{(\w+)\}", body or "")))


@frappe.whitelist()
def check_model(deal: str, modelo: str) -> dict:
	"""O que falta preencher antes de gerar (campos vazios e campos que não existem)."""
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission("read")
	body = frappe.db.get_value("CRM Modelo Documento", modelo, "corpo") or ""
	values = _values(d)
	used = _used_fields(body)
	return {
		"faltando": [{"chave": k, "descricao": VARIABLES[k]} for k in used if k in VARIABLES and not values.get(k)],
		"desconhecidos": [k for k in used if k not in VARIABLES],
	}


# ------------------------------------------------------------------ montagem do PDF

def _inline(text: str) -> str:
	text = html_lib.escape(text)
	text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
	return re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)


def _body_html(text: str) -> str:
	"""Marcação simples: '# título', '## subtítulo', '---' quebra de página, '- ' lista, linha em branco separa parágrafos."""
	out, para, items = [], [], []

	def flush():
		nonlocal para, items
		if para:
			out.append("<p>" + "<br>".join(_inline(x) for x in para) + "</p>")
			para = []
		if items:
			out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>")
			items = []

	for raw in (text or "").splitlines():
		line = raw.rstrip()
		if not line.strip():
			flush()
		elif line.strip() == "---":
			flush()
			out.append('<div style="page-break-after:always"></div>')
		elif line.startswith("## "):
			flush()
			out.append(f"<h2>{_inline(line[3:])}</h2>")
		elif line.startswith("# "):
			flush()
			out.append(f"<h1>{_inline(line[2:])}</h1>")
		elif line.startswith("- "):
			if para:
				flush()
			items.append(line[2:])
		else:
			if items:
				flush()
			para.append(line)
	flush()
	return "".join(out)


def _document_css(pal: dict) -> str:
	from crm.api.proposta import _font_faces

	C, A, N = pal["cor"], pal["destaque"], pal["neutra"]
	style = pal["estilo"]
	head_bg = {"escuro": C, "cor": C, "claro": N, "branco": "#ffffff"}[style]
	head_ink = "#ffffff" if style in ("escuro", "cor") else C
	rule = A if style != "branco" else estilo.mix("#ffffff", C, 0.25)
	return f"""
	{_font_faces()}
	html, body {{ margin:0; padding:0; }}
	body {{ font-family:'Lora', Georgia, serif; font-size:10.5pt; line-height:1.55; color:#1d2a30; }}
	.head {{ background:{head_bg}; color:{head_ink}; padding:7mm 10mm; margin:-2mm 0 8mm 0; border-bottom:0.8mm solid {rule}; }}
	.head table {{ width:100%; border-collapse:collapse; }}
	.head td, .head .brand {{ color:{head_ink}; }}
	.head img {{ max-height:16mm; max-width:60mm; }}
	.head .brand {{ font-family:'Poppins', Arial, sans-serif; font-size:9pt; letter-spacing:0.18em; font-weight:600; }}
	.head .r {{ text-align:right; }}
	h1 {{ font-size:17pt; color:{C}; margin:0 0 5mm 0; text-align:center; }}
	h2 {{ font-size:12pt; color:{C}; margin:6mm 0 2mm 0; border-bottom:0.3mm solid {rule}; padding-bottom:1mm; }}
	p {{ margin:0 0 3.2mm 0; text-align:justify; }}
	ul {{ margin:0 0 3.2mm 5mm; padding:0; }}
	li {{ margin-bottom:1.2mm; }}
	"""


def _render_pdf(body_html: str, css: str, logo: str, brand: str, title: str) -> bytes:
	logo_html = f'<img src="{logo}">' if logo else f'<span class="brand">{html_lib.escape(brand.upper())}</span>'
	page = (
		f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>'
		f'<div class="head"><table><tr><td>{logo_html}</td>'
		f'<td class="r"><span class="brand">{html_lib.escape(title.upper())}</span></td></tr></table></div>'
		f"{body_html}</body></html>"
	)
	cmd = [
		"wkhtmltopdf", "-q", "--page-size", "A4", "-T", "14", "-B", "18", "-L", "20", "-R", "20",
		"--footer-center", "Página [page] de [topage]", "--footer-font-size", "8", "--footer-spacing", "6",
		"--print-media-type", "--background", "--encoding", "UTF-8", "--disable-javascript", "-", "-",
	]
	proc = subprocess.run(cmd, input=page.encode("utf-8"), capture_output=True, timeout=120)
	if not proc.stdout.startswith(b"%PDF"):
		frappe.log_error("Modelos: falha ao gerar o PDF", proc.stderr.decode("utf-8", "ignore")[-1500:])
		frappe.throw(_("Não foi possível gerar o PDF do documento."))
	return proc.stdout


def _build(corpo: str, values: dict, tipo: str, titulo: str, estilo_key: str, blank_missing: bool) -> bytes:
	from crm.api.proposta import _logo_data_uri

	settings = frappe.get_single("FCRM Settings")
	pal = estilo.resolve(settings, estilo_key or None)
	text = corpo
	for key in set(re.findall(r"\{(\w+)\}", corpo)):
		val = values.get(key, "")
		text = text.replace("{" + key + "}", val if val else ("__________" if blank_missing else ""))
	logo = _logo_data_uri(settings.get("brand_logo") or "") if settings.get("brand_logo") else ""
	return _render_pdf(_body_html(text), _document_css(pal), logo, settings.get("brand_name") or "", titulo or tipo)


@frappe.whitelist()
def generate(deal: str, modelo: str, estilo: str = "", forcar=0) -> dict:
	"""Gera o PDF do modelo com os dados do negócio e guarda na pasta do cliente."""
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission("write")
	chk = check_model(deal, modelo)
	if chk["desconhecidos"]:
		frappe.throw(_("O modelo usa campos que não existem: {0}.").format(", ".join("{" + k + "}" for k in chk["desconhecidos"])))
	if chk["faltando"] and not cint(forcar):
		return {"ok": False, "faltando": chk["faltando"]}
	m = frappe.get_doc("CRM Modelo Documento", modelo)
	values = _values(d)
	pdf = _build(m.corpo, values, m.tipo, m.titulo or m.name, estilo, blank_missing=True)
	client = values["nome_cliente"] or deal
	safe_client = re.sub(r'[\\/:*?"<>|]+', " ", client)[:60]
	base = f"{m.tipo} - {safe_client}"
	version = frappe.db.count(
		"File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal, "file_name": ["like", f"{base} v%"]}
	) + 1
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{base} v{version}.pdf",
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"is_private": 1,
			"content": pdf,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "CRM Deal",
			"reference_name": deal,
			"content": f"Documento gerado: {file.file_name}.",
		}
	).insert(ignore_permissions=True)
	return {"ok": True, "arquivo": file.name, "nome": file.file_name, "url": file.file_url, "faltando": chk["faltando"]}


SAMPLE = {
	"nome_cliente": "Maria da Silva Souza", "primeiro_nome": "Maria", "empresa": "Silva & Souza Ltda.", "cpf_cnpj": "000.000.000-00",
	"rg": "0.000.000", "nacionalidade": "brasileira", "estado_civil": "casada", "profissao": "empresária",
	"endereco": "Rua Exemplo, 100, Centro, Petrolina/PE", "cidade_estado": "Petrolina/PE", "email": "maria@exemplo.com",
	"telefone": "(87) 99999-0000", "servico": "Consultivo", "objeto": "Descrição do que será entregue.", "prazo": "60 dias",
	"valor": "R$ 3.000,00", "valor_extenso": "três mil reais", "valor_mensal": "R$ 500,00",
	"valor_mensal_extenso": "quinhentos reais", "forma_pagamento": "via PIX", "parcelas": "em 3 parcelas de R$ 1.000,00",
	"numero_negocio": "CRM-DEAL-0000", "responsavel": "Responsável",
}


@frappe.whitelist()
def preview_model(corpo: str, tipo: str = "Contrato", titulo: str = "", estilo: str = "") -> dict:
	"""Prévia com dados de exemplo (nada é salvo). Devolve o PDF em base64 para abrir na tela."""
	_managers_only()
	settings = frappe.get_single("FCRM Settings")
	values = {**SAMPLE, "data": _date_long(), "data_curta": getdate(nowdate()).strftime("%d/%m/%Y"),
	          "escritorio": settings.get("brand_name") or "Seu Escritório"}
	pdf = _build(corpo, values, tipo, titulo or tipo, estilo, blank_missing=False)
	return {"pdf": base64.b64encode(pdf).decode()}


@frappe.whitelist()
def send_generated(deal: str, arquivo: str):
	from frappe.core.doctype.communication.email import make

	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission("write")
	file = frappe.get_doc("File", arquivo)
	if file.attached_to_name != deal:
		frappe.throw(_("Arquivo não pertence a este negócio."))
	from crm.api.automacoes import _client

	client = _client(deal)
	if not client.email:
		frappe.throw(_("Este negócio não tem e-mail cadastrado."))
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		frappe.throw(_("Configure o e-mail de envio em Configurações → E-mail antes de enviar."))
	brand = frappe.db.get_single_value("FCRM Settings", "brand_name") or ""
	text = f"Olá, {client.nome}!\n\nSegue em anexo o documento para a sua conferência. Qualquer dúvida, é só responder este e-mail.\n\n{brand}"
	make(
		doctype="CRM Deal",
		name=deal,
		content=frappe.utils.escape_html(text).replace("\n", "<br>"),
		subject=(file.file_name.rsplit(".", 1)[0] + (f" — {brand}" if brand else "")),
		recipients=client.email,
		communication_medium="Email",
		send_email=True,
		attachments=[file.name],
	)
	return {"ok": True}
