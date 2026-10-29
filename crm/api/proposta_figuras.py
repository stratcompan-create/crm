# Copyright (c) 2026, Stratcompany and contributors
# For license information, please see license.txt
#
# Figuras das páginas didáticas da proposta: celular com WhatsApp, link de acompanhamento,
# notificações, tela do sistema, cobrança, painel, site, post e passos. São desenhadas em
# HTML/CSS (WeasyPrint), nas cores da marca, e descritas por linhas simples de texto, que a IA
# preenche e o usuário edita à mão. Ex.: "Cliente: Olá, vocês atendem?" ou "Parcela 2/4 | R$ 1.500 | vencendo".

import re

# tipo -> (nome na tela, como escrever as linhas)
TIPOS = {
	"whatsapp": ("Conversa no WhatsApp", "Uma mensagem por linha: 'Cliente: texto' ou 'Empresa: texto'. Opcional: 'Equipe: Rótulo | valor' mostra ao lado o que a equipe recebe. Título = nome da empresa."),
	"acompanhamento": ("Link de acompanhamento no celular", "Uma etapa por linha: 'texto | feito', '| atual' ou '| pendente'. Título = nome do caso ou projeto."),
	"notificacoes": ("Notificações", "Uma por linha: 'Título | detalhe'."),
	"tela": ("Tela do sistema com campos", "Um campo por linha: 'Rótulo | valor'. Título = nome da tela."),
	"cobranca": ("Cobrança e pagamentos", "Uma parcela por linha: 'Descrição | valor | pago', 'vencendo' ou 'a vencer'. Título = nome do cliente."),
	"painel": ("Painel com números", "Número: 'valor | rótulo'. Barra: 'rótulo | 70%'. Título = nome do painel."),
	"site": ("Página de site", "Linha 1: título; linha 2: texto; linha 3: botão. Título = endereço do site."),
	"post": ("Post ou anúncio", "Linha 1: texto da arte; linha 2: legenda; linha 3: botão. Título = @perfil."),
	"passos": ("Passo a passo", "Um passo por linha: 'Título | texto'."),
}

# check desenhado em vetor: centralizado no círculo em qualquer tamanho (o caractere ✓ fica torto)
CHECK = (
	'<img class="chk" src="data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22>'
	'<path d=%22M6 12.5l4 4L18 8%22 fill=%22none%22 stroke=%22white%22 stroke-width=%223%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22/></svg>">'
)

CLIENTE = ("cliente", "lead", "paciente", "contato", "visitante", "aluno", "comprador")


def _e(text) -> str:
	from crm.api.proposta import _e as esc

	return esc(text)


def _lines(text) -> list[str]:
	return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def _parts(line: str, n: int) -> list[str]:
	parts = [p.strip() for p in line.split("|")]
	return (parts + [""] * n)[:n]


def _initials(name: str) -> str:
	words = [w for w in re.split(r"\s+", (name or "").replace("@", "")) if w]
	return "".join(w[0] for w in words[:2]).upper() or "•"


