// Modelos do Gerador de conteúdo do Instagram (capa, perfil, citação) - código
// compartilhado entre o editor de verdade (InstagramEditor.vue) e a exportação
// de PNG (instagramExport.js), pra não duplicar a lógica.
//
// A partir daqui, o bloco de texto (título + corpo) de qualquer modelo aceita
// um "layout" configurável (posição, margem, fonte, escala, sombra, fundo) -
// os elementos de marca de cada modelo (selo com avatar na capa, avatar+nome
// no perfil) continuam fixos, só o texto principal e o fundo são flexíveis.
import { Textbox, Rect, Circle, Gradient, Shadow, FabricImage } from 'fabric'

export const TAMANHOS = {
  Post: { w: 1080, h: 1080 },
  Carrossel: { w: 1080, h: 1080 },
  Story: { w: 1080, h: 1920 },
}

export const POSICOES = [
  { valor: 'sup-esq', rotulo: 'Sup. esq.', vAlign: 'top', hAlign: 'left' },
  { valor: 'sup-cen', rotulo: 'Sup. cen.', vAlign: 'top', hAlign: 'center' },
  { valor: 'sup-dir', rotulo: 'Sup. dir.', vAlign: 'top', hAlign: 'right' },
  { valor: 'meio-esq', rotulo: 'Meio esq.', vAlign: 'middle', hAlign: 'left' },
  { valor: 'meio-cen', rotulo: 'Meio', vAlign: 'middle', hAlign: 'center' },
  { valor: 'meio-dir', rotulo: 'Meio dir.', vAlign: 'middle', hAlign: 'right' },
  { valor: 'inf-esq', rotulo: 'Inf. esq.', vAlign: 'bottom', hAlign: 'left' },
  { valor: 'inf-cen', rotulo: 'Inf. cen.', vAlign: 'bottom', hAlign: 'center' },
  { valor: 'inf-dir', rotulo: 'Inf. dir.', vAlign: 'bottom', hAlign: 'right' },
]

export const POSICOES_LOGO = [
  { valor: 'sup-esq', rotulo: 'Sup. esq.' },
  { valor: 'sup-dir', rotulo: 'Sup. dir.' },
  { valor: 'inf-esq', rotulo: 'Inf. esq.' },
  { valor: 'inf-dir', rotulo: 'Inf. dir.' },
]

export const FUNDO_PADROES = [
  { valor: 'nenhum', rotulo: 'Nenhum' },
  { valor: 'grade', rotulo: 'Grade (quadriculado)' },
  { valor: 'bolinhas', rotulo: 'Bolinhas' },
  { valor: 'linhas-h', rotulo: 'Linhas horizontais' },
  { valor: 'linhas-d', rotulo: 'Linhas diagonais' },
  { valor: 'xadrez-d', rotulo: 'Xadrez diagonal' },
]

export const SOMBRA_ESTILOS = [
  { valor: 'nenhuma', rotulo: 'Nenhuma' },
  { valor: 'base', rotulo: 'Base forte' },
  { valor: 'topo', rotulo: 'Topo forte' },
  { valor: 'completa', rotulo: 'Completa' },
]

export const FONTES = [
  'Poppins', 'Inter', 'Space Grotesk', 'Syne', 'Outfit', 'DM Sans',
  'Raleway', 'Bebas Neue', 'Playfair Display', 'Caveat', 'Montserrat',
]

export function layoutPadraoDe(modelo) {
  const base = {
    posicao: 'inf-esq',
    margemH: 14,
    margemV: 19,
    glass: false,
    sombraEstilo: 'nenhuma',
    sombraOpacidade: 60,
    fundoPadrao: 'nenhum',
    fundoGradiente: false,
    fundoCor2: '',
    textoContorno: false,
    textoSombra: false,
    logoAtivo: false,
    logoPosicao: 'inf-dir',
    fonteTitulo: 'Poppins',
    fonteCorpo: 'Poppins',
    escala: 100,
    espacamento: 115,
  }
  if (modelo === 'twitter') return { ...base, posicao: 'meio-esq', margemV: 42 }
  if (modelo === 'citacao') return { ...base, posicao: 'sup-esq', margemV: 8 }
  return base
}

