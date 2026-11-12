# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Triagem no WhatsApp.
# Quem escreve pela primeira vez vira Atendimento e recebe perguntas FIXAS, escritas pelo
# escritório (nome, o que aconteceu, prazo, cidade). O robô nunca responde dúvida jurídica:
# a IA só lê as respostas por dentro e organiza área, urgência e resumo para o advogado.
# Quando alguém da equipe responde à mão, o robô para naquela conversa.
#
# Fala por dois motores, conforme o que o site tiver conectado:
#   - YCloud (coexistência, o número continua no celular) — é o caso da agência
#   - app `whatsapp` (API oficial da Meta) — escritório com conta Business própria
#
# PERFIL AGÊNCIA: o número é pessoal também (o dono usa o mesmo WhatsApp). Por isso lá o robô
# NÃO aborda quem escrever qualquer coisa: só entra em cena quando a mensagem traz a palavra
# combinada do anúncio ou do vídeo (ex.: "DEMO"). Em perfil de escritório, o número é do
# escritório e todo contato novo entra na triagem, como antes.

import json
import re

import frappe
import requests
from frappe import _
from frappe.utils import add_days, cint, now_datetime, nowdate

ORIGEM = "WhatsApp"
EXPIRA_HORAS = 48  # conversa parada há mais tempo que isso recomeça do zero

BOAS_VINDAS = (
	"Olá! Aqui é o atendimento do escritório. Vou fazer algumas perguntas rápidas para "
	"organizar o seu contato e um advogado vai retornar. Por aqui não damos orientação jurídica."
)
PERGUNTAS = (
	"Qual é o seu nome completo?\n"
	"Em poucas palavras, o que aconteceu e em que podemos ajudar?\n"
	"Existe algum prazo ou data marcada (audiência, notificação, intimação)? Se sim, qual?\n"
	"Em qual cidade você está?"
)
ENCERRAMENTO = (
	"Obrigado! Suas informações foram registradas e um advogado do escritório vai entrar em "
	"contato. Se for urgente, escreva URGENTE aqui."
)

# --- perfil agência: quem escreve é advogado interessado no sistema, não cliente com um caso
BOAS_VINDAS_AGENCIA = (
	"Olá! Aqui é a Stratcompany. Vou fazer três perguntas rápidas para entender o seu "
	"escritório e já te mandar o acesso de demonstração."
)
PERGUNTAS_AGENCIA = (
	"Qual é o seu nome e o nome do escritório?\n"
	"Em que área você atua?\n"
	"Hoje são quantas pessoas no escritório (só você, ou equipe)?\n"
	"O que te chamou atenção: a triagem no WhatsApp, o acompanhamento do cliente, o financeiro, ou o sistema todo?"
)
ENCERRAMENTO_AGENCIA = (
	"Perfeito, obrigado! Já tenho o que preciso — em instantes te mando o acesso de "
	"demonstração para você mexer à vontade, sem compromisso."
)
# palavra que liga o robô no perfil agência (a do CTA do vídeo). Configurável.
PALAVRA_CHAVE = "DEMO, CRM, SISTEMA"
# o que a agência vende — a IA diz em qual deles o contato está interessado
SERVICOS = ("CRM Jurídico", "Site", "Tráfego pago", "Audiovisual", "Conteúdo")

# sinais de urgência que dispensam a IA (o advogado é avisado na hora)
URGENTE = re.compile(
	r"\b(urgente|pres[oa]|pris[aã]o|flagrante|audi[eê]ncia (hoje|amanh[aã])|liminar|despejo|"
	r"intima[cç][aã]o|prazo (vence|acaba) (hoje|amanh[aã]))\b",
	re.I,
)


def _cfg():
	from crm.api.automacoes import get_config

	return get_config()


def _na_agencia() -> bool:
	from crm.provision import PERFIS_JURIDICOS, get_profile

	return get_profile() not in PERFIS_JURIDICOS


