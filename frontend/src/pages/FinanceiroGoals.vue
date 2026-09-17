<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Metas') }}</div>
    </template>
    <template #right-header>
      <Button
        v-if="goals.isDirty"
        variant="solid"
        :label="__('Salvar')"
        :loading="goals.save.loading"
        @click="save"
      />
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-6 overflow-y-auto p-8">
    <p class="text-p-base text-ink-gray-6">
      {{ __('Metas financeiras do escritório, usadas como referência nos Relatórios e na Calculadora.') }}
    </p>

    <div class="flex max-w-lg flex-col gap-5">
      <div class="flex flex-col gap-1.5">
        <label class="text-p-base-medium text-ink-gray-7">
          {{ __('Meta Trimestral de Receita') }}
        </label>
        <FormControl
          type="number"
          size="md"
          v-model="goals.doc.meta_trimestral"
          :placeholder="__('0,00')"
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <label class="text-p-base-medium text-ink-gray-7">
          {{ __('Teto de Despesa Mensal') }}
        </label>
        <FormControl
          type="number"
          size="md"
          v-model="goals.doc.teto_despesa"
          :placeholder="__('0,00')"
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <label class="text-p-base-medium text-ink-gray-7">
          {{ __('Meta de Receita Recorrente Mensal (MRR)') }}
        </label>
        <FormControl
          type="number"
          size="md"
          v-model="goals.doc.meta_mrr"
          :placeholder="__('0,00')"
        />
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { FormControl, createDocumentResource, toast } from 'frappe-ui'

const goals = createDocumentResource({
  doctype: 'CRM Financial Goals',
  name: 'CRM Financial Goals',
  auto: true,
})

function save() {
  goals.save.submit(null, {
    onSuccess: () => toast.success(__('Metas atualizadas')),
  })
}
</script>
