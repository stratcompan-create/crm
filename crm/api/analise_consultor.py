# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Análise de consultor para os relatórios do CRM (resumo semanal, métricas do
# Instagram): lê os números do relatório e escreve, em texto corrido, o que
# está bom, o que precisa de atenção e o que fazer a respeito - em vez de só
# mostrar número solto. Usa a mesma chamada central do Claude que o resto do
# sistema (gerador de conteúdo, assistente), então já entra no desconto do
# saldo de IA quando esse controle está ligado pro site.

import frappe

SISTEMA_BASE = """Você é um consultor de negócios analisando um relatório do CRM de {nome}.
Leia os dados abaixo (formato chave: valor) e escreva uma análise curta, em
português, em texto corrido (sem markdown, sem JSON, sem títulos), com no
máximo 4 frases: o que está indo bem, o que precisa de atenção, e uma
sugestão prática e específica do que fazer essa semana. Cite números reais
do relatório pra sustentar o que disser. Não invente dado que não esteja
ali. Se os números forem poucos ou neutros, diga isso com honestidade em
vez de forçar uma conclusão."""


SALDO_INSUFICIENTE = "__saldo_insuficiente__"


def gerar(dados: dict) -> str:
	"""Devolve a análise em texto corrido, "" se a IA não estiver configurada
	ou a chamada falhar por qualquer motivo, ou SALDO_INSUFICIENTE se o saldo
	de IA acabou - nunca derruba a geração do relatório por causa disso."""
	try:
		from crm.api.ficha import _api_key

		api_key = _api_key()
		if not api_key:
			return ""

		from crm.api import credito_ia

		if not credito_ia.saldo_suficiente():
			return SALDO_INSUFICIENTE

		from crm.api.conteudo import _call_claude

		nome = frappe.get_single("FCRM Settings").get("brand_name") or "sua empresa"
		system = SISTEMA_BASE.format(nome=nome)
		linhas = "\n".join(f"{k}: {v}" for k, v in dados.items() if v not in (None, ""))
		return _call_claude(api_key, system, [{"role": "user", "content": linhas}]).strip()
	except Exception:
		frappe.log_error("Análise de consultor: falha ao gerar", frappe.get_traceback())
		return ""
