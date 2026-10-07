# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Saldo pré-pago de IA por site. Cada chamada à API do Claude (ficha automática,
# gerador de conteúdo, assistente de suporte, sugestões, follow-up) desconta do
# saldo o custo real daquela chamada (a Anthropic informa quantos tokens cada
# resposta usou). Quando o saldo acaba, a IA para de responder até o cliente
# comprar mais - ver gerar_link_credito() / webhook_credito() abaixo.
#
# O pagamento usa a InfiniteTag da Stratcompany (não a de cada escritório, que é
# só pra ele cobrar os próprios clientes) - por isso o handle vem da configuração
# do servidor (comum a todos os sites), não de FCRM Settings deste site.

import json
import urllib.error
import urllib.request

import frappe
from frappe import _
from frappe.utils import cint, flt, get_url

API_URL = "https://api.checkout.infinitepay.io/links"
DOCTYPE_SALDO = "CRM Credito IA"
DOCTYPE_COMPRA = "CRM Credito IA Compra"

MANAGER_ROLES = ("System Manager", "Sales Manager")

# Preço por milhão de tokens do claude-sonnet-5 (igual ao resto do CRM usa),
# convertido pra centavos de real. Ajuste aqui se o preço da Anthropic mudar
# ou se quiser outra margem - não precisa mexer em mais nada.
PRECO_ENTRADA_CENTAVOS_POR_MILHAO = 1650  # ~US$3/milhão, dólar a ~5,50
PRECO_SAIDA_CENTAVOS_POR_MILHAO = 8250  # ~US$15/milhão

# Faixas de recarga oferecidas ao cliente. "US$" é só o rótulo (referência do
# preço da Anthropic) - o valor cobrado de verdade é o de "centavos", em reais,
# já com a margem da Stratcompany embutida.
FAIXAS = [
	{"rotulo": "US$ 5", "centavos": 2700},
	{"rotulo": "US$ 20", "centavos": 11000},
	{"rotulo": "US$ 30", "centavos": 16500},
]


def _saldo_doc():
	return frappe.get_single(DOCTYPE_SALDO)


def _handle_central() -> str:
	return (frappe.conf.get("stratcompany_infinitepay_handle") or "").strip().lstrip("$")


def _webhook_secret() -> str:
	secret = frappe.db.get_single_value("FCRM Settings", "webhook_secret_credito_ia")
	if not secret:
		secret = frappe.generate_hash(length=32)
		frappe.db.set_single_value("FCRM Settings", "webhook_secret_credito_ia", secret)
	return secret


@frappe.whitelist()
def obter_saldo() -> dict:
	return {
		"ativo": _ativo(),
		"saldo_centavos": cint(_saldo_doc().saldo_centavos),
		"faixas": FAIXAS,
		"habilitado": bool(_handle_central()),
	}


def custo_centavos(usage: dict) -> int:
	"""Custo em centavos de uma chamada, a partir do `usage` que a Anthropic devolve
	em toda resposta ({"input_tokens": N, "output_tokens": M})."""
	entrada = cint((usage or {}).get("input_tokens"))
	saida = cint((usage or {}).get("output_tokens"))
	custo = (entrada * PRECO_ENTRADA_CENTAVOS_POR_MILHAO + saida * PRECO_SAIDA_CENTAVOS_POR_MILHAO) / 1_000_000
	return max(1, round(custo)) if (entrada or saida) else 0


def _ativo() -> bool:
	"""Controle de saldo é opt-in por site (Configurações > Automações) - desligado
	por padrão, pra não passar a bloquear a IA de ninguém (inclusive a sua própria
	agência) sem ter sido ligado de propósito pra aquele cliente."""
	try:
		from crm.api.automacoes import get_config
		return bool(cint(get_config().get("credito_ia_ativo", 0)))
	except Exception:
		return False


def saldo_suficiente() -> bool:
	if not _ativo():
		return True
	return cint(_saldo_doc().saldo_centavos) > 0


