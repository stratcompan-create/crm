# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Controle de horas por negócio - uso interno da agência. Cada lançamento é
# "quem, quanto tempo, em qual negócio, em qual frente" (Vídeo/CRM/Site/
# Tráfego/Reunião/Outro). Usado pra enxergar rentabilidade real por cliente
# (valor mensal do contrato ÷ horas gastas no período = R$/hora efetivo),
# não só faturamento - um cliente que paga pouco e consome muito tempo não
# aparece como problema olhando só o financeiro.

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import get_first_day, get_last_day, getdate, nowdate

MANAGER_ROLES = ("System Manager", "Sales Manager")


def _managers_only():
	frappe.only_for(MANAGER_ROLES)


@frappe.whitelist()
def registrar_hora(deal: str, horas: float, frente: str | None = None, data: str | None = None, observacoes: str | None = None) -> dict:
	"""Lança horas trabalhadas num negócio. Qualquer um com acesso de leitura
	ao negócio pode lançar - o lançamento fica sempre em nome de quem está
	logado (não dá pra lançar hora em nome de outra pessoa)."""
	deal_doc = frappe.get_doc("CRM Deal", deal)
	deal_doc.check_permission("read")

	doc = frappe.get_doc(
		{
			"doctype": "CRM Horas",
			"deal": deal,
			"usuario": frappe.session.user,
			"data": data or nowdate(),
			"horas": horas,
			"frente": frente or "Outro",
			"observacoes": observacoes or "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def listar_horas(deal: str) -> dict:
	"""Lista os lançamentos de um negócio, mais recente primeiro, com o total
	geral e o total só do mês corrente (pra bater com o card de rentabilidade)."""
	deal_doc = frappe.get_doc("CRM Deal", deal)
	deal_doc.check_permission("read")

	lancamentos = frappe.get_all(
		"CRM Horas",
		filters={"deal": deal},
		fields=["name", "usuario", "data", "horas", "frente", "observacoes", "owner"],
		order_by="data desc, creation desc",
	)
	eh_gestor = bool(set(frappe.get_roles()) & set(MANAGER_ROLES))
	for item in lancamentos:
		item["pode_excluir"] = item["usuario"] == frappe.session.user or eh_gestor

	inicio_mes = get_first_day(nowdate())
	fim_mes = get_last_day(nowdate())
	total_mes = sum(i["horas"] for i in lancamentos if inicio_mes <= getdate(i["data"]) <= fim_mes)
	total_geral = sum(i["horas"] for i in lancamentos)

	return {"lancamentos": lancamentos, "total_mes": total_mes, "total_geral": total_geral}


@frappe.whitelist()
def excluir_hora(name: str) -> dict:
	"""Remove um lançamento - só quem lançou (ou gestor) pode apagar."""
	doc = frappe.get_doc("CRM Horas", name)
	eh_gestor = bool(set(frappe.get_roles()) & set(MANAGER_ROLES))
	if doc.usuario != frappe.session.user and not eh_gestor:
		frappe.throw(_("Você só pode excluir lançamentos que você mesmo fez."))
	doc.delete(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def rentabilidade_clientes(from_date: str | None = None, to_date: str | None = None) -> dict:
	"""Pra cada negócio ganho com mensalidade (recorrente), soma as horas
	lançadas no período e calcula o R$/hora efetivo (mensalidade ÷ horas).
	Devolve dois grupos: os piores R$/hora (ordenado do pior pro melhor, pra
	chamar atenção pra quem está consumindo tempo demais pelo que paga) e os
	que não tiveram nenhuma hora lançada no período (sem dado pra calcular)."""
	_managers_only()

	from_date = from_date or get_first_day(nowdate())
	to_date = to_date or get_last_day(nowdate())

	deals = frappe.get_all(
		"CRM Deal",
		filters={
			"status": "Won",
			"natureza": ["in", ["Recorrente", "Pontual e recorrente"]],
			"valor_recorrente": [">", 0],
		},
		fields=["name", "organization_name", "valor_recorrente"],
	)
	if not deals:
		return {"piores": [], "sem_registro": []}

	CRMHoras = DocType("CRM Horas")
	nomes = [d.name for d in deals]
	horas_por_deal = (
		frappe.qb.from_(CRMHoras)
		.select(CRMHoras.deal, Sum(CRMHoras.horas).as_("total_horas"))
		.where(CRMHoras.deal.isin(nomes))
		.where(CRMHoras.data.between(getdate(from_date), getdate(to_date)))
		.groupby(CRMHoras.deal)
		.run(as_dict=True)
	)
	horas_map = {r.deal: r.total_horas or 0 for r in horas_por_deal}

	piores, sem_registro = [], []
	for d in deals:
		horas = horas_map.get(d.name, 0)
		cliente = d.organization_name or d.name
		if horas > 0:
			piores.append(
				{
					"deal": d.name,
					"cliente": cliente,
					"valor_recorrente": d.valor_recorrente,
					"horas": horas,
					"efetivo": d.valor_recorrente / horas,
				}
			)
		else:
			sem_registro.append({"deal": d.name, "cliente": cliente, "valor_recorrente": d.valor_recorrente})

	piores.sort(key=lambda x: x["efetivo"])
	return {"piores": piores[:8], "sem_registro": sem_registro[:8]}
