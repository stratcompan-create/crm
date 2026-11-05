# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Painel de anúncios (Google e Meta) com IA MENTORA. A diferença em relação a
# qualquer gerador de campanha é que aqui a IA tem que ENSINAR: cada escolha que
# ela faz vem com o porquê em linguagem simples, e todo termo técnico (CPC, CTR,
# CPM, conversão) vai com tradução. Quem não entende de tráfego tem que sair da
# tela sabendo mais do que entrou.
#
# Regras que não se negociam:
#  - campanha NUNCA nasce publicada: nasce Rascunho e, quando vai pra plataforma,
#    vai PAUSADA. Quem liga é a pessoa, na plataforma, de olho no orçamento.
#  - aprovação humana obrigatória antes de qualquer publicação.
#  - revisão OAB é DETERMINÍSTICA (lista de termos), não depende da IA acertar:
#    no perfil de escritório, texto com promessa de resultado não passa.
#  - sem crédito de IA, nada trava: a pessoa monta a campanha à mão e exporta.
#
# Publicação direta nas plataformas depende de credencial de terceiro (developer
# token do Google Ads com acesso Basic e ads_management aprovado na Meta). Até
# lá, o caminho é exportar: CSV pro Google Ads Editor e roteiro pro Gerenciador
# da Meta. A camada de publicação já está escrita e fica desligada.

import csv
import io
import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

DOCTYPE = "CRM Anuncio Campanha"
DOCTYPE_SETTINGS = "CRM Anuncio Settings"
MANAGER_ROLES = ("System Manager", "Sales Manager")

MAX_TITULOS = 15
MAX_DESCRICOES = 4
LIMITE_TITULO = 30  # caracteres, limite do Google para título de RSA
LIMITE_DESCRICAO = 90  # idem, para descrição


# Termos que viram promessa de resultado, captação indevida ou mercantilização da
# profissão. O Provimento 205/2021 da OAB veda anúncio com promessa de resultado,
# oferta de serviço a pessoa indeterminada e uso de termos de mercantilização.
# A checagem é por substring, em texto sem acento e minúsculo.
TERMOS_PROIBIDOS = {
	"garantido": "promete resultado",
	"garantia de": "promete resultado",
	"garanto": "promete resultado",
	"100%": "promete resultado",
	"certeza de": "promete resultado",
	"sem risco": "promete resultado",
	"ganhe": "promete resultado",
	"voce vai receber": "promete resultado",
	"receba seu dinheiro": "promete resultado",
	"dinheiro na conta": "promete resultado",
	"vitoria": "promete resultado",
	"causa ganha": "promete resultado",
	"indenizacao garantida": "promete resultado",
	"aprovacao garantida": "promete resultado",
	"melhor advogado": "compara e se autoproclama",
	"maior escritorio": "compara e se autoproclama",
	"numero 1": "compara e se autoproclama",
	"especialista em": "titulo de especialista exige registro na OAB",
	"barato": "mercantiliza a profissao",
	"promocao": "mercantiliza a profissao",
	"desconto": "mercantiliza a profissao",
	"gratis": "mercantiliza a profissao",
	"preco baixo": "mercantiliza a profissao",
	"consulta gratuita": "mercantiliza a profissao",
	"rapido e facil": "banaliza o servico",
	"facil e rapido": "banaliza o servico",
	"em 24 horas": "promete prazo de resultado",
	"em poucos dias": "promete prazo de resultado",
}

