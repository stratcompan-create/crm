"""Teste de fumaça: layout novo da proposta (WeasyPrint) e os campos novos que a IA preenche.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import io, json
from unittest import mock

import frappe
from pypdf import PdfReader

from crm.api import ficha, proposta, proposta_layout


def run():
    frappe.set_user("Administrator")
    res = []
    def ck(n, c, e=""): res.append(bool(c)); print(("OK  " if c else "FAIL"), n, e)
    settings = frappe.get_single("FCRM Settings")
    made = []
    try:
        data = proposta._merge(proposta.default_proposal(), {
            "diagnostico": {"cartoes": [{"titulo": "Nota fiscal", "texto": "Um turno por mês", "solucao": "Automática"}]},
            "investimento": {"opcoes": [
                {"rotulo": "À vista", "valor": "R$ 3.500", "detalhe": "Pagamento único", "selo": "R$ 1.500 de economia"},
                {"rotulo": "Mensalidade", "valor": "R$ 850", "detalhe": ""},
            ]},
        })
        html = proposta.render_proposal_html(None, settings, [], 0, "Cliente Teste", data, "")
        ck("cartões de preço sem itens no orçamento", "R$ 3.500" in html and "R$ 1.500 de economia" in html)
        ck("dor com hoje e com a proposta", "Com a proposta" in html and "Automática" in html)
        ck("seção sem título ganha título padrão", "<h1>O que <em>entendemos da situação</em></h1>" in html)
        pdf = proposta.render_pdf(html)
        ck("PDF do layout novo: capa + 2 seções", len(PdfReader(io.BytesIO(pdf)).pages) == 3, len(PdfReader(io.BytesIO(pdf)).pages))
        items = [frappe._dict(description="Site", qty=1, unit_price=3000), frappe._dict(description="CRM", qty=2, unit_price=1500)]
        sem_opcoes = proposta._merge(proposta.default_proposal(), {})
        html2 = proposta.render_proposal_html(None, settings, items, 6000, "Cliente Teste", sem_opcoes, "")
        ck("sem cartões de preço: um por item + total", "R$ 6.000" in html2 and "2 × R$ 1.500,00" in html2)
        longo = "Texto comprido para passar da página. " * 14
        cheio = proposta._merge(proposta.default_proposal(), {"diagnostico": {"faixa_texto": longo, "cartoes": [{"titulo": f"D{i}", "texto": longo, "solucao": longo} for i in range(6)]}})
        ck("avisa seção que não cabe", any("Diagnóstico" in a for a in proposta.check_fit(settings, [], 0, "X", cheio)))
        ck("não avisa o que cabe", proposta.check_fit(settings, [], 0, "X", data) == [])
        # páginas didáticas: escritas à mão, automáticas pelo escopo, ou desligadas
        dida = proposta._merge(proposta.default_proposal(), {"didatico": {"paginas": [
            {"titulo": "Triagem", "destaque": "no WhatsApp", "texto": "Atende na hora.", "pontos": "Um | explica o um\nDois", "figura": "whatsapp",
             "figura_titulo": "Escritório X", "figura_linhas": "Cliente: Vocês atendem?\nEmpresa: Sim! Qual é o seu nome?"},
        ]}})
        h = proposta.render_proposal_html(None, settings, [], 0, "Cliente", dida, "")
        ck("página didática com conversa e selo de exemplo", "Vocês atendem?" in h and 'class="msg in"' in h and "Exemplo ilustrativo" in h)
        ck("ponto com título e explicação", "<b>Um</b><small>explica o um</small>" in h and "<b>Dois</b></div>" in h)
        esc = {"escopo": {"itens": [{"titulo": "Gestão de Instagram", "texto": "Posts"}, {"titulo": "Site institucional", "texto": "5 páginas"}]}}
        h = proposta.render_proposal_html(None, settings, [], 0, "Cliente", proposta._merge(proposta.default_proposal(), esc), "")
        ck("sem páginas: figuras automáticas pelo escopo", 'class="fig post"' in h and 'class="fig win"' in h)
        off = proposta._merge(proposta.default_proposal(), dict(esc, didatico={"automatico": 0, "paginas": []}))
        ck("automático desligado: sem figuras", "Exemplo ilustrativo" not in proposta.render_proposal_html(None, settings, [], 0, "Cliente", off, ""))
        from crm.api import proposta_figuras
        ck("todas as figuras desenham", all(proposta_figuras.render(t, "T", "A | B | pago\nC | 50%", "Marca") for t in proposta_figuras.TIPOS))
        wa = proposta_figuras.render("whatsapp", "Escritório", "Cliente: Oi\nEmpresa: Olá\nEquipe: Área | Trabalhista", "")
        ck("cartão 'o que a equipe recebe' ao lado do celular", "O que a equipe recebe" in wa and "Trabalhista" in wa and "Equipe" not in wa.split("O que a equipe")[0])
        # logo da marca: fundo liso removido, recortado e pintado quando sumiria no fundo
        import base64, os
        from PIL import Image
        caminho = frappe.get_site_path("public", "files", "zz-logo-teste.png")
        img = Image.new("RGB", (200, 120), (238, 238, 236))
        for x in range(60, 140):
            for y in range(30, 90):
                img.putpixel((x, y), (10, 60, 80))
        img.save(caminho)
        try:
            uri = proposta_layout.logo_uri("/files/zz-logo-teste.png", True, "#ffffff")
            logo = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
            ck("logo sem o fundo e recortado rente", logo.size == (80, 60) and logo.getpixel((0, 0))[3] > 200, logo.size)
            ck("logo escuro na capa escura vira branco", logo.getpixel((40, 30))[:3] == (255, 255, 255))
            ck("logo sem arquivo não quebra", proposta_layout.logo_uri("/files/nao-existe.png", False, "#000000") == "")
        finally:
            os.remove(caminho)
        # lista completa: 52 itens cabem numa página; uma lista enorme gera aviso
        grupos = [{"nome": f"Grupo {g}", "itens": "\n".join(f"Função {g}.{i}" for i in range(5))} for g in range(10)] + [{"nome": "Último", "itens": "A\nB"}]
        com_lista = proposta._merge(proposta.default_proposal(), {"lista": {"grupos": grupos}})
        h = proposta.render_proposal_html(None, settings, [], 0, "Cliente", com_lista, "")
        ck("lista completa numerada de 1 a 52", "<i>52</i>" in h and "<i>53</i>" not in h and "Tudo o que vem" in h)
        ck("52 itens cabem na página", proposta.check_fit(settings, [], 0, "X", com_lista) == [])
        enorme = proposta._merge(proposta.default_proposal(), {"lista": {"grupos": [{"nome": "G", "itens": "\n".join(f"Item {i}" for i in range(130))}]}})
        ck("lista grande demais avisa", any("Lista completa" in a for a in proposta.check_fit(settings, [], 0, "X", enorme)))
        # proposta antiga: só texto do plano e condições, sem itens -> a página de investimento aparece
        so_texto = proposta._merge(proposta.default_proposal(), {"investimento": {"plano_texto": "R$ 3.500 à vista", "condicoes": [{"titulo": "Prazo", "texto": "20 dias"}]}})
        ck("investimento só com texto ainda aparece", "R$ 3.500 à vista" in proposta.render_proposal_html(None, settings, [], 0, "C", so_texto, ""))
        crono = proposta._merge(proposta.default_proposal(), {"cronograma": {"etapas": [{"marco": "1", "titulo": "Diagnóstico", "texto": "x"}, {"marco": "Semana 2", "titulo": "Config", "texto": "y"}]}})
        h = proposta.render_proposal_html(None, settings, [], 0, "C", crono, "")
        ck("marco igual ao número da etapa não repete", '<div class="m">1</div>' not in h and '<div class="m">Semana 2</div>' in h)
        ck("capa corta no fim do trecho, sem reticências", proposta_layout._curto("Integrada ao emissor oficial de Petrolina, emitida quando o pagamento entra e enviada ao cliente.") == "Integrada ao emissor oficial de Petrolina")
        auto = proposta_figuras.auto_pages([{"titulo": "Modelos das áreas", "texto": "contrato e honorário próprios"}, {"titulo": "Nota fiscal automática", "texto": "emitida quando o pagamento entra"}])
        ck("figura automática casa pelo título primeiro", auto[0]["figura"] == "cobranca" and auto[1]["figura"] == "notificacoes" and "Nota fiscal emitida" in auto[1]["figura_linhas"], [a["figura"] for a in auto])
        texto_lista = "## Tudo o que vem\n\n### 1. Chegada: quem procura\n\n" + "".join(f"- **{i}. Função {i}.** Descrição longa da função {i}.\n  continua aqui.\n" for i in range(1, 7)) \
            + "\n### 2. Consulta\n\n" + "".join(f"- **{i}. Função {i}.** Texto.\n" for i in range(7, 13)) + "\n## Valores\n\n- **À vista: R$ 3.500**\n1. **Nota fiscal:** dor\n"
        lt = ficha._lista_do_texto(texto_lista)
        ck("lista copiada do texto sem IA, por grupo", [g["nome"] for g in lt.get("grupos", [])] == ["Chegada", "Consulta"] and lt["grupos"][1]["itens"].splitlines()[0] == "Função 7", lt)
        ck("texto sem lista estruturada não inventa lista", ficha._lista_do_texto("## Dores\n- **Nota fiscal:** um turno") == {})
        seis = proposta._merge(proposta.default_proposal(), {"diagnostico": {"faixa_texto": "Situação.", "cartoes": [{"titulo": f"Dor {i}", "texto": "Hoje assim, " * 4, "solucao": "Com a proposta assim, " * 4} for i in range(6)]}})
        ck("6 cartões 'hoje → com a proposta' viram 2 páginas e cabem", len(proposta_layout._diag_partes(seis["diagnostico"])) == 2 and proposta.check_fit(settings, [], 0, "X", seis) == [])
        ck("valor longo no cartão da equipe vai embaixo do rótulo", 'class="row col"' in proposta_figuras.render("whatsapp", "E", "Cliente: Oi\nEquipe: Resumo | Caso de guarda com detenção, atendimento imediato", ""))
        dup = proposta._merge(proposta.default_proposal(), {"investimento": {"plano_texto": "- Parcelado: R$ 5.000 em 4x", "opcoes": [{"rotulo": "À vista", "valor": "R$ 3.500"}]}})
        ck("com cartões de preço o texto do plano não se repete", "Parcelado: R$ 5.000 em 4x" not in proposta.render_proposal_html(None, settings, [], 0, "C", dup, ""))
        # motor novo falhando: cai no antigo em vez de ficar sem PDF
        with mock.patch.object(proposta_layout, "render_pdf", side_effect=RuntimeError("sem weasyprint")):
            ck("reserva no wkhtmltopdf", proposta.proposal_pdf(None, settings, items, 6000, "Cliente", data, "").startswith(b"%PDF"))

        # IA: títulos, hoje/com a proposta, preços ditos e condições chegam à proposta
        ficha.save_ai_key("sk-ant-teste123")
        lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Zz Layout", "servico": "Sites"}).insert(ignore_permissions=True); made.append(("CRM Lead", lead.name))
        ans = {"dor_objetivo": "Notas manuais", "alinhado": "CRM", "escopo": "- CRM", "prazo": "", "valor": "R$ 3.500 à vista", "objecoes": "", "proximos": "",
               "proposta": {"intro_texto": "Projeto de CRM.", "diagnostico_texto": "Notas manuais.",
                            "diagnostico_cartoes": [{"titulo": "Nota fiscal", "texto": "Um turno por mês", "solucao": "Automática"}],
                            "escopo_itens": [{"titulo": "CRM", "texto": "Base"}],
                            "titulos": {"diagnostico": {"titulo": "Nove pontos,", "destaque": "nove soluções"}, "investimento": {"titulo": "Investimento e", "destaque": "condições"}, "lixo": {"titulo": "x"}},
                            "capa_subtitulo": "CRM sob medida.",
                            "investimento_opcoes": [{"rotulo": "À vista", "valor": "R$ 3.500", "detalhe": "Único", "selo": "Economia"}],
                            "condicoes": [{"titulo": "Prazo mínimo", "texto": "6 meses"}],
                            "paginas_didaticas": [
                                {"titulo": "Cobrança", "destaque": "automática", "texto": "Lembrete e baixa.", "pontos": ["Pix", "Recibo"],
                                 "figura": "Cobranca", "figura_titulo": "Carlos", "figura_linhas": "Parcela 1/2 | R$ 500 | pago"},
                                {"titulo": "Foguete", "texto": "Tipo inválido.", "figura": "foguete", "figura_linhas": "x"}],
                            "lista_completa": {"titulo": "As funções", "destaque": "em uma página",
                                               "grupos": [{"nome": "Chegada", "itens": ["Triagem", "Origem"]}, {"nome": "", "itens": ""}]}}}
        class R:
            ok = True; status_code = 200
            def json(self): return {"content": [{"type": "text", "text": json.dumps(ans)}]}
        with mock.patch("requests.post", lambda *a, **k: R()):
            ficha.fill_from_transcript("CRM Lead", lead.name, "x" * 200)
        r = frappe.get_doc("CRM Lead", lead.name).convert_to_deal()
        deal = r if isinstance(r, str) else r.name; made.append(("CRM Deal", deal))
        p = json.loads(frappe.db.get_value("CRM Deal", deal, "proposal_data") or "{}")
        ck("título e destaque da IA", p["diagnostico"].get("titulo") == "Nove pontos," and p["diagnostico"].get("destaque") == "nove soluções")
        ck("título padrão 'Investimento' é trocado", p["investimento"].get("destaque") == "condições")
        ck("seção desconhecida descartada", "lixo" not in p)
        ck("antes e depois no diagnóstico", p["diagnostico"]["cartoes"][0].get("solucao") == "Automática")
        ck("cartão de preço e selo", p["investimento"]["opcoes"][0]["selo"] == "Economia")
        ck("condições substituem as padrão vazias", p["investimento"]["condicoes"] == [{"titulo": "Prazo mínimo", "texto": "6 meses"}])
        ck("com cartões de preço, o valor não vira texto do plano", not p["investimento"].get("plano_texto"))
        ck("subtítulo da capa", p["capa"].get("subtitulo") == "CRM sob medida.")
        pgs = p.get("didatico", {}).get("paginas") or []
        ck("páginas didáticas da IA chegam à proposta", len(pgs) == 2 and pgs[0]["figura"] == "cobranca" and pgs[0]["pontos"] == "Pix\nRecibo", pgs)
        ck("figura de tipo desconhecido é descartada", len(pgs) == 2 and pgs[1]["figura"] == "" and pgs[1]["figura_linhas"] == "")
        ck("lista completa da IA chega à proposta (grupo vazio descartado)",
           p["lista"]["grupos"] == [{"nome": "Chegada", "itens": "Triagem\nOrigem"}] and p["lista"]["titulo"] == "As funções", p.get("lista"))
    finally:
        frappe.db.rollback()
        for dt, n in reversed(made):
            if frappe.db.exists(dt, n):
                for c in frappe.get_all("Comment", filters={"reference_name": n}, pluck="name"): frappe.delete_doc("Comment", c, force=True, ignore_permissions=True)
                frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
        frappe.db.set_single_value("CRM Automacoes Config", "anthropic_api_key", "")
        from frappe.utils.password import delete_all_passwords_for
        try: delete_all_passwords_for("CRM Automacoes Config", "CRM Automacoes Config")
        except Exception: pass
        frappe.db.commit()
    return res
