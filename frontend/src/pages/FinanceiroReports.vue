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
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { createResource } from 'frappe-ui'

const summary = createResource({
  url: 'crm.api.financeiro.get_report_summary',
  auto: true,
})

function formatCurrency(value) {
  value = value || 0
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}
</script>
