# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Follow-up automático de prospecção.
#
# O CRM percebe sozinho quem foi abordado e não respondeu, cria o follow-up como tarefa
# ligada ao lead (aparece em Tarefas, no Calendário e na linha do tempo do lead) e deixa a
# mensagem pronta, com o nome da pessoa e o tipo de abordagem.
#
# Por que não envia sozinho: a Meta só permite mensagem pela API até 24 horas depois da última
# mensagem da própria pessoa. Abordar de novo quem não respondeu é proibido e arrisca a conta.
# Por isso a mensagem sai pelas mãos do usuário, com um clique (ig.me / wa.me).

import json
import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, cint, get_datetime, getdate, now_datetime, nowdate

DEFAULT_MESSAGE = (
	"Oi, {nome}! Passando para retomar nossa conversa. Você chegou a ver minha mensagem? "
	"Se fizer sentido, posso te explicar em poucos minutos. E se não for o momento, sem problema."
)

DEFAULT_ABORDAGENS = {
	"Site": (
		"Oi, {nome}! Voltei aqui para saber se você viu minha mensagem sobre o site do seu negócio. "
		"Posso te mostrar em 2 minutos como ficaria o seu? Se não fizer sentido agora, sem problema."
	),
	"Conteúdo": (
		"Oi, {nome}, tudo bem? Retomando: dá para transformar o que você já sabe em conteúdo "
		"que apresenta o seu trabalho para quem ainda não te conhece. Quer que eu te mande um exemplo?"
	),
	"CRM": (
		"Oi, {nome}! Retomando nossa conversa: o CRM que comentei organiza contatos, propostas e "
		"financeiro do seu negócio em um só lugar. Posso te mostrar rapidinho como funciona?"
	),
	"Outra": DEFAULT_MESSAGE,
}

OPEN_TASK = ["not in", ["Done", "Canceled"]]


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


# ------------------------------------------------------------------ configuração

def ensure_defaults():
	"""Cria os tipos de abordagem padrão (uma vez) para o escritório já poder usar."""
	for nome, msg in DEFAULT_ABORDAGENS.items():
		if not frappe.db.exists("CRM Abordagem", nome):
			frappe.get_doc({"doctype": "CRM Abordagem", "nome": nome, "mensagem": msg, "ativa": 1}).insert(
				ignore_permissions=True
			)


def _config():
	c = frappe.get_single("CRM Follow-up Config")
	origens = [o.strip() for o in (c.origens or "Instagram\nWhatsApp").split("\n") if o.strip()]
	return {
		"ativado": cint(c.ativado),
		"primeiro_dias": max(1, cint(c.primeiro_dias) or 2),
		"segundo_dias": max(1, cint(c.segundo_dias) or 4),
		"maximo": max(1, cint(c.maximo) or 2),
		"origens": origens,
		"mensagem_padrao": c.mensagem_padrao or DEFAULT_MESSAGE,
	}


@frappe.whitelist()
def get_settings() -> dict:
	_managers_only()
	ensure_defaults()
	cfg = _config()
	cfg["abordagens"] = frappe.get_all(
		"CRM Abordagem", fields=["nome", "mensagem", "ativa"], order_by="creation asc"
	)
	return cfg


@frappe.whitelist()
def save_settings(ativado=1, primeiro_dias=2, segundo_dias=4, maximo=2):
	_managers_only()
	for field, value in (
		("ativado", cint(ativado)),
		("primeiro_dias", max(1, cint(primeiro_dias))),
		("segundo_dias", max(1, cint(segundo_dias))),
		("maximo", max(1, min(cint(maximo), 5))),
	):
		frappe.db.set_single_value("CRM Follow-up Config", field, value)
	return {"ok": True}


@frappe.whitelist()
def save_abordagem(nome: str, mensagem: str):
	_managers_only()
	nome = (nome or "").strip()
	if not nome:
		frappe.throw(_("Informe o nome da abordagem."))
	if "{nome}" not in (mensagem or ""):
		frappe.throw(_("A mensagem precisa ter {nome} para o CRM colocar o nome da pessoa."))
	if frappe.db.exists("CRM Abordagem", nome):
		frappe.db.set_value("CRM Abordagem", nome, {"mensagem": mensagem, "ativa": 1})
	else:
		frappe.get_doc({"doctype": "CRM Abordagem", "nome": nome, "mensagem": mensagem, "ativa": 1}).insert()
	return {"ok": True}


@frappe.whitelist()
def delete_abordagem(nome: str):
	_managers_only()
	frappe.delete_doc("CRM Abordagem", nome)
	return {"ok": True}


# ------------------------------------------------------------------ registrar abordagem

@frappe.whitelist()
def get_abordagens() -> list:
	ensure_defaults()
	return frappe.get_all("CRM Abordagem", filters={"ativa": 1}, pluck="nome", order_by="creation asc")


