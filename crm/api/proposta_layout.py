# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Layout da proposta comercial gerado pelo WeasyPrint (CSS moderno: grade, cartões, faixas).
# Substitui o layout em tabelas do wkhtmltopdf; o antigo continua em proposta.py como reserva.
# Cada seção ocupa uma folha A4 deitada e o conteúdo se distribui pela página inteira.

import io

from frappe.utils import add_days, flt, getdate, nowdate

W, H = 297, 210  # mm

# título padrão (título, parte em destaque) quando a seção não tem um
DEFAULT_TITLES = {
	"intro": ("O que este projeto", "resolve"),
	"diagnostico": ("O que", "entendemos da situação"),
	"escopo": ("O que está", "incluso"),
	"cronograma": ("Do início", "à entrega"),
	"orcamento": ("Onde o investimento", "é aplicado"),
	"ciclos": ("Visão de", "ciclos"),
	"investimento": ("Investimento", ""),
}


def _p():
	from crm.api import proposta

	return proposta


# ---------------------------------------------------------------- logo da marca

_logo_cache: dict = {}


def _logo_path(url: str) -> str:
	import frappe

	url = (url or "").split("?")[0]
	if url.startswith("/private/files/"):
		return frappe.get_site_path(*url.lstrip("/").split("/"))
	if url.startswith("/files/"):
		return frappe.get_site_path("public", *url.lstrip("/").split("/"))
	return ""


def logo_uri(url: str, fundo_escuro: bool, cor: str) -> str:
	"""Logo da marca pronto para a página: sem o fundo (o arquivo costuma ser uma foto com fundo
	liso), recortado rente ao desenho e, se ele sumiria no fundo da página, pintado de `cor`."""
	import base64

	from PIL import Image, ImageChops

	key = (url, fundo_escuro, cor)
	if key in _logo_cache:
		return _logo_cache[key]
	out = ""
	try:
		path = _logo_path(url)
		if path:
			im = Image.open(path).convert("RGBA")
			im.thumbnail((700, 700))
			w, h = im.size
			px = im.load()
			cantos = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
			alpha = im.getchannel("A")
			if not all(c[3] < 20 for c in cantos):
				# fundo liso: o que difere da cor dos cantos é o desenho
				fundo = tuple(sum(c[i] for c in cantos) // 4 for i in range(3))
				diff = ImageChops.difference(im.convert("RGB"), Image.new("RGB", im.size, fundo)).convert("L")
				alpha = ImageChops.multiply(alpha, diff.point(lambda v: 0 if v < 14 else min(255, (v - 14) * 6)))
			box = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
			if box:
				im, alpha = im.crop(box), alpha.crop(box)
				gray = im.convert("L")
				pesos = alpha.point(lambda v: 1 if v > 128 else 0)
				n = sum(pesos.getdata()) or 1
				lum = sum(g for g, p in zip(gray.getdata(), pesos.getdata()) if p) / n
				some = lum < 120 if fundo_escuro else lum > 185
				if some:
					rgb = tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))
					im = Image.new("RGBA", im.size, rgb + (255,))
				im.putalpha(alpha)
				buf = io.BytesIO()
				im.save(buf, "PNG", optimize=True)
				out = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
	except Exception:
		out = ""
	_logo_cache[key] = out
	return out


# ---------------------------------------------------------------- paleta por estilo

def palette(style: str, C: str, A: str, N: str) -> dict:
	from crm.api.estilo import mix

	if style == "cor":
		ink = mix(N, "#ffffff", 0.35)
		return {
			"page": C, "ink": ink, "muted": mix(C, "#ffffff", 0.62), "title": N, "em": mix(C, "#ffffff", 0.62),
			"card": mix(C, "#ffffff", 0.08), "line": mix(C, "#ffffff", 0.20), "label": A,
			"block": mix(C, "#000000", 0.28), "block_ink": ink, "block_muted": mix(C, "#ffffff", 0.55),
			"hl": mix(C, "#000000", 0.28), "soft": mix(C, "#ffffff", 0.14), "accent": A,
		}
	page = {"claro": N, "branco": "#ffffff"}.get(style, N)
	ink = mix(C, "#111111", 0.55)
	base = {
		"page": page, "ink": ink, "muted": mix(ink, "#ffffff", 0.42), "title": C, "em": mix(A, C, 0.45),
		"card": "#ffffff" if style != "branco" else mix(N, "#ffffff", 0.55),
		"line": mix(page, C, 0.16), "label": mix(A, C, 0.40), "hl": C, "soft": mix(page, C, 0.07), "accent": A,
	}
	if style in ("claro", "branco"):
		base.update({"block": mix(page, C, 0.10), "block_ink": C, "block_muted": mix(C, "#ffffff", 0.35)})
	else:  # escuro
		base.update({"block": C, "block_ink": "#ffffff", "block_muted": mix(C, "#ffffff", 0.72)})
	return base


