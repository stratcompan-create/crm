"""Teste de fumaça: audiência confirmada (crm.api.audiencia).

Confirma o que o escritório vende: cliente e testemunha avisados 7 dias e 1 dia antes, resposta
em um toque pelo link, e quem não respondeu até a véspera virando tarefa de ligação. Nada de
e-mail real sai daqui — o envio é simulado. Apaga tudo no fim.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime

from crm.api import audiencia as au


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(nome, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", nome, extra)

	def novo_caso(nome):
		first, _s, last = nome.partition(" ")
		d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": first,
							"last_name": last, "lead_name": nome, "email": "cliente.teste@example.com"})
		d.flags.sem_cobranca_automatica = True
		return d.insert(ignore_permissions=True)

	casos, auds = [], []
	try:
		# ---------------------------------------------------------- o que levar / o que esperar
		pres = au.orientacoes("Una", "Presencial")
		video = au.orientacoes("Una", "Videoconferência")
		ck("presencial manda chegar antes", any("30 minutos antes" in i for i in pres))
		ck("presencial cobra documento com foto", any("documento com foto" in i for i in pres))
		ck("por vídeo manda testar câmera e microfone", any("câmera" in i for i in video))
		ck("por vídeo não repete a fila do fórum", not any("fila do fórum" in i for i in video))
		ck("audiência una avisa que vai ser ouvido", any("ouvido pelo juiz" in i for i in pres))
		ck("conciliação avisa que acordo não é obrigatório",
		   any("não é obrigado a aceitar" in i for i in au.orientacoes("Conciliação", "Presencial")))
		ck("perícia pede exames e laudos",
		   any("laudos" in i for i in au.orientacoes("Perícia", "Presencial")))
		ck("toda orientação termina avisando do risco de arquivamento",
		   any("arquivado" in i for i in pres))
		ck("nenhuma orientação promete resultado",
		   not any(p in " ".join(pres).lower() for p in ("vai ganhar", "garantido", "com certeza você")))

		# ---------------------------------------------------------- criar
		caso = novo_caso("Cliente Teste Audiencia")
		casos.append(caso.name)
		frappe.get_doc({"doctype": "CRM Parte", "deal": caso.name, "tipo": "Testemunha",
						"nome": "Testemunha Um", "email": "t1@example.com"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "CRM Parte", "deal": caso.name, "tipo": "Parte contrária",
						"nome": "Banco Rival Teste"}).insert(ignore_permissions=True)

		quando = add_to_date(now_datetime(), days=10)
		r = au.criar(caso.name, str(quando), tipo="Una", modalidade="Presencial",
					 local="Forum Central, sala 3", vara="2ª Vara do Trabalho")
		auds.append(r["name"])
		det = au.obter(r["name"])
		tipos = sorted(p["tipo"] for p in det["pessoas"])
		ck("a audiência nasce com o cliente dentro", "Cliente" in tipos, str(tipos))
		ck("as testemunhas do caso entram sozinhas", "Testemunha" in tipos, str(tipos))
		ck("a parte contrária NÃO é convocada", tipos.count("Testemunha") == 1 and len(tipos) == 2, str(tipos))
		ck("todo mundo começa aguardando",
		   all(p["confirmacao"] == "Aguardando" for p in det["pessoas"]))
		ck("nasce agendada", det["status"] == "Agendada")
		ck("nenhum lembrete saiu ainda", not det["lembrete_7d"] and not det["lembrete_1d"])

		r2 = au.criar(caso.name, str(add_to_date(now_datetime(), days=12)), trazer_testemunhas=0)
		auds.append(r2["name"])
		ck("pedindo, a audiência vem sem as testemunhas",
		   len(au.obter(r2["name"])["pessoas"]) == 1)

		# ---------------------------------------------------------- resposta pelo link
		pessoas = frappe.get_all("CRM Audiencia Presenca", filters={"audiencia": r["name"]},
								 fields=["name", "tipo", "token"])
		cliente = next(p for p in pessoas if p.tipo == "Cliente")
		testemunha = next(p for p in pessoas if p.tipo == "Testemunha")

		pub = au.dados_publicos(cliente.token)
		ck("a página pública mostra quando é", bool(pub["quando"]))
		ck("a página pública traz o que levar", len(pub["orientacoes"]) > 3)
		ck("a página pública ainda não tem resposta", not pub["ja_respondeu"])

		resp = au.responder(cliente.token, "confirmar")
		ck("confirmar pelo link registra presença", resp["resposta"] == "Confirmado", str(resp))
		ck("a confirmação fica gravada",
		   frappe.db.get_value("CRM Audiencia Presenca", cliente.name, "confirmacao") == "Confirmado")
		ck("a confirmação vira histórico no caso",
		   frappe.db.count("Comment", {"reference_name": caso.name, "content": ["like", "%confirmado%"]}) >= 1)
		ck("reabrir o link mostra que já respondeu", au.dados_publicos(cliente.token)["ja_respondeu"])

		frappe.db.delete("CRM Task", {"reference_docname": caso.name})
		resp = au.responder(testemunha.token, "nao", "Vou estar viajando")
		ck("recusar pelo link registra a ausência", resp["resposta"] == "Não poderá ir")
		tarefas = frappe.get_all("CRM Task", filters={"reference_docname": caso.name}, pluck="title")
		ck("quem avisa que não vai gera tarefa na hora", len(tarefas) == 1, str(tarefas))
		ck("a tarefa diz o nome de quem não vai", tarefas and "Testemunha Um" in tarefas[0])
		ck("o motivo escrito fica guardado",
		   frappe.db.get_value("CRM Audiencia Presenca", testemunha.name,
							   "observacao_resposta") == "Vou estar viajando")

		# ---------------------------------------------------------- registro manual (por telefone)
		au.marcar_manual(testemunha.name, "Confirmado", "Confirmou por telefone")
		ck("a equipe pode registrar a confirmação feita por telefone",
		   frappe.db.get_value("CRM Audiencia Presenca", testemunha.name, "confirmacao") == "Confirmado")

		# ---------------------------------------------------------- remarcou: zera tudo
		au.atualizar(r["name"], data_hora=str(add_to_date(now_datetime(), days=20)))
		det = au.obter(r["name"])
		ck("remarcar zera as confirmações",
		   all(p["confirmacao"] == "Aguardando" for p in det["pessoas"]),
		   str([p["confirmacao"] for p in det["pessoas"]]))
		ck("remarcar zera os lembretes já enviados",
		   not det["lembrete_7d"] and not det["lembrete_1d"])

		# ---------------------------------------------------------- os lembretes
		with patch("frappe.sendmail") as envio, \
				patch("crm.api.audiencia._tem_email", return_value=True):
			# 7 dias: a audiência de 20 dias não entra, a de 5 dias entra
			longe = au.criar(caso.name, str(add_to_date(now_datetime(), days=30)))
			auds.append(longe["name"])
			perto = au.criar(caso.name, str(add_to_date(now_datetime(), days=5)))
			auds.append(perto["name"])
			envio.reset_mock()
			au.enviar_lembretes()
			ck("o aviso de 7 dias sai para a audiência de 5 dias",
			   frappe.db.get_value("CRM Audiencia", perto["name"], "lembrete_7d") == 1)
			ck("a audiência de 30 dias ainda não é avisada",
			   frappe.db.get_value("CRM Audiencia", longe["name"], "lembrete_7d") == 0)
			ck("e-mail foi disparado", envio.call_count >= 1, str(envio.call_count))
			assunto = str(envio.call_args_list[0].kwargs.get("subject", "")) if envio.call_count else ""
			ck("o assunto do aviso de 7 dias pede confirmação", "Confirme" in assunto, assunto)

			envio.reset_mock()
			au.enviar_lembretes()
			ck("rodar de novo não manda o aviso de 7 dias duas vezes", envio.call_count == 0,
			   str(envio.call_count))

			# véspera
			vespera = au.criar(caso.name, str(add_to_date(now_datetime(), hours=20)))
			auds.append(vespera["name"])
			frappe.db.delete("CRM Task", {"reference_docname": caso.name})
			envio.reset_mock()
			au.enviar_lembretes()
			ck("na véspera o aviso de 1 dia sai",
			   frappe.db.get_value("CRM Audiencia", vespera["name"], "lembrete_1d") == 1)
			assuntos = [str(c.kwargs.get("subject", "")) for c in envio.call_args_list]
			ck("o assunto da véspera avisa que é amanhã",
			   any("amanhã" in s for s in assuntos), str(assuntos))
			cobrancas = frappe.get_all("CRM Task", filters={"reference_docname": caso.name}, pluck="title")
			ck("quem não respondeu até a véspera vira tarefa de ligação",
			   any("Ligar hoje" in t for t in cobrancas), str(cobrancas))
			ck("a tarefa de cobrança sai só uma vez",
			   frappe.db.get_value("CRM Audiencia", vespera["name"], "cobranca_criada") == 1)

		# sem conta de e-mail configurada, o CRM não finge que avisou: abre tarefa
		with patch("crm.api.audiencia._tem_email", return_value=False), \
				patch("crm.api.audiencia._create_task") as tarefa:
			sem = au.criar(caso.name, str(add_to_date(now_datetime(), days=4)))
			auds.append(sem["name"])
			pid = frappe.get_all("CRM Audiencia Presenca", filters={"audiencia": sem["name"]},
								 pluck="name")[0]
			au.cobrar(pid)
			ck("sem e-mail configurado, cobrar cria tarefa de ligação", tarefa.called)

		# ---------------------------------------------------------- cancelada e passada
		au.atualizar(r2["name"], status="Cancelada")
		tok = frappe.get_all("CRM Audiencia Presenca", filters={"audiencia": r2["name"]},
							 pluck="token")[0]
		ck("link de audiência cancelada avisa o cancelamento",
		   au.responder(tok, "confirmar")["situacao"] == "cancelada")

		passada = au.criar(caso.name, str(add_to_date(now_datetime(), days=1)))
		auds.append(passada["name"])
		frappe.db.set_value("CRM Audiencia", passada["name"], "data_hora",
							add_to_date(now_datetime(), days=-2), update_modified=False)
		tok = frappe.get_all("CRM Audiencia Presenca", filters={"audiencia": passada["name"]},
							 pluck="token")[0]
		ck("link de audiência que já passou não aceita resposta",
		   au.responder(tok, "confirmar")["situacao"] == "passou")

		ck("token inventado é recusado", _recusa(lambda: au.responder("naoexiste123", "confirmar")))

		# ---------------------------------------------------------- lista e travas
		lst = au.listar()
		ck("a lista traz as audiências futuras", len(lst["audiencias"]) >= 1)
		ck("a lista conta quem falta confirmar", lst["pendentes"] >= 0)
		ck("a lista marca risco em audiência próxima com gente sem resposta",
		   any(a["risco"] for a in lst["audiencias"]))

		with patch("crm.api.audiencia._cfg", return_value=frappe._dict({"audiencia_ativo": 0})):
			ck("módulo desligado não é ativo", not au._modulo_ativo())
			ck("módulo desligado recusa a lista", _recusa(au.listar))

		with patch("crm.provision.get_profile", return_value="agencia"):
			ck("fora do perfil de escritório o módulo não existe", not au._modulo_ativo())
			ck("perfil de agência recusa a lista", _recusa(au.listar))
	finally:
		frappe.set_user("Administrator")
		# varre tambem o que nao entrou na lista (se o teste crashar no meio): audiencia
		# orfa no banco faz OUTRO teste de fumaca falhar depois
		todas = set(auds)
		for n in casos:
			todas.update(frappe.get_all("CRM Audiencia", filters={"deal": n}, pluck="name"))
		for n in todas:
			frappe.db.delete("CRM Audiencia Presenca", {"audiencia": n})
			try:
				frappe.delete_doc("CRM Audiencia", n, force=True, ignore_permissions=True,
								  delete_permanently=True)
			except Exception:
				pass
		for n in casos:
			frappe.db.delete("CRM Parte", {"deal": n})
			frappe.db.delete("CRM Task", {"reference_docname": n})
			frappe.db.delete("Comment", {"reference_name": n})
			try:
				frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True,
								  delete_permanently=True)
			except Exception:
				pass
		frappe.db.commit()
	return res


def _recusa(fn) -> bool:
	try:
		fn()
		return False
	except frappe.ValidationError:
		return True


def run():
	with patch("crm.provision.get_profile", return_value="escritorio"):
		return _run()
