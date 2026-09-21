<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Instagram') }}</div>
    </template>
    <template #right-header>
      <Button :label="__('Configurações')" @click="openInstagramSettings">
        <template #prefix>
          <SettingsIcon class="size-4" />
        </template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex gap-1 border-b border-outline-gray-1 px-4 pt-1">
    <button
      v-for="t in visibleTabs"
      :key="t.key"
      type="button"
      class="-mb-px border-b-2 px-3 py-2 text-p-base"
      :class="tab === t.key ? 'border-ink-gray-9 font-medium text-ink-gray-9' : 'border-transparent text-ink-gray-5'"
      @click="tab = t.key"
    >
      {{ t.label }}
    </button>
  </div>

  <InstagramProspeccao v-if="tab === 'prospeccao'" @abrir-conversa="openFromProspeccao" />

  <InstagramAutomacao v-else-if="tab === 'automacoes' && isManager()" />

  <InstagramMetrics v-else-if="tab === 'metricas' && isManager()" />

  <div v-else class="flex min-h-0 flex-1">
    <!-- Conversas -->
    <div
      class="flex w-full flex-col border-r border-outline-gray-1 md:w-80 md:shrink-0"
      :class="selected ? 'hidden md:flex' : 'flex'"
    >
      <div class="p-3">
        <FormControl v-model="search" type="text" :placeholder="__('Buscar conversa')" />
      </div>
      <div class="flex-1 overflow-y-auto">
        <div v-if="conversations.loading && !conversations.data" class="p-4 text-p-sm text-ink-gray-5">
          {{ __('Carregando...') }}
        </div>
        <div
          v-else-if="!filtered.length"
          class="flex flex-col items-center gap-2 px-6 py-16 text-center text-ink-gray-5"
        >
          <ChatIcon class="size-8" />
          <div class="text-p-sm">
            {{
              search
                ? __('Nenhuma conversa encontrada.')
                : __('Nenhuma conversa ainda. Quando alguém mandar mensagem para o perfil, ela aparece aqui.')
            }}
          </div>
        </div>
        <button
          v-for="c in filtered"
          :key="c.lead"
          type="button"
          class="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-surface-gray-2"
          :class="selected?.lead === c.lead ? 'bg-surface-gray-2' : ''"
          @click="select(c)"
        >
          <Avatar :image="c.photo" :label="c.name" size="xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <div class="truncate text-base-medium text-ink-gray-9">{{ c.name }}</div>
              <div class="shrink-0 text-xs text-ink-gray-5">{{ timeText(c.last_time) }}</div>
            </div>
            <div v-if="c.username" class="truncate text-xs text-ink-gray-5">@{{ c.username }}</div>
            <div class="truncate text-p-sm text-ink-gray-6">
              <span v-if="c.last_direction === 'Sent'">{{ __('Você') }}: </span>{{ c.last_message }}
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- Conversa aberta -->
    <div class="min-w-0 flex-1 flex-col" :class="selected ? 'flex' : 'hidden md:flex'">
      <div v-if="!selected" class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5">
        {{ __('Escolha uma conversa ao lado para ver as mensagens.') }}
      </div>
      <template v-else>
        <div class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3">
          <Button class="md:hidden" variant="ghost" icon="lucide-chevron-left" @click="selected = null" />
          <Avatar :image="selected.photo" :label="selected.name" size="lg" />
          <div class="min-w-0 flex-1">
            <div class="truncate text-base-medium text-ink-gray-9">{{ selected.name }}</div>
            <div v-if="selected.username" class="truncate text-xs text-ink-gray-5">@{{ selected.username }}</div>
          </div>
          <Button variant="subtle" :label="__('Abrir lead')" @click="openLead" />
        </div>

        <div ref="scroller" class="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-4">
          <div
            v-for="m in thread.data || []"
            :key="m.name"
            class="flex"
            :class="m.direction === 'Sent' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[75%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-p-base"
              :class="
                m.direction === 'Sent'
                  ? 'rounded-br-md bg-surface-gray-9 text-ink-white'
                  : 'rounded-bl-md bg-surface-gray-2 text-ink-gray-9'
              "
            >
              {{ m.message }}
              <div
                class="mt-1 text-right text-[10px]"
                :class="m.direction === 'Sent' ? 'text-ink-gray-4' : 'text-ink-gray-5'"
              >
                {{ timeText(m.timestamp) }}
              </div>
            </div>
          </div>
        </div>

        <ReplySuggestions
          :lead="selected.lead"
          :version="`${thread.data?.length || 0}-${thread.data?.[thread.data.length - 1]?.name || ''}`"
          @usar="(text) => (replyMessage = text)"
        />

        <div class="border-t border-outline-gray-1 p-3">
          <ErrorMessage v-if="replyError" class="mb-2" :message="replyError" />
          <div class="flex items-end gap-2">
            <FormControl
              v-model="replyMessage"
              class="flex-1"
              type="textarea"
              :rows="2"
              :placeholder="__('Escreva sua resposta...')"
              @keydown.enter.exact.prevent="sendReply"
            />
            <Button variant="solid" :label="__('Enviar')" :loading="sending" @click="sendReply" />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ChatIcon from '@/components/Icons/InstagramIcon.vue'
