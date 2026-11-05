"""Teste de fumaca: painel de anuncios (Google e Meta) com IA mentora.

Nao fala com o Claude, nem com o Google Ads, nem com a Meta de verdade.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json
from unittest import mock

import frappe

from crm.api import anuncios


ESTRUTURA_LIMPA = {
	"grupos": [
		{
			"nome": "Duvida sobre verba rescisoria",
			"intencao": "pessoa demitida querendo entender o que tem direito",
			"palavras_chave": [
				{"texto": "verba rescisoria o que tenho direito", "correspondencia": "frase"},
				{"texto": "calculo de rescisao", "correspondencia": "exata"},
			],
			"negativas": ["curso", "concurso", "vaga de emprego", "modelo de peticao"],
			"anuncios": [
				{
					"titulos": ["Entenda sua rescisao", "Tire sua duvida"],
					"descricoes": ["Orientacao sobre o que a lei preve na rescisao do contrato de trabalho."],
					"cta": "Saiba mais",
				}
			],
		}
	]
}

ESTRUTURA_PROIBIDA = {
	"grupos": [
		{
			"nome": "Rescisao",
			"palavras_chave": [{"texto": "rescisao", "correspondencia": "frase"}],
			"negativas": [],
			"anuncios": [
				{
					"titulos": ["Indenizacao garantida"],
					"descricoes": ["Ganhe sua causa com o melhor advogado da cidade."],
				}
			],
		}
	]
}


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	criadas = []
	try:
		# ---------- revisao OAB (deterministica, sem IA) ----------
		limpa = anuncios.revisao_oab(ESTRUTURA_LIMPA)
		ck("revisao OAB aprova texto informativo", limpa["aprovado"], limpa)

		suja = anuncios.revisao_oab(ESTRUTURA_PROIBIDA)
		termos = {a["termo"] for a in suja["apontamentos"]}
		ck("revisao OAB reprova promessa de resultado", not suja["aprovado"])
		ck("revisao OAB pega 'garantida' mesmo com acento no texto", "garantido" in termos or "indenizacao garantida" in termos, termos)
		ck("revisao OAB pega 'ganhe'", "ganhe" in termos, termos)
		ck("revisao OAB pega autoproclamacao 'melhor advogado'", "melhor advogado" in termos, termos)

		# ---------- limites do Google ----------
		longa = {"grupos": [{"anuncios": [{"titulos": ["x" * 31], "descricoes": ["y" * 91]}]}]}
		avisos = anuncios._validar_limites(longa)
		ck("avisa titulo acima de 30 e descricao acima de 90", len(avisos) == 2, avisos)
		ck("nao inventa aviso em campanha dentro do limite", anuncios._validar_limites(ESTRUTURA_LIMPA) == [])

		# ---------- glossario ----------
		g = anuncios.glossario()["termos"]
		ck("glossario explica CPC sem usar IA", "CPC" in g and "clique" in g["CPC"].lower())
		ck("glossario explica palavra-chave negativa", "Palavra-chave negativa" in g)

		# ---------- criar a mao (caminho de quem esta sem credito) ----------
		manual = anuncios.criar_manual("Campanha teste fumaca", "Google", "Contatos", 5000)
		criadas.append(manual["name"])
		doc = anuncios.obter(manual["name"])
		ck("criar_manual nasce em Rascunho", doc["status"] == "Rascunho", doc["status"])
		ck("criar_manual nasce sem grupo", doc["estrutura"].get("grupos") == [])

		# ---------- aprovacao ----------
		try:
			anuncios.aprovar(manual["name"])
			ck("aprovar recusa campanha vazia", False)
		except frappe.ValidationError:
			ck("aprovar recusa campanha vazia", True)

		with mock.patch.object(anuncios, "_juridico", return_value=True):
			anuncios.atualizar_estrutura(manual["name"], json.dumps(ESTRUTURA_PROIBIDA))
			d = anuncios.obter(manual["name"])
			ck("gravar estrutura proibida marca oab_aprovado=0", not d["oab_aprovado"])
			try:
				anuncios.aprovar(manual["name"])
				ck("perfil juridico: aprovar barra texto proibido", False)
			except frappe.ValidationError:
				ck("perfil juridico: aprovar barra texto proibido", True)

			anuncios.atualizar_estrutura(manual["name"], json.dumps(ESTRUTURA_LIMPA))
			d = anuncios.obter(manual["name"])
			ck("gravar estrutura limpa volta oab_aprovado=1", d["oab_aprovado"])
			anuncios.aprovar(manual["name"])
			ck("perfil juridico: aprova texto limpo", anuncios.obter(manual["name"])["status"] == "Aprovada")

		# mexer na estrutura depois de aprovada obriga aprovar de novo
		anuncios.atualizar_estrutura(manual["name"], json.dumps(ESTRUTURA_LIMPA))
		ck("editar campanha aprovada volta pra Rascunho", anuncios.obter(manual["name"])["status"] == "Rascunho")

		# ---------- exportacao Google ----------
		exp = anuncios.exportar_google(manual["name"])
		csv_texto = exp["csv"]
		ck("CSV do Google tem cabecalho do Ads Editor", "Campaign" in csv_texto and "Criterion Type" in csv_texto)
		ck("CSV sai todo pausado", "Paused" in csv_texto and "Enabled" not in csv_texto)
		ck("CSV marca negativa como Negative Broad", "Negative Broad" in csv_texto)
		ck("CSV traduz correspondencia exata", "Exact" in csv_texto)
		ck("CSV leva o titulo do anuncio", "Entenda sua rescisao" in csv_texto)

		try:
			anuncios.exportar_meta(manual["name"])
			ck("exportar_meta recusa campanha do Google", False)
		except frappe.ValidationError:
			ck("exportar_meta recusa campanha do Google", True)

		# ---------- exportacao Meta ----------
		meta = anuncios.criar_manual("Campanha Meta fumaca", "Meta", "Mensagens no WhatsApp", 3000)
		criadas.append(meta["name"])
		anuncios.atualizar_estrutura(meta["name"], json.dumps(ESTRUTURA_LIMPA))
		expm = anuncios.exportar_meta(meta["name"])
		ck("roteiro da Meta diz que nasce pausada", "PAUSADA" in expm["texto"])
		ck("roteiro da Meta lista o conjunto", "CONJUNTO 1" in expm["texto"])

		# ---------- publicacao (sempre barrada sem credencial) ----------
		try:
			anuncios.publicar(meta["name"])
			ck("publicar exige aprovacao antes", False)
		except frappe.ValidationError as e:
			ck("publicar exige aprovacao antes", "Aprove" in str(e), str(e)[:60])

		with mock.patch.object(anuncios, "_juridico", return_value=False):
			anuncios.aprovar(meta["name"])
		try:
			anuncios.publicar(meta["name"])
			ck("publicar barra quando a publicacao direta esta desligada", False)
		except frappe.ValidationError:
			ck("publicar barra quando a publicacao direta esta desligada", True)

		# ---------- geracao com IA (resposta do Claude simulada) ----------
		resposta_ia = json.dumps({
			"nome": "Trabalhista - duvidas de rescisao",
			"resumo": "Campanha para quem acabou de ser demitido e procura entender o que tem direito.",
			"estrutura": {"orcamento_diario_sugerido": 40.0, "grupos": ESTRUTURA_LIMPA["grupos"]},
			"mentoria": [{"escolha": "Correspondencia de frase", "porque": "aparece para quem busca o tema sem gastar com curiosos", "termos": ["CPC", "Correspondência exata"]}],
			"primeiros_passos": ["Olhar o CTR no setimo dia"],
			"avisos": ["Nao ligue sem conferir o orcamento"],
		}, ensure_ascii=False)

		with mock.patch.object(anuncios, "_juridico", return_value=True), \
			mock.patch("crm.api.conteudo._call_claude", return_value=resposta_ia), \
			mock.patch("crm.api.ficha._api_key", return_value="chave-de-teste"):
			gerada = anuncios.gerar("Escritorio trabalhista em Petrolina", "Google", "Contatos", 4000)
			criadas.append(gerada["name"])
			ck("gerar nasce em Rascunho (nunca publicada)", gerada["status"] == "Rascunho", gerada["status"])
			ck("gerar guarda o resumo da IA", bool(gerada["resumo_ia"]))
			ck("gerar guarda a mentoria", len(gerada["mentoria"]) == 1)
			ck("gerar devolve o glossario dos termos usados", "CPC" in gerada["glossario_usado"])
			ck("gerar passa pela revisao OAB", gerada["oab_aprovado"])
			ck("gerar respeita o orcamento informado", gerada["orcamento_diario_centavos"] == 4000, gerada["orcamento_diario_centavos"])

			# teto de orcamento
			try:
				anuncios.gerar("teste teto", "Google", "Contatos", 999999999)
				ck("gerar barra orcamento acima do teto", False)
			except frappe.ValidationError:
				ck("gerar barra orcamento acima do teto", True)

		# sem chave de IA: explica e nao quebra
		with mock.patch("crm.api.ficha._api_key", return_value=""):
			try:
				anuncios.gerar("qualquer coisa")
				ck("sem chave de IA, gerar avisa em vez de estourar", False)
			except frappe.ValidationError as e:
				ck("sem chave de IA, gerar avisa em vez de estourar", "chave" in str(e).lower())

		# ---------- listagem e status ----------
		lista = anuncios.listar()
		ck("listar devolve as campanhas criadas", len([x for x in lista if x["name"] in criadas]) == len(criadas))
		st = anuncios.status()
		ck("status informa se a publicacao direta esta ligada", st["publicacao_direta"] is False)
		ck("status informa que Google e Meta nao estao conectados", not st["google_conectado"] and not st["meta_conectado"])

		# ---------- modulo desligado ----------
		with mock.patch.object(anuncios, "_modulo_ativo", return_value=False):
			try:
				anuncios.listar()
				ck("modulo desligado bloqueia o painel", False)
			except frappe.ValidationError:
				ck("modulo desligado bloqueia o painel", True)

	finally:
		for name in criadas:
			try:
				frappe.delete_doc(anuncios.DOCTYPE, name, force=True, ignore_permissions=True)
			except Exception:
				pass
		frappe.db.commit()

	return res
