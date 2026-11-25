"""Teste de fumaça: triagem no WhatsApp (perguntas fixas, atendimento criado, IA só por dentro, equipe assume)."""

import json
from unittest.mock import patch

import frappe
from frappe.utils import cint

from crm.api import automacoes as au
from crm.api import triagem_whatsapp as tw

TEL = "5587999990001"
TEL2 = "5587999990002"
TEL3 = "5587999990003"
TEL4 = "5587999990004"


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
			ck("apresentação e 1ª pergunta saem em duas mensagens, pela API oficial",
			   len(enviados) == 2 and "orientação jurídica" in enviados[0]["message"]
			   and enviados[0]["reference_docname"] == t.lead and enviados[1]["message"] == tw._perguntas(au.get_config())[0])

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

		# ---- agência: todo contato novo entra, e a trava por palavra é opcional
		with patch("crm.provision.get_profile", return_value="agencia"), \
			 patch("crm.api.triagem_whatsapp._motor", return_value="ycloud"), \
			 patch("crm.api.ycloud.enviar_texto", side_effect=lambda telefone, message: enviados.append({"message": message})):
			cfg = au.get_config()
			perg = tw._perguntas(cfg)
			ck("na agência as perguntas de fábrica são as do funil da agência", "escritório" in " ".join(perg[:2]).lower())
			ck("de fábrica não há palavra combinada (o robô atende todo mundo)", tw._palavras_chave(cfg) == [])

			# o WhatsApp já diz o nome: a 1ª pergunta é pulada e o nome entra nas frases
			ck("primeiro nome sai do nome do perfil", tw._primeiro_nome("Maria Clara Souza") == "Maria")
			ck("nome de fábrica não conta como nome", tw._primeiro_nome("WhatsApp 4412") == "")
			ck("com nome conhecido a frase é personalizada",
			   tw._com_nome("Então, {nome}, qual é o nome do seu escritório?", "Maria Clara")
			   == "Então, Maria, qual é o nome do seu escritório?")
			ck("sem nome conhecido a frase continua natural",
			   tw._com_nome("Então, {nome}, qual é o nome do seu escritório?", "")
			   == "Então, qual é o nome do seu escritório?")

			antes = len(enviados)
			tw._processar(Msg({"from": TEL3, "message": "Oi, tudo bem?", "reference_doctype": None, "reference_docname": None}))
			t3 = frappe.get_doc("CRM Triagem", {"telefone": TEL3})
			leads.append(t3.lead)
			ck("sem palavra configurada, qualquer contato novo entra na triagem",
			   len(enviados) == antes + 2 and "Stratcompany" in enviados[-2]["message"])
			ck("sem nome no perfil, a triagem começa perguntando o nome",
			   cint(t3.etapa) == 0 and "como você se chama" in enviados[-1]["message"].lower())

			# quando o WhatsApp identifica a pessoa, a pergunta do nome é pulada
			with patch("crm.api.triagem_whatsapp._nome_do_perfil", return_value="Maria Clara Souza"):
				antes = len(enviados)
				tw._processar(Msg({"from": TEL4, "message": "Oi, vi o vídeo de vocês", "reference_doctype": None, "reference_docname": None}))
				t4 = frappe.get_doc("CRM Triagem", {"telefone": TEL4})
				leads.append(t4.lead)
				ck("com nome no perfil, pula a pergunta do nome e já chama pelo nome",
				   len(enviados) == antes + 2 and cint(t4.etapa) == 1 and "Maria" in enviados[-1]["message"]
				   and "como você se chama" not in enviados[-1]["message"].lower(),
				   enviados[-1]["message"][-70:])
				ck("a apresentação também chama a pessoa pelo nome",
				   "Oi, Maria" in enviados[-2]["message"], enviados[-2]["message"][:40])
				ck("a apresentação não termina em pergunta (senão vem 'perfeito' no lugar da resposta)",
				   not enviados[-2]["message"].rstrip().endswith("?"), enviados[-2]["message"][-30:])

				# gentileza não é resposta: a conversa não pode andar com "perfeito"
				with patch("crm.api.ficha._api_key", return_value=None):
					antes = len(enviados)
					tw._processar(Msg({"from": TEL4, "message": "Perfeito", "reference_doctype": "CRM Lead", "reference_docname": t4.lead}))
					t4.reload()
					ck("'Perfeito' não avança a conversa e a pergunta volta",
					   cint(t4.etapa) == 1 and len(enviados) == antes + 1
					   and "registrar certinho" in enviados[-1]["message"],
					   enviados[-1]["message"][:50])

					tw._processar(Msg({"from": TEL4, "message": "Oliveira Advocacia", "reference_doctype": "CRM Lead", "reference_docname": t4.lead}))
					t4.reload()
					ck("resposta de verdade avança para a próxima pergunta", cint(t4.etapa) == 2)
					ck("o 'perfeito' não entra no resumo que vai para a equipe",
					   "Perfeito" not in tw._texto_respostas(t4))

			# quem quiser limitar escreve as palavras em Configurações
			com_trava = frappe._dict(dict(cfg, triagem_palavra_chave="DEMO, CRM"))
			ck("com palavra configurada, quem não escreve a palavra não é abordado",
			   not tw._pode_iniciar("Oi, tudo bem?", com_trava))
			ck("com palavra configurada, quem escreve a palavra é abordado",
			   tw._pode_iniciar("vi o vídeo, quero a DEMO", com_trava))

			# resposta do dono pelo próprio celular encerra o robô naquela conversa
			tw.ao_receber_ycloud(frappe._dict(direction="Sent", contato=TEL3, lead=t3.lead, pelo_celular=1))
			ck("resposta pelo celular para o robô", frappe.db.get_value("CRM Triagem", t3.name, "status") == "Assumida pela equipe")

		with patch("crm.provision.get_profile", return_value="agencia"), patch("frappe.enqueue") as fila:
			with patch("crm.api.triagem_whatsapp._cfg", return_value=frappe._dict(triagem_ativa=0)):
				tw.ao_receber_ycloud(frappe._dict(direction="Received", contato=TEL3, name="x", lead=None))
				ck("com a triagem desligada, nada é enfileirado", not fila.called)
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