# Glossário da mentoria. Fica no código, não na IA: explicar o que é CPC não pode
# custar crédito nem depender de a IA estar configurada.
GLOSSARIO = {
	"CPC": "Custo por clique. Quanto você paga cada vez que alguém clica no anúncio. Se o CPC é R$ 2 e 50 pessoas clicam, você gastou R$ 100.",
	"CPM": "Custo por mil exibições. Quanto você paga para o anúncio aparecer mil vezes na tela das pessoas, mesmo que ninguém clique.",
	"CTR": "Taxa de cliques. De cada 100 pessoas que viram o anúncio, quantas clicaram. CTR de 5% significa 5 em cada 100. CTR baixo quase sempre quer dizer que o texto não combina com o que a pessoa procurou.",
	"Conversão": "A ação que você quer que aconteça depois do clique: preencher o formulário, chamar no WhatsApp, ligar. Clique sem conversão é dinheiro gasto sem contato gerado.",
	"Impressão": "Uma exibição do anúncio na tela de alguém. Impressão não é visita: é só o anúncio ter aparecido.",
	"Lance": "O máximo que você aceita pagar por um clique. Lance baixo faz o anúncio aparecer menos; lance alto gasta o orçamento mais rápido.",
	"Orçamento diário": "O limite que você aceita gastar por dia naquela campanha. O Google e a Meta podem gastar um pouco mais num dia e compensar no outro, mas respeitam a média do mês.",
	"Palavra-chave": "O que a pessoa digita no Google para o anúncio aparecer. É a diferença entre o Google e a Meta: no Google você responde a quem já está procurando.",
	"Palavra-chave negativa": "Palavra que IMPEDE o anúncio de aparecer. Serve para não gastar com quem nunca vai contratar: quem procura 'curso', 'concurso', 'vaga de emprego', 'grátis', 'modelo de petição'.",
	"Correspondência exata": "O anúncio só aparece para quem digitou exatamente aquela expressão. Gasta menos e traz contato mais certo, mas aparece menos vezes.",
	"Correspondência ampla": "O anúncio aparece para variações e temas parecidos. Aparece muito mais, gasta mais rápido e traz gente fora do alvo.",
	"Público frio": "Gente que nunca ouviu falar de você. Precisa de anúncio que explique quem você é.",
	"Remarketing": "Anunciar de novo para quem já visitou seu site. Costuma custar menos e converter mais, porque a pessoa já te conhece.",
	"RSA": "Anúncio de pesquisa responsivo. Você escreve vários títulos e descrições e o Google testa as combinações sozinho, deixando no ar a que funciona melhor.",
	"ROAS": "Retorno sobre o gasto com anúncio. Quanto de receita cada real investido trouxe. ROAS 3 significa R$ 3 de receita por R$ 1 de anúncio.",
}

SISTEMA = """Você é um gestor de tráfego sênior que está ENSINANDO alguém que não entende
nada de anúncios. Você monta a campanha e explica cada escolha como explicaria a um amigo
inteligente que nunca abriu um gerenciador de anúncios na vida.

Negócio: {marca}
Plataforma: {plataforma}
Objetivo: {objetivo}
Orçamento diário informado: {orcamento}
{bloco_juridico}

Regras da estrutura:
- Google: monte grupos de anúncios por INTENÇÃO de busca (não por serviço solto). Cada grupo
  com 5 a 15 palavras-chave da mesma intenção, títulos de no máximo {limite_titulo} caracteres
  e descrições de no máximo {limite_descricao} caracteres. Inclua palavras-chave negativas
  para cortar quem procura curso, concurso, vaga, modelo de petição, "grátis" e consulta a
  processo próprio.
- Meta: monte conjuntos por PÚBLICO (quem é a pessoa, onde mora, faixa de idade, interesse),
  com texto principal, título curto e descrição para cada criativo.
- Nunca proponha ligar a campanha: ela vai nascer pausada.

Responda SEMPRE em JSON válido, sem nenhum texto fora do JSON, exatamente neste formato:
{{"nome": "nome curto da campanha",
  "resumo": "2 ou 3 frases dizendo em linguagem simples o que essa campanha faz e para quem",
  "estrutura": {{
    "orcamento_diario_sugerido": 50.0,
    "grupos": [{{"nome": "...",
                "intencao": "o que a pessoa está procurando quando cai aqui",
                "publico": "só para Meta: quem é, idade, onde mora, interesses",
                "palavras_chave": [{{"texto": "...", "correspondencia": "exata|frase|ampla"}}],
                "negativas": ["..."],
                "anuncios": [{{"titulos": ["..."], "descricoes": ["..."], "texto_principal": "só para Meta", "cta": "..."}}]
              }}]
  }},
  "mentoria": [{{"escolha": "a decisão que você tomou, em uma frase",
                "porque": "por que isso é melhor que a alternativa, em linguagem de quem não é da área",
                "termos": ["CPC"]}}],
  "primeiros_passos": ["o que a pessoa deve olhar na primeira semana, em ordem"],
  "avisos": ["riscos ou limites que ela precisa saber antes de ligar a campanha"]}}

Em "mentoria" devolva de 4 a 8 itens: as escolhas que mais influenciam o resultado
(estrutura dos grupos, tipo de correspondência, negativas, orçamento, tipo de público).
Em "termos" liste os termos técnicos que você usou e que precisam de tradução.
Escreva tudo em português do Brasil. Não use nenhuma palavra em inglês fora dos nomes
de métricas consagradas (CPC, CTR, CPM, ROAS)."""