def css(P: dict, fonts_css: dict) -> str:
	from crm.api.estilo import mix

	t, s, x, n = fonts_css["t"], fonts_css["s"], fonts_css["x"], fonts_css["n"]
	# fundo do painel da figura: tom quente sobre página clara (como no material feito à mão)
	escura = sum(int(P["page"][i:i + 2], 16) for i in (1, 3, 5)) < 384
	mock_bg = P["soft"] if escura else mix(P["page"], "#8a7350", 0.13)
	return f"""
	.dida {{ display:flex; gap:9mm; height:174mm; }}
	.dida .tx {{ flex:1; }}
	.dida .pts {{ margin-top:4mm; }}
	.dida .pt {{ display:flex; gap:3mm; padding:3mm 0; border-top:0.3mm solid {P['line']}; font-size:10.5pt; line-height:1.45; }}
	.dida .pt i {{ font-style:normal; font-family:{n}; color:{P['accent']}; font-size:13pt; width:7mm; flex-shrink:0; }}
	.dida .pt b {{ display:block; font-weight:600; font-size:11pt; color:{P['title']}; margin-bottom:0.8mm; }}
	.dida .pt small {{ display:block; font-size:9.6pt; line-height:1.5; color:{P['muted']}; }}
	.mock {{ width:132mm; flex-shrink:0; background:{mock_bg}; border-radius:4mm; position:relative; display:flex; align-items:center; justify-content:center; }}
	.mock .cap {{ position:absolute; bottom:4mm; left:0; right:0; text-align:center; font-family:{s}; font-size:6.4pt; letter-spacing:0.25em;
		text-transform:uppercase; color:{P['muted']}; }}
	.fig {{ font-family:{x}; color:#1f2a2e; }}
	.phone {{ width:66mm; background:#1d1d1f; border-radius:7mm; padding:2.2mm; }}
	.phone .scr {{ background:#efe9e1; border-radius:5mm; overflow:hidden; height:126mm; }}
	.phone .top {{ background:{P['hl']}; color:#ffffff; padding:3mm 3.5mm; display:flex; align-items:center; gap:2.5mm; }}
	.phone .av {{ width:8mm; height:8mm; line-height:8mm; border-radius:50%; background:#ffffff; color:{P['hl']}; text-align:center;
		font-size:6.5pt; font-weight:700; flex-shrink:0; }}
	.phone .top b {{ display:block; font-size:8pt; }}
	.phone .top small {{ font-size:6.2pt; color:#dfe7e4; }}
	.chat {{ padding:3mm 2.6mm; }}
	.msg {{ font-size:7.6pt; line-height:1.38; padding:2mm 2.6mm; border-radius:2.4mm; margin-bottom:2mm; max-width:82%; }}
	.msg.in {{ background:#ffffff; }}
	.msg.out {{ background:#d9f5c8; margin-left:auto; border-left:0.8mm solid #2f8f55; }}
	.msg .h {{ display:block; text-align:right; font-size:5.8pt; color:#8a948f; margin-top:0.6mm; }}
	.wa {{ display:flex; gap:4mm; align-items:center; }}
	.wa .phone {{ width:60mm; }}
	.wa .msg {{ font-size:7pt; padding:1.6mm 2.2mm; margin-bottom:1.6mm; }}
	.wa .phone .scr {{ height:146mm; }}
	.side {{ width:56mm; }}
	.side .card2 {{ background:#ffffff; border:0.3mm solid #e1e4e3; border-radius:2.6mm; padding:3.4mm; }}
	.side .k3 {{ font-size:5.8pt; letter-spacing:0.18em; text-transform:uppercase; color:{P['label']}; font-weight:700; margin-bottom:1.6mm; }}
	.side .row {{ font-size:7.4pt; padding:1.8mm 0; }}
	.side .pill {{ background:{P['soft']}; color:{P['title']}; }}
	.side .arrow {{ font-family:{n}; font-size:16pt; color:{P['accent']}; margin-bottom:2mm; }}
	.portal {{ padding:4mm 3.6mm; background:#ffffff; height:100%; }}
	.portal h4 {{ font-family:{t}; font-weight:400; font-size:11pt; color:{P['title']}; margin:0 0 1mm 0; }}
	.portal .sub {{ font-size:6.6pt; color:#7a8689; margin-bottom:4mm; }}
	.etp {{ display:flex; gap:2.6mm; padding-bottom:3.6mm; position:relative; }}
	.etp .d {{ width:4.4mm; height:4.4mm; border-radius:50%; flex-shrink:0; margin-top:0.4mm; background:#d5dcdc; }}
	.etp.feito .d {{ background:{P['accent']}; }}
	.etp.atual .d {{ background:{P['hl']}; }}
	.etp .tt {{ font-size:7.8pt; line-height:1.35; color:#7a8689; }}
	.etp.feito .tt, .etp.atual .tt {{ color:#1f2a2e; }}
	.etp.atual .tt {{ font-weight:700; }}
	.etp small {{ display:block; font-size:6.2pt; letter-spacing:0.12em; text-transform:uppercase; color:#9aa5a7; }}
	.portal .av2 {{ margin-top:2mm; background:{P['soft']}; border-radius:2mm; padding:2.6mm; font-size:7pt; line-height:1.4; }}
	.toasts {{ width:104mm; }}
	.stack {{ width:112mm; }} .stack .win {{ width:100%; }}
	.toast {{ display:flex; gap:3mm; align-items:center; background:{P['hl']}; color:#ffffff; border-radius:3mm; padding:3.6mm 4mm; margin-bottom:3mm; }}
	.toast .ic {{ width:7.5mm; height:7.5mm; border-radius:50%; background:{P['accent']}; flex-shrink:0;
		display:flex; align-items:center; justify-content:center; }}
	.chk {{ width:4.6mm; height:4.6mm; display:block; }}

	.toast b {{ display:block; font-size:9pt; }}
	.toast small {{ font-size:7.4pt; color:#dfe7e4; }}
	.win {{ width:112mm; background:#ffffff; border-radius:3mm; border:0.3mm solid #d9dedd; overflow:hidden; }}
	.win .bar {{ background:#f1efea; padding:2.4mm 3mm; display:flex; align-items:center; gap:1.4mm; border-bottom:0.3mm solid #e4e2dc; }}
	.win .bar i {{ width:2.2mm; height:2.2mm; border-radius:50%; background:#d5d0c6; display:inline-block; }}
	.win .bar span {{ margin-left:2.5mm; font-size:6.8pt; color:#7a8689; background:#ffffff; border-radius:3mm; padding:0.6mm 3mm; }}
	.win .wb {{ padding:4mm; }}
	.win h4 {{ font-family:{t}; font-weight:400; font-size:11pt; color:{P['title']}; margin:0 0 3mm 0; }}
	.fields {{ display:flex; flex-wrap:wrap; gap:2.6mm; }}
	.field {{ width:49mm; border:0.3mm solid #e1e4e3; border-radius:2mm; padding:2.2mm 2.6mm; font-size:8pt; line-height:1.35; }}
	.field span, .row .k2 {{ display:block; font-size:5.8pt; letter-spacing:0.16em; text-transform:uppercase; color:{P['label']}; font-weight:700; margin-bottom:0.6mm; }}
	.row {{ display:flex; justify-content:space-between; align-items:center; gap:3mm; padding:2.4mm 0; border-bottom:0.25mm dashed #e1e4e3; font-size:8pt; }}
	.pill {{ font-size:6.6pt; font-weight:700; padding:0.8mm 2.4mm; border-radius:3mm; white-space:nowrap; }}
	.pill.pago, .pill.feito {{ background:#dff1d6; color:#3c7a28; }}
	.pill.vencendo {{ background:#fde8cf; color:#a35a10; }}
	.pill.avencer {{ background:#eceeee; color:#6b7678; }}
	.tiles {{ display:flex; gap:2.6mm; margin-bottom:4mm; }}
	.tile {{ flex:1; border:0.3mm solid #e1e4e3; border-radius:2mm; padding:2.6mm; }}
	.tile b {{ display:block; font-family:{n}; font-weight:400; font-size:15pt; color:{P['title']}; line-height:1.1; }}
	.tile span {{ font-size:6.2pt; letter-spacing:0.1em; text-transform:uppercase; color:#7a8689; }}
	.bars .b {{ display:flex; align-items:center; gap:2.6mm; font-size:7.6pt; margin-bottom:2.4mm; }}
	.bars .b span {{ width:28mm; flex-shrink:0; }}
	.bars .t {{ flex:1; height:3.2mm; background:#eceeee; border-radius:2mm; overflow:hidden; }}
	.bars .t i {{ display:block; height:100%; background:{P['accent']}; border-radius:2mm; }}
	.bars .b em {{ font-style:normal; width:10mm; text-align:right; color:#7a8689; }}
	.hero {{ background:{P['hl']}; color:#ffffff; border-radius:2.4mm; padding:9mm 7mm; }}
	.hero h5 {{ font-family:{t}; font-weight:400; font-size:17pt; line-height:1.15; margin:0 0 2.5mm 0; }}
	.hero p {{ font-size:8.4pt; color:#e3e9e7; margin:0 0 4mm 0; line-height:1.45; }}
	.btn {{ display:inline-block; background:{P['accent']}; color:#ffffff; font-size:7.6pt; font-weight:700; padding:1.8mm 4mm; border-radius:4mm; }}
	.skel {{ display:flex; gap:2.6mm; margin-top:3.5mm; }}
	.skel i {{ flex:1; height:13mm; border-radius:2mm; background:#f1efea; display:block; }}
	.post {{ width:78mm; background:#ffffff; border-radius:3mm; border:0.3mm solid #d9dedd; overflow:hidden; }}
	.post .ph {{ display:flex; align-items:center; gap:2.4mm; padding:2.6mm 3mm; }}
	.post .ph .av {{ width:7mm; height:7mm; line-height:7mm; border-radius:50%; background:{P['hl']}; color:#ffffff; text-align:center; font-size:6pt; font-weight:700; }}
	.post .ph b {{ display:block; font-size:7.6pt; }}
	.post .ph small {{ font-size:6.2pt; color:#7a8689; }}
	.post .art {{ background:{P['hl']}; color:#ffffff; height:62mm; padding:6mm; display:flex; align-items:flex-end;
		font-family:{t}; font-size:16pt; line-height:1.15; }}
	.post .cap2 {{ padding:3mm; font-size:7.6pt; line-height:1.4; }}
	.post .cta {{ margin:0 3mm 3mm; background:{P['soft']}; color:{P['title']}; text-align:center; font-size:7.6pt; font-weight:700; padding:2mm; border-radius:2mm; }}
	.stepsv {{ width:108mm; }}
	.stepv {{ display:flex; gap:3.5mm; background:#ffffff; border:0.3mm solid #e1e4e3; border-radius:2.6mm; padding:3.4mm 4mm; margin-bottom:3mm; }}
	.stepv .n {{ width:8mm; height:8mm; line-height:8mm; border-radius:50%; background:{P['hl']}; color:#ffffff; text-align:center;
		font-family:{n}; font-size:10pt; flex-shrink:0; }}
	.stepv b {{ display:block; font-size:9pt; color:{P['title']}; }}
	.stepv small {{ font-size:7.6pt; color:#6b7678; line-height:1.4; }}
	"""


