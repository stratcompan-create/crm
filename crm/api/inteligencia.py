# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Inteligência do escritório:
# - Modelos de área: documentos, perguntas da consulta e honorário padrão de cada área.
# - Rentabilidade por área e por cliente (honorários, custas que ficaram com o escritório, horas).
# - Comunicados à carteira (só para quem já é cliente: informativo, sem captação).
# - Tabela de honorários (a da seccional da OAB e a praticada pelo escritório).

import base64
import io

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime, nowdate

AREAS_PADRAO = {
	"Trabalhista": {
		"documentos": ["Carteira de trabalho (física ou digital)", "Holerites / contracheques", "Termo de rescisão (TRCT)",
					   "Extrato do FGTS", "Provas da jornada (cartão de ponto, escalas, mensagens)"],
		"perguntas": ["Nome da empresa e função exercida", "Data de entrada e de saída", "Como saiu (pediu demissão, foi demitido, acordo)",
					  "O que não foi pago", "Tem testemunhas ou provas?"],
		"tipo": "Êxito", "pct": 30,
	},
	"Previdenciário": {
		"documentos": ["Extrato do INSS (CNIS)", "Carta de indeferimento do INSS", "Carteiras de trabalho",
					   "Laudos e exames médicos (se for por doença)", "Documentos do trabalho rural (se houver)"],
		"perguntas": ["Qual benefício foi pedido", "Data do pedido e da resposta do INSS", "Tempo de contribuição",
					  "Doença ou incapacidade (se houver)"],
		"tipo": "Êxito", "pct": 30,
	},
	"Família e Sucessões": {
		"documentos": ["Certidão de casamento ou de união estável", "Certidão de nascimento dos filhos", "Comprovantes de renda",
					   "Documentos dos bens (matrícula, documento do veículo)", "Comprovantes de despesas dos filhos"],
		"perguntas": ["Existe acordo entre as partes?", "Há filhos menores?", "Há bens a partilhar?", "Há pensão envolvida?"],
		"tipo": "Fixo", "pct": 0,
	},
	"Consumidor": {
		"documentos": ["Comprovante da compra ou contrato", "Protocolos e prints do atendimento", "Faturas e cobranças",
					   "Comprovante da negativação (se houver)"],
		"perguntas": ["Qual a empresa", "O que aconteceu e quando", "Valores envolvidos", "Já reclamou? Tem protocolo?"],
		"tipo": "Êxito", "pct": 30,
	},
	"Civil": {
		"documentos": ["Contrato ou documento da relação", "Comprovantes de pagamento", "Notificações e mensagens trocadas"],
		"perguntas": ["Quem é a outra parte", "O que foi combinado e o que não foi cumprido", "Valores envolvidos"],
		"tipo": "Fixo", "pct": 0,
	},
}


def _gestor():
	frappe.only_for(("System Manager", "Sales Manager"))


def _linhas(texto) -> list[str]:
	return [l.strip(" -•\t") for l in (texto or "").splitlines() if l.strip(" -•\t")]


# ------------------------------------------------------------------ modelos de área

def semear_areas(forcar=False):
	"""Cria os modelos de área padrão (só quando a lista está vazia)."""
	if not frappe.db.exists("DocType", "CRM Modelo Area"):
		return
	if frappe.db.count("CRM Modelo Area") and not forcar:
		return
	for area, m in AREAS_PADRAO.items():
		if frappe.db.exists("CRM Modelo Area", area):
			continue
		frappe.get_doc({"doctype": "CRM Modelo Area", "area": area, "documentos": "\n".join(m["documentos"]),
						"perguntas": "\n".join(m["perguntas"]), "tipo_honorario": m["tipo"], "percentual_exito": m["pct"],
						"observacoes": _("Padrão sugerido pelo CRM. Ajuste ao jeito do escritório.")}).insert(ignore_permissions=True)


def semear_se_juridico():
	from crm.provision import PERFIS_JURIDICOS, get_profile

	if get_profile() in PERFIS_JURIDICOS:
		semear_areas()


def modelo_da_area(area: str | None) -> dict | None:
	if not area or not frappe.db.exists("DocType", "CRM Modelo Area"):
		return None
	m = frappe.db.get_value("CRM Modelo Area", area, ["documentos", "perguntas", "tipo_honorario", "percentual_exito"], as_dict=True)
	if not m:
		return None
	return {"documentos": _linhas(m.documentos), "perguntas": _linhas(m.perguntas), "tipo_honorario": m.tipo_honorario,
			"percentual_exito": flt(m.percentual_exito)}


def aplicar_padrao_area(doc, method=None):
	"""Caso novo (ou que mudou de área) recebe o êxito padrão da área, se ainda não tiver percentual."""
	try:
		if not doc.meta.has_field("percentual_exito") or flt(doc.get("percentual_exito")):
			return
		if not (doc.is_new() or doc.has_value_changed("servico")):
			return
		m = modelo_da_area(doc.get("servico"))
		if m and m["percentual_exito"]:
			doc.percentual_exito = m["percentual_exito"]
	except Exception:
		frappe.log_error("Modelo de área: falha ao aplicar o padrão", frappe.get_traceback())


