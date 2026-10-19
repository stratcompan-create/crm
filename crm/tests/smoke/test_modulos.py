"""Teste de fumaça: módulos do escritório ligam/desligam por site (personalização por configuração)."""

import json

import frappe
from frappe.utils import cint

from crm.api import automacoes as au
from crm.www.crm import _config_flag


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	antes = {k: au.get_config().get(k) for k in ("processo_ativo", "prestacao_ativo")}
	try:
		cfg = au.get_config()
		ck("módulos vêm ligados por padrão", cint(cfg.get("processo_ativo")) == 1 and cint(cfg.get("prestacao_ativo")) == 1)

		au.save_settings(json.dumps({"processo_ativo": 0}))
		boot = {k: cint(_config_flag(k, 1)) for k in ("processo_ativo", "prestacao_ativo")}
		ck("desligar a aba Processo chega no app", boot.get("processo_ativo") == 0 and boot.get("prestacao_ativo") == 1)
		ck("desligar um módulo não mexe nas outras automações",
		   au.get_config().get("contas_ativo") == cfg.get("contas_ativo"))

		au.save_settings(json.dumps({"processo_ativo": 1}))
		ck("religar volta ao normal", cint(_config_flag("processo_ativo", 1)) == 1)
	finally:
		au.save_settings(json.dumps({k: (1 if v is None else v) for k, v in antes.items()}))
		frappe.db.commit()
	return res