# ---------------------------------------------------------------- figuras

def _phone(titulo, sub, body, brand=""):
	return (
		f'<div class="fig phone"><div class="scr"><div class="top"><span class="av">{_e(_initials(titulo or brand))}</span>'
		f'<div><b>{_e(titulo or brand)}</b><small>{_e(sub)}</small></div></div>{body}</div></div>'
	)


def fig_whatsapp(titulo, linhas, brand):
	msgs, equipe, minuto = "", "", 2
	# com o cartão da equipe ao lado o celular fica estreito: cabem menos mensagens
	limite = 6 if any(ln.lower().startswith("equipe:") for ln in _lines(linhas)) else 8
	for ln in _lines(linhas):
		quem, _sep, texto = ln.partition(":")
		if not _sep:
			quem, texto = "empresa", ln
		quem = quem.strip().lower()
		if quem == "equipe":
			# o que a equipe recebe organizado: cartão ao lado do celular
			rot, val = _parts(texto, 2)
			equipe += f'<div class="row"><span>{_e(rot)}</span>' + (f'<span class="pill">{_e(val)}</span>' if val else "") + "</div>"
			continue
		if msgs.count('class="msg') >= limite:
			continue
		lado = "in" if quem in CLIENTE else "out"
		msgs += f'<div class="msg {lado}">{_e(texto.strip())}<span class="h">14:{minuto:02d}</span></div>'
		minuto += 1 if lado == "out" else 0
	phone = _phone(titulo or brand, "WhatsApp", f'<div class="chat">{msgs}</div>', brand)
	if not equipe:
		return phone
	side = f'<div class="side"><div class="arrow">→</div><div class="card2"><div class="k3">O que a equipe recebe</div>{equipe}</div></div>'
	return f'<div class="fig wa">{phone}{side}</div>'