# ---------------------------------------------------------------- CSS

def css(P: dict, fonts: dict) -> str:
	from crm.api import proposta_figuras, tipografia

	t, s, x, n = (tipografia.family(fonts[r]) for r in tipografia.ROLES)
	return _css_base(P, fonts, t, s, x, n) + proposta_figuras.css(P, {"t": t, "s": s, "x": x, "n": n})


def _css_base(P: dict, fonts: dict, t: str, s: str, x: str, n: str) -> str:
	from crm.api import tipografia

	return f"""
	{_p()._font_faces()}
	{tipografia.faces_css(fonts.values())}
	@page {{ size:{W}mm {H}mm; margin:0; }}
	* {{ box-sizing:border-box; }}
	html, body {{ margin:0; padding:0; }}
	body {{ font-family:{x}; color:{P['ink']}; font-size:10pt; line-height:1.45; }}
	p {{ margin:0 0 2.4mm 0; }}
	.page {{ width:{W}mm; height:{H}mm; position:relative; overflow:hidden; page-break-after:always; background:{P['page']}; }}
	.page:last-child {{ page-break-after:auto; }}
	.hdr, .ftr {{ position:absolute; left:16mm; right:16mm; display:flex; justify-content:space-between; align-items:center; font-family:{s};
		font-size:6.4pt; letter-spacing:0.28em; text-transform:uppercase; color:{P['muted']}; }}
	.hdr {{ top:9mm; font-weight:600; }}
	.ftr {{ bottom:8mm; border-top:0.25mm solid {P['line']}; padding-top:2mm; letter-spacing:0.16em; }}
	.ftr b {{ color:{P['title']}; }}
	.dia {{ display:inline-block; width:2.4mm; height:2.4mm; border:0.3mm solid {P['accent']}; transform:rotate(45deg); margin-right:2.6mm; }}
	.hdr .hl {{ display:flex; align-items:center; }}
	.hlogo {{ height:6mm; margin-right:3mm; }}
	.cover-brand {{ position:absolute; top:12mm; left:22mm; height:13mm; }}
	.cover-toasts {{ position:absolute; right:20mm; top:46mm; width:92mm; }}
	.ct {{ display:flex; gap:3mm; align-items:center; border-radius:3mm; padding:3.6mm 4mm; margin-bottom:3mm; }}
	.ct .ic {{ width:7.5mm; height:7.5mm; border-radius:50%; background:{P['accent']}; flex-shrink:0;
		display:flex; align-items:center; justify-content:center; }}
	.ct b {{ display:block; font-size:9.4pt; }}
	.ct small {{ font-size:7.6pt; line-height:1.35; }}
	/* página em bloco, sem coluna flex: no WeasyPrint, grade dentro de coluna flex estica além da folha */
	.body {{ position:absolute; top:19mm; left:16mm; right:16mm; bottom:17mm; }}
	.price > * {{ flex-shrink:0; }}
	.band.bottom {{ position:absolute; left:0; right:0; bottom:0; margin:0; }}
	.eyebrow {{ font-family:{s}; font-size:7pt; letter-spacing:0.3em; text-transform:uppercase; color:{P['label']}; font-weight:600; margin-bottom:2mm; }}
	h1 {{ font-family:{t}; font-weight:400; font-size:28pt; line-height:1.08; color:{P['title']}; margin:0 0 3mm 0; }}
	h1 em {{ font-style:italic; color:{P['em']}; }}
	.lead {{ font-size:11.5pt; line-height:1.5; color:{P['muted']}; max-width:230mm; margin-bottom:5mm; }}
	.txt {{ font-size:11pt; line-height:1.6; }}
	.grid {{ display:grid; gap:4mm; }}
	.g2 {{ grid-template-columns:1fr 1fr; }} .g3 {{ grid-template-columns:repeat(3,1fr); }} .g4 {{ grid-template-columns:repeat(4,1fr); }}
	.g5 {{ grid-template-columns:repeat(5,1fr); }}
	.card {{ background:{P['card']}; border:0.3mm solid {P['line']}; border-radius:3mm; padding:5mm 5.5mm; }}
	.card-t {{ font-family:{t}; font-size:13pt; color:{P['title']}; margin-bottom:1.6mm; line-height:1.2; }}
	.card-x {{ font-size:9.6pt; color:{P['muted']}; line-height:1.5; }}
	.card-x p {{ margin:0; }}
	.k {{ font-family:{s}; font-size:6.6pt; letter-spacing:0.22em; text-transform:uppercase; font-weight:700; color:{P['label']}; margin-bottom:1.2mm; }}
	.num {{ display:inline-block; width:9mm; height:9mm; line-height:9mm; text-align:center; border-radius:50%;
		background:{P['accent']}; color:#ffffff; font-family:{n}; font-size:11pt; margin-bottom:3mm; }}
	.block {{ background:{P['block']}; color:{P['block_ink']}; border-radius:3mm; padding:6mm 7mm; }}
	.block .k {{ color:{P['accent']}; }}
	.block .x {{ font-size:11pt; line-height:1.55; color:{P['block_ink']}; }}
	.block .x p {{ margin:0 0 1.5mm 0; }}
	.band {{ display:flex; background:{P['block']}; border-radius:3mm; margin-top:5mm; }}
	.band div {{ flex:1; padding:5mm 6mm; border-left:0.3mm solid {P['block_muted']}; }}
	.band div:first-child {{ border-left:0; }}
	.band b {{ display:block; font-family:{n}; font-weight:400; font-size:24pt; line-height:1; color:{P['block_ink']}; }}
	.band span {{ font-size:8pt; letter-spacing:0.12em; text-transform:uppercase; color:{P['block_muted']}; }}
	.stat {{ background:{P['card']}; border:0.3mm solid {P['line']}; border-top:1.2mm solid {P['accent']}; border-radius:2.5mm; padding:4mm; text-align:center; }}
	.stat b {{ display:block; font-family:{n}; font-weight:400; font-size:24pt; color:{P['title']}; line-height:1.1; }}
	.stat span {{ font-size:7.4pt; letter-spacing:0.14em; text-transform:uppercase; color:{P['muted']}; }}
	.dor .hj, .dor .cr {{ font-size:9.6pt; line-height:1.45; padding:2.4mm 3mm; border-radius:2mm; }}
	.dor .hj {{ background:{P['soft']}; color:{P['muted']}; margin-bottom:2mm; }}
	.dor .cr {{ background:{P['block']}; color:{P['block_ink']}; }}
	.dor .hj .k {{ color:{P['muted']}; margin-bottom:0.6mm; }}
	.dor .cr .k {{ color:{P['accent']}; margin-bottom:0.6mm; }}
	.esc .card {{ min-height:58mm; }}
	.cond .card {{ min-height:40mm; }}
	.steps {{ display:flex; gap:4mm; }}
	.steps .st {{ flex:1; background:{P['card']}; border:0.3mm solid {P['line']}; border-top:1.4mm solid {P['accent']}; border-radius:3mm;
		padding:5mm 5mm; min-height:62mm; }}
	.steps .dot {{ width:12mm; height:12mm; line-height:12mm; border-radius:50%; text-align:center; background:{P['hl']}; color:#ffffff;
		font-family:{n}; font-size:14pt; margin-bottom:4mm; }}
	.steps .m {{ font-family:{s}; font-size:7pt; letter-spacing:0.18em; text-transform:uppercase; color:{P['label']}; margin-bottom:1mm; }}
	.note {{ border-left:1mm solid {P['accent']}; padding:1mm 0 1mm 4mm; font-size:10pt; color:{P['muted']}; margin-top:5mm; }}
	.note p {{ margin:0; }}
	.prices {{ display:flex; gap:4mm; margin-bottom:5mm; }}
	.price {{ flex:1; position:relative; background:{P['card']}; border:0.3mm solid {P['line']}; border-radius:3.5mm; padding:6mm 6mm 5.5mm;
		display:flex; flex-direction:column; justify-content:center; min-height:54mm; }}
	/* o selo fica no topo; o conteúdo desce um pouco para não encostar nele */
	.price .selo + .k {{ margin-top:5mm; }}
	.price b.long {{ font-size:18pt; }}
	.price.hl {{ background:{P['hl']}; border-color:{P['hl']}; color:#ffffff; }}
	.price .k {{ color:{P['label']}; }}
	.price.hl .k {{ color:{P['accent']}; }}
	.price b {{ display:block; font-family:{n}; font-weight:400; font-size:26pt; line-height:1.05; color:{P['title']}; margin:1.5mm 0 1.5mm; }}
	.price.hl b {{ color:#ffffff; }}
	.price .d {{ font-size:9pt; line-height:1.4; color:{P['muted']}; }}
	.price.hl .d {{ color:#e3e6e4; }}
	.selo {{ position:absolute; top:4.5mm; left:6mm; background:{P['accent']}; color:#ffffff; font-size:7pt; font-weight:700;
		letter-spacing:0.06em; padding:1mm 3mm; border-radius:4mm; }}
	.cond .card-t {{ font-size:11pt; }}
	.items {{ width:100%; border-collapse:collapse; font-size:9pt; margin-bottom:4mm; }}
	.items th {{ text-align:left; font-size:6.8pt; letter-spacing:0.16em; text-transform:uppercase; color:{P['muted']};
		border-bottom:0.3mm solid {P['line']}; padding:1.6mm 1mm; }}
	.items td {{ padding:1.8mm 1mm; border-bottom:0.2mm solid {P['line']}; }}
	.items .r {{ text-align:right; }} .items .c {{ text-align:center; }}
	.valid {{ font-size:9pt; color:{P['muted']}; margin-top:4mm; }}
	.cic {{ display:flex; gap:4mm; flex:1; }}
	.cic > div {{ flex:1; border-radius:3mm; padding:7mm; }}
	.cic .d1 {{ background:{P['block']}; color:{P['block_ink']}; }}
	.cic .d2 {{ background:{P['card']}; border:0.3mm solid {P['line']}; }}
	.cic .t {{ font-family:{t}; font-size:16pt; margin:1mm 0; }}
	.cic .v {{ font-family:{n}; font-size:13pt; color:{P['accent']}; margin-bottom:3mm; }}
	.cic .pt {{ font-size:9.6pt; margin-top:1.2mm; }}
	.quote {{ font-family:{t}; font-style:italic; text-align:center; font-size:15pt; color:{P['title']}; margin-top:5mm; }}
	.cover {{ width:{W}mm; height:{H}mm; position:relative; overflow:hidden; page-break-after:always; background:{P['page']}; }}
	.cover-bg {{ position:absolute; top:0; left:0; width:{W}mm; height:{H}mm; }}
	.cover-frame {{ position:absolute; top:9mm; left:9mm; right:9mm; bottom:9mm; border:0.35mm solid {P['line']}; }}
	.cover-in {{ position:absolute; left:22mm; right:22mm; top:0; bottom:44mm; display:flex; flex-direction:column; justify-content:center; }}
	.cover-logo {{ max-height:26mm; max-width:90mm; margin-bottom:8mm; align-self:flex-start; }}
	.cover-k {{ font-family:{s}; font-size:8pt; letter-spacing:0.45em; text-transform:uppercase; font-weight:700; color:{P['accent']}; margin-bottom:5mm; }}
	.cover-name {{ font-family:{t}; font-size:40pt; line-height:1.05; }}
	.cover-s {{ font-size:13pt; margin-top:5mm; max-width:190mm; line-height:1.45; }}
	.cover-meta {{ position:absolute; left:22mm; right:22mm; bottom:16mm; display:flex; gap:12mm; padding-top:5mm; }}
	.cover-meta span {{ display:block; font-family:{s}; font-size:6.6pt; letter-spacing:0.28em; text-transform:uppercase; margin-bottom:1.2mm; color:{P['accent']}; }}
	.cover-meta div {{ font-size:10pt; }}
	.cover-n {{ position:absolute; top:12mm; right:16mm; font-family:{s}; font-size:6.6pt; letter-spacing:0.3em; color:{P['accent']}; font-weight:700; }}
	"""


