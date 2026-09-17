<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('WhatsApp') }}</div>
    </template>
    <template #right-header>
      <Button :label="__('Configurações')" @click="openWhatsAppSettings">
        <template #prefix>
          <SettingsIcon class="size-4" />
        </template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 overflow-hidden">
    <div class="w-80 shrink-0 overflow-y-auto border-r border-outline-gray-1">
      <div
        v-for="conv in conversations.data || []"
        :key="conv.reference_doctype + conv.reference_name"
        class="cursor-pointer border-b border-outline-gray-1 p-3"
        :class="isActive(conv) ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
        @click="selectConversation(conv)"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="truncate text-p-base-medium text-ink-gray-9">{{ conv.title }}</div>
          <div class="shrink-0 text-2xs text-ink-gray-5">
            {{ formatDate(conv.last_message_at, 'DD/MM HH:mm') }}
          </div>
        </div>
        <div class="truncate text-p-sm text-ink-gray-6">{{ conv.last_message }}</div>
      </div>

      <div
        v-if="!conversations.loading && !conversations.data?.length"
        class="p-6 text-center text-p-sm text-ink-gray-5"
      >
        {{ __('Nenhuma conversa de WhatsApp ainda') }}
      </div>
    </div>

    <div class="flex flex-1 flex-col overflow-hidden">
      <template v-if="active">
        <div class="flex-1 overflow-y-auto p-4">
          <WhatsAppArea
            :messages="messagesData"
            v-model="messagesModel"
            v-model:reply="reply"
          />
        </div>
        <div class="border-t border-outline-gray-1 p-3">
          <div
            v-if="reply?.message"
            class="mb-2 flex items-center justify-between gap-2 rounded border-0 border-l-4 border-outline-gray-4 bg-surface-gray-2 p-2 text-p-sm text-ink-gray-6"
          >
            <div class="truncate" v-html="reply.message" />
            <Button variant="ghost" icon="lucide-x" @click="reply = {}" />
          </div>
          <div class="flex items-end gap-2">
            <FormControl
              type="textarea"
              class="flex-1"
              v-model="draft"
              :placeholder="__('Digite sua mensagem...')"
              :rows="2"
              @keydown.enter.exact.prevent="send"
            />
            <Button variant="solid" :label="__('Enviar')" :loading="sending" @click="send" />
          </div>
        </div>
      </template>
      <EmptyState
        v-else
        name="WhatsApp"
        :icon="WhatsAppIcon"
        :title="__('Nenhuma conversa selecionada')"
        :description="__('Escolha uma conversa na lista ao lado para ver as mensagens.')"
      />
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import WhatsAppArea from '@/components/Activities/WhatsAppArea.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import SettingsIcon from '@/components/Icons/SettingsIcon.vue'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { formatDate } from '@/utils'
import { createResource, FormControl, call, toast } from 'frappe-ui'
import { ref } from 'vue'

const active = ref(null)
const reply = ref({})
const draft = ref('')
const sending = ref(false)
const messagesData = ref([])

// WhatsAppArea only calls `.reload()` on this after a reaction is added.
const messagesModel = ref({ reload: () => selectConversation(active.value) })

const conversations = createResource({
  url: 'crm.api.whatsapp.get_whatsapp_conversations',
  auto: true,
})

function isActive(conv) {
  return (
    active.value &&
    active.value.reference_doctype === conv.reference_doctype &&
    active.value.reference_name === conv.reference_name
  )
}

async function selectConversation(conv) {
  if (!conv) return
  active.value = conv
  reply.value = {}
  draft.value = ''
  try {
    messagesData.value = await call('crm.api.whatsapp.get_whatsapp_messages', {
      reference_doctype: conv.reference_doctype,
      reference_name: conv.reference_name,
    })
  } catch (e) {
    toast.error(e.messages?.[0] || __('Falha ao carregar mensagens do WhatsApp'))
  }
}

function openWhatsAppSettings() {
  showSettings.value = true
  activeSettingsPage.value = 'WhatsApp'
}

async function send() {
  if (!draft.value.trim() || !active.value) return
  sending.value = true
  try {
    await call('crm.api.whatsapp.create_whatsapp_message', {
      reference_doctype: active.value.reference_doctype,
      reference_name: active.value.reference_name,
      message: draft.value,
      to: active.value.whatsapp_to,
      attach: '',
      reply_to: reply.value?.name || '',
      content_type: 'text',
    })
    draft.value = ''
    reply.value = {}
    await selectConversation(active.value)
    conversations.reload()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Falha ao enviar mensagem do WhatsApp'))
  } finally {
    sending.value = false
  }
}
</script>