@frappe.whitelist()
def register_approach(nome: str, canal: str = "Instagram", abordagem: str = "", usuario: str = "", telefone: str = ""):
	"""Registra uma pessoa que acabou de ser abordada. Cria o lead, conta a abordagem na
	Prospecção de hoje e começa a contar o prazo do follow-up."""
	frappe.has_permission("CRM Lead", "create", throw=True)
	nome = (nome or "").strip()
	canal = canal if canal in ("Instagram", "WhatsApp") else "Instagram"
	usuario = (usuario or "").strip().lstrip("@")
	telefone = re.sub(r"\D", "", telefone or "")
	if not nome and not usuario:
		frappe.throw(_("Informe o nome ou o @ da pessoa."))
	if canal == "WhatsApp" and not telefone:
		frappe.throw(_("Informe o telefone (com DDD) para abordar pelo WhatsApp."))
	if abordagem and not frappe.db.exists("CRM Abordagem", abordagem):
		frappe.throw(_("Abordagem não encontrada."))

	existing = None
	if usuario:
		existing = frappe.db.get_value("CRM Lead", {"instagram_username": usuario})
	if not existing and telefone:
		existing = frappe.db.get_value("CRM Lead", {"mobile_no": telefone})
	if existing:
		lead = frappe.get_doc("CRM Lead", existing)
		lead.check_permission("write")
		status = "atualizado"
	else:
		first, _sep, last = (nome or usuario).partition(" ")
		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"first_name": first,
				"last_name": last,
				"source": canal,
				"instagram_username": usuario,
				"mobile_no": telefone,
				"lead_owner": frappe.session.user,
			}
		)
		lead.insert()
		status = "criado"

	lead.db_set(
		{
			"abordagem": abordagem or None,
			"abordado_em": now_datetime(),
			"followups_feitos": 0,
			"ultimo_followup_em": None,
		},
		update_modified=False,
	)
	_count_approach_today()
	return {"lead": lead.name, "status": status}


def _count_approach_today():
	today = nowdate()
	if frappe.db.exists("CRM Prospecao Dia", today):
		current = cint(frappe.db.get_value("CRM Prospecao Dia", today, "abordados"))
		frappe.db.set_value("CRM Prospecao Dia", today, "abordados", current + 1)
	else:
		frappe.get_doc({"doctype": "CRM Prospecao Dia", "data": today, "abordados": 1}).insert(
			ignore_permissions=True
		)


# ------------------------------------------------------------------ o motor

def replied_since(lead: str, since) -> bool:
	"""A pessoa respondeu depois de `since`? (Instagram e, quando existir, WhatsApp)"""
	if frappe.db.count(
		"CRM Instagram Message", {"lead": lead, "direction": "Received", "timestamp": [">", since]}
	):
		return True
	try:
		if frappe.db.exists("DocType", "WhatsApp Message"):
			return bool(
				frappe.db.count(
					"WhatsApp Message",
					{"reference_doctype": "CRM Lead", "reference_name": lead, "type": "Incoming", "creation": [">", since]},
				)
			)
	except Exception:
		pass
	return False


def build_draft(lead) -> str:
	cfg = _config()
	template = None
	if lead.get("abordagem"):
		template = frappe.db.get_value("CRM Abordagem", lead.abordagem, "mensagem")
	template = template or cfg["mensagem_padrao"]
	return template.replace("{nome}", (lead.get("first_name") or "").strip() or "tudo bem")


def deep_link(lead, draft: str) -> str:
	if lead.get("source") == "WhatsApp" and lead.get("mobile_no"):
		digits = re.sub(r"\D", "", lead.mobile_no)
		if not digits.startswith("55") and len(digits) <= 11:
			digits = "55" + digits
		return f"https://wa.me/{digits}?text={quote(draft)}"
	if lead.get("instagram_username"):
		return f"https://ig.me/m/{lead.instagram_username}"
	return ""


def _responsible(lead) -> str:
	if lead.get("lead_owner"):
		return lead.lead_owner
	managers = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["Sales Manager", "System Manager"]], "parenttype": "User", "parent": ["not in", ["Administrator", "Guest"]]},
		pluck="parent",
		limit=1,
	)
	return managers[0] if managers else "Administrator"


def run_followups():
	"""Job de hora em hora: cria o follow-up de quem foi abordado e não respondeu no prazo."""
	cfg = _config()
	if not cfg["ativado"]:
		return
	ensure_defaults()
	now = now_datetime()
	leads = frappe.get_all(
		"CRM Lead",
		filters={"converted": 0, "abordado_em": ["is", "set"], "source": ["in", cfg["origens"]]},
		fields=[
			"name", "first_name", "last_name", "source", "abordagem", "abordado_em", "followups_feitos",
			"ultimo_followup_em", "instagram_username", "mobile_no", "lead_owner",
		],
	)
	created = 0
	for lead in leads:
		done = cint(lead.followups_feitos)
		if done >= cfg["maximo"]:
			continue
		base = lead.ultimo_followup_em or lead.abordado_em
		wait_days = cfg["primeiro_dias"] if done == 0 else cfg["segundo_dias"]
		if now < add_to_date(get_datetime(base), days=wait_days):
			continue
		if replied_since(lead.name, lead.abordado_em):
			continue
		if frappe.db.exists(
			"CRM Task",
			{"reference_doctype": "CRM Lead", "reference_docname": lead.name, "title": ["like", "Follow-up:%"], "status": OPEN_TASK},
		):
			continue
		_create_task(lead, done + 1)
		frappe.db.set_value(
			"CRM Lead", lead.name, {"followups_feitos": done + 1, "ultimo_followup_em": now}, update_modified=False
		)
		created += 1
	if created:
		frappe.db.commit()
	return created