def cover_css(P: dict, dark: bool) -> str:
	"""Capa escura: texto claro sobre o fundo com brilho; capa clara: texto na cor da marca."""
	if dark:
		return """
		.cover-name { color:#ffffff; } .cover-s, .cover-meta div { color:#dfe5e3; }
		.cover-meta { border-top:0.3mm solid rgba(255,255,255,0.22); }
		.ct { background:rgba(255,255,255,0.10); border:0.3mm solid rgba(255,255,255,0.20); color:#ffffff; }
		.ct small { color:#d3dcda; }
		"""
	return f"""
	.cover-name {{ color:{P['title']}; }} .cover-s, .cover-meta div {{ color:{P['muted']}; }}
	.cover-meta {{ border-top:0.3mm solid {P['line']}; }}
	.ct {{ background:{P['card']}; border:0.3mm solid {P['line']}; color:{P['ink']}; }}
	.ct small {{ color:{P['muted']}; }}
	"""


# ---------------------------------------------------------------- blocos

def _title(key, d, lead_key="subtitulo"):
	pp = _p()
	titulo, destaque = (d.get("titulo") or "").strip(), (d.get("destaque") or "").strip()
	if not (titulo or destaque):
		titulo, destaque = DEFAULT_TITLES[key]
	html = f'<div class="eyebrow">{pp._e(d.get("eyebrow") or pp.EYEBROWS.get(key, ""))}</div>'
	html += f"<h1>{pp._e(titulo)} <em>{pp._e(destaque)}</em></h1>"
	if lead_key and d.get(lead_key):
		html += f'<div class="lead">{pp._e(d.get(lead_key))}</div>'
	return html


