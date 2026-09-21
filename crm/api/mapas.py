# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Mapas de estratégia: quadros livres (fluxo, funil, upsell, cross-sell, jornada) desenhados dentro
# do CRM. O desenho é guardado como JSON (nós, ligações e posição da tela).

import json

import frappe
from frappe import _

MAX_BYTES = 1_000_000
MAX_NODES = 300


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _node(id_, label, x, y, icon="circle", color="blue", note="", kind="card"):
	return {
		"id": id_,
		"type": kind,
		"position": {"x": x, "y": y},
		"data": {"label": label, "note": note, "icon": icon, "color": color},
	}


def _edge(a, b, label="", animated=False):
	return {"id": f"e-{a}-{b}", "source": a, "target": b, "label": label, "animated": animated}


def _chain(steps, gap=260, y=120):
	nodes = [_node(f"n{i}", *s[:1], i * gap, y, *s[1:]) for i, s in enumerate(steps)]
	edges = [_edge(f"n{i}", f"n{i + 1}") for i in range(len(steps) - 1)]
	return nodes, edges


def _tpl_funil():
	return _chain(
		[
			("Atrair", "megaphone", "blue", "Conteúdo, indicação, anúncios"),
			("Conversar", "message-circle", "blue", "Instagram, WhatsApp, e-mail"),
			("Reunião", "calendar", "amber", "Entender o caso do cliente"),
			("Proposta", "file-text", "amber", "Escopo, prazo e investimento"),
			("Fechamento", "check-circle", "green", "Contrato e primeira cobrança"),
			("Pós-venda", "star", "green", "Avaliação e indicação"),
		]
	)


def _tpl_upsell():
	nodes = [
		_node("n0", "Cliente atual", 0, 160, "user", "blue", "Já contratou e está satisfeito"),
		_node("n1", "Serviço principal", 280, 160, "briefcase", "blue", "O que ele contratou primeiro"),
		_node("n2", "Upsell", 580, 20, "trending-up", "green", "Vender mais do mesmo: plano maior, mais escopo, mais frequência"),
		_node("n3", "Cross-sell", 580, 300, "layers", "amber", "Vender algo complementar que ele ainda não tem"),
		_node("n4", "Indicação", 900, 160, "users", "purple", "Pedir que apresente alguém"),
		_node("s1", "Quando oferecer? Depois de um resultado ou entrega bem-sucedida.", 280, 380, kind="sticky", color="yellow"),
	]
	edges = [
		_edge("n0", "n1"),
		_edge("n1", "n2", "resultado positivo"),
		_edge("n1", "n3", "nova necessidade"),
		_edge("n2", "n4"),
		_edge("n3", "n4"),
	]
	return nodes, edges


def _tpl_advogado():
	return _chain(
		[
			("Consulta inicial", "message-circle", "blue", "Triagem: área, viabilidade, conflito de interesses"),
			("Proposta e contrato", "file-text", "amber", "Honorários, contrato e procuração"),
			("Documentos", "folder-open", "amber", "Cliente envia pelo link seguro"),
			("Acompanhamento", "refresh-cw", "blue", "Atualizações ao cliente"),
			("Encerramento", "check-circle", "green", "Entrega e cobrança final"),
			("Indicação", "users", "purple", "Pedir indicação e avaliação"),
		]
	)


def _tpl_agencia():
	return _chain(
		[
			("Prospecção", "search", "blue", "Abordagem no Instagram e WhatsApp"),
			("Resposta", "message-circle", "blue", "Follow-up para quem não respondeu"),
			("Reunião", "calendar", "amber", "Diagnóstico do negócio"),
			("Proposta", "file-text", "amber", "Orçamento e escopo"),
			("Fechamento", "check-circle", "green", "Contrato e cobrança"),
			("Início", "rocket", "green", "Acessos, materiais, kickoff"),
			("Pós-venda", "star", "purple", "Avaliação, indicação, renovação"),
		],
		gap=250,
	)


def _tpl_branco():
	return (
		[_node("s1", "Arraste os blocos, conecte uns aos outros e monte a sua estratégia.", 40, 40, kind="sticky", color="yellow")],
		[],
	)


