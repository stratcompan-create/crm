# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Radar de prescrição — do ATENDIMENTO que ainda não virou caso.
#
# Quem sai de um emprego demora pra decidir se vai processar: fala com o escritório, pensa,
# some, e volta quando já perdeu parte do direito. Esse radar guarda a data da saída desde a
# primeira conversa e mostra, em dia e em dinheiro, o que a espera está custando.
#
# Duas regras diferentes entram na conta (CF art. 7º, XXIX):
#   - PRAZO PARA AJUIZAR (bienal): 2 anos contados da saída. Passou, acabou.
#   - QUANTO PODE PEDIR (quinquenal): só os últimos 5 anos contados do dia do ajuizamento.
#     Esse é o que sangra devagar: cada mês de espera empurra a janela pra frente e derruba
#     o mês mais antigo do pedido.
#
# IMPORTANTE — o valor aqui é ESTIMATIVA DE USO INTERNO, pra o escritório priorizar a fila.
# Não aparece pro cliente, não vira promessa de resultado e não sai em nenhuma mensagem
# automática (Provimento 205/2021 da OAB). Quem decide o que o caso vale é o advogado.
#
# E o que este radar NÃO é: ele não controla prazo de processo. Prazo processual, publicação
# e andamento continuam no software jurídico do escritório.

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, getdate, nowdate

AVISO_INTERNO = (
	"Estimativa de uso interno, para o escritório priorizar a fila de atendimento. "
	"Não é promessa de resultado e não deve ser repassada ao cliente como valor devido."
)

NIVEIS = {
	"vencido": {"rotulo": "Prazo vencido", "ordem": 0},
	"critico": {"rotulo": "Crítico", "ordem": 1},
	"atencao": {"rotulo": "Atenção", "ordem": 2},
	"no_prazo": {"rotulo": "No prazo", "ordem": 3},
	"sem_data": {"rotulo": "Sem data de saída", "ordem": 4},
}


def _managers_only():
	# o radar mostra estimativa de valor por atendimento: é informação de gestão,
	# não de operação do dia a dia
	frappe.only_for(("System Manager", "Sales Manager"))


def _juridico() -> bool:
	from crm.provision import PERFIS_JURIDICOS, get_profile

	return get_profile() in PERFIS_JURIDICOS


def _cfg():
	from crm.api.automacoes import get_config

	return get_config()


def _modulo_ativo() -> bool:
	"""Só existe em perfil de escritório, e o escritório pode desligar."""
	return _juridico() and bool(cint(_cfg().get("prescricao_ativo", 1)))


def _assert_ativo():
	if not _juridico():
		frappe.throw(_("O radar de prescrição existe só no perfil de escritório de advocacia."))
	if not cint(_cfg().get("prescricao_ativo", 1)):
		frappe.throw(_("O radar de prescrição está desligado em Configurações → Automações."))


# ------------------------------------------------------------------ a conta

def _meses_entre(inicio, fim) -> int:
	"""Meses cheios entre duas datas. 0 se a ordem estiver invertida."""
	if not inicio or not fim:
		return 0
	inicio, fim = getdate(inicio), getdate(fim)
	if fim <= inicio:
		return 0
	meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
	if fim.day < inicio.day:
		meses -= 1
	return max(0, meses)