def _filled(rows, *keys):
	return [r for r in (rows or []) if isinstance(r, dict) and any(str(r.get(k) or "").strip() for k in keys)]


def _cols(n: int) -> str:
	return "g" + str({1: 1, 2: 2, 3: 3, 4: 2, 5: 3, 6: 3, 9: 3}.get(n, 4)) if n > 1 else ""


def _cards(rows, cols_class=None, extra=""):
	pp = _p()
	rows = _filled(rows, "titulo", "texto")
	if not rows:
		return ""
	cells = "".join(
		f'<div class="card"><div class="card-t">{pp._e(r.get("titulo"))}</div>'
		f'<div class="card-x">{pp._rich(r.get("texto"))}</div></div>'
		for r in rows
	)
	return f'<div class="grid {cols_class or _cols(len(rows))} {extra}">{cells}</div>'


def _band(nums):
	pp = _p()
	nums = _filled(nums, "valor", "rotulo")
	if not nums:
		return ""
	cells = "".join(f'<div><b>{pp._e(n.get("valor"))}</b><span>{pp._e(n.get("rotulo"))}</span></div>' for n in nums)
	return f'<div class="band">{cells}</div>'


def _block(titulo, texto):
	pp = _p()
	if not (titulo or texto):
		return ""
	return f'<div class="block"><div class="k">{pp._e(titulo)}</div><div class="x">{pp._rich(texto)}</div></div>'