export function corDeFundo(modelo, corMarca) {
  return modelo === 'citacao' ? '#ffffff' : corMarca
}

// ------------------------------------------------------------------ fundo

export function corFundoFinal(canvas, { layout, corBase, corDestaque, w, h }) {
  if (!layout.fundoGradiente) return corBase
  return new Gradient({
    type: 'linear',
    coords: { x1: 0, y1: 0, x2: 0, y2: h },
    colorStops: [
      { offset: 0, color: corBase },
      { offset: 1, color: layout.fundoCor2 || corDestaque },
    ],
  })
}

export function aplicarPadraoFundo(canvas, { padrao, w, h, clara }) {
  if (!padrao || padrao === 'nenhum') return
  const cor = clara ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.08)'
  const objetos = []
  if (padrao === 'grade') {
    const passo = w / 18
    for (let x = passo; x < w; x += passo) {
      objetos.push(new Rect({ left: x, top: 0, width: 1, height: h, fill: cor, selectable: false, evented: false }))
    }
    for (let y = passo; y < h; y += passo) {
      objetos.push(new Rect({ left: 0, top: y, width: w, height: 1, fill: cor, selectable: false, evented: false }))
    }
  } else if (padrao === 'bolinhas') {
    const passo = w / 14
    const r = w * 0.006
    for (let y = passo / 2; y < h; y += passo) {
      for (let x = passo / 2; x < w; x += passo) {
        objetos.push(new Circle({ left: x - r, top: y - r, radius: r, fill: cor, selectable: false, evented: false }))
      }
    }
  } else if (padrao === 'linhas-h') {
    const passo = h / 22
    for (let y = passo; y < h; y += passo) {
      objetos.push(new Rect({ left: 0, top: y, width: w, height: 1, fill: cor, selectable: false, evented: false }))
    }
  } else if (padrao === 'linhas-d' || padrao === 'xadrez-d') {
    const passo = w / 16
    for (let d = -h; d < w + h; d += passo) {
      objetos.push(new Rect({
        left: d, top: 0, width: 1, height: h * 1.6, fill: cor, angle: 45,
        selectable: false, evented: false,
      }))
    }
    if (padrao === 'xadrez-d') {
      for (let d = -h; d < w + h; d += passo) {
        objetos.push(new Rect({
          left: d, top: 0, width: 1, height: h * 1.6, fill: cor, angle: -45,
          selectable: false, evented: false,
        }))
      }
    }
  }
  objetos.forEach((o) => {
    o.set('papel', 'padrao-fundo')
    canvas.add(o)
    canvas.sendObjectToBack(o)
  })
}

export function aplicarSombra(canvas, { estilo, opacidade, w, h }) {
  if (!estilo || estilo === 'nenhuma') return
  const a = Math.max(0, Math.min(100, Number(opacidade) || 0)) / 100

  let coords
  if (estilo === 'base') coords = { x1: 0, y1: 0, x2: 0, y2: h }
  else if (estilo === 'topo') coords = { x1: 0, y1: h, x2: 0, y2: 0 }
  else coords = { x1: 0, y1: 0, x2: 0, y2: h } // "completa" aproximada com base forte

  const retangulo = new Rect({
    left: 0, top: 0, width: w, height: h, selectable: false, evented: false, papel: 'sombra',
  })
  retangulo.set('fill', new Gradient({
    type: 'linear',
    coords,
    colorStops: [
      { offset: 0, color: estilo === 'topo' ? `rgba(0,0,0,${a})` : 'rgba(0,0,0,0)' },
      { offset: 1, color: estilo === 'topo' ? 'rgba(0,0,0,0)' : `rgba(0,0,0,${a})` },
    ],
  }))
  canvas.add(retangulo)
}