def padroes() -> dict:
	"""Textos de fábrica da triagem, conforme o perfil do site."""
	if _na_agencia():
		return {
			"boas_vindas": BOAS_VINDAS_AGENCIA,
			"perguntas": PERGUNTAS_AGENCIA,
			"encerramento": ENCERRAMENTO_AGENCIA,
			"palavra_chave": PALAVRA_CHAVE,
		}
	return {
		"boas_vindas": BOAS_VINDAS,
		"perguntas": PERGUNTAS,
		"encerramento": ENCERRAMENTO,
		"palavra_chave": "",
	}


def _texto(cfg, campo: str) -> str:
	return (cfg.get("triagem_" + campo) or "").strip() or padroes()[campo]


def _perguntas(cfg) -> list[str]:
	return [p.strip() for p in _texto(cfg, "perguntas").splitlines() if p.strip()]


def _palavras_chave(cfg) -> list[str]:
	bruto = cfg.get("triagem_palavra_chave")
	bruto = bruto.strip() if bruto else padroes()["palavra_chave"]
	return [p.strip().casefold() for p in re.split(r"[,;\n]", bruto) if p.strip()]


def _pode_iniciar(texto: str, cfg) -> bool:
	"""Começar uma triagem com quem nunca escreveu antes.

	No escritório, sim: o número é do escritório. Na agência o número também é pessoal,
	então o robô só entra quando a mensagem traz a palavra combinada no anúncio ou no vídeo.
	Palavra em branco na configuração = robô atende todo mundo (quem liga, assume).
	"""
	palavras = _palavras_chave(cfg)
	if not palavras:
		return True
	alvo = (texto or "").casefold()
	return any(re.search(r"\b" + re.escape(p) + r"\b", alvo) for p in palavras)


def _motor() -> str:
	"""Por onde este CRM fala no WhatsApp."""
	from crm.api import ycloud

	if ycloud.conectado():
		return "ycloud"
	if "whatsapp" in frappe.get_installed_apps():
		return "meta"
	return ""


def _responsavel(cfg) -> str:
	user = cfg.get("triagem_responsavel") or cfg.get("agenda_responsavel")
	if user:
		return user
	gestores = frappe.get_all(
		"Has Role", filters={"role": "Sales Manager", "parenttype": "User", "parent": ["not in", ["Administrator", "Guest"]]},
		pluck="parent", limit=1,
	)
	return gestores[0] if gestores else "Administrator"


def _enviar(telefone: str, lead: str, texto: str):
	"""Manda pelo motor conectado, marcado como mensagem do robô (não conta como 'equipe assumiu')."""
	frappe.flags.triagem_enviando = True
	try:
		if _motor() == "ycloud":
			from crm.api import ycloud

			ycloud.enviar_texto(telefone, texto)
		else:
			from whatsapp.whatsapp.api.messages import send_message

			send_message(to=telefone, message=texto, reference_doctype="CRM Lead", reference_docname=lead)
	finally:
		frappe.flags.triagem_enviando = False


def _novo_atendimento(telefone: str, nome: str, cfg) -> str:
	if not frappe.db.exists("CRM Lead Source", ORIGEM):
		frappe.get_doc({"doctype": "CRM Lead Source", "source_name": ORIGEM}).insert(ignore_permissions=True)
	first, _sep, last = (nome or "WhatsApp " + telefone[-4:]).partition(" ")
	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first,
			"last_name": last,
			"mobile_no": telefone,
			"source": ORIGEM,
			"lead_owner": _responsavel(cfg),
		}
	)
	lead.insert(ignore_permissions=True)
	return lead.name


def _triagem_aberta(telefone: str):
	nome = frappe.db.get_value(
		"CRM Triagem", {"telefone": telefone, "status": "Em andamento"}, "name", order_by="creation desc"
	)
	if not nome:
		return None
	t = frappe.get_doc("CRM Triagem", nome)
	if (now_datetime() - t.modified).total_seconds() > EXPIRA_HORAS * 3600:
		t.db_set("status", "Expirada")
		return None
	return t


