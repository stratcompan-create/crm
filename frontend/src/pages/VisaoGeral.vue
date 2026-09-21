<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Visão Geral') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex gap-1 border-b border-outline-gray-1 px-4 pt-1">
    <button
      v-for="t in tabs"
      :key="t.key"
      type="button"
      class="-mb-px border-b-2 px-3 py-2 text-p-base"
      :class="tab === t.key ? 'border-ink-gray-9 font-medium text-ink-gray-9' : 'border-transparent text-ink-gray-5'"
      @click="setTab(t.key)"
    >
      {{ t.label }}
      <span
        v-if="t.key === 'saude' && health.data?.pendencias"
        class="ml-1 rounded-full bg-surface-red-2 px-1.5 text-xs font-medium text-ink-red-6"
      >
        {{ health.data.pendencias }}
      </span>
    </button>
  </div>

  <!-- Visão geral: arquivos e conversa -->
  <EmptyState
    v-if="tab === 'visao'"
    name="Arquivos"
    :icon="FolderIcon"
    :title="__('Seus arquivos')"
    :description="__('Use a barra lateral à esquerda para navegar, criar pastas e enviar arquivos — igual num explorador de arquivos.')"
  />

  <!-- Saúde do negócio -->
  <div v-else class="flex-1 overflow-y-auto px-4 pb-10 pt-5 sm:px-6">
    <div class="mx-auto max-w-4xl">
      <div class="flex items-end justify-between gap-3">
        <div>
          <div class="text-lg-semibold text-ink-gray-9">{{ __('Saúde do negócio') }}</div>
          <p class="text-p-sm text-ink-gray-6">
            {{
              health.data
                ? health.data.pendencias
                  ? __('{0} ponto(s) precisam da sua atenção hoje.', [health.data.pendencias])
                  : __('Tudo em dia. Nada pendente por aqui.')
                : __('Carregando...')
            }}
          </p>
        </div>
        <Button variant="ghost" icon="lucide-refresh-cw" :loading="health.loading" @click="health.reload()" />
      </div>

      <div class="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
        <button
          v-for="i in health.data?.itens || []"
          :key="i.key"
          type="button"
          class="rounded-lg border p-4 text-left transition hover:shadow-sm"
          :class="cardClass(i)"
          @click="router.push({ name: i.route })"
        >
          <div class="text-p-sm text-ink-gray-6">{{ __(i.label) }}</div>
          <div class="mt-1 text-2xl font-semibold" :class="numberClass(i)">{{ i.count }}</div>
          <div v-if="i.detail" class="mt-1 truncate text-xs text-ink-gray-5">{{ i.detail }}</div>
          <div v-else-if="i.key === 'atrasados' && health.data?.valores?.atrasado" class="mt-1 text-xs text-ink-gray-5">
            {{ brl(health.data.valores.atrasado) }}
          </div>
          <div v-else-if="i.key === 'a_vencer' && health.data?.valores?.a_vencer" class="mt-1 text-xs text-ink-gray-5">
            {{ brl(health.data.valores.a_vencer) }}
          </div>
        </button>
      </div>

      <div v-if="health.data?.gestor && reports.data?.length" class="mt-8">
        <div class="text-lg-semibold text-ink-gray-9">{{ __('Resumos semanais') }}</div>
        <p class="text-p-sm text-ink-gray-6">{{ __('Gerados toda segunda-feira, às 8h, com a semana anterior.') }}</p>
        <div class="mt-3 flex flex-col gap-2">
          <div
            v-for="r in reports.data.slice(0, 4)"
            :key="r.name"
            class="flex items-center justify-between rounded-lg border border-outline-gray-2 px-4 py-3"
          >
            <span class="text-p-base text-ink-gray-8">{{ __('Semana de {0} a {1}', [fmt(r.inicio), fmt(r.fim)]) }}</span>
            <a v-if="r.arquivo" :href="r.arquivo" target="_blank" class="text-p-sm font-medium text-ink-gray-9 underline">
              {{ __('Baixar PDF') }}
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import FolderIcon from '~icons/lucide/folder'
import { Button, createResource } from 'frappe-ui'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const tabs = [
  { key: 'visao', label: __('Visão Geral') },
  { key: 'saude', label: __('Saúde do negócio') },
]

function savedTab() {
  try {
    const v = localStorage.getItem('crm_visao_tab')
    return tabs.some((t) => t.key === v) ? v : 'visao'
  } catch (e) {
    return 'visao'
  }
}
const tab = ref(savedTab())
function setTab(key) {
  tab.value = key
  try {
    localStorage.setItem('crm_visao_tab', key)
  } catch (e) {}
}

const health = createResource({ url: 'crm.api.saude.get_business_health', auto: true })
const reports = createResource({ url: 'crm.api.automacoes.list_weekly_reports', auto: true, onError() {} })
const fmt = (v) => (v ? v.split('-').reverse().slice(0, 2).join('/') : '')
const brl = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)

function cardClass(i) {
  if (!i.count) return 'border-outline-gray-2'
  return (
    { bad: 'border-outline-red-2 bg-surface-red-1', warn: 'border-outline-amber-2 bg-surface-amber-1', info: 'border-outline-blue-2 bg-surface-blue-1' }[i.tone] ||
    'border-outline-gray-2'
  )
}
function numberClass(i) {
  if (!i.count) return 'text-ink-gray-4'
  return { bad: 'text-ink-red-6', warn: 'text-ink-amber-3', info: 'text-ink-blue-3' }[i.tone] || 'text-ink-gray-9'
}
</script>
