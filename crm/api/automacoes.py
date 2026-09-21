# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Automações que ligam as pontas do CRM:
#  - distribuição de leads entre os vendedores (regra de atribuição padrão);
#  - negócio ganho -> parcelas no Financeiro, contrato em PDF, conta do cliente e tarefas de início;
#  - cobrança: lembretes antes e depois do vencimento;
#  - pós-venda: pedido de avaliação e de indicação;
#  - relatório semanal por e-mail.
# O canal de envio hoje é o e-mail. O CRM decide QUANDO falar com o cliente; o envio fica em
# `_notify_client`, o único ponto a ajustar quando o WhatsApp oficial for conectado.

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

from crm.api.followup import OPEN_TASK

RULE_NAME = "Distribuição automática de leads"
RULE_MARK = "Distribuição automática entre os vendedores (mantida pelo CRM)"

DEFAULT_COBRANCA_ASSUNTO = "Lembrete de pagamento — {descricao}"
DEFAULT_COBRANCA = (
	"Olá, {nome}! Passando para lembrar do pagamento de {valor} ({descricao}), que {situacao}. "
	"Se já pagou, pode desconsiderar esta mensagem. Qualquer dúvida, é só responder por aqui."
)
DEFAULT_AVALIACAO = (
	"Olá, {nome}! Foi um prazer trabalhar com você. Sua opinião ajuda muito: "
	"pode deixar uma avaliação rápida sobre o nosso trabalho? {link}\n\nObrigado pela confiança!"
)
DEFAULT_INDICACAO = (
	"Olá, {nome}! Tudo certo com o nosso trabalho? Se você conhece alguém que também possa precisar, "
	"vou adorar receber uma indicação. Obrigado pela confiança!"
)

CONFIG_FIELDS = (
	"cobranca_ativa cobranca_dias_antes cobranca_dias_atraso cobranca_assunto cobranca_mensagem "
	"parcelas_padrao parcelas_intervalo onboarding_ativo posvenda_ativo posvenda_avaliacao_dias "
	"posvenda_avaliacao_link posvenda_avaliacao_mensagem posvenda_indicacao_dias posvenda_indicacao_mensagem "
	"relatorio_ativo relatorio_email relatorio_destinatarios agenda_ativa agenda_titulo agenda_duracao agenda_dias "
	"agenda_inicio agenda_fim agenda_antecedencia agenda_dias_a_frente agenda_responsavel agenda_link "
	"agenda_mensagem"
).split()

DEFAULTS = {
	"cobranca_ativa": 1,
	"cobranca_dias_antes": 3,
	"cobranca_dias_atraso": "1,7,15",
	"cobranca_assunto": DEFAULT_COBRANCA_ASSUNTO,
	"cobranca_mensagem": DEFAULT_COBRANCA,
	"parcelas_padrao": 1,
	"parcelas_intervalo": 30,
	"onboarding_ativo": 1,
	"posvenda_ativo": 1,
	"posvenda_avaliacao_dias": 7,
	"posvenda_avaliacao_mensagem": DEFAULT_AVALIACAO,
	"posvenda_indicacao_dias": 30,
	"posvenda_indicacao_mensagem": DEFAULT_INDICACAO,
	"relatorio_ativo": 1,
	"relatorio_email": 1,
	"agenda_ativa": 0,
	"agenda_titulo": "Conversa inicial",
	"agenda_duracao": 30,
	"agenda_dias": "1,2,3,4,5",
	"agenda_inicio": "09:00",
	"agenda_fim": "18:00",
	"agenda_antecedencia": 4,
	"agenda_dias_a_frente": 14,
}


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def get_config() -> frappe._dict:
	"""Configuração com padrões aplicados (a página só grava o que o gestor mudou)."""
	# só o que o gestor já salvou; o resto usa o padrão (um campo de marcar nunca salvo vale 0, não 'ligado')
	saved = frappe.db.get_singles_dict("CRM Automacoes Config") or {}
	out = frappe._dict()
	for key in CONFIG_FIELDS:
		value = saved.get(key)
		if value in (None, "") and key in DEFAULTS:
			value = DEFAULTS[key]
		out[key] = value
	return out


@frappe.whitelist()
def get_settings() -> dict:
	_managers_only()
	cfg = get_config()
	cfg["agenda_link_publico"] = frappe.utils.get_url("/agendar")
	cfg["agenda_responsavel"] = cfg.get("agenda_responsavel") or ""
	return cfg


