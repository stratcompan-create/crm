<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Recorrência') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Receita Recorrente Mensal (MRR)') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ money(mrr.data?.mrr) }}</div>
        <div v-if="mrr.data?.meta_mrr" class="mt-3">
          <div class="h-2 w-full overflow-hidden rounded-full bg-surface-gray-3">
            <div class="h-2 rounded-full bg-[var(--stratcompany-accent)]" :style="{ width: progress + '%' }" />
          </div>
          <div class="mt-1 text-p-sm text-ink-gray-5">
            {{ progress }}% {{ __('da meta de') }} {{ money(mrr.data.meta_mrr) }}
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Clientes com mensalidade') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ mrr.data?.clientes || 0 }}</div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Ticket médio por cliente') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ money(ticket) }}</div>
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Mensalidades por mês') }}</div>
      <div v-if="!mrr.data?.series?.length" class="text-p-sm text-ink-gray-5">
        {{ __('Ainda não há mensalidades. Cadastre uma Receita do tipo Mensalidade.') }}
      </div>
      <div v-else class="flex h-40 items-end gap-3">
        <div v-for="p in mrr.data.series" :key="p.month" class="flex flex-1 flex-col items-center justify-end gap-1">
          <div class="text-p-xs text-ink-gray-6">{{ money(p.total) }}</div>
          <div class="w-full rounded-t bg-[var(--stratcompany-accent)]" :style="{ height: barHeight(p.total) + '%' }" />
          <div class="text-p-xs text-ink-gray-5">{{ monthLabel(p.month) }}</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('A renovar nos próximos 30 dias') }}</div>
        <div v-if="!mrr.data?.proximas?.length" class="text-p-sm italic text-ink-gray-4">{{ __('Nada a vencer.') }}</div>
        <div v-for="i in mrr.data?.proximas || []" :key="i.name" class="flex items-center justify-between border-t border-outline-gray-1 py-2 text-p-sm">
          <span class="truncate text-ink-gray-8">{{ i.cliente }}</span>
          <span class="shrink-0 text-ink-gray-6">{{ money(i.valor) }} · {{ __('em') }} {{ i.dias }} {{ __('dias') }}</span>
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Mensalidades atrasadas') }}</div>
        <div v-if="!mrr.data?.atrasadas?.length" class="text-p-sm italic text-ink-gray-4">{{ __('Nenhuma atrasada.') }}</div>
        <div v-for="i in mrr.data?.atrasadas || []" :key="i.name" class="flex items-center justify-between border-t border-outline-gray-1 py-2 text-p-sm">
          <span class="truncate text-ink-gray-8">{{ i.cliente }}</span>
          <span class="shrink-0 text-ink-red-6">{{ money(i.valor) }} · {{ i.dias }} {{ __('dias de atraso') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { createResource } from 'frappe-ui'
import { computed } from 'vue'

const mrr = createResource({ url: 'crm.api.financeiro.get_mrr', auto: true })

const money = (v) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)

const ticket = computed(() =>
  mrr.data?.clientes ? mrr.data.mrr / mrr.data.clientes : 0,
)
const progress = computed(() =>
  mrr.data?.meta_mrr
    ? Math.min(100, Math.round((mrr.data.mrr / mrr.data.meta_mrr) * 100))
    : 0,
)
const maxTotal = computed(() =>
  Math.max(1, ...(mrr.data?.series || []).map((p) => p.total)),
)
const barHeight = (total) => Math.max(4, Math.round((total / maxTotal.value) * 100))
const monthLabel = (m) => {
  const [y, mo] = m.split('-')
  return new Date(Number(y), Number(mo) - 1, 1).toLocaleDateString('pt-BR', {
    month: 'short',
    year: '2-digit',
  })
}
</script>
