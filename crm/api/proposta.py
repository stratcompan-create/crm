import base64
import io
import json
import os
import re
import subprocess

import frappe
from frappe import _
from frappe.utils import add_days, escape_html, flt, get_datetime, getdate, nowdate

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "fonts")
FONTS = [
	("Poppins", 300, "normal", "Poppins-Light.ttf"),
	("Poppins", 400, "normal", "Poppins-Regular.ttf"),
	("Poppins", 500, "normal", "Poppins-Medium.ttf"),
	("Poppins", 600, "normal", "Poppins-SemiBold.ttf"),
	("Poppins", 700, "normal", "Poppins-Bold.ttf"),
	("Lora", 400, "normal", "Lora-Regular.ttf"),
	("Lora", 600, "normal", "Lora-SemiBold.ttf"),
	("Lora", 700, "normal", "Lora-Bold.ttf"),
	("Lora", 400, "italic", "Lora-Italic.ttf"),
]
_font_css = None

DEFAULT_COLOR = "#042d3c"
DEFAULT_ACCENT = "#8aa1a9"

EYEBROWS = {
	"intro": "Introdução ao projeto",
	"diagnostico": "Diagnóstico",
	"escopo": "Escopo do projeto",
	"cronograma": "Cronograma",
	"orcamento": "Orçamento · onde o investimento é aplicado",
	"ciclos": "Visão de ciclos",
	"investimento": "Investimento",
}

CONDICOES_PADRAO = [
	{"titulo": "O que está incluso", "texto": ""},
	{"titulo": "Escopo protegido", "texto": ""},
	{"titulo": "Compromisso mínimo", "texto": ""},
]


def default_proposal() -> dict:
	"""Estrutura de partida da proposta. Seções sem conteúdo ficam de fora do PDF."""
	return {
		"capa": {"subtitulo": ""},
		"intro": {"titulo": "", "destaque": "", "texto": "", "cartoes_titulo": "", "cartoes": [], "numeros": []},
		"diagnostico": {
			"titulo": "", "destaque": "", "subtitulo": "", "numeros": [],
			"faixa_titulo": "", "faixa_texto": "", "cartoes": [], "conclusao": "",
		},
		"escopo": {"titulo": "", "destaque": "", "itens": []},
		"cronograma": {
			"titulo": "", "destaque": "", "subtitulo": "", "etapas": [],
			"faixa_titulo": "", "faixa_texto": "", "nota": "",
		},
		"orcamento": {"titulo": "", "destaque": "", "subtitulo": "", "cartoes": [], "faixa_titulo": "", "faixa_texto": ""},
		"ciclos": {"titulo": "", "destaque": "", "subtitulo": "", "blocos": [], "citacao": ""},
		"investimento": {
			"titulo": "Investimento", "destaque": "", "plano_rotulo": "", "plano_titulo": "", "plano_texto": "",
			"valor_sufixo": "", "recomendado_titulo": "", "recomendado_texto": "",
			"fases_titulo": "", "fases_texto": "", "condicoes": [dict(c) for c in CONDICOES_PADRAO],
			"validade_dias": 0, "validade": "",
		},
	}


def _merge(base, saved):
	if isinstance(base, dict) and isinstance(saved, dict):
		out = dict(base)
		for k, v in saved.items():
			out[k] = _merge(base.get(k), v) if k in base else v
		return out
	return saved if saved is not None else base


@frappe.whitelist()
def get_proposal(deal: str) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("read")
	saved = {}
	if doc.get("proposal_data"):
		try:
			saved = json.loads(doc.proposal_data)
		except ValueError:
			saved = {}
	return _merge(default_proposal(), saved)


@frappe.whitelist()
def save_proposal(deal: str, data):
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("write")
	if isinstance(data, str):
		data = json.loads(data)
	if not isinstance(data, dict):
		frappe.throw(_("Dados da proposta inválidos"))
	frappe.db.set_value("CRM Deal", deal, "proposal_data", json.dumps(data, ensure_ascii=False))
	avisos = []
	try:
		ctx = deal_context(doc)
		avisos = check_fit(ctx["settings"], ctx["items"], ctx["total"], ctx["client_name"], _merge(default_proposal(), data))
	except Exception:
		frappe.log_error("Falha ao conferir o tamanho da proposta", frappe.get_traceback())
	return {"ok": True, "avisos": avisos}


# ---------------------------------------------------------------- utilidades

def _valid_color(value: str, fallback: str) -> str:
	value = (value or "").strip()
	return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback


def _mix(color: str, other: str, ratio: float) -> str:
	"""Mistura `color` com `other` (ratio = quanto de `other`)."""
	a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
	b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
	return "#" + "".join(f"{round(x * (1 - ratio) + y * ratio):02x}" for x, y in zip(a, b))


def _fmt_currency(value) -> str:
	formatted = f"{flt(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
	return f"R$ {formatted}"


