<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Visão Geral') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto px-4 pb-10 pt-5 sm:px-6">
    <div class="mx-auto max-w-4xl">
      <!-- Painel de saúde -->
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

      <div class="mt-8">
        <EmptyState
          name="Arquivos"
          :icon="FolderIcon"
          :title="__('Seus arquivos')"
          :description="__('Use a barra lateral à esquerda para navegar, criar pastas e enviar arquivos — igual num explorador de arquivos.')"
        />
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import FolderIcon from '~icons/lucide/folder'
import { Button, createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
const health = createResource({ url: 'crm.api.saude.get_business_health', auto: true })

const brl = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)

function cardClass(i) {
  if (!i.count) return 'border-outline-gray-2'
  return { bad: 'border-outline-red-2 bg-surface-red-1', warn: 'border-outline-amber-2 bg-surface-amber-1', info: 'border-outline-blue-2 bg-surface-blue-1' }[i.tone] || 'border-outline-gray-2'
}
function numberClass(i) {
  if (!i.count) return 'text-ink-gray-4'
  return { bad: 'text-ink-red-6', warn: 'text-ink-amber-3', info: 'text-ink-blue-3' }[i.tone] || 'text-ink-gray-9'
}
</script>
