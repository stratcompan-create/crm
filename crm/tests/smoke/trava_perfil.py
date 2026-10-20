"""Teste de fumaça: funções do escritório não aparecem nem agem em site de agência."""

from unittest.mock import patch

import frappe

from crm.api import inteligencia, portal, processo, pwa, seguranca


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	with patch("crm.provision.get_profile", return_value="agencia"):
		m = pwa.dados_manifesto()
		ck("agência: aplicativo continua com o nome e ícones de antes", m["name"] == "CRM" and len(m["icons"]) == 4)

		lead = frappe.new_doc("CRM Lead")
		if lead.meta.has_field("consentimento_lgpd"):
			lead.consentimento_lgpd = 1
			seguranca.carimbar_consentimento(lead)
			ck("agência: consentimento LGPD não é carimbado", not lead.get("consentimento_em"))

		with patch("crm.api.processo.verificar_conflito") as conflito:
			processo.checar_cliente_novo(frappe._dict(name="x", lead_name="Fulano"))
			ck("agência: não checa conflito de interesses", not conflito.called)

		with patch("frappe.get_all") as busca:
			portal.lembrar_documentos()
			ck("agência: não manda lembrete de documentos", not busca.called)

		deal = frappe.new_doc("CRM Deal")
		with patch("frappe.db.get_value") as area:
			inteligencia.aplicar_padrao_area(deal)
			ck("agência: não aplica modelo de área", not area.called)
	return res
