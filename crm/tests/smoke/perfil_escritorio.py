"""Teste de fumaça: o perfil escritório fala a língua do advogado.

Vocabulário (Negócio -> Caso, Lead -> Atendimento, reunião -> consulta), ficha da consulta jurídica,
tarefas de início do caso e listas de horas/despesas por perfil. Devolve o perfil original no fim.
"""

import frappe

from crm import provision
from crm.api import automacoes, ficha, opcoes


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	base = {"Deals": "Negócios", "Create Deal": "Criar Negócio", "Leads": "Leads", "Deal Owner": "Responsável pelo Negócio",
			"lead_name": "lead_name", "New Deal": "Novo negócio"}
	m = provision.profile_messages("escritorio", base=base)
	ck("Negócios vira Casos", m.get("Deals") == "Casos", str(m.get("Deals")))
	ck("Criar Negócio vira Criar Caso", m.get("Create Deal") == "Criar Caso")
	ck("Leads vira Atendimentos", m.get("Leads") == "Atendimentos")
	ck("concordância: 'pelo Negócio' vira 'pelo Caso'", m.get("Deal Owner") == "Responsável pelo Caso")
	ck("não mexe em nome técnico (lead_name)", "lead_name" not in m)
	ck("minúscula também: 'novo negócio' vira 'novo caso'", m.get("New Deal") == "Novo caso")
	ag = provision.profile_messages("agencia", base=base)
	ck("agência continua com o vocabulário dela", "Deals" not in ag and ag.get("Honorários") == "Receitas")
	tela = provision._textos_da_tela()
	ck("acha os textos das telas que citam negócio/lead/reunião", len(tela) > 20, str(len(tela)))
	ck("'Ficha da reunião' vira 'Ficha da consulta'", m.get("Ficha da reunião") == "Ficha da consulta" or
	   provision.profile_messages("escritorio", base={}).get("Ficha da reunião") == "Ficha da consulta")

	perfil_antes = frappe.db.get_default("crm_profile")
	try:
		frappe.db.set_default("crm_profile", "escritorio")
		chaves = ficha._keys()
		ck("ficha do escritório tem urgência e partes", "urgencia" in chaves and "partes" in chaves, str(chaves))
		ck("ficha do escritório mantém as chaves da proposta", all(k in chaves for k in ("dor_objetivo", "escopo", "valor", "prazo")))
		ck("IA da ficha recebe instrução de consulta jurídica sem opinar",
		   "CONSULTA JURÍDICA" in ficha._system_prompt() and "NÃO dá opinião jurídica" in ficha._system_prompt())
		tarefas = " | ".join(t for t, _d in automacoes._onboarding_tasks())
		ck("tarefas de início falam de procuração e documentos", "procuração" in tarefas and "documentos" in tarefas, tarefas)
		ck("tarefas de início não falam de kickoff", "kickoff" not in tarefas)

		frappe.db.set_default("crm_profile", "agencia")
		ck("agência mantém a ficha comercial (7 campos)", len(ficha._keys()) == 7)
		ck("agência mantém as tarefas de início dela", "kickoff" in " ".join(t for t, _d in automacoes._onboarding_tasks()))
	finally:
		frappe.db.set_default("crm_profile", perfil_antes or "agencia")
		frappe.db.commit()

	ck("lista de horas vem do site", len(opcoes.opcoes("CRM Horas", "frente")) > 2)
	ck("lista de despesas vem do site", "Outros" in opcoes.opcoes("CRM Despesa", "categoria"))
	erro = None
	try:
		opcoes.opcoes("User", "role_profile_name")
	except frappe.ValidationError as e:
		erro = str(e)
	ck("recusa listas fora das liberadas", bool(erro))
	ck("frentes do escritório incluem 'Outro' (padrão do lançamento de horas)", "Outro" in provision.HORAS_JURIDICO)
	ck("categorias do escritório incluem as usadas pelas automações",
	   all(c in provision.DESPESAS_JURIDICO for c in ("Custas e Taxas", "Contas Fixas", "Ferramentas e Software", "Outros")))
	return res
