"""Teste de fumaça: segurança e dados (crm.api.seguranca) e caso sigiloso (permissões)."""

import frappe

from crm.api import seguranca as sg

EMAIL = "advogado.teste.sigilo@example.com"


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	def caso(nome, **kw):
		first, last = nome.split(" ", 1)
		d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": first, "last_name": last, "lead_name": nome, **kw})
		d.flags.sem_cobranca_automatica = True
		return d.insert(ignore_permissions=True)

	criados = []
	try:
		if not frappe.db.exists("User", EMAIL):
			u = frappe.get_doc({"doctype": "User", "email": EMAIL, "first_name": "Advogado", "last_name": "Sigilo", "send_welcome_email": 0})
			u.append("roles", {"role": "Sales Manager"})
			u.insert(ignore_permissions=True)
		normal = caso("Caso Normal Sigilo")
		secreto = caso("Caso Secreto Sigilo", sigiloso=1)
		dele = caso("Caso Proprio Sigilo", sigiloso=1, deal_owner=EMAIL)
		criados += [normal.name, secreto.name, dele.name]
		frappe.db.commit()

		frappe.set_user(EMAIL)
		ck("advogado (gestor) vê caso comum", frappe.has_permission("CRM Deal", "read", normal.name))
		ck("advogado NÃO vê caso sigiloso de outro", not frappe.has_permission("CRM Deal", "read", secreto.name))
		ck("advogado vê o caso sigiloso que é dele", frappe.has_permission("CRM Deal", "read", dele.name))
		lista = frappe.get_list("CRM Deal", filters={"name": ["in", criados]}, pluck="name")
		ck("lista de casos esconde o sigiloso dos outros", secreto.name not in lista and normal.name in lista and dele.name in lista, str(lista))
		frappe.set_user("Administrator")
		ck("administrador vê tudo", frappe.has_permission("CRM Deal", "read", secreto.name))

		d = frappe.get_doc("CRM Deal", normal.name)
		d.consentimento_lgpd = 1
		d.save(ignore_permissions=True)
		ck("autorização LGPD fica com data e hora", bool(frappe.db.get_value("CRM Deal", normal.name, "consentimento_em")))

		x = sg.exportar_tudo()
		ck("exporta todos os dados numa planilha", x["nome"].endswith(".xlsx") and len(x["arquivo"]) > 1000)
		t = sg.buscar_titular("Caso Normal Sigilo")
		ck("acha o titular pelo nome", any(i["name"] == normal.name for i in t))
		ck("exporta os dados do titular", sg.exportar_titular("CRM Deal", normal.name)["nome"].endswith(".xlsx"))

		frappe.get_doc({"doctype": "CRM Honorario", "deal": normal.name, "status": "Pago", "tipo_honorario": "Fixo", "valor": 300,
						"data_vencimento": frappe.utils.nowdate(), "data_pagamento": frappe.utils.nowdate()}).insert(ignore_permissions=True)
		erro = None
		try:
			sg.anonimizar_titular("CRM Deal", normal.name, "sim")
		except frappe.ValidationError as e:
			erro = str(e)
		ck("anonimizar exige digitar ANONIMIZAR", bool(erro))
		sg.anonimizar_titular("CRM Deal", normal.name, "ANONIMIZAR")
		v = frappe.db.get_value("CRM Deal", normal.name, ["lead_name", "email", "consentimento_lgpd"], as_dict=True)
		ck("anonimizar apaga nome e contato", v.lead_name == sg.ANON and not v.email, str(v))
		ck("financeiro continua depois de anonimizar", frappe.db.exists("CRM Honorario", {"deal": normal.name, "valor": 300}))

		frappe.get_doc({"doctype": "View Log", "reference_doctype": "CRM Deal", "reference_name": dele.name, "viewed_by": EMAIL}).insert(ignore_permissions=True)
		qa = sg.quem_acessou(dele.name)
		ck("mostra quem abriu o caso", any(p["usuario"] == EMAIL for p in qa), str(qa))

		frappe.get_doc({"doctype": "CRM Task", "title": "Tarefa atrasada sigilo", "status": "Todo", "assigned_to": EMAIL,
						"due_date": frappe.utils.add_days(frappe.utils.nowdate(), -2), "reference_doctype": "CRM Deal",
						"reference_docname": dele.name}).insert(ignore_permissions=True)
		carga = {c["usuario"]: c for c in sg.carga_equipe()}
		c = carga.get(EMAIL)
		ck("carga mostra casos ativos e tarefa atrasada da pessoa", c and c["casos_ativos"] >= 1 and c["tarefas_atrasadas"] >= 1, str(c))
		erro = None
		frappe.conf.demo_username = "x"
		try:
			sg.definir_dois_fatores(1)
		except frappe.ValidationError as e:
			erro = str(e)
		finally:
			frappe.conf.pop("demo_username", None)
		ck("no site de demonstração não liga o login em duas etapas", bool(erro))
	finally:
		frappe.set_user("Administrator")
		for n in criados:
			frappe.db.delete("CRM Honorario", {"deal": n})
			frappe.db.delete("CRM Task", {"reference_docname": n})
			frappe.db.delete("View Log", {"reference_name": n})
			frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True)
		if frappe.db.exists("User", EMAIL):
			frappe.delete_doc("User", EMAIL, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res