@frappe.whitelist()
def save_settings(values):
	_managers_only()
	values = frappe.parse_json(values)
	for key, value in values.items():
		if key not in CONFIG_FIELDS:
			continue
		if isinstance(value, str):
			value = value.strip()
		frappe.db.set_single_value("CRM Automacoes Config", key, value)
	return {"ok": True}


# ------------------------------------------------------------------ utilidades

def _brl(value) -> str:
	text = f"{flt(value):,.2f}"
	return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def _date_br(value) -> str:
	return getdate(value).strftime("%d/%m/%Y")


def _fill(template: str, **values) -> str:
	text = template or ""
	for key, value in values.items():
		text = text.replace("{" + key + "}", str(value or ""))
	return text.strip()


def _brand() -> str:
	return frappe.db.get_single_value("FCRM Settings", "brand_name") or ""


def _client(deal: str) -> frappe._dict:
	d = frappe.db.get_value(
		"CRM Deal",
		deal,
		["first_name", "last_name", "lead_name", "organization_name", "email", "lead", "deal_owner", "closed_date"],
		as_dict=True,
	) or frappe._dict()
	email = d.get("email") or (frappe.db.get_value("CRM Lead", d.lead, "email") if d.get("lead") else "")
	first = (d.get("first_name") or (d.get("lead_name") or "").split(" ")[0] or "").strip()
	return frappe._dict(
		nome=first,
		completo=" ".join(filter(None, [d.get("first_name"), d.get("last_name")])) or d.get("organization_name") or deal,
		email=email or "",
		owner=d.get("deal_owner") or _first_manager(),
		lead=d.get("lead"),
	)


def _first_manager() -> str | None:
	for role in ("Sales Manager", "System Manager"):
		users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
		users = [u for u in users if u != "Administrator" and frappe.db.get_value("User", u, "enabled")]
		if users:
			return users[0]
	return "Administrator"


def _notify_client(deal: str, subject: str, message: str, task_title: str) -> str:
	"""Único ponto de envio ao cliente. Hoje é e-mail; sem e-mail (ou sem conta de envio)
	cria a tarefa para a pessoa responsável fazer o contato. O WhatsApp entra aqui."""
	client = _client(deal)
	if client.email and frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		from frappe.core.doctype.communication.email import make

		make(
			doctype="CRM Deal",
			name=deal,
			content=frappe.utils.escape_html(message).replace("\n", "<br>"),
			subject=subject,
			recipients=client.email,
			communication_medium="Email",
			send_email=True,
		)
		return "email"
	_create_task(deal, task_title, message, client.owner)
	return "tarefa"


def _create_task(deal: str, title: str, description: str, owner: str | None, days: int = 0):
	frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": title,
			"description": frappe.utils.escape_html(description or "").replace("\n", "<br>"),
			"status": "Todo",
			"priority": "Medium",
			"assigned_to": owner,
			"due_date": add_days(nowdate(), days),
			"reference_doctype": "CRM Deal",
			"reference_docname": deal,
		}
	).insert(ignore_permissions=True)


# ------------------------------------------------------------------ 1. distribuição de leads

def _sellers() -> list[str]:
	def users_with(role):
		names = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent")
		return [u for u in dict.fromkeys(names) if u != "Administrator" and frappe.db.get_value("User", u, "enabled")]

	return users_with("Sales User") or users_with("Sales Manager") or users_with("System Manager")


def sync_lead_distribution():
	"""Mantém uma regra de atribuição padrão para os leads, em rodízio entre os vendedores.
	Se o gestor editar a regra na mão, o CRM não mexe mais nela."""
	users = _sellers()
	if not users:
		return
	name = RULE_NAME if frappe.db.exists("Assignment Rule", RULE_NAME) else None
	if name:
		rule = frappe.get_doc("Assignment Rule", name)
		if rule.description != RULE_MARK:
			return
		if sorted(u.user for u in rule.users) == sorted(users):
			return
		rule.users = []
		for u in users:
			rule.append("users", {"user": u})
		rule.save(ignore_permissions=True)
		return
	rule = frappe.get_doc(
		{
			"doctype": "Assignment Rule",
			"name": RULE_NAME,
			"document_type": "CRM Lead",
			"description": RULE_MARK,
			"assign_condition": "not lead_owner",
			"rule": "Round Robin",
			"priority": 1,
			"disabled": 0,
			"assignment_days": [
				{"day": d}
				for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
			],
			"users": [{"user": u} for u in users],
		}
	)
	rule.insert(ignore_permissions=True)