# ------------------------------------------------------------------ ganchos do WhatsApp Message

def _equipe_assumiu(filtros: dict):
	for nome in frappe.get_all("CRM Triagem", dict(filtros, status="Em andamento"), pluck="name"):
		frappe.db.set_value("CRM Triagem", nome, "status", "Assumida pela equipe")


def ao_receber(doc, method=None):
	"""after_insert de WhatsApp Message (app da Meta): entrada → triagem; saída manual → equipe assumiu."""
	if doc.direction == "Outgoing":
		if not frappe.flags.triagem_enviando and doc.reference_doctype == "CRM Lead" and doc.reference_docname:
			_equipe_assumiu({"lead": doc.reference_docname})
		return
	if not cint(_cfg().get("triagem_ativa")):
		return
	frappe.enqueue(
		"crm.api.triagem_whatsapp.processar", queue="short", mensagem=doc.name, enqueue_after_commit=True
	)


def ao_receber_ycloud(doc, method=None):
	"""after_insert de CRM WhatsApp Mensagem (YCloud, número em coexistência).

	Resposta humana — pelo CRM ou pelo próprio celular — encerra o robô naquela conversa.
	É o que protege quem usa o mesmo número no dia a dia: assim que o dono responde, o robô cala.
	"""
	if doc.direction != "Received":
		if not frappe.flags.triagem_enviando:
			_equipe_assumiu({"telefone": doc.contato})
		return
	if not cint(_cfg().get("triagem_ativa")):
		return
	from crm.api import ycloud

	if cint(frappe.db.get_value(ycloud.CONTATO, doc.contato, "pessoal")):
		return  # contato marcado como pessoal nunca é abordado pelo robô
	frappe.enqueue(
		"crm.api.triagem_whatsapp.processar_ycloud", queue="short", mensagem=doc.name, enqueue_after_commit=True
	)


def _nome_do_perfil(telefone: str) -> str:
	if _motor() == "ycloud":
		from crm.api import ycloud

		return frappe.db.get_value(ycloud.CONTATO, telefone, "nome") or ""
	return frappe.db.get_value("WhatsApp Profile", {"phone_number": telefone}, "profile_name") or ""


def processar(mensagem: str):
	frappe.set_user("Administrator")
	try:
		_processar(frappe.get_doc("WhatsApp Message", mensagem))
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Triagem WhatsApp: falha", frappe.get_traceback())


class MensagemYCloud:
	"""Faz uma CRM WhatsApp Mensagem responder como a mensagem que `_processar` espera."""

	def __init__(self, doc):
		self._doc = doc
		self.message = doc.message or ""
		self.reference_doctype = "CRM Lead" if doc.lead else None
		self.reference_docname = doc.lead or None

	def get(self, campo, padrao=None):
		return {"from": self._doc.contato}.get(campo, padrao)

	def db_set(self, valores: dict, update_modified=True):
		lead = valores.get("reference_docname")
		if not lead:
			return
		from crm.api import ycloud

		frappe.db.set_value(ycloud.MENSAGEM, self._doc.name, "lead", lead, update_modified=False)
		frappe.db.set_value(ycloud.CONTATO, self._doc.contato, "lead", lead, update_modified=False)
		self.reference_doctype, self.reference_docname = "CRM Lead", lead


def processar_ycloud(mensagem: str):
	from crm.api import ycloud

	frappe.set_user("Administrator")
	try:
		_processar(MensagemYCloud(frappe.get_doc(ycloud.MENSAGEM, mensagem)))
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error("Triagem WhatsApp: falha", frappe.get_traceback())


