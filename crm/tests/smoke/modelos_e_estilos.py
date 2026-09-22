"""Teste de fumaça: modelos de documentos (contrato, procuração...) e estilos de cor dos documentos.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import base64
import io

import frappe
from pypdf import PdfReader

from crm.api import estilo, modelos_documentos as md, proposta, tipografia


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def _fonts_in(pdf: bytes) -> str:
    names = set()
    for page in PdfReader(io.BytesIO(pdf)).pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for ref in fonts.values():
            names.add(str(ref.get_object().get("/BaseFont", "")))
    return " ".join(names).lower()


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    made, deal = [], None
    try:
        md.ensure_example()
        ck("modelo de exemplo existe depois da migração", frappe.db.count("CRM Modelo Documento") >= 1)
        ck("valor por extenso em português", md._extenso(1500) == "mil e quinhentos reais", md._extenso(1500))
        ck("data por extenso", md._date_long("2026-09-21") == "21 de setembro de 2026")

        nome = "Zz Modelo Teste"
        md.save_model(nome, "Contrato", "# CONTRATO\n\nCliente: {nome_cliente}, CPF {cpf_cnpj}.\nValor: {valor} ({valor_extenso}).\n\n**Objeto:** {objeto}\n\n{data}", "Contrato de teste")
        made.append(nome)
        deal = frappe.get_doc(
            {"doctype": "CRM Deal", "organization_name": "Zz Org Modelo", "first_name": "Maria Souza", "deal_value": 1500,
             "status": "Qualification", "budget_items": [{"description": "Consultoria mensal", "qty": 1, "unit_price": 1500}]}
        ).insert(ignore_permissions=True)

        chk = md.check_model(deal.name, nome)
        ck("aponta o que falta antes de gerar (CPF)", [f["chave"] for f in chk["faltando"]] == ["cpf_cnpj"], str(chk))
        out = md.generate(deal.name, nome)
        ck("não gera com dado faltando", out["ok"] is False)
        md.save_client_data(deal.name, {"cpf_cnpj": "123.456.789-09"})
        out = md.generate(deal.name, nome, "claro")
        ck("gera o PDF quando está completo", out["ok"] and out["nome"].startswith("Contrato - Maria Souza") and out["nome"].endswith("v1.pdf"), out.get("nome"))
        pdf = frappe.get_doc("File", out["arquivo"]).get_content()
        txt = _text(pdf)
        ck("PDF traz os dados do cliente e do negócio", "Maria Souza" in txt and "123.456.789-09" in txt and "R$ 1.500,00" in txt and "mil e quinhentos reais" in txt)
        ck("objeto vem do orçamento", "Consultoria mensal" in txt)
        ck("arquivo vai para a pasta do cliente", frappe.db.get_value("File", out["arquivo"], "folder") == frappe.db.get_value("CRM Deal", deal.name, "pasta_cliente"))
        out2 = md.generate(deal.name, nome)
        ck("segunda geração vira v2", out2["nome"].endswith("v2.pdf"))

        md.save_model("Zz Modelo Ruim", "Outro", "Olá {campo_que_nao_existe}")
        made.append("Zz Modelo Ruim")
        try:
            md.generate(deal.name, "Zz Modelo Ruim")
            ck("recusa campo que não existe", False)
        except Exception:
            ck("recusa campo que não existe", True)

        for st in ("escuro", "claro", "branco", "cor"):
            pdf = base64.b64decode(md.preview_model("# Título\n\nTexto {nome_cliente}.", "Contrato", "Teste", st)["pdf"])
            ck(f"documento no estilo '{st}' gera PDF", pdf.startswith(b"%PDF"))

        # proposta: cada estilo gera o mesmo número de páginas, sem página em branco
        data = proposta._merge(proposta.default_proposal(), {
            "capa": {"subtitulo": "Teste"},
            "intro": {"titulo": "Um projeto", "texto": "Texto."},
            "escopo": {"titulo": "Escopo", "itens": [{"titulo": "A", "texto": "B"}]},
            "investimento": {"titulo": "Investimento", "plano_titulo": "Plano"},
        })
        settings = {"brand_color": "#1f4d3a", "brand_accent": "#b89b5e", "brand_neutral": "#f1ead9", "brand_name": "Teste"}
        items = [frappe._dict(description="Item", qty=1, unit_price=100)]
        counts = {}
        for st in ("escuro", "claro", "branco", "cor"):
            data["capa"]["tema"] = st
            html = proposta.render_proposal_html(None, settings, items, 100, "Cliente", data, "")
            counts[st] = len(PdfReader(io.BytesIO(proposta.render_pdf(html))).pages)
        ck("proposta: 4 estilos, sem página em branco (capa + 3 seções = 4 páginas)", set(counts.values()) == {4}, str(counts))
        for st in ("escuro", "claro", "branco", "cor"):
            pdf = base64.b64decode(estilo.preview_pdf("#1f4d3a", "#b89b5e", "#f1ead9", st, "Escritório X")["pdf"])
            ck(f"prévia em PDF das cores digitadas (estilo '{st}')", pdf.startswith(b"%PDF") and len(PdfReader(io.BytesIO(pdf)).pages) >= 4)
        # tipografia: catálogo completo, padrões e cada par pronto embutido no PDF
        cat = tipografia.get_catalog()
        ck("catálogo: todas as fontes têm os arquivos", all(f["arquivos"] for f in cat["fontes"]) and len(cat["fontes"]) >= 14)
        ck("função sem escolha usa o padrão; fonte inválida também", tipografia.resolve({}, "proposta")["titulo"] == "lora" and tipografia.resolve({"fonte_texto": "xyz"}, "documento")["texto"] == "lora")
        sample = {"classico": "playfair", "moderno": "montserrat", "elegante": "cormorant", "tradicional": "baskerville", "tecnologia": "space"}
        for key, marker in sample.items():
            f = tipografia.PRESETS[key][2]
            pdf = base64.b64decode(estilo.preview_pdf("#1f4d3a", "#b89b5e", "#f1ead9", "claro", "X", f["titulo"], f["subtitulo"], f["texto"], f["numeros"])["pdf"])
            used = _fonts_in(pdf)
            ck(f"par '{key}': fonte {marker} embutida no PDF, mesmo número de páginas", marker in used.replace(" ", "") and len(PdfReader(io.BytesIO(pdf)).pages) >= 4, used[:80])
        ck("estilo inválido volta ao padrão", estilo.resolve({}, "xyz")["estilo"] == "escuro")
    finally:
        frappe.db.rollback()
        if deal:
            for x in frappe.get_all("File", filters={"attached_to_name": deal.name}, pluck="name"):
                frappe.delete_doc("File", x, force=True, ignore_permissions=True)
            for x in frappe.get_all("Comment", filters={"reference_name": deal.name}, pluck="name"):
                frappe.delete_doc("Comment", x, force=True, ignore_permissions=True)
            frappe.delete_doc("CRM Deal", deal.name, force=True, ignore_permissions=True)
            for f in ("Home/Clientes/Zz Org Modelo",):
                if frappe.db.exists("File", f):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            if frappe.db.exists("CRM Organization", "Zz Org Modelo"):
                frappe.delete_doc("CRM Organization", "Zz Org Modelo", force=True, ignore_permissions=True)
        for n in made:
            if frappe.db.exists("CRM Modelo Documento", n):
                frappe.delete_doc("CRM Modelo Documento", n, force=True, ignore_permissions=True)
        frappe.db.commit()
    return res