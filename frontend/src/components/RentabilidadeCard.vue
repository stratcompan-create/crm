<template>
  <div class="rounded-lg border border-outline-gray-2 p-5">
    <div class="text-p-base-medium text-ink-gray-8">{{ __('Rentabilidade') }}</div>
    <div class="mb-3 text-p-sm text-ink-gray-5">
      {{ __('Últimos 12 meses: honorários recebidos menos as custas que ficaram com o escritório, e quanto isso dá por hora trabalhada (horas lançadas nos casos).') }}
    </div>
    <div class="mb-2 flex gap-2">
      <Button size="sm" :variant="aba === 'areas' ? 'solid' : 'subtle'" :label="__('Por área')" @click="aba = 'areas'" />
      <Button size="sm" :variant="aba === 'clientes' ? 'solid' : 'subtle'" :label="__('Por cliente')" @click="aba = 'clientes'" />
    </div>
    <div v-if="!linhas.length" class="text-p-sm text-ink-gray-5">{{ __('Ainda não há honorários recebidos no período.') }}</div>
    <table v-else class="w-full text-left text-p-sm">
      <thead class="text-ink-gray-5">
        <tr>
          <th class="py-1 pr-2">{{ aba === 'areas' ? __('Área') : __('Cliente') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Recebido') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Custas') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Líquido') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('A receber') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Horas') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Por hora') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in linhas" :key="l.nome" class="border-t border-outline-gray-1">
          <td class="py-1 pr-2">{{ l.nome }} <span class="text-xs text-ink-gray-5">({{ l.casos }})</span></td>
          <td class="py-1 pr-2 text-right">{{ brl(l.recebido) }}</td>
          <td class="py-1 pr-2 text-right">{{ brl(l.custas) }}</td>
          <td class="py-1 pr-2 text-right font-medium">{{ brl(l.liquido) }}</td>
          <td class="py-1 pr-2 text-right">{{ brl(l.a_receber) }}</td>
          <td class="py-1 pr-2 text-right">{{ l.horas || '—' }}</td>
          <td class="py-1 pr-2 text-right">{{ l.por_hora ? brl(l.por_hora) : '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { Button, createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

const aba = ref('areas')
const brl = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const dados = createResource({ url: 'crm.api.inteligencia.rentabilidade', auto: true })
const linhas = computed(() => dados.data?.[aba.value] || [])
</script>
