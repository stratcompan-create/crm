# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Tipografia dos documentos: cada escritório escolhe a fonte de quatro funções
# (título, subtítulo, texto e números), separadamente ou por um par pronto.
# As fontes ficam dentro do CRM (crm/public/fonts, licença aberta OFL) e são embutidas no PDF.

import base64
import os

import frappe

ROLES = ("titulo", "subtitulo", "texto", "numeros")
ROLE_LABELS = {"titulo": "Título", "subtitulo": "Subtítulo", "texto": "Texto", "numeros": "Números"}

N, I = "normal", "italic"


def _files(prefix: str, italic: bool = True, bold: bool = True) -> list:
	out = [(400, N, f"{prefix}-Regular.ttf")]
	if bold:
		out.append((700, N, f"{prefix}-Bold.ttf"))
	if italic:
		out.append((400, I, f"{prefix}-Italic.ttf"))
	return out


# chave -> (nome, categoria, arquivos [(peso, estilo, arquivo)], alternativa se a fonte faltar)
FONTS = {
	"lora": ("Lora", "Serifada", [(400, N, "Lora-Regular.ttf"), (600, N, "Lora-SemiBold.ttf"), (700, N, "Lora-Bold.ttf"), (400, I, "Lora-Italic.ttf")], "Georgia, serif"),
	"playfair": ("Playfair Display", "Serifada", _files("PlayfairDisplay"), "Georgia, serif"),
	"cormorant": ("Cormorant Garamond", "Serifada", _files("CormorantGaramond"), "Georgia, serif"),
	"garamond": ("EB Garamond", "Serifada", _files("EBGaramond"), "Georgia, serif"),
	"merriweather": ("Merriweather", "Serifada", _files("Merriweather"), "Georgia, serif"),
	"baskerville": ("Libre Baskerville", "Serifada", _files("LibreBaskerville"), "Georgia, serif"),
	"dmserif": ("DM Serif Display", "Serifada de destaque", [(400, N, "DMSerifDisplay-Regular.ttf"), (700, N, "DMSerifDisplay-Regular.ttf"), (400, I, "DMSerifDisplay-Italic.ttf")], "Georgia, serif"),
	"poppins": ("Poppins", "Sem serifa", [(300, N, "Poppins-Light.ttf"), (400, N, "Poppins-Regular.ttf"), (500, N, "Poppins-Medium.ttf"), (600, N, "Poppins-SemiBold.ttf"), (700, N, "Poppins-Bold.ttf")], "Arial, sans-serif"),
	"inter": ("Inter", "Sem serifa", _files("Inter", italic=False), "Arial, sans-serif"),
	"montserrat": ("Montserrat", "Sem serifa", _files("Montserrat", italic=False), "Arial, sans-serif"),
	"lato": ("Lato", "Sem serifa", _files("Lato"), "Arial, sans-serif"),
	"opensans": ("Open Sans", "Sem serifa", _files("OpenSans", italic=False), "Arial, sans-serif"),
	"raleway": ("Raleway", "Sem serifa", _files("Raleway", italic=False), "Arial, sans-serif"),
	"dmsans": ("DM Sans", "Sem serifa", _files("DMSans", italic=False), "Arial, sans-serif"),
	"spacegrotesk": ("Space Grotesk", "Sem serifa (tecnologia)", _files("SpaceGrotesk", italic=False), "Arial, sans-serif"),
}
BASE_FONTS = ("lora", "poppins")  # já embutidas pelo CSS base da proposta

# funções -> fonte, quando o escritório não escolheu
DEFAULTS = {
	"proposta": {"titulo": "lora", "subtitulo": "poppins", "texto": "poppins", "numeros": "lora"},
	"documento": {"titulo": "lora", "subtitulo": "poppins", "texto": "lora", "numeros": "lora"},
}

