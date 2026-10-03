<template>
  <div class="flex h-full flex-col overflow-y-auto pb-10 pt-4">
    <div v-if="!horas.data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <div v-else class="mx-auto flex w-full max-w-4xl flex-col gap-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-lg-semibold text-ink-gray-9">{{ __('Horas') }}</div>
          <div class="mt-0.5 text-p-sm text-ink-gray-6">
            {{ __('{0}h este mês · {1}h no total', [formatHoras(horas.data.total_mes), formatHoras(horas.data.total_geral)]) }}
          </div>
        </div>
      </div>

      <!-- Lançar nova hora -->
      <div class="grid grid-cols-1 gap-3 rounded-lg border border-outline-gray-2 p-3 sm:grid-cols-5">
        <FormControl type="date" v-model="novo.data" :label="__('Data')" />
        <FormControl type="select" v-model="novo.frente" :label="__('Frente')" :options="frentes" />
        <FormControl type="number" v-model="novo.horas" :label="__('Horas')" step="0.25" min="0" />
        <FormControl class="sm:col-span-2" type="text" v-model="novo.observacoes" :label="__('Observação (opcional)')" :placeholder="__('O que foi feito')" />
        <Button class="sm:col-start-5" variant="solid" :label="__('Lançar')" :loading="lancando" @click="lancar" />
      </div>

      <!-- Lançamentos -->
      <table v-if="horas.data.lancamentos.length" class="w-full text-sm">
        <thead>
          <tr class="text-left text-ink-gray-5">
            <th class="w-28 pb-2 font-normal">{{ __('Data') }}</th>
            <th class="pb-2 font-normal">{{ __('Quem') }}</th>
            <th class="w-24 pb-2 font-normal">{{ __('Frente') }}</th>
            <th class="w-20 pb-2 text-right font-normal">{{ __('Horas') }}</th>
            <th class="pb-2 font-normal">{{ __('Observação') }}</th>
            <th class="w-8"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in horas.data.lancamentos" :key="item.name" class="border-t border-outline-gray-2">
            <td class="py-2 pr-2 text-ink-gray-7">{{ formatData(item.data) }}</td>
            <td class="py-2 pr-2 text-ink-gray-7">{{ item.usuario }}</td>
            <td class="py-2 pr-2 text-ink-gray-7">{{ item.frente }}</td>
            <td class="py-2 pr-2 text-right font-medium text-ink-gray-9">{{ formatHoras(item.horas) }}</td>
            <td class="py-2 pr-2 text-ink-gray-6">{{ item.observacoes }}</td>
            <td class="py-2">
              <Button v-if="item.pode_excluir" variant="ghost" icon="lucide-trash-2" @click="excluir(item.name)" />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="py-10 text-center text-p-sm text-ink-gray-5">
        {{ __('Nenhuma hora lançada ainda neste negócio.') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const props = defineProps({ doctype: String, docname: String })

const frentes = ['Vídeo', 'CRM', 'Site', 'Tráfego', 'Reunião', 'Outro'].map((f) => ({ label: f, value: f }))

const horas = createResource({
  url: 'crm.api.horas.listar_horas',
  makeParams: () => ({ deal: props.docname }),
  auto: props.doctype === 'CRM Deal',
})
watch(() => props.docname, () => {
  if (props.doctype === 'CRM Deal') horas.reload()
})

function hoje() {
  return new Date().toISOString().slice(0, 10)
}

const novo = reactive({ data: hoje(), frente: 'Outro', horas: '', observacoes: '' })
const lancando = ref(false)

async function lancar() {
  const valor = Number(novo.horas)
  if (!valor || valor <= 0) {
    toast.error(__('Informe quantas horas foram trabalhadas.'))
    return
  }
  lancando.value = true
  try {
    await call('crm.api.horas.registrar_hora', {
      deal: props.docname,
      horas: valor,
      frente: novo.frente,
      data: novo.data,
      observacoes: novo.observacoes,
    })
    novo.horas = ''
    novo.observacoes = ''
    await horas.reload()
    toast.success(__('Hora lançada'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não consegui lançar a hora.'))
  } finally {
    lancando.value = false
  }
}

async function excluir(name) {
  try {
    await call('crm.api.horas.excluir_hora', { name })
    await horas.reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não consegui excluir o lançamento.'))
  }
}

function formatHoras(value) {
  return (Number(value) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 })
}

function formatData(value) {
  if (!value) return ''
  const [ano, mes, dia] = String(value).slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}
</script>
