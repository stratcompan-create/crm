<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex items-start justify-between gap-4 px-2">
      <div class="flex flex-col gap-1">
        <h2 class="text-2xl-semibold leading-none">{{ __('Modelos de área') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('O padrão de cada área: documentos que o cliente traz, perguntas da primeira consulta e o honorário mais usado. O pedido de documentos e o percentual de êxito do caso já saem daqui.') }}
        </p>
      </div>
      <div class="flex shrink-0 gap-2">
        <Button variant="subtle" :label="__('Restaurar padrões')" @click="restaurar" />
        <Button variant="solid" iconLeft="lucide-plus" :label="__('Nova área')" @click="abrir()" />
      </div>
    </div>
    <div class="mx-2 flex flex-col gap-2">
      <div v-for="a in lista.data || []" :key="a.name" class="flex items-start justify-between gap-3 rounded-lg border border-outline-gray-2 px-4 py-3">
        <div class="min-w-0">
          <div class="text-p-base-medium text-ink-gray-9">{{ a.area }}</div>
          <div class="text-xs text-ink-gray-5">
            {{ __(a.tipo_honorario) }}<span v-if="a.percentual_exito"> · {{ __('êxito {0}%', [a.percentual_exito]) }}</span>
            · {{ __('{0} documentos', [(a.documentos || '').split('\n').filter(Boolean).length]) }}
            · {{ __('{0} perguntas', [(a.perguntas || '').split('\n').filter(Boolean).length]) }}
          </div>
        </div>
        <div class="flex shrink-0 gap-1">
          <Button variant="subtle" :label="__('Editar')" @click="abrir(a)" />
          <Button variant="ghost" theme="red" :label="__('Excluir')" @click="excluir(a)" />
        </div>
      </div>
      <div v-if="!lista.data?.length && !lista.loading" class="rounded-lg border border-dashed border-outline-gray-3 p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Nenhuma área ainda. Clique em "Restaurar padrões" para começar com trabalhista, previdenciário, família, consumidor e cível.') }}
      </div>
    </div>

    <Dialog v-model="form.show" :options="{ title: form.name ? __('Editar área') : __('Nova área'), size: '2xl' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <FormControl v-model="form.area" type="text" :label="__('Área')" :disabled="!!form.name" />
            <FormControl v-model="form.tipo_honorario" type="select" :label="__('Honorário mais usado')" :options="tipos" />
            <FormControl v-model="form.percentual_exito" type="number" :label="__('Êxito padrão (%)')" />
          </div>
          <FormControl v-model="form.documentos" type="textarea" :rows="5" :label="__('Documentos que o cliente traz (um por linha)')" />
          <FormControl v-model="form.perguntas" type="textarea" :rows="5" :label="__('Perguntas da primeira consulta (uma por linha)')" />
          <ErrorMessage v-if="erro" :message="erro" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end"><Button variant="solid" :label="__('Salvar')" @click="salvar" /></div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'

const lista = createResource({ url: 'crm.api.inteligencia.listar_areas', auto: true })
const tipos = ['Fixo', 'Êxito', 'Consultivo Mensal', 'Por Ato'].map((t) => ({ label: __(t), value: t }))
const form = reactive({ show: false })
const erro = ref('')

function abrir(a) {
  erro.value = ''
  Object.assign(form, { show: true, name: '', area: '', tipo_honorario: 'Fixo', percentual_exito: 0, documentos: '', perguntas: '' }, a || {})
}
async function salvar() {
  try {
    const { show, ...dados } = form
    await call('crm.api.inteligencia.salvar_area', { dados: JSON.stringify(dados) })
    form.show = false
    toast.success(__('Área salva'))
    lista.reload()
  } catch (e) {
    erro.value = e?.messages?.[0] || __('Não foi possível salvar.')
  }
}
async function excluir(a) {
  if (!window.confirm(__('Excluir o modelo da área {0}?', [a.area]))) return
  await call('crm.api.inteligencia.excluir_area', { name: a.name })
  lista.reload()
}
async function restaurar() {
  await call('crm.api.inteligencia.restaurar_areas_padrao')
  toast.success(__('Áreas padrão restauradas (as que você já tinha não mudaram)'))
  lista.reload()
}
</script>