# ---------------------------------------------------------------- seções

def sec_intro(d):
	pp = _p()
	html = _title("intro", d, None)
	cards = _filled(d.get("cartoes"), "titulo", "texto")
	if cards:
		right = (f'<div class="eyebrow">{pp._e(d.get("cartoes_titulo"))}</div>' if d.get("cartoes_titulo") else "") + _cards(cards, "g2" if len(cards) > 1 else "")
		html += (
			f'<div class="grid" style="grid-template-columns:1.1fr 1fr;gap:9mm;align-items:start">'
			f'<div class="txt">{pp._rich(d.get("texto"))}</div><div>{right}</div></div>'
		)
	else:
		html += f'<div class="txt" style="font-size:13pt;max-width:225mm;line-height:1.65">{pp._rich(d.get("texto"))}</div>'
	band = _band(d.get("numeros"))
	return html + band.replace('class="band"', 'class="band bottom"', 1)


def _dor(r):
	pp = _p()
	if not str(r.get("solucao") or "").strip():
		return f'<div class="card"><div class="card-t">{pp._e(r.get("titulo"))}</div><div class="card-x">{pp._rich(r.get("texto"))}</div></div>'
	return (
		f'<div class="card dor"><div class="card-t">{pp._e(r.get("titulo"))}</div>'
		f'<div class="hj"><div class="k">Hoje</div>{pp._e(r.get("texto"))}</div>'
		f'<div class="cr"><div class="k">Com a proposta</div>{pp._e(r.get("solucao"))}</div></div>'
	)


def sec_diag(d):
	pp = _p()
	html = _title("diagnostico", d)
	nums = _filled(d.get("numeros"), "valor", "rotulo")
	if nums:
		cells = "".join(f'<div class="stat"><b>{pp._e(n.get("valor"))}</b><span>{pp._e(n.get("rotulo"))}</span></div>' for n in nums)
		html += f'<div class="grid g{min(len(nums), 5)}" style="margin-bottom:4mm">{cells}</div>'
	faixa = _block(d.get("faixa_titulo"), d.get("faixa_texto"))
	if faixa:
		html += f'<div style="margin-bottom:4mm">{faixa}</div>'
	rows = _filled(d.get("cartoes"), "titulo", "texto", "solucao")
	if rows:
		html += f'<div class="grid {_cols(len(rows))}">{"".join(_dor(r) for r in rows)}</div>'
	if d.get("conclusao"):
		html += f'<div class="note">{pp._rich(d.get("conclusao"))}</div>'
	return html


def sec_escopo(d):
	pp = _p()
	html = _title("escopo", d)
	rows = _filled(d.get("itens"), "titulo", "texto")
	cells = "".join(
		f'<div class="card"><span class="num">{i + 1}</span><div class="card-t">{pp._e(r.get("titulo"))}</div>'
		f'<div class="card-x">{pp._rich(r.get("texto"))}</div></div>'
		for i, r in enumerate(rows)
	)
	return html + f'<div class="grid esc {_cols(len(rows))}">{cells}</div>'


def sec_crono(d):
	pp = _p()
	html = _title("cronograma", d)
	etapas = _filled(d.get("etapas"), "marco", "titulo", "texto")
	if etapas:
		cells = "".join(
			f'<div class="st"><div class="dot">{i + 1}</div>'
			+ (f'<div class="m">{pp._e(e.get("marco"))}</div>' if e.get("marco") else "")
			+ f'<div class="card-t">{pp._e(e.get("titulo"))}</div><div class="card-x">{pp._e(e.get("texto"))}</div></div>'
			for i, e in enumerate(etapas)
		)
		html += f'<div class="steps" style="margin-top:2mm">{cells}</div>'
	faixa = _block(d.get("faixa_titulo"), d.get("faixa_texto"))
	if faixa:
		html += f'<div style="margin-top:6mm">{faixa}</div>'
	if d.get("nota"):
		html += f'<div class="note">{pp._rich(d.get("nota"))}</div>'
	return html


