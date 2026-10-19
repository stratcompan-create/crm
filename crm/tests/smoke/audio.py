"""Teste de fumaça: ficha por áudio (crm.api.audio). Não chama o serviço externo: confere chave,
permissões e mensagens; a chamada à OpenAI é simulada."""

import io
from unittest.mock import patch

import frappe
from werkzeug.datastructures import FileStorage

from crm.api import audio


class _Resp:
	def __init__(self, status, text):
		self.status_code, self.text, self.ok = status, text, 200 <= status < 300


def _req_com_arquivo(nome, conteudo):
	class R:
		files = {"file": FileStorage(stream=io.BytesIO(conteudo), filename=nome)}

	return R()


def run():
	frappe.set_user("Administrator")
	res = []

	def ck(name, cond, extra=""):
		res.append(bool(cond))
		print("OK  " if cond else "FAIL", name, extra)

	chave_antes = audio._chave() if not frappe.conf.get("openai_api_key") else ""
	outros_antes = {k: v for k, v in frappe.db.sql("select field, value from tabSingles where doctype='CRM Automacoes Config' and field not in ('chave_transcricao', 'modified', 'modified_by')")}
	try:
		erro = None
		try:
			audio.salvar_chave("abc")
		except frappe.ValidationError as e:
			erro = str(e)
		ck("recusa chave que não é da OpenAI", bool(erro))

		audio.salvar_chave("")
		frappe.local.request = _req_com_arquivo("consulta.webm", b"x" * 100)
		erro = None
		try:
			audio.transcrever()
		except frappe.ValidationError as e:
			erro = str(e)
		ck("sem chave, explica que precisa ligar (ditado continua)", erro and "ditado" in erro)

		audio.salvar_chave("sk-teste-123")
		ck("estado mostra que está configurado", audio.estado()["configurado"])

		frappe.local.request = _req_com_arquivo("audio.exe", b"x" * 100)
		erro = None
		try:
			audio.transcrever()
		except frappe.ValidationError as e:
			erro = str(e)
		ck("recusa arquivo que não é áudio", erro and "Formato" in erro)

		frappe.local.request = _req_com_arquivo("whatsapp.ogg", b"x" * 1000)
		with patch("crm.api.audio.requests.post", return_value=_Resp(200, "O cliente foi demitido em março.")) as m:
			r = audio.transcrever()
		ck("transcreve áudio do WhatsApp (.ogg) em português", r["texto"] == "O cliente foi demitido em março." and m.call_args.kwargs["data"]["language"] == "pt")

		frappe.local.request = _req_com_arquivo("consulta.webm", b"x" * 1000)
		with patch("crm.api.audio.requests.post", return_value=_Resp(401, "bad key")):
			erro = None
			try:
				audio.transcrever()
			except frappe.ValidationError as e:
				erro = str(e)
		ck("chave recusada vira mensagem clara", erro and "recusada" in erro)
		outros_depois = {k: v for k, v in frappe.db.sql("select field, value from tabSingles where doctype='CRM Automacoes Config' and field not in ('chave_transcricao', 'modified', 'modified_by')")}
		ck("salvar a chave não mexe nas outras automações", outros_depois == outros_antes)
	finally:
		frappe.local.request = None
		audio.salvar_chave(chave_antes or "")
		frappe.db.commit()
	return res
