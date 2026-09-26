"""Teste de fumaça: assistente do Claude fixo no CRM (painel geral, com contexto
da tela atual e pedido de atendimento humano). A chamada real à API do Claude é
substituída por um stub. Roda no site atual
(bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from unittest import mock

import frappe

from crm.api import assistente as asst


def run():
	frappe.set_user("Administrator")
	res = []
	made = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	# limpa qualquer conversa anterior do Administrator pra não herdar estado de outro teste/uso
	if frappe.db.exists("CRM Assistente Conversa", "Administrator"):
		frappe.delete_doc("CRM Assistente Conversa", "Administrator", force=True, ignore_permissions=True)

	settings = frappe.get_single("FCRM Settings")
	chave_original = settings.get_password("claude_api_key", raise_exception=False)
	try:
		# _resumo_registro: com registro válido, com permissão
		lead = frappe.get_doc({
			"doctype": "CRM Lead", "first_name": "Zz Assistente", "last_name": "Teste",
			"email": "zz.assistente@example.com", "lead_owner": "Administrator",
		}).insert(ignore_permissions=True)
		made.append(("CRM Lead", lead.name))

		resumo = asst._resumo_registro("CRM Lead", lead.name)
		ck("resumo do registro traz o nome do lead", "Zz Assistente" in resumo)

		resumo_vazio = asst._resumo_registro("CRM Lead", "não-existe-xyz")
		ck("registro inexistente não quebra, devolve vazio", resumo_vazio == "")

		resumo_sem_doctype = asst._resumo_registro("", "")
		ck("sem doctype/registro não quebra, devolve vazio", resumo_sem_doctype == "")

		# sem chave: recusa com mensagem clara
		settings.claude_api_key = ""
		settings.save()
		erro_sem_chave = None
		try:
			asst.enviar_mensagem(mensagem="oi", tela="Dashboard")
		except frappe.ValidationError as e:
			erro_sem_chave = str(e)
		ck("sem chave configurada, recusa com mensagem clara", erro_sem_chave and "chave" in erro_sem_chave.lower())

		# com chave (fake) e _call_claude substituído
		settings.claude_api_key = "sk-ant-teste-fake"
		settings.save()

		with mock.patch.object(asst, "_call_claude", side_effect=["Isso é um lead novo, ainda sem negócio.", "Beleza, qualquer coisa chama."]):
			r1 = asst.enviar_mensagem(
				mensagem="quem é esse lead?", tela="Lead", doctype="CRM Lead", registro=lead.name,
			)
			ck("1ª mensagem responde com o texto do stub", r1["resposta"] == "Isso é um lead novo, ainda sem negócio.")

			r2 = asst.enviar_mensagem(mensagem="valeu", tela="Lead", doctype="CRM Lead", registro=lead.name)
			ck("2ª mensagem continua a mesma conversa", r2["resposta"] == "Beleza, qualquer coisa chama.")

		hist = asst.obter_historico()
		ck("histórico acumula as 4 mensagens (2 turnos)", len(hist["mensagens"]) == 4)

		asst.nova_conversa()
		hist_depois = asst.obter_historico()
		ck("nova_conversa zera o histórico", hist_depois["mensagens"] == [])

		# solicitar_atendimento: cria atribuição pro(s) gerente(s). No ambiente de teste só o
		# Administrator tem papel de gerente, e ele é propositalmente excluído dos atribuídos
		# (é conta de sistema, não pessoa real) — então criamos um gerente de teste de verdade.
		gerente_teste = frappe.get_doc({
			"doctype": "User", "email": "zz.gerente.assistente@example.com", "first_name": "Zz Gerente",
			"send_welcome_email": 0, "roles": [{"role": "Sales Manager"}],
		}).insert(ignore_permissions=True)
		made.append(("User", gerente_teste.name))

		with mock.patch.object(asst, "_call_claude", return_value="ok"):
			asst.enviar_mensagem(mensagem="preciso de ajuda com uma configuração", tela="Financeiro")
		antes = frappe.db.count("ToDo", {"reference_type": "CRM Assistente Conversa", "reference_name": "Administrator"})
		asst.solicitar_atendimento(mensagem="não consigo configurar o InfinitePay")
		depois = frappe.db.count("ToDo", {"reference_type": "CRM Assistente Conversa", "reference_name": "Administrator"})
		ck("solicitar_atendimento cria pelo menos uma atribuição nova", depois > antes)
		ck(
			"a atribuição vai pro gerente de teste, não pro Administrator",
			frappe.db.exists("ToDo", {"reference_type": "CRM Assistente Conversa", "reference_name": "Administrator", "allocated_to": gerente_teste.name}),
		)
	finally:
		for todo in frappe.get_all("ToDo", filters={"reference_type": "CRM Assistente Conversa", "reference_name": "Administrator"}, pluck="name"):
			frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
		if frappe.db.exists("CRM Assistente Conversa", "Administrator"):
			frappe.delete_doc("CRM Assistente Conversa", "Administrator", force=True, ignore_permissions=True)
		for dt, name in reversed(made):
			frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
		settings.claude_api_key = chave_original or ""
		settings.save()
		frappe.db.commit()

	return res