def sec_orc(d):
	html = _title("orcamento", d) + _cards(d.get("cartoes"))
	faixa = _block(d.get("faixa_titulo"), d.get("faixa_texto"))
	return html + (f'<div style="margin-top:4mm">{faixa}</div>' if faixa else "")


def sec_ciclos(d):
	pp = _p()
	html = _title("ciclos", d)
	blocos = _filled(d.get("blocos"), "rotulo", "titulo", "detalhe", "texto", "pontos")[:2]
	cells = ""
	for i, b in enumerate(blocos):
		pontos = "".join(f'<div class="pt">› {pp._e(p.strip())}</div>' for p in (b.get("pontos") or "").split("\n") if p.strip())
		cells += (
			f'<div class="d{1 if i == 0 else 2}"><div class="k">{pp._e(b.get("rotulo"))}</div><div class="t">{pp._e(b.get("titulo"))}</div>'
			f'<div class="v">{pp._e(b.get("detalhe"))}</div><div>{pp._e(b.get("texto"))}</div>{pontos}</div>'
		)
	html += f'<div class="cic">{cells}</div>'
	if d.get("citacao"):
		html += f'<div class="quote">"{pp._e(d.get("citacao"))}"</div>'
	return html


def _price_cards(d, items, total, discount):
	"""Cartões de preço: as opções escritas na proposta; sem elas, um cartão por item do orçamento + o total."""
	pp = _p()
	opcoes = _filled(d.get("opcoes"), "rotulo", "valor")
	cards = []
	if opcoes:
		hl = next((i for i, o in enumerate(opcoes) if str(o.get("selo") or "").strip()), 0)
		for i, o in enumerate(opcoes):
			cards.append((i == hl, o.get("rotulo"), o.get("valor"), o.get("detalhe"), o.get("selo")))
	else:
		for it in items[:3]:
			qty = flt(it.qty)
			valor = pp._fmt_money_short(qty * flt(it.unit_price))
			det = f"{qty:g} × {pp._fmt_currency(it.unit_price)}" if qty != 1 else ""
			cards.append((False, it.description, valor, det, ""))
		if len(items) != 1 or discount:
			det = f"Já com desconto de {pp._fmt_currency(discount)}" if discount else (d.get("valor_sufixo") or "")
			cards.append((True, "Total", pp._fmt_money_short(total), det, ""))
		elif cards:
			cards[0] = (True,) + cards[0][1:]
	html = "".join(
		f'<div class="price{" hl" if hl else ""}">'
		+ (f'<span class="selo">{pp._e(selo)}</span>' if selo else "")
		+ f'<div class="k">{pp._e(rotulo)}</div><b{" class=long" if len(str(valor or "")) > 12 else ""}>{pp._e(valor)}</b>'
		+ (f'<div class="d">{pp._e(det)}</div>' if det else "")
		+ "</div>"
		for hl, rotulo, valor, det, selo in cards
	)
	return f'<div class="prices">{html}</div>' if html else ""


def sec_invest(d, items, total, discount=0):
	pp = _p()
	html = _title("investimento", d, None)
	html += _price_cards(d, items, total, discount)
	if not _filled(d.get("opcoes"), "rotulo", "valor") and len(items) > 3:
		rows = "".join(
			f'<tr><td>{pp._e(i.description)}</td><td class="c">{flt(i.qty):g}</td>'
			f'<td class="r">{pp._fmt_currency(i.unit_price)}</td><td class="r">{pp._fmt_currency(flt(i.qty) * flt(i.unit_price))}</td></tr>'
			for i in items
		)
		html += f'<table class="items"><tr><th>Descrição</th><th class="c">Qtd</th><th class="r">Valor unitário</th><th class="r">Subtotal</th></tr>{rows}</table>'
	plano = ""
	if d.get("plano_titulo") or d.get("plano_texto"):
		plano = _block(d.get("plano_rotulo") or d.get("plano_titulo"), (f'**{d.get("plano_titulo")}**\n\n' if d.get("plano_rotulo") and d.get("plano_titulo") else "") + (d.get("plano_texto") or ""))
	extras = [b for b in (plano, _block(d.get("recomendado_titulo"), d.get("recomendado_texto")), _block(d.get("fases_titulo"), d.get("fases_texto"))) if b]
	conds = _filled(d.get("condicoes"), "texto")
	if extras:
		html += f'<div class="grid g{min(len(extras), 3)}" style="margin-bottom:4mm">{"".join(extras)}</div>'
	if conds:
		html += f'<div class="eyebrow" style="margin-top:1mm">Condições</div>{_cards(conds, extra="cond")}'
	if d.get("validade"):
		html += f'<div class="valid">{pp._e(d.get("validade"))}</div>'
	return html


