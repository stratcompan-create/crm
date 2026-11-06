# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Audiência confirmada — a logística da audiência, não o prazo dela.
#
# Falta de cliente em audiência é o prejuízo mais silencioso de um escritório de volume:
# perde-se o dia, o deslocamento, o correspondente e, na trabalhista, o processo pode ser
# arquivado (CLT art. 844). Aqui o CRM confirma cliente e testemunha 7 dias antes e 1 dia
# antes, com resposta em um toque pelo link. Quem não responde até a véspera vira tarefa
# para alguém ligar.
#
# O CRM NÃO controla prazo nem intimação: a data da audiência é digitada (ou importada) pelo
# escritório a partir do software jurídico, que continua sendo a fonte oficial.
#
# Tudo que sai para o cliente é informativo e em linguagem simples: o que levar e o que
# esperar. Nenhuma mensagem promete resultado (Provimento 205/2021 da OAB).

import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, get_url, now_datetime

from crm.api.automacoes import _brand, _create_task, _first_manager

DOCTYPE = "CRM Audiencia"
DOCTYPE_PESSOA = "CRM Audiencia Presenca"

TIPOS = ["Inicial", "Una", "Instrução", "Conciliação", "Julgamento", "Perícia", "Outra"]
MODALIDADES = ["Presencial", "Videoconferência"]
SITUACOES = ["Agendada", "Realizada", "Adiada", "Cancelada"]
TIPOS_PESSOA = ["Cliente", "Testemunha", "Preposto", "Advogado", "Outro"]
CONFIRMACOES = ["Aguardando", "Confirmado", "Não poderá ir"]

# quantas horas antes cada aviso sai (o job roda de hora em hora)
JANELA_7D = 7 * 24
JANELA_1D = 30


def _juridico() -> bool:
	from crm.provision import PERFIS_JURIDICOS, get_profile

	return get_profile() in PERFIS_JURIDICOS


def _cfg():
	from crm.api.automacoes import get_config

	return get_config()


def _modulo_ativo() -> bool:
	return _juridico() and bool(cint(_cfg().get("audiencia_ativo", 1)))


def _assert_ativo():
	if not _juridico():
		frappe.throw(_("A agenda de audiências existe só no perfil de escritório de advocacia."))
	if not cint(_cfg().get("audiencia_ativo", 1)):
		frappe.throw(_("A agenda de audiências está desligada em Configurações → Automações."))


def _deal(deal: str, ptype: str = "read"):
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission(ptype)
	return d


def _aud(audiencia: str, ptype: str = "read"):
	a = frappe.get_doc(DOCTYPE, audiencia)
	_deal(a.deal, ptype)
	return a


# ------------------------------------------------------------------ o que levar / o que esperar

def orientacoes(tipo: str = "Una", modalidade: str = "Presencial") -> list[str]:
	"""Texto fixo, em linguagem simples. Não gasta crédito de IA e não promete resultado."""
	itens = []
	if modalidade == "Videoconferência":
		itens += [
			_("A audiência é por vídeo. Entre pelo link 15 minutos antes para testar câmera, microfone e internet."),
			_("Fique num lugar silencioso, sozinho e com boa luz. Não pode ter outra pessoa ajudando a responder."),
			_("Tenha o documento com foto na mão: o juiz pede para mostrar na câmera."),
		]
	else:
		itens += [
			_("Chegue 30 minutos antes do horário. A entrada do fórum tem fila e revista."),
			_("Leve documento com foto (RG ou CNH). Sem documento não entra."),
		]
	itens.append(_("Vista-se de forma discreta: evite short, chinelo, boné e regata."))

	if tipo in ("Inicial", "Una", "Conciliação"):
		itens.append(_("Nessa audiência pode aparecer proposta de acordo. Você não é obrigado a aceitar nada na hora — "
						"quem decide é você, e o escritório explica a conta antes."))
	if tipo in ("Una", "Instrução"):
		itens += [
			_("Você vai ser ouvido pelo juiz. Responda só o que for perguntado, com calma, e diga 'não lembro' "
			  "quando não lembrar. Não é prova de memória."),
			_("As testemunhas ficam fora da sala e entram uma por vez. Não combine resposta com ninguém: "
			  "isso derruba o valor do depoimento."),
		]
	if tipo == "Perícia":
		itens.append(_("Leve todos os exames, laudos e receitas que tiver, mesmo os antigos, na via original."))
	if tipo == "Julgamento":
		itens.append(_("Sua presença não é obrigatória nessa, mas avise se puder comparecer."))

	itens.append(_("Se faltar sem avisar e sem justificativa, o processo pode ser arquivado e ter custas a pagar "
					"(CLT art. 844). Qualquer problema para comparecer, avise o escritório o quanto antes."))
	return itens