def _processar(msg):
	cfg = _cfg()
	telefone = msg.get("from")
	texto = (msg.message or "").strip()
	if not telefone:
		return
	t = _triagem_aberta(telefone)
	if not t:
		# já é contato conhecido (cliente, caso ou atendimento em curso): quem atende é a equipe
		if msg.reference_doctype and msg.reference_docname:
			return
		if not _pode_iniciar(texto, cfg):
			return
		lead = _novo_atendimento(telefone, _nome_do_perfil(telefone), cfg)
		msg.db_set({"reference_doctype": "CRM Lead", "reference_docname": lead}, update_modified=False)
		t = frappe.get_doc(
			{"doctype": "CRM Triagem", "lead": lead, "telefone": telefone, "etapa": 0, "status": "Em andamento",
			 "respostas": json.dumps([{"pergunta": "Primeira mensagem", "resposta": texto}], ensure_ascii=False)}
		).insert(ignore_permissions=True)
		if URGENTE.search(texto):
			_avisar_urgente(t, texto, cfg)
		perguntas = _perguntas(cfg)
		_enviar(telefone, lead, _texto(cfg, "boas_vindas") + "\n\n" + perguntas[0])
		return

	perguntas = _perguntas(cfg)
	respostas = json.loads(t.respostas or "[]")
	etapa = cint(t.etapa)
	respostas.append({"pergunta": perguntas[etapa] if etapa < len(perguntas) else "", "resposta": texto})
	t.respostas = json.dumps(respostas, ensure_ascii=False)
	if etapa == 0 and texto and len(texto) <= 80 and not any(c.isdigit() for c in texto):
		# primeira pergunta é o nome: corrige o atendimento com o nome que a pessoa informou
		first, _sep, last = texto.partition(" ")
		frappe.db.set_value("CRM Lead", t.lead, {"first_name": first[:140], "last_name": last[:140]})
	if URGENTE.search(texto) and t.urgencia != "Alta":
		_avisar_urgente(t, texto, cfg)
	etapa += 1
	t.etapa = etapa
	if etapa < len(perguntas):
		t.save(ignore_permissions=True)
		_enviar(telefone, t.lead, perguntas[etapa])
		return
	t.status = "Concluída"
	t.concluida_em = now_datetime()
	t.save(ignore_permissions=True)
	_enviar(telefone, t.lead, _texto(cfg, "encerramento"))
	_concluir(t, cfg)


def _avisar_urgente(t, texto: str, cfg):
	t.urgencia = "Alta"
	t.save(ignore_permissions=True)
	_tarefa(t, cfg, _("URGENTE: retornar atendimento pelo WhatsApp"), _("Mensagem recebida: {0}").format(texto[:500]), "High", 0)


def _tarefa(t, cfg, titulo: str, descricao: str, prioridade: str, dias: int):
	frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": titulo,
			"description": frappe.utils.escape_html(descricao).replace("\n", "<br>"),
			"status": "Todo",
			"priority": prioridade,
			"assigned_to": frappe.db.get_value("CRM Lead", t.lead, "lead_owner") or _responsavel(cfg),
			"due_date": add_days(nowdate(), dias),
			"reference_doctype": "CRM Lead",
			"reference_docname": t.lead,
		}
	).insert(ignore_permissions=True)


def _texto_respostas(t) -> str:
	return "\n\n".join(f"{r['pergunta']}\n→ {r['resposta']}" for r in json.loads(t.respostas or "[]"))


def _concluir(t, cfg):
	classe = _classificar(t)
	t.area = classe.get("area") or ""
	if t.urgencia != "Alta":
		t.urgencia = classe.get("urgencia") or ""
	t.resumo = classe.get("resumo") or ""
	t.save(ignore_permissions=True)
	partes = [_("Triagem pelo WhatsApp concluída.")]
	if t.area:
		partes.append((_("Interesse: {0}") if _na_agencia() else _("Área provável: {0}")).format(t.area))
	if t.urgencia:
		partes.append(_("Urgência: {0}").format(t.urgencia))
	if t.resumo:
		partes.append(_("Resumo: {0}").format(t.resumo))
	cabeca = "\n".join(partes)
	frappe.get_doc(
		{
			"doctype": "FCRM Note",
			"title": _("Triagem pelo WhatsApp"),
			"content": frappe.utils.escape_html(cabeca + "\n\n" + _texto_respostas(t)).replace("\n", "<br>"),
			"reference_doctype": "CRM Lead",
			"reference_docname": t.lead,
		}
	).insert(ignore_permissions=True)
	if t.urgencia != "Alta":
		prioridade = "Medium" if t.urgencia == "Média" else "Low"
		_tarefa(t, cfg, _("Retornar atendimento do WhatsApp"), cabeca, prioridade, 1)


