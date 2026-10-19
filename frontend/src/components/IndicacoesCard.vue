<template>
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
    <div class="rounded-lg border border-outline-gray-2 p-5 lg:col-span-2">
      <div class="text-p-base-medium text-ink-gray-8">{{ __('Quem mais indica') }}</div>
      <div class="mb-3 text-p-sm text-ink-gray-5">{{ __('Últimos 12 meses, pelo campo "Indicado por" dos atendimentos e casos.') }}</div>
      <div v-if="!ranking.data?.length" class="text-p-sm text-ink-gray-5">
        {{ __('Ainda não há indicações registradas. Preencha "Indicado por" nos novos atendimentos.') }}
      </div>
      <table v-else class="w-full text-left text-p-sm">
        <thead class="text-ink-gray-5">
          <tr>
            <th class="py-1 pr-2">{{ __('Quem indicou') }}</th>
            <th class="py-1 pr-2 text-right">{{ __('Indicações') }}</th>
            <th class="py-1 pr-2 text-right">{{ __('Fechadas') }}</th>
            <th class="py-1 pr-2 text-right">{{ __('Honorários recebidos') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in ranking.data" :key="r.nome" class="border-t border-outline-gray-1">
            <td class="py-1 pr-2">{{ r.nome }}</td>
            <td class="py-1 pr-2 text-right">{{ r.atendimentos + r.casos }}</td>
            <td class="py-1 pr-2 text-right">{{ r.fechados }}</td>
            <td class="py-1 pr-2 text-right">{{ brl(r.honorarios) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="juridico" class="rounded-lg border border-outline-gray-2 p-5">
      <div class="text-p-base-medium text-ink-gray-8">{{ __('Satisfação dos clientes') }}</div>
      <div class="mb-3 text-p-sm text-ink-gray-5">{{ __('Pesquisa enviada ao encerrar cada caso.') }}</div>
      <div v-if="!nps.data?.respostas" class="text-p-sm text-ink-gray-5">{{ __('Ainda sem respostas.') }}</div>
      <template v-else>
        <div class="text-3xl font-semibold text-ink-gray-9">{{ nps.data.media }}<span class="text-p-base text-ink-gray-5">/10</span></div>
        <div class="text-p-sm text-ink-gray-6">{{ __('NPS {0} · {1} de {2} responderam', [nps.data.nps, nps.data.respostas, nps.data.enviadas]) }}</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const juridico = ['escritorio', 'escritorio_empresarial'].includes(window.crm_profile)
const brl = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const ranking = createResource({ url: 'crm.api.portal.ranking_indicacoes', auto: true })
const nps = createResource({ url: 'crm.api.portal.resumo_pesquisas', auto: juridico })
</script>
