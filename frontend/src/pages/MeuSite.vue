<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Meu Site') }}</div>
    </template>
    <template #right-header>
      <Button :label="__('Trocar Link')" @click="startEdit">
        <template #prefix>
          <span class="lucide-link size-4" aria-hidden="true" />
        </template>
      </Button>
      <Button v-if="url" :label="__('Abrir em Nova Aba')" @click="openInNewTab">
        <template #prefix>
          <span class="lucide-external-link size-4" aria-hidden="true" />
        </template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col overflow-hidden">
    <iframe
      v-if="url"
      :src="url"
      class="h-full w-full flex-1 border-0"
      :title="__('Meu Site')"
    />
    <div v-else class="flex flex-1 flex-col items-center justify-center gap-3">
      <span class="lucide-globe size-10 text-ink-gray-5" aria-hidden="true" />
      <div class="flex flex-col items-center gap-1">
        <span class="text-lg-medium text-ink-gray-8">{{ __('Nenhum site configurado') }}</span>
        <span class="text-center text-p-base text-ink-gray-6">
          {{ __('Informe o endereço do site do escritório para vê-lo aqui dentro do CRM.') }}
        </span>
      </div>
      <Button variant="solid" :label="__('Configurar Site')" @click="startEdit" />
    </div>
  </div>

  <Dialog v-model="showEditDialog" :options="{ title: __('Meu Site'), size: 'sm' }">
    <template #body-content>
      <p class="mb-3 text-p-sm text-ink-gray-6">
        {{ __('Informe o endereço do site do escritório.') }}
      </p>
      <FormControl
        type="text"
        v-model="urlDraft"
        :placeholder="__('https://seusite.com')"
        @keydown.enter="save"
      />
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Salvar')" :loading="saving" @click="save" />
    </template>
  </Dialog>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { getSettings } from '@/stores/settings'
import { Dialog, FormControl, Button, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const { settings, _settings } = getSettings()

const url = computed(() => settings.value?.website_url || '')

const showEditDialog = ref(false)
const urlDraft = ref('')
const saving = ref(false)

function startEdit() {
  urlDraft.value = url.value
  showEditDialog.value = true
}

function openInNewTab() {
  window.open(url.value, '_blank', 'noopener')
}

async function save() {
  const newUrl = urlDraft.value.trim()
  if (!newUrl) return
  saving.value = true
  try {
    await _settings.setValue.submit({ website_url: newUrl })
    if (settings.value) settings.value.website_url = newUrl
    showEditDialog.value = false
    toast.success(__('Site salvo'))
  } catch (e) {
    toast.error(e.messages?.[0] || __('Falha ao salvar o site'))
  } finally {
    saving.value = false
  }
}
</script>
