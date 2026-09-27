import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

// Seeded from the boot payload so the office's own name/logo is there on the
// very first paint instead of a generic placeholder while settings load.
const brand = reactive({ ...(window.crm_brand || {}) })

const BLANK_ICON =
  'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='

function applyBrandToHead() {
  const href = brand.favicon || BLANK_ICON
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

applyBrandToHead()

const _settings = createDocumentResource({
  doctype: 'FCRM Settings',
  name: 'FCRM Settings',
  onSuccess: () => {
    getSettings().setupBrand()
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
    applyBrandToHead()
  }

  return {
    _settings,
    settings,
    brand,
    setupBrand,
  }
}
