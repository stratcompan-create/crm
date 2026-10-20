"""Teste de fumaça: inteligência (crm.api.inteligencia) — modelos de área, rentabilidade,
comunicados e tabela de honorários. Apaga tudo no fim."""

import frappe
from frappe.utils import add_days, nowdate

from crm.api import inteligencia as it

AREA = "Área Teste Inteligência"


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	criados, itens = [], []
	try:
		it.salvar_area({"area": AREA, "documentos": "RG\nLaudo médico\n- Extrato do INSS", "perguntas": "Qual benefício?\nQuando pediu?",
						"tipo_honorario": "Êxito", "percentual_exito": 25})
		m = it.modelo_da_area(AREA)
		ck("modelo de área guarda documentos e perguntas (um por linha)", m and m["documentos"] == ["RG", "Laudo médico", "Extrato do INSS"] and len(m["perguntas"]) == 2, str(m))
		ck("salvar área cria o serviço correspondente", frappe.db.exists("CRM Servico", AREA))

		d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": "Cliente", "last_name": "Inteligencia Teste",
							"lead_name": "Cliente Inteligencia Teste", "servico": AREA})
		d.flags.sem_cobranca_automatica = True
		d.insert(ignore_permissions=True)
		criados.append(d.name)
		ck("caso novo recebe o êxito padrão da área", frappe.db.get_value("CRM Deal", d.name, "percentual_exito") == 25)
		from crm.api.clientes import _default_items

		sug = _default_items(d.name)
		ck("pedido de documentos sugere os documentos da área", "Laudo médico" in sug and "Extrato do INSS" in sug, str(sug))
		ck("perguntas da área aparecem para o caso", it.perguntas_do_caso("CRM Deal", d.name) == ["Qual benefício?", "Quando pediu?"])

		frappe.get_doc({"doctype": "CRM Honorario", "deal": d.name, "status": "Pago", "tipo_honorario": "Êxito", "valor": 10000,
						"data_vencimento": nowdate(), "data_pagamento": nowdate()}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "CRM Honorario", "deal": d.name, "status": "Pendente", "tipo_honorario": "Fixo", "valor": 1000,
						"data_vencimento": add_days(nowdate(), 10)}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "CRM Despesa", "deal": d.name, "descricao": "Perícia", "valor": 1000, "status": "Pago",
						"data_vencimento": nowdate(), "categoria": "Outros"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "CRM Horas", "deal": d.name, "usuario": "Administrator", "data": nowdate(), "horas": 10,
						"frente": "Outro"}).insert(ignore_permissions=True)
		r = it.rentabilidade()
		a = next((x for x in r["areas"] if x["nome"] == AREA), None)
		ck("rentabilidade por área: recebido, custas e líquido", a and a["recebido"] == 10000 and a["custas"] == 1000 and a["liquido"] == 9000, str(a))
		ck("rentabilidade por área: a receber e R$ por hora (9.000 / 10h)", a and a["a_receber"] == 1000 and a["por_hora"] == 900, str(a))
		ck("rentabilidade por cliente", any(x["nome"] == "Cliente Inteligencia Teste" for x in r["clientes"]))

		p = it.previa_comunicado(AREA, "Ativos")
		ck("comunicado conta os clientes ativos da área", p["total"] == 1, str(p))
		lst = it.lista_comunicado(AREA, "Ativos")
		ck("comunicado: lista em planilha para avisar pelo WhatsApp", lst["nome"].endswith(".xlsx"))
		if not p["tem_conta_email"]:
			erro = None
			try:
				it.enviar_comunicado("Teste", "Olá {nome}", AREA, "Ativos")
			except frappe.ValidationError as e:
				erro = str(e)
			ck("sem e-mail de envio, explica e oferece a lista", erro and "WhatsApp" in erro)
		else:
			ck("envia o comunicado por e-mail", it.enviar_comunicado("Teste", "Olá {nome}", AREA, "Ativos")["enviados"] >= 0)

		i = it.salvar_item_tabela({"descricao": "Reclamação trabalhista teste", "area": AREA, "valor_tabela": 3000, "valor_escritorio": 3500})
		itens.append(i["name"])
		ck("tabela de honorários: busca pelo serviço", any(x["name"] == i["name"] for x in it.tabela_honorarios("trabalhista teste")))
		ck("tabela de honorários: busca pela área", any(x["name"] == i["name"] for x in it.tabela_honorarios(AREA)))
	finally:
		frappe.set_user("Administrator")
		for n in criados:
			for dt in ("CRM Honorario", "CRM Despesa", "CRM Horas"):
				frappe.db.delete(dt, {"deal": n})
			frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True)
		for n in itens:
			frappe.delete_doc("CRM Tabela Honorario", n, force=True, ignore_permissions=True)
		frappe.db.delete("CRM Comunicado", {"titulo": "Teste"})
		if frappe.db.exists("CRM Modelo Area", AREA):
			frappe.delete_doc("CRM Modelo Area", AREA, force=True, ignore_permissions=True)
		if frappe.db.exists("CRM Servico", AREA):
			frappe.delete_doc("CRM Servico", AREA, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res


def run():
	from unittest.mock import patch

	with patch("crm.provision.get_profile", return_value="escritorio"):
		return _run()