def _fmt_money_short(value) -> str:
	value = flt(value)
	if value == int(value):
		return "R$ " + f"{int(value):,}".replace(",", ".")
	return _fmt_currency(value)


def _rich(text: str) -> str:
	"""Escapa o texto e aceita **negrito**, parágrafos (linha em branco) e quebras de linha."""
	text = (text or "").strip()
	if not text:
		return ""
	paragraphs = []
	for block in re.split(r"\n\s*\n", text):
		block = escape_html(block.strip()).replace("\n", "<br>")
		block = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", block)
		paragraphs.append(f"<p>{block}</p>")
	return "".join(paragraphs)


def _e(text) -> str:
	return escape_html(str(text or ""))


def _spaced(text: str) -> str:
	return _e(text).upper()


def _font_faces() -> str:
	global _font_css
	if _font_css is None:
		css = ""
		for family, weight, style, filename in FONTS:
			path = os.path.join(FONT_DIR, filename)
			if not os.path.exists(path):
				continue
			with open(path, "rb") as fh:
				data = base64.b64encode(fh.read()).decode()
			css += (
				f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: {style}; "
				f"src: url(data:font/ttf;base64,{data}) format('truetype'); }}\n"
			)
		_font_css = css
	return _font_css


def _logo_data_uri(url: str) -> str:
	if not url:
		return ""
	try:
		if url.startswith("/private/files/") or url.startswith("/files/"):
			rel = url.lstrip("/")
			path = frappe.get_site_path(*rel.split("/"))
			if url.startswith("/files/"):
				path = frappe.get_site_path("public", *rel.split("/"))
			with open(path, "rb") as fh:
				raw = fh.read()
			ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
			mime = {"svg": "image/svg+xml", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, f"image/{ext}")
			return f"data:{mime};base64," + base64.b64encode(raw).decode()
	except Exception:
		pass
	return ""


def _cover_background(color: str) -> str:
	"""Fundo da capa: brilho radial da cor da marca com uma grade discreta."""
	from PIL import Image, ImageDraw

	w, h = 1754, 1240
	mask = Image.radial_gradient("L").resize((w, h))
	light = Image.new("RGB", (w, h), _mix(color, "#ffffff", 0.16))
	dark = Image.new("RGB", (w, h), _mix(color, "#000000", 0.35))
	img = Image.composite(dark, light, mask)
	overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
	draw = ImageDraw.Draw(overlay)
	step = 84
	for x in range(0, w, step):
		draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 12), width=1)
	for y in range(0, h, step):
		draw.line([(0, y), (w, y)], fill=(255, 255, 255, 12), width=1)
	img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
	buf = io.BytesIO()
	img.save(buf, "JPEG", quality=88)
	return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- blocos de HTML

def _cards(items, cols):
	items = [i for i in items if (i.get("titulo") or i.get("texto"))]
	if not items:
		return ""
	rows = ""
	for start in range(0, len(items), cols):
		chunk = items[start:start + cols]
		cells = ""
		for it in chunk:
			cells += (
				f'<td class="card" style="width:{100 // cols}%">'
				f'<div class="card-t">{_e(it.get("titulo"))}</div>'
				f'<div class="card-x">{_e(it.get("texto"))}</div></td>'
			)
		cells += "<td></td>" * (cols - len(chunk))
		rows += f"<tr>{cells}</tr>"
	return f'<table class="grid">{rows}</table>'


def _band(nums):
	nums = [n for n in nums if (n.get("valor") or n.get("rotulo"))]
	if not nums:
		return ""
	cells = "".join(
		f'<td class="band-c"><div class="band-v">{_e(n.get("valor"))}</div>'
		f'<div class="band-l">{_spaced(n.get("rotulo"))}</div></td>'
		for n in nums
	)
	return f'<table class="band"><tr>{cells}</tr></table>'


def _stats(nums):
	nums = [n for n in nums if (n.get("valor") or n.get("rotulo"))]
	if not nums:
		return ""
	cells = "".join(
		f'<td class="stat"><div class="stat-v">{_e(n.get("valor"))}</div>'
		f'<div class="stat-l">{_spaced(n.get("rotulo"))}</div></td>'
		for n in nums
	)
	return f'<table class="grid stats"><tr>{cells}</tr></table>'


def _callout(titulo, texto, dark=True):
	if not (titulo or texto):
		return ""
	cls = "callout-d" if dark else "callout-l"
	return (
		f'<table class="grid"><tr><td class="{cls}">'
		f'<div class="callout-t">{_spaced(titulo)}</div><div class="callout-x">{_rich(texto)}</div>'
		f"</td></tr></table>"
	)


def _title(section, data):
	eyebrow = data.get("eyebrow") or EYEBROWS.get(section, "")
	titulo, destaque = data.get("titulo") or "", data.get("destaque") or ""
	html = f'<div class="eyebrow">{_spaced(eyebrow)}</div>'
	if titulo or destaque:
		html += f'<h1>{_e(titulo)} <i>{_e(destaque)}</i></h1>'
	if data.get("subtitulo"):
		html += f'<div class="sub">{_e(data.get("subtitulo"))}</div>'
	return html


