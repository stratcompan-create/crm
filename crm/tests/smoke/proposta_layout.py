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
                            "condicoes": [{"titulo": "Prazo mínimo", "texto": "6 meses"}]}}
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