def calcular(data_saida, data_admissao=None, valor_mes=0, cfg=None, hoje=None) -> dict:
	"""O coração do radar. Separado da leitura do banco pra poder ser testado sozinho."""
	cfg = cfg if cfg is not None else _cfg()
	hoje = getdate(hoje or nowdate())
	anos = max(1, cint(cfg.get("prescricao_anos")) or 2)
	retro = max(1, cint(cfg.get("prescricao_retroativo_anos")) or 5)
	dias_critico = max(1, cint(cfg.get("prescricao_dias_critico")) or 30)
	dias_atencao = max(dias_critico + 1, cint(cfg.get("prescricao_dias_atencao")) or 90)

	if not data_saida:
		return {
			"nivel": "sem_data",
			"rotulo": NIVEIS["sem_data"]["rotulo"],
			"ordem": NIVEIS["sem_data"]["ordem"],
			"limite": "",
			"dias_restantes": None,
			"meses_no_pedido": None,
			"meses_perdidos": None,
			"custo_espera": 0.0,
			"perde_por_mes": 0.0,
			"explicacao": _("Sem a data da saída o radar não tem como contar o prazo. Pergunte no próximo contato."),
		}

	data_saida = getdate(data_saida)
	data_admissao = getdate(data_admissao) if data_admissao else None
	if data_admissao and data_admissao > data_saida:
		# cadastro trocado: não inventa conta em cima de dado errado
		data_admissao = None

	limite = getdate(add_to_date(data_saida, years=anos))
	dias = (limite - hoje).days

	# o que ainda cabe no pedido se ajuizar HOJE
	corte_hoje = getdate(add_to_date(hoje, years=-retro))
	ini_hoje = max(corte_hoje, data_admissao) if data_admissao else corte_hoje
	ini_hoje = min(ini_hoje, data_saida)
	meses_hoje = _meses_entre(ini_hoje, data_saida)

	# o que caberia se tivesse ajuizado no dia da saída
	corte_saida = getdate(add_to_date(data_saida, years=-retro))
	ini_saida = max(corte_saida, data_admissao) if data_admissao else corte_saida
	ini_saida = min(ini_saida, data_saida)
	meses_saida = _meses_entre(ini_saida, data_saida)

	meses_perdidos = max(0, meses_saida - meses_hoje)
	valor_mes = flt(valor_mes)

	# ainda perde mês a mês? só se o corte dos 5 anos for o que está limitando
	# (se a janela já começa na admissão, não tem mais o que cair)
	ainda_sangra = meses_hoje > 0 and (not data_admissao or corte_hoje > data_admissao)

	if dias < 0:
		nivel = "vencido"
	elif dias <= dias_critico:
		nivel = "critico"
	elif dias <= dias_atencao:
		nivel = "atencao"
	else:
		nivel = "no_prazo"

	return {
		"nivel": nivel,
		"rotulo": NIVEIS[nivel]["rotulo"],
		"ordem": NIVEIS[nivel]["ordem"],
		"limite": str(limite),
		"dias_restantes": dias,
		"meses_no_pedido": meses_hoje,
		"meses_perdidos": meses_perdidos,
		"custo_espera": round(meses_perdidos * valor_mes, 2),
		"perde_por_mes": round(valor_mes, 2) if ainda_sangra else 0.0,
		"janela_inicio": str(ini_hoje),
		"explicacao": _explicar(nivel, dias, meses_hoje, meses_perdidos, anos, retro, ainda_sangra),
	}


def _explicar(nivel, dias, meses_hoje, meses_perdidos, anos, retro, ainda_sangra) -> str:
	if nivel == "vencido":
		return _(
			"O prazo de {0} anos para entrar com a ação venceu há {1} dia(s). "
			"Confira se houve alguma causa de interrupção antes de descartar o atendimento."
		).format(anos, abs(dias))
	partes = [
		_("Faltam {0} dia(s) para fechar o prazo de {1} anos contado da saída.").format(dias, anos)
	]
	if meses_hoje:
		partes.append(
			_("Entrando com a ação hoje, o pedido alcança {0} mês(es) de contrato — a regra dos {1} anos "
			  "para trás conta do dia do ajuizamento, não da saída.").format(meses_hoje, retro)
		)
	else:
		partes.append(
			_("A janela de {0} anos para trás já passou por cima de todo o período trabalhado: "
			  "pelo recorte de tempo não resta parcela a pedir.").format(retro)
		)
	if meses_perdidos:
		partes.append(_("Desde a saída, {0} mês(es) já saíram do alcance do pedido.").format(meses_perdidos))
	if ainda_sangra:
		partes.append(_("A cada mês de espera, mais um mês cai fora."))
	return " ".join(partes)


# ------------------------------------------------------------------ leitura