def on_user_change(doc, method=None):
	"""Quando entra ou muda um vendedor, o rodízio já passa a contar com ele."""
	try:
		sync_lead_distribution()
	except Exception:
		frappe.log_error("Distribuição de leads: falha ao atualizar a regra", frappe.get_traceback())


# ------------------------------------------------------------------ 2. negócio ganho

def on_deal_won(deal_doc, valor: float) -> None:
	"""Chamado quando o negócio vira 'ganho': parcelas, contrato, conta do cliente e tarefas."""
	cfg = get_config()
	create_installments(deal_doc, valor, cint(cfg.parcelas_padrao) or 1, cint(cfg.parcelas_intervalo) or 30)
	try:
		_attach_contract(deal_doc)
	except Exception:
		frappe.log_error("Negócio ganho: não foi possível gerar o contrato", frappe.get_traceback())
	try:
		_ensure_client_account(deal_doc)
	except Exception:
		frappe.log_error("Negócio ganho: conta do cliente", frappe.get_traceback())
	if cint(cfg.onboarding_ativo):
		owner = deal_doc.deal_owner or _first_manager()
		for title, days in (
			(_("Início: dar boas-vindas ao cliente"), 1),
			(_("Início: combinar a reunião de kickoff"), 2),
			(_("Início: reunir acessos e materiais do cliente"), 5),
		):
			_create_task(deal_doc.name, f"{title} — {_client(deal_doc.name).completo}", "", owner, days)


def create_installments(deal_doc, valor: float, parcelas: int, intervalo: int):
	tipos = (frappe.get_meta("CRM Honorario").get_field("tipo_honorario").options or "").split("\n")
	tipo = tipos[0] if tipos and tipos[0] else None
	parcelas = max(1, min(parcelas, 36))
	base = round(valor / parcelas, 2)
	primeira = add_days(nowdate(), 30)
	for i in range(parcelas):
		this = base if i < parcelas - 1 else round(valor - base * (parcelas - 1), 2)
		due = add_days(primeira, intervalo * i) if intervalo != 30 else add_months(primeira, i)
		frappe.get_doc(
			{
				"doctype": "CRM Honorario",
				"deal": deal_doc.name,
				"status": "Pendente",
				"tipo_honorario": tipo,
				"servico": deal_doc._guess_service(),
				"valor": this,
				"parcelas": parcelas,
				"data_vencimento": due,
				"observacoes": _("Parcela {0} de {1}").format(i + 1, parcelas) if parcelas > 1 else "",
			}
		).insert(ignore_permissions=True)


def _attach_contract(deal_doc):
	"""Gera o contrato em PDF a partir do orçamento e deixa anexado ao negócio (envio é com um clique)."""
	if not (deal_doc.get("budget_items") or []):
		return
	if frappe.db.exists(
		"File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal_doc.name, "file_name": ["like", "Contrato v%"]}
	):
		return
	from crm.api.budget import build_document

	filename, content, _doc = build_document(deal_doc.name, "contrato")
	client = _client(deal_doc.name).completo
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Contrato v1 - {client}.pdf",
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal_doc.name,
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)


def _ensure_client_account(deal_doc):
	name = _client(deal_doc.name).completo
	if not name or frappe.db.exists("CRM Client Account", {"client_name": name}):
		return
	frappe.get_doc({"doctype": "CRM Client Account", "client_name": name, "status": "Ativo"}).insert(
		ignore_permissions=True
	)


# ------------------------------------------------------------------ 3. cobrança

def _atraso_days(cfg) -> set[int]:
	out = set()
	for part in str(cfg.cobranca_dias_atraso or "").split(","):
		if part.strip().isdigit():
			out.add(int(part.strip()))
	return out


def _reminder_due(due, today, cfg) -> bool:
	delta = (getdate(due) - today).days
	if delta >= 0:
		return delta in {cint(cfg.cobranca_dias_antes), 0}
	return -delta in _atraso_days(cfg)


