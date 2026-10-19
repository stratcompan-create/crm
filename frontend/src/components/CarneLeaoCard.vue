<template>
  <div class="rounded-lg border border-outline-gray-2 p-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <div class="text-p-base-medium text-ink-gray-8">{{ __('Carnê-leão do mês') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Honorários recebidos de pessoa física no mês, prontos para lançar no carnê-leão. Confira com o seu contador.') }}
        </div>
      </div>
      <div class="flex items-end gap-2">
        <FormControl v-model="mes" type="month" class="w-40" />
        <Button variant="subtle" iconLeft="lucide-download" :label="__('Baixar planilha')" :loading="baixando" @click="baixar" />
      </div>
    </div>
    <div v-if="dados.data" class="mt-4 flex flex-col gap-2">
      <div class="flex flex-wrap gap-2 text-p-sm">
        <span class="rounded bg-surface-gray-2 px-2 py-1">{{ __('Pessoa física') }}: <b>{{ brl(dados.data.total_pf) }}</b></span>
        <span class="rounded bg-surface-gray-2 px-2 py-1">{{ __('Pessoa jurídica (fora do carnê-leão)') }}: <b>{{ brl(dados.data.total_pj) }}</b></span>
        <span v-if="dados.data.sem_cpf" class="rounded bg-surface-amber-2 px-2 py-1 text-ink-amber-3">
          {{ __('{0} recebimento(s) sem CPF do cliente: preencha nos dados do cliente', [dados.data.sem_cpf]) }}
        </span>
      </div>
      <table v-if="dados.data.linhas.length" class="w-full text-left text-p-sm">
        <thead class="text-ink-gray-5">
          <tr>
            <th class="py-1 pr-2">{{ __('Data') }}</th>
            <th class="py-1 pr-2">{{ __('Cliente') }}</th>
            <th class="py-1 pr-2">{{ __('CPF') }}</th>
            <th class="py-1 pr-2 text-right">{{ __('Valor') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(l, i) in dados.data.linhas" :key="i" class="border-t border-outline-gray-1">
            <td class="py-1 pr-2">{{ l.data.split('-').reverse().join('/') }}</td>
            <td class="py-1 pr-2">{{ l.cliente }}</td>
            <td class="py-1 pr-2">{{ l.cpf || '—' }}</td>
            <td class="py-1 pr-2 text-right">{{ brl(l.valor) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-p-sm text-ink-gray-5">{{ __('Nenhum honorário de pessoa física recebido neste mês.') }}</div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { ref, watch } from 'vue'

const mes = ref(new Date().toISOString().slice(0, 7))
const brl = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const dados = createResource({ url: 'crm.api.prestacao_contas.carne_leao', makeParams: () => ({ mes: mes.value }), auto: true })
watch(mes, () => dados.reload())

const baixando = ref(false)
async function baixar() {
  baixando.value = true
  try {
    const r = await call('crm.api.prestacao_contas.carne_leao_planilha', { mes: mes.value })
    const bytes = Uint8Array.from(atob(r.arquivo), (c) => c.charCodeAt(0))
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
    a.download = r.nome
    a.click()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível gerar a planilha.'))
  } finally {
    baixando.value = false
  }
}
</script>