def _rotulo_lead(l) -> str:
	return (l.get("lead_name") or f"{l.get('first_name') or ''} {l.get('last_name') or ''}".strip()
			or l.get("organization") or l.get("name"))


@frappe.whitelist()
def status() -> dict:
	return {
		"ativo": _modulo_ativo(),
		"juridico": _juridico(),
		"aviso_interno": AVISO_INTERNO,
	}


@frappe.whitelist()
def listar(busca: str = "", incluir_vencidos=1, incluir_sem_data=0, limite=400) -> dict:
	"""Fila de atendimentos ordenada por urgência do prazo."""
	_managers_only()
	_assert_ativo()
	cfg = _cfg()
	filtros = {"converted": 0}
	campos = ["name", "lead_name", "first_name", "last_name", "organization", "mobile_no", "email",
			  "status", "lead_owner", "servico", "data_saida", "data_admissao", "valor_mes_estimado",
			  "prescricao_avisado_em", "modified"]
	or_filtros = None
	if (busca or "").strip():
		termo = f"%{busca.strip()}%"
		or_filtros = [["lead_name", "like", termo], ["first_name", "like", termo],
					  ["last_name", "like", termo], ["organization", "like", termo],
					  ["mobile_no", "like", termo]]
	leads = frappe.get_list("CRM Lead", filters=filtros, or_filters=or_filtros, fields=campos,
							limit_page_length=cint(limite) or 400, order_by="modified desc")

	fila, resumo = [], {k: 0 for k in NIVEIS}
	total_custo = 0.0
	for l in leads:
		calc = calcular(l.get("data_saida"), l.get("data_admissao"), l.get("valor_mes_estimado"), cfg)
		resumo[calc["nivel"]] += 1
		if calc["nivel"] == "sem_data" and not cint(incluir_sem_data):
			continue
		if calc["nivel"] == "vencido" and not cint(incluir_vencidos):
			continue
		fila.append({
			"lead": l.name,
			"nome": _rotulo_lead(l),
			"telefone": l.get("mobile_no") or "",
			"email": l.get("email") or "",
			"status": l.get("status") or "",
			"responsavel": l.get("lead_owner") or "",
			"servico": l.get("servico") or "",
			"data_saida": str(l.get("data_saida") or ""),
			"data_admissao": str(l.get("data_admissao") or ""),
			"valor_mes_estimado": flt(l.get("valor_mes_estimado")),
			"avisado_em": str(l.get("prescricao_avisado_em") or ""),
			**calc,
		})
		total_custo += calc["custo_espera"]

	fila.sort(key=lambda x: (x["ordem"], x["dias_restantes"] if x["dias_restantes"] is not None else 99999))
	return {
		"fila": fila,
		"resumo": resumo,
		"custo_total": round(total_custo, 2),
		"aviso_interno": AVISO_INTERNO,
		"config": {
			"anos": max(1, cint(cfg.get("prescricao_anos")) or 2),
			"retroativo_anos": max(1, cint(cfg.get("prescricao_retroativo_anos")) or 5),
			"dias_critico": max(1, cint(cfg.get("prescricao_dias_critico")) or 30),
			"dias_atencao": cint(cfg.get("prescricao_dias_atencao")) or 90,
		},
	}


