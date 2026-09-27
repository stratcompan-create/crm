<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex flex-col gap-2 border-b border-outline-gray-1 px-4 py-2.5">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex gap-1">
          <button
            v-for="t in tipos"
            :key="t.value"
            type="button"
            class="rounded-full border px-3 py-1 text-p-sm"
            :class="tipo === t.value ? 'border-ink-gray-9 bg-surface-gray-2 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-7'"
            @click="tipo = t.value"
          >
            {{ t.label }}
          </button>
        </div>
        <div class="flex gap-2">
          <Button variant="ghost" :label="__('Histórico')" @click="toggleHistorico" />
          <Button variant="subtle" :label="__('+ Nova')" @click="novaConversa" />
        </div>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="text-xs text-ink-gray-5">{{ __('Modelo:') }}</span>
        <button
          v-for="m in modelos"
          :key="m.value"
          type="button"
          class="rounded-full border px-2.5 py-0.5 text-xs"
          :class="modelo === m.value ? 'border-ink-gray-9 bg-surface-gray-2 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6'"
          @click="modelo = m.value"
        >
          {{ m.label }}
        </button>
      </div>
    </div>

    <div v-if="mostrarHistorico" class="border-b border-outline-gray-1 px-4 py-2">
      <div v-if="historico.loading" class="py-2 text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <div v-else-if="!historico.data?.length" class="py-2 text-p-sm text-ink-gray-5">
        {{ __('Nenhuma conversa ainda.') }}
      </div>
      <div v-else class="flex flex-col gap-1 max-h-40 overflow-y-auto">
        <button
          v-for="c in historico.data"
          :key="c.name"
          type="button"
          class="flex items-center justify-between rounded px-2 py-1.5 text-left text-p-sm hover:bg-surface-gray-2"
          @click="abrirConversa(c.name)"
        >
          <span class="truncate">{{ c.titulo || c.name }}</span>
          <span class="shrink-0 text-xs text-ink-gray-5">{{ c.tipo }} · {{ c.status }}</span>
        </button>
      </div>
    </div>

    <div class="flex min-h-0 flex-1">
      <!-- Chat -->
      <div class="flex w-full min-w-0 flex-1 flex-col border-r border-outline-gray-1 md:max-w-md">
        <div ref="scroller" class="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-4">
          <div v-if="!mensagens.length" class="flex flex-col items-center gap-2 px-6 py-16 text-center text-ink-gray-5">
            <SparkleIcon class="size-8" />
            <div class="text-base-medium text-ink-gray-7">{{ __('Criar conteúdo') }}</div>
            <div class="text-p-sm">
              {{ __('Descreva o que você quer criar. O texto já sai com a cor e o nome da marca aplicados.') }}
            </div>
          </div>
          <div
            v-for="(m, i) in mensagens"
            :key="i"
            class="flex"
            :class="m.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2 text-p-base"
              :class="
                m.role === 'user'
                  ? 'rounded-br-md bg-surface-gray-9 text-ink-white'
                  : 'rounded-bl-md bg-surface-gray-2 text-ink-gray-9'
              "
            >
              {{ textoExibido(m) }}
            </div>
          </div>
          <div v-if="enviando" class="flex justify-start">
            <div class="rounded-2xl rounded-bl-md bg-surface-gray-2 px-3.5 py-2 text-p-sm text-ink-gray-5">
              {{ __('Gerando...') }}
            </div>
          </div>
        </div>

        <div class="border-t border-outline-gray-1 p-3">
          <ErrorMessage v-if="erro" class="mb-2" :message="erro" />
          <div class="flex items-end gap-2">
            <FormControl
              v-model="mensagem"
              class="flex-1"
              type="textarea"
              :rows="2"
              :placeholder="__('Descreva o que você quer criar...')"
              @keydown.enter.exact.prevent="enviar"
            />
            <Button variant="solid" :label="__('Enviar')" :loading="enviando" @click="enviar" />
          </div>
        </div>
      </div>

      <!-- Editor -->
      <div class="hidden min-w-0 flex-1 flex-col md:flex">
        <div v-if="!slides.length" class="flex flex-1 items-center justify-center text-center text-p-sm text-ink-gray-5">
          {{ __('Descreva no chat o que você quer. Quando o conteúdo ficar pronto, o editor aparece aqui.') }}
        </div>
        <template v-else>
          <div class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-2">
            <div class="flex items-center gap-1">
              <button
                v-for="(s, i) in slides"
                :key="i"
                type="button"
                class="flex size-7 items-center justify-center rounded-full border text-p-sm"
                :class="i === slideAtivo ? 'border-ink-gray-9 bg-surface-gray-2 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6'"
                @click="slideAtivo = i"
              >
                {{ i + 1 }}
              </button>
            </div>
            <Button
              variant="outline"
              size="sm"
              :label="statusConversa === 'Agendado' ? __('Reagendar') : __('Agendar')"
              @click="mostrarAgendar = true"
            />
          </div>
          <InstagramEditor
            :key="conversa + '-' + slideAtivo"
            :conversa="conversa"
            :indice="slideAtivo"
            :slide="slides[slideAtivo]"
            :tipo="tipo"
            :modelo="modelo"
            :cor-marca="corFundo"
            :cor-destaque="settings.doc?.brand_accent || '#8aa1a9'"
            :cor-neutra="settings.doc?.brand_neutral || '#f4f2ed'"
            :nome-marca="brandName"
          />
        </template>
      </div>
    </div>

    <Dialog v-model="mostrarAgendar" :options="{ title: __('Agendar publicação'), size: 'sm' }">
      <template #body-content>
        <FormControl type="date" v-model="dataAgendada" :label="__('Data')" />
      </template>
      <template #actions>
        <Button variant="solid" :label="__('Salvar')" :loading="agendando" @click="agendar" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import SparkleIcon from '@/components/Icons/SparkleIcon.vue'
