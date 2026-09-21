<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex items-start justify-between gap-4 px-2">
      <div class="flex flex-col gap-1">
        <h2 class="text-2xl-semibold leading-none">{{ __('Modelos de documentos') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('Cole aqui o texto do contrato, da procuração e de outros documentos do escritório. Nos dados que mudam de cliente para cliente, use os campos entre chaves. O CRM preenche tudo e gera o PDF com a marca do escritório.') }}
        </p>
      </div>
      <Button variant="solid" iconLeft="lucide-plus" :label="__('Novo modelo')" @click="openNew" />
    </div>

    <div class="mx-2 flex flex-col gap-2">
      <div v-if="!list.data?.length && !list.loading" class="rounded-lg border border-dashed border-outline-gray-3 p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Nenhum modelo ainda.') }}
      </div>
      <div
        v-for="m in list.data || []"
        :key="m.name"
        class="flex items-center justify-between gap-3 rounded-lg border border-outline-gray-2 px-4 py-3"
      >
        <div class="min-w-0">
          <div class="truncate text-p-base-medium text-ink-gray-9">{{ m.name }}</div>
          <div class="text-xs text-ink-gray-5">{{ m.tipo }}</div>
        </div>
        <div class="flex shrink-0 gap-1">
          <Button variant="subtle" :label="__('Editar')" @click="openEdit(m.name)" />
          <Button variant="ghost" theme="red" :label="__('Excluir')" @click="remove(m)" />
        </div>
      </div>
    </div>
    <p class="mx-2 text-xs text-ink-gray-5">
      {{ __('O texto dos modelos é do escritório. O CRM não escreve nem altera cláusulas: só preenche os campos e monta o PDF. Peça a um advogado para revisar cada modelo antes de usar.') }}
    </p>

    <Dialog v-model="show" :options="{ title: editing ? __('Editar modelo') : __('Novo modelo'), size: '4xl' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div class="flex flex-col gap-1 sm:col-span-2">
              <span class="text-p-sm text-ink-gray-6">{{ __('Nome do modelo') }}</span>
              <FormControl v-model="form.nome" type="text" :placeholder="__('Ex.: Contrato de honorários — consultivo')" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-p-sm text-ink-gray-6">{{ __('Tipo') }}</span>
              <FormControl v-model="form.tipo" type="select" :options="tipos" />
            </div>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Título no cabeçalho do PDF (opcional)') }}</span>
            <FormControl v-model="form.titulo" type="text" :placeholder="__('Ex.: Contrato de honorários')" />
          </div>

          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Texto do documento') }}</span>
            <textarea
              ref="bodyBox"
              v-model="form.corpo"
              rows="14"
              class="w-full rounded border border-outline-gray-2 bg-transparent px-3 py-2 font-mono text-p-sm text-ink-gray-9"
              :placeholder="__('Cole o texto aqui. Use # para título, ## para subtítulo, **negrito**, uma linha em branco entre parágrafos e --- para mudar de página.')"
            />
            <p class="text-xs text-ink-gray-5">
              {{ __('Dica: # Título, ## Subtítulo, **negrito**, *itálico*, "- " para lista, linha em branco para novo parágrafo e --- para nova página.') }}
            </p>
          </div>

          <div>
            <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Campos preenchidos automaticamente (clique para inserir onde está o cursor)') }}</div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="v in variables.data || []"
                :key="v.chave"
                type="button"
                :title="v.descricao"
                class="rounded-full border border-outline-gray-2 px-2.5 py-0.5 text-xs text-ink-gray-8 hover:bg-surface-gray-2"
                @click="insert(v.chave)"
              >
                {{ '{' + v.chave + '}' }}
              </button>
            </div>
          </div>
          <ErrorMessage v-if="error" :message="error" />
        </div>
      </template>
      <template #actions>
        <div class="flex w-full items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <FormControl v-model="previewStyle" type="select" :options="styleOptions" class="w-56" />
            <Button variant="subtle" iconLeft="lucide-eye" :label="__('Ver prévia')" :loading="previewing" @click="preview" />
          </div>
          <Button variant="solid" :label="__('Salvar modelo')" :loading="saving" @click="save" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { nextTick, reactive, ref } from 'vue'

const list = createResource({ url: 'crm.api.modelos_documentos.list_models', auto: true })
const variables = createResource({ url: 'crm.api.modelos_documentos.get_variables', auto: true })

const tipos = ['Contrato', 'Procuração', 'Declaração', 'Recibo', 'Outro'].map((t) => ({ label: t, value: t }))
const styleOptions = [
  { label: __('Estilo padrão do escritório'), value: '' },
  { label: __('Cor da marca nos destaques'), value: 'escuro' },
  { label: __('Fundo neutro'), value: 'claro' },
  { label: __('Fundo branco'), value: 'branco' },
  { label: __('Cor da marca em tudo'), value: 'cor' },
]

const show = ref(false)
const editing = ref(false)
const original = ref('')
const form = reactive({ nome: '', tipo: 'Contrato', titulo: '', corpo: '' })
const saving = ref(false)
const previewing = ref(false)
const previewStyle = ref('')
const error = ref('')
const bodyBox = ref(null)

function openNew() {
  Object.assign(form, { nome: '', tipo: 'Contrato', titulo: '', corpo: '' })
  original.value = ''
  editing.value = false
  error.value = ''
  show.value = true
}
async function openEdit(name) {
  const m = await call('crm.api.modelos_documentos.get_model', { nome: name })
  Object.assign(form, { nome: m.nome, tipo: m.tipo, titulo: m.titulo, corpo: m.corpo })
  original.value = m.nome
  editing.value = true
  error.value = ''
  show.value = true
}

function insert(key) {
  const el = bodyBox.value
  const token = `{${key}}`
  if (!el) {
    form.corpo += token
    return
  }
  const start = el.selectionStart ?? form.corpo.length
  const end = el.selectionEnd ?? start
  form.corpo = form.corpo.slice(0, start) + token + form.corpo.slice(end)
  nextTick(() => {
    el.focus()
    el.selectionStart = el.selectionEnd = start + token.length
  })
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const r = await call('crm.api.modelos_documentos.save_model', { ...form, original: original.value })
    if (r.campos_desconhecidos?.length) {
      toast.warning(__('Atenção: estes campos não existem e vão impedir a geração: {0}', [r.campos_desconhecidos.map((k) => `{${k}}`).join(', ')]))
    } else {
      toast.success(__('Modelo salvo'))
    }
    show.value = false
    list.reload()
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível salvar o modelo.')
  } finally {
    saving.value = false
  }
}

async function preview() {
  previewing.value = true
  error.value = ''
  try {
    const r = await call('crm.api.modelos_documentos.preview_model', {
      corpo: form.corpo,
      tipo: form.tipo,
      titulo: form.titulo || form.nome,
      estilo: previewStyle.value,
    })
    const bytes = Uint8Array.from(atob(r.pdf), (c) => c.charCodeAt(0))
    window.open(URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' })), '_blank')
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível gerar a prévia.')
  } finally {
    previewing.value = false
  }
}

async function remove(m) {
  if (!window.confirm(__('Excluir o modelo "{0}"?', [m.name]))) return
  await call('crm.api.modelos_documentos.delete_model', { nome: m.name })
  list.reload()
}
</script>