def _tpl_vivo():
	"""Funil ligado ao CRM: cada bloco mostra o número real e abre a lista."""
	steps = [
		("lead:New", "Leads novos", "users", "blue"),
		("lead:Contacted", "Leads em conversa", "message-circle", "blue"),
		("lead:Qualified", "Leads qualificados", "target", "amber"),
		("deal:Qualification", "Negócios em qualificação", "briefcase", "amber"),
		("deal:Proposal/Quotation", "Propostas enviadas", "file-text", "amber"),
		("deal:Negotiation", "Em negociação", "refresh-cw", "amber"),
		("deal:Won", "Negócios ganhos", "check-circle", "green"),
	]
	nodes = [
		_node(f"n{i}", label, i * 250, 100, icon, color, kind="data") for i, (_k, label, icon, color) in enumerate(steps)
	]
	for n, (key, *_rest) in zip(nodes, steps):
		n["data"]["metric"] = key
	edges = [_edge(f"n{i}", f"n{i + 1}") for i in range(len(steps) - 1)]
	money = [("receita_pendente", "A receber", "dollar-sign", "amber"), ("receita_atrasada", "Em atraso", "bell", "red"), ("recebido_mes", "Recebido no mês", "check-circle", "green")]
	for j, (key, label, icon, color) in enumerate(money):
		n = _node(f"m{j}", label, 500 + j * 250, 330, icon, color, kind="data")
		n["data"]["metric"] = key
		nodes.append(n)
	nodes.append(_node("s1", "Os números se atualizam sozinhos. Clique duas vezes num bloco para abrir a lista.", 0, 300, kind="sticky", color="yellow"))
	return nodes, edges


TEMPLATES = {
	"funil_vivo": ("Funil ao vivo (dados do CRM)", "Blocos com os números reais de leads, negócios e receita.", _tpl_vivo),
	"em_branco": ("Em branco", "Comece do zero, com liberdade total.", _tpl_branco),
	"funil": ("Funil de vendas", "Do primeiro contato ao pós-venda.", _tpl_funil),
	"upsell": ("Upsell e cross-sell", "Como vender mais para quem já é cliente.", _tpl_upsell),
	"advogado": ("Jornada do cliente (escritório)", "Da consulta à indicação.", _tpl_advogado),
	"agencia": ("Jornada do cliente (agência)", "Da prospecção à renovação.", _tpl_agencia),
}


@frappe.whitelist()
def get_templates() -> list:
	return [{"chave": k, "titulo": v[0], "descricao": v[1]} for k, v in TEMPLATES.items()]


def _payload(nodes, edges) -> str:
	return json.dumps({"nodes": nodes, "edges": edges, "viewport": {"x": 40, "y": 40, "zoom": 0.9}}, ensure_ascii=False)


@frappe.whitelist()
def list_maps() -> list:
	return frappe.get_all("CRM Mapa", fields=["name", "titulo", "modified", "owner"], order_by="modified desc", limit=100)


@frappe.whitelist()
def create_map(titulo: str = "", modelo: str = "em_branco") -> dict:
	_managers_only()
	key = modelo if modelo in TEMPLATES else "em_branco"
	title = (titulo or "").strip() or TEMPLATES[key][0]
	nodes, edges = TEMPLATES[key][2]()
	doc = frappe.get_doc({"doctype": "CRM Mapa", "titulo": title[:120], "dados": _payload(nodes, edges)}).insert()
	return {"name": doc.name}


@frappe.whitelist()
def get_map(name: str) -> dict:
	doc = frappe.get_doc("CRM Mapa", name)
	doc.check_permission("read")
	try:
		data = json.loads(doc.dados or "{}")
	except ValueError:
		data = {}
	return {
		"name": doc.name,
		"titulo": doc.titulo,
		"dados": {"nodes": data.get("nodes", []), "edges": data.get("edges", []), "viewport": data.get("viewport")},
		"pode_editar": bool(set(frappe.get_roles()) & {"System Manager", "Sales Manager"}),
	}


