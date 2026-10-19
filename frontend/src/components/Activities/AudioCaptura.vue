<template>
  <div class="flex flex-col gap-2 rounded-lg border border-outline-gray-2 p-3">
    <div class="flex flex-wrap items-center gap-2">
      <Button
        :variant="ditando ? 'solid' : 'subtle'"
        :theme="ditando ? 'red' : 'gray'"
        :iconLeft="ditando ? 'lucide-square' : 'lucide-mic'"
        :label="ditando ? __('Parar ditado') : __('Ditar agora')"
        :disabled="!temDitado || gravando"
        @click="alternarDitado"
      />
      <Button
        :variant="gravando ? 'solid' : 'subtle'"
        :theme="gravando ? 'red' : 'gray'"
        :iconLeft="gravando ? 'lucide-square' : 'lucide-audio-lines'"
        :label="gravando ? __('Parar e transcrever ({0})', [tempo]) : __('Gravar a consulta')"
        :disabled="ditando || enviando"
        @click="alternarGravacao"
      />
      <Button variant="subtle" iconLeft="lucide-upload" :label="__('Enviar áudio')" :disabled="ditando || gravando || enviando" @click="$refs.arq.click()" />
      <input ref="arq" type="file" accept="audio/*,.ogg,.opus,.m4a,.mp3,.wav,.webm" class="hidden" @change="enviarArquivo" />
      <span v-if="enviando" class="text-p-sm text-ink-gray-5">{{ __('Transcrevendo o áudio...') }}</span>
    </div>
    <p class="text-xs text-ink-gray-5">
      {{ __('Ditar: o texto aparece enquanto você fala (grátis, funciona melhor no Chrome). Gravar ou enviar áudio (até 25 min, inclusive áudio do WhatsApp): o áudio é transcrito e entra no texto abaixo.') }}
    </p>
    <div v-if="estado.data && !estado.data.configurado" class="rounded bg-surface-amber-1 px-3 py-2 text-xs text-ink-amber-3">
      <template v-if="estado.data.pode_configurar">
        {{ __('Para gravar ou enviar áudio, cadastre uma chave da OpenAI (transcrição custa centavos por minuto). O ditado funciona sem chave.') }}
        <div class="mt-2 flex gap-2">
          <FormControl v-model="chave" type="password" class="flex-1" placeholder="sk-..." />
          <Button size="sm" variant="solid" :label="__('Salvar chave')" @click="salvarChave" />
        </div>
      </template>
      <template v-else>{{ __('Gravar ou enviar áudio ainda não está ligado. Use o ditado ou peça a um gestor para ligar.') }}</template>
    </div>
    <ErrorMessage v-if="erro" :message="erro" />
  </div>
</template>

<script setup>
import { Button, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { onBeforeUnmount, ref } from 'vue'

const emit = defineEmits(['texto'])
const estado = createResource({ url: 'crm.api.audio.estado', auto: true })
const erro = ref('')

// ---- ditado ao vivo (reconhecimento de voz do navegador)
const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition
const temDitado = !!Reconhecimento
const ditando = ref(false)
let rec = null
function alternarDitado() {
  if (ditando.value) {
    ditando.value = false
    rec?.stop()
    return
  }
  erro.value = ''
  rec = new Reconhecimento()
  rec.lang = 'pt-BR'
  rec.continuous = true
  rec.interimResults = false
  rec.onresult = (e) => {
    for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) emit('texto', e.results[i][0].transcript.trim())
  }
  // o navegador para sozinho depois de um silêncio: recomeça enquanto o botão estiver ligado
  rec.onend = () => ditando.value && rec.start()
  rec.onerror = (e) => {
    if (e.error === 'not-allowed') {
      erro.value = __('Libere o microfone para este site.')
      ditando.value = false
    }
  }
  rec.start()
  ditando.value = true
}

// ---- gravação da consulta
const gravando = ref(false)
const tempo = ref('0:00')
let gravador = null
let pedacos = []
let relogio = null
async function alternarGravacao() {
  if (gravando.value) {
    gravador?.stop()
    return
  }
  if (estado.data && !estado.data.configurado) return (erro.value = __('Cadastre a chave de transcrição primeiro (ou use o ditado).'))
  erro.value = ''
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    pedacos = []
    gravador = new MediaRecorder(stream)
    gravador.ondataavailable = (e) => e.data.size && pedacos.push(e.data)
    gravador.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      clearInterval(relogio)
      gravando.value = false
      const tipo = gravador.mimeType || 'audio/webm'
      transcrever(new Blob(pedacos, { type: tipo }), 'consulta.' + (tipo.includes('ogg') ? 'ogg' : tipo.includes('mp4') ? 'm4a' : 'webm'))
    }
    gravador.start(1000)
    const inicio = Date.now()
    relogio = setInterval(() => {
      const s = Math.floor((Date.now() - inicio) / 1000)
      tempo.value = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
      if (s >= 25 * 60) gravador.stop() // limite do serviço de transcrição
    }, 1000)
    gravando.value = true
  } catch (e) {
    erro.value = __('Não foi possível usar o microfone. Libere o acesso no navegador.')
  }
}

// ---- envio de arquivo
const enviando = ref(false)
function enviarArquivo(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (f) transcrever(f, f.name)
}
async function transcrever(blob, nome) {
  enviando.value = true
  erro.value = ''
  try {
    const fd = new FormData()
    fd.append('file', blob, nome)
    const r = await fetch('/api/method/crm.api.audio.transcrever', {
      method: 'POST',
      body: fd,
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    })
    const j = await r.json()
    if (!r.ok) {
      let msg = __('Não foi possível transcrever.')
      try {
        msg = JSON.parse(JSON.parse(j._server_messages)[0]).message
      } catch (x) {}
      throw new Error(msg)
    }
    emit('texto', j.message.texto)
    toast.success(__('Áudio transcrito'))
  } catch (e) {
    erro.value = e.message
  } finally {
    enviando.value = false
  }
}

const chave = ref('')
async function salvarChave() {
  try {
    await call('crm.api.audio.salvar_chave', { chave: chave.value })
    chave.value = ''
    estado.reload()
    toast.success(__('Chave salva'))
  } catch (e) {
    erro.value = e?.messages?.[0] || __('Não foi possível salvar.')
  }
}

onBeforeUnmount(() => {
  ditando.value = false
  rec?.stop()
  if (gravando.value) gravador?.stop()
})
</script>