def _has(data, *keys):
	for k in keys:
		v = data.get(k)
		if isinstance(v, list):
			if any(any(str(x or "").strip() for x in (i.values() if isinstance(i, dict) else [i])) for i in v):
				return True
		elif str(v or "").strip():
			return True
	return False


def _page(inner, n, total, client, brand):
	return (
		f'<div class="page"><table class="hdr"><tr><td><span class="dia"></span>{_spaced(client)}</td>'
		f'<td class="r">{n:02d} / {total:02d}</td></tr></table>'
		f'<div class="body">{inner}</div>'
		f'<table class="ftr"><tr><td>{_spaced(brand)} × <b>{_spaced(client)}</b></td>'
		f'<td class="r">DOCUMENTO COMERCIAL · {n:02d} / {total:02d}</td></tr></table></div>'
	)


def _sec_intro(d):
	html = _title("intro", d)
	left = f'<div class="txt">{_rich(d.get("texto"))}</div>'
	right = ""
	if _has(d, "cartoes"):
		right = f'<div class="eyebrow" style="margin-top:2mm">{_spaced(d.get("cartoes_titulo") or "")}</div>' + _cards(d.get("cartoes") or [], 2)
	html += (
		f'<table class="two"><tr><td class="two-l">{left}</td><td class="two-r">{right}</td></tr></table>'
	)
	html += _band(d.get("numeros") or [])
	return html


def _sec_diag(d):
	html = _title("diagnostico", d) + _stats(d.get("numeros") or [])
	html += _callout(d.get("faixa_titulo"), d.get("faixa_texto"), True)
	html += _cards(d.get("cartoes") or [], 4)
	if d.get("conclusao"):
		html += f'<div class="txt" style="margin-top:4mm">{_rich(d.get("conclusao"))}</div>'
	return html


def _sec_escopo(d):
	html = _title("escopo", d)
	itens = [i for i in (d.get("itens") or []) if i.get("titulo") or i.get("texto")]
	rows = ""
	for start in range(0, len(itens), 2):
		cells = ""
		for k, it in enumerate(itens[start:start + 2]):
			num = start + k + 1
			cells += (
				f'<td class="esc"><table><tr><td class="esc-n">{num:02d}</td><td>'
				f'<div class="esc-t">{_e(it.get("titulo"))}</div>'
				f'<div class="esc-x">{_rich(it.get("texto"))}</div></td></tr></table></td>'
			)
		if len(itens[start:start + 2]) == 1:
			cells += "<td></td>"
		rows += f"<tr>{cells}</tr>"
	return html + f'<table class="grid esc-g">{rows}</table>'


def _sec_crono(d):
	html = _title("cronograma", d)
	etapas = [e for e in (d.get("etapas") or []) if any(str(v or "").strip() for v in e.values())]
	if etapas:
		cells = "".join(
			f'<td class="etp"><div class="etp-m">{_e(e.get("marco"))}</div>'
			f'<div class="etp-t">{_e(e.get("titulo"))}</div><div class="etp-x">{_e(e.get("texto"))}</div></td>'
			for e in etapas
		)
		html += f'<table class="grid"><tr>{cells}</tr></table>'
	html += _callout(d.get("faixa_titulo"), d.get("faixa_texto"), False)
	if d.get("nota"):
		html += f'<div class="nota">{_rich(d.get("nota"))}</div>'
	return html


def _sec_orc(d):
	html = _title("orcamento", d) + _cards(d.get("cartoes") or [], 4)
	return html + _callout(d.get("faixa_titulo"), d.get("faixa_texto"), False)


def _sec_ciclos(d):
	html = _title("ciclos", d)
	blocos = [b for b in (d.get("blocos") or []) if any(str(v or "").strip() for v in b.values())][:2]
	cells = ""
	for idx, b in enumerate(blocos):
		dark = idx == 0
		pontos = "".join(
			f'<div class="pt">› {_e(p.strip())}</div>' for p in (b.get("pontos") or "").split("\n") if p.strip()
		)
		cells += (
			f'<td class="{"cic-d" if dark else "cic-l"}">'
			f'<div class="callout-t">{_spaced(b.get("rotulo"))}</div>'
			f'<div class="cic-t">{_e(b.get("titulo"))}</div>'
			f'<div class="cic-v">{_e(b.get("detalhe"))}</div>'
			f'<div class="cic-x">{_e(b.get("texto"))}</div>{pontos}</td>'
		)
	html += f'<table class="grid"><tr>{cells}</tr></table>'
	if d.get("citacao"):
		html += f'<div class="cita">"{_e(d.get("citacao"))}"</div>'
	return html


