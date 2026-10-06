<template>
  <FrappeUIProvider>
    <NotPermitted v-if="$route.name === 'Not Permitted'" />
    <router-view v-else-if="$route.name === 'Onboarding'" />
    <Layout v-else-if="session.isLoggedIn" class="isolate">
      <router-view :key="$route.fullPath" />
    </Layout>
    <AssistenteClaude v-if="session.isLoggedIn && !!window.assistente_ativo" />
    <Dialogs />
    <DoctypeModals />
    <EventNotificationPopup />
  </FrappeUIProvider>
</template>

<script setup>
import NotPermitted from '@/pages/NotPermitted.vue'
import AssistenteClaude from '@/components/AssistenteClaude.vue'
import EventNotificationPopup from '@/components/EventNotificationPopup.vue'
import DoctypeModals from '@/components/Modals/DoctypeModals.vue'
import { Dialogs } from '@/utils/dialogs'
import { sessionStore } from '@/stores/session'
import { FrappeUIProvider, setConfig, useTheme } from 'frappe-ui'
import { computed, defineAsyncComponent, onMounted, provide, ref } from 'vue'
import { toast } from 'frappe-ui'

const session = sessionStore()
provide('session', session)

// `useTheme()` auto-inicializa no primeiro uso (efeito colateral da propria
// lib): se nao achar nada salvo, ja escreve 'system' no localStorage sozinho -
// entao checar `localStorage.getItem('theme') DEPOIS de chamar useTheme() (como
// era feito antes) sempre via algo salvo e nunca forcava 'light' de verdade. Le
// o valor salvo ANTES de chamar useTheme(), pra pegar o estado real da visita.
const storedTheme = localStorage.getItem('theme')
const { setTheme } = useTheme()
// 'system' segue o SO e podia cair em modo escuro sem o usuario pedir - so
// mantem tema salvo quando foi uma escolha explicita (claro ou escuro) feita
// no seletor de tema; qualquer outra coisa (nada salvo, ou 'system') vira claro.
if (storedTheme !== 'light' && storedTheme !== 'dark') {
  setTheme('light')
}

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  const result = params.get('gdrive')
  if (!result) return
  if (result === 'ok') toast.success(__('Google Drive conectado. Configure a pasta em Configurações → Integrações.'))
  else toast.error(__('Não foi possível conectar o Google Drive. Tente de novo.'))
  params.delete('gdrive')
  const qs = params.toString()
  window.history.replaceState({}, '', window.location.pathname + (qs ? `?${qs}` : ''))
})

const MobileLayout = defineAsyncComponent(
  () => import('./components/Layouts/MobileLayout.vue'),
)
const DesktopLayout = defineAsyncComponent(
  () => import('./components/Layouts/DesktopLayout.vue'),
)
// window.innerWidth sozinho não é reativo - sem acompanhar o resize, essa escolha
// ficava travada no tamanho de tela de quando a página carregou pela primeira vez.
const windowWidth = ref(window.innerWidth)
window.addEventListener('resize', () => {
  windowWidth.value = window.innerWidth
})
const Layout = computed(() => {
  if (windowWidth.value < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
setConfig('translatedMessages', window.translated_messages || {})
</script>
