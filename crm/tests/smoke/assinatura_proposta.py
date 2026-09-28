"""Teste de fumaça: assinatura eletrônica da proposta (link público, token, e o
negócio virando Ganho quando assinado).

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Cria dados de teste e limpa no fim.
"""

import uuid

import frappe

from crm.api import proposta as pp

U = uuid.uuid4().hex[:6]


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(n, c, e=""):
		res.append(bool(c))
		print("OK  " if c else "FAIL", n, e)

	made = []
	try:
		lead = frappe.get_doc(
			{"doctype": "CRM Lead", "first_name": "Zz Assinatura", "last_name": "Teste" + U}
		).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))
		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"first_name": "Zz Assinatura",
				"last_name": "Teste" + U,
				"lead": lead.name,
				"deal_owner": "Administrator",
				"status": "Proposal/Quotation",
			}
		).insert(ignore_permissions=True)
		made.append(("CRM Deal", deal.name))

		# token: gerado na primeira chamada, reaproveitado depois
		link1 = pp._link_assinatura(deal.name)
		link2 = pp._link_assinatura(deal.name)
		ck("link de assinatura é gerado e reaproveitado", link1 and link1 == link2 and "/assinatura?t=" in link1)

		token = frappe.db.get_value("CRM Deal", deal.name, "proposta_token")

		# token inválido não acha nada
		ck("token errado não acha o negócio", pp._deal_by_token("token-que-nao-existe" + U) is None)
		ck("token vazio não acha o negócio", pp._deal_by_token("") is None)

		# tela pública antes de assinar
		pub = pp.get_public_signature(token)
		ck("tela pública mostra o cliente e ainda não assinada", pub["cliente"] == deal.name and pub["assinada"] is False)

		# validações
		erro_nome = None
		try:
			pp.assinar_proposta(token, nome="SóUmNome", documento="12345678900", email="a@b.com")
		except frappe.ValidationError as e:
			erro_nome = str(e)
		ck("recusa nome sem sobrenome", bool(erro_nome))

		erro_doc = None
		try:
			pp.assinar_proposta(token, nome="Fulano de Tal", documento="123", email="a@b.com")
		except frappe.ValidationError as e:
			erro_doc = str(e)
		ck("recusa CPF/CNPJ inválido", bool(erro_doc))

		erro_email = None
		try:
			pp.assinar_proposta(token, nome="Fulano de Tal", documento="12345678900", email="nao-e-email")
		except frappe.ValidationError as e:
			erro_email = str(e)
		ck("recusa e-mail inválido", bool(erro_email))

		# assinatura válida
		r = pp.assinar_proposta(token, nome="Fulano de Tal", documento="123.456.789-00", email="fulano@teste.com")
		ck("assinatura válida retorna nome e horário", r["ok"] and r["assinante_nome"] == "Fulano de Tal" and bool(r["assinado_em"]))

		row = frappe.db.get_value(
			"CRM Deal", deal.name,
			["proposta_assinada", "assinante_nome", "assinante_documento", "assinante_email", "status"],
			as_dict=True,
		)
		ck(
			"campos gravados no negócio",
			row.proposta_assinada == 1 and row.assinante_nome == "Fulano de Tal" and row.assinante_documento == "12345678900"
			and row.assinante_email == "fulano@teste.com",
			row,
		)
		ck("negócio marcado como Ganho", row.status == "Won", row.status)

		# status via chamada autenticada (usada pelo badge na tela da proposta)
		status = pp.get_signature_status(deal.name)
		ck("get_signature_status reflete a assinatura", status["assinada"] and status["nome"] == "Fulano de Tal")

		# tela pública depois de assinar
		pub2 = pp.get_public_signature(token)
		ck("tela pública mostra assinado depois", pub2["assinada"] and pub2["assinante_nome"] == "Fulano de Tal")

		# assinar de novo (duplo clique / reenvio) não sobrescreve quem assinou primeiro
		r2 = pp.assinar_proposta(token, nome="Outra Pessoa", documento="98765432100", email="outra@teste.com")
		ck("reenvio depois de assinado não sobrescreve", r2["assinante_nome"] == "Fulano de Tal")
	finally:
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	return res
