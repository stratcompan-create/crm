"""Teste de fumaça: WhatsApp pela YCloud (coexistência).

Mensagem recebida, eco do celular, status, ligação com lead pelo telefone (com e sem o 9),
contato pessoal, criar lead, envio (com a API simulada) e assinatura do webhook.
Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all). Limpa no fim.
"""

import hashlib
import hmac
import random
import uuid

import frappe

from crm.api import ycloud as yc

U = uuid.uuid4().hex[:6]


class _Resp:
	def __init__(self, ok, dados):
		self.ok, self._dados, self.status_code, self.text = ok, dados, 200 if ok else 400, str(dados)

	def json(self):
		return self._dados


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(nome, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", nome, extra)

	oito = f"{random.randint(10000000, 99999999)}"
	tel_lead = f"55749{oito}"  # com o 9
	tel_sem9 = f"5574{oito}"  # mesmo celular, sem o 9
	tel_novo = f"55879{random.randint(10000000, 99999999)}"
	leads, contatos = [], [tel_lead, tel_sem9, tel_novo]
	conf_antiga = {k: frappe.local.conf.get(k) for k in ("ycloud_api_key", "ycloud_numero")}
	post_antigo = yc.requests.post
	try:
		# telefones
		ck("mesmo celular com e sem 9", yc._mesmo_telefone("5574988335930", "557488335930"))
		ck("máscara e sem 55", yc._mesmo_telefone("(74) 98833-5930", "+55 74 98833-5930"))
		ck("números diferentes", not yc._mesmo_telefone("5574988335930", "5574988335931"))

		lead = frappe.get_doc(
			{"doctype": "CRM Lead", "first_name": "Zz Whats", "last_name": U, "mobile_no": f"(74) 9{oito[:4]}-{oito[4:]}"}
		).insert(ignore_permissions=True)
		leads.append(lead.name)

		# recebida de quem já é lead (WhatsApp manda sem o 9)
		yc.receber(
			{
				"id": "Y1" + U, "wamid": "W1" + U, "from": "+" + tel_sem9, "to": "+557488335930",
				"type": "text", "text": {"body": "Oi, quero um orçamento"},
				"customerProfile": {"name": "Cliente Teste"}, "sendTime": "2026-11-02T12:00:00.000Z",
			}
		)
		c = frappe.db.get_value(yc.CONTATO, tel_sem9, ["lead", "nao_lidas", "ultima_mensagem", "nome"], as_dict=True)
		ck("contato ligado ao lead pelo telefone (sem o 9)", c and c.lead == lead.name, str(c))
		ck("não lidas = 1 e resumo da última", c and c.nao_lidas == 1 and "orçamento" in (c.ultima_mensagem or ""))
		msg = frappe.db.get_value(yc.MENSAGEM, {"wamid": "W1" + U}, ["direction", "lead", "message"], as_dict=True)
		ck("mensagem gravada como recebida e com lead", msg and msg.direction == "Received" and msg.lead == lead.name)

		yc.receber({"id": "Y1" + U, "wamid": "W1" + U, "from": "+" + tel_sem9, "type": "text", "text": {"body": "x"}})
		ck("mesma mensagem não duplica", frappe.db.count(yc.MENSAGEM, {"contato": tel_sem9}) == 1)

		# eco: o dono respondeu pelo celular
		yc.eco_do_celular(
			{"id": "Y2" + U, "wamid": "W2" + U, "from": "+557488335930", "to": "+" + tel_sem9,
			 "type": "text", "text": {"body": "Claro! Te mando agora"}, "status": "sent"}
		)
		eco = frappe.db.get_value(yc.MENSAGEM, {"wamid": "W2" + U}, ["direction", "pelo_celular"], as_dict=True)
		ck("resposta pelo celular aparece como enviada", eco and eco.direction == "Sent" and eco.pelo_celular == 1)

		yc.atualizar_status({"id": "Y2" + U, "status": "read"})
		ck("status atualizado para lida", frappe.db.get_value(yc.MENSAGEM, {"ycloud_id": "Y2" + U}, "status") == "read")

		# mídia sem link não quebra
		yc.receber({"id": "Y3" + U, "wamid": "W3" + U, "from": "+" + tel_sem9, "type": "audio", "audio": {"id": "m1"}})
		ck("áudio sem link vira mensagem com rótulo", frappe.db.get_value(yc.MENSAGEM, {"wamid": "W3" + U}, "message") == "🎤 Áudio")

		# número desconhecido: não vira lead sozinho
		antes = frappe.db.count("CRM Lead")
		yc.receber({"id": "Y4" + U, "wamid": "W4" + U, "from": "+" + tel_novo, "type": "text", "text": {"body": "Oi"},
					"customerProfile": {"name": "Maria Nova"}})
		ck("número novo não cria lead sozinho", frappe.db.count("CRM Lead") == antes and not frappe.db.get_value(yc.CONTATO, tel_novo, "lead"))

		conversas = yc.get_conversations()
		ck("caixa de entrada lista as duas conversas", {tel_sem9, tel_novo} <= {x.telefone for x in conversas})
		ck("título usa o nome do lead", next(x for x in conversas if x.telefone == tel_sem9).titulo.startswith("Zz Whats"))

		yc.get_messages(tel_sem9)
		ck("abrir a conversa zera as não lidas", frappe.db.get_value(yc.CONTATO, tel_sem9, "nao_lidas") == 0)

		# pessoal
		yc.marcar_pessoal(tel_novo, 1)
		ck("pessoal some da caixa de entrada", tel_novo not in {x.telefone for x in yc.get_conversations()})
		ck("pessoal aparece no filtro de pessoais", tel_novo in {x.telefone for x in yc.get_conversations(pessoais=1)})
		yc.marcar_pessoal(tel_novo, 0)

		# criar lead
		novo = yc.criar_lead(tel_novo)
		leads.append(novo)
		ld = frappe.db.get_value("CRM Lead", novo, ["first_name", "mobile_no", "source"], as_dict=True)
		ck("criar lead usa nome e telefone do WhatsApp", ld.first_name == "Maria" and ld.mobile_no == "+" + tel_novo and ld.source == "WhatsApp")
		ck("mensagens antigas ganham o lead", frappe.db.get_value(yc.MENSAGEM, {"wamid": "W4" + U}, "lead") == novo)

		# envio (API simulada)
		frappe.local.conf["ycloud_api_key"] = "teste"
		frappe.local.conf["ycloud_numero"] = "+557488335930"
		enviado = {}

		def falso_ok(url, headers=None, json=None, timeout=None):
			enviado.update(json or {})
			return _Resp(True, {"id": "Y5" + U, "status": "accepted", "type": "text"})

		yc.requests.post = falso_ok
		yc.send_message(tel_sem9, "Segue o orçamento")
		ck("envio manda para o número certo", enviado.get("to") == "+" + tel_sem9 and enviado.get("from") == "+557488335930")
		ck("envio fica gravado na conversa", frappe.db.get_value(yc.MENSAGEM, {"ycloud_id": "Y5" + U}, "direction") == "Sent")

		yc.requests.post = lambda *a, **k: _Resp(False, {"error": {"code": "131047", "message": "Re-engagement message"}})
		try:
			yc.send_message(tel_sem9, "Oi de novo")
			ck("fora de 24h dá erro", False)
		except frappe.ValidationError as e:
			ck("fora de 24h explica a regra da Meta", "24 horas" in str(e))

		# assinatura do webhook
		corpo = b'{"id":"evt_1","type":"whatsapp.message.updated"}'
		assinatura = hmac.new(b"segredo", b"1700000000." + corpo, hashlib.sha256).hexdigest()
		ck("assinatura válida aceita", yc._assinatura_valida(corpo, f"t=1700000000,s={assinatura}", "segredo"))
		ck("corpo alterado recusado", not yc._assinatura_valida(corpo + b" ", f"t=1700000000,s={assinatura}", "segredo"))
		ck("sem cabeçalho recusado", not yc._assinatura_valida(corpo, None, "segredo"))
	finally:
		yc.requests.post = post_antigo
		for k, v in conf_antiga.items():
			if v is None:
				frappe.local.conf.pop(k, None)
			else:
				frappe.local.conf[k] = v
		for tel in contatos:
			for m in frappe.get_all(yc.MENSAGEM, filters={"contato": tel}, pluck="name"):
				frappe.delete_doc(yc.MENSAGEM, m, ignore_permissions=True, force=True)
			if frappe.db.exists(yc.CONTATO, tel):
				frappe.delete_doc(yc.CONTATO, tel, ignore_permissions=True, force=True)
		for lead in leads:
			if frappe.db.exists("CRM Lead", lead):
				frappe.delete_doc("CRM Lead", lead, ignore_permissions=True, force=True)
		frappe.db.commit()
	return res
