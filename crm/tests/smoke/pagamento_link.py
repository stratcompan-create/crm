"""Teste de fumaça: link de pagamento do InfinitePay (Financeiro).
A chamada real à API do InfinitePay é substituída por um stub — não faz
requisição de verdade. Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json
from unittest import mock

import frappe

from crm.api import pagamento as pg


def run():
	frappe.set_user("Administrator")
	res = []
	made = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	settings = frappe.get_single("FCRM Settings")
	handle_original = settings.get("infinitepay_handle")

	try:
		# sem InfiniteTag configurada: deve recusar com mensagem clara
		settings.infinitepay_handle = ""
		settings.save()
		lead = frappe.get_doc({
			"doctype": "CRM Lead", "first_name": "Zz Pagamento", "last_name": "Teste",
			"email": "zz.pagamento@example.com", "lead_owner": "Administrator",
		}).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))
		deal = frappe.get_doc({
			"doctype": "CRM Deal", "first_name": "Zz Pagamento", "last_name": "Teste",
			"email": "zz.pagamento@example.com", "lead": lead.name, "deal_owner": "Administrator",
			"deal_value": 1000, "status": "Qualification",
		}).insert(ignore_permissions=True)
		made.append(("CRM Deal", deal.name))
		honorario = frappe.get_doc({
			"doctype": "CRM Honorario", "deal": deal.name, "tipo_honorario": "Fixo",
			"servico": "CRM Jurídico", "valor": 850.0,
		}).insert(ignore_permissions=True)
		made.append(("CRM Honorario", honorario.name))

		erro_sem_handle = None
		try:
			pg.gerar_link_pagamento(honorario.name)
		except frappe.ValidationError as e:
			erro_sem_handle = str(e)
		ck("sem InfiniteTag configurada, recusa com mensagem clara", erro_sem_handle and "infinitetag" in erro_sem_handle.lower())

		# com handle configurado e urlopen substituído: gera e salva o link
		settings.infinitepay_handle = "$stratcompany-teste"
		settings.save()

		class _RespFake:
			def __init__(self, body):
				self._body = body
			def read(self):
				return self._body
			def __enter__(self):
				return self
			def __exit__(self, *a):
				return False

		resposta_fake = json.dumps({"url": "https://checkout.infinitepay.io/abc123"}).encode()
		with mock.patch.object(pg.urllib.request, "urlopen", return_value=_RespFake(resposta_fake)) as mocked:
			r = pg.gerar_link_pagamento(honorario.name)
			ck("devolve o link da resposta", r["link"] == "https://checkout.infinitepay.io/abc123")

			payload_enviado = json.loads(mocked.call_args[0][0].data)
			ck("manda o handle sem o $", payload_enviado["handle"] == "stratcompany-teste")
			ck("manda o valor em centavos", payload_enviado["items"][0]["price"] == 85000)
			ck("order_nsu é o nome do honorário (para correlacionar depois)", payload_enviado["order_nsu"] == honorario.name)
			ck("webhook_url leva o secret pra validar quem chama depois", "secret=" in payload_enviado["webhook_url"])

		link_salvo = frappe.db.get_value("CRM Honorario", honorario.name, "link_pagamento")
		ck("link fica salvo no honorário", link_salvo == "https://checkout.infinitepay.io/abc123")

		# webhook: correlaciona pelo order_nsu e marca como Pago
		r1 = pg._aplicar_pagamento({"order_nsu": honorario.name, "amount": 85000, "paid_amount": 85000})
		ck("webhook marca como pago quando o valor bate", r1["ok"] and frappe.db.get_value("CRM Honorario", honorario.name, "status") == "Pago")

		r2 = pg._aplicar_pagamento({"order_nsu": "não-existe-123"})
		ck("webhook ignora order_nsu desconhecido", r2["ok"] is False)

		frappe.db.set_value("CRM Honorario", honorario.name, "status", "Pendente")
		r3 = pg._aplicar_pagamento({"order_nsu": honorario.name, "amount": 85000, "paid_amount": 100})
		ck("webhook ignora pagamento com valor menor que o esperado", r3["ok"] is False and frappe.db.get_value("CRM Honorario", honorario.name, "status") == "Pendente")

		# endpoint publico (webhook_infinitepay) exige o secret certo - sem isso
		# qualquer um na internet poderia marcar um honorario como pago so
		# adivinhando o nome do documento
		payload_bytes = json.dumps({"order_nsu": honorario.name, "amount": 85000, "paid_amount": 85000}).encode()
		with mock.patch.object(frappe, "request", mock.Mock(args={"secret": "errado"}, get_data=lambda: payload_bytes), create=True):
			r4 = pg.webhook_infinitepay()
		ck(
			"endpoint do webhook recusa secret errado",
			r4["ok"] is False and frappe.db.get_value("CRM Honorario", honorario.name, "status") == "Pendente",
		)

		secreto_certo = pg._webhook_secret()
		with mock.patch.object(frappe, "request", mock.Mock(args={"secret": secreto_certo}, get_data=lambda: payload_bytes), create=True):
			r5 = pg.webhook_infinitepay()
		ck(
			"endpoint do webhook aceita com o secret certo",
			r5["ok"] and frappe.db.get_value("CRM Honorario", honorario.name, "status") == "Pago",
		)
	finally:
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		settings.infinitepay_handle = handle_original or ""
		settings.save()
		frappe.db.commit()

	return res
