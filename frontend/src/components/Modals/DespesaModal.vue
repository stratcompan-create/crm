<template>
  <Dialog v-model="show" :options="{ title: name ? __('Editar despesa') : __('Nova despesa'), size: 'lg' }">
    <template #body-content>
      <div v-if="loading" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <div v-else class="flex flex-col gap-4">
        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('O que foi pago') }}</label>
          <FormControl v-model="form.descricao" type="text" :placeholder="__('Ex.: Adobe Creative Cloud')" />
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Tipo de despesa') }}</label>
            <FormControl v-model="form.categoria" type="select" :options="categorias" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Valor (R$)') }}</label>
            <FormControl v-model="form.valor" type="number" placeholder="0,00" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Vencimento') }}</label>
            <FormControl v-model="form.data_vencimento" type="date" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Situação') }}</label>
            <FormControl
              v-model="form.status"
              type="select"
              :options="[
                { label: __('Pendente'), value: 'Pendente' },
                { label: __('Pago'), value: 'Pago' },
                { label: __('Atrasado'), value: 'Atrasado' },
              ]"
            />
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Pago a (opcional)') }}</label>
          <FormControl v-model="form.fornecedor" type="text" :placeholder="__('Fornecedor ou pessoa')" />
        </div>

        <label class="flex items-start gap-2 text-p-sm text-ink-gray-7">
          <input v-model="form.recorrente" type="checkbox" class="mt-0.5" />
          <span>
            {{ __('Repete todo mês') }}
            <span class="block text-ink-gray-5">
              {{ __('Quando esta despesa for marcada como paga, a do mês seguinte é criada sozinha.') }}
            </span>
          </span>
        </label>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Observações (opcional)') }}</label>
          <FormControl v-model="form.observacoes" type="textarea" :rows="2" />
        </div>

        <ErrorMessage v-if="error" :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex w-full items-center justify-between">
        <Button v-if="name" variant="ghost" theme="red" :label="__('Excluir')" @click="remove" />
        <span v-else />
        <Button variant="solid" :label="name ? __('Salvar') : __('Criar despesa')" :loading="saving" @click="save" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const props = defineProps({ name: { type: String, default: '' } })
const emit = defineEmits(['saved'])
const show = defineModel({ type: Boolean })

const categorias = [
  { label: __('Ferramentas e Software'), value: 'Ferramentas e Software' },
  { label: __('Edição e Filmagem'), value: 'Edição e Filmagem' },
  { label: __('Freelancers'), value: 'Freelancers' },
  { label: __('Tráfego Pago'), value: 'Tráfego Pago' },
  { label: __('Equipamentos'), value: 'Equipamentos' },
  { label: __('Impostos e Taxas'), value: 'Impostos e Taxas' },
  { label: __('Custas e Taxas'), value: 'Custas e Taxas' },
  { label: __('Contas Fixas'), value: 'Contas Fixas' },
  { label: __('Outros'), value: 'Outros' },
]

const today = () => new Date().toISOString().slice(0, 10)
const blank = () => ({
  descricao: '',
  categoria: 'Ferramentas e Software',
  valor: '',
  data_vencimento: today(),
  status: 'Pendente',
  fornecedor: '',
  recorrente: false,
  observacoes: '',
})

const form = reactive(blank())
const loading = ref(false)
const saving = ref(false)
const error = ref('')

watch(show, async (open) => {
  if (!open) return
  error.value = ''
  Object.assign(form, blank())
  if (!props.name) return
  loading.value = true
  try {
    const doc = await call('frappe.client.get', { doctype: 'CRM Despesa', name: props.name })
    Object.keys(blank()).forEach((k) => (form[k] = doc[k] ?? form[k]))
    form.recorrente = !!doc.recorrente
  } finally {
    loading.value = false
  }
})

function validate() {
  if (!form.descricao.trim()) return __('Diga o que foi pago.')
  if (!(Number(form.valor) > 0)) return __('Informe o valor da despesa.')
  if (!form.data_vencimento) return __('Informe o vencimento.')
  return ''
}

async function save() {
  error.value = validate()
  if (error.value) return
  saving.value = true
  const values = { ...form, valor: Number(form.valor), recorrente: form.recorrente ? 1 : 0 }
  try {
    if (props.name) {
      await call('frappe.client.set_value', { doctype: 'CRM Despesa', name: props.name, fieldname: values })
    } else {
      await call('frappe.client.insert', { doc: { doctype: 'CRM Despesa', ...values } })
    }
    toast.success(props.name ? __('Despesa atualizada') : __('Despesa criada'))
    show.value = false
    emit('saved')
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível salvar a despesa.')
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!window.confirm(__('Excluir esta despesa?'))) return
  try {
    await call('frappe.client.delete', { doctype: 'CRM Despesa', name: props.name })
    toast.success(__('Despesa excluída'))
    show.value = false
    emit('saved')
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível excluir.')
  }
}
</script>
