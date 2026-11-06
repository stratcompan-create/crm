"""Teste de fumaça: banco de testemunhas (crm.api.testemunhas).

A pergunta que a tela tem que responder na reunião: "quem trabalhou na agência Centro entre
2019 e 2022?". E o aviso que protege o escritório: a mesma testemunha aparecendo em casos
demais. Apaga tudo no fim.
"""

from unittest.mock import patch

import frappe

from crm.api import testemunhas as ts


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(nome, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", nome, extra)

	def novo_caso(nome):
		first, _s, last = nome.partition(" ")
		d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": first,
							"last_name": last, "lead_name": nome})
		d.flags.sem_cobranca_automatica = True
		return d.insert(ignore_permissions=True)

	def parte(deal, nome, **kw):
		return frappe.get_doc({"doctype": "CRM Parte", "deal": deal, "tipo": "Testemunha",
							   "nome": nome, **kw}).insert(ignore_permissions=True)

	casos = []
	try:
		a = novo_caso("Cliente Um Testemunhas")
		b = novo_caso("Cliente Dois Testemunhas")
		c = novo_caso("Cliente Tres Testemunhas")
		casos += [a.name, b.name, c.name]

		# a mesma pessoa em três casos: é essa que o banco vai apontar
		p1 = parte(a.name, "Maria Souza Teste", documento="111.222.333-44",
				   local_trabalho="Agência Centro", periodo_inicio="2019-03-01",
				   periodo_fim="2022-08-31", telefone="87999990000")
		parte(b.name, "Maria Souza Teste", documento="11122233344",
			  local_trabalho="Agência Centro", periodo_inicio="2019-03-01", periodo_fim="2022-08-31")
		parte(c.name, "maria souza teste", local_trabalho="Agência Centro")

		p2 = parte(a.name, "Joao Lima Teste", local_trabalho="Agência Zona Norte",
				   periodo_inicio="2015-01-01", periodo_fim="2017-12-31")
		p3 = parte(b.name, "Ana Paula Teste", local_trabalho="Agência Centro",
				   periodo_inicio="2023-01-01")
		p4 = parte(c.name, "Sem Periodo Teste", local_trabalho="Agência Centro")

		# ---------------------------------------------------------- a busca da reunião
		r = ts.buscar(local="Agência Centro", de="2019-01-01", ate="2022-12-31")
		nomes = {x["nome"] for x in r["testemunhas"]}
		ck("acha quem trabalhou na agência no período", "Maria Souza Teste" in nomes, str(nomes))
		ck("não traz quem é de outra agência", "Joao Lima Teste" not in nomes, str(nomes))
		ck("não traz quem só começou depois da janela", "Ana Paula Teste" not in nomes, str(nomes))
		ck("quem está sem período cadastrado entra (é 'não sei', não 'não')",
		   "Sem Periodo Teste" in nomes, str(nomes))
		ck("a busca marca quem está sem período",
		   any(x["sem_periodo"] for x in r["testemunhas"] if x["nome"] == "Sem Periodo Teste"))

		r2 = ts.buscar(local="agencia centro")
		ck("a busca ignora acento e maiúscula", len(r2["testemunhas"]) >= 4, str(len(r2["testemunhas"])))

		r3 = ts.buscar(termo="joao")
		ck("busca por nome funciona sem o local",
		   {x["nome"] for x in r3["testemunhas"]} == {"Joao Lima Teste"},
		   str([x["nome"] for x in r3["testemunhas"]]))

		r4 = ts.buscar(local="Agência Centro", de="2023-06-01")
		ck("janela só a partir de 2023 pega quem ainda está lá",
		   "Ana Paula Teste" in {x["nome"] for x in r4["testemunhas"]})

		# ---------------------------------------------------------- o aviso de repetição
		maria = next(x for x in r["testemunhas"] if x["nome"] == "Maria Souza Teste")
		ck("conta em quantos casos a testemunha aparece", maria["casos"] == 3, str(maria["casos"]))
		ck("marca a testemunha muito usada", maria["muito_usada"])
		ck("quem aparece uma vez só não é marcada",
		   not any(x["muito_usada"] for x in r3["testemunhas"]))
		ck("o resultado vem com o aviso sobre depoimento questionado",
		   "questionado" in r["aviso_repetidas"])
		ck("a mais usada vem primeiro na lista", r2["testemunhas"][0]["nome"] == "Maria Souza Teste",
		   r2["testemunhas"][0]["nome"])

		rep = ts.repetidas()
		alvo = [x for x in rep["repetidas"] if x["nome"].lower() == "maria souza teste"]
		ck("a lista de repetidas traz a Maria", len(alvo) == 1, str([x["nome"] for x in rep["repetidas"]]))
		ck("e diz em quantos casos ela está", alvo and alvo[0]["quantidade"] == 3,
		   str(alvo[0]["quantidade"]) if alvo else "")
		ck("a lista de repetidas junta os casos dela", alvo and len(alvo[0]["casos"]) == 3)
		ck("junta pelo nome mesmo sem documento nas três",
		   alvo and alvo[0]["documento"] in ("111.222.333-44", "11122233344"))
		ck("quem aparece uma vez só fica fora das repetidas",
		   all("Joao" not in x["nome"] for x in rep["repetidas"]))

		# ---------------------------------------------------------- juntar cadastros da mesma pessoa
		# o cadastro de c nao tem CPF e ainda assim entrou no grupo dos outros dois
		ck("o cadastro sem CPF entra no grupo do CPF quando o nome bate",
		   maria["casos"] == 3, str(maria["casos"]))

		# dois CPFs diferentes para o mesmo nome: homonimos, nao pode juntar
		# (o escritorio tem que olhar, nao o CRM decidir)
		d = novo_caso("Cliente Quatro Testemunhas")
		casos.append(d.name)
		e = novo_caso("Cliente Cinco Testemunhas")
		casos.append(e.name)
		parte(d.name, "Jose Homonimo Teste", documento="555.666.777-88",
			  local_trabalho="Agência Sul")
		parte(e.name, "Jose Homonimo Teste", documento="999.888.777-66",
			  local_trabalho="Agência Sul")
		f = novo_caso("Cliente Seis Testemunhas")
		casos.append(f.name)
		parte(f.name, "jose homonimo teste", local_trabalho="Agência Sul")

		r7 = ts.buscar(local="Agência Sul")
		josés = [x for x in r7["testemunhas"] if "homonimo" in x["nome"].lower()]
		ck("os três cadastros de homônimo aparecem", len(josés) == 3, str(len(josés)))
		ck("nome com dois CPFs diferentes NÃO é contado como a mesma pessoa",
		   all(x["casos"] <= 2 for x in josés), str([x["casos"] for x in josés]))
		ck("e a tela recebe o aviso de nome ambíguo",
		   all(x["nome_ambiguo"] for x in josés), str([x["nome_ambiguo"] for x in josés]))
		ck("homônimo com 2 cadastros não entra no alerta de limite 3",
		   all(not x["muito_usada"] for x in josés))

		# o grupo mostra o CPF mesmo quando o primeiro cadastro nao tinha
		rep2 = ts.repetidas()
		alvo2 = [x for x in rep2["repetidas"] if x["nome"].lower() == "maria souza teste"]
		ck("o grupo exibe o CPF vindo de qualquer cadastro dele",
		   alvo2 and alvo2[0]["documento"], str(alvo2[0]["documento"]) if alvo2 else "")
		ck("o grupo exibe o nome bem escrito, não o em minúscula",
		   alvo2 and alvo2[0]["nome"] == "Maria Souza Teste",
		   alvo2[0]["nome"] if alvo2 else "")

		# o limite é configurável
		with patch("crm.api.testemunhas._cfg",
				   return_value=frappe._dict({"testemunhas_ativo": 1, "testemunhas_limite_alerta": 4})):
			ck("subindo o limite para 4, a Maria sai do alerta",
			   all("maria" not in x["nome"].lower() for x in ts.repetidas()["repetidas"]))

		# ---------------------------------------------------------- locais e caso
		locs = ts.locais()
		ck("sugere os locais já cadastrados", "Agência Centro" in locs, str(locs))
		ck("não repete o mesmo local duas vezes", len(locs) == len(set(locs)))

		doc = ts.do_caso(a.name)
		ck("as testemunhas do caso vêm só desse caso", len(doc["testemunhas"]) == 2,
		   str(len(doc["testemunhas"])))
		ck("e já vêm com o aviso de repetição",
		   any(x["muito_usada"] for x in doc["testemunhas"]))

		# ---------------------------------------------------------- completar a ficha
		ts.atualizar(p2.name, local_trabalho="Agência Centro", periodo_inicio="2019-06-01",
					 periodo_fim="2021-01-31", telefone="87988887777", email="joao@example.com",
					 disponivel=0, observacoes="Mudou de cidade")
		d2 = frappe.db.get_value("CRM Parte", p2.name,
								 ["local_trabalho", "telefone", "disponivel", "periodo_fim"], as_dict=True)
		ck("a ficha da testemunha é completada", d2.local_trabalho == "Agência Centro" and d2.telefone == "87988887777")
		ck("quem não pode depor fica marcado", d2.disponivel == 0)

		r5 = ts.buscar(local="Agência Centro", de="2019-01-01", ate="2022-12-31")
		ck("depois de completar, o João aparece na busca",
		   "Joao Lima Teste" in {x["nome"] for x in r5["testemunhas"]})
		r6 = ts.buscar(local="Agência Centro", de="2019-01-01", ate="2022-12-31", so_disponiveis=1)
		ck("filtrando só disponíveis, ele sai",
		   "Joao Lima Teste" not in {x["nome"] for x in r6["testemunhas"]})

		try:
			ts.atualizar(p3.name, periodo_inicio="2022-01-01", periodo_fim="2020-01-01")
			ck("período invertido é recusado", False)
		except frappe.ValidationError:
			ck("período invertido é recusado", True)

		ck("testemunha inexistente é recusada",
		   _recusa(lambda: ts.atualizar("naoexiste", local_trabalho="X")))

		# ---------------------------------------------------------- travas
		ck("status informa o limite de alerta", ts.status()["limite_alerta"] == 3,
		   str(ts.status()["limite_alerta"]))

		with patch("crm.api.testemunhas._cfg", return_value=frappe._dict({"testemunhas_ativo": 0})):
			ck("módulo desligado não é ativo", not ts._modulo_ativo())
			ck("módulo desligado recusa a busca", _recusa(lambda: ts.buscar(local="x")))

		with patch("crm.provision.get_profile", return_value="agencia"):
			ck("fora do perfil de escritório o módulo não existe", not ts._modulo_ativo())
			ck("perfil de agência recusa a busca", _recusa(lambda: ts.buscar(local="x")))

		_ = (p1, p4)
	finally:
		frappe.set_user("Administrator")
		for n in casos:
			frappe.db.delete("CRM Parte", {"deal": n})
			frappe.db.delete("CRM Task", {"reference_docname": n})
			frappe.db.delete("Comment", {"reference_name": n})
			try:
				frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True)
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