BLOCO_JURIDICO = """
ATENÇÃO - este anúncio é de um escritório de advocacia no Brasil. A publicidade de
advogado é regulada (Provimento 205/2021 da OAB). Portanto:
- NUNCA prometa resultado, valor a receber, prazo de êxito ou chance de ganho.
- NUNCA use "garantido", "ganhe", "receba", "vitória", "melhor", "número 1", "barato",
  "promoção", "desconto", "grátis" ou "consulta gratuita".
- NUNCA se apresente como "especialista em" (o título exige registro na OAB).
- O tom é informativo e sóbrio: explica o direito, não vende promessa.
- O convite é para INFORMAÇÃO ("entenda seus direitos", "tire sua dúvida"), nunca
  captação de clientela com oferta de vantagem."""


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


def _modulo_ativo() -> bool:
	try:
		from crm.api.automacoes import get_config

		return bool(cint(get_config().get("anuncios_ativo", 1)))
	except Exception:
		return True


def _assert_ativo():
	if not _modulo_ativo():
		frappe.throw(_("O painel de anúncios está desligado neste site. Ligue em Configurações → Automações."))


def _juridico() -> bool:
	try:
		from crm.provision import PERFIS_JURIDICOS, get_profile

		return get_profile() in PERFIS_JURIDICOS
	except Exception:
		return False


def _marca() -> str:
	try:
		return frappe.get_single("FCRM Settings").get("brand_name") or "a empresa"
	except Exception:
		return "a empresa"


def _sem_acento(texto: str) -> str:
	import unicodedata

	nfkd = unicodedata.normalize("NFKD", texto or "")
	return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _textos_da_estrutura(estrutura: dict) -> list:
	"""Todo texto que vai aparecer pro público - é isso que a revisão OAB olha."""
	out = []
	for grupo in (estrutura or {}).get("grupos") or []:
		for anuncio in grupo.get("anuncios") or []:
			out.extend(anuncio.get("titulos") or [])
			out.extend(anuncio.get("descricoes") or [])
			if anuncio.get("texto_principal"):
				out.append(anuncio["texto_principal"])
	return [t for t in out if t]


def revisao_oab(estrutura: dict) -> dict:
	"""Checagem determinística, sem IA: procura termo proibido em todo texto que o
	público vai ver. Não depende de a IA ter obedecido o prompt."""
	apontamentos = []
	for texto in _textos_da_estrutura(estrutura):
		limpo = _sem_acento(texto)
		for termo, motivo in TERMOS_PROIBIDOS.items():
			if termo in limpo:
				apontamentos.append({"texto": texto, "termo": termo, "motivo": motivo})
	return {"aprovado": not apontamentos, "apontamentos": apontamentos}


def _validar_limites(estrutura: dict) -> list:
	"""Google recusa título acima de 30 e descrição acima de 90 caracteres. Melhor
	avisar aqui do que a pessoa descobrir no meio da importação."""
	avisos = []
	for grupo in (estrutura or {}).get("grupos") or []:
		for anuncio in grupo.get("anuncios") or []:
			for t in anuncio.get("titulos") or []:
				if len(t) > LIMITE_TITULO:
					avisos.append(_("Título com {0} caracteres (o limite é {1}): {2}").format(len(t), LIMITE_TITULO, t))
			for d in anuncio.get("descricoes") or []:
				if len(d) > LIMITE_DESCRICAO:
					avisos.append(_("Descrição com {0} caracteres (o limite é {1}): {2}").format(len(d), LIMITE_DESCRICAO, d))
	return avisos


def _parse_json_ia(texto: str) -> dict:
	texto = (texto or "").strip()
	if texto.startswith("```"):
		texto = texto.strip("`")
		primeira, _sep, resto = texto.partition("\n")
		texto = resto if primeira.strip().lower() in ("json", "") else texto
	try:
		dados = json.loads(texto)
	except Exception:
		frappe.throw(_("A IA respondeu em um formato que eu não consegui ler. Tente de novo."))
	if not isinstance(dados, dict):
		frappe.throw(_("A IA respondeu em um formato que eu não consegui ler. Tente de novo."))
	return dados


