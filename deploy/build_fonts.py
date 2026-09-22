"""Gera as fontes dos documentos (crm/public/fonts) a partir do repositório Google Fonts.

As fontes do Google vêm como fontes "variáveis"; o gerador de PDF precisa de arquivos fixos. Este roteiro baixa cada
família, extrai os pesos Regular (400), Bold (700) e Itálico (400) e reduz ao alfabeto latino (português incluso),
deixando cada arquivo pequeno. Todas as fontes usadas são de licença aberta (SIL OFL).

Uso (dentro do container, na pasta do app):  python deploy/build_fonts.py
"""

import io
import os
import urllib.parse
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
OUT = os.path.join(os.path.dirname(__file__), "..", "crm", "public", "fonts")

# nome do arquivo final -> (pasta no Google Fonts, arquivo de origem, peso, é fixo?)
SOURCES = {
	"PlayfairDisplay": ("playfairdisplay", "PlayfairDisplay[wght].ttf", "PlayfairDisplay-Italic[wght].ttf"),
	"CormorantGaramond": ("cormorantgaramond", "CormorantGaramond[wght].ttf", "CormorantGaramond-Italic[wght].ttf"),
	"EBGaramond": ("ebgaramond", "EBGaramond[wght].ttf", "EBGaramond-Italic[wght].ttf"),
	"Merriweather": ("merriweather", "Merriweather[opsz,wdth,wght].ttf", "Merriweather-Italic[opsz,wdth,wght].ttf"),
	"LibreBaskerville": ("librebaskerville", "LibreBaskerville[wght].ttf", "LibreBaskerville-Italic[wght].ttf"),
	"Inter": ("inter", "Inter[opsz,wght].ttf", None),
	"Montserrat": ("montserrat", "Montserrat[wght].ttf", None),
	"OpenSans": ("opensans", "OpenSans[wdth,wght].ttf", None),
	"Raleway": ("raleway", "Raleway[wght].ttf", None),
	"DMSans": ("dmsans", "DMSans[opsz,wght].ttf", None),
	"SpaceGrotesk": ("spacegrotesk", "SpaceGrotesk[wght].ttf", None),
}
# famílias que já vêm em arquivos fixos
STATIC = {
	"Lato": ("lato", {"Regular": "Lato-Regular.ttf", "Bold": "Lato-Bold.ttf", "Italic": "Lato-Italic.ttf"}),
	"DMSerifDisplay": ("dmserifdisplay", {"Regular": "DMSerifDisplay-Regular.ttf", "Italic": "DMSerifDisplay-Italic.ttf"}),
}

# alfabeto latino + pontuação e símbolos comuns em documentos em português
UNICODES = (
	list(range(0x20, 0x7F)) + list(range(0xA0, 0x180)) + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC, 0x2116, 0x00BA, 0x00AA]
)


def fetch(folder: str, name: str) -> bytes:
	url = BASE + folder + "/" + urllib.parse.quote(name)
	with urllib.request.urlopen(url, timeout=60) as r:
		return r.read()


def instance(data: bytes, wght: float) -> TTFont:
	font = TTFont(io.BytesIO(data))
	axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
	if "wght" in axes:
		axes["wght"] = wght
	return instancer.instantiateVariableFont(font, axes)


def save_subset(font: TTFont, path: str):
	opts = subset.Options()
	opts.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk", "tnum", "lnum"]
	opts.name_IDs = ["*"]
	opts.notdef_outline = True
	sub = subset.Subsetter(opts)
	sub.populate(unicodes=UNICODES)
	sub.subset(font)
	font.save(path)


def main():
	os.makedirs(OUT, exist_ok=True)
	for fam, (folder, roman, italic) in SOURCES.items():
		data = fetch(folder, roman)
		save_subset(instance(data, 400), os.path.join(OUT, f"{fam}-Regular.ttf"))
		save_subset(instance(data, 700), os.path.join(OUT, f"{fam}-Bold.ttf"))
		if italic:
			save_subset(instance(fetch(folder, italic), 400), os.path.join(OUT, f"{fam}-Italic.ttf"))
		print("ok", fam)
	for fam, (folder, files) in STATIC.items():
		for style, name in files.items():
			save_subset(TTFont(io.BytesIO(fetch(folder, name))), os.path.join(OUT, f"{fam}-{style}.ttf"))
		print("ok", fam)


if __name__ == "__main__":
	main()
