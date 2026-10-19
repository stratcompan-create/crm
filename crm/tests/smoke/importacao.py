"""Teste de fumaça: importar planilha (crm.api.importacao).

Monta planilhas como as de um escritório (Excel e CSV, colunas com nomes variados), confere a
prévia, importa e verifica o que entrou. Apaga tudo no fim.
"""

import base64
import io

import frappe
from frappe.utils import add_days, nowdate

from crm.api import importacao as imp

MARCA = "Teste Importação"


def _xlsx(rows):
	from openpyxl import Workbook

	wb = Workbook()
	for r in rows:
		wb.active.append(r)
	buf = io.BytesIO()
	wb.save(buf)
	return base64.b64encode(buf.getvalue()).decode()


def _csv(text):
	return base64.b64encode(text.encode("latin-1")).decode()


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	criados = {"lead": [], "deal": [], "hon": [], "desp": []}
	servicos_antes = set(frappe.get_all("CRM Servico", pluck="name"))
	fontes_antes = set(frappe.get_all("CRM Lead Source", pluck="name"))
	try:
		# ---------------- contatos (Excel, com uma linha de título antes do cabeçalho)
		arq = _xlsx([
			["Planilha de contatos do escritório"],
			["Nome completo", "WhatsApp", "E-mail", "Assunto", "Como conheceu", "Obs"],
			[f"Maria {MARCA}", "(87) 90000-1111", "maria.teste.imp@example.com", "Trabalhista", "Indicação", "Rescisão"],
			[f"João {MARCA}", "(87) 90000-2222", "email-errado", "Previdenciário", "Instagram", ""],
			["", "(87) 90000-3333", "", "", "", "sem nome"],
		])
		a = imp.analisar("contatos", arq, "contatos.xlsx")
		ck("acha o cabeçalho mesmo com título antes", a["colunas"][0] == "Nome completo")
		ck("reconhece 'WhatsApp' como telefone", a["mapeamento"]["telefone"] == 1)
		ck("reconhece 'Como conheceu' como origem", a["mapeamento"]["origem"] == 4)
		ck("conta 2 linhas válidas e 1 com erro", a["validas"] == 2 and a["com_erro"] == 1, str((a["validas"], a["com_erro"])))
		r = imp.importar("contatos", arq, "contatos.xlsx")
		ck("importa 2 contatos", r["criados"] == 2, str(r))
		leads = frappe.get_all("CRM Lead", filters={"last_name": ["like", f"%{MARCA}%"]}, fields=["name", "email", "source", "servico"])
		criados["lead"] = [l.name for l in leads]
		maria = next((l for l in leads if l.email == "maria.teste.imp@example.com"), None)
		ck("origem 'Indicação' vira a fonte de indicação", maria and maria.source == "Reference")
		ck("área 'Trabalhista' entra no serviço", maria and maria.servico == "Trabalhista")
		r2 = imp.importar("contatos", arq, "contatos.xlsx")
		ck("não duplica quem já existe (mesmo telefone/e-mail)", r2["criados"] == 0 and r2["ignorados"] == 2, str(r2))

		# ---------------- honorários (CSV com ; e valores/datas em português)
		venc_passado = add_days(nowdate(), -20)
		dd = "/".join(reversed(venc_passado.split("-")))
		csv_txt = (
			"Cliente;Valor da parcela;Data de vencimento;Pago em;Status;Modalidade;Meio de pagamento;Área;Referente\n"
			f"Ana {MARCA};R$ 1.500,00;10/09/2026;10/09/2026;Pago;Fixo;Pix;Família;Parcela 1\n"
			f"Ana {MARCA};1.500,00;{dd};;;Fixo;Boleto;Família;Parcela 2\n"
			f"Ana {MARCA};abc;10/12/2026;;Pendente;Êxito;;Família;Parcela inválida\n"
		)
		arq_h = _csv(csv_txt)
		a = imp.analisar("honorarios", arq_h, "financeiro.csv")
		ck("CSV com ponto e vírgula: reconhece valor e vencimento",
		   a["mapeamento"]["valor"] == 1 and a["mapeamento"]["vencimento"] == 2, str(a["mapeamento"]))
		ck("valor 'abc' é apontado como erro", a["com_erro"] == 1)
		r = imp.importar("honorarios", arq_h, "financeiro.csv")
		ck("importa 2 honorários", r["criados"] == 2, str(r))
		deal = frappe.db.get_value("CRM Deal", {"lead_name": f"Ana {MARCA}"}, "name")
		ck("cria o caso da cliente que ainda não existia", bool(deal))
		if deal:
			criados["deal"].append(deal)
			hons = frappe.get_all("CRM Honorario", filters={"deal": deal}, fields=["name", "status", "valor", "forma_pagamento", "servico"], order_by="data_vencimento asc")
			criados["hon"] = [h.name for h in hons]
			ck("só os 2 honorários da planilha (sem cobrança automática extra)", len(hons) == 2, str(len(hons)))
			ck("parcela paga entra como Paga com 1.500,00", hons and hons[0].status == "Pago" and hons[0].valor == 1500)
			ck("parcela vencida sem pagamento entra como Atrasada", len(hons) > 1 and hons[1].status == "Atrasado", str(hons[1].status if len(hons) > 1 else ""))
			ck("'Pix' vira PIX", hons and hons[0].forma_pagamento == "PIX")
			opcoes = (frappe.get_meta("CRM Honorario").get_field("servico").options or "").split("\n")
			esperado = "Família e Sucessões" if "Família e Sucessões" in opcoes else None
			ck("área do honorário segue as áreas do perfil do site", hons and (hons[0].servico or None) == esperado, str(hons[0].servico if hons else ""))
			ck("o caso guarda a área no serviço", frappe.db.get_value("CRM Deal", deal, "servico") in ("Família e Sucessões", "Família"))

		# ---------------- despesas ligadas ao caso
		arq_d = _xlsx([
			["Descrição", "Valor", "Vencimento", "Situação", "Cliente"],
			["Custas iniciais", 350, "05/09/2026", "pago", f"Ana {MARCA}"],
			["Aluguel da sala", "2.200,00", "05/12/2026", "", ""],
		])
		r = imp.importar("despesas", arq_d, "despesas.xlsx")
		ck("importa 2 despesas", r["criados"] == 2, str(r))
		desp = frappe.get_all("CRM Despesa", filters={"observacoes": ["like", "Importado da planilha%"]}, fields=["name", "categoria", "deal", "descricao"])
		criados["desp"] = [d.name for d in desp]
		custas = next((d for d in desp if d.descricao == "Custas iniciais"), None)
		ck("custas ficam ligadas ao caso da cliente", custas and custas.deal == deal)
		ck("'Custas' vira a categoria Custas e Taxas", custas and custas.categoria == "Custas e Taxas")
		aluguel = next((d for d in desp if d.descricao == "Aluguel da sala"), None)
		ck("'Aluguel' vira Contas Fixas", aluguel and aluguel.categoria == "Contas Fixas")

		# ---------------- modelo e formato não aceito
		m = imp.baixar_modelo("honorarios")
		ck("baixar_modelo devolve um .xlsx", m["nome"].endswith(".xlsx") and len(m["arquivo"]) > 100)
		erro = None
		try:
			imp.analisar("contatos", _csv("x"), "antigo.xls")
		except frappe.ValidationError as e:
			erro = str(e)
		ck("recusa .xls antigo com explicação", erro and ".xlsx" in erro)
	finally:
		frappe.set_user("Administrator")
		for n in criados["hon"]:
			frappe.delete_doc("CRM Honorario", n, force=True, ignore_permissions=True)
		for n in criados["desp"]:
			frappe.delete_doc("CRM Despesa", n, force=True, ignore_permissions=True)
		for n in criados["deal"]:
			frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True)
		for n in criados["lead"]:
			frappe.delete_doc("CRM Lead", n, force=True, ignore_permissions=True)
		for c in frappe.get_all("Contact", filters={"last_name": ["like", f"%{MARCA}%"]}, pluck="name"):
			frappe.delete_doc("Contact", c, force=True, ignore_permissions=True)
		for n in set(frappe.get_all("CRM Servico", pluck="name")) - servicos_antes:
			frappe.delete_doc("CRM Servico", n, force=True, ignore_permissions=True)
		for n in set(frappe.get_all("CRM Lead Source", pluck="name")) - fontes_antes:
			frappe.delete_doc("CRM Lead Source", n, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res