# ------------------------------------------------------------------ envio

def _link(token: str) -> str:
	return get_url(f"/audiencia?t={token}")


def _quando(dt) -> str:
	return get_datetime(dt).strftime("%d/%m/%Y às %H:%M")


def _tem_email() -> bool:
	"""Existe conta de envio configurada? Isolado numa função própria porque é a condição
	que decide entre avisar de verdade e abrir tarefa para alguém ligar."""
	return bool(frappe.db.exists("Email Account", {"enable_outgoing": 1}))


def _enviar_para(pessoa, aud, vespera: bool = False) -> str:
	"""Manda o pedido de confirmação. Sem e-mail (da pessoa ou do sistema), cria tarefa
	para alguém ligar — o CRM não finge que avisou."""
	quando = _quando(aud.data_hora)
	marca = _brand()
	if not (pessoa.get("email") or "").strip() or not _tem_email():
		_create_task(
			aud.deal,
			_("Ligar para {0} — confirmar audiência de {1}").format(pessoa.nome, quando),
			_("{0} não tem e-mail cadastrado (ou o envio não está configurado). Confirme a presença por telefone: {1}").format(
				pessoa.nome, pessoa.get("telefone") or _("sem telefone cadastrado")
			),
			aud.get("responsavel") or _first_manager(),
		)
		return "tarefa"

	botao = "display:inline-block;padding:11px 20px;border-radius:999px;text-decoration:none;font-weight:bold;margin:4px 6px 4px 0"
	onde = ""
	if aud.get("modalidade") == "Videoconferência":
		if aud.get("link_virtual"):
			onde = _("<p><b>Por vídeo:</b> <a href='{0}'>{0}</a></p>").format(frappe.utils.escape_html(aud.link_virtual))
		else:
			onde = _("<p><b>Por vídeo.</b> O link é enviado pelo escritório antes do dia.</p>")
	elif aud.get("local"):
		onde = f"<p><b>{_('Local')}:</b> {frappe.utils.escape_html(aud.local)}</p>"
	if aud.get("vara"):
		onde += f"<p><b>{_('Vara')}:</b> {frappe.utils.escape_html(aud.vara)}</p>"

	lista = "".join(f"<li style='margin-bottom:6px'>{frappe.utils.escape_html(i)}</li>"
					for i in orientacoes(aud.get("tipo") or "Una", aud.get("modalidade") or "Presencial"))
	extra = (f"<p>{frappe.utils.escape_html(aud.orientacoes)}</p>" if aud.get("orientacoes") else "")
	intro = (_("Sua audiência é amanhã.") if vespera
			 else _("Sua audiência está marcada. Confirme abaixo se você vai poder comparecer."))
	primeiro = (pessoa.nome or "").split(" ")[0]

	html = (
		f"<div style='font-family:Arial,sans-serif;max-width:560px;color:#111'>"
		f"<p>{_('Olá')}, {frappe.utils.escape_html(primeiro)}! {intro}</p>"
		f"<p style='font-size:17px'><b>{quando}</b> ({_('horário de Brasília')})</p>{onde}{extra}"
		f"<p><a style='{botao};background:#042d3c;color:#fff' href='{_link(pessoa.token)}&acao=confirmar'>{_('Confirmo que vou')}</a>"
		f"<a style='{botao};background:#eee;color:#333' href='{_link(pessoa.token)}&acao=nao'>{_('Não vou poder ir')}</a></p>"
		f"<p style='margin-top:22px'><b>{_('O que levar e o que esperar')}</b></p>"
		f"<ul style='padding-left:18px;font-size:14px;line-height:1.5'>{lista}</ul>"
		f"<p style='color:#777;font-size:12px;margin-top:22px'>{frappe.utils.escape_html(marca)}<br>"
		f"{_('Esta mensagem é informativa e não representa garantia de resultado.')}</p></div>"
	)
	frappe.sendmail(
		recipients=[pessoa.email],
		subject=(_("Lembrete: audiência amanhã, {0}") if vespera else _("Confirme sua audiência — {0}")).format(quando),
		message=html,
		delayed=False,
	)
	frappe.db.set_value(DOCTYPE_PESSOA, pessoa.name, "avisos_enviados",
						cint(pessoa.get("avisos_enviados")) + 1, update_modified=False)
	return "email"


