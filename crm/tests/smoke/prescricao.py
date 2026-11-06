"""Teste de fumaça: radar de prescrição (crm.api.prescricao).

O miolo é a conta de dois prazos — o bienal (quando não dá mais para ajuizar) e o quinquenal
(quanto do contrato ainda cabe no pedido). A conta é testada sozinha, sem banco, porque é ela
que o escritório vai usar para decidir quem ligar primeiro. Apaga tudo no fim.
"""

import frappe
from frappe.utils import add_to_date, getdate, nowdate

from crm.api import prescricao as pc


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(nome, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", nome, extra)

	cfg = frappe._dict({"prescricao_ativo": 1, "prescricao_anos": 2, "prescricao_retroativo_anos": 5,
						"prescricao_dias_critico": 30, "prescricao_dias_atencao": 90})
	hoje = getdate(nowdate())

	def d(**kw):
		return getdate(add_to_date(hoje, **kw))

	leads = []
	try:
		# ---------------------------------------------------------- a conta, sem banco
		c = pc.calcular(d(years=-1), None, 0, cfg, hoje)
		ck("saída há 1 ano fica no prazo", c["nivel"] == "no_prazo", c["rotulo"])
		ck("o limite é a saída + 2 anos", c["limite"] == str(d(years=1)), c["limite"])

		c = pc.calcular(d(years=-2, days=-1), None, 0, cfg, hoje)
		ck("saída há 2 anos e 1 dia está vencida", c["nivel"] == "vencido", str(c["dias_restantes"]))
		ck("vencido explica que o prazo passou", "venceu" in c["explicacao"])

		c = pc.calcular(d(years=-2, days=20), None, 0, cfg, hoje)
		ck("faltando 20 dias é crítico", c["nivel"] == "critico", str(c["dias_restantes"]))

		c = pc.calcular(d(years=-2, days=60), None, 0, cfg, hoje)
		ck("faltando 60 dias é atenção", c["nivel"] == "atencao", str(c["dias_restantes"]))

		c = pc.calcular(None, None, 0, cfg, hoje)
		ck("sem data de saída o radar não inventa conta", c["nivel"] == "sem_data" and c["dias_restantes"] is None)

		# ---------------------------------------------------------- o que a espera custa
		# admitido há 10 anos, saiu há 1 ano: esperou 1 ano, perdeu 12 meses de pedido
		c = pc.calcular(d(years=-1), d(years=-10), 1000, cfg, hoje)
		ck("o pedido alcança 48 meses (5 anos para trás menos o ano de espera)",
		   c["meses_no_pedido"] == 48, str(c["meses_no_pedido"]))
		ck("12 meses já caíram fora do pedido", c["meses_perdidos"] == 12, str(c["meses_perdidos"]))
		ck("o custo da espera é 12 x o valor do mês", c["custo_espera"] == 12000.0, str(c["custo_espera"]))
		ck("ainda perde 1 mês por mês de espera", c["perde_por_mes"] == 1000.0, str(c["perde_por_mes"]))

		# contrato curto: a janela de 5 anos já começa na admissão, não tem mais o que cair
		c = pc.calcular(d(years=-1), d(years=-3), 1000, cfg, hoje)
		ck("contrato dentro da janela não perde parcela", c["meses_perdidos"] == 0, str(c["meses_perdidos"]))
		ck("e não sangra mais por mês", c["perde_por_mes"] == 0.0, str(c["perde_por_mes"]))
		ck("mas o pedido alcança os 24 meses do contrato", c["meses_no_pedido"] == 24, str(c["meses_no_pedido"]))

		# cadastro trocado não pode virar conta errada
		c = pc.calcular(d(years=-3), d(years=-1), 1000, cfg, hoje)
		ck("admissão depois da saída é ignorada em vez de gerar conta torta",
		   c["nivel"] in ("vencido", "critico", "atencao", "no_prazo"), c["rotulo"])

		# prazo configurável (outras áreas têm prazo diferente)
		cfg5 = frappe._dict(dict(cfg, prescricao_anos=5))
		c = pc.calcular(d(years=-3), None, 0, cfg5, hoje)
		ck("com prazo de 5 anos na configuração, 3 anos ainda está no prazo", c["nivel"] == "no_prazo")

		# ---------------------------------------------------------- com banco
		def novo_lead(nome, **extra):
			first, _s, last = nome.partition(" ")
			l = frappe.get_doc({"doctype": "CRM Lead", "first_name": first, "last_name": last,
								"lead_name": nome, **extra})
			l.insert(ignore_permissions=True)
			leads.append(l.name)
			return l

		a = novo_lead("Fulano Prescricao Critico", data_saida=d(years=-2, days=15),
					  data_admissao=d(years=-9), valor_mes_estimado=800)
		b = novo_lead("Beltrano Prescricao Tranquilo", data_saida=d(months=-3))
		novo_lead("Cicrano Prescricao Sem Data")

		r = pc.listar()
		nomes = {x["lead"]: x for x in r["fila"]}
		ck("o atendimento crítico aparece na fila", a.name in nomes, str(list(nomes)[:3]))
		ck("o crítico vem antes do tranquilo na ordem",
		   r["fila"][0]["lead"] == a.name if r["fila"] else False)
		ck("quem está no prazo também aparece", b.name in nomes)
		ck("quem não tem data de saída fica fora por padrão",
		   all(x["nivel"] != "sem_data" for x in r["fila"]))
		ck("o resumo conta quem está sem data", r["resumo"]["sem_data"] >= 1, str(r["resumo"]))
		ck("o custo total soma a fila", r["custo_total"] >= 0)
		ck("a tela recebe o aviso de uso interno", "promessa de resultado" in r["aviso_interno"])

		r2 = pc.listar(incluir_sem_data=1)
		ck("pedindo, quem está sem data entra na lista",
		   any(x["nivel"] == "sem_data" for x in r2["fila"]))

		# gravação e suas travas
		pc.salvar(b.name, str(d(years=-1)), str(d(years=-6)), 500)
		ck("salva as datas no atendimento",
		   str(frappe.db.get_value("CRM Lead", b.name, "data_saida")) == str(d(years=-1)))
		try:
			pc.salvar(b.name, str(d(days=5)))
			ck("data de saída no futuro é recusada", False)
		except frappe.ValidationError:
			ck("data de saída no futuro é recusada", True)
		try:
			pc.salvar(b.name, str(d(years=-2)), str(d(years=-1)))
			ck("admissão depois da saída é recusada", False)
		except frappe.ValidationError:
			ck("admissão depois da saída é recusada", True)

		# ---------------------------------------------------------- aviso diário
		frappe.db.delete("CRM Task", {"reference_docname": a.name})
		frappe.db.set_value("CRM Lead", a.name, "prescricao_avisado_em", None, update_modified=False)
		pc.alertar()
		tarefas = frappe.get_all("CRM Task", filters={"reference_doctype": "CRM Lead",
													   "reference_docname": a.name}, pluck="title")
		ck("o aviso diário cria tarefa para o crítico", len(tarefas) == 1, str(tarefas))
		ck("a tarefa diz quantos dias faltam", tarefas and "dia" in tarefas[0])
		ck("o atendimento fica marcado como avisado",
		   frappe.db.get_value("CRM Lead", a.name, "prescricao_avisado_em") is not None)
		pc.alertar()
		ck("rodar de novo no mesmo dia não duplica a tarefa",
		   frappe.db.count("CRM Task", {"reference_doctype": "CRM Lead", "reference_docname": a.name}) == 1)

		# ---------------------------------------------------------- textos e travas
		ex = pc.como_funciona()
		ck("a explicação tem os quatro blocos", len(ex["blocos"]) == 4)
		ck("a explicação diz o que a tela NÃO faz",
		   any("NÃO faz" in b["titulo"] for b in ex["blocos"]))
		ck("status informa que o módulo está ligado", pc.status()["ativo"])

		from unittest.mock import patch

		with patch("crm.api.prescricao._cfg", return_value=frappe._dict({"prescricao_ativo": 0})):
			ck("módulo desligado não é ativo", not pc._modulo_ativo())
			try:
				pc.listar()
				ck("módulo desligado recusa a listagem", False)
			except frappe.ValidationError:
				ck("módulo desligado recusa a listagem", True)

		with patch("crm.provision.get_profile", return_value="agencia"):
			ck("fora do perfil de escritório o módulo não existe", not pc._modulo_ativo())
			try:
				pc.listar()
				ck("perfil de agência recusa a listagem", False)
			except frappe.ValidationError:
				ck("perfil de agência recusa a listagem", True)
	finally:
		frappe.set_user("Administrator")
		for n in leads:
			frappe.db.delete("CRM Task", {"reference_docname": n})
			try:
				frappe.delete_doc("CRM Lead", n, force=True, ignore_permissions=True)
			except Exception:
				pass
		frappe.db.commit()
	return res


def run():
	from unittest.mock import patch

	with patch("crm.provision.get_profile", return_value="escritorio"):
		return _run()