def _sec_invest(d, items, total):
	html = _title("investimento", d)
	desc = d.get("plano_texto") or " · ".join(i.description for i in items if i.description)
	sufixo = f'<div class="val-s">{_e(d.get("valor_sufixo"))}</div>' if d.get("valor_sufixo") else ""
	html += (
		'<table class="grid flush"><tr><td class="plano">'
		f'<div class="callout-t">{_spaced(d.get("plano_rotulo"))}</div>'
		f'<div class="plano-t">{_e(d.get("plano_titulo") or "Investimento")}</div>'
		f'<div class="plano-x">{_e(desc)}</div></td>'
		f'<td class="plano val"><div class="val-v">{_fmt_money_short(total)}</div>{sufixo}</td></tr></table>'
	)
	if len(items) > 1:
		rows = "".join(
			f'<tr><td>{_e(i.description)}</td><td class="c">{flt(i.qty):g}</td>'
			f'<td class="r">{_fmt_currency(i.unit_price)}</td>'
			f'<td class="r">{_fmt_currency(flt(i.qty) * flt(i.unit_price))}</td></tr>'
			for i in items
		)
		html += (
			'<table class="items"><tr><th>DESCRIÇÃO</th><th class="c">QTD</th><th class="r">VALOR UNITÁRIO</th>'
			f'<th class="r">SUBTOTAL</th></tr>{rows}</table>'
		)
	left = _callout(d.get("recomendado_titulo"), d.get("recomendado_texto"), False) if _has(d, "recomendado_titulo", "recomendado_texto") else ""
	right = ""
	if _has(d, "fases_titulo", "fases_texto"):
		right = (
			f'<div class="box"><div class="callout-t">{_spaced(d.get("fases_titulo"))}</div>'
			f'<div class="callout-x">{_rich(d.get("fases_texto"))}</div></div>'
		)
	if left or right:
		html += f'<table class="two2"><tr><td class="tl">{left}</td><td class="tr">{right}</td></tr></table>'
	conds = [c for c in (d.get("condicoes") or []) if str(c.get("texto") or "").strip()]
	if conds:
		html += f'<div class="eyebrow" style="margin-top:5mm">{_spaced("Condições e regras de escopo")}</div>'
		rows = ""
		for start in range(0, len(conds), 2):
			cells = ""
			for c in conds[start:start + 2]:
				cells += f'<td class="cnd">— <b>{_e(c.get("titulo"))}:</b> {_e(c.get("texto"))}</td>'
			if len(conds[start:start + 2]) == 1:
				cells += "<td></td>"
			rows += f"<tr>{cells}</tr>"
		html += f'<table class="grid">{rows}</table>'
	if d.get("validade"):
		html += f'<div class="nota" style="border-top:0.2mm solid #d3dcdd;padding-top:3mm;margin-top:3mm">{_e(d.get("validade"))}</div>'
	return html


# ---------------------------------------------------------------- documento

