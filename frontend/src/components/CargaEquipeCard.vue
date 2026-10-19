<template>
  <div v-if="carga.data?.length" class="mb-5 rounded-lg border border-outline-gray-2 p-4">
    <div class="text-p-base-medium text-ink-gray-8">{{ __('Carga de trabalho') }}</div>
    <div class="mb-3 text-p-sm text-ink-gray-5">{{ __('Casos ativos sob responsabilidade de cada pessoa, tarefas em aberto e horas lançadas no mês.') }}</div>
    <table class="w-full text-left text-p-sm">
      <thead class="text-ink-gray-5">
        <tr>
          <th class="py-1 pr-2">{{ __('Pessoa') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Casos ativos') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Tarefas abertas') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Atrasadas') }}</th>
          <th class="py-1 pr-2 text-right">{{ __('Horas no mês') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in carga.data" :key="p.usuario" class="border-t border-outline-gray-1">
          <td class="py-1 pr-2">{{ p.nome }}</td>
          <td class="py-1 pr-2 text-right">{{ p.casos_ativos }}</td>
          <td class="py-1 pr-2 text-right">{{ p.tarefas_abertas }}</td>
          <td class="py-1 pr-2 text-right" :class="p.tarefas_atrasadas ? 'font-semibold text-ink-red-4' : ''">{{ p.tarefas_atrasadas }}</td>
          <td class="py-1 pr-2 text-right">{{ p.horas_mes }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const carga = createResource({ url: 'crm.api.seguranca.carga_equipe', auto: true })
</script>
