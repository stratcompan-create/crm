"""Teste de fumaça: Gerador de conteúdo do Instagram (chat com o Claude).
A chamada real à API do Claude é substituída por um stub — não gasta tokens
nem depende de rede. Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json
from unittest import mock

import frappe

from crm.api import conteudo as gc


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	# _parse_resposta: com e sem cerca de código
	limpo = gc._parse_resposta('{"resposta": "pronto", "slides": [{"titulo": "A", "corpo": "B"}]}')
	ck("parse de JSON simples", limpo["slides"][0]["titulo"] == "A")

	cercado = gc._parse_resposta('```json\n{"resposta": "ok", "slides": []}\n```')
	ck("parse de JSON com cerca de código", cercado["resposta"] == "ok")

	texto_livre = gc._parse_resposta("não isso não é json")
	ck("texto que não é JSON vira resposta sem quebrar", texto_livre["slides"] == [] and texto_livre["resposta"])

	# sem chave configurada: deve recusar com mensagem clara, não com erro cru
	settings = frappe.get_single("FCRM Settings")
	chave_original = settings.get_password("claude_api_key", raise_exception=False)
	try:
		settings.claude_api_key = ""
		settings.save()
		erro_sem_chave = None
		try:
			gc.enviar_mensagem(mensagem="cria um post", tipo="Post")
		except frappe.ValidationError as e:
			erro_sem_chave = str(e)
		ck("sem chave configurada, recusa com mensagem clara", erro_sem_chave and "chave" in erro_sem_chave.lower())

		# com chave (fake) e o _call_claude substituído: fluxo completo, incluindo 2º turno
		settings.claude_api_key = "sk-ant-teste-fake"
		settings.save()

		resposta_1 = json.dumps({
			"resposta": "Criei o post sobre o lançamento.",
			"slides": [{"titulo": "Chegou o CRM Jurídico", "corpo": "Feito pra advogado."}],
		})
		resposta_2 = json.dumps({
			"resposta": "Deixei mais curto.",
			"slides": [{"titulo": "CRM Jurídico", "corpo": "Pra advogado."}],
		})

		conversa_criada = None
		with mock.patch.object(gc, "_call_claude", side_effect=[resposta_1, resposta_2]):
			r1 = gc.enviar_mensagem(mensagem="cria um post sobre o lançamento do CRM", tipo="Post")
			conversa_criada = r1["conversa"]
			ck("1ª mensagem cria a conversa", bool(conversa_criada))
			ck("1ª mensagem devolve o texto do chat", r1["resposta"] == "Criei o post sobre o lançamento.")
			ck("1ª mensagem devolve 1 slide (tipo Post)", len(r1["slides"]) == 1)

			r2 = gc.enviar_mensagem(mensagem="deixa mais curto", conversa=conversa_criada)
			ck("2ª mensagem reaproveita a mesma conversa", r2["conversa"] == conversa_criada)
			ck("2ª mensagem atualiza os slides", r2["slides"][0]["titulo"] == "CRM Jurídico")

		if conversa_criada:
			obtida = gc.obter_conversa(conversa_criada)
			ck("obter_conversa traz as 4 mensagens do histórico (2 turnos)", len(obtida["mensagens"]) == 4)

			listadas = gc.listar_conversas(tipo="Post")
			ck("listar_conversas encontra a conversa criada", any(c["name"] == conversa_criada for c in listadas))

			gc.marcar_agendado(conversa_criada, frappe.utils.add_days(frappe.utils.nowdate(), 3))
			status_depois = frappe.db.get_value("CRM Conteudo Conversa", conversa_criada, "status")
			ck("marcar_agendado muda o status para Agendado", status_depois == "Agendado")

			frappe.delete_doc("CRM Conteudo Conversa", conversa_criada, force=True, ignore_permissions=True)
	finally:
		settings.claude_api_key = chave_original or ""
		settings.save()
		frappe.db.commit()

	return res