@frappe.whitelist()
def glossario() -> dict:
	"""Tradução dos termos técnicos. De propósito sem IA: é conteúdo fixo, não pode
	custar crédito nem depender da chave estar configurada."""
	return {"termos": GLOSSARIO}


@frappe.whitelist()
def status() -> dict:
	_managers_only()
	from crm.api.ficha import _api_key

	cfg = frappe.get_single(DOCTYPE_SETTINGS)
	google_ok = bool(cfg.get("google_customer_id") and cfg.get_password("google_developer_token", raise_exception=False))
	meta_ok = bool(cfg.get("meta_ad_account_id") and cfg.get_password("meta_access_token", raise_exception=False))
	return {
		"ativo": _modulo_ativo(),
		"juridico": _juridico(),
		"ia_configurada": bool(_api_key()),
		"publicacao_direta": bool(cint(cfg.get("publicacao_direta"))),
		"google_conectado": google_ok,
		"meta_conectado": meta_ok,
		"teto_orcamento_centavos": cint(cfg.get("teto_orcamento_diario_centavos")) or 20000,
	}


@frappe.whitelist()
def listar(plataforma: str = None, limite: int = 50) -> list:
	_managers_only()
	_assert_ativo()
	filtros = {}
	if plataforma:
		filtros["plataforma"] = plataforma
	return frappe.get_all(
		DOCTYPE,
		filters=filtros,
		fields=["name", "titulo", "plataforma", "objetivo", "status", "orcamento_diario_centavos", "oab_aprovado", "modified"],
		order_by="modified desc",
		limit=cint(limite) or 50,
	)


@frappe.whitelist()
def obter(name: str) -> dict:
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	estrutura = json.loads(doc.estrutura or "{}")
	mentoria = json.loads(doc.mentoria or "[]")
	revisao = json.loads(doc.revisao_oab or "{}")
	usados = sorted({t for item in mentoria for t in (item.get("termos") or []) if t in GLOSSARIO})
	return {
		"name": doc.name,
		"titulo": doc.titulo,
		"plataforma": doc.plataforma,
		"objetivo": doc.objetivo,
		"status": doc.status,
		"orcamento_diario_centavos": cint(doc.orcamento_diario_centavos),
		"briefing": doc.briefing,
		"origem": doc.origem,
		"origem_referencia": doc.origem_referencia,
		"area": doc.area,
		"resumo_ia": doc.resumo_ia,
		"estrutura": estrutura,
		"mentoria": mentoria,
		"revisao_oab": revisao,
		"oab_aprovado": bool(cint(doc.oab_aprovado)),
		"aprovado_por": doc.aprovado_por,
		"aprovado_em": doc.aprovado_em,
		"publicado_em": doc.publicado_em,
		"erro_publicacao": doc.erro_publicacao,
		"avisos_limite": _validar_limites(estrutura),
		"glossario_usado": {t: GLOSSARIO[t] for t in usados},
	}


