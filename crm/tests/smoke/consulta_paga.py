"""Teste de fumaça: consulta paga no agendamento online + confirmação/desmarcação pelo e-mail."""

import json
from unittest.mock import patch

import frappe

from crm.api import agenda
from crm.api import automacoes as au
from crm.api import pagamento


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	feitos = []
	try:
		au.save_settings(json.dumps({"agenda_ativa": 1, "agenda_responsavel": "Administrator", "agenda_valor_consulta": 150}))
		info = agenda.get_public_info()
		ck("página de agendamento mostra o valor da consulta", info["valor"] == 150)
		dia = next(d for d in info["dias"] if len(d["horarios"]) >= 2)
		frappe.local.request_ip = "127.0.0.21"
		with patch("crm.api.pagamento.link_avulso", return_value="https://pagar.exemplo/consulta") as m:
			r = agenda.book("Zz Consulta Paga", "zz.consulta.paga@example.com", "(87) 98888-1212", dia["data"], dia["horarios"][0], "")
		reu = frappe.get_doc("CRM Reuniao", {"email": "zz.consulta.paga@example.com"})
		feitos.append(reu)
		ck("agendar consulta paga devolve o link de pagamento", r["pagamento"] == "https://pagar.exemplo/consulta" and r["valor"] == 150)
		ck("link é gerado com o código da consulta", m.call_args.args[0] == f"REU-{reu.name}" and m.call_args.args[1] == 150)
		ck("consulta guarda valor, link e código dos botões do e-mail", reu.valor == 150 and reu.link_pagamento and reu.token)

		ck("pagamento confirmado pelo InfinitePay marca a consulta como paga",
		   pagamento._aplicar_pagamento({"order_nsu": f"REU-{reu.name}", "amount": 15000, "paid_amount": 15000})["ok"]
		   and frappe.db.get_value("CRM Reuniao", reu.name, "pago") == 1)

		frappe.set_user("Guest")
		c = agenda.responder_presenca(reu.token, "confirmar")
		frappe.set_user("Administrator")
		ck("cliente confirma presença pelo botão do e-mail", c["status"] == "confirmada" and frappe.db.get_value("CRM Reuniao", reu.name, "confirmada") == 1)

		frappe.local.request_ip = "127.0.0.22"
		with patch("crm.api.pagamento.link_avulso", return_value=""):
			agenda.book("Zz Desmarca", "zz.desmarca@example.com", "(87) 98888-3434", dia["data"], dia["horarios"][1], "")
		reu2 = frappe.get_doc("CRM Reuniao", {"email": "zz.desmarca@example.com"})
		feitos.append(reu2)
		frappe.set_user("Guest")
		c = agenda.responder_presenca(reu2.token, "cancelar")
		frappe.set_user("Administrator")
		ck("cliente desmarca pelo botão do e-mail", c["status"] == "cancelada" and frappe.db.get_value("CRM Reuniao", reu2.name, "status") == "Cancelada")
		livres = next(d for d in agenda.get_public_info()["dias"] if d["data"] == dia["data"])["horarios"]
		ck("horário desmarcado volta a ficar livre", dia["horarios"][1] in livres)

		au.save_settings(json.dumps({"agenda_valor_consulta": 0}))
		ck("sem valor, a consulta é gratuita (sem link)", agenda._link_da_consulta(frappe._dict(name="x", valor=0, nome="y"), au.get_config()) == "")
	finally:
		frappe.set_user("Administrator")
		for r in feitos:
			frappe.db.delete("CRM Task", {"reference_docname": r.lead})
			frappe.db.delete("Event", {"subject": ["like", f"%{r.nome}"]})
			frappe.delete_doc("CRM Reuniao", r.name, force=True, ignore_permissions=True)
			if r.lead and frappe.db.exists("CRM Lead", r.lead):
				frappe.delete_doc("CRM Lead", r.lead, force=True, ignore_permissions=True)
		au.save_settings(json.dumps({"agenda_valor_consulta": 0, "agenda_ativa": 0}))
		frappe.db.commit()
	return res
