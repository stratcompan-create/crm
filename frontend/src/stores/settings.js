import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

// Seeded from the boot payload so the office's own name/logo is there on the
// very first paint instead of a generic placeholder while settings load.
const brand = reactive({ ...(window.crm_brand || {}) })

// icone da agencia (losango Stratcompany) - mesmo fallback do lado do servidor
// (crm.html, /login, /agendar, /documentos), pra nunca cair no icone generico do
// Frappe/Frappe Cloud quando o cliente ainda nao tem favicon proprio.
const AGENCIA_FAVICON = '/assets/crm/images/marca-agencia.png'

function applyBrandToHead() {
  const href = brand.favicon || AGENCIA_FAVICON
  for (const rel of ['icon', 'apple-touch-icon']) {
    let link = document.querySelector(`link[rel="${rel}"]`)
    if (!link) {
      link = document.createElement('link')
      link.rel = rel
      document.head.appendChild(link)
    }
    link.removeAttribute('type')
    link.removeAttribute('sizes')
    link.href = href
  }
}

const DEFAULT_ACCENT = '#8aa1a9'

function hexToRgb(hex) {
  const h = (hex || '').replace('#', '')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `${r}, ${g}, ${b}`
}

// Cor do item/aba ativo (barra lateral e TopNav) - a mesma usada nas propostas
// (Configuracoes > Marca). Aplicada como variavel inline em <html>, que tem
// prioridade sobre a regra padrao (sage) e a de modo escuro em index.css, entao
// cada cliente ve a cor dele, clara ou escura, em vez da cor fixa da Stratcompany.
function applyAccentToRoot() {
  const rgb = hexToRgb(brand.accent) || hexToRgb(DEFAULT_ACCENT)
  const accent = hexToRgb(brand.accent) ? brand.accent : DEFAULT_ACCENT
  const root = document.documentElement.style
  root.setProperty('--stratcompany-accent', accent)
  root.setProperty('--stratcompany-accent-glow', `rgba(${rgb}, 0.65)`)
  root.setProperty('--stratcompany-accent-glow-soft', `rgba(${rgb}, 0.9)`)
  root.setProperty('--stratcompany-explorer', accent)
}

applyBrandToHead()
applyAccentToRoot()

const _settings = createDocumentResource({
  doctype: 'FCRM Settings',
  name: 'FCRM Settings',
  onSuccess: () => {
    getSettings().setupBrand()
  },
  // Se o carregamento inicial falhar (ex.: app recem-aberto disputando com a
  // sessao ainda sendo estabelecida), _settings.doc fica null pro resto da
  // sessao inteira, sem nenhum aviso - e qualquer tela que chame
  // _settings.setValue.submit(...) depois disso quebra silenciosamente
  // (o beforeSubmit do frappe-ui faz Object.assign(null, ...), que da erro
  // sem passar pelo onError de setValue). Tenta de novo sozinho em vez de
  // deixar isso morto pelo resto da sessao.
  onError: (err) => {
    // eslint-disable-next-line no-console
    console.error('Falha ao carregar FCRM Settings, tentando de novo em 1.5s:', err)
    setTimeout(() => _settings.reload(), 1500)
  },
  // Sem essa chave, o frappe-ui nao monta o sub-recurso _settings.setValue -
  // era por isso que MeuSite.vue (que chama _settings.setValue.submit(...))
  // sempre falhava com "Falha ao salvar o site" antes mesmo de chegar no
  // servidor (nenhum erro ficava registrado no CRM por causa disso).
  setValue: {
    onError: (err) => {
      // eslint-disable-next-line no-console
      console.error('Falha ao salvar FCRM Settings:', err)
    },
  },
})

// Espelha _settings.doc sempre - antes "settings" só era preenchido uma vez, na mão,
// dentro do onSuccess acima; se esse momento específico falhasse por qualquer motivo
// (sessão ainda carregando, ordem de montagem dos componentes, etc.), settings.value
// ficava vazio pelo resto da sessão inteira mesmo com o documento já carregado certo
// (é o que já vinha acontecendo com o menu de Configurações e o Meu Site).
const settings = computed(() => _settings.doc || {})

export function getSettings() {
  function setupBrand() {
    brand.name = settings.value?.brand_name
    brand.logo = settings.value?.brand_logo
    brand.favicon = settings.value?.favicon
    brand.accent = settings.value?.brand_accent
    applyBrandToHead()
    applyAccentToRoot()
  }

  return {
    _settings,
    settings,
    brand,
    setupBrand,
  }
}
