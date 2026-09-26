<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8 text-ink-gray-8">
    <div class="flex justify-between px-2 text-ink-gray-8">
      <div class="flex flex-col gap-1">
        <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
          {{ __('Pagamentos') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('Configuração da geração de links de pagamento (InfinitePay).') }}
        </p>
      </div>
      <div class="flex item-center space-x-2 w-3/12 justify-end">
        <Button
          v-if="settings.isDirty"
          :label="__('Update')"
          variant="solid"
          :loading="settings.loading"
          @click="updateSettings"
        />
      </div>
    </div>

    <div class="flex flex-1 flex-col p-2 gap-4 overflow-y-auto">
      <div class="flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('InfiniteTag (InfinitePay)') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Sua InfiniteTag no app InfinitePay, sem o $ do início. Usada para gerar links de pagamento no Financeiro.') }}
        </div>
        <FormControl
          type="text"
          v-model="settings.doc.infinitepay_handle"
          :placeholder="__('seu-handle')"
        />
      </div>
    </div>
  </div>
</template>
<script setup>
import { FormControl } from 'frappe-ui'
import { getSettings } from '@/stores/settings'
import { showSettings } from '@/composables/settings'

const { _settings: settings, setupBrand } = getSettings()

function updateSettings() {
  settings.save.submit(null, {
    onSuccess: () => {
      showSettings.value = false
      setupBrand()
    },
  })
}
</script>
