"""Teste de fumaça: controle de horas por negócio (crm.api.horas).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

import frappe

from crm.api import horas as h


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	deal = frappe.get_doc(
		{
			"doctype": "CRM Deal",
			"organization_name": "Cliente de Teste - Controle de Horas",
			"status": "Won",
			"natureza": "Recorrente",
			"valor_recorrente": 3300,
		}
	).insert(ignore_permissions=True)

	deal_sem_horas = frappe.get_doc(
		{
			"doctype": "CRM Deal",
			"organization_name": "Cliente de Teste - Sem Lançamento",
			"status": "Won",
			"natureza": "Recorrente",
			"valor_recorrente": 2000,
		}
	).insert(ignore_permissions=True)

	try:
		r1 = h.registrar_hora(deal.name, 2.5, "CRM", observacoes="ajuste de automação")
		ck("registrar_hora devolve o nome do lançamento", bool(r1.get("name")))

		r2 = h.registrar_hora(deal.name, 1, "Reunião")
		ck("registrar_hora aceita um segundo lançamento", bool(r2.get("name")))

		lancado = frappe.db.get_value("CRM Horas", r1["name"], "usuario")
		ck("o lançamento fica em nome de quem está logado", lancado == "Administrator")

		lst = h.listar_horas(deal.name)
		ck("listar_horas traz os 2 lançamentos", len(lst["lancamentos"]) == 2)
		ck("listar_horas soma o total geral certo", lst["total_geral"] == 3.5)
		ck("listar_horas soma o total do mês certo (lançamentos de hoje)", lst["total_mes"] == 3.5)

		rent = h.rentabilidade_clientes()
		piores = {p["deal"]: p for p in rent["piores"]}
		ck("rentabilidade_clientes traz o cliente com horas lançadas em 'piores'", deal.name in piores)
		ck(
			"rentabilidade_clientes calcula o R$/hora efetivo certo (3300 / 3.5h)",
			abs(piores[deal.name]["efetivo"] - (3300 / 3.5)) < 0.01,
		)
		sem_registro_nomes = {s["deal"] for s in rent["sem_registro"]}
		ck("rentabilidade_clientes põe quem não lançou hora em 'sem_registro'", deal_sem_horas.name in sem_registro_nomes)
		ck("rentabilidade_clientes não duplica quem não lançou hora em 'piores'", deal_sem_horas.name not in piores)

		erro_excluir_alheio = None
		frappe.set_user("Guest")
		try:
			h.excluir_hora(r1["name"])
		except frappe.ValidationError as e:
			erro_excluir_alheio = str(e)
		finally:
			frappe.set_user("Administrator")
		ck("excluir_hora recusa apagar lançamento de outra pessoa (sem ser gestor)", bool(erro_excluir_alheio))

		h.excluir_hora(r1["name"])
		ck("excluir_hora remove de verdade quem lançou", not frappe.db.exists("CRM Horas", r1["name"]))
	finally:
		frappe.set_user("Administrator")
		frappe.db.delete("CRM Horas", {"deal": ["in", [deal.name, deal_sem_horas.name]]})
		frappe.delete_doc("CRM Deal", deal.name, force=True, ignore_permissions=True)
		frappe.delete_doc("CRM Deal", deal_sem_horas.name, force=True, ignore_permissions=True)
		frappe.db.commit()

	return res