# ------------------------------------------------------------------ leitura

@frappe.whitelist()
def status() -> dict:
	return {"ativo": _modulo_ativo(), "juridico": _juridico()}


@frappe.whitelist()
def listar(dias=90, incluir_passadas=0) -> dict:
	_assert_ativo()
	agora = now_datetime()
	filtros = {"status": ["in", ["Agendada", "Adiada"]]}
	if cint(incluir_passadas):
		filtros["data_hora"] = [">=", add_to_date(agora, days=-cint(dias) or -90)]
	else:
		filtros["data_hora"] = ["between", [agora, add_to_date(agora, days=cint(dias) or 90)]]

	saida, pendentes_total = [], 0
	for a in frappe.get_list(DOCTYPE, filters=filtros, fields=["name", "deal", "tipo", "data_hora", "status",
															   "modalidade", "local", "vara", "responsavel"],
							 order_by="data_hora asc", limit_page_length=300):
		pessoas = frappe.get_all(DOCTYPE_PESSOA, filters={"audiencia": a.name},
								 fields=["name", "tipo", "nome", "telefone", "email", "confirmacao", "respondido_em"],
								 order_by="creation asc")
		pend = [p for p in pessoas if p.confirmacao == "Aguardando"]
		nao = [p for p in pessoas if p.confirmacao == "Não poderá ir"]
		pendentes_total += len(pend)
		horas = (get_datetime(a.data_hora) - agora).total_seconds() / 3600
		saida.append({
			"name": a.name,
			"deal": a.deal,
			"caso": _rotulo(a.deal),
			"tipo": a.tipo,
			"data_hora": str(a.data_hora),
			"quando": _quando(a.data_hora),
			"status": a.status,
			"modalidade": a.modalidade,
			"local": a.local or "",
			"vara": a.vara or "",
			"responsavel": a.responsavel or "",
			"pessoas": [{**p, "respondido_em": str(p.respondido_em or "")} for p in pessoas],
			"total": len(pessoas),
			"confirmados": len(pessoas) - len(pend) - len(nao),
			"aguardando": len(pend),
			"recusaram": len(nao),
			"horas_restantes": round(horas, 1),
			# o alerta que importa: véspera com gente sem resposta
			"risco": bool(pend) and horas <= 48,
		})
	return {"audiencias": saida, "pendentes": pendentes_total, "tipos": TIPOS, "modalidades": MODALIDADES,
			"tipos_pessoa": TIPOS_PESSOA, "situacoes": SITUACOES}


def _rotulo(deal: str) -> str:
	from crm.api.processo import _rotulo_caso

	try:
		return _rotulo_caso(deal)
	except Exception:
		return deal


