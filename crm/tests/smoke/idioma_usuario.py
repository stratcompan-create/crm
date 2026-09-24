"""Teste de fumaça: usuário sem idioma definido recebe pt-BR sozinho (e-mails/avisos do
próprio Frappe, como o de atribuição de tarefa, saem em português em vez de inglês).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe

from crm.api import automacoes as au


def run():
    frappe.set_user("Administrator")
    res = []

    def ck(name, cond, extra=""):
        res.append(bool(cond))
        print("OK  " if cond else "FAIL", name, extra)

    d1 = frappe._dict(language="")
    au.ensure_user_language(d1)
    ck("idioma em branco vira pt-BR", d1.language == "pt-BR")

    d2 = frappe._dict(language="en")
    au.ensure_user_language(d2)
    ck("idioma já escolhido não é sobrescrito", d2.language == "en")

    made = None
    try:
        made = frappe.get_doc(
            {"doctype": "User", "email": "zz.idioma@example.com", "first_name": "Zz", "send_welcome_email": 0}
        ).insert(ignore_permissions=True)
        ck("usuário novo já nasce com pt-BR", frappe.db.get_value("User", made.name, "language") == "pt-BR")
    finally:
        if made:
            frappe.delete_doc("User", made.name, force=True, ignore_permissions=True)
        frappe.db.commit()
    return res
