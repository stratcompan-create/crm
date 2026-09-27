<template>
  <Dropdown :options="dropdownItems" v-bind="$attrs">
    <template #default="{ open }">
      <button
        class="flex h-12 items-center rounded-md py-2 duration-300 ease-in-out"
        :class="
          isCollapsed
            ? 'w-auto px-0'
            : open
              ? 'w-full px-2 bg-surface-elevation-3 shadow-sm'
              : 'w-full px-2 hover:bg-surface-gray-2'
        "
      >
        <BrandLogo v-model="brand" class="h-8 max-w-16 flex-shrink-0" />
        <div
          class="flex flex-1 flex-col text-left duration-300 ease-in-out truncate"
          :class="
            isCollapsed
              ? 'ml-0 w-0 overflow-hidden opacity-0'
              : 'ml-2 w-auto opacity-100'
          "
        >
          <div class="text-base-medium leading-none text-ink-gray-9 truncate">
            {{ __(brand.name || 'CRM') }}
          </div>
          <div class="mt-1 text-sm leading-none text-ink-gray-7 truncate">
            {{ user.full_name }}
          </div>
        </div>
        <div
          class="duration-300 ease-in-out"
          :class="
            isCollapsed
              ? 'ml-0 w-0 overflow-hidden opacity-0'
              : 'ml-2 w-auto opacity-100'
          "
        >
          <span
            class="lucide-chevron-down size-4 text-ink-gray-5"
            aria-hidden="true"
          />
        </div>
      </button>
    </template>
  </Dropdown>
</template>

<script setup>
import BrandLogo from '@/components/BrandLogo.vue'
import FrappeCloudIcon from '@/components/Icons/FrappeCloudIcon.vue'
import { sessionStore } from '@/stores/session'
import { usersStore } from '@/stores/users'
import { getSettings } from '@/stores/settings'
import { showSettings, isMobileView } from '@/composables/settings'
import { showAboutModal } from '@/composables/modals'
import { confirmLoginToFrappeCloud } from '@/composables/frappecloud'
import { createResource, Dropdown } from 'frappe-ui'
import { computed, h, markRaw } from 'vue'

defineProps({
  isCollapsed: { type: Boolean, default: false },
})

const { settings, brand } = getSettings()
const { logout } = sessionStore()
const { getUser } = usersStore()

const user = computed(() => getUser() || {})

// Configurações e Sair são navegação essencial: nunca dependem de a Ficha de
// Configurações (FCRM Settings) ter carregado certo. Só os itens EXTRAS
// (não padrão) vêm de lá - hoje ninguém usa isso, mas fica compatível caso
// algum dia alguém cadastre um item próprio.
const STANDARD_ITEMS = {
  settings: { name1: 'settings', label: 'Settings', icon: 'settings', is_standard: 1 },
  login_to_fc: { name1: 'login_to_fc', label: 'Login to Frappe Cloud', is_standard: 1 },
  about: { name1: 'about', label: 'About', icon: 'info', is_standard: 1 },
  logout: { name1: 'logout', label: 'Log out', icon: 'log-out', is_standard: 1 },
}

const dropdownItems = computed(() => {
  const principais = []
  if (!isMobileView.value) {
    principais.push(getStandardItem(STANDARD_ITEMS.settings))
    if (window.is_fc_site) principais.push(getStandardItem(STANDARD_ITEMS.login_to_fc))
  }
  principais.push(getStandardItem(STANDARD_ITEMS.about))

  const extras = (settings.value?.dropdown_items || []).filter(
    (item) => !item.hidden && item.name1 !== 'app_selector' && !item.is_standard,
  )
  extras.forEach((item) => principais.push(dropdownItemObj(item)))

  return [
    { group: 'Dropdown Items', hideLabel: true, items: principais },
    { group: '', hideLabel: true, items: [getStandardItem(STANDARD_ITEMS.logout)] },
  ]
})

function dropdownItemObj(item) {
  let _item = JSON.parse(JSON.stringify(item))
  let icon = _item.icon || 'external-link'
  if (typeof icon === 'string' && icon.startsWith('<svg')) {
    icon = markRaw(h('div', { innerHTML: icon }))
  }
  _item.icon = icon

  if (_item.is_standard) {
    return getStandardItem(_item)
  }

  return {
    icon: _item.icon,
    label: __(_item.label),
    onClick: () =>
      window.open(_item.route, _item.open_in_new_window ? '_blank' : ''),
  }
}

function getStandardItem(item) {
  switch (item.name1) {
    case 'settings':
      return {
        icon: item.icon,
        label: __(item.label),
        onClick: () => (showSettings.value = true),
        condition: () => !isMobileView.value,
      }
    case 'login_to_fc':
      return {
        icon: h(FrappeCloudIcon),
        label: __(item.label),
        onClick: () => confirmLoginToFrappeCloud(),
        condition: () => !isMobileView.value && window.is_fc_site,
      }
    case 'about':
      return {
        icon: item.icon,
        label: __(item.label),
        onClick: () => (showAboutModal.value = true),
      }
    case 'logout':
      return {
        icon: item.icon,
        label: __(item.label),
        onClick: () => logout.submit(),
      }
  }
}
</script>
