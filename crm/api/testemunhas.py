# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Banco de testemunhas — a busca que hoje mora na cabeça de alguém.
#
# Nesse tipo de caso (bancário, trabalhista de volume) a testemunha vale tanto quanto
# documento. O escritório precisa responder "quem trabalhou na agência Centro entre 2019 e
# 2022?" na hora, e não depois de abrir quarenta pastas.
#
# A base é o cadastro de partes do caso (CRM Parte, tipo "Testemunha"), que já existe. Aqui
# entra o que faltava: onde a pessoa trabalhou, em que período, como falar com ela, e o aviso
# quando a MESMA testemunha já apareceu em muitos casos — porque é exatamente isso que a
# outra parte usa para tentar desqualificar o depoimento (testemunha "profissional").
#
# A busca cruza casos, então ela é restrita a gestor: o CRM tem permissão por caso
# (quem atende um caso não enxerga os outros), e uma busca que varre tudo furaria essa regra
# se ficasse aberta para qualquer usuário.

import frappe
from frappe import _
from frappe.utils import cint, getdate

from crm.api.processo import _digitos, _norm

TIPO = "Testemunha"


def _managers_only():
	frappe.only_for(("System Manager", "Sales Manager"))


def _juridico() -> bool:
	from crm.provision import PERFIS_JURIDICOS, get_profile

	return get_profile() in PERFIS_JURIDICOS


def _cfg():
	from crm.api.automacoes import get_config

	return get_config()


def _modulo_ativo() -> bool:
	return _juridico() and bool(cint(_cfg().get("testemunhas_ativo", 1)))


def _assert_ativo():
	if not _juridico():
		frappe.throw(_("O banco de testemunhas existe só no perfil de escritório de advocacia."))
	if not cint(_cfg().get("testemunhas_ativo", 1)):
		frappe.throw(_("O banco de testemunhas está desligado em Configurações → Automações."))


def _limite_alerta() -> int:
	return max(2, cint(_cfg().get("testemunhas_limite_alerta")) or 3)


def _agrupar(linhas: list[dict]) -> tuple[dict, set]:
	"""Diz quais cadastros são a MESMA pessoa, em casos diferentes.

	CPF é a identidade boa, mas a equipe nem sempre preenche. Então: quem tem CPF agrupa
	por CPF; quem não tem entra no grupo do CPF cujo nome bate — desde que o nome bata com
	UM único CPF. Se o mesmo nome aparece com dois CPFs, são provavelmente duas pessoas
	homônimas: não junta e devolve o nome como ambíguo, para a tela avisar.

	Devolve (chave_por_cadastro, nomes_ambiguos)."""
	nome_para_docs: dict[str, set] = {}
	for l in linhas:
		doc = _digitos(l.get("documento"))
		if doc:
			nome_para_docs.setdefault(_norm(l.get("nome")), set()).add(doc)
	ambiguos = {n for n, docs in nome_para_docs.items() if len(docs) > 1}

	chaves = {}
	for l in linhas:
		doc = _digitos(l.get("documento"))
		if doc:
			chaves[l["name"]] = f"doc:{doc}"
			continue
		nome = _norm(l.get("nome"))
		docs = nome_para_docs.get(nome) or set()
		chaves[l["name"]] = f"doc:{next(iter(docs))}" if len(docs) == 1 else f"nome:{nome}"
	return chaves, ambiguos


def _rotulo(deal: str) -> str:
	from crm.api.processo import _rotulo_caso

	try:
		return _rotulo_caso(deal)
	except Exception:
		return deal


def _sobrepoe(ini, fim, de, ate) -> bool:
	"""O período da testemunha encosta na janela pesquisada?
	Sem data cadastrada, a testemunha ENTRA no resultado (é um 'não sei', não um 'não')."""
	if not de and not ate:
		return True
	if not ini and not fim:
		return True
	ini = getdate(ini) if ini else None
	fim = getdate(fim) if fim else None
	de = getdate(de) if de else None
	ate = getdate(ate) if ate else None
	if ate and ini and ini > ate:
		return False
	if de and fim and fim < de:
		return False
	return True


# ------------------------------------------------------------------ leitura

