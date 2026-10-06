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
    applyBrandToHead()
  }

  return {
    _settings,
    settings,
    brand,
    setupBrand,
  }
}