@frappe.whitelist()
def buscar_casos(termo: str = "", limite=20) -> list[dict]:
	"""Para escolher o caso ao marcar a audiência. Vai pelo get_list (e não get_all) para
	respeitar a permissão por caso: quem não tem acesso ao caso não o vê na lista."""
	_assert_ativo()
	termo = (termo or "").strip()
	or_filtros = None
	if termo:
		like = f"%{termo}%"
		or_filtros = [["lead_name", "like", like], ["organization", "like", like],
					  ["first_name", "like", like], ["last_name", "like", like],
					  ["numero_processo", "like", like]]
	linhas = frappe.get_list("CRM Deal", or_filters=or_filtros,
							 filters={"encerrado": 0},
							 fields=["name", "lead_name", "organization", "first_name",
									 "last_name", "numero_processo"],
							 order_by="modified desc", limit_page_length=cint(limite) or 20)
	saida = []
	for l in linhas:
		nome = (l.lead_name or l.organization
				or f"{l.first_name or ''} {l.last_name or ''}".strip() or l.name)
		saida.append({"name": l.name, "rotulo": nome,
					  "processo": l.numero_processo or ""})
	return saida


@frappe.whitelist()
def obter(audiencia: str) -> dict:
	_assert_ativo()
	a = _aud(audiencia)
	pessoas = frappe.get_all(DOCTYPE_PESSOA, filters={"audiencia": a.name},
							 fields=["name", "tipo", "nome", "telefone", "email", "parte", "confirmacao",
									 "respondido_em", "observacao_resposta", "avisos_enviados"],
							 order_by="creation asc")
	return {
		"name": a.name, "deal": a.deal, "caso": _rotulo(a.deal), "tipo": a.tipo,
		"data_hora": str(a.data_hora), "quando": _quando(a.data_hora), "status": a.status,
		"modalidade": a.modalidade, "local": a.local or "", "vara": a.vara or "",
		"link_virtual": a.link_virtual or "", "responsavel": a.responsavel or "",
		"orientacoes": a.orientacoes or "", "observacoes": a.observacoes or "",
		"lembrete_7d": cint(a.lembrete_7d), "lembrete_1d": cint(a.lembrete_1d),
		"pessoas": [{**p, "respondido_em": str(p.respondido_em or "")} for p in pessoas],
		"orientacoes_padrao": orientacoes(a.tipo or "Una", a.modalidade or "Presencial"),
	}


# ------------------------------------------------------------------ gravação

@frappe.whitelist()
def criar(deal: str, data_hora: str, tipo: str = "Una", modalidade: str = "Presencial", local: str = "",
		  vara: str = "", link_virtual: str = "", responsavel: str = "", orientacoes_extras: str = "",
		  observacoes: str = "", trazer_testemunhas=1) -> dict:
	_assert_ativo()
	d = _deal(deal, "write")
	if not (data_hora or "").strip():
		frappe.throw(_("Informe a data e a hora da audiência."))
	quando = get_datetime(data_hora)
	if tipo not in TIPOS:
		tipo = "Outra"
	if modalidade not in MODALIDADES:
		modalidade = "Presencial"
	a = frappe.get_doc({
		"doctype": DOCTYPE, "deal": deal, "tipo": tipo, "data_hora": quando, "status": "Agendada",
		"modalidade": modalidade, "local": (local or "").strip()[:200] or None,
		"vara": (vara or "").strip()[:140] or None, "link_virtual": (link_virtual or "").strip()[:300] or None,
		"responsavel": responsavel or d.get("deal_owner") or _first_manager(),
		"orientacoes": (orientacoes_extras or "").strip()[:1000] or None,
		"observacoes": (observacoes or "").strip()[:1000] or None,
	}).insert()

	# o cliente do caso entra sempre
	from crm.api.automacoes import _client

	cli = _client(deal)
	_inserir_pessoa(a.name, "Cliente", cli.completo, "", cli.email or "")
	if cint(trazer_testemunhas):
		for p in frappe.get_all("CRM Parte", filters={"deal": deal, "tipo": "Testemunha"},
								fields=["name", "nome", "telefone", "email"]):
			_inserir_pessoa(a.name, "Testemunha", p.nome, p.get("telefone") or "", p.get("email") or "", p.name)

	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal",
					"reference_name": deal,
					"content": _("Audiência {0} marcada para {1}.").format(tipo.lower(), _quando(quando))}
				   ).insert(ignore_permissions=True)
	return {"name": a.name}


