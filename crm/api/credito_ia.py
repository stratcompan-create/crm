# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Saldo pré-pago de IA por site. Cada chamada à API do Claude (ficha automática,
# gerador de conteúdo, assistente de suporte, sugestões, follow-up) desconta do
# saldo o custo da chamada, já na margem de venda (ver MARGEM_VENDA) - não no
# custo cru que a Anthropic cobra. Quando o saldo acaba, a IA para de responder
# até o cliente comprar mais - ver gerar_link_credito() / webhook_credito().
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

# Preço de CUSTO por milhão de tokens do claude-sonnet-5 (o que a Anthropic cobra
# de verdade, igual ao resto do CRM usa), convertido pra centavos de real.
PRECO_ENTRADA_CENTAVOS_POR_MILHAO = 1650  # ~US$3/milhão, dólar a ~5,50
PRECO_SAIDA_CENTAVOS_POR_MILHAO = 8250  # ~US$15/milhão

# Margem da Stratcompany em cima do custo - tanto no preço de venda das faixas
# de recarga quanto no que é descontado do saldo a cada uso. É por isso que a
# margem vira lucro de verdade: o saldo do cliente desconta no preço DE VENDA
# (custo + margem), não no custo cru - a diferença fica guardada como lucro em
# vez de virar uso extra de graça pro cliente.
MARGEM_VENDA = 0.20

DOLAR_EM_CENTAVOS = 550  # só usado pra calcular o preço de venda das faixas


def _preco_venda_centavos(usd: float) -> int:
	return round(usd * DOLAR_EM_CENTAVOS * (1 + MARGEM_VENDA))


def _custo_venda_uso(entrada: int, saida: int) -> int:
	"""Preço de venda (com margem) de UM uso típico de uma funcionalidade,
	a partir de uma estimativa de tokens de entrada/saída dela."""
	raw = (entrada * PRECO_ENTRADA_CENTAVOS_POR_MILHAO + saida * PRECO_SAIDA_CENTAVOS_POR_MILHAO) / 1_000_000
	return max(1, round(raw * (1 + MARGEM_VENDA)))


# Tokens típicos (entrada, saída) de cada funcionalidade que usa IA - são as
# mesmas pra qualquer tipo de negócio (loja, escritório, o que for), só o
# CONTEÚDO que a IA gera é que muda, não a quantidade de uso. Usado só pra
# mostrar pro cliente, de forma concreta, o que cada faixa de recarga permite
# fazer - "tokens" sozinho não diz nada pra ninguém.
USO_REFERENCIA = [
	{"label": "fichas de reunião geradas automaticamente", "entrada": 4000, "saida": 700},
	{"label": "conteúdos de Instagram gerados", "entrada": 2500, "saida": 1200},
	{"label": "trocas de mensagem com o assistente de suporte", "entrada": 1800, "saida": 350},
]


def _capacidades(centavos: int) -> list:
	out = []
	for info in USO_REFERENCIA:
		custo = _custo_venda_uso(info["entrada"], info["saida"])
		out.append({"label": info["label"], "quantidade": centavos // custo})
	return out


def _formatar_reais(centavos: int) -> str:
	return f"R$ {centavos / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Faixas de recarga oferecidas ao cliente. Os US$ abaixo são só a referência
# INTERNA de custo da Anthropic usada pra calcular o preço de venda em reais
# (já com a margem da Stratcompany embutida) - o cliente só vê o valor em R$,
# nunca dólar. "capacidades" é uma estimativa de quanto cada faixa rende em
# uso real, pro cliente ver valor concreto, não só um preço em reais solto.
FAIXAS = [
	{"centavos": _preco_venda_centavos(5)},
	{"centavos": _preco_venda_centavos(20)},
	{"centavos": _preco_venda_centavos(30)},
]
for _faixa in FAIXAS:
	_faixa["rotulo"] = _formatar_reais(_faixa["centavos"])
	_faixa["capacidades"] = _capacidades(_faixa["centavos"])
del _faixa


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


@frappe.whitelist()
def relatorio() -> dict:
	"""Pra mostrar no Financeiro: quanto entrou de recarga, quanto custou de IA
	de verdade (preço cru da Anthropic, sem a margem) e quanto disso é lucro."""
	frappe.only_for(MANAGER_ROLES)
	recarregado = cint(
		frappe.db.sql(
			f"select coalesce(sum(valor_centavos), 0) from `tab{DOCTYPE_COMPRA}` where status = 'Pago'"
		)[0][0]
	)
	doc = _saldo_doc()
	custo_real = cint(doc.custo_real_centavos)
	return {
		"ativo": _ativo(),
		"recarregado_centavos": recarregado,
		"custo_real_centavos": custo_real,
		"lucro_centavos": recarregado - custo_real,
		"saldo_centavos": cint(doc.saldo_centavos),
	}


def custo_real_centavos(usage: dict) -> int:
	"""Custo de verdade (o que a Anthropic cobra, sem margem) de uma chamada, a
	partir do `usage` que ela devolve em toda resposta
	({"input_tokens": N, "output_tokens": M})."""
	entrada = cint((usage or {}).get("input_tokens"))
	saida = cint((usage or {}).get("output_tokens"))
	custo = (entrada * PRECO_ENTRADA_CENTAVOS_POR_MILHAO + saida * PRECO_SAIDA_CENTAVOS_POR_MILHAO) / 1_000_000
	return max(1, round(custo)) if (entrada or saida) else 0


def custo_centavos(usage: dict) -> int:
	"""Mantido pelo nome antigo pra compatibilidade - ver custo_real_centavos()."""
	return custo_real_centavos(usage)


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
	"""Desconta do saldo o custo de uma chamada, já no preço de venda (com
	margem) - e separadamente soma o custo real (sem margem) pro relatório de
	lucro. Só roda se o controle estiver ligado pra este site. Nunca lança
	exceção - cobrar errado uma vez não pode derrubar a resposta que a pessoa
	já recebeu."""
	if not _ativo():
		return
	try:
		custo_real = custo_real_centavos(usage)
		if not custo_real:
			return
		custo_venda = round(custo_real * (1 + MARGEM_VENDA))
		doc = _saldo_doc()
		frappe.db.set_single_value(DOCTYPE_SALDO, "saldo_centavos", cint(doc.saldo_centavos) - custo_venda)
		frappe.db.set_single_value(
			DOCTYPE_SALDO, "custo_real_centavos", cint(doc.custo_real_centavos) + custo_real
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
