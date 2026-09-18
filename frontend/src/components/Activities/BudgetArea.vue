<template>
  <div
    class="my-3 flex items-center justify-between text-lg-medium sm:mb-4 sm:mt-8"
  >
    <div class="flex h-8 items-center text-2xl-semibold text-ink-gray-8">
      {{ __('Orçamento') }}
      <Badge
        v-if="document.isDirty"
        class="ml-3"
        :label="__('Não Salvo')"
        theme="orange"
      />
    </div>
    <div class="flex gap-2">
      <Dropdown :options="generateOptions" placement="right">
        <Button :label="__('Gerar Documento')">
          <template #prefix>
            <span class="lucide-file-text size-4" aria-hidden="true" />
          </template>
        </Button>
      </Dropdown>
      <Button
        variant="solid"
        :label="__('Salvar')"
        :disabled="!document.isDirty"
        :loading="document.save.loading"
        @click="save"
      />
    </div>
  </div>

  <div class="pb-8">
    <table class="w-full text-sm">
      <thead>
        <tr class="text-left text-ink-gray-5">
          <th class="pb-2 font-normal">{{ __('Descrição') }}</th>
          <th class="w-20 pb-2 font-normal">{{ __('Qtd') }}</th>
          <th class="w-32 pb-2 font-normal">{{ __('Preço Unitário') }}</th>
          <th class="w-32 pb-2 text-right font-normal">{{ __('Subtotal') }}</th>
          <th class="w-8"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(item, idx) in items"
          :key="idx"
          class="border-t border-outline-gray-2"
        >
          <td class="py-2 pr-2">
            <FormControl type="text" v-model="item.description" :placeholder="__('Item')" />
          </td>
          <td class="py-2 pr-2">
            <FormControl type="number" v-model="item.qty" />
          </td>
          <td class="py-2 pr-2">
            <FormControl type="number" v-model="item.unit_price" />
          </td>
          <td class="py-2 pr-2 text-right text-ink-gray-7">
            {{ formatCurrency(itemAmount(item)) }}
          </td>
          <td class="py-2">
            <Button variant="ghost" icon="lucide-trash-2" @click="removeItem(idx)" />
          </td>
        </tr>
      </tbody>
    </table>

    <Button class="mt-2" variant="subtle" iconLeft="plus" :label="__('Adicionar Item')" @click="addItem" />

    <div class="ml-auto mt-6 flex w-72 flex-col gap-2">
      <div class="flex items-center justify-between text-sm text-ink-gray-6">
        <span>{{ __('Subtotal') }}</span>
        <span>{{ formatCurrency(subtotal) }}</span>
      </div>
      <div class="flex items-center justify-between text-sm text-ink-gray-6">
        <span>{{ __('Desconto') }}</span>
        <FormControl type="number" class="w-28" v-model="discount" />
      </div>
      <div class="flex items-center justify-between border-t border-outline-gray-2 pt-2 text-base font-semibold text-ink-gray-9">
        <span>{{ __('Total') }}</span>
        <span>{{ formatCurrency(total) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, Dropdown, FormControl, toast } from 'frappe-ui'
import { useDocument } from '@/data/document'
import { computed } from 'vue'

const props = defineProps({
  doctype: { type: String, required: true },
  docname: { type: String, required: true },
})

const { document } = useDocument(props.doctype, props.docname)

const items = computed(() => {
  if (!document.doc.budget_items) document.doc.budget_items = []
  return document.doc.budget_items
})

const discount = computed({
  get: () => document.doc.budget_discount || 0,
  set: (val) => (document.doc.budget_discount = val),
})

function itemAmount(item) {
  return (Number(item.qty) || 0) * (Number(item.unit_price) || 0)
}

const subtotal = computed(() =>
  items.value.reduce((sum, item) => sum + itemAmount(item), 0),
)
const total = computed(() => subtotal.value - (Number(discount.value) || 0))

function addItem() {
  items.value.push({ description: '', qty: 1, unit_price: 0 })
}

function removeItem(idx) {
  items.value.splice(idx, 1)
}

function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value || 0)
}

function save() {
  document.save.submit(null, {
    onSuccess: () => toast.success(__('Orçamento salvo')),
    onError: (err) => toast.error(err.messages?.[0] || __('Erro ao salvar')),
  })
}

const generateOptions = [
  { label: __('Orçamento'), onClick: () => generate('orcamento') },
  { label: __('Proposta Comercial'), onClick: () => generate('proposta') },
  { label: __('Contrato'), onClick: () => generate('contrato') },
]

function generate(docType) {
  if (document.isDirty) {
    toast.error(__('Salve o orçamento antes de gerar o documento'))
    return
  }
  const params = new URLSearchParams({ deal: props.docname, doc_type: docType })
  window.open(`/api/method/crm.api.budget.generate_document?${params.toString()}`, '_blank')
}
</script>
