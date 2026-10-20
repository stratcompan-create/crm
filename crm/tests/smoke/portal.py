"""Teste de fumaça: relação com o cliente (crm.api.portal) — portal do cliente, lembrete de
documentos, pesquisa de satisfação e ranking de indicações. Apaga tudo no fim."""

import json

import frappe
from frappe.utils import add_days, nowdate

from crm.api import portal, processo


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": "Cliente", "last_name": "Portal Teste",
						"lead_name": "Cliente Portal Teste", "indicado_por": "Contador Indicador Teste"})
	d.flags.sem_cobranca_automatica = True
	d.insert(ignore_permissions=True)
	lead = None
	try:
		link = portal.link_portal(d.name)["link"]
		token = link.split("t=")[1]
		ck("gera o link do portal", "/portal?t=" in link and len(token) > 20)
		ck("o mesmo link volta na segunda vez", portal.link_portal(d.name)["link"] == link)

		processo.adicionar_andamento(d.name, "Petição protocolada.", 1)
		processo.adicionar_andamento(d.name, "Nota interna", 0)
		frappe.get_doc({"doctype": "CRM Honorario", "deal": d.name, "status": "Atrasado", "tipo_honorario": "Fixo", "valor": 800,
						"data_vencimento": add_days(nowdate(), -3), "link_pagamento": "https://pagar.exemplo/abc"}).insert(ignore_permissions=True)
		from crm.api.clientes import create_request

		pedido = create_request(d.name, json.dumps(["RG", "Comprovante de residência"]), "", 14)
		frappe.set_user("Guest")
		p = portal.get_portal(token)
		frappe.set_user("Administrator")
		ck("portal abre sem login (só com o código)", p["nome"] and p["marca"] is not None)
		ck("cliente vê só o andamento liberado", len(p["andamentos"]) == 1 and "protocolada" in p["andamentos"][0]["texto"])
		ck("cliente vê o pagamento atrasado com o link", p["pagamentos"] and p["pagamentos"][0]["atrasado"] and p["pagamentos"][0]["link"])
		ck("cliente vê os documentos que faltam", p["documentos"] and len(p["documentos"][0]["faltando"]) == 2)
		erro = None
		try:
			portal.get_portal("codigo-errado")
		except frappe.ValidationError as e:
			erro = str(e)
		ck("código errado não abre nada", bool(erro))
		novo = portal.link_portal(d.name, novo=1)["link"]
		erro = None
		try:
			portal.get_portal(token)
		except frappe.ValidationError as e:
			erro = str(e)
		ck("trocar o link desativa o antigo", novo != link and bool(erro))

		# lembrete: pedido criado há 4 dias, sem nada enviado
		frappe.db.set_value("CRM Pedido Documentos", pedido["name"], "creation", add_days(nowdate(), -4) + " 09:00:00")
		portal.lembrar_documentos()
		v = frappe.db.get_value("CRM Pedido Documentos", pedido["name"], ["lembretes_enviados", "ultimo_lembrete"], as_dict=True)
		ck("lembra o cliente dos documentos pendentes", v.lembretes_enviados == 1 and str(v.ultimo_lembrete) == nowdate(), str(v))
		portal.lembrar_documentos()
		ck("não repete o lembrete antes de 3 dias", frappe.db.get_value("CRM Pedido Documentos", pedido["name"], "lembretes_enviados") == 1)
		tarefa = frappe.db.exists("CRM Task", {"reference_docname": d.name, "title": ["like", "%documentos pendentes%"]})
		ck("sem e-mail configurado, vira tarefa para o escritório cobrar", bool(tarefa) or frappe.db.exists("Email Account", {"enable_outgoing": 1}))

		# pesquisa ao encerrar
		processo.encerrar(d.name, "Êxito", 1, "", mesmo_com_pendencias=1)
		tk = frappe.db.get_value("CRM Pesquisa", {"deal": d.name}, "token")
		ck("encerrar o caso cria a pesquisa de satisfação", bool(tk))
		frappe.set_user("Guest")
		ck("pesquisa abre sem login", portal.get_pesquisa(tk)["respondida"] is False)
		ck("portal mostra o convite para avaliar", portal.get_portal(novo.split("t=")[1])["pesquisa"])
		portal.responder_pesquisa(tk, 9, "Muito bom", 1)
		erro = None
		try:
			portal.responder_pesquisa(tk, 3, "", 0)
		except frappe.ValidationError as e:
			erro = str(e)
		frappe.set_user("Administrator")
		ck("não deixa responder duas vezes", bool(erro))
		r = portal.resumo_pesquisas()
		ck("resumo da satisfação conta a resposta", r["respostas"] >= 1 and r["media"] > 0)

		# indicações
		lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Indicado", "last_name": "Teste Portal", "status": "New",
							   "indicado_por": "contador indicador teste"}).insert(ignore_permissions=True)
		frappe.db.set_value("CRM Honorario", {"deal": d.name}, "status", "Pago")
		rk = {r["nome"].lower(): r for r in portal.ranking_indicacoes()}
		r = rk.get("contador indicador teste")
		ck("ranking junta as indicações da mesma pessoa (maiúsculas/minúsculas)", r and r["atendimentos"] == 1 and r["casos"] == 1, str(r))
		ck("ranking soma os honorários pagos dos casos indicados", r and r["honorarios"] == 800, str(r))
	finally:
		frappe.set_user("Administrator")
		for dt in ("CRM Andamento", "CRM Honorario", "CRM Pesquisa", "CRM Pedido Documentos"):
			frappe.db.delete(dt, {"deal": d.name})
		frappe.db.delete("CRM Task", {"reference_docname": d.name})
		frappe.delete_doc("CRM Deal", d.name, force=True, ignore_permissions=True)
		if lead:
			frappe.delete_doc("CRM Lead", lead.name, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res


def run():
	from unittest.mock import patch

	with patch("crm.provision.get_profile", return_value="escritorio"):
		return _run()