def send_billing_reminders(force_for: str | None = None):
	"""Job diário. Cobra as parcelas que vencem em breve, vencem hoje ou estão atrasadas."""
	cfg = get_config()
	if not cint(cfg.cobranca_ativa) and not force_for:
		return 0
	today = getdate(nowdate())
	filters = {"name": force_for} if force_for else {"status": ["in", ["Pendente", "Atrasado"]]}
	sent = 0
	for h in frappe.get_all(
		"CRM Honorario",
		filters=filters,
		fields=["name", "deal", "valor", "data_vencimento", "servico", "ultimo_lembrete", "observacoes"],
	):
		if not h.deal or not h.data_vencimento:
			continue
		if not force_for and (h.ultimo_lembrete == today or not _reminder_due(h.data_vencimento, today, cfg)):
			continue
		try:
			_remind(h, cfg, today)
			sent += 1
		except Exception:
			frappe.log_error("Cobrança: falha ao enviar lembrete", frappe.get_traceback())
	frappe.db.commit()
	return sent


def _remind(h, cfg, today):
	client = _client(h.deal)
	overdue = getdate(h.data_vencimento) < today
	situacao = (
		f"venceu em {_date_br(h.data_vencimento)}"
		if overdue
		else ("vence hoje" if getdate(h.data_vencimento) == today else f"vence em {_date_br(h.data_vencimento)}")
	)
	descricao = h.servico or h.observacoes or "seu serviço"
	values = {"nome": client.nome, "valor": _brl(h.valor), "descricao": descricao, "situacao": situacao,
	          "vencimento": _date_br(h.data_vencimento)}
	message = _fill(cfg.cobranca_mensagem, **values)
	subject = _fill(cfg.cobranca_assunto, **values)
	title = f"Cobrar {client.completo} — {_brl(h.valor)} ({situacao})"
	_notify_client(h.deal, subject, message, title)
	frappe.db.set_value(
		"CRM Honorario",
		h.name,
		{"ultimo_lembrete": today, "lembretes_enviados": cint(frappe.db.get_value("CRM Honorario", h.name, "lembretes_enviados")) + 1},
		update_modified=False,
	)


@frappe.whitelist()
def send_reminder_now(honorario: str):
	"""Botão 'Enviar lembrete agora' no Financeiro."""
	_managers_only()
	if not frappe.db.exists("CRM Honorario", honorario):
		frappe.throw(_("Cobrança não encontrada."))
	send_billing_reminders(force_for=honorario)
	return {"ok": True}


# ------------------------------------------------------------------ 9. pós-venda

def run_posvenda():
	"""Job diário: depois de N dias do fechamento pede avaliação; depois de mais N pede indicação."""
	cfg = get_config()
	if not cint(cfg.posvenda_ativo):
		return
	today = getdate(nowdate())
	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")
	if not won:
		return
	steps = (
		("posvenda_avaliacao_em", cint(cfg.posvenda_avaliacao_dias) or 7, cfg.posvenda_avaliacao_mensagem or DEFAULT_AVALIACAO,
		 "Como foi trabalhar com a gente?", "Pós-venda: pedir avaliação"),
		("posvenda_indicacao_em", cint(cfg.posvenda_indicacao_dias) or 30, cfg.posvenda_indicacao_mensagem or DEFAULT_INDICACAO,
		 "Uma indicação sua vale muito", "Pós-venda: pedir indicação"),
	)
	for field, days, template, subject, title in steps:
		limit = add_days(today, -days)
		for d in frappe.get_all(
			"CRM Deal",
			filters={"status": ["in", won], "closed_date": ["between", [add_days(today, -400), limit]], field: ["is", "not set"]},
			fields=["name"],
			limit_page_length=100,
		):
			try:
				client = _client(d.name)
				message = _fill(template, nome=client.nome, link=cfg.posvenda_avaliacao_link or "")
				_notify_client(d.name, subject, message, f"{title} — {client.completo}")
				frappe.db.set_value("CRM Deal", d.name, field, today, update_modified=False)
			except Exception:
				frappe.log_error("Pós-venda: falha ao enviar", frappe.get_traceback())
	frappe.db.commit()


# ------------------------------------------------------------------ 11. resumo semanal

def _week_bounds(ref=None):
	"""Semana anterior fechada: de segunda a domingo, contando a partir da data de referência."""
	ref = getdate(ref or nowdate())
	this_monday = ref - timedelta(days=ref.weekday())
	return this_monday - timedelta(days=7), this_monday - timedelta(days=1)


def _report_recipients(cfg) -> list[str]:
	listed = [e.strip() for e in (cfg.relatorio_destinatarios or "").replace(",", "\n").split("\n") if "@" in e]
	if listed:
		return listed
	out = []
	for role in ("Sales Manager", "System Manager"):
		for u in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"):
			email = frappe.db.get_value("User", u, ["email", "enabled"], as_dict=True)
			if u != "Administrator" and email and email.enabled and email.email:
				out.append(email.email)
	if not out:
		admin = frappe.db.get_value("User", "Administrator", "email")
		if admin and "@" in admin:
			out.append(admin)
	return list(dict.fromkeys(out))


