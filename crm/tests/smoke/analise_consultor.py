"""Teste de fumaca: analise de consultor dos relatorios (resumo semanal,
metricas do Instagram) - a chamada real ao Claude e substituida por um stub.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from unittest import mock

import frappe

from crm.api import analise_consultor
from crm.api import conteudo as gc
from crm.api import ficha


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	chave_original = ficha._api_key()
	try:
		# sem chave configurada: devolve vazio, nao quebra, nao loga erro de verdade
		ficha.save_ai_key("")
		ck("sem chave configurada, devolve vazio", analise_consultor.gerar({"Leads": 5}) == "")

		# com chave: chama o _call_claude central e devolve o texto dele
		ficha.save_ai_key("sk-ant-teste-fake")
		texto_esperado = "Foram 5 leads na semana, um bom numero. Vale focar em fechar os negocios em aberto."
		with mock.patch.object(gc, "_call_claude", return_value=texto_esperado) as mocked:
			resultado = analise_consultor.gerar({"Leads novos": 5, "Negocios ganhos": 2})
		ck("com chave, devolve o texto da IA", resultado == texto_esperado)
		ck("manda os dados do relatorio pro Claude", "Leads novos: 5" in str(mocked.call_args))

		# dado vazio/None nao aparece na mensagem mandada pro Claude
		with mock.patch.object(gc, "_call_claude", return_value="ok") as mocked2:
			analise_consultor.gerar({"Campo vazio": None, "Campo com valor": 10})
		ck("ignora campos vazios/None na mensagem", "Campo vazio" not in str(mocked2.call_args) and "Campo com valor: 10" in str(mocked2.call_args))

		# se o Claude falhar, devolve vazio em vez de quebrar o relatorio
		with mock.patch.object(gc, "_call_claude", side_effect=Exception("rede fora")):
			ck("se o Claude falhar, devolve vazio em vez de quebrar", analise_consultor.gerar({"x": 1}) == "")
	finally:
		ficha.save_ai_key(chave_original or "")
	return res