import SettingsIcon from '@/components/Icons/SettingsIcon.vue'
import { timestampCell } from '@/composables/useTimelinePreferences'
import InstagramMetrics from '@/components/InstagramMetrics.vue'
import InstagramAutomacao from '@/components/InstagramAutomacao.vue'
import ReplySuggestions from '@/components/ReplySuggestions.vue'
import InstagramProspeccao from '@/components/InstagramProspeccao.vue'
import { usersStore } from '@/stores/users'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { Avatar, Button, ErrorMessage, FormControl, call, createResource } from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { isManager } = usersStore()
const tab = ref('mensagens')
const tabs = [
  { key: 'mensagens', label: __('Mensagens') },
  { key: 'prospeccao', label: __('Prospecção') },
  { key: 'automacoes', label: __('Automações'), manager: true },
  { key: 'metricas', label: __('Perfil'), manager: true },
]
const visibleTabs = computed(() => tabs.filter((t) => !t.manager || isManager()))

function openFromProspeccao(lead) {
  tab.value = 'mensagens'
  const c = (conversations.data || []).find((x) => x.lead === lead)
  if (c) select(c)
}
const search = ref('')
const selected = ref(null)
const scroller = ref(null)
const replyMessage = ref('')
const replyError = ref('')
const sending = ref(false)

const conversations = createResource({
  url: 'crm.api.instagram.get_conversations',
  auto: true,
})

const thread = createResource({
  url: 'crm.api.instagram.get_messages',
  makeParams: () => ({ lead: selected.value?.lead }),
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const list = conversations.data || []
  if (!q) return list
  return list.filter((c) => `${c.name} ${c.username}`.toLowerCase().includes(q))
})

function timeText(value) {
  return value ? timestampCell(value).timeAgo : ''
}

function select(c) {
  selected.value = c
  thread.fetch()
}

function scrollToEnd() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

// rola para a última mensagem quando chegar algo novo
watch(() => thread.data?.length, scrollToEnd)

// atualiza sozinho: novas mensagens aparecem sem precisar recarregar a página
let timer = null
onMounted(() => {
  timer = setInterval(() => {
    conversations.reload()
    if (selected.value) thread.reload()
  }, 10000)
})
onBeforeUnmount(() => clearInterval(timer))

async function sendReply() {
  const text = replyMessage.value.trim()
  if (!text || !selected.value) return
  sending.value = true
  replyError.value = ''
  try {
    await call('crm.api.instagram.send_reply', { lead: selected.value.lead, message: text })
    replyMessage.value = ''
    await Promise.all([thread.reload(), conversations.reload()])
    scrollToEnd()
  } catch (e) {
    replyError.value = e.messages?.join(', ') || e.message || __('Falha ao enviar')
  } finally {
    sending.value = false
  }
}

function openLead() {
  router.push({ name: 'Lead', params: { leadId: selected.value.lead } })
}

function openInstagramSettings() {
  showSettings.value = true
  activeSettingsPage.value = 'Instagram'
}
</script>
