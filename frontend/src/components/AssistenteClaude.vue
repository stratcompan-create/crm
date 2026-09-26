<template>
  <div class="flex h-full shrink-0" :class="aberto ? 'w-96 border-l border-outline-gray-1' : 'w-0'">
    <button
      v-if="!aberto"
      type="button"
      class="fixed bottom-6 right-6 z-20 flex size-12 items-center justify-center rounded-full bg-surface-gray-9 text-ink-white shadow-lg"
      @click="abrir"
    >
      <SparkleIcon class="size-5" />
    </button>

    <div v-else class="flex h-full w-96 flex-col">
      <div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
        <div class="flex items-center gap-2">
          <SparkleIcon class="size-4 text-ink-gray-7" />
          <span class="text-base-medium text-ink-gray-9">{{ __('Claude') }}</span>
          <span class="truncate text-xs text-ink-gray-5">· {{ contexto.tela }}</span>
        </div>
        <div class="flex items-center gap-1">
          <Button variant="ghost" size="sm" :label="__('Nova conversa')" @click="novaConversa" />
          <Button variant="ghost" size="sm" icon="x" @click="aberto = false" />
        </div>
      </div>

      <div ref="scroller" class="flex flex-1 flex-col gap-2 overflow-y-auto px-3 py-3">
        <div v-if="!mensagens.length" class="flex flex-col items-center gap-2 px-4 py-10 text-center text-ink-gray-5">
          <SparkleIcon class="size-6" />
          <div class="text-p-sm">
            {{ __('Pergunte alguma coisa. Ele sabe em qual tela você está.') }}
          </div>
        </div>
        <div v-for="(m, i) in mensagens" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
          <div
            class="max-w-[88%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-p-base"
            :class="
              m.role === 'user'
                ? 'rounded-br-md bg-surface-gray-9 text-ink-white'
                : 'rounded-bl-md bg-surface-gray-2 text-ink-gray-9'
            "
          >
            {{ m.content }}
          </div>
        </div>
        <div v-if="enviando" class="flex justify-start">
          <div class="rounded-2xl rounded-bl-md bg-surface-gray-2 px-3.5 py-2 text-p-sm text-ink-gray-5">
            {{ __('Pensando...') }}
          </div>
        </div>
      </div>

      <div class="border-t border-outline-gray-1 p-3">
        <ErrorMessage v-if="erro" class="mb-2" :message="erro" />
        <div class="mb-2">
          <Button variant="outline" size="sm" :label="__('Falar com atendente')" @click="falarComAtendente" />
        </div>
        <div class="flex items-end gap-2">
          <FormControl
            v-model="mensagem"
            class="flex-1"
            type="textarea"
            :rows="2"
            :placeholder="__('Pergunte algo...')"
            @keydown.enter.exact.prevent="enviar"
          />
          <Button variant="solid" :label="__('Enviar')" :loading="enviando" @click="enviar" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import SparkleIcon from '@/components/Icons/SparkleIcon.vue'
import { Button, ErrorMessage, FormControl, call, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// Mapa tela -> doctype/param, para o assistente saber automaticamente qual
// registro está aberto sem precisar instrumentar cada página do CRM.
const ROTA_CONTEXTO = {
  Lead: { doctype: 'CRM Lead', param: 'leadId', label: 'Lead' },
  MobileLead: { doctype: 'CRM Lead', param: 'leadId', label: 'Lead' },
  Deal: { doctype: 'CRM Deal', param: 'dealId', label: 'Negócio' },
  MobileDeal: { doctype: 'CRM Deal', param: 'dealId', label: 'Negócio' },
  Contact: { doctype: 'Contact', param: 'contactId', label: 'Contato' },
  MobileContact: { doctype: 'Contact', param: 'contactId', label: 'Contato' },
  Organization: { doctype: 'CRM Organization', param: 'organizationId', label: 'Organização' },
  MobileOrganization: { doctype: 'CRM Organization', param: 'organizationId', label: 'Organização' },
  Leads: { label: 'Lista de leads' },
  Deals: { label: 'Lista de negócios' },
  Contacts: { label: 'Lista de contatos' },
  Organizations: { label: 'Lista de organizações' },
  Financeiro: { label: 'Financeiro' },
  'Financeiro Despesas': { label: 'Financeiro - Despesas' },
  'Financeiro Recorrencia': { label: 'Financeiro - Recorrência' },
  'Financeiro Metas': { label: 'Financeiro - Metas' },
  'Financeiro Relatorios': { label: 'Financeiro - Relatórios' },
  Instagram: { label: 'Instagram' },
  MeuSite: { label: 'Meu Site' },
  Mapas: { label: 'Mapas' },
  Prospeccao: { label: 'Prospecção' },
  Dashboard: { label: 'Visão Geral' },
  Tasks: { label: 'Tarefas' },
  Calendar: { label: 'Agenda' },
  Equipe: { label: 'Equipe' },
}

const contexto = computed(() => {
  const info = ROTA_CONTEXTO[route.name] || {}
  return {
    tela: info.label || String(route.name || ''),
    doctype: info.doctype || '',
    registro: info.param ? route.params?.[info.param] || '' : '',
  }
})

const aberto = ref(false)
const mensagens = ref([])
const mensagem = ref('')
const enviando = ref(false)
const erro = ref('')
const scroller = ref(null)
let carregado = false

function scrollToEnd() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

async function carregarHistorico() {
  if (carregado) return
  carregado = true
  try {
    const r = await call('crm.api.assistente.obter_historico')
    mensagens.value = r.mensagens || []
    scrollToEnd()
  } catch {
    carregado = false
  }
}

function abrir() {
  aberto.value = true
  carregarHistorico()
}

watch(aberto, (v) => {
  if (v) carregarHistorico()
})

async function enviar() {
  const texto = mensagem.value.trim()
  if (!texto || enviando.value) return
  erro.value = ''
  mensagens.value.push({ role: 'user', content: texto })
  mensagem.value = ''
  scrollToEnd()
  enviando.value = true
  try {
    const r = await call('crm.api.assistente.enviar_mensagem', {
      mensagem: texto,
      tela: contexto.value.tela,
      doctype: contexto.value.doctype,
      registro: contexto.value.registro,
    })
    mensagens.value.push({ role: 'assistant', content: r.resposta })
    scrollToEnd()
  } catch (e) {
    erro.value = e.messages?.join(', ') || e.message || __('Falha ao responder')
    mensagens.value.pop()
  } finally {
    enviando.value = false
  }
}

async function novaConversa() {
  await call('crm.api.assistente.nova_conversa')
  mensagens.value = []
  erro.value = ''
}

async function falarComAtendente() {
  try {
    await call('crm.api.assistente.solicitar_atendimento', { mensagem: mensagem.value.trim() })
    toast.success(__('Chamado o responsável. Você já pode continuar por aqui ou aguardar contato.'))
  } catch (e) {
    toast.error(e.messages?.join(', ') || e.message || __('Não consegui chamar o atendente'))
  }
}
</script>