def _inserir_pessoa(audiencia: str, tipo: str, nome: str, telefone: str = "", email: str = "",
					parte: str | None = None) -> str:
	p = frappe.get_doc({
		"doctype": DOCTYPE_PESSOA, "audiencia": audiencia, "tipo": tipo if tipo in TIPOS_PESSOA else "Outro",
		"nome": (nome or _("Sem nome")).strip()[:140], "telefone": (telefone or "").strip()[:30] or None,
		"email": (email or "").strip()[:140] or None, "parte": parte,
		"confirmacao": "Aguardando", "token": secrets.token_urlsafe(20),
	}).insert()
	return p.name


@frappe.whitelist()
def atualizar(audiencia: str, **campos) -> dict:
	_assert_ativo()
	a = _aud(audiencia, "write")
	permitidos = {"tipo", "data_hora", "modalidade", "local", "vara", "link_virtual", "responsavel",
				  "orientacoes", "observacoes", "status"}
	mudou = {}
	for k, v in (campos or {}).items():
		if k not in permitidos:
			continue
		if k == "tipo" and v not in TIPOS:
			continue
		if k == "modalidade" and v not in MODALIDADES:
			continue
		if k == "status" and v not in SITUACOES:
			continue
		mudou[k] = get_datetime(v) if k == "data_hora" else ((v or "").strip() or None if isinstance(v, str) else v)
	if not mudou:
		return {"ok": True}
	# remarcou: os avisos precisam sair de novo com a data nova
	if "data_hora" in mudou and get_datetime(mudou["data_hora"]) != get_datetime(a.data_hora):
		mudou.update({"lembrete_7d": 0, "lembrete_1d": 0, "cobranca_criada": 0})
		frappe.db.set_value(DOCTYPE_PESSOA, {"audiencia": audiencia}, {
			"confirmacao": "Aguardando", "respondido_em": None,
		}, update_modified=False)
		frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal",
						"reference_name": a.deal,
						"content": _("Audiência remarcada para {0}. As confirmações foram zeradas.").format(
							_quando(mudou["data_hora"]))}).insert(ignore_permissions=True)
	frappe.db.set_value(DOCTYPE, audiencia, mudou)
	return {"ok": True}


@frappe.whitelist()
def adicionar_pessoa(audiencia: str, nome: str, tipo: str = "Testemunha", telefone: str = "",
					 email: str = "", parte: str = "") -> dict:
	_assert_ativo()
	_aud(audiencia, "write")
	if not (nome or "").strip():
		frappe.throw(_("Informe o nome."))
	return {"name": _inserir_pessoa(audiencia, tipo, nome, telefone, email, parte or None)}


@frappe.whitelist()
def remover_pessoa(pessoa: str) -> dict:
	_assert_ativo()
	aud = frappe.db.get_value(DOCTYPE_PESSOA, pessoa, "audiencia")
	_aud(aud, "write")
	frappe.delete_doc(DOCTYPE_PESSOA, pessoa)
	return {"ok": True}