export async function aplicarLogo(canvas, { logoUrl, posicao, w, h }) {
  if (!logoUrl) return
  let img
  try {
    img = await FabricImage.fromURL(logoUrl, { crossOrigin: 'anonymous' })
  } catch {
    return
  }
  const alvo = w * 0.14
  img.scaleToWidth(alvo)
  const margem = w * 0.05
  const alturaFinal = img.getScaledHeight()
  const posicoes = {
    'sup-esq': { left: margem, top: margem },
    'sup-dir': { left: w - margem - alvo, top: margem },
    'inf-esq': { left: margem, top: h - margem - alturaFinal },
    'inf-dir': { left: w - margem - alvo, top: h - margem - alturaFinal },
  }
  const pos = posicoes[posicao] || posicoes['inf-dir']
  img.set({ ...pos, papel: 'logo', selectable: false, evented: false })
  canvas.add(img)
}

// ------------------------------------------------------------------ bloco de texto

function areaConteudo(w, h, layout) {
  const mh = (Number(layout.margemH) || 0) / 100 * w
  const mv = (Number(layout.margemV) || 0) / 100 * h
  return { left: mh, right: w - mh, top: mv, bottom: h - mv, largura: w - mh * 2 }
}

// Cor e tamanho-base do título/corpo por modelo - usado tanto na montagem
// completa quanto quando o painel só precisa reaplicar o bloco de texto
// (mudou posição/margem/fonte) sem remontar o slide inteiro.
export function estiloTextoPara(modelo, corDestaque, w, h) {
  if (modelo === 'twitter') {
    return { corTitulo: '#ffffff', corCorpo: '#d0d0d0', tamanhoTituloBase: w * 0.036, tamanhoCorpoBase: w * 0.028 }
  }
  if (modelo === 'citacao') {
    return { corTitulo: corDestaque, corCorpo: '#666666', tamanhoTituloBase: w * 0.062, tamanhoCorpoBase: w * 0.034 }
  }
  return { corTitulo: '#ffffff', corCorpo: 'rgba(255,255,255,.55)', tamanhoTituloBase: h * 0.065, tamanhoCorpoBase: h * 0.028 }
}

function estiloExtraTexto(layout, w) {
  const extra = {}
  if (layout.textoContorno) {
    extra.stroke = 'rgba(0,0,0,.55)'
    extra.strokeWidth = Math.max(1, w * 0.0015)
    extra.paintFirst = 'stroke'
  }
  if (layout.textoSombra) {
    extra.shadow = new Shadow({ color: 'rgba(0,0,0,.45)', blur: w * 0.012, offsetX: w * 0.004, offsetY: w * 0.004 })
  }
  return extra
}

// Monta o título + corpo dentro da área definida pelo layout - devolve os
// objetos criados (pra poder marcar o "papel" de cada um e reaplicar estilo
// via o painel sem precisar remontar o slide inteiro).
export function construirBlocoTexto(canvas, { slide, layout, w, h, corTitulo, corCorpo, tamanhoTituloBase, tamanhoCorpoBase }) {
  const pos = POSICOES.find((p) => p.valor === layout.posicao) || POSICOES[6]
  const area = areaConteudo(w, h, layout)
  const escala = (Number(layout.escala) || 100) / 100
  const espacamento = (Number(layout.espacamento) || 115) / 100
  const alinhamento = pos.hAlign === 'center' ? 'center' : pos.hAlign === 'right' ? 'right' : 'left'
  const extra = estiloExtraTexto(layout, w)

  const tamTitulo = Math.round(tamanhoTituloBase * escala)
  const tamCorpo = Math.round(tamanhoCorpoBase * escala)

  const titulo = slide.titulo
    ? new Textbox(slide.titulo, {
        left: area.left, top: 0, width: area.largura,
        fontSize: tamTitulo, fontWeight: 'bold', fontFamily: layout.fonteTitulo || 'Poppins',
        fill: corTitulo, lineHeight: espacamento, textAlign: alinhamento, ...extra,
      })
    : null
  const corpo = slide.corpo
    ? new Textbox(slide.corpo, {
        left: area.left, top: 0, width: area.largura,
        fontSize: tamCorpo, fontFamily: layout.fonteCorpo || 'Poppins',
        fill: corCorpo, lineHeight: espacamento, textAlign: alinhamento, ...extra,
      })
    : null

  const gapo = h * 0.02
  const alturaTitulo = titulo ? titulo.height : 0
  const alturaCorpo = corpo ? corpo.height : 0
  const alturaTotal = alturaTitulo + (titulo && corpo ? gapo : 0) + alturaCorpo

  let topoBloco
  if (pos.vAlign === 'top') topoBloco = area.top
  else if (pos.vAlign === 'bottom') topoBloco = area.bottom - alturaTotal
  else topoBloco = (area.top + area.bottom) / 2 - alturaTotal / 2

  const criados = []
  if (titulo) {
    titulo.set({ top: topoBloco, papel: 'titulo' })
    canvas.add(titulo)
    criados.push(titulo)
  }
  if (corpo) {
    corpo.set({ top: topoBloco + (titulo ? alturaTitulo + gapo : 0), papel: 'corpo' })
    canvas.add(corpo)
    criados.push(corpo)
  }

  if (layout.glass && criados.length) {
    const pad = w * 0.03
    const painel = new Rect({
      left: area.left - pad, top: topoBloco - pad, width: area.largura + pad * 2, height: alturaTotal + pad * 2,
      rx: 16, ry: 16, fill: 'rgba(255,255,255,.1)', stroke: 'rgba(255,255,255,.18)', strokeWidth: 1,
      selectable: false, evented: false, papel: 'glass',
    })
    canvas.add(painel)
    canvas.sendObjectToBack(painel)
    criados.push(painel)
  }

  return criados
}

