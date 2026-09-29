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

PLACEHOLDER_TITULO = "Título chamativo aqui"
PLACEHOLDER_CORPO = "Subtítulo curto de apoio"

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
def criar_rascunho(tipo: str = "Carrossel", anterior: str = None) -> dict:
	"""Cria uma conversa só com um slide de exemplo, pra o editor (painel de edição +
	canvas) abrir direto na tela, sem a pessoa precisar mandar mensagem pro chat primeiro.
	Se "anterior" for passado e ainda não tiver nenhuma mensagem, apaga (era só rascunho,
	ninguém usou) pra não acumular lixo toda vez que a pessoa troca de aba Post/Carrossel/Story."""
	if anterior:
		try:
			doc_antigo = frappe.get_doc("CRM Conteudo Conversa", anterior)
			if doc_antigo.owner == frappe.session.user and not json.loads(doc_antigo.mensagens or "[]"):
				frappe.delete_doc("CRM Conteudo Conversa", anterior, force=True, ignore_permissions=True)
		except frappe.DoesNotExistError:
			pass

	doc = frappe.new_doc("CRM Conteudo Conversa")
	doc.tipo = tipo if tipo in ("Post", "Carrossel", "Story") else "Carrossel"
	doc.titulo = "Rascunho"
	doc.mensagens = "[]"
	doc.slides = json.dumps([{"titulo": PLACEHOLDER_TITULO, "corpo": PLACEHOLDER_CORPO}])
	doc.insert()
	return {"conversa": doc.name, "tipo": doc.tipo, "slides": json.loads(doc.slides)}


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
		"legenda": doc.legenda or "",
	}


@frappe.whitelist()
def marcar_agendado(conversa: str, data_agendada: str) -> dict:
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.status = "Agendado"
	doc.data_agendada = data_agendada
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def salvar_slide(conversa: str, indice, canvas: str = None, titulo: str = None, corpo: str = None, layout: str = None) -> dict:
	"""Guarda o estado do editor visual (Fabric.js) daquele slide especifico. titulo/corpo/layout
	sao opcionais - so vem quando a pessoa edita o texto ou o layout direto pelo painel (sem
	isso, o slide.canvas salvo ficaria com o texto novo mas o dado por tras ficaria desatualizado,
	e o proximo "gerar com IA" ou remontagem do slide usaria o texto antigo)."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	slides = json.loads(doc.slides or "[]")
	indice = int(indice)
	if indice < 0 or indice >= len(slides):
		frappe.throw("Esse slide não existe mais nessa conversa.")
	if canvas is not None:
		slides[indice]["canvas"] = json.loads(canvas)
	if titulo is not None:
		slides[indice]["titulo"] = titulo
	if corpo is not None:
		slides[indice]["corpo"] = corpo
	if layout is not None:
		slides[indice]["layout"] = json.loads(layout) if isinstance(layout, str) else layout
	doc.slides = json.dumps(slides)
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def gerar_texto_slide(conversa: str, indice, instrucao: str = "") -> dict:
	"""Reescreve titulo+corpo de UM slide, olhando o resto do carrossel pra manter
	consistencia. Sem instrucao: gera conteudo novo pro slide (mesmo tema dos outros).
	Com instrucao: refina o que ja esta la ("deixe mais curto", "tom mais direto", etc)."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.check_permission("write")

	from crm.api.ficha import _api_key as _claude_api_key

	api_key = _claude_api_key()
	if not api_key:
		frappe.throw("Configure a chave da API do Claude em Configurações → Automações antes de usar o gerador de conteúdo.")

	slides = json.loads(doc.slides or "[]")
	indice = int(indice)
	if indice < 0 or indice >= len(slides):
		frappe.throw("Esse slide não existe mais nessa conversa.")

	contexto = "\n".join(
		f"Slide {i + 1}{' (este é o que você vai reescrever)' if i == indice else ''}: "
		f"título=\"{s.get('titulo', '')}\" corpo=\"{s.get('corpo', '')}\""
		for i, s in enumerate(slides)
	)
	instrucao = (instrucao or "").strip()
	pedido = (
		f"Reescreva o slide {indice + 1} seguindo esta instrução: {instrucao}"
		if instrucao
		else f"Gere um título e um corpo novos para o slide {indice + 1}, no mesmo tema e tom dos outros slides."
	)
	system = (
		"Você ajuda a criar o conteúdo de UM slide de um carrossel de Instagram, mantendo "
		"consistência com os outros slides do mesmo carrossel.\n\n"
		f"Carrossel até agora:\n{contexto}\n\n"
		"Responda SEMPRE em JSON válido, sem nenhum texto fora do JSON, exatamente neste formato: "
		'{"titulo": "...", "corpo": "..."}'
	)
	try:
		texto = _call_claude(api_key, system, [{"role": "user", "content": pedido}])
	except urllib.error.HTTPError as e:
		frappe.log_error("Gerador de conteúdo: a API do Claude recusou o pedido", f"{e.code} {e.read()}")
		frappe.throw("A API do Claude recusou o pedido. Confira a chave configurada.")
	except Exception:
		frappe.log_error("Gerador de conteúdo: falha ao chamar a API do Claude", frappe.get_traceback())
		frappe.throw("Não consegui falar com a IA agora. Tente de novo em instantes.")

	novo = _parse_slide_unico(texto)
	if not novo:
		frappe.throw("A IA não devolveu um formato que eu entendesse. Tente de novo.")

	slides[indice]["titulo"] = novo.get("titulo", slides[indice].get("titulo", ""))
	slides[indice]["corpo"] = novo.get("corpo", slides[indice].get("corpo", ""))
	slides[indice].pop("canvas", None)  # o canvas salvo tinha o texto antigo - remonta do zero
	doc.slides = json.dumps(slides)
	doc.save()
	return {"titulo": slides[indice]["titulo"], "corpo": slides[indice]["corpo"]}