def _create_task(lead, number: int):
	nome = " ".join(filter(None, [lead.first_name, lead.last_name]))
	draft = build_draft(lead)
	link = deep_link(lead, draft)
	canal = lead.source or "Instagram"
	desc = (
		f"<p>{frappe.utils.escape_html(nome)} foi abordado(a) pelo {canal} e não respondeu. "
		f"Este é o follow-up {number}.</p>"
		f"<p><b>Mensagem sugerida:</b><br>{frappe.utils.escape_html(draft)}</p>"
	)
	if link:
		desc += f'<p><a href="{link}">Abrir a conversa</a></p>'
	task = frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": f"Follow-up: {nome}",
			"status": "Todo",
			"priority": "Medium",
			"assigned_to": _responsible(lead),
			"reference_doctype": "CRM Lead",
			"reference_docname": lead.name,
			"due_date": now_datetime(),
			"description": desc,
		}
	).insert(ignore_permissions=True)
	try:
		frappe.get_doc("CRM Lead", lead.name).add_comment(
			"Comment", f"Follow-up {number} criado automaticamente: sem resposta desde a abordagem."
		)
	except Exception:
		pass
	return task


# ------------------------------------------------------------------ telas

@frappe.whitelist()
def get_pending_followups() -> list[dict]:
	"""Follow-ups em aberto (das tarefas), já com a mensagem e o link para enviar."""
	tasks = frappe.get_list(
		"CRM Task",
		filters={"reference_doctype": "CRM Lead", "title": ["like", "Follow-up:%"], "status": OPEN_TASK},
		fields=["name", "title", "reference_docname", "due_date", "assigned_to"],
		order_by="due_date asc",
		limit_page_length=100,
	)
	out = []
	for t in tasks:
		if not frappe.has_permission("CRM Lead", "read", t.reference_docname):
			continue
		lead = frappe.get_doc("CRM Lead", t.reference_docname)
		draft = build_draft(lead)
		out.append(
			{
				"task": t.name,
				"lead": lead.name,
				"nome": " ".join(filter(None, [lead.first_name, lead.last_name])),
				"canal": lead.source,
				"usuario": lead.get("instagram_username") or "",
				"abordagem": lead.get("abordagem") or "",
				"abordado_em": lead.get("abordado_em"),
				"numero": cint(lead.get("followups_feitos")),
				"mensagem": draft,
				"link": deep_link(lead, draft),
			}
		)
	return out


@frappe.whitelist()
def complete_followup(task: str):
	doc = frappe.get_doc("CRM Task", task)
	doc.check_permission("write")
	doc.status = "Done"
	doc.save()
	return {"ok": True}


# ------------------------------------------------------------------ entendimento do lead

INTEREST = ("orçamento", "orcamento", "valor", "preço", "preco", "quanto custa", "proposta", "reunião", "reuniao", "agendar", "contratar", "quero", "tenho interesse", "me interessa")
OBJECTIONS = {
	"Preço": ("caro", "não tenho verba", "sem verba", "muito alto"),
	"Momento": ("agora não", "sem tempo", "depois eu vejo", "mais pra frente", "outro momento"),
	"Já tem fornecedor": ("já tenho", "já temos", "já trabalho com"),
}


def analyze_lead(lead: str) -> dict:
	"""Leitura simples e transparente da conversa: temperatura, objeção e próxima ação."""
	msgs = frappe.get_all(
		"CRM Instagram Message",
		filters={"lead": lead},
		fields=["direction", "message", "timestamp"],
		order_by="timestamp asc",
	)
	received = [m for m in msgs if m.direction == "Received"]
	text = " ".join((m.message or "").lower() for m in received)
	if not received:
		return {"temperatura": "Frio", "motivo": "Ainda não respondeu.", "objecao": "", "proxima": "Aguardar o prazo do follow-up."}
	last = msgs[-1]
	hours = (now_datetime() - get_datetime(last.timestamp)).total_seconds() / 3600
	interest = any(k in text for k in INTEREST)
	objection = next((name for name, keys in OBJECTIONS.items() if any(k in text for k in keys)), "")
	if last.direction == "Received" and hours >= 1:
		proxima = "Responder agora: a pessoa está esperando." if hours < 24 else "Responder hoje; passou de 24h, use o Instagram para enviar."
	elif last.direction == "Sent" and hours >= 48:
		proxima = "Fazer um follow-up."
	else:
		proxima = "Aguardar a resposta."
	if interest and hours < 72:
		temp, motivo = "Quente", "Falou de valor, proposta ou reunião recentemente."
	elif hours < 168:
		temp, motivo = "Morno", "Respondeu na última semana."
	else:
		temp, motivo = "Frio", "Sem conversa há mais de uma semana."
	return {"temperatura": temp, "motivo": motivo, "objecao": objection, "proxima": proxima}