@frappe.whitelist()
def criar_manual(titulo: str, plataforma: str = "Google", objetivo: str = "Contatos", orcamento_diario_centavos: int = 0) -> dict:
	"""Campanha em branco, sem IA. É o caminho de quem está sem crédito: a regra é
	que a falta de saldo nunca trava a função, só tira a parte de IA."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc({
		"doctype": DOCTYPE,
		"titulo": (titulo or "").strip() or _("Campanha sem nome"),
		"plataforma": plataforma,
		"objetivo": objetivo,
		"orcamento_diario_centavos": cint(orcamento_diario_centavos),
		"status": "Rascunho",
		"estrutura": json.dumps({"grupos": []}, ensure_ascii=False),
		"mentoria": "[]",
		"revisao_oab": json.dumps({"aprovado": True, "apontamentos": []}, ensure_ascii=False),
		"oab_aprovado": 1,
	})
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist()
def gerar(
	briefing: str,
	plataforma: str = "Google",
	objetivo: str = "Contatos",
	orcamento_diario_centavos: int = 0,
	origem: str = "Briefing",
	origem_referencia: str = None,
	area: str = None,
) -> dict:
	"""✦ Usa IA. Monta a campanha a partir do briefing (ou da legenda de um Reel já
	postado) e devolve a mentoria junto. Sempre em Rascunho."""
	_managers_only()
	_assert_ativo()

	briefing = (briefing or "").strip()
	if not briefing:
		frappe.throw(_("Escreva o briefing: o que você vende, para quem e em que cidade."))

	from crm.api.conteudo import _call_claude
	from crm.api.ficha import _api_key

	api_key = _api_key()
	if not api_key:
		frappe.throw(_("Configure a chave da API do Claude em Configurações → Automações para a IA montar a campanha. Você também pode criar a campanha à mão."))

	teto = cint(frappe.get_single(DOCTYPE_SETTINGS).get("teto_orcamento_diario_centavos")) or 20000
	if cint(orcamento_diario_centavos) > teto:
		frappe.throw(_("O orçamento diário informado passa do teto configurado ({0}).").format(_reais(teto)))

	system = SISTEMA.format(
		marca=_marca(),
		plataforma=plataforma,
		objetivo=objetivo,
		orcamento=_reais(cint(orcamento_diario_centavos)) if cint(orcamento_diario_centavos) else _("não informado"),
		bloco_juridico=BLOCO_JURIDICO if _juridico() else "",
		limite_titulo=LIMITE_TITULO,
		limite_descricao=LIMITE_DESCRICAO,
	)
	pedido = briefing
	if area:
		pedido += f"\n\nÁrea do direito: {area}"
	if origem == "Publicação do Instagram" and origem_referencia:
		pedido += f"\n\nEssa campanha nasce de uma publicação que já existe no Instagram (referência {origem_referencia}). Aproveite o tema dela."

	texto = _call_claude(api_key, system, [{"role": "user", "content": pedido}])
	dados = _parse_json_ia(texto)

	estrutura = dados.get("estrutura") or {"grupos": []}
	estrutura["primeiros_passos"] = dados.get("primeiros_passos") or []
	estrutura["avisos"] = dados.get("avisos") or []
	revisao = revisao_oab(estrutura) if _juridico() else {"aprovado": True, "apontamentos": []}

	orcamento = cint(orcamento_diario_centavos)
	if not orcamento and estrutura.get("orcamento_diario_sugerido"):
		try:
			orcamento = int(round(float(estrutura["orcamento_diario_sugerido"]) * 100))
		except Exception:
			orcamento = 0

	doc = frappe.get_doc({
		"doctype": DOCTYPE,
		"titulo": (dados.get("nome") or briefing[:60]).strip(),
		"plataforma": plataforma,
		"objetivo": objetivo,
		"orcamento_diario_centavos": min(orcamento, teto),
		"briefing": briefing,
		"origem": origem,
		"origem_referencia": origem_referencia,
		"area": area,
		"status": "Rascunho",
		"resumo_ia": dados.get("resumo"),
		"estrutura": json.dumps(estrutura, ensure_ascii=False),
		"mentoria": json.dumps(dados.get("mentoria") or [], ensure_ascii=False),
		"revisao_oab": json.dumps(revisao, ensure_ascii=False),
		"oab_aprovado": 1 if revisao.get("aprovado") else 0,
	})
	doc.insert()
	return obter(doc.name)


@frappe.whitelist()
def aprovar(name: str) -> dict:
	"""Aprovação humana. Sem isso nada é exportado como pronto nem publicado."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status in ("Publicada (pausada)", "Arquivada"):
		frappe.throw(_("Essa campanha já saiu do rascunho."))

	estrutura = json.loads(doc.estrutura or "{}")
	if not (estrutura.get("grupos") or []):
		frappe.throw(_("A campanha está vazia: não há grupo de anúncio para aprovar."))

	if _juridico():
		revisao = revisao_oab(estrutura)
		doc.db_set("revisao_oab", json.dumps(revisao, ensure_ascii=False))
		doc.db_set("oab_aprovado", 1 if revisao.get("aprovado") else 0)
		if not revisao.get("aprovado"):
			frappe.throw(
				_("A revisão OAB apontou {0} texto(s) com problema. Corrija antes de aprovar.").format(
					len(revisao.get("apontamentos") or [])
				)
			)

	doc.db_set("status", "Aprovada")
	doc.db_set("aprovado_por", frappe.session.user)
	doc.db_set("aprovado_em", now_datetime())
	return {"ok": True, "status": "Aprovada"}


