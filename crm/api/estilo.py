# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Estilos de cor dos documentos (proposta, contratos, relatórios).
# A marca tem três cores: principal (ex.: verde escuro), destaque e fundo neutro (ex.: bege).
# O estilo define QUAL delas predomina no documento.

import re

DEFAULT_NEUTRAL = "#f4f2ed"

# chave -> (nome, descrição)
STYLES = {
	"escuro": ("Cor da marca nos destaques", "Capa e faixas na cor principal, páginas em fundo neutro."),
	"claro": ("Fundo neutro", "Predomina o fundo neutro (bege). A cor principal aparece só nos textos e detalhes."),
	"branco": ("Fundo branco", "Visual limpo: páginas brancas, com detalhes na cor da marca."),
	"cor": ("Cor da marca em tudo", "Todas as páginas na cor principal, com texto claro."),
}
DEFAULT_STYLE = "escuro"


def valid_hex(value: str, fallback: str) -> str:
	value = (value or "").strip()
	return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback


def mix(color: str, other: str, ratio: float) -> str:
	a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
	b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
	return "#" + "".join(f"{round(x * (1 - ratio) + y * ratio):02x}" for x, y in zip(a, b))


def resolve(settings, override: str | None = None) -> dict:
	"""Estilo e paleta a usar: o do documento, senão o padrão do escritório, senão o escuro."""
	style = override or settings.get("documento_estilo") or DEFAULT_STYLE
	if style not in STYLES:
		style = DEFAULT_STYLE
	return {
		"estilo": style,
		"cor": valid_hex(settings.get("brand_color"), "#042d3c"),
		"destaque": valid_hex(settings.get("brand_accent"), "#8aa1a9"),
		"neutra": valid_hex(settings.get("brand_neutral"), DEFAULT_NEUTRAL),
	}


def is_dark_cover(style: str) -> bool:
	return style in ("escuro", "cor")


def theme_css(style: str, C: str, A: str, N: str) -> str:
	"""Ajustes que se somam ao CSS base da proposta (o estilo 'escuro' é o próprio CSS base)."""
	if style == "escuro":
		return f".page {{ background:{N}; }}"
	if style in ("claro", "branco"):
		page = N if style == "claro" else "#ffffff"
		card = "#ffffff" if style == "claro" else mix(N, "#ffffff", 0.55)
		block = mix(page, C, 0.10)
		line = mix(page, C, 0.22)
		muted = mix(C, "#ffffff", 0.35)
		return f"""
		.page {{ background:{page}; }}
		.card, .stat, .box {{ background:{card}; }}
		.band {{ background:{block}; border-top:0.3mm solid {line}; border-bottom:0.3mm solid {line}; }}
		.band-c {{ border-left:0.25mm solid {line}; }}
		.band-v {{ color:{C}; }}
		.callout-d {{ background:{block}; color:{C}; border:0.25mm solid {line}; }}
		.cic-d {{ background:{block}; color:{C}; border:0.25mm solid {line}; }}
		.cic-d .cic-x {{ color:{muted}; }}
		.cic-v {{ color:{muted}; }}
		.cic-l, .callout-l {{ background:{mix(page, C, 0.04)}; }}
		.plano {{ background:{block}; color:{C}; border:0.25mm solid {line}; }}
		.plano-x {{ color:{muted}; }}
		.val-v {{ color:{C}; }}
		.cover {{ background:{page}; }}
		.cover-frame {{ position:absolute; top:9mm; left:9mm; right:9mm; bottom:9mm; border:0.35mm solid {mix(page, C, 0.30)}; }}
		.cover-name {{ color:{C}; border-bottom:0.6mm solid {A}; }}
		.cover-k {{ color:{A}; }}
		.cover-s {{ color:{muted}; }}
		.cover-s b {{ color:{C}; }}
		.cover-n, .cover-f {{ color:{muted}; }}
		"""
	# "cor": páginas inteiras na cor principal, texto claro
	dark = mix(C, "#000000", 0.28)
	muted = mix(C, "#ffffff", 0.62)
	card = mix(C, "#ffffff", 0.08)
	line = mix(C, "#ffffff", 0.20)
	ink = mix(N, "#ffffff", 0.35)
	return f"""
	body {{ color:{ink}; }}
	.page {{ background:{C}; }}
	.hdr, .eyebrow, .sub, .card-x, .esc-x, .etp-x, .nota, .stat-l, .cita, .etp-m {{ color:{muted}; }}
	.ftr {{ color:{muted}; border-top:0.25mm solid {line}; }}
	.ftr b, h1, .card-t, .esc-t, .stat-v, .etp-t {{ color:{N}; }}
	h1 i {{ color:{muted}; }}
	.txt, .callout-x {{ color:{ink}; }}
	.card, .stat, .box {{ background:{card}; border:0.25mm solid {line}; border-left:1mm solid {A}; }}
	.stat {{ border-left:0.25mm solid {line}; border-top:1mm solid {A}; }}
	.esc-g td.esc {{ border-bottom:0.25mm solid {line}; }}
	.etp {{ border-left:0.8mm solid {A}; }}
	.band, .callout-d, .cic-d, .plano {{ background:{dark}; }}
	.callout-l, .cic-l {{ background:{card}; border:0.25mm solid {line}; color:{ink}; }}
	.cic-l .cic-v {{ color:{muted}; }}
	table.items th {{ color:{muted}; border-bottom:0.25mm solid {line}; }}
	table.items td {{ border-bottom:0.2mm solid {line}; color:{ink}; }}
	.cover-name {{ color:{N}; border-bottom:0.6mm solid {A}; }}
	"""
