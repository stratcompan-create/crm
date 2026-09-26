<template>
  <div class="flex h-full shrink-0" :class="aberto ? 'w-96 border-l border-outline-gray-1' : 'w-0'">
    <button
      v-if="!aberto"
      type="button"
      class="fixed bottom-6 right-6 z-20 flex size-12 items-center justify-center rounded-full shadow-lg"
      :style="{ background: corDestaque }"
      @click="abrir"
    >
      <LucideBot class="size-6 text-white" />
    </button>

    <div v-else class="flex h-full w-96 flex-col">
      <div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
        <div class="flex items-center gap-2">
          <LucideBot class="size-4" :style="{ color: corDestaque }" />
          <span class="text-base-medium text-ink-gray-9">{{ __('Claude') }}</span>
          <span class="truncate text-xs text-ink-gray-5">· {{ contexto.tela }}</span>
        </div>
        <div class="flex items-center gap-1">
          <Button variant="ghost" size="sm" :label="__('Nova conversa')" @click="novaConversa" />
          <Button variant="ghost" size="sm" icon="x" @click="aberto = false" />
        </div>
      </div>

      <div ref="scroller" class="flex flex-1 flex-col gap-2 overflow-y-auto px-3 py-3">
        <div v-if="!mensagens.length" class="flex flex-col items-center gap-3 px-4 py-8 text-center">
          <LucideBot class="size-9" :style="{ color: corDestaque }" />
          <div class="text-base-medium text-ink-gray-8">{{ __('Converse com o Claude') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Ele sabe em qual tela você está. Pergunte algo ou escolha uma opção abaixo.') }}
          </div>
          <div class="flex w-full flex-col gap-2 pt-2">
            <button
              v-for="s in sugestoes"
              :key="s.texto"
              type="button"
              class="w-full rounded-full border border-outline-gray-2 px-4 py-2 text-p-sm text-ink-gray-7 hover:bg-surface-gray-2"
              @click="enviarSugestao(s.texto)"
            >
              {{ s.label }}
            </button>
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
            :placeholder="gravando ? __('Ouvindo...') : __('Pergunte algo...')"
            @keydown.enter.exact.prevent="enviar"
          />
          <button
            v-if="reconhecimentoDisponivel"
            type="button"
            class="flex size-8 shrink-0 items-center justify-center rounded-full"
            :class="gravando ? 'bg-red-500 text-white' : 'bg-surface-gray-3 text-ink-gray-7 hover:bg-surface-gray-4'"
            :title="gravando ? __('Parar gravação') : __('Gravar áudio')"
            @click="alternarGravacao"
          >
            <LucideMic class="size-4" />
          </button>
          <Button variant="solid" :label="__('Enviar')" :loading="enviando" @click="enviar" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LucideBot from '~icons/lucide/bot'
import LucideMic from '~icons/lucide/mic'
import { Button, ErrorMessage, FormControl, call, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getSettings } from '@/stores/settings'

const route = useRoute()
const { _settings: brandSettings } = getSettings()
const corDestaque = computed(() => brandSettings.doc?.brand_accent || '#8aa1a9')

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

// Três perguntas prontas por tela, pra quem não sabe por onde começar.
const SUGESTOES_POR_ROTA = {
  Dashboard: [
    { label: __('Como estão os negócios esse mês?'), texto: 'Como estão os negócios esse mês?' },
    { label: __('Tem alguma tarefa atrasada?'), texto: 'Tem alguma tarefa atrasada?' },
    { label: __('Resume o que mudou essa semana'), texto: 'Resume o que mudou essa semana' },
  ],
  Leads: [
    { label: __('Quantos leads novos essa semana?'), texto: 'Quantos leads novos entraram essa semana?' },
    { label: __('Quais leads preciso responder?'), texto: 'Quais leads eu ainda preciso responder?' },
    { label: __('Como funciona a distribuição de leads?'), texto: 'Como funciona a distribuição automática de leads?' },
  ],
  Lead: [
    { label: __('Resume esse lead'), texto: 'Resume esse lead pra mim' },
    { label: __('Ele já respondeu alguma mensagem?'), texto: 'Esse lead já respondeu alguma mensagem?' },
    { label: __('Que abordagem eu uso aqui?'), texto: 'Que abordagem eu uso com esse tipo de lead?' },
  ],
  Deals: [
    { label: __('Quais negócios estão parados?'), texto: 'Quais negócios estão parados sem movimento?' },
    { label: __('Quanto tenho em negociação?'), texto: 'Quanto eu tenho em negociação agora, somando tudo?' },
    { label: __('Como marco um negócio como ganho?'), texto: 'Como eu marco um negócio como ganho?' },
  ],
  Deal: [
    { label: __('Resume esse negócio'), texto: 'Resume esse negócio pra mim' },
    { label: __('Falta algo pra fechar?'), texto: 'Falta alguma coisa pra eu fechar esse negócio?' },
    { label: __('Como gero a proposta?'), texto: 'Como eu gero a proposta pra esse negócio?' },
  ],
  Financeiro: [
    { label: __('Quanto tenho a receber esse mês?'), texto: 'Quanto eu tenho a receber esse mês?' },
    { label: __('Tem pagamento atrasado?'), texto: 'Tem algum pagamento atrasado agora?' },
    { label: __('Como gero um link de pagamento?'), texto: 'Como eu gero um link de pagamento pra um cliente?' },
  ],
  Instagram: [
    { label: __('Como funciona a automação de comentários?'), texto: 'Como funciona a automação de comentários do Instagram?' },
    { label: __('Tenho mensagens sem resposta?'), texto: 'Eu tenho mensagens do Instagram sem resposta?' },
    { label: __('Como uso o gerador de conteúdo?'), texto: 'Como eu uso o gerador de conteúdo do Instagram?' },
  ],
  MeuSite: [
    { label: __('Como eu edito o meu site?'), texto: 'Como eu edito o meu site institucional?' },
    { label: __('Onde configuro o domínio?'), texto: 'Onde eu configuro o domínio do meu site?' },
    { label: __('Pra que serve essa aba?'), texto: 'Pra que serve a aba Meu Site?' },
  ],
}
const SUGESTOES_PADRAO = [
  { label: __('O que eu posso fazer nessa tela?'), texto: 'O que eu posso fazer nessa tela?' },
  { label: __('Como funciona o CRM no geral?'), texto: 'Como funciona o CRM no geral?' },
  { label: __('Me explica essa parte do sistema'), texto: 'Me explica pra que serve essa parte do sistema' },
]

const contexto = computed(() => {
  const info = ROTA_CONTEXTO[route.name] || {}
  return {
    tela: info.label || String(route.name || ''),
    doctype: info.doctype || '',
    registro: info.param ? route.params?.[info.param] || '' : '',
  }
})

const sugestoes = computed(() => SUGESTOES_POR_ROTA[route.name] || SUGESTOES_PADRAO)

const aberto = ref(false)
const mensagens = ref([])
const mensagem = ref('')
const enviando = ref(false)
const erro = ref('')
const scroller = ref(null)
let carregado = false

// Ditar por voz: usa o reconhecimento de fala do próprio navegador (Chrome/Edge),
// sem chave nem serviço novo - só não funciona em navegadores sem suporte (ex.: Firefox).
const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
const reconhecimentoDisponivel = !!SpeechRecognitionAPI
const gravando = ref(false)
let reconhecimento = null

function alternarGravacao() {
  if (!reconhecimentoDisponivel) return
  if (gravando.value) {
    reconhecimento?.stop()
    return
  }
  reconhecimento = new SpeechRecognitionAPI()
  reconhecimento.lang = 'pt-BR'
  reconhecimento.interimResults = false
  reconhecimento.continuous = false
  reconhecimento.onresult = (ev) => {
    const texto = Array.from(ev.results).map((r) => r[0].transcript).join(' ')
    mensagem.value = mensagem.value ? `${mensagem.value} ${texto}` : texto
  }
  reconhecimento.onerror = () => {
    erro.value = __('Não consegui ouvir. Confira a permissão do microfone.')
  }
  reconhecimento.onend = () => {
    gravando.value = false
  }
  erro.value = ''
  gravando.value = true
  reconhecimento.start()
}

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

async function enviarTexto(texto) {
  if (!texto || enviando.value) return
  erro.value = ''
  mensagens.value.push({ role: 'user', content: texto })
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

function enviar() {
  const texto = mensagem.value.trim()
  mensagem.value = ''
  enviarTexto(texto)
}

function enviarSugestao(texto) {
  enviarTexto(texto)
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
