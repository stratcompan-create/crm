import { computed, ref } from 'vue'

export const mobileSidebarOpened = ref(false)

// window.innerWidth sozinho não é reativo - sem o listener de resize, esse valor
// fica travado no que era na hora que a página carregou (ex.: girar o iPad, usar
// tela dividida, redimensionar a janela) e nunca mais atualiza pelo resto da sessão.
const windowWidth = ref(window.innerWidth)
window.addEventListener('resize', () => {
  windowWidth.value = window.innerWidth
})
export const isMobileView = computed(() => windowWidth.value < 768)

export const showSettings = ref(false)

export const disableSettingModalOutsideClick = ref(false)

export const activeSettingsPage = ref('')
