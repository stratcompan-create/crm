<template>
  <LayoutHeader>
    <template #left-header>
      <div class="flex items-center gap-2">
        <div class="text-lg font-semibold text-ink-gray-9">{{ __('WhatsApp') }}</div>
        <span v-if="status.data?.numero" class="text-p-sm text-ink-gray-5">· {{ status.data.numero }}</span>
      </div>
    </template>
    <template #right-header>
      <Button
        :variant="pessoais ? 'solid' : 'subtle'"
        :label="pessoais ? __('Ver conversas de trabalho') : __('Ver pessoais')"
        @click="alternarPessoais"
      />
    </template>
  </LayoutHeader>

  <div
    v-if="status.data && (!status.data.chave || !status.data.numero)"
    class="border-b border-outline-gray-1 bg-surface-amber-2 px-4 py-2 text-p-sm text-ink-amber-6"
  >
    {{ __('O WhatsApp ainda não está conectado neste CRM. Fale com o suporte da Stratcompany.') }}
  </div>

  <div class="flex min-h-0 flex-1">
    <!-- Conversas -->
    <div
      class="flex w-full flex-col border-r border-outline-gray-1 md:w-80 md:shrink-0"
      :class="selected ? 'hidden md:flex' : 'flex'"
    >
      <div class="p-3">
        <FormControl v-model="search" type="text" :placeholder="__('Buscar por nome ou telefone')" />
      </div>
      <div class="flex-1 overflow-y-auto">
        <div v-if="conversations.loading && !conversations.data" class="p-4 text-p-sm text-ink-gray-5">
          {{ __('Carregando...') }}
        </div>
        <div v-else-if="!filtered.length" class="flex flex-col items-center gap-2 px-6 py-16 text-center text-ink-gray-5">
          <WhatsAppIcon class="size-8" />
          <div class="text-p-sm">
            {{
              search
                ? __('Nenhuma conversa encontrada.')
                : pessoais
                  ? __('Nenhuma conversa marcada como pessoal.')
                  : __('Nenhuma conversa ainda. Quando alguém mandar mensagem para o seu WhatsApp, ela aparece aqui.')
            }}
          </div>
        </div>
        <button
          v-for="c in filtered"
          :key="c.telefone"
          type="button"
          class="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-surface-gray-2"
          :class="selected?.telefone === c.telefone ? 'bg-surface-gray-2' : ''"
          @click="select(c)"
        >
          <Avatar :label="c.titulo" size="xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <div class="truncate text-base-medium text-ink-gray-9">{{ c.titulo }}</div>
              <div class="shrink-0 text-xs text-ink-gray-5">{{ timeText(c.ultima_em) }}</div>
            </div>
            <div class="flex items-center justify-between gap-2">
              <div class="truncate text-p-sm text-ink-gray-6">
                <span v-if="c.ultima_direcao === 'Sent'">{{ __('Você') }}: </span>{{ c.ultima_mensagem }}
              </div>
              <span
                v-if="c.nao_lidas"
                class="shrink-0 rounded-full bg-[#25D366] px-1.5 text-xs font-medium text-white"
              >
                {{ c.nao_lidas }}
              </span>
            </div>
            <div v-if="!c.lead" class="text-xs text-ink-gray-4">{{ __('Ainda não é lead') }}</div>
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
          <Avatar :label="selected.titulo" size="lg" />
          <div class="min-w-0 flex-1">
            <div class="truncate text-base-medium text-ink-gray-9">{{ selected.titulo }}</div>
            <div class="truncate text-xs text-ink-gray-5">+{{ selected.telefone }}</div>
          </div>
          <Button
            variant="ghost"
            :label="selected.pessoal ? __('Voltar para trabalho') : __('Marcar como pessoal')"
            @click="trocarPessoal"
          />
          <Button v-if="selected.lead" variant="subtle" :label="__('Abrir lead')" @click="openLead" />
          <Button v-else variant="solid" :label="__('Criar lead')" :loading="criando" @click="criarLead" />
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
              <audio v-if="m.anexo && m.tipo === 'audio'" :src="m.anexo" controls class="mb-1 max-w-full" />
              <a v-else-if="m.anexo && ['image', 'sticker'].includes(m.tipo)" :href="m.anexo" target="_blank">
                <img :src="m.anexo" class="mb-1 max-h-64 rounded-lg" />
              </a>
              <video v-else-if="m.anexo && m.tipo === 'video'" :src="m.anexo" controls class="mb-1 max-h-64 rounded-lg" />
              <a
                v-else-if="m.anexo"
                :href="m.anexo"
                target="_blank"
                class="mb-1 block underline"
              >{{ __('Abrir arquivo') }}</a>
              <span v-if="!(m.anexo && ['audio', 'image', 'sticker', 'video'].includes(m.tipo) && isRotulo(m.message))">{{ m.message }}</span>
              <div
                class="mt-1 flex items-center justify-end gap-1 text-[10px]"
                :class="m.direction === 'Sent' ? 'text-ink-gray-4' : 'text-ink-gray-5'"
              >
                <span v-if="m.pelo_celular">{{ __('pelo celular') }} ·</span>
                <span>{{ timeText(m.timestamp) }}</span>
                <span v-if="m.direction === 'Sent'">{{ checks(m.status) }}</span>
              </div>
              <div v-if="m.erro" class="mt-1 text-[11px] text-[#f87171]">{{ __('Não entregue') }}: {{ m.erro }}</div>
            </div>
          </div>
        </div>

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
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import { timestampCell } from '@/composables/useTimelinePreferences'
import { Avatar, Button, ErrorMessage, FormControl, call, createResource } from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const search = ref('')
const pessoais = ref(false)
const selected = ref(null)
const scroller = ref(null)
const replyMessage = ref('')
const replyError = ref('')
const sending = ref(false)
const criando = ref(false)