def _css(color, accent):
	soft = _mix(accent, "#ffffff", 0.55)
	return f"""
	{_font_faces()}
	html, body {{ margin:0; padding:0; }}
	body {{ font-family:'Poppins', Arial, sans-serif; color:#1f2d33; font-size:7pt; }}
	table {{ border-collapse:collapse; }}
	p {{ margin:0 0 2.2mm 0; }}
	.page {{ width:298mm; height:210.15mm; position:relative; overflow:hidden; page-break-after:always; background:#f4f2ed; }}
	.hdr {{ position:absolute; top:9mm; left:16mm; width:265mm; font-size:5.6pt; letter-spacing:0.35em; color:#6b7c82; font-weight:600; }}
	.hdr .r, .ftr .r {{ text-align:right; letter-spacing:0.2em; font-weight:400; }}
	.dia {{ display:inline-block; width:2.4mm; height:2.4mm; border:0.3mm solid {accent}; margin-right:2.5mm; -webkit-transform:rotate(45deg); }}
	.body {{ position:absolute; top:22mm; left:16mm; width:265mm; }}
	.ftr {{ position:absolute; bottom:8mm; left:16mm; width:265mm; border-top:0.25mm solid #d3dcdd; padding-top:2mm; font-size:5pt; letter-spacing:0.14em; color:#7a8a90; }}
	.ftr b {{ color:{color}; }}
	.eyebrow {{ font-size:5.6pt; letter-spacing:0.32em; color:#6b7c82; font-weight:600; margin-bottom:3mm; }}
	h1 {{ font-family:'Lora', Georgia, serif; font-weight:700; font-size:21pt; color:{color}; margin:0 0 3mm 0; line-height:1.15; }}
	h1 i {{ font-weight:400; font-style:italic; color:#5d7078; }}
	.sub {{ color:#7a8a90; font-size:7.2pt; margin-bottom:5mm; }}
	.txt {{ font-size:7.4pt; line-height:1.65; color:#1f2d33; }}
	.grid {{ width:100%; border-collapse:separate; border-spacing:2.6mm; margin:0; }}
	.body > table.grid {{ margin:0 -2.6mm; width:271mm; }}
	.body > table.grid.flush {{ margin:0; width:265mm; border-spacing:0; }}
	.card {{ background:#ffffff; border:0.25mm solid #d3dcdd; border-left:1mm solid {accent}; padding:3.2mm 3.6mm; vertical-align:top; }}
	.card-t {{ font-family:'Lora', Georgia, serif; font-weight:600; font-size:8.6pt; color:{color}; margin-bottom:1.2mm; }}
	.card-x {{ font-size:6.2pt; color:#7a8a90; line-height:1.5; }}
	.two {{ width:265mm; }}
	.two-l {{ width:135mm; vertical-align:top; padding-right:9mm; }}
	.two-r {{ width:121mm; vertical-align:top; }}
	.two-r .grid {{ width:127mm; margin-left:-2.6mm; }}
	.band {{ width:100%; margin-top:6mm; background:{color}; }}
	.band-c {{ padding:4mm 6mm; border-left:0.25mm solid {_mix(color, '#ffffff', 0.18)}; }}
	.band-c:first-child {{ border-left:0; }}
	.band-v {{ font-family:'Lora', Georgia, serif; font-size:12pt; color:#ffffff; }}
	.band-l {{ font-size:5pt; letter-spacing:0.22em; color:{accent}; margin-top:0.8mm; }}
	.stat {{ background:#ffffff; border:0.25mm solid #d3dcdd; border-top:1mm solid {accent}; text-align:center; padding:3.2mm 2mm; }}
	.stat-v {{ font-family:'Lora', Georgia, serif; font-weight:700; font-size:15pt; color:{color}; }}
	.stat-l {{ font-size:4.9pt; letter-spacing:0.16em; color:#7a8a90; margin-top:1mm; }}
	.callout-d {{ background:{color}; padding:4mm 5mm; color:#ffffff; }}
	.callout-l {{ background:#e9ecec; border:0.25mm solid #d3dcdd; padding:4mm 5mm; color:#1f2d33; }}
	.callout-t {{ font-size:5.2pt; letter-spacing:0.26em; color:{accent}; font-weight:600; margin-bottom:1.6mm; }}
	.callout-x {{ font-size:7pt; line-height:1.55; }}
	.callout-x p {{ margin:0; }}
	.esc-g td.esc {{ vertical-align:top; border-bottom:0.25mm solid #d3dcdd; padding:1mm 0 3.4mm 0; width:50%; }}
	.esc-n {{ font-family:'Lora', Georgia, serif; font-size:12pt; color:{accent}; width:11mm; vertical-align:top; padding-top:0.6mm; }}
	.esc-t {{ font-family:'Lora', Georgia, serif; font-weight:600; font-size:9pt; color:{color}; margin-bottom:1mm; }}
	.esc-x {{ font-size:6.7pt; color:#7a8a90; line-height:1.55; padding-right:8mm; }}
	.esc-x p {{ margin:0; }}
	.etp {{ border-left:0.8mm solid {soft}; padding:0 3mm; vertical-align:top; }}
	.etp-m {{ font-family:'Lora', Georgia, serif; font-size:10pt; color:#5d7078; margin-bottom:1.6mm; }}
	.etp-t {{ font-weight:700; font-size:6.6pt; color:{color}; margin-bottom:1mm; }}
	.etp-x {{ font-size:5.8pt; color:#7a8a90; line-height:1.5; }}
	.nota {{ font-size:6.2pt; font-style:italic; color:#7a8a90; margin-top:3mm; border-left:0.8mm solid {accent}; padding-left:3mm; }}
	.cic-d, .cic-l {{ vertical-align:top; padding:5mm 6mm; width:50%; }}
	.cic-d {{ background:{color}; color:#ffffff; }}
	.cic-l {{ background:#e9ecec; border:0.25mm solid #d3dcdd; color:{color}; }}
	.cic-t {{ font-family:'Lora', Georgia, serif; font-size:11pt; margin-bottom:1mm; }}
	.cic-v {{ font-family:'Lora', Georgia, serif; font-size:11pt; color:{soft}; margin-bottom:2mm; }}
	.cic-l .cic-v {{ color:#5d7078; font-style:italic; font-size:9pt; }}
	.cic-x {{ font-size:6.4pt; line-height:1.55; margin-bottom:2.4mm; }}
	.cic-d .cic-x {{ color:#d5e0e4; }}
	.pt {{ font-size:6.4pt; margin-top:1mm; }}
	.cita {{ font-family:'Lora', Georgia, serif; font-style:italic; text-align:center; font-size:8pt; color:{color}; margin-top:5mm; }}
	.plano {{ background:{color}; color:#ffffff; padding:5mm 6mm; vertical-align:middle; }}
	.plano-t {{ font-family:'Lora', Georgia, serif; font-size:11pt; margin-bottom:1.2mm; }}
	.plano-x {{ font-size:6.2pt; color:{soft}; line-height:1.5; }}
	.val {{ text-align:right; width:60mm; }}
	.val-v {{ font-family:'Lora', Georgia, serif; font-size:24pt; color:#ffffff; }}
	.val-s {{ font-size:6pt; letter-spacing:0.14em; color:{accent}; }}
	.two2 {{ width:271mm; border-collapse:separate; border-spacing:2.6mm; margin:0 -2.6mm; }}
	.tl, .tr {{ width:50%; vertical-align:top; }}
	.tl .grid {{ margin:0; width:100%; border-spacing:0; }}
	.box {{ background:#ffffff; border:0.25mm solid #d3dcdd; padding:4mm 5mm; }}
	.cnd {{ width:50%; vertical-align:top; font-size:6.4pt; line-height:1.5; padding:1mm 4mm 1.4mm 0; }}
	table.items {{ width:100%; margin-top:2mm; font-size:6.4pt; }}
	table.items th {{ text-align:left; font-size:5pt; letter-spacing:0.16em; color:#7a8a90; border-bottom:0.25mm solid #d3dcdd; padding:1.6mm 1mm; }}
	table.items td {{ padding:1.8mm 1mm; border-bottom:0.2mm solid #e3e7e7; }}
	.c {{ text-align:center; }} .r {{ text-align:right; }}
	table.items th.c {{ text-align:center; }} table.items th.r {{ text-align:right; }}
	.cover {{ width:298mm; height:210.15mm; position:relative; overflow:hidden; page-break-after:always; }}
	.cover-bg {{ position:absolute; top:0; left:0; width:298mm; height:210.15mm; }}
	.cover-mid {{ position:absolute; top:0; left:0; width:298mm; height:210.15mm; text-align:center; }}
	.cover-mid table {{ width:298mm; height:210.15mm; }}
	.cover-name {{ font-family:'Lora', Georgia, serif; font-size:30pt; letter-spacing:0.03em; color:{_mix(accent, '#ffffff', 0.55)}; display:inline-block; border-bottom:0.6mm solid {_mix(accent, '#ffffff', 0.55)}; padding-bottom:1.2mm; }}
	.cover-logo {{ max-height:38mm; max-width:120mm; margin-bottom:6mm; }}
	.cover-k {{ font-size:6pt; letter-spacing:0.5em; color:{_mix(accent, '#000000', 0.05)}; font-weight:700; margin-top:9mm; }}
	.cover-s {{ font-size:8.4pt; color:#d7e1e4; margin-top:3.4mm; font-weight:300; }}
	.cover-s b {{ font-weight:500; color:#ffffff; }}
	.cover-n {{ position:absolute; top:12mm; right:16mm; width:60mm; text-align:right; white-space:nowrap; font-size:5.6pt; letter-spacing:0.3em; color:{accent}; font-weight:700; }}
	.cover-f {{ position:absolute; bottom:12mm; left:16mm; width:200mm; white-space:nowrap; font-size:5.2pt; letter-spacing:0.28em; color:{accent}; }}
	.hdr td, .ftr td {{ white-space:nowrap; }}
	"""


