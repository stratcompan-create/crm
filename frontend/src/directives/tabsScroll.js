// Barra de abas que rola para o lado: arrastar com o mouse, roda do mouse, setas nas pontas
// e toque no celular. Usada nas telas de Lead e Negócio, onde as abas passam da largura da tela.
// Uso: <Tabs v-tabs-scroll ...>

const ARROW_STYLE =
  'position:absolute;top:8px;z-index:5;width:28px;height:28px;border-radius:9999px;border:1px solid #d5dbe0;' +
  'background:#fff;color:#334;font-size:18px;line-height:1;display:none;align-items:center;justify-content:center;' +
  'cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.12);padding:0;'

function setup(root) {
  const list = root.querySelector('[role="tablist"]')
  if (!list || list.__tabsScroll) return !!list
  list.__tabsScroll = true
  if (getComputedStyle(root).position === 'static') root.style.position = 'relative'
  list.style.cursor = 'grab'
  list.style.scrollbarWidth = 'none'

  const mkArrow = (side, text) => {
    const b = document.createElement('button')
    b.type = 'button'
    b.setAttribute('aria-label', side === 'left' ? 'Abas anteriores' : 'Próximas abas')
    b.style.cssText = ARROW_STYLE + (side === 'left' ? 'left:6px;' : 'right:6px;')
    b.textContent = text
    b.addEventListener('click', () => list.scrollBy({ left: side === 'left' ? -240 : 240, behavior: 'smooth' }))
    root.appendChild(b)
    return b
  }
  const left = mkArrow('left', '‹')
  const right = mkArrow('right', '›')

  const update = () => {
    const overflow = list.scrollWidth - list.clientWidth > 4
    left.style.display = overflow && list.scrollLeft > 4 ? 'flex' : 'none'
    right.style.display = overflow && list.scrollLeft < list.scrollWidth - list.clientWidth - 4 ? 'flex' : 'none'
  }

  // arrastar com o mouse (sem atrapalhar o clique numa aba)
  let down = false
  let moved = 0
  let startX = 0
  let startLeft = 0
  const onDown = (e) => {
    if (e.button !== 0) return
    down = true
    moved = 0
    startX = e.clientX
    startLeft = list.scrollLeft
  }
  const onMove = (e) => {
    if (!down) return
    const dx = e.clientX - startX
    moved = Math.max(moved, Math.abs(dx))
    if (moved > 5) {
      list.scrollLeft = startLeft - dx
      list.style.cursor = 'grabbing'
    }
  }
  const onUp = () => {
    if (!down) return
    down = false
    list.style.cursor = 'grab'
  }
  const onClickCapture = (e) => {
    if (moved > 5) {
      e.stopPropagation()
      e.preventDefault()
      moved = 0
    }
  }
  // roda do mouse rola as abas para o lado
  const onWheel = (e) => {
    if (list.scrollWidth <= list.clientWidth) return
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      list.scrollLeft += e.deltaY
      e.preventDefault()
    }
  }

  list.addEventListener('mousedown', onDown)
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
  list.addEventListener('click', onClickCapture, true)
  list.addEventListener('wheel', onWheel, { passive: false })
  list.addEventListener('scroll', update, { passive: true })
  const ro = new ResizeObserver(update)
  ro.observe(list)
  const mo = new MutationObserver(update)
  mo.observe(list, { childList: true, subtree: true })
  update()

  root.__tabsCleanup = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    ro.disconnect()
    mo.disconnect()
    left.remove()
    right.remove()
  }
  return true
}

export default {
  mounted(root) {
    // a lista de abas aparece depois do primeiro desenho
    let tries = 0
    const attempt = () => {
      if (!root.isConnected || setup(root) || ++tries > 20) return
      setTimeout(attempt, 100)
    }
    attempt()
  },
  unmounted(root) {
    root.__tabsCleanup?.()
  },
}