@frappe.whitelist()
def save_map(name: str, dados, titulo: str = ""):
	_managers_only()
	doc = frappe.get_doc("CRM Mapa", name)
	doc.check_permission("write")
	data = frappe.parse_json(dados) or {}
	nodes = (data.get("nodes") or [])[:MAX_NODES]
	edges = (data.get("edges") or [])[: MAX_NODES * 3]
	raw = json.dumps({"nodes": nodes, "edges": edges, "viewport": data.get("viewport")}, ensure_ascii=False)
	if len(raw.encode("utf-8")) > MAX_BYTES:
		frappe.throw(_("O mapa ficou grande demais para salvar. Remova alguns itens."))
	doc.dados = raw
	if titulo and titulo.strip():
		doc.titulo = titulo.strip()[:120]
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def duplicate_map(name: str) -> dict:
	_managers_only()
	src = frappe.get_doc("CRM Mapa", name)
	src.check_permission("read")
	doc = frappe.get_doc({"doctype": "CRM Mapa", "titulo": f"{src.titulo} (cópia)"[:120], "dados": src.dados}).insert()
	return {"name": doc.name}


@frappe.whitelist()
def delete_map(name: str):
	_managers_only()
	frappe.delete_doc("CRM Mapa", name)
	return {"ok": True}


# ------------------------------------------------------------------ blocos com dados do CRM

def _catalog() -> list:
	items = []
	for s in frappe.get_all("CRM Lead Status", fields=["name", "position"], order_by="position asc"):
		items.append({"key": f"lead:{s.name}", "label": _("Leads: {0}").format(_(s.name)), "grupo": "Leads", "tipo": "n", "route": "Leads"})
	items.append({"key": "leads_semana", "label": _("Leads novos nos últimos 7 dias"), "grupo": "Leads", "tipo": "n", "route": "Leads"})
	for s in frappe.get_all("CRM Deal Status", fields=["name", "position"], order_by="position asc"):
		items.append({"key": f"deal:{s.name}", "label": _("Negócios: {0}").format(_(s.name)), "grupo": "Negócios", "tipo": "n", "route": "Deals"})
	items += [
		{"key": "reunioes_semana", "label": _("Reuniões nos próximos 7 dias"), "grupo": "Agenda", "tipo": "n", "route": "Calendar"},
		{"key": "followups", "label": _("Follow-ups para enviar"), "grupo": "Tarefas", "tipo": "n", "route": "Tasks"},
		{"key": "tarefas_atrasadas", "label": _("Tarefas atrasadas"), "grupo": "Tarefas", "tipo": "n", "route": "Tasks"},
		{"key": "receita_pendente", "label": _("A receber"), "grupo": "Financeiro", "tipo": "brl", "route": "Financeiro"},
		{"key": "receita_atrasada", "label": _("Em atraso"), "grupo": "Financeiro", "tipo": "brl", "route": "Financeiro"},
		{"key": "recebido_mes", "label": _("Recebido no mês"), "grupo": "Financeiro", "tipo": "brl", "route": "Financeiro"},
	]
	return items


@frappe.whitelist()
def get_metrics() -> dict:
	"""Valores ao vivo dos blocos de dados do mapa."""
	_managers_only()
	from frappe.utils import add_days, flt, get_first_day, nowdate

	today = nowdate()
	values = {}
	for row in frappe.db.sql("select status, count(*) as n from `tabCRM Lead` group by status", as_dict=True):
		values[f"lead:{row.status}"] = row.n
	for row in frappe.db.sql("select status, count(*) as n from `tabCRM Deal` group by status", as_dict=True):
		values[f"deal:{row.status}"] = row.n
	values["leads_semana"] = frappe.db.count("CRM Lead", {"creation": [">=", f"{add_days(today, -7)} 00:00:00"]})
	values["reunioes_semana"] = frappe.db.count(
		"CRM Reuniao", {"status": "Agendada", "inicio": ["between", [f"{today} 00:00:00", f"{add_days(today, 7)} 23:59:59"]]}
	)
	values["followups"] = frappe.db.count(
		"CRM Task", {"title": ["like", "Follow-up:%"], "status": ["in", ["Backlog", "Todo", "In Progress"]]}
	)
	values["tarefas_atrasadas"] = frappe.db.count(
		"CRM Task", {"status": ["in", ["Backlog", "Todo", "In Progress"]], "due_date": ["<", f"{today} 00:00:00"]}
	)

	def money(filters):
		return flt(frappe.get_all("CRM Honorario", filters=filters, fields=["sum(valor) as t"])[0].t)

	values["receita_pendente"] = money({"status": "Pendente"})
	values["receita_atrasada"] = money({"status": "Atrasado"})
	values["recebido_mes"] = money({"status": "Pago", "data_pagamento": [">=", str(get_first_day(today))]})
	return {"catalogo": _catalog(), "valores": values}