def validity_text(d) -> str:
	"""Texto da validade: calculado a partir de "dias de validade" ou, se vazio, o texto digitado."""
	dias = int(flt(d.get("validade_dias")))
	if dias > 0:
		limite = add_days(nowdate(), dias)
		return (
			f"Valores válidos até {getdate(limite).strftime('%d/%m/%Y')} "
			f"({dias} dias a partir da apresentação desta proposta)."
		)
	return d.get("validade") or ""


def _build_sections(data, items, total):
	"""Lista de (chave, html) das seções que têm conteúdo, na ordem do documento."""
	sections = []
	if _has(data["intro"], "titulo", "destaque", "texto", "cartoes", "numeros"):
		sections.append(("intro", _sec_intro(data["intro"])))
	if _has(data["diagnostico"], "titulo", "destaque", "numeros", "faixa_titulo", "faixa_texto", "cartoes", "conclusao"):
		sections.append(("diagnostico", _sec_diag(data["diagnostico"])))
	if _has(data["escopo"], "titulo", "destaque", "itens"):
		sections.append(("escopo", _sec_escopo(data["escopo"])))
	if _has(data["cronograma"], "titulo", "destaque", "etapas", "faixa_titulo", "faixa_texto", "nota"):
		sections.append(("cronograma", _sec_crono(data["cronograma"])))
	if _has(data["orcamento"], "titulo", "destaque", "cartoes", "faixa_titulo", "faixa_texto"):
		sections.append(("orcamento", _sec_orc(data["orcamento"])))
	if _has(data["ciclos"], "titulo", "destaque", "blocos", "citacao"):
		sections.append(("ciclos", _sec_ciclos(data["ciclos"])))
	if items or total:
		inv = dict(data["investimento"])
		inv["validade"] = validity_text(inv)
		sections.append(("investimento", _sec_invest(inv, items, total)))
	return sections


SECTION_LABELS = {
	"intro": "Introdução ao projeto",
	"diagnostico": "Diagnóstico",
	"escopo": "Escopo do projeto",
	"cronograma": "Cronograma",
	"orcamento": "Onde o investimento é aplicado",
	"ciclos": "Visão de ciclos",
	"investimento": "Investimento",
}


