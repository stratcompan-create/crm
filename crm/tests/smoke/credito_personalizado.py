"""Teste de fumaça: recarga de crédito de IA com valor personalizado (mínimo R$ 20, sem teto, ligada por site)."""

import io
import json
from unittest.mock import patch

import frappe

from crm.api import automacoes as au
from crm.api import credito_ia as ci


class _Resp(io.BytesIO):
	def __enter__(self):
		return self

	def __exit__(self, *a):
		return False


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	antes = frappe.db.get_single_value("CRM Credito IA", "saldo_centavos") or 0
	compras = []
	resposta = lambda *a, **k: _Resp(json.dumps({"url": "https://pagar.exemplo/credito"}).encode())
	try:
		with patch("crm.api.credito_ia._handle_central", return_value="stratcompany"), patch("urllib.request.urlopen", side_effect=resposta):
			au.save_settings(json.dumps({"credito_personalizado_ativo": 0}))
			ck("desligado: a tela não mostra o valor livre", not ci.obter_saldo()["personalizado"])
			try:
				ci.gerar_link_credito(valor_centavos=5000)
				ck("desligado: valor livre é recusado", False)
			except frappe.ValidationError:
				ck("desligado: valor livre é recusado", True)

			au.save_settings(json.dumps({"credito_personalizado_ativo": 1}))
			s = ci.obter_saldo()
			ck("ligado: tela recebe o mínimo e a estimativa de uso", s["personalizado"] and s["minimo_centavos"] == 2000 and len(s["uso_referencia"]) == 3)
			try:
				ci.gerar_link_credito(valor_centavos=1999)
				ck("abaixo de R$ 20 é recusado", False)
			except frappe.ValidationError:
				ck("abaixo de R$ 20 é recusado", True)

			r = ci.gerar_link_credito(valor_centavos=7550)
			c = frappe.get_last_doc(ci.DOCTYPE_COMPRA)
			compras.append(c.name)
			ck("R$ 75,50 gera o link com o valor exato", r["link"] == "https://pagar.exemplo/credito" and c.valor_centavos == 7550)

			r2 = ci.gerar_link_credito(valor_centavos=5_000_000)
			c2 = frappe.get_last_doc(ci.DOCTYPE_COMPRA)
			compras.append(c2.name)
			ck("sem teto: R$ 50.000 também gera link", c2.valor_centavos == 5_000_000)

			ci._aplicar_pagamento({"order_nsu": c.name, "amount": 7550, "paid_amount": 7550})
			ck("pagamento confirmado credita exatamente o valor", frappe.db.get_single_value("CRM Credito IA", "saldo_centavos") == antes + 7550)

			r3 = ci.gerar_link_credito(indice=0)
			c3 = frappe.get_last_doc(ci.DOCTYPE_COMPRA)
			compras.append(c3.name)
			ck("pacotes fixos continuam funcionando", c3.valor_centavos == ci.FAIXAS[0]["centavos"])
	finally:
		for n in compras:
			frappe.delete_doc(ci.DOCTYPE_COMPRA, n, force=1, ignore_permissions=True)
		frappe.db.set_single_value("CRM Credito IA", "saldo_centavos", antes)
		au.save_settings(json.dumps({"credito_personalizado_ativo": 0}))
		frappe.db.commit()
	return res
