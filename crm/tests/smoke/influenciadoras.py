"""Teste de fumaça: carteira de influenciadoras e parcerias (crm.api.influenciadoras).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe

from crm.api import influenciadoras as inf


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	i1 = None
	try:
		r1 = inf.criar_influenciadora("Zz Teste Influenciadora", instagram="@zzteste", nicho="Moda", seguidores_aprox=1000)
		i1 = r1["name"]
		ck("criar_influenciadora devolve o nome", bool(i1))

		p1 = inf.criar_parceria(i1, "Marca A", status="Negociando", valor=1000, prazo_entrega="2026-11-01")
		p2 = inf.criar_parceria(i1, "Marca B", valor=2000)
		ck("criar_parceria aceita status explícito", bool(p1.get("name")))
		ck("criar_parceria usa 'Negociando' como padrão quando não informado", frappe.db.get_value("CRM Parceria", p2["name"], "status") == "Negociando")

		erro_sem_influenciadora = None
		try:
			inf.criar_parceria("influenciadora-que-nao-existe", "Marca X")
		except frappe.ValidationError as e:
			erro_sem_influenciadora = str(e)
		ck("criar_parceria recusa influenciadora inexistente", bool(erro_sem_influenciadora))

		lst = inf.listar_influenciadoras()
		encontrada = next((x for x in lst if x["name"] == i1), None)
		ck("listar_influenciadoras encontra a criada", encontrada is not None)
		ck("listar_influenciadoras conta as 2 parcerias dela", encontrada and encontrada["parcerias"] == 2)

		parcerias = inf.listar_parcerias(i1)
		ck("listar_parcerias traz as 2 parcerias", len(parcerias) == 2)

		inf.atualizar_parceria(p1["name"], status="Fechada", valor=1200)
		depois = frappe.db.get_value("CRM Parceria", p1["name"], ["status", "valor"], as_dict=True)
		ck("atualizar_parceria muda status e valor", depois.status == "Fechada" and depois.valor == 1200)

		inf.atualizar_influenciadora(i1, nicho="Moda e Beleza")
		ck("atualizar_influenciadora muda o nicho", frappe.db.get_value("CRM Influenciadora", i1, "nicho") == "Moda e Beleza")

		inf.excluir_parceria(p2["name"])
		ck("excluir_parceria remove de verdade", not frappe.db.exists("CRM Parceria", p2["name"]))
		ck("excluir_parceria não mexe na outra parceria", frappe.db.exists("CRM Parceria", p1["name"]))

		inf.excluir_influenciadora(i1)
		ck("excluir_influenciadora remove a influenciadora", not frappe.db.exists("CRM Influenciadora", i1))
		ck("excluir_influenciadora apaga as parcerias dela junto", not frappe.db.exists("CRM Parceria", p1["name"]))
		i1 = None
	finally:
		if i1:
			for p in frappe.get_all("CRM Parceria", filters={"influenciadora": i1}, pluck="name"):
				frappe.delete_doc("CRM Parceria", p, force=True, ignore_permissions=True)
			frappe.delete_doc("CRM Influenciadora", i1, force=True, ignore_permissions=True)
		frappe.db.commit()

	return res
