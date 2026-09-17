<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Estimador de Projeto') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <p class="max-w-2xl text-p-base text-ink-gray-6">
      {{ __('Estime o custo e o preço de um novo projeto ou caso antes de aceitá-lo, com base nas horas de trabalho previstas, despesas e na margem de lucro desejada.') }}
    </p>

    <div class="flex flex-wrap gap-8">
      <div class="flex w-full max-w-md flex-col gap-5">
        <div class="flex flex-col gap-1.5">
          <label class="text-p-base-medium text-ink-gray-7">
            {{ __('Nome do Projeto/Caso') }}
          </label>
          <FormControl
            type="text"
            size="md"
            v-model="projectName"
            :placeholder="__('Opcional, apenas para referência')"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-base-medium text-ink-gray-7">
            {{ __('Horas Estimadas de Trabalho') }}
          </label>
          <FormControl type="number" size="md" v-model="hours" placeholder="0" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-base-medium text-ink-gray-7">
            {{ __('Custo por Hora (Interno)') }}
          </label>
          <FormControl
            type="number"
            size="md"
            v-model="hourlyCost"
            :placeholder="__('0,00')"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-base-medium text-ink-gray-7">
            {{ __('Despesas Adicionais Previstas') }}
          </label>
          <FormControl
            type="number"
            size="md"
            v-model="extraExpenses"
            :placeholder="__('0,00')"
          />
          <span class="text-p-sm text-ink-gray-5">
            {{ __('Custas, terceiros, deslocamento, ferramentas etc.') }}
          </span>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-base-medium text-ink-gray-7">
            {{ __('Margem de Lucro Desejada (%)') }}
          </label>
          <FormControl type="number" size="md" v-model="margin" placeholder="0" />
        </div>
      </div>

      <div class="flex w-full max-w-sm flex-col gap-4 rounded-xl border border-outline-gray-2 bg-surface-white p-6">
        <div class="text-p-base-medium text-ink-gray-7">
          {{ __('Resultado') }}
          <span v-if="projectName" class="text-ink-gray-5">— {{ projectName }}</span>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-p-base text-ink-gray-6">{{ __('Custo Total Estimado') }}</span>
          <span class="text-lg font-semibold text-ink-gray-9">{{ formatCurrency(totalCost) }}</span>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-p-base text-ink-gray-6">{{ __('Preço Sugerido') }}</span>
          <span class="text-lg font-semibold text-ink-green-6">{{ formatCurrency(suggestedPrice) }}</span>
        </div>

        <div class="flex items-center justify-between border-t border-outline-gray-2 pt-4">
          <span class="text-p-base text-ink-gray-6">{{ __('Lucro Estimado') }}</span>
          <span class="text-p-base-medium text-ink-gray-8">{{ formatCurrency(estimatedProfit) }}</span>
        </div>

        <div v-if="marginTooHigh" class="rounded-md bg-surface-red-2 px-3 py-2 text-p-sm text-ink-red-6">
          {{ __('Margem de 100% ou mais não permite calcular um preço sugerido. Reduza a margem.') }}
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { FormControl } from 'frappe-ui'
import { ref, computed } from 'vue'

const projectName = ref('')
const hours = ref(0)
const hourlyCost = ref(0)
const extraExpenses = ref(0)
const margin = ref(20)

function toNum(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const totalCost = computed(() => toNum(hours.value) * toNum(hourlyCost.value) + toNum(extraExpenses.value))

const marginTooHigh = computed(() => toNum(margin.value) >= 100)

const suggestedPrice = computed(() => {
  if (marginTooHigh.value) return totalCost.value
  const factor = 1 - toNum(margin.value) / 100
  return factor > 0 ? totalCost.value / factor : totalCost.value
})

const estimatedProfit = computed(() => suggestedPrice.value - totalCost.value)

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value || 0)
}
</script>