@frappe.whitelist()
def como_funciona() -> dict:
	"""Texto fixo: explicar a regra não gasta crédito de IA."""
	cfg = _cfg()
	anos = max(1, cint(cfg.get("prescricao_anos")) or 2)
	retro = max(1, cint(cfg.get("prescricao_retroativo_anos")) or 5)
	return {
		"aviso_interno": AVISO_INTERNO,
		"blocos": [
			{
				"titulo": _("Dois relógios, não um"),
				"texto": _(
					"O primeiro relógio é o prazo para entrar com a ação: {0} anos contados do dia da saída. "
					"Quando ele zera, não dá mais para ajuizar. O segundo relógio decide o TAMANHO do pedido: "
					"só entram os últimos {1} anos contados do dia em que a ação é protocolada."
				).format(anos, retro),
			},
			{
				"titulo": _("Por que a espera custa dinheiro"),
				"texto": _(
					"O segundo relógio conta do protocolo, não da saída. Então cada mês que o cliente leva para "
					"decidir empurra a janela dos {0} anos para frente e derruba o mês mais antigo do pedido. "
					"O direito de ajuizar continua; o valor que se pode pedir encurta."
				).format(retro),
			},
			{
				"titulo": _("Para que serve essa tela"),
				"texto": _(
					"Para o escritório decidir quem ligar primeiro. Quem está perto de fechar o prazo sobe na fila. "
					"O valor mostrado é referência interna de priorização."
				),
			},
			{
				"titulo": _("O que esta tela NÃO faz"),
				"texto": _(
					"Não controla prazo de processo. Publicação, intimação e prazo de recurso continuam no "
					"software jurídico do escritório. Aqui é o contato que ainda não virou caso."
				),
			},
		],
	}


# ------------------------------------------------------------------ gravação

@frappe.whitelist()
def salvar(lead: str, data_saida: str = "", data_admissao: str = "", valor_mes_estimado=0) -> dict:
	_assert_ativo()
	doc = frappe.get_doc("CRM Lead", lead)
	doc.check_permission("write")
	saida = getdate(data_saida) if (data_saida or "").strip() else None
	admissao = getdate(data_admissao) if (data_admissao or "").strip() else None
	if saida and saida > getdate(nowdate()):
		frappe.throw(_("A data da saída não pode estar no futuro."))
	if admissao and saida and admissao > saida:
		frappe.throw(_("A admissão não pode ser depois da saída."))
	valor = flt(valor_mes_estimado)
	if valor < 0:
		frappe.throw(_("O valor estimado por mês não pode ser negativo."))
	frappe.db.set_value("CRM Lead", lead, {
		"data_saida": saida, "data_admissao": admissao, "valor_mes_estimado": valor or None,
	})
	return {"ok": True, **calcular(saida, admissao, valor)}


# ------------------------------------------------------------------ job diário

def alertar():
	"""Job diário: quem entrou na zona crítica vira tarefa para o responsável.
	Não manda nada para o cliente — é aviso interno."""
	from crm.provision import PERFIS_JURIDICOS, get_profile

	if get_profile() not in PERFIS_JURIDICOS:
		return
	cfg = _cfg()
	if not cint(cfg.get("prescricao_ativo", 1)):
		return
	hoje = getdate(nowdate())
	avisados = 0
	for l in frappe.get_all("CRM Lead", filters={"converted": 0, "data_saida": ["is", "set"]},
							fields=["name", "lead_name", "first_name", "last_name", "lead_owner",
									"data_saida", "data_admissao", "valor_mes_estimado",
									"prescricao_avisado_em"], limit=20000):
		calc = calcular(l.get("data_saida"), l.get("data_admissao"), l.get("valor_mes_estimado"), cfg, hoje)
		if calc["nivel"] != "critico":
			continue
		avisado = getdate(l.prescricao_avisado_em) if l.get("prescricao_avisado_em") else None
		if avisado and (hoje - avisado).days < 7:
			continue
		nome = _rotulo_lead(l)
		try:
			frappe.get_doc({
				"doctype": "CRM Task",
				"title": _("Prazo apertado: {0} — faltam {1} dia(s)").format(nome, calc["dias_restantes"]),
				"description": calc["explicacao"] + "\n\n" + AVISO_INTERNO,
				"status": "Todo",
				"priority": "High",
				"assigned_to": l.get("lead_owner"),
				"due_date": nowdate(),
				"reference_doctype": "CRM Lead",
				"reference_docname": l.name,
			}).insert(ignore_permissions=True)
			frappe.db.set_value("CRM Lead", l.name, "prescricao_avisado_em", hoje, update_modified=False)
			avisados += 1
		except Exception:
			frappe.log_error("Radar de prescrição: falha ao criar a tarefa de aviso", frappe.get_traceback())
	if avisados:
		frappe.db.commit()