def fig_acompanhamento(titulo, linhas, brand):
	etapas, aviso = "", ""
	for ln in _lines(linhas)[:7]:
		texto, status = _parts(ln, 2)
		status = status.lower().replace(" ", "")
		if status not in ("feito", "atual", "pendente"):
			aviso = texto if not status else aviso
			if not status:
				continue
			status = "pendente"
		rotulo = {"feito": "Concluído", "atual": "Agora", "pendente": "Próximo"}[status]
		etapas += f'<div class="etp {status}"><span class="d"></span><div class="tt"><small>{rotulo}</small>{_e(texto)}</div></div>'
	body = (
		f'<div class="portal"><h4>{_e(titulo or "Acompanhamento")}</h4><div class="sub">Atualizado hoje · sem login e sem senha</div>'
		f'{etapas}' + (f'<div class="av2">{_e(aviso)}</div>' if aviso else "") + "</div>"
	)
	return _phone(brand or titulo, "link de acompanhamento", body, brand)


def fig_notificacoes(titulo, linhas, brand):
	itens = "".join(
		f'<div class="toast"><span class="ic">{CHECK}</span><div><b>{_e(t)}</b><small>{_e(d)}</small></div></div>'
		for t, d in (_parts(ln, 2) for ln in _lines(linhas)[:4])
	)
	return f'<div class="fig toasts">{itens}</div>'


def _win(endereco, inner):
	return f'<div class="fig win"><div class="bar"><i></i><i></i><i></i><span>{_e(endereco)}</span></div><div class="wb">{inner}</div></div>'