@frappe.whitelist()
def arquivar(name: str) -> dict:
	_managers_only()
	_assert_ativo()
	frappe.db.set_value(DOCTYPE, name, "status", "Arquivada")
	return {"ok": True}


@frappe.whitelist()
def atualizar_estrutura(name: str, estrutura: str) -> dict:
	"""Edição manual do que a IA montou (ou da campanha feita à mão). Reexecuta a
	revisão OAB a cada gravação."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status == "Publicada (pausada)":
		frappe.throw(_("Essa campanha já foi publicada. Crie uma nova para mudar a estrutura."))
	try:
		dados = json.loads(estrutura) if isinstance(estrutura, str) else estrutura
	except Exception:
		frappe.throw(_("A estrutura enviada não é um JSON válido."))

	revisao = revisao_oab(dados) if _juridico() else {"aprovado": True, "apontamentos": []}
	doc.db_set("estrutura", json.dumps(dados, ensure_ascii=False))
	doc.db_set("revisao_oab", json.dumps(revisao, ensure_ascii=False))
	doc.db_set("oab_aprovado", 1 if revisao.get("aprovado") else 0)
	if doc.status == "Aprovada":
		doc.db_set("status", "Rascunho")  # mexeu, aprova de novo
	return obter(name)


def _reais(centavos: int) -> str:
	return f"R$ {cint(centavos) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


COLUNAS_GOOGLE = [
	"Campaign", "Campaign Type", "Campaign Daily Budget", "Campaign Status",
	"Ad Group", "Ad Group Status", "Max CPC",
	"Keyword", "Criterion Type",
	"Ad Status", "Final URL", "Path 1", "Path 2",
]
COLUNAS_GOOGLE += [f"Headline {i}" for i in range(1, MAX_TITULOS + 1)]
COLUNAS_GOOGLE += [f"Description {i}" for i in range(1, MAX_DESCRICOES + 1)]

CORRESPONDENCIA = {
	"exata": "Exact",
	"frase": "Phrase",
	"ampla": "Broad",
}


@frappe.whitelist()
def exportar_google(name: str) -> dict:
	"""CSV no formato do Google Ads Editor. Tudo sai como Paused de propósito."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.plataforma != "Google":
		frappe.throw(_("Essa campanha é da Meta. Use a exportação da Meta."))
	estrutura = json.loads(doc.estrutura or "{}")
	url_final = (frappe.get_single("FCRM Settings").get("website_url") or "").strip()

	buffer = io.StringIO()
	writer = csv.DictWriter(buffer, fieldnames=COLUNAS_GOOGLE, extrasaction="ignore")
	writer.writeheader()

	orcamento = cint(doc.orcamento_diario_centavos) / 100
	for grupo in estrutura.get("grupos") or []:
		base = {
			"Campaign": doc.titulo,
			"Campaign Type": "Search",
			"Campaign Daily Budget": f"{orcamento:.2f}" if orcamento else "",
			"Campaign Status": "Paused",
			"Ad Group": grupo.get("nome") or "Grupo 1",
			"Ad Group Status": "Paused",
		}
		for palavra in grupo.get("palavras_chave") or []:
			linha = dict(base)
			linha["Keyword"] = palavra.get("texto") if isinstance(palavra, dict) else palavra
			tipo = (palavra.get("correspondencia") if isinstance(palavra, dict) else "") or "frase"
			linha["Criterion Type"] = CORRESPONDENCIA.get(str(tipo).lower(), "Phrase")
			writer.writerow(linha)
		for negativa in grupo.get("negativas") or []:
			linha = dict(base)
			linha["Keyword"] = negativa
			linha["Criterion Type"] = "Negative Broad"
			writer.writerow(linha)
		for anuncio in grupo.get("anuncios") or []:
			linha = dict(base)
			linha["Ad Status"] = "Paused"
			linha["Final URL"] = url_final
			for i, titulo in enumerate((anuncio.get("titulos") or [])[:MAX_TITULOS], start=1):
				linha[f"Headline {i}"] = titulo
			for i, descricao in enumerate((anuncio.get("descricoes") or [])[:MAX_DESCRICOES], start=1):
				linha[f"Description {i}"] = descricao
			writer.writerow(linha)

	return {
		"nome_arquivo": f"{doc.name}-google-ads.csv",
		"csv": buffer.getvalue(),
		"instrucao": _(
			"Abra o Google Ads Editor, vá em Conta → Importar → Da área de transferência ou arquivo, "
			"escolha esse arquivo e confira a prévia antes de publicar. Tudo entra PAUSADO: nada começa "
			"a gastar sem você ligar."
		),
	}


