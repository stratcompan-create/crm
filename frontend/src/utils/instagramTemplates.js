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
    posicao: 'meio-cen',
    margemH: 12,
    margemV: 19,
    glass: false,
    sombraEstilo: 'nenhuma',
    sombraOpacidade: 60,
    fundoPadrao: 'nenhum',
    fundoCor: '',
    fundoGradiente: false,
    fundoCor2: '',
    fundoImagem: '',
    citacaoImagem: '',
    imagemPosicao: 'baixo',
    textoContorno: false,
    textoSombra: false,
    logoAtivo: false,
    logoPosicao: 'inf-dir',
    fonteTitulo: 'Poppins',
    fonteCorpo: 'Poppins',
    escala: 100,
    espacamento: 115,
  }
  // Estilo Twitter: o texto principal é o "post" logo abaixo do perfil - fica
  // alinhado com a mesma margem do avatar/nome, não centralizado no card
  // inteiro (senão ele flutua longe do resto da identidade).
  if (modelo === 'twitter') return { ...base, posicao: 'sup-esq', margemH: 18.6, margemV: 49 }
  // Citacao: o texto fica centralizado no card de verdade (nao so "no espaco
  // que sobra") - a caixa de imagem fica menor e mais pra baixo (ou mais pra
  // cima, se a posicao for "cima") pra nao disputar espaco com o centro.
  if (modelo === 'citacao') return { ...base, posicao: 'meio-cen', margemH: 9, margemV: 10 }
  return base
}

// Modelos "claros" (fundo claro, texto escuro) - Padrão e Estilo Twitter
// seguem a referência de mercado (MyPostFlow) e usam essa base como padrão;
// a pessoa ainda pode trocar pra qualquer cor no seletor de fundo.
export const COR_CLARA_PADRAO = '#f2efe4'

