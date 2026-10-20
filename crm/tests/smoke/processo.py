"""Teste de fumaça: aba Processo (crm.api.processo) — número CNJ, partes, conflito de interesses,
andamentos para o cliente e encerramento. Apaga tudo no fim."""

import frappe

from crm.api import processo as pr


def _run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	def novo_caso(nome):
		first, last = nome.split(" ", 1)
		d = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", "first_name": first, "last_name": last, "lead_name": nome})
		d.flags.sem_cobranca_automatica = True
		return d.insert(ignore_permissions=True)

	casos = []
	try:
		ok, _a = pr.validar_cnj("0000001-45.2024.8.26.0100")
		calc = 98 - (int("0000001" + "2024" + "8" + "26" + "0100" + "00") % 97)
		numero_ok = f"0000001-{calc:02d}.2024.8.26.0100"
		ck("número CNJ com dígito certo é aceito", pr.validar_cnj(numero_ok)[0], numero_ok)
		ck("número CNJ com dígito errado é apontado", not pr.validar_cnj(numero_ok.replace(f"-{calc:02d}.", f"-{(calc + 1) % 100:02d}."))[0])
		ck("número sem 20 dígitos é apontado", not pr.validar_cnj("123")[0])

		a = novo_caso("Cliente Teste Processo")
		casos.append(a.name)
		r = pr.salvar_processo(a.name, numero_ok.replace("-", "").replace(".", ""), "1ª Vara Cível")
		ck("salva o número já formatado", frappe.db.get_value("CRM Deal", a.name, "numero_processo") == numero_ok, r["numero_processo"])

		b = novo_caso("Empresa Rival Teste")
		casos.append(b.name)
		r = pr.adicionar_parte(a.name, "Empresa Rival Teste Ltda", "Parte contrária")
		ck("parte contrária que é cliente gera alerta de conflito", r["conflitos"] and r["conflitos"][0].get("deal") == b.name, str(r["conflitos"]))
		r = pr.adicionar_parte(a.name, "Fulano Testemunha", "Testemunha")
		ck("testemunha não passa pela checagem", r["conflitos"] == [])

		pr.adicionar_parte(a.name, "Pessoa Contraria Teste", "Parte contrária")
		c = novo_caso("Pessoa Contraria Teste")
		casos.append(c.name)
		tarefa = frappe.db.exists("CRM Task", {"reference_docname": c.name, "title": ["like", "%conflito de interesses%"]})
		ck("cliente novo que é parte contrária em outro caso cria tarefa de alerta", bool(tarefa))

		pr.adicionar_andamento(a.name, "Nota interna: estudar jurisprudência", visivel_cliente=0)
		st = pr.status_para_cliente(a.name)
		ck("sem andamento visível, o cliente vê mensagem padrão", st["tem"] is False)
		pr.adicionar_andamento(a.name, "A audiência foi marcada para 20/11.", visivel_cliente=1)
		st = pr.status_para_cliente(a.name)
		ck("cliente vê o último andamento visível", st["tem"] and "audiência" in st["texto"])

		frappe.get_doc({"doctype": "CRM Honorario", "deal": a.name, "status": "Pendente", "tipo_honorario": "Fixo", "valor": 500,
						"data_vencimento": frappe.utils.nowdate()}).insert(ignore_permissions=True)
		r = pr.encerrar(a.name, "Acordo", 1, "Acordo homologado")
		ck("encerramento avisa honorário em aberto", r["ok"] is False and any("honorário" in p for p in r["pendencias"]), str(r))
		r = pr.encerrar(a.name, "Acordo", 1, "Acordo homologado", mesmo_com_pendencias=1)
		v = frappe.db.get_value("CRM Deal", a.name, ["encerrado", "motivo_encerramento", "documentos_devolvidos"], as_dict=True)
		ck("encerra mesmo com pendências quando confirmado", r["ok"] and v.encerrado == 1 and v.motivo_encerramento == "Acordo" and v.documentos_devolvidos == 1)
		t = pr.termo_encerramento_pdf(a.name)
		ck("gera o termo de encerramento em PDF", t["pdf"][:4] == "JVBE")
		pr.reabrir(a.name)
		ck("reabre o caso", frappe.db.get_value("CRM Deal", a.name, "encerrado") == 0)
		d = pr.dados(a.name)
		ck("dados da aba trazem partes, andamentos e o conflito", len(d["partes"]) == 3 and len(d["andamentos"]) == 2 and d["partes"][0]["conflitos"])
	finally:
		frappe.set_user("Administrator")
		for n in casos:
			for dt in ("CRM Parte", "CRM Andamento", "CRM Honorario"):
				frappe.db.delete(dt, {"deal": n})
			frappe.db.delete("CRM Task", {"reference_docname": n})
			frappe.delete_doc("CRM Deal", n, force=True, ignore_permissions=True)
		frappe.db.commit()
	return res


def run():
	from unittest.mock import patch

	with patch("crm.provision.get_profile", return_value="escritorio"):
		return _run()
