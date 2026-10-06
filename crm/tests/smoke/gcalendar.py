"""Teste de fumaca: Google Agenda (conexao e cruzamento com o agendamento online),
sem falar com o Google de verdade.

Roda no site atual (bench --site SITE execute crm.tests.run_smoke.run_all).
"""

from datetime import datetime
from unittest import mock

import frappe

from crm.api import agenda, gcalendar


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	before = frappe.db.get_singles_dict("CRM Google Calendar") or {}
	try:
		frappe.db.set_single_value("CRM Google Calendar", "conectado", 0)
		frappe.db.commit()

		status = gcalendar.get_status()
		ck("desconectado por padrao", status["conectado"] is False)

		ck(
			"obter_ocupado nao quebra sem estar conectado",
			gcalendar.obter_ocupado(datetime(2026, 1, 1, 9), datetime(2026, 1, 1, 18)) == [],
		)
		ck(
			"criar_evento nao quebra sem estar conectado",
			gcalendar.criar_evento("Reuniao", datetime(2026, 1, 1, 9), datetime(2026, 1, 1, 10)) is None,
		)

		# conectado, mas a chamada ao Google falha (ex.: internet fora, token vencido) -
		# o agendamento tem que continuar funcionando mesmo assim
		frappe.db.set_single_value("CRM Google Calendar", "conectado", 1)
		frappe.db.set_single_value("CRM Google Calendar", "bloquear_ocupado", 1)
		frappe.db.set_single_value("CRM Google Calendar", "criar_eventos", 1)
		frappe.db.commit()

		with mock.patch.object(gcalendar, "_access_token", side_effect=Exception("rede fora")):
			ocupado = gcalendar.obter_ocupado(datetime(2026, 1, 1, 9), datetime(2026, 1, 1, 18))
			gcalendar.criar_evento("Reuniao", datetime(2026, 1, 1, 9), datetime(2026, 1, 1, 10))
		ck("conectado mas o Google falhou: obter_ocupado devolve vazio em vez de quebrar", ocupado == [])

		# o cruzamento soma ao que o CRM ja sabia (reunioes marcadas por ele mesmo)
		with mock.patch.object(
			gcalendar, "obter_ocupado", lambda s, e: [(datetime(2026, 1, 1, 14), datetime(2026, 1, 1, 15))]
		):
			busy = agenda._busy(datetime(2026, 1, 1, 0), datetime(2026, 1, 2, 0))
		ck("_busy() do agendamento soma o ocupado do Google Agenda", (datetime(2026, 1, 1, 14), datetime(2026, 1, 1, 15)) in busy)

		# o slot que cai dentro do horario "ocupado no Google" some da lista oferecida
		cfg = frappe._dict(
			agenda_dias="1,2,3,4,5,6,7", agenda_duracao=60, agenda_inicio="09:00", agenda_fim="18:00", agenda_antecedencia=0
		)
		with mock.patch.object(
			gcalendar, "obter_ocupado", lambda s, e: [(datetime(2026, 1, 1, 14), datetime(2026, 1, 1, 15))]
		):
			slots = agenda._slots_for(datetime(2026, 1, 1).date(), cfg)
		ck("horario ocupado no Google Agenda nao aparece como livre", datetime(2026, 1, 1, 14) not in slots)
	finally:
		for k, v in before.items():
			frappe.db.set_single_value("CRM Google Calendar", k, v)
		frappe.db.commit()
	return res