@frappe.whitelist()
def marcar_manual(pessoa: str, confirmacao: str, observacao: str = "") -> dict:
	"""Confirmou por telefone: a pessoa da equipe registra aqui."""
	_assert_ativo()
	aud = frappe.db.get_value(DOCTYPE_PESSOA, pessoa, "audiencia")
	a = _aud(aud, "write")
	if confirmacao not in CONFIRMACOES:
		frappe.throw(_("Situação inválida."))
	nome = frappe.db.get_value(DOCTYPE_PESSOA, pessoa, "nome")
	frappe.db.set_value(DOCTYPE_PESSOA, pessoa, {
		"confirmacao": confirmacao, "respondido_em": now_datetime(),
		"observacao_resposta": _("Registrado pela equipe. {0}").format((observacao or "").strip())[:500],
	})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal",
					"reference_name": a.deal,
					"content": _("{0}: {1} (registrado pela equipe) para a audiência de {2}.").format(
						nome, confirmacao.lower(), _quando(a.data_hora))}).insert(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def cobrar(pessoa: str) -> dict:
	"""Botão 'cobrar agora' da tela."""
	_assert_ativo()
	aud = frappe.db.get_value(DOCTYPE_PESSOA, pessoa, "audiencia")
	a = _aud(aud, "write")
	if a.status not in ("Agendada", "Adiada"):
		frappe.throw(_("Essa audiência não está mais agendada."))
	p = frappe.get_doc(DOCTYPE_PESSOA, pessoa)
	via = _enviar_para(p, a, vespera=(get_datetime(a.data_hora) - now_datetime()).total_seconds() <= 48 * 3600)
	return {"ok": True, "via": via}


# ------------------------------------------------------------------ resposta pelo link (público)

def _limite_publico():
	"""O token é a credencial; segura tentativa em massa de adivinhar link."""
	cache = frappe.cache()
	# fora de uma requisicao web (job, teste, console) nao existe IP: nao e motivo pra quebrar
	chave = f"audiencia_pub_{getattr(frappe.local, 'request_ip', None) or 'interno'}"
	n = cint(cache.get_value(chave))
	if n >= 40:
		frappe.throw(_("Muitas tentativas. Tente de novo mais tarde."), frappe.RateLimitExceededError)
	cache.set_value(chave, n + 1, expires_in_sec=3600)


@frappe.whitelist(allow_guest=True)
def responder(token: str, acao: str = "confirmar", observacao: str = "") -> dict:
	"""Chamada pela página pública /audiencia. Não exige login: o token é a credencial."""
	_limite_publico()
	if not token or len(token) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value(DOCTYPE_PESSOA, {"token": token})
	if not name:
		frappe.throw(_("Link inválido."))
	p = frappe.get_doc(DOCTYPE_PESSOA, name)
	a = frappe.get_doc(DOCTYPE, p.audiencia)
	if a.status == "Cancelada":
		return {"situacao": "cancelada", "quando": _quando(a.data_hora)}
	if get_datetime(a.data_hora) < now_datetime():
		return {"situacao": "passou", "quando": _quando(a.data_hora)}

	nova = "Confirmado" if acao == "confirmar" else "Não poderá ir"
	frappe.db.set_value(DOCTYPE_PESSOA, name, {
		"confirmacao": nova, "respondido_em": now_datetime(),
		"observacao_resposta": (observacao or "").strip()[:500] or None,
	})
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Deal",
					"reference_name": a.deal,
					"content": _("{0} respondeu pelo link: {1} — audiência de {2}.").format(
						p.nome, nova.lower(), _quando(a.data_hora))}).insert(ignore_permissions=True)
	if nova == "Não poderá ir":
		_create_task(
			a.deal,
			_("{0} avisou que NÃO vai à audiência de {1}").format(p.nome, _quando(a.data_hora)),
			_("Resposta pelo link. {0}").format((observacao or "").strip() or _("Sem justificativa escrita.")),
			a.get("responsavel") or _first_manager(),
		)
	frappe.db.commit()
	return {"situacao": "ok", "resposta": nova, "quando": _quando(a.data_hora)}