def didactic_pages(data) -> list[dict]:
	"""Páginas "texto + figura": as escritas na proposta (pela IA ou à mão); sem nenhuma, e com o
	automático ligado, o sistema monta até 3 a partir do escopo, para a proposta nunca ser só texto."""
	from crm.api import proposta_figuras

	d = data.get("didatico") or {}
	pages = _filled(d.get("paginas"), "titulo", "texto", "figura_linhas")
	if pages or not int(flt(d.get("automatico", 1))):
		return pages[:6]
	return proposta_figuras.auto_pages((data.get("escopo") or {}).get("itens"))


def sec_didatico(pg, client_name):
	from crm.api import proposta_figuras

	pp = _p()
	fig = proposta_figuras.render(pg.get("figura"), pg.get("figura_titulo"), pg.get("figura_linhas"), client_name)
	titulo, destaque = (pg.get("titulo") or "").strip(), (pg.get("destaque") or "").strip()
	if not (fig or titulo or pg.get("texto")):
		return ""
	# cada ponto: "Título | explicação curta" (a explicação aparece embaixo, em letra menor)
	pontos = ""
	for i, ln in enumerate(ln.strip(" -•") for ln in str(pg.get("pontos") or "").splitlines() if ln.strip(" -•")):
		titulo_pt, _sep, expl = ln.partition("|")
		pontos += (
			f'<div class="pt"><i>{i + 1:02d}</i><div><b>{pp._e(titulo_pt.strip())}</b>'
			+ (f"<small>{pp._e(expl.strip())}</small>" if expl.strip() else "") + "</div></div>"
		)
	left = (
		f'<div class="tx"><div class="eyebrow">Na prática</div><h1>{pp._e(titulo)} <em>{pp._e(destaque)}</em></h1>'
		+ (f'<div class="lead">{pp._e(pg.get("texto"))}</div>' if pg.get("texto") else "")
		+ (f'<div class="pts">{pontos}</div>' if pontos else "") + "</div>"
	)
	right = f'<div class="mock">{fig}<div class="cap">Exemplo ilustrativo</div></div>' if fig else ""
	return f'<div class="dida">{left}{right}</div>'


def build_sections(data, items, total, discount=0, client_name=""):
	"""Lista de (chave, html) das seções com conteúdo, na ordem do documento."""
	pp = _p()
	has = pp._has
	out = []
	if has(data["intro"], "titulo", "destaque", "texto", "cartoes", "numeros"):
		out.append(("intro", sec_intro(data["intro"])))
	if has(data["diagnostico"], "titulo", "destaque", "numeros", "faixa_titulo", "faixa_texto", "cartoes", "conclusao"):
		out.append(("diagnostico", sec_diag(data["diagnostico"])))
	for pg in didactic_pages(data):
		html = sec_didatico(pg, client_name)
		if html:
			out.append(("didatico", html))
	if has(data["escopo"], "titulo", "destaque", "itens"):
		out.append(("escopo", sec_escopo(data["escopo"])))
	if has(data["cronograma"], "titulo", "destaque", "etapas", "faixa_titulo", "faixa_texto", "nota"):
		out.append(("cronograma", sec_crono(data["cronograma"])))
	if has(data["orcamento"], "titulo", "destaque", "cartoes", "faixa_titulo", "faixa_texto"):
		out.append(("orcamento", sec_orc(data["orcamento"])))
	if has(data["ciclos"], "titulo", "destaque", "blocos", "citacao"):
		out.append(("ciclos", sec_ciclos(data["ciclos"])))
	inv = dict(data["investimento"])
	if items or total or _filled(inv.get("opcoes"), "rotulo", "valor"):
		inv["validade"] = pp.validity_text(inv)
		out.append(("investimento", sec_invest(inv, items, total, discount)))
	return out


# ---------------------------------------------------------------- documento

def _page(inner, n, total, client, brand, logo=""):
	pp = _p()
	marca = f'<img class="hlogo" src="{logo}">' if logo else '<span class="dia"></span>'
	return (
		f'<div class="page"><div class="hdr"><span class="hl">{marca}{pp._e(brand + " · " if brand else "")}{pp._e(client)}</span><span>{n:02d} / {total:02d}</span></div>'
		f'<div class="body">{inner}</div>'
		f'<div class="ftr"><span>{pp._e(brand)} × <b>{pp._e(client)}</b></span><span>Proposta comercial · {n:02d} / {total:02d}</span></div></div>'
	)


def _cover_toasts(data) -> str:
	"""Avisos na capa (como no material feito à mão): os primeiros itens do escopo, já "acontecendo"."""
	from crm.api import proposta_figuras

	pp = _p()
	itens = _filled((data.get("escopo") or {}).get("itens"), "titulo")[:4]
	if len(itens) < 3:
		return ""
	cells = "".join(
		f'<div class="ct"><span class="ic">{proposta_figuras.CHECK}</span><div><b>{pp._e(it.get("titulo"))}</b>'
		+ (f'<small>{pp._e(_curto(it.get("texto")))}</small>' if it.get("texto") else "") + "</div></div>"
		for it in itens
	)
	return f'<div class="cover-toasts">{cells}</div>'


