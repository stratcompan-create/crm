"""Teste de fumaça: exclusão em massa de documentos (crm.api.doc.delete_bulk_docs).

Cobre o bug real visto em produção: doctypes com autoname "autoincrement"
(como CRM Task) têm o "name" como número - o navegador manda os ids do JSON
como int, não como string, e isso quebrava o processamento de documentos
vinculados e o delete_bulk do Frappe (erros "sequence item 0: expected str
instance, int found" e "Argument 'docname' should be..." na Saúde do sistema).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import json

import frappe

from crm.api.doc import delete_bulk_docs


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	# CRM Task usa autoname "autoincrement" - o name vem como int de verdade,
	# exatamente a condição que gerava o bug em produção
	t1 = frappe.get_doc({"doctype": "CRM Task", "title": "Exclusão em massa - teste 1", "status": "Backlog"}).insert(
		ignore_permissions=True
	)
	t2 = frappe.get_doc({"doctype": "CRM Task", "title": "Exclusão em massa - teste 2", "status": "Backlog"}).insert(
		ignore_permissions=True
	)
	ck("CRM Task nasce com name numérico (autoincrement)", isinstance(t1.name, int))

	# dá um comentário e uma atribuição pra ter documentos vinculados de verdade
	# (sem isso o loop de "linked docs" nem roda, e o bug não aparece)
	frappe.get_doc(
		{"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "CRM Task", "reference_name": str(t1.name), "content": "comentário de teste"}
	).insert(ignore_permissions=True)
	from frappe.desk.form.assign_to import add as assign_add

	assign_add({"doctype": "CRM Task", "name": t1.name, "assign_to": [frappe.session.user]})
	frappe.db.commit()

	antes = frappe.db.count("Error Log")

	# exatamente como o navegador manda pra um doctype autoincrement: uma
	# lista de NÚMEROS json, não de strings
	resultado = delete_bulk_docs("CRM Task", json.dumps([int(t1.name), int(t2.name)]))

	ck("delete_bulk_docs não lança exceção com ids inteiros", resultado == "success")
	ck("tarefa 1 (com vínculos) foi excluída de verdade", not frappe.db.exists("CRM Task", t1.name))
	ck("tarefa 2 (sem vínculos) foi excluída de verdade", not frappe.db.exists("CRM Task", t2.name))

	depois = frappe.db.count("Error Log")
	ck("não registrou nenhum Error Log novo (antes vazava 'Bulk Delete Error')", depois == antes, f"antes={antes} depois={depois}")

	frappe.db.commit()
	return res