// ------------------------------------------------------------------ elementos fixos de marca por modelo

function elementosCapa(canvas, { w, h, tipo, nomeMarca }) {
  const margemTopo = w * 0.06
  const handleTexto = '@' + (nomeMarca || __('suamarca')).toLowerCase().replace(/\s+/g, '')

  const handleTopo = new Textbox(handleTexto, {
    left: margemTopo, top: h * 0.02, width: w * 0.45,
    fontSize: Math.round(h * 0.021), fontFamily: 'Poppins', fill: 'rgba(255,255,255,.7)', papel: 'marca',
  })
  const tagTopo = new Textbox(tipo || '', {
    left: w - margemTopo - w * 0.32, top: h * 0.02, width: w * 0.32,
    fontSize: Math.round(h * 0.021), fontFamily: 'Poppins', fill: 'rgba(255,255,255,.7)', textAlign: 'right', papel: 'marca',
  })
  canvas.add(handleTopo, tagTopo)

  const pillTop = h * 0.5
  const pillHeight = h * 0.048
  const avatarD = pillHeight * 0.74
  const pillPad = w * 0.012
  const pillWidth = pillPad * 3 + avatarD + handleTexto.length * w * 0.016
  const margemConteudo = w * 0.14

  const pill = new Rect({
    left: margemConteudo, top: pillTop, width: pillWidth, height: pillHeight,
    rx: pillHeight / 2, ry: pillHeight / 2, fill: 'rgba(255,255,255,.12)', papel: 'marca',
  })
  const avatarPill = new Circle({
    left: margemConteudo + pillPad, top: pillTop + (pillHeight - avatarD) / 2, radius: avatarD / 2, fill: '#ffffff', papel: 'marca',
  })
  const handlePill = new Textbox(handleTexto, {
    left: margemConteudo + pillPad * 2 + avatarD, top: pillTop + pillHeight * 0.24,
    width: pillWidth, fontSize: Math.round(h * 0.021), fontFamily: 'Poppins', fill: '#ffffff', papel: 'marca',
  })
  canvas.add(pill, avatarPill, handlePill)

  const rodapeEsq = new Textbox(tipo || '', {
    left: margemTopo, top: h * 0.95, width: w * 0.4,
    fontSize: Math.round(h * 0.02), fontFamily: 'Poppins', fill: 'rgba(255,255,255,.45)', papel: 'marca',
  })
  canvas.add(rodapeEsq)
  if (tipo === 'Carrossel') {
    const rodapeDir = new Textbox(__('Arraste'), {
      left: w - margemTopo - w * 0.32, top: h * 0.95, width: w * 0.32,
      fontSize: Math.round(h * 0.02), fontFamily: 'Poppins', fill: 'rgba(255,255,255,.45)', textAlign: 'right', papel: 'marca',
    })
    canvas.add(rodapeDir)
  }
}

