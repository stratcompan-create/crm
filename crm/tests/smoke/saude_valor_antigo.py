"""Teste de fumaça: valor antigo não conta como venda, saúde do sistema e resumo semanal.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import json
from unittest import mock

import frappe
from frappe.utils import nowdate

from crm.api import automacoes as au
from crm.api import prospeccao
from crm.api import saude_sistema as ss


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    deal = None
    try:
        deal = frappe.get_doc(
            {"doctype": "CRM Deal", "organization_name": "Zz Antigo", "first_name": "Zz", "deal_value": 1500,
             "lancamento_antigo": 1, "status": "Qualification"}
        ).insert(ignore_permissions=True)
        deal.status = "Won"
        deal.save(ignore_permissions=True)
        rows = frappe.get_all("CRM Honorario", filters={"deal": deal.name}, fields=["valor", "data_vencimento"])
        ck("valor antigo gera a cobrança vencendo hoje", len(rows) == 1 and str(rows[0].data_vencimento) == nowdate())
        ck("valor antigo não cria tarefas de início", frappe.db.count("CRM Task", {"reference_docname": deal.name}) == 0)
        ck("valor antigo não gera contrato", not frappe.db.exists("File", {"attached_to_name": deal.name, "file_name": ["like", "Contrato%"]}))
        ck("valor antigo não conta como fechamento na Prospecção", prospeccao._automatic(nowdate()).get(nowdate(), {}).get("fechamentos", 0) == 0)
    finally:
        frappe.db.rollback()
        if deal:
            for dt, f in (("CRM Honorario", "deal"), ("CRM Task", "reference_docname")):
                for x in frappe.get_all(dt, filters={f: deal.name}, pluck="name"):
                    frappe.delete_doc(dt, x, force=True, ignore_permissions=True)
            for x in frappe.get_all("File", filters={"folder": ["like", "Home/Clientes/Zz Antigo%"]}, pluck="name"):
                frappe.delete_doc("File", x, force=True, ignore_permissions=True)
            frappe.delete_doc("CRM Deal", deal.name, force=True, ignore_permissions=True)
            for dt, n in (("File", "Home/Clientes/Zz Antigo"), ("CRM Organization", "Zz Antigo")):
                if frappe.db.exists(dt, n):
                    frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
        frappe.db.commit()

    # saúde do sistema: avisa uma vez, não repete, e avisa quando volta ao normal
    sent = []
    bad = [{"key": "email", "label": "E-mail", "ok": False, "mensagem": "x"}]
    good = [{"key": "email", "label": "E-mail", "ok": True, "mensagem": "ok"}]
    frappe.db.set_default(ss.LAST_SIG, "")
    with mock.patch.object(ss, "_send", lambda p, recovered=False: sent.append((len(p), recovered))):
        with mock.patch.object(ss, "run_checks", lambda since=None: bad):
            ss.check_and_alert()
            ss.check_and_alert()
        with mock.patch.object(ss, "run_checks", lambda since=None: good):
            ss.check_and_alert()
    frappe.db.set_default(ss.LAST_SIG, "")
    ck("alerta de falha: 1 aviso do problema e 1 de recuperação", sent == [(1, False), (0, True)], str(sent))
    ck("painel de saúde do sistema devolve todos os itens", len(ss.get_system_health()["itens"]) == 9)

    # resumo semanal: o job horário gera uma vez só
    for x in frappe.get_all("CRM Relatorio Semanal", pluck="name"):
        frappe.delete_doc("CRM Relatorio Semanal", x, force=True, ignore_permissions=True)
    with mock.patch("frappe.utils.now_datetime", lambda: frappe.utils.get_datetime(nowdate() + " 09:00:00")):
        au.weekly_job()
        first = frappe.db.count("CRM Relatorio Semanal")
        au.weekly_job()
        second = frappe.db.count("CRM Relatorio Semanal")
    ck("resumo semanal gerado pelo job horário sem duplicar", first == 1 and second == 1)
    for x in frappe.get_all("CRM Relatorio Semanal", pluck="name"):
        frappe.delete_doc("CRM Relatorio Semanal", x, force=True, ignore_permissions=True)
    for x in frappe.get_all("File", filters={"attached_to_doctype": "CRM Relatorio Semanal"}, pluck="name"):
        frappe.delete_doc("File", x, force=True, ignore_permissions=True)
    frappe.db.commit()
    return res