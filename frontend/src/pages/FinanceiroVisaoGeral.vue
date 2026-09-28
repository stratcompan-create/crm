<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Visão Geral') }}</div>
    </template>
    <template #right-header>
      <Dropdown :options="periodos">
        <template #default="{ open }">
          <Button :label="periodoAtual.label" iconRight="chevron-down" />
        </template>
      </Dropdown>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="flex h-24 w-full items-start overflow-hidden rounded-lg border border-outline-gray-2 shadow">
        <Tooltip class="w-full" :text="receita.data?.tooltip || ''">
          <NumberChart v-if="receita.data" class="w-full !items-start" :config="receita.data" />
          <div v-else class="flex h-24 w-full items-center justify-center text-p-sm text-ink-gray-4">...</div>
        </Tooltip>
      </div>
      <div class="flex h-24 w-full items-start overflow-hidden rounded-lg border border-outline-gray-2 shadow">
        <Tooltip class="w-full" :text="meta.data?.tooltip || ''">
          <NumberChart v-if="meta.data" class="w-full !items-start" :config="meta.data" />
          <div v-else class="flex h-24 w-full items-center justify-center text-p-sm text-ink-gray-4">...</div>
        </Tooltip>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('A receber (pendente)') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-amber-6">{{ formatCurrency(summary.data?.Pendente) }}</div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Atrasado') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-red-6">{{ formatCurrency(summary.data?.Atrasado) }}</div>
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-1 text-p-base-medium text-ink-gray-8">{{ __('Faturamento do mês') }}</div>
      <div class="mb-4 text-p-sm text-ink-gray-5">{{ __('Honorários pagos, por dia, no período selecionado.') }}</div>
      <div v-if="trend.data" class="h-72 w-full">
        <FixedAxisChart :config="trend.data" />
      </div>
      <div v-else class="flex h-40 items-center justify-center text-p-sm text-ink-gray-4">
        {{ __('Carregando...') }}
      </div>
    </div>

    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="text-p-sm text-ink-gray-6">{{ __('Total geral (todos os honorários cadastrados)') }}</div>
      <div class="mt-1 flex items-center justify-between">
        <div class="text-3xl font-semibold text-ink-gray-9">{{ formatCurrency(summary.data?.total_geral) }}</div>
        <Button variant="outline" :label="__('Ver relatório completo')" @click="$router.push({ name: 'Financeiro Relatorios' })" />
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import FixedAxisChart from '@/components/Dashboard/FixedAxisChart.vue'
import { Button, Dropdown, NumberChart, Tooltip, createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

const periodos = [
  { label: __('Este mês'), onClick: () => selecionarPeriodo(0) },
  { label: __('Mês passado'), onClick: () => selecionarPeriodo(1) },
]
const mesesAtras = ref(0)
const periodoAtual = computed(() => (mesesAtras.value === 0 ? periodos[0] : periodos[1]))

function _limites(offsetMeses) {
  const hoje = new Date()
  const base = new Date(hoje.getFullYear(), hoje.getMonth() - offsetMeses, 1)
  const inicio = new Date(base.getFullYear(), base.getMonth(), 1)
  const fim = new Date(base.getFullYear(), base.getMonth() + 1, 0)
  const fmt = (d) => d.toISOString().slice(0, 10)
  return { from_date: fmt(inicio), to_date: fmt(fim) }
}

const summary = createResource({ url: 'crm.api.financeiro.get_report_summary', auto: true })

const receita = createResource({
  url: 'crm.api.dashboard.get_receita_recebida',
  params: _limites(0),
  auto: true,
})
const meta = createResource({
  url: 'crm.api.dashboard.get_meta_mensal',
  params: _limites(0),
  auto: true,
})
const trend = createResource({
  url: 'crm.api.dashboard.get_receita_trend',
  params: _limites(0),
  auto: true,
})

function selecionarPeriodo(offset) {
  mesesAtras.value = offset
  const params = _limites(offset)
  receita.update({ params })
  meta.update({ params })
  trend.update({ params })
  receita.reload()
  meta.reload()
  trend.reload()
}

function formatCurrency(value) {
  value = value || 0
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}
</script>