const status = createResource({ url: 'crm.api.ycloud.get_status', auto: true })

const conversations = createResource({
  url: 'crm.api.ycloud.get_conversations',
  makeParams: () => ({ pessoais: pessoais.value ? 1 : 0 }),
  auto: true,
})

const thread = createResource({
  url: 'crm.api.ycloud.get_messages',
  makeParams: () => ({ telefone: selected.value?.telefone }),
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const lista = conversations.data || []
  if (!q) return lista
  const digitos = q.replace(/\D/g, '')
  return lista.filter(
    (c) => c.titulo.toLowerCase().includes(q) || (digitos && c.telefone.includes(digitos)),
  )
})

function timeText(value) {
  return value ? timestampCell(value).timeAgo : ''
}

function checks(s) {
  if (s === 'read') return '✓✓ lida'
  if (s === 'delivered') return '✓✓'
  if (s === 'failed') return '✕'
  return '✓'
}

// "🎤 Áudio" sozinho não precisa aparecer embaixo do próprio player
function isRotulo(texto) {
  return ['📷 Foto', '🎤 Áudio', '🎬 Vídeo', 'Figurinha'].includes(texto)
}

function select(c) {
  selected.value = c
  replyError.value = ''
  thread.fetch().then(() => conversations.reload())
}

function alternarPessoais() {
  pessoais.value = !pessoais.value
  selected.value = null
  conversations.reload()
}

function scrollToEnd() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

watch(() => thread.data?.length, scrollToEnd)

// atualiza sozinho: mensagens novas aparecem sem recarregar a página
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
    await call('crm.api.ycloud.send_message', { telefone: selected.value.telefone, message: text })
    replyMessage.value = ''
    await Promise.all([thread.reload(), conversations.reload()])
    scrollToEnd()
  } catch (e) {
    replyError.value = e.messages?.join(', ') || e.message || __('Falha ao enviar')
  } finally {
    sending.value = false
  }
}

async function criarLead() {
  criando.value = true
  try {
    const lead = await call('crm.api.ycloud.criar_lead', { telefone: selected.value.telefone })
    selected.value = { ...selected.value, lead }
    conversations.reload()
  } catch (e) {
    replyError.value = e.messages?.join(', ') || e.message || __('Falha ao criar o lead')
  } finally {
    criando.value = false
  }
}

async function trocarPessoal() {
  await call('crm.api.ycloud.marcar_pessoal', {
    telefone: selected.value.telefone,
    pessoal: selected.value.pessoal ? 0 : 1,
  })
  selected.value = null
  conversations.reload()
}

function openLead() {
  router.push({ name: 'Lead', params: { leadId: selected.value.lead } })
}
</script>
