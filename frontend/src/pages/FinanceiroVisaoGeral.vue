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
        <NumberChart v-if="receita.data" class="w-full !items-start" :config="receita.data" />
        <div v-else class="flex h-24 w-full items-center justify-center text-p-sm text-ink-gray-4">...</div>
      </div>
      <div class="flex h-24 w-full items-start overflow-hidden rounded-lg border border-outline-gray-2 shadow">
        <NumberChart v-if="meta.data" class="w-full !items-start" :config="meta.data" />
        <div v-else class="flex h-24 w-full items-center justify-center text-p-sm text-ink-gray-4">...</div>
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

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-1 text-p-base-medium text-ink-gray-8">{{ __('Faturamento por serviço') }}</div>
        <div class="mb-4 text-p-sm text-ink-gray-5">{{ __('Total acumulado (pago + a receber), todos os períodos.') }}</div>
        <div v-if="breakdown.data?.servicos?.length" class="flex flex-col gap-3">
          <div v-for="s in breakdown.data.servicos" :key="s.servico" class="flex flex-col gap-1">
            <div class="flex items-center justify-between text-p-sm">
              <span class="text-ink-gray-7">{{ s.servico }}</span>
              <span class="font-medium text-ink-gray-9">{{ formatCurrency(s.pago + s.pendente) }}</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-surface-gray-2">
              <div class="h-2 rounded-full bg-blue-500" :style="{ width: barWidth(s) }" />
            </div>
          </div>
        </div>
        <div v-else class="flex h-20 items-center justify-center text-p-sm text-ink-gray-4">
          {{ __('Sem honorários cadastrados ainda.') }}
        </div>
      </div>

      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="mb-1 flex items-center justify-between">
          <div class="text-p-base-medium text-ink-gray-8">{{ __('Próximas mensalidades a vencer') }}</div>
          <Button variant="ghost" size="sm" :label="__('Ver tudo')" @click="$router.push({ name: 'Financeiro Recorrencia' })" />
        </div>
        <div class="mb-4 text-p-sm text-ink-gray-5">{{ __('Mensalidades atrasadas ou vencendo nos próximos 30 dias.') }}</div>
        <div v-if="mrr.data?.atrasadas?.length || mrr.data?.proximas?.length" class="flex flex-col divide-y divide-outline-gray-1">
          <div v-for="item in mrr.data.atrasadas" :key="'a-' + item.name" class="flex items-center justify-between py-2 text-p-sm">
            <span class="text-ink-gray-8">{{ item.cliente }}</span>
            <span class="font-medium text-ink-red-6">{{ formatCurrency(item.valor) }} · {{ __('{0} dias atrasado', [item.dias]) }}</span>
          </div>
          <div v-for="item in mrr.data.proximas" :key="'p-' + item.name" class="flex items-center justify-between py-2 text-p-sm">
            <span class="text-ink-gray-8">{{ item.cliente }}</span>
            <span class="font-medium text-ink-gray-7">{{ formatCurrency(item.valor) }} · {{ __('vence em {0} dias', [item.dias]) }}</span>
          </div>
        </div>
        <div v-else class="flex h-20 items-center justify-center text-p-sm text-ink-gray-4">
          {{ __('Nenhuma mensalidade atrasada ou vencendo em breve.') }}
        </div>
      </div>
    </div>

    <div v-if="isAgency" class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-1 text-p-base-medium text-ink-gray-8">{{ __('Rentabilidade por cliente') }}</div>
      <div class="mb-4 text-p-sm text-ink-gray-5">
        {{ __('Mensalidade ÷ horas lançadas no mês (aba Horas, dentro do negócio). Os piores R$/hora primeiro.') }}
      </div>
      <div v-if="rentabilidade.data?.piores?.length" class="flex flex-col divide-y divide-outline-gray-1">
        <div v-for="item in rentabilidade.data.piores" :key="item.deal" class="flex items-center justify-between py-2 text-p-sm">
          <span class="text-ink-gray-8">{{ item.cliente }}</span>
          <span class="font-medium text-ink-gray-7">
            {{ formatCurrency(item.efetivo) }}/h · {{ formatHoras(item.horas) }}h no mês
          </span>
        </div>
      </div>
      <div v-else class="flex h-16 items-center justify-center text-p-sm text-ink-gray-4">
        {{ __('Nenhuma hora lançada neste mês ainda.') }}
      </div>
      <div v-if="rentabilidade.data?.sem_registro?.length" class="mt-3 border-t border-outline-gray-1 pt-3 text-p-sm text-ink-gray-5">
        {{ __('Sem hora lançada este mês:') }}
        <span class="text-ink-gray-7">{{ rentabilidade.data.sem_registro.map((s) => s.cliente).join(', ') }}</span>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import FixedAxisChart from '@/components/Dashboard/FixedAxisChart.vue'
import { Button, Dropdown, NumberChart, createResource } from 'frappe-ui'
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

const breakdown = createResource({ url: 'crm.api.financeiro.get_revenue_breakdown', auto: true })
const mrr = createResource({ url: 'crm.api.financeiro.get_mrr', auto: true })

const isAgency = computed(() => (window.crm_profile || 'agencia') === 'agencia')
const rentabilidade = createResource({
  url: 'crm.api.horas.rentabilidade_clientes',
  auto: isAgency.value,
})

function barWidth(servico) {
  const valores = breakdown.data?.servicos?.map((s) => s.pago + s.pendente) || [0]
  const max = Math.max(...valores, 1)
  const pct = Math.round(((servico.pago + servico.pendente) / max) * 100)
  return Math.max(4, pct) + '%'
}

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

function formatHoras(value) {
  return (Number(value) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 })
}
</script>