function elementosPerfil(canvas, { w, h, nomeMarca }) {
  const nomeTexto = nomeMarca || __('Sua marca')
  const avatarD = w * 0.08
  const avatarLeft = w * 0.18
  const avatarTop = h * 0.42

  const avatar = new Circle({ left: avatarLeft, top: avatarTop, radius: avatarD / 2, fill: '#2f2f2f', papel: 'marca' })
  const marca = new Textbox('?', {
    left: avatarLeft, top: avatarTop + avatarD * 0.18, width: avatarD,
    fontSize: Math.round(avatarD * 0.5), fontFamily: 'Poppins', fill: 'rgba(255,255,255,.35)',
    textAlign: 'center', selectable: false, papel: 'marca',
  })
  canvas.add(avatar, marca)

  const nomeLeft = avatarLeft + avatarD + w * 0.02
  const nomeTop = avatarTop + h * 0.013
  const nome = new Textbox(nomeTexto, {
    left: nomeLeft, top: nomeTop,
    width: w * 0.6, fontSize: Math.round(w * 0.036), fontWeight: 'bold', fontFamily: 'Poppins', fill: '#ffffff', papel: 'marca',
  })
  const selo = new Circle({
    left: nomeLeft + nomeTexto.length * w * 0.021 + 10,
    top: nomeTop + w * 0.005, radius: w * 0.014, fill: '#3897f0', papel: 'marca',
  })
  const check = new Textbox('✓', {
    left: selo.left - w * 0.008, top: selo.top - w * 0.011,
    fontSize: Math.round(w * 0.02), fontFamily: 'Poppins', fill: '#ffffff', selectable: false, papel: 'marca',
  })
  const handle = new Textbox('@' + nomeTexto.toLowerCase().replace(/\s+/g, ''), {
    left: nomeLeft, top: nomeTop + Math.round(w * 0.036) + 4,
    width: w * 0.6, fontSize: Math.round(w * 0.022), fontFamily: 'Poppins', fill: '#9fb0b5', papel: 'marca',
  })
  canvas.add(nome, selo, check, handle)
}

function elementosCitacao(canvas, { w, h }) {
  const espacoImagem = new Rect({
    left: w * 0.09, top: h * 0.54, width: w * 0.82, height: h * 0.37, rx: 20, ry: 20,
    fill: '#f2f2f2', stroke: '#d8d8d8', strokeWidth: 1, strokeDashArray: [6, 6], papel: 'marca',
  })
  canvas.add(espacoImagem)
}

// ------------------------------------------------------------------ montagem geral

export function construirSlide(canvas, { tipo, modelo, slide, corMarca, corDestaque, nomeMarca }) {
  const { w, h } = TAMANHOS[tipo] || TAMANHOS.Carrossel
  const layout = { ...layoutPadraoDe(modelo), ...(slide.layout || {}) }
  const claraDeFundo = modelo === 'citacao'

  canvas.setDimensions({ width: w, height: h })
  const corBase = corDeFundo(modelo, corMarca)
  canvas.backgroundColor = corFundoFinal(canvas, { layout, corBase, corDestaque, w, h })

  aplicarPadraoFundo(canvas, { padrao: layout.fundoPadrao, w, h, clara: claraDeFundo })
  aplicarSombra(canvas, { estilo: layout.sombraEstilo, opacidade: layout.sombraOpacidade, w, h })

  if (modelo === 'twitter') elementosPerfil(canvas, { w, h, nomeMarca })
  else if (modelo === 'citacao') elementosCitacao(canvas, { w, h })
  else elementosCapa(canvas, { w, h, tipo, nomeMarca })

  construirBlocoTexto(canvas, { slide, layout, w, h, ...estiloTextoPara(modelo, corDestaque, w, h) })

  canvas.renderAll()
}
