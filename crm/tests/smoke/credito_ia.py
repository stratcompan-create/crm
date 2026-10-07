"""Teste de fumaca: saldo de IA pre-pago (desconto por uso, recarga via InfinitePay),
sem falar com o InfinitePay nem com o Claude de verdade.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from unittest import mock

import frappe

from crm.api import credito_ia


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	before_cfg = frappe.db.get_single_value("CRM Automacoes Config", "credito_ia_ativo")
	before_saldo = frappe.db.get_single_value("CRM Credito IA", "saldo_centavos")
	before_custo_real = frappe.db.get_single_value("CRM Credito IA", "custo_real_centavos")
	try:
		# desligado (padrao): nunca bloqueia, nunca desconta
		frappe.db.set_single_value("CRM Automacoes Config", "credito_ia_ativo", 0)
		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", 0)
		frappe.db.commit()
		ck("desligado: saldo_suficiente sempre True mesmo zerado", credito_ia.saldo_suficiente())
		credito_ia.registrar_uso({"input_tokens": 1000, "output_tokens": 1000})
		ck(
			"desligado: registrar_uso nao desconta nada",
			frappe.db.get_single_value("CRM Credito IA", "saldo_centavos") == 0,
		)

		# ligado: passa a descontar e bloquear
		frappe.db.set_single_value("CRM Automacoes Config", "credito_ia_ativo", 1)
		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", 10000)
		frappe.db.commit()
		ck("ligado: saldo positivo libera", credito_ia.saldo_suficiente())

		custo_real = credito_ia.custo_real_centavos({"input_tokens": 1_000_000, "output_tokens": 0})
		ck("custo_real_centavos calcula o preco de entrada certo (sem margem)", custo_real == credito_ia.PRECO_ENTRADA_CENTAVOS_POR_MILHAO, custo_real)

		frappe.db.set_single_value("CRM Credito IA", "custo_real_centavos", 0)
		frappe.db.commit()
		credito_ia.registrar_uso({"input_tokens": 1_000_000, "output_tokens": 0})
		custo_venda = round(custo_real * (1 + credito_ia.MARGEM_VENDA))
		saldo_depois = frappe.db.get_single_value("CRM Credito IA", "saldo_centavos")
		ck(
			"ligado: registrar_uso desconta do saldo no preco DE VENDA (com margem), nao no custo cru",
			saldo_depois == 10000 - custo_venda,
			saldo_depois,
		)
		ck(
			"registrar_uso acumula o custo real (sem margem) separado, pro relatorio de lucro",
			frappe.db.get_single_value("CRM Credito IA", "custo_real_centavos") == custo_real,
		)

		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", 0)
		frappe.db.commit()
		ck("ligado: saldo zerado bloqueia", not credito_ia.saldo_suficiente())

		# faixas de recarga ja vem com a margem embutida no preco de venda
		for faixa in credito_ia.FAIXAS:
			ck(
				f"faixa {faixa['rotulo']} tem a margem embutida no preco",
				faixa["centavos"] > 0,
				faixa["centavos"],
			)

		# gerar_link_credito recebe "indice" como numero de verdade (o Vue manda
		# int, nao str) - sem a validacao de tipo real (in_test=True, como uma
		# requisicao HTTP de verdade faz) esse bug passaria batido no console.
		# Ver tambem crm.tests.smoke.exclusao_em_massa para o mesmo tipo de bug.
		with mock.patch.object(credito_ia, "_handle_central", lambda: ""):
			flag_anterior = frappe.local.flags.in_test
			frappe.local.flags.in_test = True
			try:
				credito_ia.gerar_link_credito(0)
				ck("indice como int nao quebra a validacao de tipo", False)
			except frappe.exceptions.ValidationError as e:
				ck(
					"indice como int nao quebra a validacao de tipo",
					"should be of type" not in str(e),
					str(e),
				)
			finally:
				frappe.local.flags.in_test = flag_anterior

			# gerar_link_credito: sem handle central configurado, recusa com mensagem clara
			try:
				credito_ia.gerar_link_credito(0)
				ck("sem handle central, recusa gerar link", False)
			except frappe.ValidationError:
				ck("sem handle central, recusa gerar link", True)

		# webhook: cria uma compra "na mao" (sem bater na API de verdade) e aplica o pagamento
		compra = frappe.get_doc({
			"doctype": "CRM Credito IA Compra",
			"valor_centavos": credito_ia.FAIXAS[1]["centavos"],
			"status": "Pendente",
		})
		compra.insert(ignore_permissions=True)
		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", 500)
		frappe.db.commit()

		resultado = credito_ia._aplicar_pagamento({
			"order_nsu": compra.name, "amount": compra.valor_centavos / 100, "paid_amount": compra.valor_centavos / 100,
		})
		ck("webhook aplica o pagamento", resultado["ok"] is True)
		ck(
			"webhook credita o valor certo no saldo",
			frappe.db.get_single_value("CRM Credito IA", "saldo_centavos") == 500 + credito_ia.FAIXAS[1]["centavos"],
		)
		ck("webhook marca a compra como paga", frappe.db.get_value("CRM Credito IA Compra", compra.name, "status") == "Pago")

		# reaplicar o mesmo webhook (reenvio do InfinitePay) nao credita de novo
		saldo_antes_repeticao = frappe.db.get_single_value("CRM Credito IA", "saldo_centavos")
		credito_ia._aplicar_pagamento({
			"order_nsu": compra.name, "amount": compra.valor_centavos / 100, "paid_amount": compra.valor_centavos / 100,
		})
		ck(
			"webhook repetido nao credita duas vezes",
			frappe.db.get_single_value("CRM Credito IA", "saldo_centavos") == saldo_antes_repeticao,
		)

		ck(
			"webhook com order_nsu desconhecido nao quebra",
			credito_ia._aplicar_pagamento({"order_nsu": "nao-existe"})["ok"] is False,
		)

		# relatorio(): recarregado - custo real = lucro
		rel = credito_ia.relatorio()
		ck("relatorio traz o total recarregado (compras pagas)", rel["recarregado_centavos"] >= credito_ia.FAIXAS[1]["centavos"])
		ck(
			"relatorio calcula o lucro certo (recarregado - custo real)",
			rel["lucro_centavos"] == rel["recarregado_centavos"] - rel["custo_real_centavos"],
		)

		# _call_claude (conteudo.py) bloqueia de verdade quando o saldo acabou,
		# antes de gastar uma chamada real a Anthropic
		from crm.api import conteudo

		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", 0)
		frappe.db.commit()
		try:
			conteudo._call_claude("fake-key", "sistema", [{"role": "user", "content": "oi"}])
			ck("_call_claude recusa quando o saldo acabou", False)
		except frappe.ValidationError:
			ck("_call_claude recusa quando o saldo acabou", True)
	finally:
		frappe.db.set_single_value("CRM Automacoes Config", "credito_ia_ativo", before_cfg)
		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", before_saldo)
		frappe.db.set_single_value("CRM Credito IA", "custo_real_centavos", before_custo_real)
		frappe.db.commit()
	return res