def _parse_slide_unico(texto: str) -> dict:
	texto = (texto or "").strip()
	if texto.startswith("```"):
		texto = texto.strip("`")
		primeira_linha, _, resto = texto.partition("\n")
		texto = resto if primeira_linha.strip().lower() in ("json", "") else texto
	try:
		dados = json.loads(texto)
		if isinstance(dados, dict) and ("titulo" in dados or "corpo" in dados):
			return dados
	except Exception:
		pass
	return {}


@frappe.whitelist()
def duplicar_slide(conversa: str, indice) -> dict:
	"""Clona o slide (titulo, corpo, layout e canvas) e insere logo depois do original."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.check_permission("write")
	slides = json.loads(doc.slides or "[]")
	indice = int(indice)
	if indice < 0 or indice >= len(slides):
		frappe.throw("Esse slide não existe mais nessa conversa.")
	copia = json.loads(json.dumps(slides[indice]))
	slides.insert(indice + 1, copia)
	doc.slides = json.dumps(slides)
	doc.save()
	return {"slides": slides, "novo_indice": indice + 1}


@frappe.whitelist()
def aplicar_layout_todos(conversa: str, layout: str) -> dict:
	"""Aplica o mesmo layout (posicao, margem, fonte, sombra, fundo, etc.) em todos os
	slides da conversa. Apaga o canvas salvo de cada um pra eles remontarem do zero com
	o layout novo, igual acontece quando o layout muda so de um slide."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.check_permission("write")
	layout_dict = json.loads(layout) if isinstance(layout, str) else layout
	slides = json.loads(doc.slides or "[]")
	for slide in slides:
		slide["layout"] = dict(layout_dict)
		slide.pop("canvas", None)
	doc.slides = json.dumps(slides)
	doc.save()
	return {"slides": slides}


@frappe.whitelist()
def salvar_legenda(conversa: str, legenda: str = "") -> dict:
	"""Salva a legenda escrita/editada a mao - sem chamar a IA."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.check_permission("write")
	doc.legenda = legenda or ""
	doc.save()
	return {"ok": True}


@frappe.whitelist()
def gerar_legenda(conversa: str) -> dict:
	"""Gera a legenda do post/carrossel a partir do conteudo de todos os slides."""
	doc = frappe.get_doc("CRM Conteudo Conversa", conversa)
	doc.check_permission("write")

	from crm.api.ficha import _api_key as _claude_api_key

	api_key = _claude_api_key()
	if not api_key:
		frappe.throw("Configure a chave da API do Claude em Configurações → Automações antes de usar o gerador de conteúdo.")

	slides = json.loads(doc.slides or "[]")
	if not slides:
		frappe.throw("Gere os slides antes de pedir a legenda.")

	conteudo = "\n".join(f"Slide {i + 1}: {s.get('titulo', '')} — {s.get('corpo', '')}" for i, s in enumerate(slides))
	system = (
		"Você escreve a legenda de um post de Instagram a partir do conteúdo dos slides do carrossel. "
		"Direto, sem hashtag em excesso (no máximo 3, só se fizer sentido), sem emoji forçado, "
		"terminando com uma chamada pra ação simples (comentar, salvar ou compartilhar). "
		"Responda só com o texto da legenda, nada mais."
	)
	try:
		legenda = _call_claude(api_key, system, [{"role": "user", "content": conteudo}]).strip()
	except urllib.error.HTTPError as e:
		frappe.log_error("Gerador de conteúdo: a API do Claude recusou o pedido", f"{e.code} {e.read()}")
		frappe.throw("A API do Claude recusou o pedido. Confira a chave configurada.")
	except Exception:
		frappe.log_error("Gerador de conteúdo: falha ao chamar a API do Claude", frappe.get_traceback())
		frappe.throw("Não consegui falar com a IA agora. Tente de novo em instantes.")

	doc.legenda = legenda
	doc.save()
	return {"legenda": legenda}