@frappe.whitelist()
def status() -> dict:
	return {"ativo": _modulo_ativo(), "juridico": _juridico(), "limite_alerta": _limite_alerta()}


def _todas() -> list[dict]:
	linhas = frappe.get_all(
		"CRM Parte", filters={"tipo": TIPO},
		fields=["name", "deal", "nome", "documento", "telefone", "email", "local_trabalho",
				"periodo_inicio", "periodo_fim", "disponivel", "observacoes", "creation"],
		order_by="nome asc", limit_page_length=20000,
	)
	# quantos casos distintos cada pessoa aparece
	chaves, ambiguos = _agrupar(linhas)
	casos: dict[str, set] = {}
	for l in linhas:
		casos.setdefault(chaves[l["name"]], set()).add(l.deal)
	for l in linhas:
		l["chave"] = chaves[l["name"]]
		l["casos"] = len(casos.get(l["chave"], ()))
		l["nome_ambiguo"] = _norm(l.get("nome")) in ambiguos
	return linhas


@frappe.whitelist()
def buscar(local: str = "", de: str = "", ate: str = "", termo: str = "", so_disponiveis=0) -> dict:
	"""A pergunta da reunião: quem trabalhou em tal lugar em tal período."""
	_managers_only()
	_assert_ativo()
	alvo_local = _norm(local)
	alvo_termo = _norm(termo)
	limite = _limite_alerta()

	achados = []
	for l in _todas():
		if alvo_local and alvo_local not in _norm(l.get("local_trabalho")):
			continue
		if alvo_termo and alvo_termo not in _norm(l.get("nome")) and alvo_termo not in _norm(l.get("observacoes")):
			continue
		if not _sobrepoe(l.get("periodo_inicio"), l.get("periodo_fim"), de, ate):
			continue
		if cint(so_disponiveis) and not cint(l.get("disponivel", 1)):
			continue
		achados.append({
			"parte": l.name,
			"deal": l.deal,
			"caso": _rotulo(l.deal),
			"nome": l.nome,
			"documento": l.get("documento") or "",
			"telefone": l.get("telefone") or "",
			"email": l.get("email") or "",
			"local_trabalho": l.get("local_trabalho") or "",
			"periodo_inicio": str(l.get("periodo_inicio") or ""),
			"periodo_fim": str(l.get("periodo_fim") or ""),
			"disponivel": cint(l.get("disponivel", 1)),
			"observacoes": l.get("observacoes") or "",
			"casos": l["casos"],
			"muito_usada": l["casos"] >= limite,
			"sem_periodo": not (l.get("periodo_inicio") or l.get("periodo_fim")),
			"nome_ambiguo": l.get("nome_ambiguo", False),
		})
	achados.sort(key=lambda x: (-x["casos"], x["nome"]))
	return {
		"testemunhas": achados,
		"total": len(achados),
		"limite_alerta": limite,
		"aviso_repetidas": _(
			"Testemunha que aparece em muitos casos pode ter o depoimento questionado pela outra parte. "
			"Quem decide se vale usar é o advogado — o CRM só mostra o número antes de alguém ser surpreendido."
		),
	}


@frappe.whitelist()
def repetidas() -> dict:
	"""Quem já apareceu em casos demais — a lista que o escritório precisa olhar antes do banco olhar."""
	_managers_only()
	_assert_ativo()
	limite = _limite_alerta()
	grupos: dict[str, dict] = {}
	for l in _todas():
		g = grupos.setdefault(l["chave"], {"nome": "", "documento": "", "locais": set(),
											"casos": [], "telefone": "", "email": "",
											"nome_ambiguo": False})
		# o grupo junta cadastros que podem estar incompletos de formas diferentes:
		# pega cada dado do primeiro cadastro que o tiver, nao do primeiro cadastro
		if l.get("documento") and not g["documento"]:
			g["documento"] = l["documento"]
		# prefere o nome do cadastro que tem documento (tende a ser o mais bem preenchido)
		if not g["nome"] or (l.get("documento") and l.nome != g["nome"] and l.nome.istitle()):
			g["nome"] = l.nome
		if l.get("local_trabalho"):
			g["locais"].add(l["local_trabalho"])
		if l.get("telefone") and not g["telefone"]:
			g["telefone"] = l["telefone"]
		if l.get("email") and not g["email"]:
			g["email"] = l["email"]
		if l.get("nome_ambiguo"):
			g["nome_ambiguo"] = True
		g["casos"].append({"deal": l.deal, "caso": _rotulo(l.deal), "parte": l.name})
	saida = []
	for g in grupos.values():
		distintos = {c["deal"] for c in g["casos"]}
		if len(distintos) < limite:
			continue
		saida.append({"nome": g["nome"], "documento": g["documento"], "telefone": g["telefone"],
					  "email": g["email"], "locais": sorted(g["locais"]),
					  "casos": g["casos"], "quantidade": len(distintos),
					  "nome_ambiguo": g["nome_ambiguo"]})
	saida.sort(key=lambda x: -x["quantidade"])
	return {"repetidas": saida, "limite_alerta": limite}