@frappe.whitelist()
def exportar_meta(name: str) -> dict:
	"""A Meta não tem importação por planilha como o Google Ads Editor, então aqui a
	exportação é um roteiro para montar no Gerenciador de Anúncios, mais o JSON para
	quando a publicação direta estiver liberada."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.plataforma != "Meta":
		frappe.throw(_("Essa campanha é do Google. Use a exportação do Google."))
	estrutura = json.loads(doc.estrutura or "{}")

	linhas = [
		f"CAMPANHA: {doc.titulo}",
		f"Objetivo: {doc.objetivo}",
		f"Orçamento diário: {_reais(doc.orcamento_diario_centavos)}",
		"Status ao criar: PAUSADA (ligue só depois de revisar)",
		"",
	]
	for i, grupo in enumerate(estrutura.get("grupos") or [], start=1):
		linhas.append(f"--- CONJUNTO {i}: {grupo.get('nome') or ''} ---")
		if grupo.get("publico"):
			linhas.append(f"Público: {grupo['publico']}")
		if grupo.get("intencao"):
			linhas.append(f"Momento da pessoa: {grupo['intencao']}")
		for j, anuncio in enumerate(grupo.get("anuncios") or [], start=1):
			linhas.append(f"  Criativo {j}:")
			if anuncio.get("texto_principal"):
				linhas.append(f"    Texto principal: {anuncio['texto_principal']}")
			for titulo in anuncio.get("titulos") or []:
				linhas.append(f"    Título: {titulo}")
			for descricao in anuncio.get("descricoes") or []:
				linhas.append(f"    Descrição: {descricao}")
			if anuncio.get("cta"):
				linhas.append(f"    Botão: {anuncio['cta']}")
		linhas.append("")

	return {
		"nome_arquivo": f"{doc.name}-meta.txt",
		"texto": "\n".join(linhas),
		"json": estrutura,
		"instrucao": _(
			"No Gerenciador de Anúncios da Meta, crie a campanha com esse objetivo e cole cada bloco no "
			"conjunto correspondente. Deixe a campanha pausada até revisar tudo."
		),
	}


@frappe.whitelist()
def publicar(name: str) -> dict:
	"""Publicação direta nas plataformas, SEMPRE pausada. Depende de credencial
	aprovada (developer token Basic no Google Ads, ads_management na Meta). Enquanto
	não houver, explica o que falta em vez de falhar com erro técnico."""
	_managers_only()
	_assert_ativo()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status != "Aprovada":
		frappe.throw(_("Aprove a campanha antes de publicar."))

	cfg = frappe.get_single(DOCTYPE_SETTINGS)
	if not cint(cfg.get("publicacao_direta")):
		frappe.throw(_(
			"A publicação direta está desligada neste site. Use a exportação: ela gera o arquivo "
			"pronto para o Google Ads Editor ou o roteiro para o Gerenciador da Meta."
		))

	if doc.plataforma == "Google":
		falta = not (cfg.get("google_customer_id") and cfg.get_password("google_developer_token", raise_exception=False))
		pendencia = _("o developer token do Google Ads com acesso Basic")
	else:
		falta = not (cfg.get("meta_ad_account_id") and cfg.get_password("meta_access_token", raise_exception=False))
		pendencia = _("a permissão ads_management aprovada no App Review da Meta")

	if falta:
		frappe.throw(_("Falta {0}. Enquanto isso não sair, use a exportação.").format(pendencia))

	# A chamada real a cada plataforma entra aqui quando a credencial existir. Até
	# então não há caminho silencioso: ou publica de verdade, ou avisa o que falta.
	frappe.throw(_("A conexão com a plataforma ainda não foi concluída neste servidor. Use a exportação."))