def check_fit(settings, items, total, client_name, data) -> list[str]:
	"""Avisa quais seções não cabem em uma página (o excesso seria cortado no PDF).

	Renderiza cada seção com altura livre; se o PDF ganhar páginas extras, a seção da
	página anterior passou do limite."""
	from pypdf import PdfReader

	sections = _build_sections(data, items, total)
	if not sections:
		return []
	color = _valid_color(settings.get("brand_color"), DEFAULT_COLOR)
	accent = _valid_color(settings.get("brand_accent"), DEFAULT_ACCENT)
	pages = "".join(
		f'<div class="page m"><div class="body">{html}</div></div>' for _key, html in sections
	)
	css = _css(color, accent) + """
	.page.m { height:auto; padding:22mm 0 19mm 16mm; overflow:visible; position:static; }
	.page.m .body { position:static; }
	"""
	html = f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>{pages}</body></html>'
	reader = PdfReader(io.BytesIO(render_pdf(html)))
	norm = lambda t: re.sub(r"\s+", "", (t or "")).upper()
	starts = [norm(EYEBROWS.get(k, "")) for k, _h in sections]

	problemas, atual = [], -1
	for page in reader.pages:
		text = norm(page.extract_text())
		nxt = atual + 1
		if nxt < len(sections) and starts[nxt] and text.startswith(starts[nxt]):
			atual = nxt
		elif atual >= 0 and sections[atual][0] not in problemas:
			problemas.append(sections[atual][0])
	return [
		_("A seção “{0}” tem conteúdo demais para uma página. Reduza o texto ou o número de itens, senão parte dela será cortada no PDF.").format(_(SECTION_LABELS[k]))
		for k in problemas
	]


def render_proposal_html(deal_doc, settings, items, total, client_name, data, logo_url=""):
	color = _valid_color(settings.get("brand_color"), DEFAULT_COLOR)
	accent = _valid_color(settings.get("brand_accent"), DEFAULT_ACCENT)
	brand = settings.get("brand_name") or ""

	sections = [html for _key, html in _build_sections(data, items, total)]

	total_pages = len(sections) + 1
	pages = "".join(_page(s, i + 2, total_pages, client_name, brand) for i, s in enumerate(sections))

	logo_uri = _logo_data_uri(logo_url)
	if logo_uri:
		emblem = f'<img class="cover-logo" src="{logo_uri}"><br>'
		name_html = f'<div class="cover-name">{_spaced(client_name)}</div>'
	else:
		emblem, name_html = "", f'<div class="cover-name">{_spaced(client_name)}</div>'
	subtitulo = data["capa"].get("subtitulo") or ""
	cover = (
		f'<div class="cover"><img class="cover-bg" src="{_cover_background(color)}">'
		f'<div class="cover-n">01 / {total_pages:02d}</div>'
		f'<div class="cover-mid"><table><tr><td style="vertical-align:middle;text-align:center">{emblem}{name_html}'
		f'<div class="cover-k">PROPOSTA COMERCIAL</div>'
		f'<div class="cover-s">{_e(subtitulo)}</div></td></tr></table></div>'
		f'<div class="cover-f">{_spaced(brand)} &nbsp;×&nbsp; {_spaced(client_name)}</div></div>'
	)
	return f'<html><head><meta charset="utf-8"><style>{_css(color, accent)}</style></head><body>{cover}{pages}</body></html>'


def render_pdf(html: str) -> bytes:
	"""Gera o PDF direto pelo wkhtmltopdf (paisagem, sem margens).

	Não usa o get_pdf do Frappe porque ele reescreve o HTML e derruba as fontes embutidas."""
	cmd = [
		"wkhtmltopdf", "-q", "--page-size", "A4", "--orientation", "Landscape",
		"-T", "0", "-B", "0", "-L", "0", "-R", "0",
		"--disable-smart-shrinking", "--print-media-type", "--background",
		"--encoding", "UTF-8", "--disable-javascript", "-", "-",
	]
	proc = subprocess.run(cmd, input=html.encode("utf-8"), capture_output=True, timeout=180)
	if not proc.stdout.startswith(b"%PDF"):
		frappe.log_error("Falha ao gerar PDF da proposta", proc.stderr.decode("utf-8", "ignore")[-2000:])
		frappe.throw(_("Não foi possível gerar o PDF da proposta"))
	return proc.stdout


# ---------------------------------------------------------------- contexto do negócio

def deal_context(doc) -> dict:
	from crm.api.budget import _get_client_name

	items = doc.get("budget_items") or []
	subtotal = sum(flt(i.qty) * flt(i.unit_price) for i in items)
	return {
		"settings": frappe.get_single("FCRM Settings"),
		"items": items,
		"total": subtotal - flt(doc.get("budget_discount")),
		"client_name": _get_client_name(doc),
	}


# ---------------------------------------------------------------- modelos

@frappe.whitelist()
def list_templates() -> list:
	return frappe.get_all("CRM Proposal Template", pluck="name", order_by="modified desc")