# ------------------------------------------------------------------ IA (só por dentro, nunca fala com o cliente)

def _classificar(t) -> dict:
	from crm.api import credito_ia
	from crm.api.ficha import API_URL, MODEL, _api_key

	key = _api_key()
	if not key or not credito_ia.saldo_suficiente():
		return {}
	if _na_agencia():
		sistema = (
			"Você organiza a triagem de uma agência que vende sistema, site e marketing para advogados. "
			"Leia as respostas e devolva SOMENTE um JSON com: "
			"\"area\" (o que a pessoa procura — um destes, ou \"Outra\": " + ", ".join(SERVICOS) + "), "
			"\"urgencia\" (\"Alta\", \"Média\" ou \"Baixa\": Alta se a pessoa já quer contratar ou tem prazo "
			"próprio; Baixa se está só olhando), "
			"\"resumo\" (até 3 frases objetivas: porte do escritório, área de atuação e o que ela quer resolver). "
			"Não invente fatos que não estejam nas respostas."
		)
	else:
		areas = frappe.get_all("CRM Modelo Area", pluck="area") or []
		sistema = (
			"Você organiza a triagem de um escritório de advocacia. Leia as respostas do cliente e devolva "
			"SOMENTE um JSON com: \"area\" (uma destas, ou \"Outra\": " + ", ".join(areas) + "), "
			"\"urgencia\" (\"Alta\", \"Média\" ou \"Baixa\": Alta se houver prisão, audiência ou prazo em até 5 dias), "
			"\"resumo\" (até 3 frases objetivas, sem opinar sobre o mérito nem sobre chances de êxito). "
			"Não invente fatos que não estejam nas respostas."
		)
	try:
		resp = requests.post(
			API_URL,
			headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
			json={"model": MODEL, "max_tokens": 600, "system": sistema,
				  "messages": [{"role": "user", "content": f"<respostas>\n{_texto_respostas(t)[:6000]}\n</respostas>"}]},
			timeout=60,
		)
		if not resp.ok:
			frappe.log_error("Triagem WhatsApp: IA com erro", resp.text[:1500])
			return {}
		data = resp.json()
		credito_ia.registrar_uso(data.get("usage"))
		texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
		m = re.search(r"\{.*\}", texto, re.S)
		out = json.loads(m.group(0)) if m else {}
	except (requests.RequestException, ValueError):
		frappe.log_error("Triagem WhatsApp: falha na IA", frappe.get_traceback())
		return {}
	urg = out.get("urgencia") if out.get("urgencia") in ("Alta", "Média", "Baixa") else ""
	return {"area": str(out.get("area") or "")[:140], "urgencia": urg, "resumo": str(out.get("resumo") or "")[:1000]}


# ------------------------------------------------------------------ tela de Configurações

@frappe.whitelist()
def estado() -> dict:
	frappe.only_for(("System Manager", "Sales Manager"))
	motor = _motor()
	conectado = motor == "ycloud" or (
		motor == "meta" and bool(frappe.db.count("WhatsApp Account", {"status": ["!=", "Inactive"]}))
	)
	cfg = _cfg()
	return {
		"conectado": conectado,
		"motor": motor,
		"por_palavra": _na_agencia(),
		"padrao": padroes(),
		"ultimas": frappe.get_all(
			"CRM Triagem", fields=["name", "lead", "status", "area", "urgencia", "creation"],
			order_by="creation desc", limit=10,
		),
		"ativa": cint(cfg.get("triagem_ativa")),
	}