# pares prontos (chave -> nome, descrição, fontes)
PRESETS = {
	"editorial": ("Editorial", "Título serifado elegante e texto limpo.", {"titulo": "lora", "subtitulo": "poppins", "texto": "poppins", "numeros": "lora"}),
	"classico": ("Clássico", "Playfair Display nos títulos, com texto em Lato.", {"titulo": "playfair", "subtitulo": "lato", "texto": "lato", "numeros": "playfair"}),
	"moderno": ("Moderno", "Montserrat e Inter: geométrico e atual.", {"titulo": "montserrat", "subtitulo": "inter", "texto": "inter", "numeros": "montserrat"}),
	"elegante": ("Elegante", "Cormorant Garamond nos títulos, delicado e sofisticado.", {"titulo": "cormorant", "subtitulo": "raleway", "texto": "lato", "numeros": "playfair"}),
	"tradicional": ("Tradicional", "Tudo serifado, no estilo de escritório de advocacia.", {"titulo": "baskerville", "subtitulo": "lato", "texto": "baskerville", "numeros": "baskerville"}),
	"tecnologia": ("Tecnologia", "Space Grotesk e Inter, para marcas de tecnologia.", {"titulo": "spacegrotesk", "subtitulo": "inter", "texto": "inter", "numeros": "spacegrotesk"}),
}

_cache: dict = {}


def _dir() -> str:
	return frappe.get_app_path("crm", "public", "fonts")


def family(key: str) -> str:
	"""Nome CSS da família. Lora e Poppins mantêm os nomes do CSS base."""
	name, _cat, _files_, fallback = FONTS[key]
	css = name if key in BASE_FONTS else f"F-{key}"
	return f"'{css}', {fallback}"


def resolve(settings, kind: str = "proposta") -> dict:
	"""Fonte de cada função: a escolhida em Marca, senão o padrão do tipo de documento."""
	out = {}
	for role in ROLES:
		value = (settings.get(f"fonte_{role}") or "").strip()
		out[role] = value if value in FONTS else DEFAULTS[kind][role]
	return out


def faces_css(keys) -> str:
	"""@font-face embutido (base64) das fontes escolhidas que o CSS base ainda não traz."""
	css = []
	for key in sorted({k for k in keys if k not in BASE_FONTS}):
		if key not in _cache:
			parts = []
			for weight, style, file in FONTS[key][2]:
				path = os.path.join(_dir(), file)
				if not os.path.isfile(path):
					continue
				with open(path, "rb") as fh:
					data = base64.b64encode(fh.read()).decode()
				parts.append(
					f"@font-face {{ font-family:'F-{key}'; font-weight:{weight}; font-style:{style}; "
					f"src:url(data:font/truetype;base64,{data}) format('truetype'); }}"
				)
			_cache[key] = "\n".join(parts)
		css.append(_cache[key])
	return "\n".join(css)


def css_proposal(fonts: dict) -> str:
	t, s, x, n = (family(fonts[r]) for r in ROLES)
	return f"""
	h1, h1 i, .cover-name, .card-t, .esc-t, .plano-t, .cic-t, .cita {{ font-family:{t}; }}
	.cover-name {{ white-space:nowrap; }}
	.eyebrow, .sub, .callout-t, .cover-k, .cover-s, .etp-t, .hdr, .ftr, .cover-n, .cover-f, .band-l, .stat-l, .val-s {{ font-family:{s}; }}
	body, .txt, .card-x, .esc-x, .etp-x, .nota, .callout-x, .cic-x, .pt, .cnd, table.items, table.items td, table.items th {{ font-family:{x}; }}
	.stat-v, .band-v, .val-v, .esc-n, .etp-m, .cic-v, .hdr .r, .ftr .r, table.items td.r, table.items td.c {{ font-family:{n}; }}
	"""


def css_document(fonts: dict) -> str:
	t, s, x, _n = (family(fonts[r]) for r in ROLES)
	return f"""
	body {{ font-family:{x}; }}
	h1, h2 {{ font-family:{t}; }}
	.head td, .head .brand {{ font-family:{s}; }}
	"""


@frappe.whitelist()
def get_catalog() -> dict:
	"""Fontes, pares prontos e padrões, para a tela de Marca (a prévia carrega as mesmas fontes)."""
	fonts = []
	for key, (name, cat, files, _fb) in FONTS.items():
		fonts.append(
			{
				"chave": key,
				"nome": name,
				"categoria": cat,
				"css": family(key).split(",")[0].strip("'"),
				"arquivos": [
					{"peso": w, "estilo": st, "url": f"/assets/crm/fonts/{f}"}
					for w, st, f in files
					if os.path.isfile(os.path.join(_dir(), f))
				],
			}
		)
	return {
		"fontes": fonts,
		"pares": [{"chave": k, "nome": v[0], "descricao": v[1], "fontes": v[2]} for k, v in PRESETS.items()],
		"padrao": DEFAULTS["proposta"],
		"funcoes": [{"chave": r, "nome": ROLE_LABELS[r]} for r in ROLES],
	}