import InstagramEditor from '@/components/InstagramEditor.vue'
import { getSettings } from '@/stores/settings'
import { Button, Dialog, ErrorMessage, FormControl, call, createResource } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'

const { _settings: settings } = getSettings()
const brandName = computed(() => settings.doc?.brand_name || 'Sua marca')
const corFundo = computed(() => settings.doc?.brand_color || '#042d3c')
const corTexto = computed(() => '#ffffff')

const tipos = [
  { value: 'Post', label: __('Post') },
  { value: 'Carrossel', label: __('Carrossel') },
  { value: 'Story', label: __('Story') },
]
const tipo = ref('Carrossel')
const slideAtivo = ref(0)

const modelos = [
  { value: 'padrao', label: __('Padrão') },
  { value: 'twitter', label: __('Estilo Twitter') },
  { value: 'citacao', label: __('Citação') },
]
const modelo = ref('padrao')

const conversa = ref(null)
const statusConversa = ref('Rascunho')
const mensagens = ref([])
const slides = ref([])
const mensagem = ref('')
const enviando = ref(false)
const erro = ref('')
const scroller = ref(null)

const mostrarHistorico = ref(false)
const historico = createResource({ url: 'crm.api.conteudo.listar_conversas' })

function toggleHistorico() {
  mostrarHistorico.value = !mostrarHistorico.value
  if (mostrarHistorico.value) historico.fetch()
}

function novaConversa() {
  conversa.value = null
  statusConversa.value = 'Rascunho'
  mensagens.value = []
  slides.value = []
  slideAtivo.value = 0
  mensagem.value = ''
  erro.value = ''
  mostrarHistorico.value = false
}

async function abrirConversa(name) {
  mostrarHistorico.value = false
  const r = await call('crm.api.conteudo.obter_conversa', { conversa: name })
  conversa.value = r.name
  tipo.value = r.tipo
  statusConversa.value = r.status
  mensagens.value = r.mensagens
  slides.value = r.slides
  slideAtivo.value = 0
  scrollToEnd()
}

function textoExibido(m) {
  if (m.role !== 'assistant') return m.content
  try {
    const parsed = JSON.parse(m.content)
    return parsed.resposta || m.content
  } catch {
    return m.content
  }
}

function scrollToEnd() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

async function enviar() {
  const texto = mensagem.value.trim()
  if (!texto || enviando.value) return
  erro.value = ''
  mensagens.value.push({ role: 'user', content: texto })
  mensagem.value = ''
  scrollToEnd()
  enviando.value = true
  try {
    const r = await call('crm.api.conteudo.enviar_mensagem', {
      mensagem: texto,
      conversa: conversa.value,
      tipo: tipo.value,
    })
    conversa.value = r.conversa
    tipo.value = r.tipo
    mensagens.value.push({ role: 'assistant', content: JSON.stringify({ resposta: r.resposta }) })
    if (r.slides?.length) {
      slides.value = r.slides
      slideAtivo.value = 0
    }
    scrollToEnd()
  } catch (e) {
    erro.value = e.messages?.join(', ') || e.message || __('Falha ao gerar conteúdo')
    mensagens.value.pop()
  } finally {
    enviando.value = false
  }
}

const mostrarAgendar = ref(false)
const dataAgendada = ref('')
const agendando = ref(false)

async function agendar() {
  if (!conversa.value || !dataAgendada.value) return
  agendando.value = true
  try {
    await call('crm.api.conteudo.marcar_agendado', {
      conversa: conversa.value,
      data_agendada: dataAgendada.value,
    })
    statusConversa.value = 'Agendado'
    mostrarAgendar.value = false
  } finally {
    agendando.value = false
  }
}
</script>