export function corDeFundo(modelo, corMarca) {
  if (modelo === 'citacao') return '#ffffff'
  if (modelo === 'padrao' || modelo === 'twitter') return COR_CLARA_PADRAO
  return corMarca
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
      objetos.push(new Rect({ left: x, top: 0, width: 1, height: h, fill: cor, selectable: false, evented: false, originX: 'left', originY: 'top' }))
    }
    for (let y = passo; y < h; y += passo) {
      objetos.push(new Rect({ left: 0, top: y, width: w, height: 1, fill: cor, selectable: false, evented: false, originX: 'left', originY: 'top' }))
    }
  } else if (padrao === 'bolinhas') {
    const passo = w / 14
    const r = w * 0.006
    for (let y = passo / 2; y < h; y += passo) {
      for (let x = passo / 2; x < w; x += passo) {
        objetos.push(new Circle({ left: x - r, top: y - r, radius: r, fill: cor, selectable: false, evented: false, originX: 'left', originY: 'top' }))
      }
    }
  } else if (padrao === 'linhas-h') {
    const passo = h / 22
    for (let y = passo; y < h; y += passo) {
      objetos.push(new Rect({ left: 0, top: y, width: w, height: 1, fill: cor, selectable: false, evented: false, originX: 'left', originY: 'top' }))
    }
  } else if (padrao === 'linhas-d' || padrao === 'xadrez-d') {
    const passo = w / 16
    for (let d = -h; d < w + h; d += passo) {
      objetos.push(new Rect({
        left: d, top: 0, width: 1, height: h * 1.6, fill: cor, angle: 45,
        selectable: false, evented: false, originX: 'left', originY: 'top',
      }))
    }
    if (padrao === 'xadrez-d') {
      for (let d = -h; d < w + h; d += passo) {
        objetos.push(new Rect({
          left: d, top: 0, width: 1, height: h * 1.6, fill: cor, angle: -45,
          selectable: false, evented: false, originX: 'left', originY: 'top',
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
    left: 0, top: 0, width: w, height: h, selectable: false, evented: false, papel: 'sombra', originX: 'left', originY: 'top',
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

// Imagem cobrindo o slide inteiro (recorta o excesso, como um "cover" de
// CSS), atrás de tudo - continua a mostrar a cor de fundo nas bordas se a
// proporção da imagem não bater exatamente com a do slide.
export async function aplicarFundoImagem(canvas, { url, w, h }) {
  if (!url) return
  let img
  try {
    img = await FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
  } catch {
    return
  }
  const escala = Math.max(w / img.width, h / img.height)
  const larguraFinal = img.width * escala
  const alturaFinal = img.height * escala
  img.set({
    left: (w - larguraFinal) / 2, top: (h - alturaFinal) / 2,
    originX: 'left', originY: 'top', scaleX: escala, scaleY: escala,
    papel: 'fundo-imagem', selectable: false, evented: false,
  })
  canvas.add(img)
  canvas.sendObjectToBack(img)
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
  img.set({ ...pos, papel: 'logo', selectable: false, evented: false, originX: 'left', originY: 'top' })
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
    return { corTitulo: '#2d2d2d', corCorpo: '#767676', tamanhoTituloBase: w * 0.042, tamanhoCorpoBase: w * 0.03 }
  }
  if (modelo === 'citacao') {
    return { corTitulo: corDestaque, corCorpo: '#666666', tamanhoTituloBase: w * 0.062, tamanhoCorpoBase: w * 0.034 }
  }
  return { corTitulo: '#1c1c1c', corCorpo: '#6b6b6b', tamanhoTituloBase: h * 0.058, tamanhoCorpoBase: h * 0.028 }
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
        left: area.left, top: 0, width: area.largura, originX: 'left', originY: 'top',
        fontSize: tamTitulo, fontWeight: 'bold', fontFamily: layout.fonteTitulo || 'Poppins',
        fill: corTitulo, lineHeight: espacamento, textAlign: alinhamento, ...extra,
      })
    : null
  const corpo = slide.corpo
    ? new Textbox(slide.corpo, {
        left: area.left, top: 0, width: area.largura, originX: 'left', originY: 'top',
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
      selectable: false, evented: false, papel: 'glass', originX: 'left', originY: 'top',
    })
    canvas.add(painel)
    canvas.sendObjectToBack(painel)
    criados.push(painel)
  }

  return criados
}

// ------------------------------------------------------------------ elementos fixos de marca por modelo

// Modelo "Padrão" (Minimalista): só handle no topo, categoria no topo direito,
// e categoria + "Arraste" no rodapé. Sem selo/pill no meio - o título+corpo já
// ocupa a metade de baixo do card (via layoutPadraoDe: posicao inf-esq).
function elementosCapa(canvas, { w, h, tipo, nomeMarca }) {
  const margemTopo = w * 0.06
  const handleTexto = '@' + (nomeMarca || __('suamarca')).toLowerCase().replace(/\s+/g, '')

  const handleTopo = new Textbox(handleTexto, {
    left: margemTopo, top: h * 0.055, width: w * 0.45, originX: 'left', originY: 'top',
    fontSize: Math.round(h * 0.019), fontFamily: 'Poppins', fill: '#4a4a4a', papel: 'marca',
  })
  const tagTopo = new Textbox(tipo || '', {
    left: w - margemTopo - w * 0.32, top: h * 0.055, width: w * 0.32, originX: 'left', originY: 'top',
    fontSize: Math.round(h * 0.019), fontFamily: 'Poppins', fill: '#4a4a4a', textAlign: 'right', papel: 'marca',
  })
  canvas.add(handleTopo, tagTopo)

  const rodapeEsq = new Textbox(tipo || '', {
    left: margemTopo, top: h * 0.93, width: w * 0.4, originX: 'left', originY: 'top',
    fontSize: Math.round(h * 0.018), fontFamily: 'Poppins', fill: '#8a8a8a', papel: 'marca',
  })
  canvas.add(rodapeEsq)
  if (tipo === 'Carrossel') {
    const rodapeDir = new Textbox(__('Arraste'), {
      left: w - margemTopo - w * 0.32, top: h * 0.93, width: w * 0.32, originX: 'left', originY: 'top',
      fontSize: Math.round(h * 0.018), fontFamily: 'Poppins', fill: '#8a8a8a', textAlign: 'right', papel: 'marca',
    })
    canvas.add(rodapeDir)
  }
}

// Modelo "Estilo Twitter" (Profile): avatar pequeno + nome em negrito + selo
// de verificado, com o @handle logo abaixo - tudo compacto, mesma margem
// esquerda do título/corpo (que renderiza como se fosse a bio/post abaixo).
function elementosPerfil(canvas, { w, h, nomeMarca }) {
  const nomeTexto = nomeMarca || __('Sua marca')
  const margemEsq = w * 0.186
  const avatarD = w * 0.045
  const avatarTop = h * 0.404

  const avatar = new Circle({
    left: margemEsq, top: avatarTop, radius: avatarD / 2, fill: '#3a3a3a', selectable: false, evented: false, papel: 'marca', originX: 'left', originY: 'top',
  })
  canvas.add(avatar)

  const nomeLeft = margemEsq + avatarD + w * 0.018
  const nomeTop = avatarTop - h * 0.006
  const nome = new Textbox(nomeTexto, {
    left: nomeLeft, top: nomeTop, originX: 'left', originY: 'top',
    width: w * 0.55, fontSize: Math.round(w * 0.03), fontWeight: 'bold', fontFamily: 'Poppins', fill: '#1c1c1c', papel: 'marca',
  })
  const selo = new Circle({
    left: nomeLeft + nomeTexto.length * w * 0.0175 + 8,
    top: nomeTop - h * 0.001, radius: w * 0.011, fill: '#3897f0', selectable: false, evented: false, papel: 'marca', originX: 'left', originY: 'top',
  })
  const check = new Textbox('✓', {
    left: selo.left - w * 0.0065, top: selo.top - w * 0.008, originX: 'left', originY: 'top',
    fontSize: Math.round(w * 0.016), fontFamily: 'Poppins', fill: '#ffffff', selectable: false, evented: false, papel: 'marca',
  })
  const handle = new Textbox('@' + nomeTexto.toLowerCase().replace(/\s+/g, ''), {
    left: nomeLeft, top: nomeTop + Math.round(w * 0.03) + 2, originX: 'left', originY: 'top',
    width: w * 0.55, fontSize: Math.round(w * 0.018), fontFamily: 'Poppins', fill: '#8a8a8a', papel: 'marca',
  })
  canvas.add(nome, selo, check, handle)
}

// A caixa de imagem da citação pode ficar embaixo (padrão) ou em cima -
// usado tanto pra desenhar o espaço reservado (quando ainda não tem imagem)
// quanto pra encaixar a imagem de verdade depois de enviada.
export function caixaCitacao(posicao, w, h) {
  const top = posicao === 'cima' ? h * 0.08 : h * 0.6
  return { left: w * 0.09, top, width: w * 0.82, height: h * 0.3 }
}

export function elementosCitacao(canvas, { w, h, imagemPosicao, temImagem }) {
  if (temImagem) return
  const caixa = caixaCitacao(imagemPosicao, w, h)
  const espacoImagem = new Rect({
    ...caixa, rx: 20, ry: 20, originX: 'left', originY: 'top',
    fill: '#f2f2f2', stroke: '#d8d8d8', strokeWidth: 1, strokeDashArray: [6, 6], papel: 'marca',
  })
  canvas.add(espacoImagem)
}

// Imagem de verdade dentro da caixa da citação - cobre a caixa toda
// (recorta o excesso, como um "cover" de CSS) e ganha as mesmas bordas
// arredondadas do espaço reservado que ela substitui.
export async function aplicarImagemCitacao(canvas, { url, posicao, w, h }) {
  if (!url) return
  let img
  try {
    img = await FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
  } catch {
    return
  }
  const caixa = caixaCitacao(posicao, w, h)
  const escala = Math.max(caixa.width / img.width, caixa.height / img.height)
  const larguraFinal = img.width * escala
  const alturaFinal = img.height * escala
  img.set({
    left: caixa.left - (larguraFinal - caixa.width) / 2,
    top: caixa.top - (alturaFinal - caixa.height) / 2,
    originX: 'left', originY: 'top', scaleX: escala, scaleY: escala,
    clipPath: new Rect({
      left: caixa.left, top: caixa.top, width: caixa.width, height: caixa.height,
      rx: 20, ry: 20, originX: 'left', originY: 'top', absolutePositioned: true,
    }),
    papel: 'citacao-imagem', selectable: false, evented: false,
  })
  canvas.add(img)
}

// ------------------------------------------------------------------ montagem geral

export function construirSlide(canvas, { tipo, modelo, slide, corMarca, corDestaque, nomeMarca }) {
  const { w, h } = TAMANHOS[tipo] || TAMANHOS.Carrossel
  const layout = { ...layoutPadraoDe(modelo), ...(slide.layout || {}) }
  const claraDeFundo = ['citacao', 'padrao', 'twitter'].includes(modelo)

  canvas.setDimensions({ width: w, height: h })
  const corBase = corDeFundo(modelo, corMarca)
  canvas.backgroundColor = corFundoFinal(canvas, { layout, corBase, corDestaque, w, h })

  aplicarPadraoFundo(canvas, { padrao: layout.fundoPadrao, w, h, clara: claraDeFundo })
  aplicarSombra(canvas, { estilo: layout.sombraEstilo, opacidade: layout.sombraOpacidade, w, h })

  if (modelo === 'twitter') elementosPerfil(canvas, { w, h, nomeMarca })
  else if (modelo === 'citacao') elementosCitacao(canvas, { w, h, imagemPosicao: layout.imagemPosicao, temImagem: !!layout.citacaoImagem })
  else elementosCapa(canvas, { w, h, tipo, nomeMarca })

  construirBlocoTexto(canvas, { slide, layout, w, h, ...estiloTextoPara(modelo, corDestaque, w, h) })

  canvas.renderAll()
}