@frappe.whitelist()
def get_template(nome: str) -> dict:
	frappe.has_permission("CRM Proposal Template", "read", throw=True)
	saved = json.loads(frappe.db.get_value("CRM Proposal Template", nome, "dados") or "{}")
	return _merge(default_proposal(), saved)


@frappe.whitelist()
def save_template(nome: str, data):
	nome = (nome or "").strip()
	if not nome:
		frappe.throw(_("Informe um nome para o modelo"))
	if isinstance(data, str):
		data = json.loads(data)
	payload = json.dumps(data, ensure_ascii=False)
	if frappe.db.exists("CRM Proposal Template", nome):
		doc = frappe.get_doc("CRM Proposal Template", nome)
		doc.dados = payload
		doc.save()
	else:
		frappe.get_doc({"doctype": "CRM Proposal Template", "nome": nome, "dados": payload}).insert()
	return {"ok": True}


@frappe.whitelist()
def delete_template(nome: str):
	frappe.delete_doc("CRM Proposal Template", nome)
	return {"ok": True}


# ---------------------------------------------------------------- acompanhamento

def create_followup_task(doc, data, client_name):
	"""Cria (ou atualiza) a tarefa de cobrar a resposta na data limite da proposta."""
	dias = int(flt((data.get("investimento") or {}).get("validade_dias")))
	if dias <= 0:
		return
	limite = add_days(nowdate(), dias)
	title = _("Acompanhar proposta — {0}").format(client_name)
	filters = {
		"reference_doctype": "CRM Deal",
		"reference_docname": doc.name,
		"title": title,
		"status": ["not in", ["Done", "Canceled"]],
	}
	existing = frappe.db.get_value("CRM Task", filters, "name")
	if existing:
		frappe.db.set_value("CRM Task", existing, "due_date", f"{limite} 09:00:00")
		return
	frappe.get_doc(
		{
			"doctype": "CRM Task",
			"title": title,
			"status": "Todo",
			"priority": "Medium",
			"assigned_to": doc.get("deal_owner") or frappe.session.user,
			"reference_doctype": "CRM Deal",
			"reference_docname": doc.name,
			"due_date": f"{limite} 09:00:00",
			"description": _("A proposta vence em {0}. Entre em contato para saber a resposta.").format(
				getdate(limite).strftime("%d/%m/%Y")
			),
		}
	).insert(ignore_permissions=True)


# ---------------------------------------------------------------- envio por e-mail

@frappe.whitelist()
def get_send_defaults(deal: str) -> dict:
	doc = frappe.get_doc("CRM Deal", deal)
	doc.check_permission("read")
	email, nome = "", ""
	for c in doc.get("contacts") or []:
		if c.get("is_primary") or not email:
			email = frappe.db.get_value("CRM Contact", c.contact, "email_id") or email
			nome = frappe.db.get_value("CRM Contact", c.contact, "first_name") or nome
	email = email or doc.get("email") or ""
	nome = nome or doc.get("first_name") or ""
	brand = frappe.db.get_single_value("FCRM Settings", "brand_name") or ""
	return {
		"to": email,
		"subject": _("Proposta comercial") + (f" — {brand}" if brand else ""),
		"message": _("Olá{0},\n\nSegue em anexo o documento que preparei para você. Fico à disposição para tirar qualquer dúvida.\n\nAtenciosamente,\n{1}").format(
			f" {nome}" if nome else "", brand
		),
	}


@frappe.whitelist()
def send_document(deal: str, doc_type: str, to: str, subject: str, message: str):
	from frappe.core.doctype.communication.email import make

	from crm.api.budget import DOC_TITLES, build_document

	if not to or "@" not in to:
		frappe.throw(_("Informe um e-mail válido para o destinatário"))
	if not frappe.db.exists("Email Account", {"enable_outgoing": 1}):
		frappe.throw(_("Configure o e-mail de envio em Configurações → E-mail antes de enviar."))

	filename, content, doc = build_document(deal, doc_type)
	base = filename[:-4]
	versao = frappe.db.count(
		"File", {"attached_to_doctype": "CRM Deal", "attached_to_name": deal, "file_name": ["like", f"{DOC_TITLES[doc_type]} v%"]}
	) + 1
	client = base.split(" - ", 1)[-1] if " - " in base else deal
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{DOC_TITLES[doc_type]} v{versao} - {client}.pdf",
			"attached_to_doctype": "CRM Deal",
			"attached_to_name": deal,
			"is_private": 1,
			"content": content,
		}
	)
	file_doc.insert(ignore_permissions=True)

	body = escape_html(message or "").replace("\n", "<br>")
	make(
		doctype="CRM Deal",
		name=deal,
		content=body,
		subject=subject or DOC_TITLES[doc_type],
		recipients=to,
		communication_medium="Email",
		send_email=True,
		attachments=[file_doc.name],
	)
	return {"ok": True, "arquivo": file_doc.file_name}