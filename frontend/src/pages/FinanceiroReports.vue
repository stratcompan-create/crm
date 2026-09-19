<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Relatórios') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Recebido (Pago)') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-green-6">
          {{ formatCurrency(summary.data?.Pago) }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Pendente') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-amber-6">
          {{ formatCurrency(summary.data?.Pendente) }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Atrasado') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-red-6">
          {{ formatCurrency(summary.data?.Atrasado) }}
        </div>
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="text-p-sm text-ink-gray-6">{{ __('Total Geral (todos os honorários cadastrados)') }}</div>
      <div class="mt-1 text-3xl font-semibold text-ink-gray-9">
        {{ formatCurrency(summary.data?.total_geral) }}
      </div>
    </div>

    <div v-if="!summary.loading && !summary.data?.total_geral" class="text-p-base text-ink-gray-5">
      {{ __('Ainda não há Honorários cadastrados para gerar relatório.') }}
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Fluxo de Caixa') }}</div>
      <div class="overflow-x-auto">
        <table class="w-full text-p-sm">
          <thead>
            <tr class="text-left text-ink-gray-5">
              <th class="py-1 pr-4 font-medium">{{ __('Mês') }}</th>
              <th class="py-1 pr-4 text-right font-medium">{{ __('Entradas') }}</th>
              <th class="py-1 pr-4 text-right font-medium">{{ __('Saídas') }}</th>
              <th class="py-1 pr-4 text-right font-medium">{{ __('Saldo do mês') }}</th>
              <th class="py-1 pr-4 text-right font-medium">{{ __('Saldo acumulado') }}</th>
              <th class="py-1 text-right font-medium">{{ __('Previsto (a receber / a pagar)') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in cashflow.data || []" :key="row.month" class="border-t border-outline-gray-1">
              <td class="py-2 pr-4 text-ink-gray-8">{{ monthLabel(row.month) }}</td>
              <td class="py-2 pr-4 text-right text-ink-green-6">{{ formatCurrency(row.entradas) }}</td>
              <td class="py-2 pr-4 text-right text-ink-red-6">{{ formatCurrency(row.saidas) }}</td>
              <td class="py-2 pr-4 text-right font-medium" :class="row.saldo < 0 ? 'text-ink-red-6' : 'text-ink-gray-9'">{{ formatCurrency(row.saldo) }}</td>
              <td class="py-2 pr-4 text-right text-ink-gray-7">{{ formatCurrency(row.acumulado) }}</td>
              <td class="py-2 text-right text-ink-gray-6">{{ formatCurrency(row.prev_entradas) }} / {{ formatCurrency(row.prev_saidas) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Receita por Cliente') }}</div>
        <div v-if="!breakdown.data?.clientes?.length" class="text-p-sm italic text-ink-gray-4">{{ __('Sem dados ainda.') }}</div>
        <div v-for="c in breakdown.data?.clientes || []" :key="c.cliente" class="mb-3">
          <div class="flex justify-between text-p-sm">
            <span class="truncate text-ink-gray-8">{{ c.cliente }}</span>
            <span class="shrink-0 text-ink-gray-6">{{ formatCurrency(c.pago + c.pendente) }}</span>
          </div>
          <div class="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-gray-3">
            <div class="h-2 rounded-full bg-[var(--stratcompany-accent)]" :style="{ width: pct(c.pago + c.pendente, maxClient) + '%' }" />
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Receita por Serviço') }}</div>
        <div v-if="!breakdown.data?.servicos?.length" class="text-p-sm italic text-ink-gray-4">{{ __('Sem dados ainda.') }}</div>
        <div v-for="s in breakdown.data?.servicos || []" :key="s.servico" class="mb-3">
          <div class="flex justify-between text-p-sm">
            <span class="truncate text-ink-gray-8">{{ __(s.servico) }}</span>
            <span class="shrink-0 text-ink-gray-6">{{ formatCurrency(s.pago + s.pendente) }}</span>
          </div>
          <div class="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-gray-3">
            <div class="h-2 rounded-full bg-[var(--stratcompany-accent)]" :style="{ width: pct(s.pago + s.pendente, maxService) + '%' }" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { createResource } from 'frappe-ui'
import { computed } from 'vue'

const summary = createResource({
  url: 'crm.api.financeiro.get_report_summary',
  auto: true,
})

const cashflow = createResource({
  url: 'crm.api.financeiro.get_cashflow',
  params: { months: 6 },
  auto: true,
})
const breakdown = createResource({
  url: 'crm.api.financeiro.get_revenue_breakdown',
  auto: true,
})

const maxClient = computed(() =>
  Math.max(1, ...(breakdown.data?.clientes || []).map((c) => c.pago + c.pendente)),
)
const maxService = computed(() =>
  Math.max(1, ...(breakdown.data?.servicos || []).map((c) => c.pago + c.pendente)),
)
const pct = (value, max) => Math.max(2, Math.round((value / max) * 100))
const monthLabel = (m) => {
  const [y, mo] = m.split('-')
  return new Date(Number(y), Number(mo) - 1, 1).toLocaleDateString('pt-BR', {
    month: 'long',
    year: 'numeric',
  })
}

function formatCurrency(value) {
  value = value || 0
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}
</script>
