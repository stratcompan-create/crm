<template>
  <div class="flex min-h-0 flex-1">
    <!-- Canvas -->
    <div class="flex flex-1 flex-col items-center gap-4 overflow-auto bg-gradient-to-b from-surface-gray-1 to-surface-gray-2 p-8">
      <div class="rounded-lg shadow-lg ring-1 ring-black/5 transition-shadow duration-300 hover:shadow-xl">
        <canvas ref="canvasEl" class="rounded-lg" />
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :label="__('Baixar PNG')" @click="baixarPng" />
        <Button variant="solid" size="sm" :label="__('Salvar')" :loading="salvando" @click="salvar" />
      </div>
    </div>
    <!-- Painel de edição -->
    <div class="flex w-72 shrink-0 flex-col overflow-y-auto border-l border-outline-gray-1 p-3">
      <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Adicionar') }}</div>
      <div class="mb-4 flex gap-2">
        <button
          type="button"
          class="flex flex-1 flex-col items-center gap-1 rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 transition-all duration-150 hover:-translate-y-0.5 hover:text-white hover:shadow-sm"
          @mouseenter="$event.currentTarget.style.background = corDestaque"
          @mouseleave="$event.currentTarget.style.background = ''"
          @click="adicionarTexto"
        >
          <LucideType class="size-4" />
          <span class="text-[10px]">{{ __('Texto') }}</span>
        </button>
        <button
          type="button"
          class="flex flex-1 flex-col items-center gap-1 rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 transition-all duration-150 hover:-translate-y-0.5 hover:text-white hover:shadow-sm"
          @mouseenter="$event.currentTarget.style.background = corDestaque"
          @mouseleave="$event.currentTarget.style.background = ''"
          @click="abrirUpload(null)"
        >
          <LucideImage class="size-4" />
          <span class="text-[10px]">{{ __('Imagem') }}</span>
        </button>
        <button
          type="button"
          class="flex flex-1 flex-col items-center gap-1 rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 transition-all duration-150 hover:-translate-y-0.5 hover:text-white hover:shadow-sm"
          @mouseenter="$event.currentTarget.style.background = corDestaque"
          @mouseleave="$event.currentTarget.style.background = ''"
          @click="adicionarForma"
        >
          <LucideSquare class="size-4" />
          <span class="text-[10px]">{{ __('Forma') }}</span>
        </button>
      </div>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileSelecionado" />

      <!-- Texto & IA -->
      <div class="border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.texto = !secoes.texto">
          {{ __('Texto & IA') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.texto ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.texto" class="flex flex-col gap-2">
          <FormControl type="textarea" :label="__('Título')" :rows="2" v-model="tituloEdit" @update:modelValue="aoEditarTexto" />
          <FormControl type="textarea" :label="__('Subtítulo')" :rows="3" v-model="corpoEdit" @update:modelValue="aoEditarTexto" />
          <Button
            class="mt-1"
            variant="outline"
            size="sm"
            :label="__('Gerar conteúdo deste slide com IA')"
            :loading="gerandoConteudo"
            @click="gerarConteudoSlide"
          />
          <div class="mt-2">
            <FormControl type="textarea" :rows="2" :placeholder="__('Ex.: deixe mais curto, tom mais direto...')" v-model="instrucaoRefinar" />
            <Button class="mt-1 w-full" variant="ghost" size="sm" :label="__('Refinar slide com IA')" :loading="refinando" @click="refinarSlide" />
          </div>
        </div>
      </div>

      <!-- Layout do texto -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.layout = !secoes.layout">
          {{ __('Layout do texto') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.layout ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.layout" class="flex flex-col gap-3">
          <div>
            <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Posição') }}</div>
            <div class="grid grid-cols-3 gap-1">
              <button
                v-for="p in POSICOES"
                :key="p.valor"
                type="button"
                class="rounded border px-1 py-1.5 text-[10px]"
                :class="layoutAtual.posicao === p.valor ? 'border-ink-gray-9 bg-surface-gray-3 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2'"
                @click="atualizarLayout({ posicao: p.valor })"
              >
                {{ p.rotulo }}
              </button>
            </div>
          </div>
          <label class="flex items-center justify-between text-p-sm text-ink-gray-6">
            {{ __('Glass ao redor do conteúdo') }}
            <input type="checkbox" :checked="layoutAtual.glass" @change="atualizarLayout({ glass: $event.target.checked })" />
          </label>
          <FormControl
            type="number"
            :label="__('Margem horizontal — {0}%', [layoutAtual.margemH])"
            :model-value="layoutAtual.margemH"
            @update:modelValue="(v) => atualizarLayout({ margemH: Number(v) || 0 })"
          />
          <FormControl
            type="number"
            :label="__('Margem vertical — {0}%', [layoutAtual.margemV])"
            :model-value="layoutAtual.margemV"
            @update:modelValue="(v) => atualizarLayout({ margemV: Number(v) || 0 })"
          />
          <Button variant="outline" size="sm" :label="__('Aplicar configurações no próximo slide')" @click="aplicarNoProximo" />
        </div>
      </div>

      <!-- Sombra / Overlay -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.sombra = !secoes.sombra">
          {{ __('Sombra / Overlay') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.sombra ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.sombra" class="flex flex-col gap-2">
          <FormControl
            type="select"
            :label="__('Estilo')"
            :model-value="layoutAtual.sombraEstilo"
            :options="SOMBRA_ESTILOS.map((s) => ({ label: s.rotulo, value: s.valor }))"
            @update:modelValue="(v) => atualizarLayout({ sombraEstilo: v })"
          />
          <FormControl
            type="number"
            :label="__('Opacidade — {0}%', [layoutAtual.sombraOpacidade])"
            :model-value="layoutAtual.sombraOpacidade"
            @update:modelValue="(v) => atualizarLayout({ sombraOpacidade: Number(v) || 0 })"
          />
        </div>
      </div>

      <!-- Fundo do slide -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.fundo = !secoes.fundo">
          {{ __('Fundo do slide') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.fundo ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.fundo" class="flex flex-col gap-2">
          <div class="mb-1 flex flex-wrap gap-2">
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
          <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="corFundoAtual" @input="aplicarCorFundo" />
          <FormControl
            type="select"
            :label="__('Padrão sobre o fundo')"
            :model-value="layoutAtual.fundoPadrao"
            :options="FUNDO_PADROES.map((f) => ({ label: f.rotulo, value: f.valor }))"
            @update:modelValue="(v) => atualizarLayout({ fundoPadrao: v })"
          />
        </div>
      </div>

      <!-- Tipografia -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.tipografia = !secoes.tipografia">
          {{ __('Tipografia') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.tipografia ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.tipografia" class="flex flex-col gap-2">
          <FormControl
            type="number"
            :label="__('Escala geral — {0}%', [layoutAtual.escala])"
            :model-value="layoutAtual.escala"
            @update:modelValue="(v) => atualizarLayout({ escala: Number(v) || 100 })"
          />
          <FormControl
            type="number"
            :label="__('Espaçamento entre linhas — {0}%', [layoutAtual.espacamento])"
            :model-value="layoutAtual.espacamento"
            @update:modelValue="(v) => atualizarLayout({ espacamento: Number(v) || 115 })"
          />
          <FormControl
            type="select"
            :label="__('Fonte do título')"
            :model-value="layoutAtual.fonteTitulo"
            :options="opcoesFontes"
            @update:modelValue="(v) => atualizarLayout({ fonteTitulo: v })"
          />
          <FormControl
            type="select"
            :label="__('Fonte do subtítulo')"
            :model-value="layoutAtual.fonteCorpo"
            :options="opcoesFontes"
            @update:modelValue="(v) => atualizarLayout({ fonteCorpo: v })"
          />
        </div>
      </div>

      <!-- Propriedades do objeto selecionado (elementos adicionados manualmente) -->
      <div v-if="objetoSelecionado" class="mt-4 border-t border-outline-gray-1 pt-3">
        <template v-if="objetoSelecionado.type === 'textbox' && objetoSelecionado.papel !== 'titulo' && objetoSelecionado.papel !== 'corpo'">
          <div class="mb-3 flex items-center justify-between">
            <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Texto selecionado') }}</div>
            <button type="button" class="flex items-center gap-1 rounded px-1 py-0.5 text-red-500 hover:bg-red-50" @click="removerSelecionado">
              <LucideTrash2 class="size-3.5" />
            </button>
          </div>
          <div class="flex flex-col gap-2">
            <FormControl type="select" :label="__('Fonte')" v-model="propTexto.fontFamily" :options="opcoesFontes" @update:modelValue="aplicarFonte" />
            <FormControl type="number" :label="__('Tamanho')" v-model="propTexto.fontSize" @update:modelValue="aplicarTamanho" />
            <div>
              <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Cor') }}</div>
              <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="propTexto.fill" @input="aplicarCorTexto" />
            </div>
          </div>
        </template>
        <template v-else-if="objetoSelecionado.type === 'rect' && objetoSelecionado.papel !== 'glass'">
          <div class="mb-3 flex items-center justify-between">
            <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Forma selecionada') }}</div>
            <button type="button" class="flex items-center gap-1 rounded px-1 py-0.5 text-red-500 hover:bg-red-50" @click="removerSelecionado">
              <LucideTrash2 class="size-3.5" />
            </button>
          </div>
          <div>
            <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Cor') }}</div>
            <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="propForma.fill" @input="aplicarCorForma" />
          </div>
        </template>
        <template v-else-if="objetoSelecionado.type === 'image'">
          <div class="mb-3 flex items-center justify-between">
            <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Imagem') }}</div>
            <button type="button" class="flex items-center gap-1 rounded px-1 py-0.5 text-red-500 hover:bg-red-50" @click="removerSelecionado">
              <LucideTrash2 class="size-3.5" />
            </button>
          </div>
          <Button variant="outline" size="sm" class="w-full" :label="__('Trocar imagem')" @click="abrirUpload(objetoSelecionado)" />
        </template>
      </div>

      <!-- Camadas -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
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
import LucideChevronDown from '~icons/lucide/chevron-down'
import { Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Canvas, Textbox, Rect, FabricImage } from 'fabric'
import {
  TAMANHOS, POSICOES, FUNDO_PADROES, SOMBRA_ESTILOS, FONTES,
  layoutPadraoDe, corDeFundo, construirSlide, construirBlocoTexto,
  aplicarPadraoFundo, aplicarSombra, estiloTextoPara,
} from '@/utils/instagramTemplates'

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
const emit = defineEmits(['salvo', 'aplicar-layout-proximo'])

const PROPRIEDADES_EXTRA = ['papel']

const canvasEl = ref(null)
const fileInput = ref(null)
const objetoSelecionado = ref(null)
const camadas = ref([])
const salvando = ref(false)
const gerandoConteudo = ref(false)
const refinando = ref(false)
const instrucaoRefinar = ref('')
const tituloEdit = ref(props.slide.titulo || '')
const corpoEdit = ref(props.slide.corpo || '')
const corFundoAtual = ref(props.corMarca)
const secoes = reactive({ texto: true, layout: false, sombra: false, fundo: false, tipografia: false })

const layoutAtual = reactive({ ...layoutPadraoDe(props.modelo), ...(props.slide.layout || {}) })

const paletaFundo = computed(() => [
  { cor: '#ffffff', rotulo: __('Branco') },
  { cor: props.corMarca, rotulo: __('Cor principal') },
  { cor: props.corDestaque, rotulo: __('Cor de destaque') },
  { cor: props.corNeutra, rotulo: __('Cor neutra') },
])
const propTexto = ref({ fontFamily: 'Poppins', fontSize: 32, fill: '#ffffff' })
const propForma = ref({ fill: '#ffffff' })
const opcoesFontes = FONTES.map((f) => ({ label: f, value: f }))

let canvas = null
let alvoUpload = null

function tamanhoAtivo() {
  return TAMANHOS[props.tipo] || TAMANHOS.Carrossel
}

function rotuloObjeto(o) {
  if (o.papel === 'titulo') return __('Título')
  if (o.papel === 'corpo') return __('Subtítulo')
  if (o.type === 'textbox') return (o.text || __('Texto')).slice(0, 24)
  if (o.type === 'image') return __('Imagem')
  if (o.type === 'rect') return __('Forma')
  return o.type
}

function atualizarCamadas() {
  if (!canvas) return
  camadas.value = canvas.getObjects()
    .filter((o) => !['padrao-fundo', 'sombra'].includes(o.papel))
    .map((o) => ({ obj: o, rotulo: rotuloObjeto(o), ativo: o === canvas.getActiveObject() }))
}

function aoSelecionar() {
  const obj = canvas.getActiveObject()
  objetoSelecionado.value = obj || null
  if (obj?.type === 'textbox') {
    propTexto.value = { fontFamily: obj.fontFamily || 'Poppins', fontSize: obj.fontSize || 32, fill: obj.fill || '#ffffff' }
  } else if (obj?.type === 'rect') {
    propForma.value = { fill: obj.fill || '#ffffff' }
  }
  atualizarCamadas()
}

function aoLimparSelecao() {
  objetoSelecionado.value = null
  atualizarCamadas()
}

async function montarCanvas() {
  // espera as fontes carregarem de verdade antes de desenhar - sem isso o
  // canvas as vezes renderiza com a fonte padrao do navegador
  await document.fonts.ready
  const { w, h } = tamanhoAtivo()
  if (props.slide.canvas) {
    await canvas.loadFromJSON(props.slide.canvas)
    canvas.setDimensions({ width: props.slide.canvas.width || w, height: props.slide.canvas.height || h })
    corFundoAtual.value = canvas.backgroundColor || props.corMarca
    canvas.renderAll()
  } else {
    construirSlide(canvas, {
      tipo: props.tipo, modelo: props.modelo, slide: props.slide,
      corMarca: props.corMarca, corDestaque: props.corDestaque, corNeutra: props.corNeutra, nomeMarca: props.nomeMarca,
    })
    corFundoAtual.value = corDeFundo(props.modelo, props.corMarca)
  }
  atualizarCamadas()
}

onMounted(() => {
  canvas = new Canvas(canvasEl.value, { width: tamanhoAtivo().w, height: tamanhoAtivo().h })
  const escalaTela = 0.37
  canvas.setZoom(escalaTela)
  canvas.setDimensions({ width: tamanhoAtivo().w * escalaTela, height: tamanhoAtivo().h * escalaTela }, { cssOnly: true })
  canvas._escalaTela = escalaTela
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
  tituloEdit.value = props.slide.titulo || ''
  corpoEdit.value = props.slide.corpo || ''
  instrucaoRefinar.value = ''
  Object.assign(layoutAtual, layoutPadraoDe(props.modelo), props.slide.layout || {})
  canvas.clear()
  montarCanvas()
})

// ------------------------------------------------------------------ texto & IA

function aoEditarTexto() {
  props.slide.titulo = tituloEdit.value
  props.slide.corpo = corpoEdit.value
  delete props.slide.canvas
  reaplicarTexto()
}

async function gerarConteudoSlide() {
  gerandoConteudo.value = true
  try {
    const r = await call('crm.api.conteudo.gerar_texto_slide', { conversa: props.conversa, indice: props.indice })
    props.slide.titulo = r.titulo
    props.slide.corpo = r.corpo
    delete props.slide.canvas
    tituloEdit.value = r.titulo
    corpoEdit.value = r.corpo
    reaplicarTexto()
  } catch (e) {
    toast.error(e.messages?.join(', ') || e.message || __('Não consegui gerar agora.'))
  } finally {
    gerandoConteudo.value = false
  }
}

async function refinarSlide() {
  if (!instrucaoRefinar.value.trim()) return
  refinando.value = true
  try {
    const r = await call('crm.api.conteudo.gerar_texto_slide', {
      conversa: props.conversa, indice: props.indice, instrucao: instrucaoRefinar.value,
    })
    props.slide.titulo = r.titulo
    props.slide.corpo = r.corpo
    delete props.slide.canvas
    tituloEdit.value = r.titulo
    corpoEdit.value = r.corpo
    instrucaoRefinar.value = ''
    reaplicarTexto()
  } catch (e) {
    toast.error(e.messages?.join(', ') || e.message || __('Não consegui refinar agora.'))
  } finally {
    refinando.value = false
  }
}

// ------------------------------------------------------------------ layout (reaplica sem apagar elementos manuais)

function removerPorPapel(...papeis) {
  canvas.getObjects().filter((o) => papeis.includes(o.papel)).forEach((o) => canvas.remove(o))
}

function reaplicarTexto() {
  if (!canvas) return
  removerPorPapel('titulo', 'corpo', 'glass')
  const { w, h } = tamanhoAtivo()
  construirBlocoTexto(canvas, {
    slide: props.slide, layout: layoutAtual, w, h,
    ...estiloTextoPara(props.modelo, props.corDestaque, w, h),
  })
  canvas.renderAll()
  atualizarCamadas()
}

function reaplicarFundoPadrao() {
  if (!canvas) return
  removerPorPapel('padrao-fundo')
  const { w, h } = tamanhoAtivo()
  aplicarPadraoFundo(canvas, { padrao: layoutAtual.fundoPadrao, w, h, clara: props.modelo === 'citacao' })
  canvas.renderAll()
}

function reaplicarSombra() {
  if (!canvas) return
  removerPorPapel('sombra')
  const { w, h } = tamanhoAtivo()
  aplicarSombra(canvas, { estilo: layoutAtual.sombraEstilo, opacidade: layoutAtual.sombraOpacidade, w, h })
  canvas.renderAll()
}

function atualizarLayout(mudancas) {
  Object.assign(layoutAtual, mudancas)
  props.slide.layout = { ...layoutAtual }
  if ('fundoPadrao' in mudancas) reaplicarFundoPadrao()
  if ('sombraEstilo' in mudancas || 'sombraOpacidade' in mudancas) reaplicarSombra()
  reaplicarTexto()
}

function aplicarNoProximo() {
  emit('aplicar-layout-proximo', { indice: props.indice, layout: { ...layoutAtual } })
  toast.success(__('Layout aplicado no próximo slide'))
}

// ------------------------------------------------------------------ ferramentas gerais

function adicionarTexto() {
  const { w } = tamanhoAtivo()
  const t = new Textbox(__('Novo texto'), { left: w * 0.1, top: w * 0.1, width: w * 0.6, fontSize: Math.round(w * 0.04), fill: '#ffffff', fontFamily: 'Poppins' })
  canvas.add(t)
  canvas.setActiveObject(t)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarForma() {
  const { w } = tamanhoAtivo()
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
  const { w } = tamanhoAtivo()
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
  const obj = camadas.value[i]?.obj
  if (!obj) return
  canvas.setActiveObject(obj)
  canvas.renderAll()
  aoSelecionar()
}

function baixarPng() {
  const url = canvas.toDataURL({ format: 'png', multiplier: 1 / canvas._escalaTela })
  const a = document.createElement('a')
  a.href = url
  a.download = `slide-${props.indice + 1}.png`
  a.click()
}

async function salvar() {
  salvando.value = true
  try {
    await call('crm.api.conteudo.salvar_slide', {
      conversa: props.conversa,
      indice: props.indice,
      canvas: JSON.stringify(canvas.toObject(PROPRIEDADES_EXTRA)),
      titulo: props.slide.titulo || '',
      corpo: props.slide.corpo || '',
      layout: JSON.stringify(layoutAtual),
    })
    emit('salvo')
  } finally {
    salvando.value = false
  }
}

defineExpose({ salvar })
</script>
