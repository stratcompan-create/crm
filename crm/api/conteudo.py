# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Gerador de conteúdo do Instagram: um chat com o Claude que já conhece a marca
# (cor, fonte, nome) e devolve o texto de cada slide de um post/carrossel/story.

import json
import urllib.error
import urllib.request

import frappe

MODEL = "claude-sonnet-5"
MAX_TOKENS = 2000
API_URL = "https://api.anthropic.com/v1/messages"

SISTEMA_TEMPLATE = """Você ajuda a criar conteúdo para o Instagram (posts, carrosséis e stories) de uma empresa.

Marca:
- Nome: {nome}
- Cor principal: {cor}
- Cor de destaque: {destaque}
- Cor neutra: {neutra}

Tipo de conteúdo pedido: {tipo}

Responda SEMPRE em JSON válido, sem nenhum texto fora do JSON, exatamente neste formato:
{{"resposta": "texto curto pro chat, explicando o que você fez ou perguntando algo",
  "slides": [{{"titulo": "...", "corpo": "..."}}]}}

Para "Post" e "Story", use só 1 slide. Para "Carrossel", use entre 3 e 8 slides.
Se o pedido do usuário não tiver informação suficiente para gerar algo bom, pergunte
no campo "resposta" o que falta e devolva "slides": []."""


def _brand_context() -> dict:
	s = frappe.get_single("FCRM Settings")
	return {
		"nome": s.get("brand_name") or "a empresa",
		"cor": s.get("brand_color") or "#042d3c",
		"destaque": s.get("brand_accent") or "#8aa1a9",
		"neutra": s.get("brand_neutral") or "#f4f2ed",
	}


def _call_claude(api_key: str, system: str, mensagens: list) -> str:
	body = json.dumps({
		"model": MODEL,
		"max_tokens": MAX_TOKENS,
		"system": system,
		"messages": [{"role": m["role"], "content": m["content"]} for m in mensagens],
	}).encode()
	req = urllib.request.Request(
		API_URL,
		data=body,
		headers={
			"content-type": "application/json",
			"x-api-key": api_key,
			"anthropic-version": "2023-06-01",
		},
	)
	with urllib.request.urlopen(req, timeout=60) as resp:
		data = json.loads(resp.read())
	return "".join(bloco.get("text", "") for bloco in data.get("content", []))


def _parse_resposta(texto: str) -> dict:
	texto = (texto or "").strip()
	if texto.startswith("```"):
		texto = texto.strip("`")
		primeira_linha, _, resto = texto.partition("\n")
		texto = resto if primeira_linha.strip().lower() in ("json", "") else texto
	try:
		dados = json.loads(texto)
		if isinstance(dados, dict) and "slides" in dados:
			return dados
	except Exception:
		pass
	return {"resposta": texto, "slides": []}


@frappe.whitelist()
def enviar_mensagem(mensagem: str, conversa: str = None, tipo: str = "Carrossel") -> dict:
	mensagem = (mensagem or "").strip()
	if not mensagem:
		frappe.throw("Escreva o que você quer criar.")

	from crm.api.ficha import _api_key as _claude_api_key

	api_key = _claude_api_key()
	if not api_key:
		frappe.throw("Configure a chave da API do Claude em Configurações → Automações antes de usar o gerador de conteúdo.")

	if conversa:
		doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	else:
		doc = frappe.new_doc("CRM Conteudo Conversa")
		doc.tipo = tipo if tipo in ("Post", "Carrossel", "Story") else "Carrossel"
		doc.titulo = mensagem[:80]
		doc.mensagens = "[]"
		doc.slides = "[]"
		doc.insert()

	historico = json.loads(doc.mensagens or "[]")
	historico.append({"role": "user", "content": mensagem})

	system = SISTEMA_TEMPLATE.format(tipo=doc.tipo, **_brand_context())
	try:
		texto = _call_claude(api_key, system, historico)
	except urllib.error.HTTPError as e:
		frappe.log_error("Gerador de conteúdo: a API do Claude recusou o pedido", f"{e.code} {e.read()}")
		frappe.throw("A API do Claude recusou o pedido. Confira a chave configurada.")
	except Exception:
		frappe.log_error("Gerador de conteúdo: falha ao chamar a API do Claude", frappe.get_traceback())
		frappe.throw("Não consegui falar com a IA agora. Tente de novo em instantes.")

	resultado = _parse_resposta(texto)
	historico.append({"role": "assistant", "content": texto})
	doc.mensagens = json.dumps(historico)
	if resultado.get("slides"):
		doc.slides = json.dumps(resultado["slides"])
	doc.save()

	return {
		"conversa": doc.name,
		"tipo": doc.tipo,
		"resposta": resultado.get("resposta", ""),
		"slides": json.loads(doc.slides or "[]"),
	}


@frappe.whitelist()
def listar_conversas(tipo: str = None) -> list:
	filters = {"tipo": tipo} if tipo else {}
	return frappe.get_all(
		"CRM Conteudo Conversa",
		filters=filters,
		fields=["name", "titulo", "tipo", "status", "modified"],
		order_by="modified desc",
		limit_page_length=50,
	)


@frappe.whitelist()
def obter_conversa(conversa: str) -> dict:
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	return {
		"name": doc.name,
		"titulo": doc.titulo,
		"tipo": doc.tipo,
		"status": doc.status,
		"mensagens": json.loads(doc.mensagens or "[]"),
		"slides": json.loads(doc.slides or "[]"),
	}


@frappe.whitelist()
def marcar_agendado(conversa: str, data_agendada: str) -> dict:
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.status = "Agendado"
	doc.data_agendada = data_agendada
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def salvar_slide(conversa: str, indice, canvas: str) -> dict:
	"""Guarda o estado do editor visual (Fabric.js) daquele slide especifico -
	o resto do slide (titulo/corpo gerados pela IA) continua junto, so ganha
	a chave "canvas" com o que a pessoa desenhou/ajustou."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	slides = json.loads(doc.slides or "[]")
	indice = int(indice)
	if indice < 0 or indice >= len(slides):
		frappe.throw("Esse slide não existe mais nessa conversa.")
	slides[indice]["canvas"] = json.loads(canvas)
	doc.slides = json.dumps(slides)
	doc.save()
	return {"ok": True}
