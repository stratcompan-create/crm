# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Assistente do Claude fixo no CRM (painel à direita, em toda tela). Sabe em que
# tela/registro a pessoa está porque o frontend manda isso junto com cada
# mensagem — não precisa instrumentar cada página uma por uma. Reaproveita a
# mesma chamada à API do Claude do Gerador de conteúdo (crm.api.conteudo).

import json

import frappe

from crm.api.conteudo import _call_claude

MANAGER_ROLES = ("System Manager", "Sales Manager")

SISTEMA_BASE = """Você é o assistente do CRM da {nome}, integrado direto no sistema (aparece
fixo do lado direito da tela). Ajuda quem está usando o CRM: tira dúvida de como usar o
sistema, explica os dados que aparecem na tela atual, ajuda a interpretar leads, negócios
e informações financeiras.

Tela atual: {tela}
{registro_bloco}

Responda em português, direto, em texto simples (sem JSON, sem markdown pesado). Se não
souber algo porque não foi te enviado, diga isso em vez de inventar. Se a dúvida for algo
que você não consegue resolver sozinho, sugira usar o botão "Falar com atendente"."""

CAMPOS_IGNORADOS = {
	"Table", "Table MultiSelect", "Attach", "Attach Image", "Password",
	"HTML", "Section Break", "Column Break", "Tab Break", "Button",
}


def _resumo_registro(doctype: str, name: str) -> str:
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return ""
	try:
		doc = frappe.get_doc(doctype, name)
		if not doc.has_permission("read"):
			return ""
	except Exception:
		return ""

	linhas = []
	for df in doc.meta.fields:
		if df.fieldtype in CAMPOS_IGNORADOS:
			continue
		valor = doc.get(df.fieldname)
		if not valor:
			continue
		linhas.append(f"{df.label or df.fieldname}: {str(valor)[:200]}")
		if len(linhas) >= 25:
			break

	if not linhas:
		return ""
	return f"Registro aberto agora ({doctype} {name}):\n" + "\n".join(linhas)


def _get_or_create_conversa():
	user = frappe.session.user
	if frappe.db.exists("CRM Assistente Conversa", user):
		return frappe.get_doc("CRM Assistente Conversa", user)
	doc = frappe.new_doc("CRM Assistente Conversa")
	doc.usuario = user
	doc.mensagens = "[]"
	doc.insert(ignore_permissions=True)
	return doc


@frappe.whitelist()
def enviar_mensagem(mensagem: str, tela: str = "", doctype: str = "", registro: str = "") -> dict:
	mensagem = (mensagem or "").strip()
	if not mensagem:
		frappe.throw("Escreva sua pergunta.")

	api_key = frappe.get_single("FCRM Settings").get_password("claude_api_key", raise_exception=False)
	if not api_key:
		frappe.throw("Configure a chave da API do Claude em Configurações → Integrações → IA & Pagamentos antes de usar o assistente.")

	doc = _get_or_create_conversa()
	historico = json.loads(doc.mensagens or "[]")
	historico.append({"role": "user", "content": mensagem})

	system = SISTEMA_BASE.format(
		nome=frappe.get_single("FCRM Settings").get("brand_name") or "sua empresa",
		tela=tela or "não informado",
		registro_bloco=_resumo_registro(doctype, registro),
	)
	try:
		texto = _call_claude(api_key, system, historico[-20:])
	except Exception:
		frappe.log_error("Assistente do CRM: falha ao chamar a API do Claude", frappe.get_traceback())
		frappe.throw("Não consegui responder agora. Tente de novo em instantes.")

	historico.append({"role": "assistant", "content": texto})
	doc.mensagens = json.dumps(historico[-40:])
	doc.save()
	return {"resposta": texto}


@frappe.whitelist()
def obter_historico() -> dict:
	doc = _get_or_create_conversa()
	return {"mensagens": json.loads(doc.mensagens or "[]")}


@frappe.whitelist()
def nova_conversa() -> dict:
	doc = _get_or_create_conversa()
	doc.mensagens = "[]"
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def solicitar_atendimento(mensagem: str = "") -> dict:
	doc = _get_or_create_conversa()
	historico = json.loads(doc.mensagens or "[]")
	ultimas = historico[-6:]
	resumo = "\n".join(
		f"{'Pessoa' if m['role'] == 'user' else 'Assistente'}: {m['content']}" for m in ultimas
	)

	gerentes = frappe.get_all(
		"Has Role", filters={"role": ["in", MANAGER_ROLES], "parenttype": "User"}, pluck="parent"
	)
	gerentes = list({g for g in gerentes if g not in ("Administrator", "Guest")})
	if not gerentes:
		frappe.throw("Nenhum responsável configurado pra receber o pedido de atendimento.")

	from frappe.desk.form.assign_to import add as assign_to_add

	descricao = f"{frappe.session.user} pediu atendimento humano no chat do CRM"
	if mensagem:
		descricao += f": {mensagem}"
	if resumo:
		descricao += f"\n\nÚltimas mensagens:\n{resumo}"

	assign_to_add({
		"assign_to": gerentes,
		"doctype": "CRM Assistente Conversa",
		"name": doc.name,
		"description": descricao,
	})
	return {"ok": True}