def fig_tela(titulo, linhas, brand):
	campos = "".join(f'<div class="field"><span>{_e(r)}</span>{_e(v)}</div>' for r, v in (_parts(ln, 2) for ln in _lines(linhas)[:8]))
	return _win(brand or "sistema", f'<h4>{_e(titulo)}</h4><div class="fields">{campos}</div>')


def fig_cobranca(titulo, linhas, brand):
	rows, avisos = "", []
	for ln in _lines(linhas)[:6]:
		desc, valor, status = _parts(ln, 3)
		chave = status.lower().replace(" ", "").replace("à", "a") or "avencer"
		chave = chave if chave in ("pago", "vencendo", "avencer") else "avencer"
		rows += f'<div class="row"><span>{_e(desc)}</span><b>{_e(valor)}</b><span class="pill {chave}">{_e(status or "a vencer")}</span></div>'
		# o que a automação fez com cada parcela vira um aviso embaixo da tela
		if chave == "vencendo" and not any(a[0] == "lembrete" for a in avisos):
			avisos.append(("lembrete", "Lembrete enviado no WhatsApp", f"{desc} · com o link de pagamento"))
		if chave == "pago" and not any(a[0] == "pago" for a in avisos):
			avisos.append(("pago", f"Pagamento confirmado · {valor}", f"{desc} · baixa automática e recibo enviado"))
	toasts = "".join(f'<div class="toast"><span class="ic">{CHECK}</span><div><b>{_e(t)}</b><small>{_e(d)}</small></div></div>' for _k, t, d in avisos)
	win = _win(brand or "financeiro", f'<h4>{_e(titulo or "Honorários")}</h4>{rows}')
	return f'<div class="fig stack">{win}<div class="toasts" style="width:100%;margin-top:4mm">{toasts}</div></div>' if toasts else win


def fig_painel(titulo, linhas, brand):
	tiles, bars = "", ""
	for ln in _lines(linhas)[:8]:
		a, b = _parts(ln, 2)
		m = re.fullmatch(r"(\d{1,3})\s*%", b)
		if m:
			w = min(int(m.group(1)), 100)
			bars += f'<div class="b"><span>{_e(a)}</span><div class="t"><i style="width:{w}%"></i></div><em>{w}%</em></div>'
		else:
			tiles += f'<div class="tile"><b>{_e(a)}</b><span>{_e(b)}</span></div>'
	inner = f'<h4>{_e(titulo or "Painel")}</h4>' + (f'<div class="tiles">{tiles}</div>' if tiles else "") + (f'<div class="bars">{bars}</div>' if bars else "")
	return _win(brand or "painel", inner)


def fig_site(titulo, linhas, brand):
	ls = _lines(linhas)
	t, x, btn = (ls + ["", "", ""])[:3]
	inner = (
		f'<div class="hero"><h5>{_e(t)}</h5>' + (f"<p>{_e(x)}</p>" if x else "") + (f'<span class="btn">{_e(btn)}</span>' if btn else "")
		+ '</div><div class="skel"><i></i><i></i><i></i></div>'
	)
	return _win(titulo or "seusite.com.br", inner)


def fig_post(titulo, linhas, brand):
	ls = _lines(linhas)
	arte, legenda, btn = (ls + ["", "", ""])[:3]
	perfil = titulo or brand
	return (
		f'<div class="fig post"><div class="ph"><span class="av">{_e(_initials(perfil))}</span><div><b>{_e(perfil)}</b><small>Instagram</small></div></div>'
		f'<div class="art">{_e(arte)}</div>' + (f'<div class="cap2">{_e(legenda)}</div>' if legenda else "")
		+ (f'<div class="cta">{_e(btn)}</div>' if btn else "") + "</div>"
	)


def fig_passos(titulo, linhas, brand):
	passos = "".join(
		f'<div class="stepv"><span class="n">{i + 1}</span><div><b>{_e(t)}</b><small>{_e(x)}</small></div></div>'
		for i, (t, x) in enumerate(_parts(ln, 2) for ln in _lines(linhas)[:5])
	)
	return f'<div class="fig stepsv">{passos}</div>'


RENDER = {
	"whatsapp": fig_whatsapp, "acompanhamento": fig_acompanhamento, "notificacoes": fig_notificacoes, "tela": fig_tela,
	"cobranca": fig_cobranca, "painel": fig_painel, "site": fig_site, "post": fig_post, "passos": fig_passos,
}


def render(tipo, titulo, linhas, brand="") -> str:
	fn = RENDER.get((tipo or "").strip().lower())
	if not fn or not _lines(linhas):
		return ""
	return fn(titulo, linhas, brand)