def _curto(texto, limite=70) -> str:
	texto = " ".join(str(texto or "").split())
	return texto if len(texto) <= limite else texto[: limite - 1].rsplit(" ", 1)[0] + "…"


def _cover(P, style, color, client, brand, data, logo_uri, total_pages, brand_logo=""):
	from crm.api import estilo

	pp = _p()
	dark = estilo.is_dark_cover(style)
	backdrop = f'<img class="cover-bg" src="{pp._cover_background(color)}">' if dark else '<div class="cover-frame"></div>'
	emblem = f'<img class="cover-logo" src="{logo_uri}">' if logo_uri else ""
	toasts = _cover_toasts(data)
	backdrop += (f'<img class="cover-brand" src="{brand_logo}">' if brand_logo else "") + toasts
	if toasts:
		backdrop += '<style>.cover-in { right:120mm; } .cover-name { font-size:34pt; }</style>'
	sub = (data["capa"].get("subtitulo") or "").strip()
	meta = [("Para", client), ("Data", getdate(nowdate()).strftime("%d/%m/%Y"))]
	dias = int(flt(data["investimento"].get("validade_dias")))
	if dias > 0:
		meta.append(("Validade", f"até {getdate(add_days(nowdate(), dias)).strftime('%d/%m/%Y')}"))
	if brand:
		meta.append(("Por", brand))
	meta_html = "".join(f"<div><span>{pp._e(k)}</span>{pp._e(v)}</div>" for k, v in meta)
	return (
		f'<div class="cover">{backdrop}<div class="cover-n">01 / {total_pages:02d}</div>'
		f'<div class="cover-in">{emblem}<div class="cover-k">Proposta comercial</div>'
		f'<div class="cover-name">{pp._e(client)}</div>'
		+ (f'<div class="cover-s">{pp._e(sub)}</div>' if sub else "")
		+ f'</div><div class="cover-meta">{meta_html}</div></div>'
	)


def render_html(settings, items, total, client_name, data, logo_url="", discount=0):
	from crm.api import estilo, tipografia

	pp = _p()
	pal = estilo.resolve(settings, (data.get("capa") or {}).get("tema"))
	fonts = tipografia.resolve(settings, "proposta")
	P = palette(pal["estilo"], pal["cor"], pal["destaque"], pal["neutra"])
	brand = settings.get("brand_name") or ""
	sections = [h for _k, h in build_sections(data, items, total, discount, client_name)]
	total_pages = len(sections) + 1
	marca = settings.get("brand_logo") or ""
	dark_cover = estilo.is_dark_cover(pal["estilo"])
	hlogo = logo_uri(marca, pal["estilo"] == "cor", "#ffffff" if pal["estilo"] == "cor" else P["title"])
	clogo = logo_uri(marca, dark_cover, "#ffffff" if dark_cover else P["title"])
	pages = "".join(_page(s, i + 2, total_pages, client_name, brand, hlogo) for i, s in enumerate(sections))
	cover = _cover(P, pal["estilo"], pal["cor"], client_name, brand, data, pp._logo_data_uri(logo_url), total_pages, clogo)
	style = css(P, fonts) + cover_css(P, estilo.is_dark_cover(pal["estilo"]))
	return f'<html><head><meta charset="utf-8"><style>{style}</style></head><body>{cover}{pages}</body></html>'


def render_pdf(html: str) -> bytes:
	from weasyprint import HTML

	return HTML(string=html).write_pdf()


def overflowing(settings, items, total, client_name, data, discount=0) -> list[str]:
	"""Seções cujo conteúdo não cabe na folha (o excesso seria cortado): cada uma é
	renderizada com altura livre e conta quantas páginas ocupa."""
	from weasyprint import HTML

	from crm.api import estilo, tipografia

	pal = estilo.resolve(settings, (data.get("capa") or {}).get("tema"))
	P = palette(pal["estilo"], pal["cor"], pal["destaque"], pal["neutra"])
	base = css(P, tipografia.resolve(settings, "proposta")) + """
	.page.m { height:auto; min-height:0; overflow:visible; padding:19mm 16mm 17mm; }
	/* em bloco (não flex): o WeasyPrint só quebra página em bloco, e é a página extra que denuncia o excesso */
	.page.m .body { position:static; display:block; }
	.page.m .band.bottom { position:static; margin-top:5mm; }
	.page.m .dida { height:auto; } .page.m .mock { height:150mm; }
	"""
	out = []
	for key, html in build_sections(data, items, total, discount, client_name):
		doc = f'<html><head><meta charset="utf-8"><style>{base}</style></head><body><div class="page m"><div class="body">{html}</div></div></body></html>'
		if len(HTML(string=doc).render().pages) > 1:
			out.append(key)
	return out
