"""Teste de fumaça: Gerador de conteúdo do Instagram (chat com o Claude).
A chamada real à API do Claude é substituída por um stub — não gasta tokens
nem depende de rede. Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json
from unittest import mock

import frappe

from crm.api import conteudo as gc
from crm.api import ficha


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
	chave_original = ficha._api_key()
	try:
		ficha.save_ai_key("")
		erro_sem_chave = None
		try:
			gc.enviar_mensagem(mensagem="cria um post", tipo="Post")
		except frappe.ValidationError as e:
			erro_sem_chave = str(e)
		ck("sem chave configurada, recusa com mensagem clara", erro_sem_chave and "chave" in erro_sem_chave.lower())

		# com chave (fake) e o _call_claude substituído: fluxo completo, incluindo 2º turno
		ficha.save_ai_key("sk-ant-teste-fake")

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

			# salvar_slide agora tambem grava titulo/corpo/layout, alem do canvas
			gc.salvar_slide(
				conversa_criada, 0,
				canvas=json.dumps({"objects": [], "background": "#000"}),
				titulo="Titulo editado a mao",
				corpo="Corpo editado a mao",
				layout=json.dumps({"posicao": "meio-cen", "margemH": 10}),
			)
			slide_0 = json.loads(frappe.db.get_value("CRM Conteudo Conversa", conversa_criada, "slides"))[0]
			ck(
				"salvar_slide grava titulo/corpo/layout junto com o canvas",
				slide_0["titulo"] == "Titulo editado a mao" and slide_0["corpo"] == "Corpo editado a mao"
				and slide_0["layout"]["posicao"] == "meio-cen" and slide_0.get("canvas", {}).get("background") == "#000",
			)

			# _parse_slide_unico: com e sem cerca de codigo
			ck("_parse_slide_unico entende JSON simples", gc._parse_slide_unico('{"titulo": "T", "corpo": "C"}') == {"titulo": "T", "corpo": "C"})
			ck("_parse_slide_unico entende JSON com cerca", gc._parse_slide_unico('```json\n{"titulo": "T2", "corpo": "C2"}\n```')["titulo"] == "T2")
			ck("_parse_slide_unico devolve vazio se nao for JSON valido", gc._parse_slide_unico("bagunca") == {})

			# gerar_texto_slide: gera do zero (sem instrucao) e refina (com instrucao)
			with mock.patch.object(gc, "_call_claude", return_value='{"titulo": "Gerado pela IA", "corpo": "Corpo novo"}'):
				r_gerar = gc.gerar_texto_slide(conversa_criada, 0)
				ck("gerar_texto_slide sem instrucao gera conteudo novo", r_gerar["titulo"] == "Gerado pela IA")

			slide_0_depois = json.loads(frappe.db.get_value("CRM Conteudo Conversa", conversa_criada, "slides"))[0]
			ck("gerar_texto_slide apaga o canvas salvo (texto mudou, remonta do zero)", "canvas" not in slide_0_depois)

			with mock.patch.object(gc, "_call_claude", return_value='{"titulo": "Refinado", "corpo": "Mais curto"}') as mocked:
				r_refinar = gc.gerar_texto_slide(conversa_criada, 0, instrucao="deixa mais curto")
				ck("gerar_texto_slide com instrucao refina o slide", r_refinar["corpo"] == "Mais curto")
				pedido_mandado = mocked.call_args[0][2][0]["content"]
				ck("instrucao de refino vai no pedido pra IA", "deixa mais curto" in pedido_mandado)

			erro_indice = None
			try:
				gc.gerar_texto_slide(conversa_criada, 99)
			except frappe.ValidationError as e:
				erro_indice = str(e)
			ck("gerar_texto_slide recusa indice que nao existe", bool(erro_indice))

			# gerar_legenda e salvar_legenda
			with mock.patch.object(gc, "_call_claude", return_value="Legenda gerada pela IA. Comenta aí embaixo!"):
				r_legenda = gc.gerar_legenda(conversa_criada)
				ck("gerar_legenda devolve e salva a legenda", r_legenda["legenda"].startswith("Legenda gerada"))
			legenda_no_banco = frappe.db.get_value("CRM Conteudo Conversa", conversa_criada, "legenda")
			ck("gerar_legenda persiste no banco", legenda_no_banco == r_legenda["legenda"])

			gc.salvar_legenda(conversa_criada, "Legenda escrita na mão")
			ck(
				"salvar_legenda grava sem chamar IA",
				frappe.db.get_value("CRM Conteudo Conversa", conversa_criada, "legenda") == "Legenda escrita na mão",
			)

			trazida = gc.obter_conversa(conversa_criada)
			ck("obter_conversa devolve a legenda", trazida["legenda"] == "Legenda escrita na mão")

			frappe.delete_doc("CRM Conteudo Conversa", conversa_criada, force=True, ignore_permissions=True)
	finally:
		ficha.save_ai_key(chave_original or "")
		frappe.db.commit()

	return res
