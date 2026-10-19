<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex items-start justify-between gap-4 px-2">
      <div class="flex flex-col gap-1">
        <h2 class="text-2xl-semibold leading-none">{{ __('Tabela de honorários') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('Cadastre a tabela da sua seccional da OAB e quanto o escritório pratica. Na hora de montar a proposta, é só buscar o serviço.') }}
        </p>
      </div>
      <Button variant="solid" iconLeft="lucide-plus" :label="__('Novo serviço')" @click="abrir()" />
    </div>
    <div class="mx-2"><FormControl v-model="busca" type="text" :placeholder="__('Buscar serviço ou área...')" /></div>
    <div class="mx-2 overflow-x-auto rounded-lg border border-outline-gray-2">
      <table class="w-full text-left text-p-sm">
        <thead class="bg-surface-gray-2 text-ink-gray-6">
          <tr>
            <th class="px-3 py-2">{{ __('Serviço') }}</th>
            <th class="px-3 py-2">{{ __('Área') }}</th>
            <th class="px-3 py-2 text-right">{{ __('Mínimo da tabela OAB') }}</th>
            <th class="px-3 py-2 text-right">{{ __('Valor do escritório') }}</th>
            <th class="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in itens.data || []" :key="i.name" class="border-t border-outline-gray-1">
            <td class="px-3 py-2">{{ i.descricao }}<div v-if="i.observacoes" class="text-xs text-ink-gray-5">{{ i.observacoes }}</div></td>
            <td class="px-3 py-2">{{ i.area }}</td>
            <td class="px-3 py-2 text-right">{{ i.percentual ? i.percentual + '%' : brl(i.valor_tabela) }}</td>
            <td class="px-3 py-2 text-right font-medium" :class="abaixo(i) ? 'text-ink-red-4' : ''">
              {{ brl(i.valor_escritorio) }}<div v-if="abaixo(i)" class="text-xs">{{ __('abaixo da tabela') }}</div>
            </td>
            <td class="px-3 py-2 text-right">
              <Button size="sm" variant="ghost" icon="edit-2" @click="abrir(i)" />
              <Button size="sm" variant="ghost" theme="red" icon="trash-2" @click="excluir(i)" />
            </td>
          </tr>
          <tr v-if="!itens.data?.length">
            <td colspan="5" class="px-3 py-6 text-center text-ink-gray-5">{{ __('Nenhum serviço cadastrado.') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="mx-2 text-xs text-ink-gray-5">{{ __('A tabela muda todo ano: confira a versão vigente da sua seccional.') }}</p>

    <Dialog v-model="form.show" :options="{ title: form.name ? __('Editar serviço') : __('Novo serviço'), size: 'lg' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <FormControl v-model="form.descricao" type="text" :label="__('Serviço')" :placeholder="__('Ex.: Reclamação trabalhista (rito ordinário)')" />
          <FormControl v-model="form.area" type="text" :label="__('Área')" />
          <div class="grid grid-cols-3 gap-3">
            <FormControl v-model="form.valor_tabela" type="number" :label="__('Mínimo OAB (R$)')" />
            <FormControl v-model="form.percentual" type="number" :label="__('Ou % do proveito')" />
            <FormControl v-model="form.valor_escritorio" type="number" :label="__('Valor do escritório (R$)')" />
          </div>
          <FormControl v-model="form.observacoes" type="textarea" :rows="2" :label="__('Observações')" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end"><Button variant="solid" :label="__('Salvar')" @click="salvar" /></div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const busca = ref('')
const itens = createResource({ url: 'crm.api.inteligencia.tabela_honorarios', makeParams: () => ({ q: busca.value }), auto: true })
let t = null
watch(busca, () => {
  clearTimeout(t)
  t = setTimeout(() => itens.reload(), 300)
})
const brl = (v) => (v ? Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—')
const abaixo = (i) => i.valor_tabela && i.valor_escritorio && Number(i.valor_escritorio) < Number(i.valor_tabela)

const form = reactive({ show: false })
function abrir(i) {
  Object.assign(form, { show: true, name: '', descricao: '', area: '', valor_tabela: '', valor_escritorio: '', percentual: '', observacoes: '' }, i || {})
}
async function salvar() {
  try {
    const { show, ...dados } = form
    await call('crm.api.inteligencia.salvar_item_tabela', { dados: JSON.stringify(dados) })
    form.show = false
    itens.reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível salvar.'))
  }
}
async function excluir(i) {
  if (!window.confirm(__('Excluir {0}?', [i.descricao]))) return
  await call('crm.api.inteligencia.excluir_item_tabela', { name: i.name })
  itens.reload()
}
</script>
