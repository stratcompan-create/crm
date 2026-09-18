<template>
  <!-- h-14 lines up with the sidebar's own header row (p-2 padding + the
       h-12 UserDropdown button) — so this reads as a continuation of that
       same top strip, not a second stacked header. -->
  <div
    class="flex h-14 shrink-0 items-center justify-center border-b border-outline-gray-1 bg-surface-white px-4"
  >
    <nav class="flex items-center gap-1">
      <button
        v-for="section in sections"
        :key="section.key"
        type="button"
        class="relative rounded-md px-4 py-2 text-sm font-medium transition-all duration-300 ease-out active:scale-90"
        :class="
          activeKey === section.key
            ? 'scale-105 bg-[var(--stratcompany-accent)] text-white shadow-[0_2px_16px_-2px_var(--stratcompany-accent-glow)]'
            : 'text-ink-gray-6 hover:scale-105 hover:bg-surface-gray-2 hover:text-ink-gray-8'
        "
        @click="handleClick(section)"
      >
        {{ __(section.label) }}
        <span
          class="absolute inset-x-3 -bottom-0.5 h-[3px] rounded-full bg-[var(--stratcompany-accent)] shadow-[0_0_8px_var(--stratcompany-accent-glow-soft)] transition-transform duration-300 ease-out"
          :class="activeKey === section.key ? 'scale-x-100' : 'scale-x-0'"
        />
      </button>
    </nav>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import router from '@/router'

const route = useRoute()

// Route names that live inside the classic Frappe CRM sidebar (Leads,
// Deals, Contacts...) — all of them fall under the single "CRM" tab here.
const CRM_ROUTE_NAMES = [
  'Leads',
  'Lead',
  'Deals',
  'Deal',
  'Notes',
  'Tasks',
  'Contacts',
  'Contact',
  'Organizations',
  'Organization',
  'Call Logs',
  'Calendar',
  'Contas',
  'WhatsApp',
  'Equipe',
]

const sections = [
  { key: 'overview', label: 'Visão Geral', route: 'Dashboard' },
  { key: 'meusite', label: 'Meu Site', route: 'MeuSite' },
  { key: 'instagram', label: 'Instagram', route: 'Instagram' },
  { key: 'financeiro', label: 'Financeiro', route: 'Financeiro' },
  { key: 'crm', label: 'CRM', route: 'Leads' },
]

const activeKey = computed(() => {
  const name = route.name
  if (name === 'Dashboard') return 'overview'
  if (name === 'MeuSite') return 'meusite'
  if (name === 'Instagram') return 'instagram'
  if (
    name === 'Financeiro' ||
    name === 'Financeiro Metas' ||
    name === 'Financeiro Relatorios' ||
    name === 'Financeiro Saude' ||
    name === 'Financeiro Calculadora' ||
    name === 'Financeiro Estimador'
  )
    return 'financeiro'
  if (CRM_ROUTE_NAMES.includes(name)) return 'crm'
  return ''
})

function handleClick(section) {
  router.push({ name: section.route })
}
</script>
