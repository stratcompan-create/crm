"""Teste de fumaça: relatório de métricas do Instagram em PDF.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import io
from unittest import mock

import frappe
from pypdf import PdfReader

from crm.api import instagram_metricas as im
from crm.api import analise_consultor


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(n, c):
        res.append(bool(c))
        print(("OK  " if c else "FAIL"), n)

    S = frappe.get_single("CRM Instagram Settings")
    old = (S.enabled, S.get_password("access_token", raise_exception=False))
    frappe.db.set_single_value("CRM Instagram Settings", "enabled", 1)
    frappe.db.set_single_value("CRM Instagram Settings", "access_token", "x")
    frappe.cache().delete_value("ig_insights:7")

    calls = {"totais": 0}

    class R:
        status_code = 200

        def json(self):
            return self._data

    def fake_get(url, params=None, timeout=None):
        r = R()
        params = params or {}
        if url.endswith("/me") and "username" in (params.get("fields") or ""):
            r._data = {
                "username": "minhamarca", "name": "Minha Marca", "account_type": "BUSINESS",
                "followers_count": 1500, "follows_count": 300, "media_count": 42,
            }
        elif url.endswith("/me/insights") and params.get("metric_type") == "total_value":
            calls["totais"] += 1
            vals = (
                {"reach": 5000, "views": 8000, "profile_views": 300, "accounts_engaged": 200,
                 "total_interactions": 900, "likes": 600, "comments": 100, "shares": 50,
                 "saves": 150, "website_clicks": 20}
                if calls["totais"] == 1 else
                {"reach": 4000, "views": 6000, "profile_views": 250, "accounts_engaged": 150,
                 "total_interactions": 700, "likes": 450, "comments": 80, "shares": 40,
                 "saves": 130, "website_clicks": 10}
            )
            r._data = {"data": [{"name": k, "total_value": {"value": v}} for k, v in vals.items()]}
        elif url.endswith("/me/insights") and params.get("metric") == "reach":
            r._data = {"data": [{"values": [
                {"end_time": "2026-09-29T07:00:00+0000", "value": 500},
                {"end_time": "2026-09-30T07:00:00+0000", "value": 700},
            ]}]}
        elif url.endswith("/me/media"):
            r._data = {"data": [{
                "id": "M1", "caption": "Post de teste", "media_type": "IMAGE", "media_product_type": "FEED",
                "permalink": "https://instagram.com/p/1", "thumbnail_url": "", "media_url": "https://x/1.jpg",
                "timestamp": "2026-09-28T12:00:00+0000", "like_count": 60, "comments_count": 5,
            }]}
        elif url.endswith("/M1/insights"):
            vals = {"reach": 1000, "views": 1200, "likes": 60, "comments": 5, "shares": 2, "saved": 10, "total_interactions": 77}
            r._data = {"data": [{"name": k, "values": [{"value": v}]} for k, v in vals.items()]}
        else:
            r._data = {"data": []}
        return r

    folder = "Home/Instagram"
    try:
        with mock.patch("requests.get", fake_get):
            r = im.export_metrics_pdf(days=7)
            ck("export_metrics_pdf devolve o arquivo", bool(r.get("file_url")) and bool(r.get("file_name")))

            file_name = frappe.get_all("File", filters={"file_name": r["file_name"]}, pluck="name")[0]
            file_doc = frappe.get_doc("File", file_name)
            ck("arquivo salvo na pasta Instagram", file_doc.folder == folder)
            ck("arquivo privado", bool(file_doc.is_private))

            texto = _text(file_doc.get_content())
            ck("relatório traz o título", "Relatório do Instagram" in texto)
            ck("relatório traz o @ do perfil", "minhamarca" in texto)
            ck("relatório traz o alcance do período atual", "5.000" in texto)
            ck("relatório traz o alcance do período anterior", "4.000" in texto)
            ck("relatório traz a variação percentual", "%" in texto)
            ck("relatório traz os seguidores", "1.500" in texto)
            ck("relatório traz o melhor post do período", "1.000" in texto)
            ck("sem análise de IA configurada, o relatório não mostra a seção", "Análise" not in texto)

            with mock.patch.object(analise_consultor, "gerar", return_value="Alcance caiu, vale testar horários diferentes de postagem."):
                r_ia = im.export_metrics_pdf(days=7)
                file_name_ia = frappe.get_all("File", filters={"file_name": r_ia["file_name"]}, pluck="name")[0]
                texto_ia = _text(frappe.get_doc("File", file_name_ia).get_content())
            ck("com IA, o relatório traz a análise de consultor", "horários diferentes de postagem" in texto_ia)

            # gerar de novo (mesmo período) substitui o arquivo anterior, não duplica
            im.export_metrics_pdf(days=7)
            ck(
                "gerar de novo não deixa arquivo duplicado",
                frappe.db.count("File", {"folder": folder, "file_name": ["like", "Relatorio Instagram 7d%"]}) == 1,
            )

            # dia fora da lista permitida cai para 30
            r2 = im.export_metrics_pdf(days=999)
            ck("dia inválido cai para 30", "Relatorio Instagram 30d" in r2["file_name"])
    finally:
        for f in frappe.get_all("File", filters={"folder": folder}, pluck="name"):
            frappe.delete_doc("File", f, force=True, ignore_permissions=True)
        if frappe.db.exists("File", folder):
            frappe.delete_doc("File", folder, force=True, ignore_permissions=True)
        frappe.db.set_single_value("CRM Instagram Settings", "enabled", old[0])
        frappe.db.set_single_value("CRM Instagram Settings", "access_token", old[1] or "")
        frappe.cache().delete_value("ig_insights:7")
        frappe.cache().delete_value("ig_insights:30")
        frappe.db.commit()

    return res
