# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Link de cobrança do InfinitePay para um Honorário: gera o link (POST na API
# do InfinitePay) e recebe a confirmação de pagamento por webhook, marcando o
# Honorário como Pago sozinho. Usa a InfiniteTag (handle) configurada em
# Configurações — a API do InfinitePay não pede chave secreta, só o handle.

import json
import urllib.error
import urllib.request

import frappe
from frappe.utils import flt, get_url, nowdate

API_URL = "https://api.checkout.infinitepay.io/links"

MANAGER_ROLES = ("System Manager", "Sales Manager")


def _client_label(deal: str) -> str:
	row = frappe.db.get_value("CRM Deal", deal, ["organization", "first_name", "last_name"], as_dict=True) or {}
	return row.get("organization") or " ".join(filter(None, [row.get("first_name"), row.get("last_name")])) or deal


def _webhook_secret() -> str:
	"""Segredo usado pra validar que o POST no webhook realmente veio do fluxo
	que a gente iniciou - a API do InfinitePay não assina o webhook, então sem
	isso qualquer pessoa que adivinhasse o nome de um Honorário conseguiria
	marcar ele como Pago só chamando a URL do webhook na mão."""
	secret = frappe.db.get_single_value("FCRM Settings", "webhook_secret_pagamento")
	if not secret:
		secret = frappe.generate_hash(length=32)
		frappe.db.set_single_value("FCRM Settings", "webhook_secret_pagamento", secret)
	return secret


@frappe.whitelist()
def gerar_link_pagamento(honorario: str) -> dict:
	frappe.only_for(MANAGER_ROLES)

	handle = (frappe.get_single("FCRM Settings").get("infinitepay_handle") or "").strip().lstrip("$")
	if not handle:
		frappe.throw("Configure a InfiniteTag (handle do InfinitePay) em Configurações → Integrações → IA & Pagamentos antes de gerar um link.")

	doc = frappe.get_doc("CRM Honorario", honorario)
	if not flt(doc.valor):
		frappe.throw("Esse honorário não tem valor definido.")

	descricao = (doc.servico or doc.tipo_honorario or "Honorário")[:80]
	payload = {
		"handle": handle,
		"order_nsu": doc.name,
		"webhook_url": get_url(f"/api/method/crm.api.pagamento.webhook_infinitepay?secret={_webhook_secret()}"),
		"items": [{
			"quantity": 1,
			"price": round(flt(doc.valor) * 100),
			"description": f"{descricao} - {_client_label(doc.deal)}"[:120],
		}],
	}
	req = urllib.request.Request(
		API_URL,
		data=json.dumps(payload).encode(),
		headers={"content-type": "application/json"},
		method="POST",
	)
	try:
		with urllib.request.urlopen(req, timeout=20) as resp:
			data = json.loads(resp.read())
	except urllib.error.HTTPError as e:
		frappe.log_error("InfinitePay: falha ao gerar link", f"{e.code} {e.read()}")
		frappe.throw("O InfinitePay recusou o pedido de link. Confira a InfiniteTag configurada.")
	except Exception:
		frappe.log_error("InfinitePay: falha ao gerar link", frappe.get_traceback())
		frappe.throw("Não consegui gerar o link agora. Tente de novo em instantes.")

	link = data.get("url") or data.get("payment_url") or data.get("checkout_url") or data.get("link")
	if not link:
		frappe.log_error("InfinitePay: resposta sem link reconhecível", json.dumps(data))
		frappe.throw("O InfinitePay respondeu, mas a resposta não trouxe um link reconhecível. Veja o log de erros.")

	doc.db_set("link_pagamento", link)
	return {"link": link}


@frappe.whitelist(allow_guest=True)
def webhook_infinitepay():
	"""Chamado pelo InfinitePay quando um link é pago."""
	if frappe.request.args.get("secret") != _webhook_secret():
		frappe.local.response.http_status_code = 403
		return {"ok": False}
	try:
		payload = json.loads((frappe.request.get_data() or b"{}").decode("utf-8", "replace"))
	except ValueError:
		return {"ok": False}
	return _aplicar_pagamento(payload)


def _aplicar_pagamento(payload: dict) -> dict:
	"""Correlaciona pelo order_nsu (que é o próprio nome do Honorário) e marca como
	Pago. Separado de webhook_infinitepay() para poder ser testado sem uma requisição HTTP real."""
	order_nsu = payload.get("order_nsu")
	if not order_nsu or not frappe.db.exists("CRM Honorario", order_nsu):
		return {"ok": False}

	amount = flt(payload.get("amount"))
	paid_amount = flt(payload.get("paid_amount"))
	if amount and paid_amount < amount:
		return {"ok": False}

	doc = frappe.get_doc("CRM Honorario", order_nsu)
	if doc.status != "Pago":
		doc.status = "Pago"
		doc.data_pagamento = nowdate()
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	return {"ok": True}
