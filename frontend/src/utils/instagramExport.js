// Renderiza um slide do Gerador de conteúdo pra PNG, fora da tela (sem canvas
// visível) - usado no "Baixar Todos". Usa o mesmo desenho do editor
// (slide.canvas salvo) ou monta o modelo do zero se o slide nunca foi editado.
import { Canvas } from 'fabric'
import { TAMANHOS, construirSlide } from './instagramTemplates'

export async function renderizarSlidePng(slide, ctx) {
  const { w, h } = TAMANHOS[ctx.tipo] || TAMANHOS.Carrossel
  const el = document.createElement('canvas')
  const canvas = new Canvas(el, { width: w, height: h })
  try {
    if (slide.canvas) {
      await canvas.loadFromJSON(slide.canvas)
      canvas.setDimensions({ width: slide.canvas.width || w, height: slide.canvas.height || h })
      canvas.renderAll()
    } else {
      await document.fonts.ready
      construirSlide(canvas, { ...ctx, slide })
    }
    return canvas.toDataURL({ format: 'png', multiplier: 1 })
  } finally {
    canvas.dispose()
  }
}

export async function baixarTodosSlides(slides, ctx, tituloConversa) {
  const base = (tituloConversa || 'carrossel').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) || 'carrossel'
  for (let i = 0; i < slides.length; i++) {
    const url = await renderizarSlidePng(slides[i], ctx)
    const a = document.createElement('a')
    a.href = url
    a.download = `${base}-slide-${i + 1}.png`
    document.body.appendChild(a)
    a.click()
    a.remove()
    // pequena pausa entre downloads - navegadores bloqueiam vários downloads
    // simultâneos disparados muito rápido um atrás do outro
    await new Promise((resolve) => setTimeout(resolve, 400))
  }
}