def _metrics(start, end) -> dict:
	from crm.api import prospeccao

	days = prospeccao._effective_days(str(start), str(end))

	def total(key):
		return sum(cint(d.get(key)) for d in days.values())

	def money(filters):
		return flt(frappe.get_all("CRM Honorario", filters=filters, fields=["sum(valor) as t"])[0].t)

	won = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="name")
	span = ["between", [str(start), str(end)]]
	return {
		"abordados": total("abordados"),
		"agendadas": total("agendadas"),
		"propostas": total("propostas"),
		"fechamentos": total("fechamentos"),
		"leads_novos": frappe.db.count("CRM Lead", {"creation": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]}),
		"ganhos": frappe.db.count("CRM Deal", {"status": ["in", won], "closed_date": span}) if won else 0,
		"recebido": money({"status": "Pago", "data_pagamento": span}),
	}


def build_weekly_report(start=None, end=None) -> dict:
	if not start:
		start, end = _week_bounds()
	today = getdate(nowdate())
	previous = _metrics(start - timedelta(days=7), end - timedelta(days=7))
	report = _metrics(start, end)
	report["anterior"] = previous
	report["periodo"] = f"{_date_br(start)} a {_date_br(end)}"

	def money(filters):
		return flt(frappe.get_all("CRM Honorario", filters=filters, fields=["sum(valor) as t"])[0].t)

	report.update(
		{
			"a_receber": money({"status": "Pendente", "data_vencimento": ["between", [today, today + timedelta(days=7)]]}),
			"atrasado": money({"status": "Atrasado"}),
			"followups": frappe.db.count(
				"CRM Task", {"reference_doctype": "CRM Lead", "title": ["like", "Follow-up:%"], "status": OPEN_TASK}
			),
			"reunioes": frappe.db.count(
				"CRM Reuniao", {"status": "Agendada", "inicio": ["between", [str(today), str(today + timedelta(days=7))]]}
			),
			"tarefas_atrasadas": frappe.db.count(
				"CRM Task", {"status": ["in", ["Backlog", "Todo", "In Progress"]], "due_date": ["<", f"{today} 00:00:00"]}
			),
		}
	)
	return report


def _delta(now, before, money=False) -> str:
	if not before:
		return ""
	pct = round((flt(now) - flt(before)) / flt(before) * 100)
	if pct == 0:
		return "<span style='color:#888;font-size:12px'> igual à semana anterior</span>"
	color = "#1a7f4b" if pct > 0 else "#c0392b"
	arrow = "▲" if pct > 0 else "▼"
	return f"<span style='color:{color};font-size:12px'> {arrow} {abs(pct)}% vs. semana anterior</span>"


def _report_html(r: dict) -> str:
	prev = r.get("anterior") or {}

	def row(label, value, delta=""):
		return (
			f"<tr><td style='padding:8px 12px;color:#555;border-bottom:1px solid #eef1f3'>{label}</td>"
			f"<td style='padding:8px 12px;text-align:right;border-bottom:1px solid #eef1f3'>"
			f"<b style='color:#042d3c'>{value}</b>{delta}</td></tr>"
		)

	def block(title, rows):
		return (
			f"<h3 style='margin:24px 0 8px;color:#042d3c;font-size:15px'>{title}</h3>"
			f"<table style='width:100%;border-collapse:collapse;border:1px solid #e4e7ea'>{''.join(rows)}</table>"
		)

	return (
		"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body style='margin:0'>"
		"<div style='font-family:Arial,sans-serif;max-width:640px;margin:auto;padding:8px'>"
		"<div style='background:#042d3c;color:#fff;padding:18px 20px;border-radius:8px'>"
		f"<div style='font-size:20px;font-weight:bold'>Resumo da semana</div>"
		f"<div style='opacity:.8;font-size:13px;margin-top:2px'>{_brand()} · {r['periodo']}</div></div>"
		+ block("Prospecção e vendas", [
			row("Abordagens", r["abordados"], _delta(r["abordados"], prev.get("abordados"))),
			row("Leads novos", r["leads_novos"], _delta(r["leads_novos"], prev.get("leads_novos"))),
			row("Reuniões agendadas", r["agendadas"], _delta(r["agendadas"], prev.get("agendadas"))),
			row("Propostas enviadas", r["propostas"], _delta(r["propostas"], prev.get("propostas"))),
			row("Negócios ganhos", r["ganhos"], _delta(r["ganhos"], prev.get("ganhos"))),
		])
		+ block("Financeiro", [
			row("Recebido na semana", _brl(r["recebido"]), _delta(r["recebido"], prev.get("recebido"))),
			row("A receber nos próximos 7 dias", _brl(r["a_receber"])),
			row("Em atraso", _brl(r["atrasado"])),
		])
		+ block("Precisa de atenção", [
			row("Follow-ups para enviar", r["followups"]), row("Tarefas atrasadas", r["tarefas_atrasadas"]),
			row("Reuniões nos próximos 7 dias", r["reunioes"]),
		])
		+ "<p style='color:#999;font-size:12px;margin-top:22px'>Gerado automaticamente pelo CRM toda segunda-feira, às 8h.</p>"
		"</div></body></html>"
	)


