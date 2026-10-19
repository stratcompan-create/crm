"""Teste de fumaça: prestação de contas ao cliente (crm.api.prestacao_contas).

Caso com 30% de êxito, duas custas adiantadas (uma para cobrar do cliente), alvará de R$ 48.000
com divisão de 20% dos honorários para um correspondente; confere honorário, repasse, PDF e
carnê-leão. Apaga tudo no fim.
"""

import frappe
from frappe.utils import nowdate

from crm.api import prestacao_contas as pc


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	deal = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": "Teste", "last_name": "Prestação Contas",
						   "lead_name": "Teste Prestação Contas"})
	deal.flags.sem_cobranca_automatica = True
	deal.insert(ignore_permissions=True)
	try:
		pc.salvar_percentual(deal.name, 30)
		ck("guarda o percentual de êxito no caso", frappe.db.get_value("CRM Deal", deal.name, "percentual_exito") == 30)

		c1 = pc.nova_custa(deal.name, "Custas iniciais", 350)["name"]
		c2 = pc.nova_custa(deal.name, "Cópias", 50, reembolsavel=0)["name"]
		r = pc.resumo(deal.name)
		ck("custa marcada para cobrar do cliente aparece como a descontar", r["totais"]["custas_a_descontar"] == 350, str(r["totais"]))

		rec = pc.salvar_recebimento({
			"deal": deal.name, "data": nowdate(), "origem": "Alvará judicial", "valor_bruto": 48000,
			"parceiros": [{"parceiro": "Dr. Correspondente", "oab": "PE 12345", "percentual": 20}],
		})
		d = frappe.get_doc("CRM Recebimento", rec["name"])
		ck("usa o percentual do caso quando não informado", d.percentual_honorarios == 30)
		ck("honorário = 30% de 48.000 = 14.400", d.valor_honorarios == 14400, str(d.valor_honorarios))
		ck("desconta só a custa marcada (350)", d.despesas_reembolsadas == 350, str(d.despesas_reembolsadas))
		ck("repasse = 48.000 - 14.400 - 350 = 33.250", d.valor_repasse == 33250, str(d.valor_repasse))
		ck("correspondente fica com 20% dos honorários (2.880)", d.valor_parceiros == 2880, str(d.valor_parceiros))
		h = frappe.db.get_value("CRM Honorario", d.honorario, ["tipo_honorario", "status", "valor", "repasse"], as_dict=True)
		ck("gera o honorário de êxito pago no Financeiro", h and h.tipo_honorario == "Êxito" and h.status == "Pago" and h.valor == 14400, str(h))
		ck("custa descontada fica presa ao recebimento",
		   frappe.db.get_value("CRM Despesa", c1, ["recebimento", "reembolsado"]) == (d.name, 1))
		ck("custa não marcada continua fora", not frappe.db.get_value("CRM Despesa", c2, "recebimento"))

		erro = None
		try:
			pc.marcar_reembolsavel(c1, 0)
		except frappe.ValidationError as e:
			erro = str(e)
		ck("não deixa desmarcar custa já descontada", bool(erro))

		pc.salvar_recebimento({"name": d.name, "percentual_honorarios": 20})
		d.reload()
		ck("mudar o percentual recalcula honorário e repasse", d.valor_honorarios == 9600 and d.valor_repasse == 38050, str((d.valor_honorarios, d.valor_repasse)))
		ck("e atualiza o honorário no Financeiro", frappe.db.get_value("CRM Honorario", d.honorario, "valor") == 9600)
		ck("e a parte do correspondente (20% de 9.600)", d.valor_parceiros == 1920, str(d.valor_parceiros))

		c3 = pc.nova_custa(deal.name, "Perícia", 500)["name"]
		erro = None
		try:
			pc.salvar_recebimento({"deal": deal.name, "valor_bruto": 100, "percentual_honorarios": 90})
		except frappe.ValidationError as e:
			erro = str(e)
		ck("recusa quando honorários e custas passam do valor recebido", bool(erro) and "passam do valor" in erro)
		frappe.delete_doc("CRM Despesa", c3, force=True, ignore_permissions=True)

		pc.marcar_repasse(d.name, forma="PIX")
		r = pc.resumo(deal.name)
		ck("repasse marcado entra como repassado", r["totais"]["repassado"] == 38050 and r["totais"]["a_repassar"] == 0, str(r["totais"]))

		pdf = pc.demonstrativo_pdf(deal.name)
		ck("gera o demonstrativo em PDF", pdf["pdf"][:4] == "JVBE" and pdf["nome"].endswith(".pdf"))
		md = pc._markdown_demonstrativo(deal.name)
		ck("demonstrativo mostra valor recebido, honorários, custas e líquido",
		   all(t in md for t in ("R$ 48.000,00", "R$ 9.600,00", "R$ 350,00", "R$ 38.050,00")))

		cl = pc.carne_leao(nowdate()[:7])
		minha = [x for x in cl["linhas"] if x["cliente"] == "Teste Prestação Contas"]
		ck("carnê-leão traz o honorário recebido de pessoa física no mês", minha and minha[0]["valor"] == 9600, str(minha))
		pl = pc.carne_leao_planilha(nowdate()[:7])
		ck("carnê-leão em planilha", pl["nome"].endswith(".xlsx") and len(pl["arquivo"]) > 100)

		hon = d.honorario
		pc.excluir_recebimento(d.name)
		ck("excluir o recebimento apaga o honorário gerado", not frappe.db.exists("CRM Honorario", hon))
		ck("e devolve a custa para 'a descontar'", not frappe.db.get_value("CRM Despesa", c1, "recebimento"))
	finally:
		frappe.set_user("Administrator")
		for r in frappe.get_all("CRM Recebimento", filters={"deal": deal.name}, pluck="name"):
			frappe.delete_doc("CRM Recebimento", r, force=True, ignore_permissions=True)
		frappe.db.delete("CRM Honorario", {"deal": deal.name})
		frappe.db.delete("CRM Despesa", {"deal": deal.name})
		frappe.delete_doc("CRM Deal", deal.name, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res
