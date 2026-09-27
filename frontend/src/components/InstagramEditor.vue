<template>
  <div class="flex min-h-0 flex-1">
    <!-- Barra de ferramentas -->
    <div class="flex w-14 shrink-0 flex-col items-center gap-1 border-r border-outline-gray-1 py-3">
      <button type="button" class="flex flex-col items-center gap-0.5 rounded p-2 text-ink-gray-6 hover:bg-surface-gray-2" @click="adicionarTexto">
        <LucideType class="size-4" />
        <span class="text-[10px]">{{ __('Texto') }}</span>
      </button>
      <button type="button" class="flex flex-col items-center gap-0.5 rounded p-2 text-ink-gray-6 hover:bg-surface-gray-2" @click="abrirUpload(null)">
        <LucideImage class="size-4" />
        <span class="text-[10px]">{{ __('Imagem') }}</span>
      </button>
      <button type="button" class="flex flex-col items-center gap-0.5 rounded p-2 text-ink-gray-6 hover:bg-surface-gray-2" @click="adicionarForma">
        <LucideSquare class="size-4" />
        <span class="text-[10px]">{{ __('Forma') }}</span>
      </button>
      <button
        v-if="objetoSelecionado"
        type="button"
        class="mt-2 flex flex-col items-center gap-0.5 rounded p-2 text-red-500 hover:bg-surface-gray-2"
        @click="removerSelecionado"
      >
        <LucideTrash2 class="size-4" />
        <span class="text-[10px]">{{ __('Excluir') }}</span>
      </button>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileSelecionado" />
    </div>

    <!-- Canvas -->
    <div class="flex flex-1 flex-col items-center gap-3 overflow-auto bg-surface-gray-1 p-6">
      <canvas ref="canvasEl" />
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :label="__('Baixar PNG')" @click="baixarPng" />
        <Button variant="solid" size="sm" :label="__('Salvar')" :loading="salvando" @click="salvar" />
      </div>
    </div>

    <!-- Painel do objeto selecionado / camadas -->
    <div class="flex w-56 shrink-0 flex-col border-l border-outline-gray-1 p-3">
      <template v-if="objetoSelecionado?.type === 'textbox'">
        <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Texto') }}</div>
        <div class="flex flex-col gap-2">
          <FormControl type="select" :label="__('Fonte')" v-model="propTexto.fontFamily" :options="fontes" @update:modelValue="aplicarFonte" />
          <FormControl type="number" :label="__('Tamanho')" v-model="propTexto.fontSize" @update:modelValue="aplicarTamanho" />
          <div>
            <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Cor') }}</div>
            <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="propTexto.fill" @input="aplicarCorTexto" />
          </div>
        </div>
      </template>
      <template v-else-if="objetoSelecionado?.type === 'rect'">
        <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Forma') }}</div>
        <div>
          <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Cor') }}</div>
          <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="propForma.fill" @input="aplicarCorForma" />
        </div>
      </template>
      <template v-else-if="objetoSelecionado?.type === 'image'">
        <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Imagem') }}</div>
        <Button variant="outline" size="sm" :label="__('Trocar imagem')" @click="abrirUpload(objetoSelecionado)" />
      </template>
      <template v-else>
        <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Fundo') }}</div>
        <div class="mb-3 flex flex-wrap gap-2">
          <button
            v-for="p in paletaFundo"
            :key="p.cor"
            type="button"
            class="size-8 rounded-full border-2"
            :class="corFundoAtual.toLowerCase() === p.cor.toLowerCase() ? 'border-ink-gray-9' : 'border-outline-gray-2'"
            :style="{ background: p.cor }"
            :title="p.rotulo"
            @click="corFundoAtual = p.cor; aplicarCorFundo()"
          />
        </div>
        <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Outra cor') }}</div>
        <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="corFundoAtual" @input="aplicarCorFundo" />
      </template>

      <div class="mt-6 border-t border-outline-gray-1 pt-3">
        <div class="mb-2 text-p-sm font-medium text-ink-gray-7">{{ __('Camadas') }}</div>
        <div class="flex flex-col gap-1">
          <button
            v-for="(o, i) in camadas"
            :key="i"
            type="button"
            class="truncate rounded px-2 py-1 text-left text-p-sm"
            :class="o.ativo ? 'bg-surface-gray-3 text-ink-gray-9' : 'text-ink-gray-6 hover:bg-surface-gray-2'"
            @click="selecionarCamada(i)"
          >
            {{ o.rotulo }}
          </button>
          <div v-if="!camadas.length" class="text-p-sm text-ink-gray-4">{{ __('Nenhum elemento ainda.') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LucideType from '~icons/lucide/type'
import LucideImage from '~icons/lucide/image'
import LucideSquare from '~icons/lucide/square'
import LucideTrash2 from '~icons/lucide/trash-2'
import { Button, FormControl, call } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Canvas, Textbox, Rect, FabricImage, Circle } from 'fabric'

const props = defineProps({
  conversa: { type: String, required: true },
  indice: { type: Number, required: true },
  slide: { type: Object, required: true },
  tipo: { type: String, default: 'Carrossel' },
  modelo: { type: String, default: 'padrao' },
  corMarca: { type: String, default: '#042d3c' },
  corDestaque: { type: String, default: '#8aa1a9' },
  corNeutra: { type: String, default: '#f4f2ed' },
  nomeMarca: { type: String, default: '' },
})

const TAMANHOS = {
  Post: { w: 1080, h: 1080 },
  Carrossel: { w: 1080, h: 1080 },
  Story: { w: 1080, h: 1920 },
}
const ESCALA_TELA = 0.37

const fontes = [
  { label: 'Arial', value: 'Arial' },
  { label: 'Georgia', value: 'Georgia' },
  { label: 'Helvetica', value: 'Helvetica' },
  { label: 'Times New Roman', value: 'Times New Roman' },
  { label: 'Verdana', value: 'Verdana' },
  { label: 'Courier New', value: 'Courier New' },
]

const canvasEl = ref(null)
const fileInput = ref(null)
const objetoSelecionado = ref(null)
const camadas = ref([])
const salvando = ref(false)
const corFundoAtual = ref(props.corMarca)
const paletaFundo = computed(() => [
  { cor: '#ffffff', rotulo: __('Branco') },
  { cor: props.corMarca, rotulo: __('Cor principal') },
  { cor: props.corDestaque, rotulo: __('Cor de destaque') },
  { cor: props.corNeutra, rotulo: __('Cor neutra') },
])
const propTexto = ref({ fontFamily: 'Arial', fontSize: 32, fill: '#ffffff' })
const propForma = ref({ fill: '#ffffff' })

let canvas = null
let alvoUpload = null

function rotuloObjeto(o) {
  if (o.type === 'textbox') return (o.text || __('Texto')).slice(0, 24)
  if (o.type === 'image') return __('Imagem')
  if (o.type === 'rect') return __('Forma')
  return o.type
}

function atualizarCamadas() {
  if (!canvas) return
  camadas.value = canvas.getObjects().map((o) => ({
    rotulo: rotuloObjeto(o),
    ativo: o === canvas.getActiveObject(),
  }))
}

function aoSelecionar() {
  const obj = canvas.getActiveObject()
  objetoSelecionado.value = obj || null
  if (obj?.type === 'textbox') {
    propTexto.value = { fontFamily: obj.fontFamily || 'Arial', fontSize: obj.fontSize || 32, fill: obj.fill || '#ffffff' }
  } else if (obj?.type === 'rect') {
    propForma.value = { fill: obj.fill || '#ffffff' }
  }
  atualizarCamadas()
}

function aoLimparSelecao() {
  objetoSelecionado.value = null
  atualizarCamadas()
}

function montarPadrao() {
  const { w, h } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  canvas.setDimensions({ width: w, height: h })
  canvas.backgroundColor = props.corMarca
  corFundoAtual.value = props.corMarca

  const titulo = new Textbox(props.slide.titulo || '', {
    left: w * 0.08, top: h * 0.32, width: w * 0.84,
    fontSize: Math.round(w * 0.075), fontWeight: 'bold', fontFamily: 'Arial',
    fill: '#ffffff',
  })
  const corpo = new Textbox(props.slide.corpo || '', {
    left: w * 0.08, top: h * 0.32 + Math.round(w * 0.075) * 2 + 30, width: w * 0.84,
    fontSize: Math.round(w * 0.035), fontFamily: 'Arial',
    fill: props.corDestaque,
  })
  canvas.add(titulo, corpo)
  if (props.nomeMarca) {
    const marca = new Textbox(props.nomeMarca, {
      left: w * 0.08, top: h * 0.06, width: w * 0.6,
      fontSize: Math.round(w * 0.03), fontFamily: 'Arial', fill: '#ffffff',
    })
    canvas.add(marca)
  }
  canvas.renderAll()
}

// Modelo "estilo Twitter": avatar + nome da marca no topo, título e texto,
// espaço de imagem arredondado embaixo - pra colar a foto (upload) por cima.
function montarTwitter() {
  const { w, h } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  canvas.setDimensions({ width: w, height: h })
  canvas.backgroundColor = props.corMarca
  corFundoAtual.value = props.corMarca

  const raioAvatar = w * 0.045
  const avatar = new Circle({ left: w * 0.08, top: h * 0.08, radius: raioAvatar, fill: '#ffffff' })
  canvas.add(avatar)

  const handle = new Textbox(props.nomeMarca || __('sua marca'), {
    left: w * 0.08 + raioAvatar * 2 + 16, top: h * 0.08,
    width: w * 0.6, fontSize: Math.round(w * 0.032), fontWeight: 'bold', fontFamily: 'Arial', fill: '#ffffff',
  })
  const tagline = new Textbox(__('marketing jurídico'), {
    left: w * 0.08 + raioAvatar * 2 + 16, top: h * 0.08 + Math.round(w * 0.032) + 8,
    width: w * 0.6, fontSize: Math.round(w * 0.024), fontFamily: 'Arial', fill: props.corDestaque,
  })
  canvas.add(handle, tagline)

  const titulo = new Textbox(props.slide.titulo || '', {
    left: w * 0.08, top: h * 0.22, width: w * 0.84,
    fontSize: Math.round(w * 0.062), fontWeight: 'bold', fontFamily: 'Arial', fill: '#ffffff',
  })
  const corpo = new Textbox(props.slide.corpo || '', {
    left: w * 0.08, top: h * 0.22 + Math.round(w * 0.062) * 2.5 + 20, width: w * 0.84,
    fontSize: Math.round(w * 0.032), fontFamily: 'Arial', fill: '#c7d3d6',
  })
  canvas.add(titulo, corpo)

  const espacoImagem = new Rect({
    left: w * 0.08, top: h * 0.6, width: w * 0.84, height: h * 0.34, rx: 18, ry: 18,
    fill: '#ffffff', opacity: 0.15,
  })
  canvas.add(espacoImagem)
  canvas.renderAll()
}

// Modelo "citação clara": fundo branco, título na cor de destaque, texto cinza,
// espaço de imagem arredondado embaixo.
function montarCitacao() {
  const { w, h } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  canvas.setDimensions({ width: w, height: h })
  canvas.backgroundColor = '#ffffff'
  corFundoAtual.value = '#ffffff'

  const titulo = new Textbox(props.slide.titulo || '', {
    left: w * 0.09, top: h * 0.08, width: w * 0.82,
    fontSize: Math.round(w * 0.062), fontWeight: 'bold', fontFamily: 'Arial', fill: props.corDestaque,
  })
  const corpo = new Textbox(props.slide.corpo || '', {
    left: w * 0.09, top: h * 0.08 + Math.round(w * 0.062) * 2.3 + 24, width: w * 0.82,
    fontSize: Math.round(w * 0.034), fontFamily: 'Arial', fill: '#666666',
  })
  canvas.add(titulo, corpo)

  const espacoImagem = new Rect({
    left: w * 0.09, top: h * 0.52, width: w * 0.82, height: h * 0.4, rx: 14, ry: 14,
    fill: '#e4e4e4',
  })
  canvas.add(espacoImagem)
  canvas.renderAll()
}

async function montarCanvas() {
  const { w, h } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  if (props.slide.canvas) {
    await canvas.loadFromJSON(props.slide.canvas)
    canvas.setDimensions({ width: props.slide.canvas.width || w, height: props.slide.canvas.height || h })
    corFundoAtual.value = canvas.backgroundColor || props.corMarca
    canvas.renderAll()
  } else if (props.modelo === 'twitter') {
    montarTwitter()
  } else if (props.modelo === 'citacao') {
    montarCitacao()
  } else {
    montarPadrao()
  }
  atualizarCamadas()
}

onMounted(() => {
  canvas = new Canvas(canvasEl.value, {
    width: TAMANHOS[props.tipo]?.w || 1080,
    height: TAMANHOS[props.tipo]?.h || 1080,
  })
  canvas.setZoom(ESCALA_TELA)
  canvas.setDimensions(
    { width: (TAMANHOS[props.tipo]?.w || 1080) * ESCALA_TELA, height: (TAMANHOS[props.tipo]?.h || 1080) * ESCALA_TELA },
    { cssOnly: true },
  )
  canvas.on('selection:created', aoSelecionar)
  canvas.on('selection:updated', aoSelecionar)
  canvas.on('selection:cleared', aoLimparSelecao)
  canvas.on('object:modified', atualizarCamadas)
  montarCanvas()
})

onBeforeUnmount(() => {
  canvas?.dispose()
})

watch(() => [props.conversa, props.indice], () => {
  if (!canvas) return
  objetoSelecionado.value = null
  canvas.clear()
  montarCanvas()
})

function adicionarTexto() {
  const { w } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  const t = new Textbox(__('Novo texto'), { left: w * 0.1, top: w * 0.1, width: w * 0.6, fontSize: Math.round(w * 0.04), fill: '#ffffff', fontFamily: 'Arial' })
  canvas.add(t)
  canvas.setActiveObject(t)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarForma() {
  const { w } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  const r = new Rect({ left: w * 0.1, top: w * 0.1, width: w * 0.3, height: w * 0.2, fill: props.corDestaque })
  canvas.add(r)
  canvas.setActiveObject(r)
  canvas.renderAll()
  atualizarCamadas()
}

function removerSelecionado() {
  if (!objetoSelecionado.value) return
  canvas.remove(objetoSelecionado.value)
  canvas.discardActiveObject()
  canvas.renderAll()
  aoLimparSelecao()
}

function abrirUpload(alvo) {
  alvoUpload = alvo
  fileInput.value?.click()
}

async function onFileSelecionado(ev) {
  const file = ev.target.files?.[0]
  ev.target.value = ''
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '0')
  const resp = await fetch('/api/method/upload_file', {
    method: 'POST',
    headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    body: formData,
  })
  const data = await resp.json()
  const url = data?.message?.file_url
  if (!url) return
  const img = await FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
  const { w } = TAMANHOS[props.tipo] || TAMANHOS.Carrossel
  if (alvoUpload && alvoUpload.type === 'image') {
    img.set({ left: alvoUpload.left, top: alvoUpload.top, scaleX: alvoUpload.scaleX, scaleY: alvoUpload.scaleY })
    canvas.remove(alvoUpload)
    canvas.add(img)
    canvas.setActiveObject(img)
  } else {
    img.scaleToWidth(w * 0.5)
    img.set({ left: w * 0.25, top: w * 0.25 })
    canvas.add(img)
    canvas.setActiveObject(img)
  }
  canvas.renderAll()
  atualizarCamadas()
}

function aplicarFonte() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  objetoSelecionado.value.set({ fontFamily: propTexto.value.fontFamily })
  canvas.renderAll()
}
function aplicarTamanho() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  objetoSelecionado.value.set({ fontSize: Number(propTexto.value.fontSize) || 32 })
  canvas.renderAll()
}
function aplicarCorTexto() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  objetoSelecionado.value.set({ fill: propTexto.value.fill })
  canvas.renderAll()
}
function aplicarCorForma() {
  if (objetoSelecionado.value?.type !== 'rect') return
  objetoSelecionado.value.set({ fill: propForma.value.fill })
  canvas.renderAll()
}
function aplicarCorFundo() {
  canvas.backgroundColor = corFundoAtual.value
  canvas.renderAll()
}

function selecionarCamada(i) {
  const obj = canvas.getObjects()[i]
  if (!obj) return
  canvas.setActiveObject(obj)
  canvas.renderAll()
  aoSelecionar()
}

function baixarPng() {
  const url = canvas.toDataURL({ format: 'png', multiplier: 1 / ESCALA_TELA })
  const a = document.createElement('a')
  a.href = url
  a.download = `slide-${props.indice + 1}.png`
  a.click()
}

const emit = defineEmits(['salvo'])

async function salvar() {
  salvando.value = true
  try {
    await call('crm.api.conteudo.salvar_slide', {
      conversa: props.conversa,
      indice: props.indice,
      canvas: JSON.stringify(canvas.toJSON()),
    })
    emit('salvo')
  } finally {
    salvando.value = false
  }
}

defineExpose({ salvar })
</script>