@frappe.whitelist()
def locais() -> list[str]:
	"""Os lugares já cadastrados, para o campo de busca sugerir em vez de exigir digitação exata."""
	_managers_only()
	_assert_ativo()
	vistos = {}
	for l in frappe.get_all("CRM Parte", filters={"tipo": TIPO, "local_trabalho": ["is", "set"]},
							pluck="local_trabalho", limit_page_length=20000):
		vistos.setdefault(_norm(l), l)
	return sorted(vistos.values())


@frappe.whitelist()
def do_caso(deal: str) -> dict:
	"""As testemunhas de um caso só — essa qualquer pessoa com acesso ao caso pode ver."""
	_assert_ativo()
	d = frappe.get_doc("CRM Deal", deal)
	d.check_permission("read")
	limite = _limite_alerta()
	todas = _todas()
	saida = []
	for l in todas:
		if l.deal != deal:
			continue
		saida.append({
			"parte": l.name, "nome": l.nome, "documento": l.get("documento") or "",
			"telefone": l.get("telefone") or "", "email": l.get("email") or "",
			"local_trabalho": l.get("local_trabalho") or "",
			"periodo_inicio": str(l.get("periodo_inicio") or ""),
			"periodo_fim": str(l.get("periodo_fim") or ""),
			"disponivel": cint(l.get("disponivel", 1)),
			"observacoes": l.get("observacoes") or "",
			"casos": l["casos"], "muito_usada": l["casos"] >= limite,
		})
	return {"testemunhas": saida, "limite_alerta": limite}


# ------------------------------------------------------------------ gravação

@frappe.whitelist()
def atualizar(parte: str, local_trabalho: str = None, periodo_inicio: str = None, periodo_fim: str = None,
			  telefone: str = None, email: str = None, disponivel: str = None, observacoes: str = None) -> dict:
	"""Completa a ficha da testemunha. Exige escrever no caso dela."""
	_assert_ativo()
	linha = frappe.db.get_value("CRM Parte", parte, ["deal", "tipo"], as_dict=True)
	if not linha:
		frappe.throw(_("Testemunha não encontrada."))
	d = frappe.get_doc("CRM Deal", linha.deal)
	d.check_permission("write")

	ini = getdate(periodo_inicio) if (periodo_inicio or "").strip() else None
	fim = getdate(periodo_fim) if (periodo_fim or "").strip() else None
	if ini and fim and ini > fim:
		frappe.throw(_("O início do período não pode ser depois do fim."))

	campos = {}
	if local_trabalho is not None:
		campos["local_trabalho"] = (local_trabalho or "").strip()[:200] or None
	if periodo_inicio is not None:
		campos["periodo_inicio"] = ini
	if periodo_fim is not None:
		campos["periodo_fim"] = fim
	if telefone is not None:
		campos["telefone"] = (telefone or "").strip()[:30] or None
	if email is not None:
		campos["email"] = (email or "").strip()[:140] or None
	if disponivel is not None:
		campos["disponivel"] = cint(disponivel)
	if observacoes is not None:
		campos["observacoes"] = (observacoes or "").strip()[:500] or None
	if campos:
		frappe.db.set_value("CRM Parte", parte, campos)
	return {"ok": True}
