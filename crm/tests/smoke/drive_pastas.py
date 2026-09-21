"""Teste de fumaça: envio ao Google Drive (pastas e tentativas), sem falar com o Google.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json
import types
from unittest import mock

import frappe

from crm.api import gdrive


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    before = frappe.db.get_value("CRM Google Drive", None, ["pasta_id", "pasta_nome", "pastas"], as_dict=True) or {}
    try:
        ids = iter(f"id{i}" for i in range(100))
        with mock.patch.object(gdrive, "_find_or_create_folder", lambda name, parent: next(ids)):
            first = gdrive._folder_for(["Clientes", "Ana Silva"])
            calls_before = frappe.db.get_single_value("CRM Google Drive", "pastas")
            second = gdrive._folder_for(["Clientes", "Ana Silva"])
        ck("pasta do cliente criada no Drive e reaproveitada", first == second and "/Clientes/Ana Silva" in json.loads(calls_before))
        ck("configuração do Drive gravada sem salvar o documento inteiro", frappe.db.get_single_value("CRM Google Drive", "pasta_id"))

        # cliente: documentos do cliente vão para Clientes/<nome>; proposta continua em Propostas
        doc = types.SimpleNamespace(folder="Home/Clientes/Ana Silva", file_name="RG - 2026.jpg", attached_to_doctype="CRM Deal", attached_to_name="X")
        ck("documento do cliente espelha a pasta Clientes", gdrive._path_for_file(doc) == ["Clientes", "Ana Silva"])

        # tentativas: deadlock passageiro não perde o arquivo
        calls = []

        def flaky(name):
            calls.append(1)
            if len(calls) < 3:
                raise frappe.QueryDeadlockError("x")
            return "ok"

        with mock.patch.object(gdrive, "_upload_file_doc", flaky), mock.patch("time.sleep", lambda s: None):
            ck("envio tenta de novo após disputa no banco", gdrive.upload_file_doc("F") == "ok" and len(calls) == 3)
    finally:
        frappe.db.rollback()
        for k, v in before.items():
            frappe.db.set_single_value("CRM Google Drive", k, v)
        frappe.db.commit()
    return res