def _render_report_pdf(html: str) -> bytes:
	import subprocess

	cmd = ["wkhtmltopdf", "-q", "--page-size", "A4", "-T", "12", "-B", "12", "-L", "12", "-R", "12",
	       "--print-media-type", "--background", "--encoding", "UTF-8", "--disable-javascript", "-", "-"]
	proc = subprocess.run(cmd, input=html.encode("utf-8"), capture_output=True, timeout=120)
	if not proc.stdout.startswith(b"%PDF"):
		frappe.log_error("Resumo semanal: falha ao gerar o PDF", proc.stderr.decode("utf-8", "ignore")[-1500:])
		frappe.throw(_("Não foi possível gerar o PDF do resumo."))
	return proc.stdout


def generate_weekly_report(force: bool = False, send_email: bool | None = None) -> str | None:
	"""Gera o PDF da semana anterior, guarda no CRM (para baixar) e, se ligado, manda por e-mail."""
	cfg = get_config()
	start, end = _week_bounds()
	name = frappe.db.get_value("CRM Relatorio Semanal", {"inicio": start})
	if name and not force:
		return name
	report = build_weekly_report(start, end)
	pdf = _render_report_pdf(_report_html(report))
	filename = f"Resumo da semana {start.strftime('%d-%m')} a {end.strftime('%d-%m-%Y')}.pdf"
	if name:
		doc = frappe.get_doc("CRM Relatorio Semanal", name)
		for f in frappe.get_all("File", filters={"attached_to_doctype": "CRM Relatorio Semanal", "attached_to_name": name}, pluck="name"):
			frappe.delete_doc("File", f, ignore_permissions=True, force=True)
	else:
		doc = frappe.get_doc({"doctype": "CRM Relatorio Semanal", "inicio": start, "fim": end}).insert(ignore_permissions=True)
	file = frappe.get_doc(
		{"doctype": "File", "file_name": filename, "attached_to_doctype": "CRM Relatorio Semanal",
		 "attached_to_name": doc.name, "attached_to_field": "arquivo", "is_private": 1, "content": pdf}
	).insert(ignore_permissions=True)
	doc.db_set("arquivo", file.file_url)
	want_email = cint(cfg.relatorio_email) if send_email is None else send_email
	if want_email and frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		recipients = _report_recipients(cfg)
		if recipients:
			frappe.sendmail(
				recipients=recipients,
				subject=f"Resumo da semana — {_brand() or 'CRM'} ({report['periodo']})",
				message=_report_html(report),
				attachments=[{"fname": filename, "fcontent": pdf}],
				delayed=False,
			)
			doc.db_set("enviado_por_email", 1)
	frappe.db.commit()
	return doc.name


def weekly_job():
	"""Toda segunda-feira às 8h (horário do site)."""
	if cint(get_config().relatorio_ativo):
		generate_weekly_report()


@frappe.whitelist()
def list_weekly_reports(limit: int = 8) -> list:
	_managers_only()
	return frappe.get_all(
		"CRM Relatorio Semanal",
		fields=["name", "inicio", "fim", "arquivo", "enviado_por_email", "creation"],
		order_by="inicio desc",
		limit=cint(limit) or 8,
	)


@frappe.whitelist()
def generate_weekly_report_now():
	"""Botão 'Gerar o resumo da última semana agora' (refaz o da semana anterior)."""
	_managers_only()
	name = generate_weekly_report(force=True, send_email=False)
	return {"name": name, "arquivo": frappe.db.get_value("CRM Relatorio Semanal", name, "arquivo")}