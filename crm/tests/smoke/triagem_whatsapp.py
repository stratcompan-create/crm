"""Teste de fumaça: triagem no WhatsApp (perguntas fixas, atendimento criado, IA só por dentro, equipe assume)."""

import json
from unittest.mock import patch

import frappe

from crm.api import automacoes as au
from crm.api import triagem_whatsapp as tw

TEL = "5587999990001"
TEL2 = "5587999990002"


class Msg(frappe._dict):
	def db_set(self, valores, update_modified=True):
		self.update(valores)


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	enviados = []
	leads = []
	try:
		au.save_settings(json.dumps({"triagem_ativa": 1, "triagem_responsavel": "Administrator"}))
		with patch("crm.provision.get_profile", return_value="escritorio"), \
			 patch("whatsapp.whatsapp.api.messages.send_message", side_effect=lambda **k: enviados.append(k)), \
			 patch("crm.api.triagem_whatsapp._classificar", return_value={"area": "Trabalhista", "urgencia": "Média", "resumo": "Dispensa sem registro."}):
			tw._processar(Msg({"from": TEL, "message": "Boa tarde, fui mandado embora", "reference_doctype": None, "reference_docname": None}))
			t = frappe.get_doc("CRM Triagem", {"telefone": TEL})
			leads.append(t.lead)
			ck("número desconhecido vira atendimento com origem WhatsApp", frappe.db.get_value("CRM Lead", t.lead, "source") == "WhatsApp")
			ck("boas-vindas + 1ª pergunta saem pela API oficial", len(enviados) == 1 and "orientação jurídica" in enviados[0]["message"]
			   and enviados[0]["reference_docname"] == t.lead)

			perguntas = tw._perguntas(au.get_config())
			respostas = ["Carlos Alberto Souza", "Trabalhei 4 anos sem carteira", "Não", "Petrolina"]
			for r in respostas[: len(perguntas)]:
				tw._processar(Msg({"from": TEL, "message": r, "reference_doctype": "CRM Lead", "reference_docname": t.lead}))
			t.reload()
			ck("perguntas saem uma a uma, na ordem", [e["message"] for e in enviados[1:len(perguntas)]] == perguntas[1:])
			ck("nome informado corrige o atendimento", frappe.db.get_value("CRM Lead", t.lead, "first_name") == "Carlos")
			ck("triagem concluída com área, urgência e resumo", t.status == "Concluída" and t.area == "Trabalhista" and t.urgencia == "Média")
			ck("resumo vira nota no atendimento", frappe.db.exists("FCRM Note", {"reference_docname": t.lead, "title": "Triagem pelo WhatsApp"}))
			ck("equipe recebe a tarefa de retorno", frappe.db.exists("CRM Task", {"reference_docname": t.lead, "title": "Retornar atendimento do WhatsApp"}))

			# urgência + equipe assumindo
			tw._processar(Msg({"from": TEL2, "message": "Meu filho está preso desde ontem", "reference_doctype": None, "reference_docname": None}))
			t2 = frappe.get_doc("CRM Triagem", {"telefone": TEL2})
			leads.append(t2.lead)
			ck("palavra de urgência gera tarefa alta na hora", frappe.db.get_value("CRM Task", {"reference_docname": t2.lead}, "priority") == "High")
			tw.ao_receber(frappe._dict(direction="Outgoing", reference_doctype="CRM Lead", reference_docname=t2.lead))
			ck("quando a equipe responde, o robô para", frappe.db.get_value("CRM Triagem", t2.name, "status") == "Assumida pela equipe")

		with patch("crm.provision.get_profile", return_value="agencia"), patch("frappe.enqueue") as fila:
			tw.ao_receber(frappe._dict(direction="Incoming", name="x"))
			ck("na agência a triagem não age", not fila.called)
	finally:
		for lead in leads:
			frappe.db.delete("CRM Task", {"reference_docname": lead})
			frappe.db.delete("FCRM Note", {"reference_docname": lead})
			frappe.db.delete("CRM Triagem", {"lead": lead})
			if frappe.db.exists("CRM Lead", lead):
				frappe.delete_doc("CRM Lead", lead, force=True, ignore_permissions=True)
		au.save_settings(json.dumps({"triagem_ativa": 0, "triagem_responsavel": ""}))
		frappe.db.commit()
	return res