def registrar_uso(usage: dict) -> None:
	"""Desconta do saldo o custo de uma chamada. Só desconta se o controle estiver
	ligado pra este site. Nunca lança exceção - cobrar errado uma vez não pode
	derrubar a resposta que a pessoa já recebeu."""
	if not _ativo():
		return
	try:
		custo = custo_centavos(usage)
		if not custo:
			return
		frappe.db.set_single_value(
			DOCTYPE_SALDO, "saldo_centavos", cint(_saldo_doc().saldo_centavos) - custo
		)
		frappe.db.commit()
	except Exception:
		frappe.log_error("Crédito de IA: falha ao descontar uso", frappe.get_traceback())


@frappe.whitelist()
def gerar_link_credito(indice: int) -> dict:
	frappe.only_for(MANAGER_ROLES)
	handle = _handle_central()
	if not handle:
		frappe.throw(_("A recarga de crédito ainda não foi habilitada neste servidor. Fale com o suporte."))

	i = cint(indice)
	if i < 0 or i >= len(FAIXAS):
		frappe.throw(_("Faixa de recarga inválida."))
	faixa = FAIXAS[i]

	compra = frappe.get_doc({
		"doctype": DOCTYPE_COMPRA,
		"valor_centavos": faixa["centavos"],
		"status": "Pendente",
	})
	compra.insert(ignore_permissions=True)

	payload = {
		"handle": handle,
		"order_nsu": compra.name,
		"webhook_url": get_url(f"/api/method/crm.api.credito_ia.webhook_credito?secret={_webhook_secret()}"),
		"items": [{
			"quantity": 1,
			"price": faixa["centavos"],
			"description": f"Crédito de IA - {faixa['rotulo']}"[:120],
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
		frappe.log_error("Crédito de IA: falha ao gerar link", f"{e.code} {e.read()}")
		frappe.throw(_("O InfinitePay recusou o pedido de link."))
	except Exception:
		frappe.log_error("Crédito de IA: falha ao gerar link", frappe.get_traceback())
		frappe.throw(_("Não consegui gerar o link agora. Tente de novo em instantes."))

	link = data.get("url") or data.get("payment_url") or data.get("checkout_url") or data.get("link")
	if not link:
		frappe.log_error("Crédito de IA: resposta sem link reconhecível", json.dumps(data))
		frappe.throw(_("O InfinitePay respondeu, mas sem um link reconhecível. Veja o log de erros."))

	compra.db_set("link_pagamento", link)
	return {"link": link}


@frappe.whitelist(allow_guest=True)
def webhook_credito():
	if frappe.request.args.get("secret") != _webhook_secret():
		frappe.local.response.http_status_code = 403
		return {"ok": False}
	try:
		payload = json.loads((frappe.request.get_data() or b"{}").decode("utf-8", "replace"))
	except ValueError:
		return {"ok": False}
	return _aplicar_pagamento(payload)


def _aplicar_pagamento(payload: dict) -> dict:
	"""Correlaciona pelo order_nsu (nome da CRM Credito IA Compra) e credita o
	saldo. Separado de webhook_credito() para poder ser testado sem HTTP real."""
	order_nsu = payload.get("order_nsu")
	if not order_nsu or not frappe.db.exists(DOCTYPE_COMPRA, order_nsu):
		return {"ok": False}

	compra = frappe.get_doc(DOCTYPE_COMPRA, order_nsu)
	if compra.status == "Pago":
		return {"ok": True}

	amount = flt(payload.get("amount"))
	paid_amount = flt(payload.get("paid_amount"))
	if amount and paid_amount < amount:
		return {"ok": False}

	compra.status = "Pago"
	compra.save(ignore_permissions=True)
	frappe.db.set_single_value(
		DOCTYPE_SALDO, "saldo_centavos", cint(_saldo_doc().saldo_centavos) + cint(compra.valor_centavos)
	)
	frappe.db.commit()
	return {"ok": True}
