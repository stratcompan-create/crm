<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Saúde Financeira') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <!-- Veredito -->
    <div
      class="flex items-center gap-3 rounded-lg border p-5"
      :class="verdict.class"
    >
      <component :is="verdict.icon" class="size-6 shrink-0" />
      <div>
        <div class="text-base font-semibold">{{ verdict.title }}</div>
        <div class="text-p-sm opacity-80">{{ verdict.description }}</div>
      </div>
    </div>

    <!-- Receita real x perdida -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Receita Real (honorários pagos)') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-green-6">
          {{ formatCurrency(health.data?.received) }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Receita Perdida (negócios perdidos)') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-red-6">
          {{ formatCurrency(health.data?.lost_value) }}
        </div>
      </div>
    </div>

    <!-- Progresso da meta trimestral -->
    <div class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-2 flex items-center justify-between">
        <div class="text-p-sm text-ink-gray-6">{{ __('Progresso da Meta Trimestral') }}</div>
        <div class="text-p-sm text-ink-gray-6">
          {{ formatCurrency(health.data?.received) }} / {{ formatCurrency(health.data?.meta_trimestral) }}
        </div>
      </div>
      <div class="h-2.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
        <div
          class="h-full rounded-full bg-blue-6 transition-all duration-700 ease-out"
          :style="{ width: goalProgress + '%' }"
        />
      </div>
      <div class="mt-1 text-right text-p-sm text-ink-gray-5">{{ goalProgress }}%</div>
    </div>

    <!-- Despesas -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Despesas pagas no mês') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">
          {{ formatCurrency(health.data?.expenses_month) }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Despesas a pagar') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">
          {{ formatCurrency(health.data?.expenses_pending) }}
        </div>
      </div>
    </div>

    <!-- Teto de despesa mensal -->
    <div v-if="health.data?.teto_despesa" class="rounded-lg border border-outline-gray-2 p-5">
      <div class="mb-2 flex items-center justify-between">
        <div class="text-p-sm text-ink-gray-6">{{ __('Uso do Teto de Despesa Mensal') }}</div>
        <div class="text-p-sm text-ink-gray-6">
          {{ formatCurrency(health.data?.expenses_month) }} / {{ formatCurrency(health.data?.teto_despesa) }}
        </div>
      </div>
      <div class="h-2.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
        <div
          class="h-full rounded-full transition-all duration-700 ease-out"
          :class="overTeto ? 'bg-red-6' : 'bg-blue-6'"
          :style="{ width: tetoProgress + '%' }"
        />
      </div>
      <div class="mt-1 text-right text-p-sm" :class="overTeto ? 'text-ink-red-6' : 'text-ink-gray-5'">
        {{ tetoPercent }}%
      </div>
    </div>

    <!-- Negocios ganhos x perdidos -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Negócios Ganhos') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">
          {{ health.data?.won_count || 0 }}
        </div>
      </div>
      <div class="rounded-lg border border-outline-gray-2 p-5">
        <div class="text-p-sm text-ink-gray-6">{{ __('Negócios Perdidos') }}</div>
        <div class="mt-1 text-2xl font-semibold text-ink-gray-9">
          {{ health.data?.lost_count || 0 }}
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { createResource } from 'frappe-ui'
import { computed } from 'vue'
import CheckIcon from '~icons/lucide/circle-check'
import AlertIcon from '~icons/lucide/triangle-alert'
import XIcon from '~icons/lucide/circle-x'

const health = createResource({
  url: 'crm.api.financeiro.get_financial_health',
  auto: true,
})

function formatCurrency(value) {
  value = value || 0
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

const goalProgress = computed(() => {
  const meta = health.data?.meta_trimestral || 0
  const received = health.data?.received || 0
  if (!meta) return 0
  return Math.min(100, Math.round((received / meta) * 100))
})

const tetoPercent = computed(() => {
  const teto = health.data?.teto_despesa || 0
  if (!teto) return 0
  return Math.round(((health.data?.expenses_month || 0) / teto) * 100)
})
const tetoProgress = computed(() => Math.min(100, tetoPercent.value))
const overTeto = computed(() => tetoPercent.value > 100)

// Simple health read: comparing what actually came in against what was lost
// along the way — not a precise accounting statement, just a quick signal.
const verdict = computed(() => {
  const received = health.data?.received || 0
  const lost = health.data?.lost_value || 0

  if (!received && !lost) {
    return {
      title: __('Sem dados suficientes ainda'),
      description: __('Cadastre Honorários e Negócios pra a calculadora ter o que analisar.'),
      class: 'border-outline-gray-2 bg-surface-gray-1 text-ink-gray-7',
      icon: AlertIcon,
    }
  }
  if (overTeto.value) {
    return {
      title: __('Atenção'),
      description: __('As despesas pagas neste mês passaram do teto de despesa mensal definido nas Metas.'),
      class: 'border-outline-gray-2 bg-surface-red-2 text-ink-red-6',
      icon: XIcon,
    }
  }
  if (received >= lost) {
    return {
      title: __('Saudável'),
      description: __('A receita realizada está cobrindo (ou superando) o que foi perdido em negócios não fechados.'),
      class: 'border-outline-gray-2 bg-surface-green-2 text-ink-green-6',
      icon: CheckIcon,
    }
  }
  return {
    title: __('Atenção'),
    description: __('O valor perdido em negócios não fechados está maior que a receita realizada.'),
    class: 'border-outline-gray-2 bg-surface-red-2 text-ink-red-6',
    icon: XIcon,
  }
})
</script>