@frappe.whitelist()
def listar_areas() -> list[dict]:
	_gestor()
	return frappe.get_all("CRM Modelo Area", fields=["name", "area", "documentos", "perguntas", "tipo_honorario", "percentual_exito", "observacoes"],
						  order_by="area asc")


@frappe.whitelist()
def salvar_area(dados) -> dict:
	_gestor()
	dados = frappe.parse_json(dados) or {}
	area = (dados.get("area") or "").strip()
	if not area:
		frappe.throw(_("Informe a área."))
	if dados.get("name") and frappe.db.exists("CRM Modelo Area", dados["name"]):
		d = frappe.get_doc("CRM Modelo Area", dados["name"])
	else:
		d = frappe.new_doc("CRM Modelo Area")
		d.area = area
	for c in ("documentos", "perguntas", "tipo_honorario", "percentual_exito", "observacoes"):
		if c in dados:
			d.set(c, dados[c])
	d.save(ignore_permissions=True)
	if not frappe.db.exists("CRM Servico", area):
		frappe.get_doc({"doctype": "CRM Servico", "nome": area, "ativo": 1}).insert(ignore_permissions=True)
	return {"name": d.name}


@frappe.whitelist()
def excluir_area(name: str) -> dict:
	_gestor()
	frappe.delete_doc("CRM Modelo Area", name, ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def restaurar_areas_padrao() -> dict:
	_gestor()
	semear_areas(forcar=True)
	return {"ok": True}


@frappe.whitelist()
def perguntas_do_caso(doctype: str, name: str) -> list[str]:
	"""Perguntas da primeira consulta para a área do atendimento/caso (aparecem na ficha)."""
	if doctype not in ("CRM Lead", "CRM Deal"):
		return []
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	m = modelo_da_area(doc.get("servico"))
	return m["perguntas"] if m else []


# ------------------------------------------------------------------ rentabilidade

@frappe.whitelist()
def rentabilidade(dias: int = 365) -> dict:
	"""Por área e por cliente: honorários recebidos, a receber, custas do escritório, horas e R$/hora."""
	_gestor()
	desde = add_days(nowdate(), -cint(dias))
	deals = {d.name: d for d in frappe.get_all("CRM Deal", fields=["name", "servico", "lead_name", "organization", "first_name", "last_name"], limit=50000)}

	def novo():
		return {"recebido": 0.0, "a_receber": 0.0, "custas": 0.0, "horas": 0.0, "casos": set()}

	por_area, por_cliente = {}, {}

	def soma(deal, campo, valor):
		d = deals.get(deal)
		if not d:
			return
		area = d.servico or _("Sem área")
		cliente = d.lead_name or d.organization or f"{d.first_name or ''} {d.last_name or ''}".strip() or deal
		for alvo, chave in ((por_area, area), (por_cliente, cliente)):
			r = alvo.setdefault(chave, novo())
			r[campo] += flt(valor)
			r["casos"].add(deal)

	for h in frappe.get_all("CRM Honorario", filters={"status": "Pago", "data_pagamento": [">=", desde]}, fields=["deal", "valor"]):
		soma(h.deal, "recebido", h.valor)
	for h in frappe.get_all("CRM Honorario", filters={"status": ["in", ["Pendente", "Atrasado"]]}, fields=["deal", "valor"]):
		soma(h.deal, "a_receber", h.valor)
	desp_filtro = {"deal": ["is", "set"], "data_vencimento": [">=", desde]}
	if frappe.get_meta("CRM Despesa").has_field("reembolsado"):
		desp_filtro["reembolsado"] = 0
	for x in frappe.get_all("CRM Despesa", filters=desp_filtro, fields=["deal", "valor"]):
		soma(x.deal, "custas", x.valor)
	if frappe.db.exists("DocType", "CRM Horas"):
		for x in frappe.get_all("CRM Horas", filters={"data": [">=", desde]}, fields=["deal", "horas"]):
			soma(x.deal, "horas", x.horas)

	def fechar(dic, limite=None):
		out = []
		for nome, r in dic.items():
			liquido = r["recebido"] - r["custas"]
			out.append({"nome": nome, "casos": len(r["casos"]), "recebido": round(r["recebido"], 2), "a_receber": round(r["a_receber"], 2),
						"custas": round(r["custas"], 2), "liquido": round(liquido, 2), "horas": round(r["horas"], 1),
						"por_hora": round(liquido / r["horas"], 2) if r["horas"] else None})
		out.sort(key=lambda x: x["liquido"], reverse=True)
		return out[:limite] if limite else out

	return {"areas": fechar(por_area), "clientes": fechar(por_cliente, 15)}


# ------------------------------------------------------------------ comunicados à carteira

def _destinatarios(area: str | None, situacao: str) -> list[dict]:
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")
	filtros = {"status": ["in", won]}
	if area:
		filtros["servico"] = area
	if frappe.get_meta("CRM Deal").has_field("encerrado"):
		if situacao == "Ativos":
			filtros["encerrado"] = 0
		elif situacao == "Encerrados":
			filtros["encerrado"] = 1
	vistos, out = set(), []
	from crm.api.automacoes import _client

	for d in frappe.get_all("CRM Deal", filters=filtros, fields=["name"], limit=5000):
		c = _client(d.name)
		chave = (c.email or "").lower() or c.completo
		if not chave or chave in vistos:
			continue
		vistos.add(chave)
		tel = frappe.db.get_value("CRM Deal", d.name, "mobile_no") or ""
		out.append({"deal": d.name, "nome": c.completo, "email": c.email or "", "telefone": tel})
	return out


@frappe.whitelist()
def previa_comunicado(area: str | None = None, situacao: str = "Ativos") -> dict:
	_gestor()
	dest = _destinatarios(area or None, situacao)
	return {"total": len(dest), "com_email": sum(1 for d in dest if d["email"]),
			"tem_conta_email": bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))}


