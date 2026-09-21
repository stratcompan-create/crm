"""Roda todos os testes de fumaça e mostra um resumo.

Uso (no ambiente local, nunca em produção, pois cria e apaga dados de teste):
    bench --site crm.localhost execute crm.tests.run_smoke.run_all
"""

import importlib
import sys

import frappe

MODULES = [
    "automacoes_financeiro_agenda",
    "instagram_automacoes",
    "pasta_e_documentos_do_cliente",
    "ficha_e_proposta",
    "sugestoes_de_resposta",
    "interligacoes",
    "mapas",
    "saude_valor_antigo",
]


def run_all():
    total = failed = 0
    for name in MODULES:
        print(f"\n=== {name}")
        frappe.db.rollback()
        try:
            res = importlib.import_module(f"crm.tests.smoke.{name}").run()
        except Exception:
            import traceback

            traceback.print_exc()
            total += 1
            failed += 1
            continue
        total += len(res)
        failed += sum(1 for r in res if not r)
    print(f"\nRESULTADO GERAL: {total - failed}/{total}")
    if failed:
        sys.exit(1)