@frappe.whitelist(allow_guest=True)
def dados_publicos(token: str) -> dict:
	"""O que a página pública mostra antes da pessoa clicar."""
	_limite_publico()
	if not token or len(token) > 80:
		frappe.throw(_("Link inválido."))
	name = frappe.db.get_value(DOCTYPE_PESSOA, {"token": token})
	if not name:
		frappe.throw(_("Link inválido."))
	p = frappe.get_doc(DOCTYPE_PESSOA, name)
	a = frappe.get_doc(DOCTYPE, p.audiencia)
	return {
		"nome": (p.nome or "").split(" ")[0],
		"marca": _brand(),
		"logo": frappe.db.get_single_value("FCRM Settings", "brand_logo") or "",
		"quando": _quando(a.data_hora),
		"tipo": a.tipo,
		"modalidade": a.modalidade,
		"local": a.local or "",
		"vara": a.vara or "",
		"link_virtual": a.link_virtual or "",
		"cancelada": a.status == "Cancelada",
		"passou": get_datetime(a.data_hora) < now_datetime(),
		"ja_respondeu": p.confirmacao != "Aguardando",
		"resposta": p.confirmacao,
		"orientacoes": orientacoes(a.tipo or "Una", a.modalidade or "Presencial") + (
			[a.orientacoes] if a.orientacoes else []),
	}


# ------------------------------------------------------------------ job de hora em hora

def enviar_lembretes():
	"""7 dias antes e 1 dia antes. Quem não respondeu até a véspera vira tarefa de ligação.
	A janela é 'até X horas antes' (e não uma faixa estreita) para o aviso não se perder se o
	servidor ficou fora do ar na hora exata."""
	from crm.provision import PERFIS_JURIDICOS, get_profile

	if get_profile() not in PERFIS_JURIDICOS:
		return
	if not cint(_cfg().get("audiencia_ativo", 1)):
		return
	agora = now_datetime()
	proximas = frappe.get_all(
		DOCTYPE,
		filters={"status": ["in", ["Agendada", "Adiada"]],
				 "data_hora": ["between", [agora, add_to_date(agora, hours=JANELA_7D)]]},
		fields=["name", "deal", "tipo", "data_hora", "status", "modalidade", "local", "vara",
				"link_virtual", "orientacoes", "responsavel", "lembrete_7d", "lembrete_1d", "cobranca_criada"],
	)
	for a in proximas:
		aud = frappe._dict(a)
		horas = (get_datetime(aud.data_hora) - agora).total_seconds() / 3600
		vespera = horas <= JANELA_1D
		if vespera and cint(aud.lembrete_1d):
			continue
		if not vespera and cint(aud.lembrete_7d):
			continue
		pessoas = frappe.get_all(DOCTYPE_PESSOA, filters={"audiencia": aud.name},
								 fields=["name", "nome", "telefone", "email", "confirmacao",
										 "token", "avisos_enviados"])
		for linha in pessoas:
			# no aviso de 7 dias cobra quem não respondeu; na véspera fala com todo mundo
			if not vespera and linha.confirmacao != "Aguardando":
				continue
			if vespera and linha.confirmacao == "Não poderá ir":
				continue
			try:
				_enviar_para(frappe._dict(linha), aud, vespera=vespera)
			except Exception:
				frappe.log_error("Audiência: falha ao avisar participante", frappe.get_traceback())
		frappe.db.set_value(DOCTYPE, aud.name,
							{"lembrete_1d": 1} if vespera else {"lembrete_7d": 1}, update_modified=False)

		# véspera com gente sem resposta: alguém tem que ligar
		if vespera and not cint(aud.cobranca_criada):
			sem_resposta = [l.nome for l in pessoas if l.confirmacao == "Aguardando"]
			if sem_resposta:
				try:
					_create_task(
						aud.deal,
						_("Ligar hoje: {0} sem confirmação para a audiência de {1}").format(
							", ".join(sem_resposta[:6]), _quando(aud.data_hora)),
						_("Ninguém respondeu o link de confirmação. Confirme por telefone antes da audiência."),
						aud.get("responsavel") or _first_manager(),
					)
					frappe.db.set_value(DOCTYPE, aud.name, "cobranca_criada", 1, update_modified=False)
				except Exception:
					frappe.log_error("Audiência: falha ao criar a tarefa de cobrança", frappe.get_traceback())
	frappe.db.commit()