# ---------------------------------------------------------------- figura automática

# palavras do escopo -> figura com um exemplo neutro (quando a IA não montou as páginas)
AUTO = [
	(r"whats|triagem|atendimento|mensage|conversa|chat", "whatsapp", "",
	 "Cliente: Olá! Gostaria de saber mais sobre o serviço.\nEmpresa: Olá! Já vou te ajudar. Qual é o seu nome?\nCliente: Maria Souza.\n"
	 "Empresa: Obrigado, Maria! Em poucas palavras, do que você precisa?\nCliente: Quero entender como funciona e os próximos passos.\n"
	 "Empresa: Perfeito. Alguém da equipe te responde em instantes."),
	(r"acompanh|portal|andamento|status|progresso", "acompanhamento", "Seu projeto",
	 "Contrato assinado | feito\nDocumentos recebidos | feito\nEm andamento | atual\nRevisão | pendente\nEntrega | pendente\n"
	 "Você recebe um aviso no WhatsApp a cada nova etapa."),
	(r"nota fiscal|nfs-?e", "notificacoes", "",
	 "Pagamento confirmado | parcela 1/4 · R$ 1.000,00\nNota fiscal emitida | no emissor oficial da Prefeitura\n"
	 "Nota enviada ao cliente | pelo WhatsApp e por e-mail\nLançada no financeiro | sem ninguém digitar"),
	(r"automa|lembrete|aviso|notifica", "notificacoes", "",
	 "Tarefa concluída automaticamente | sem ninguém precisar lembrar\nAviso enviado ao cliente | pelo WhatsApp e por e-mail\n"
	 "Documento recebido | já na pasta certa\nPagamento confirmado | baixa feita sozinha"),
	(r"cobran|pagament|honor|parcela|financeir|receb", "cobranca", "Cliente exemplo",
	 "Parcela 1/4 | R$ 1.000,00 | pago\nParcela 2/4 | R$ 1.000,00 | vencendo\nParcela 3/4 | R$ 1.000,00 | a vencer\nParcela 4/4 | R$ 1.000,00 | a vencer"),
	(r"site|página|landing|loja", "site", "seusite.com.br",
	 "Um título claro sobre o que você faz\nTexto curto que explica para quem é e o que a pessoa ganha.\nFale com a gente"),
	(r"instagram|conteúdo|post|anúncio|tráfego|campanha|redes", "post", "",
	 "Uma ideia por post, dita de forma simples\nLegenda que explica e convida a pessoa a chamar no direct.\nEnviar mensagem"),
	(r"relat|painel|gest|métric|indicador|dashboard|meta", "painel", "Visão do mês",
	 "Atendimentos | 80%\nPropostas enviadas | 55%\nNegócios fechados | 35%"),
	(r"ficha|cadastro|crm|organiza", "tela", "Ficha do cliente",
	 "Nome | Maria Souza\nOrigem | Instagram\nEtapa | Proposta enviada\nPróximo passo | Retornar amanhã"),
]


def auto_pages(escopo_itens, limite=3) -> list[dict]:
	"""Até `limite` páginas didáticas a partir do escopo, uma figura diferente por página."""
	pages, usados, feitos = [], set(), set()
	# primeiro pelo título do item (sinal forte), depois pela descrição; na ordem do escopo
	for campo in ("titulo", "texto"):
		for n, it in enumerate(escopo_itens or []):
			texto = str(it.get(campo) or "").lower()
			if n in feitos or len(pages) >= limite:
				continue
			for padrao, tipo, ftitulo, linhas in AUTO:
				if tipo not in usados and re.search(padrao, texto):
					usados.add(tipo)
					feitos.add(n)
					pages.append({
						"n": n, "titulo": it.get("titulo") or "", "destaque": "na prática", "texto": it.get("texto") or "", "pontos": "",
						"figura": tipo, "figura_titulo": ftitulo, "figura_linhas": linhas,
					})
					break
	pages = [{k: v for k, v in p.items() if k != "n"} for p in sorted(pages, key=lambda p: p["n"])]
	itens = [i for i in (escopo_itens or []) if i.get("titulo")]
	if not pages and len(itens) >= 2:
		pages.append({
			"titulo": "Como o projeto", "destaque": "acontece", "texto": "", "pontos": "", "figura": "passos", "figura_titulo": "",
			"figura_linhas": "\n".join(f"{i['titulo']} | {i.get('texto') or ''}" for i in itens[:5]),
		})
	return pages
