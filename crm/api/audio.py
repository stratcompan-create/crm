# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Ficha por áudio: o áudio gravado na consulta (ou um áudio de WhatsApp) vira texto aqui e depois
# a IA da ficha organiza os campos. A transcrição usa o Whisper (OpenAI) com a chave do escritório.
# O ditado ao vivo não passa por aqui: acontece no próprio navegador, sem custo.

import requests

import frappe
from frappe import _
from frappe.utils import cint

MAX_BYTES = 25 * 1024 * 1024  # limite do serviço de transcrição
URL = "https://api.openai.com/v1/audio/transcriptions"
TIPOS = (".webm", ".ogg", ".oga", ".opus", ".mp3", ".m4a", ".mp4", ".wav", ".mpeg", ".mpga", ".aac")


def _chave() -> str:
	try:
		dt = "CRM Automacoes Config"
		if frappe.get_meta(dt).has_field("chave_transcricao") and frappe.db.get_single_value(dt, "chave_transcricao"):
			from frappe.utils.password import get_decrypted_password

			return get_decrypted_password(dt, dt, "chave_transcricao", raise_exception=False) or ""
	except Exception:
		pass
	return frappe.conf.get("openai_api_key") or ""


@frappe.whitelist()
def estado() -> dict:
	return {"configurado": bool(_chave()), "pode_configurar": bool(set(frappe.get_roles()) & {"System Manager", "Sales Manager"})}


@frappe.whitelist()
def salvar_chave(chave: str = "") -> dict:
	frappe.only_for(("System Manager", "Sales Manager"))
	chave = (chave or "").strip()
	if chave and not chave.startswith("sk-"):
		frappe.throw(_("Essa não parece uma chave da OpenAI (começa com sk-)."))
	# grava só a chave: salvar a configuração inteira gravaria "desligado" nas automações que estão no padrão
	from frappe.utils.password import remove_encrypted_password, set_encrypted_password

	dt = "CRM Automacoes Config"
	if chave:
		set_encrypted_password(dt, dt, chave, "chave_transcricao")
		frappe.db.set_single_value(dt, "chave_transcricao", "*" * 10)
	else:
		remove_encrypted_password(dt, dt, "chave_transcricao")
		frappe.db.set_single_value(dt, "chave_transcricao", "")
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
def transcrever() -> dict:
	"""Recebe um arquivo de áudio (campo 'file') e devolve o texto em português."""
	if not (set(frappe.get_roles()) & {"System Manager", "Sales Manager", "Sales User"}):
		frappe.throw(_("Sem permissão."), frappe.PermissionError)
	chave = _chave()
	if not chave:
		frappe.throw(_("A transcrição de áudio ainda não está ligada. Um gestor precisa cadastrar a chave na ficha (ou use o ditado ao vivo)."))
	up = frappe.request.files.get("file") if frappe.request else None
	if not up:
		frappe.throw(_("Nenhum áudio enviado."))
	conteudo = up.stream.read(MAX_BYTES + 1)
	if len(conteudo) > MAX_BYTES:
		frappe.throw(_("Áudio maior que 25 MB. Divida em partes (cerca de 25 minutos cada)."))
	nome = (up.filename or "audio.webm").rsplit("/", 1)[-1]
	if not nome.lower().endswith(TIPOS):
		frappe.throw(_("Formato de áudio não aceito. Use webm, ogg/opus (WhatsApp), mp3, m4a ou wav."))
	try:
		resp = requests.post(
			URL,
			headers={"Authorization": f"Bearer {chave}"},
			files={"file": (nome, conteudo)},
			data={"model": "whisper-1", "language": "pt", "response_format": "text"},
			timeout=300,
		)
	except requests.RequestException:
		frappe.log_error("Áudio: falha ao falar com o serviço de transcrição", frappe.get_traceback())
		frappe.throw(_("Não foi possível transcrever agora. Tente de novo em instantes."))
	if resp.status_code in (401, 403):
		frappe.throw(_("A chave de transcrição foi recusada. Confira a chave."))
	if not resp.ok:
		frappe.log_error("Áudio: resposta com erro do serviço de transcrição", resp.text[:1500])
		frappe.throw(_("O serviço não conseguiu transcrever este áudio."))
	texto = (resp.text or "").strip()
	return {"texto": texto, "caracteres": len(texto), "duracao_aprox_min": round(cint(len(conteudo)) / (16000 * 60), 1)}