@frappe.whitelist()
def enviar_comunicado(titulo: str, mensagem: str, area: str | None = None, situacao: str = "Ativos") -> dict:
	_gestor()
	if not (titulo or "").strip() or not (mensagem or "").strip():
		frappe.throw(_("Escreva o assunto e a mensagem."))
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		frappe.throw(_("Configure um e-mail de envio (Configurações → E-mail) ou baixe a lista para avisar pelo WhatsApp."))
	dest = _destinatarios(area or None, situacao)
	enviados = 0
	for d in dest:
		if not d["email"]:
			continue
		texto = mensagem.replace("{nome}", (d["nome"] or "").split(" ")[0])
		frappe.sendmail(recipients=[d["email"]], subject=titulo.strip()[:140], message=frappe.utils.escape_html(texto).replace("\n", "<br>"),
						reference_doctype="CRM Deal", reference_name=d["deal"], delayed=True)
		enviados += 1
	frappe.get_doc({"doctype": "CRM Comunicado", "titulo": titulo.strip()[:140], "mensagem": mensagem, "area": area or None,
					"situacao": situacao, "destinatarios": len(dest), "enviados": enviados, "enviado_em": now_datetime()}).insert(ignore_permissions=True)
	return {"enviados": enviados, "sem_email": len(dest) - enviados}


@frappe.whitelist()
def lista_comunicado(area: str | None = None, situacao: str = "Ativos") -> dict:
	"""Planilha com nome, telefone e e-mail (para avisar pelo WhatsApp quem não tem e-mail)."""
	_gestor()
	from openpyxl import Workbook

	wb = Workbook()
	ws = wb.active
	ws.title = "Clientes"
	ws.append(["Nome", "Telefone", "E-mail"])
	for d in _destinatarios(area or None, situacao):
		ws.append([d["nome"], d["telefone"], d["email"]])
	buf = io.BytesIO()
	wb.save(buf)
	return {"arquivo": base64.b64encode(buf.getvalue()).decode(), "nome": f"Clientes - {area or 'todas as áreas'} - {situacao}.xlsx"}


@frappe.whitelist()
def historico_comunicados() -> list[dict]:
	_gestor()
	return frappe.get_all("CRM Comunicado", fields=["titulo", "area", "situacao", "destinatarios", "enviados", "enviado_em"],
						  order_by="creation desc", limit=20)


# ------------------------------------------------------------------ tabela de honorários

@frappe.whitelist()
def tabela_honorarios(q: str = "") -> list[dict]:
	filtros = {}
	or_f = None
	if (q or "").strip():
		like = f"%{q.strip()}%"
		or_f = {"descricao": ["like", like], "area": ["like", like]}
	return frappe.get_all("CRM Tabela Honorario", filters=filtros, or_filters=or_f,
						  fields=["name", "descricao", "area", "valor_tabela", "valor_escritorio", "percentual", "observacoes"],
						  order_by="area asc, descricao asc", limit=500)


@frappe.whitelist()
def salvar_item_tabela(dados) -> dict:
	_gestor()
	dados = frappe.parse_json(dados) or {}
	if not (dados.get("descricao") or "").strip():
		frappe.throw(_("Informe o serviço."))
	d = frappe.get_doc("CRM Tabela Honorario", dados["name"]) if dados.get("name") else frappe.new_doc("CRM Tabela Honorario")
	for c in ("descricao", "area", "valor_tabela", "valor_escritorio", "percentual", "observacoes"):
		if c in dados:
			d.set(c, dados[c])
	d.save(ignore_permissions=True)
	return {"name": d.name}


@frappe.whitelist()
def excluir_item_tabela(name: str) -> dict:
	_gestor()
	frappe.delete_doc("CRM Tabela Honorario", name, ignore_permissions=True)
	return {"ok": True}
