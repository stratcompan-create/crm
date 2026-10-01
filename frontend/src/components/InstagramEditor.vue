<template>
  <div class="flex min-h-0 flex-1">
    <!-- Canvas -->
    <div ref="canvasArea" class="flex flex-1 flex-col items-center gap-4 overflow-auto bg-gradient-to-b from-surface-gray-1 to-surface-gray-2 p-8">
      <div class="rounded-lg shadow-lg ring-1 ring-black/5 transition-shadow duration-300 hover:shadow-xl">
        <canvas ref="canvasEl" class="rounded-lg" />
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="flex size-8 items-center justify-center rounded-lg border border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2 disabled:cursor-not-allowed disabled:opacity-40"
          :title="__('Desfazer última alteração')"
          :disabled="!podeDesfazer"
          @click="desfazer"
        >
          <LucideUndo2 class="size-4" />
        </button>
        <Button variant="outline" size="sm" :label="__('Baixar PNG')" @click="baixarPng" />
        <Button variant="solid" size="sm" :label="__('Salvar')" :loading="salvando" @click="salvar" />
      </div>
    </div>
    <!-- Painel de edição -->
    <div class="flex w-72 shrink-0 flex-col overflow-y-auto border-l border-outline-gray-1 p-3">
      <div class="mb-3 text-p-sm font-medium text-ink-gray-7">{{ __('Adicionar') }}</div>
      <div class="mb-3 flex gap-2">
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
      <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Elementos') }}</div>
      <div class="mb-4 grid grid-cols-4 gap-2">
        <button type="button" class="flex items-center justify-center rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 hover:bg-surface-gray-2" :title="__('Seta')" @click="adicionarSeta">
          <LucideArrowRight class="size-4" />
        </button>
        <button type="button" class="flex items-center justify-center rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 hover:bg-surface-gray-2" :title="__('Aspas')" @click="adicionarAspas">
          <LucideQuote class="size-4" />
        </button>
        <button type="button" class="flex items-center justify-center rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 hover:bg-surface-gray-2" :title="__('Numeração')" @click="adicionarNumeracao">
          <LucideListOrdered class="size-4" />
        </button>
        <button type="button" class="flex items-center justify-center rounded-lg border border-outline-gray-2 p-2 text-ink-gray-6 hover:bg-surface-gray-2" :title="__('Estrela')" @click="adicionarEstrela">
          <LucideStar class="size-4" />
        </button>
      </div>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileSelecionado" />
      <input ref="fileInputExtra" type="file" accept="image/*" class="hidden" @change="onFileSelecionadoExtra" />

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
          <div class="mt-1 text-p-sm text-ink-gray-6">{{ __('Aplicar estas configurações em:') }}</div>
          <div class="flex gap-2">
            <Button class="flex-1" variant="outline" size="sm" :label="__('Próximo slide')" @click="aplicarNoProximo" />
            <Button class="flex-1" variant="outline" size="sm" :label="__('Todos')" @click="aplicarEmTodos" />
          </div>
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
          <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Outra cor (clique pra escolher qualquer uma)') }}</div>
          <input type="color" class="h-8 w-full cursor-pointer rounded border border-outline-gray-2" v-model="corFundoAtual" @input="aplicarCorFundo" />
          <FormControl
            type="select"
            :label="__('Padrão sobre o fundo')"
            :model-value="layoutAtual.fundoPadrao"
            :options="FUNDO_PADROES.map((f) => ({ label: f.rotulo, value: f.valor }))"
            @update:modelValue="(v) => atualizarLayout({ fundoPadrao: v })"
          />
          <label class="flex items-center justify-between text-p-sm text-ink-gray-6">
            {{ __('Gradiente') }}
            <input type="checkbox" :checked="layoutAtual.fundoGradiente" @change="atualizarLayout({ fundoGradiente: $event.target.checked })" />
          </label>
          <div v-if="layoutAtual.fundoGradiente">
            <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Segunda cor do gradiente') }}</div>
            <input
              type="color"
              class="h-8 w-full cursor-pointer rounded border border-outline-gray-2"
              :value="layoutAtual.fundoCor2 || corDestaque"
              @input="atualizarLayout({ fundoCor2: $event.target.value })"
            />
          </div>
          <div class="mt-1 text-p-sm text-ink-gray-6">{{ __('Imagem de fundo (cobre o slide inteiro)') }}</div>
          <div class="flex gap-2">
            <Button
              class="flex-1" variant="outline" size="sm"
              :label="layoutAtual.fundoImagem ? __('Trocar imagem') : __('Adicionar imagem')"
              :loading="enviandoFundo"
              @click="abrirUploadFundo"
            />
            <Button v-if="layoutAtual.fundoImagem" variant="ghost" size="sm" :label="__('Remover')" @click="removerFundoImagem" />
          </div>
        </div>
      </div>

      <!-- Imagem da citação -->
      <div v-if="modelo === 'citacao'" class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.citacaoImagem = !secoes.citacaoImagem">
          {{ __('Imagem da citação') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.citacaoImagem ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.citacaoImagem" class="flex flex-col gap-2">
          <div class="flex gap-2">
            <Button
              class="flex-1" variant="outline" size="sm"
              :label="layoutAtual.citacaoImagem ? __('Trocar imagem') : __('Adicionar imagem')"
              :loading="enviandoCitacao"
              @click="abrirUploadCitacao"
            />
            <Button v-if="layoutAtual.citacaoImagem" variant="ghost" size="sm" :label="__('Remover')" @click="removerImagemCitacao" />
          </div>
          <div class="mb-1 text-p-sm text-ink-gray-6">{{ __('Posição da caixa') }}</div>
          <div class="grid grid-cols-2 gap-1">
            <button
              type="button" class="rounded border px-1 py-1.5 text-[10px]"
              :class="(layoutAtual.imagemPosicao || 'baixo') === 'cima' ? 'border-ink-gray-9 bg-surface-gray-3 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2'"
              @click="atualizarLayout({ imagemPosicao: 'cima' })"
            >
              {{ __('Em cima') }}
            </button>
            <button
              type="button" class="rounded border px-1 py-1.5 text-[10px]"
              :class="(layoutAtual.imagemPosicao || 'baixo') === 'baixo' ? 'border-ink-gray-9 bg-surface-gray-3 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2'"
              @click="atualizarLayout({ imagemPosicao: 'baixo' })"
            >
              {{ __('Embaixo') }}
            </button>
          </div>
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
          <label class="flex items-center justify-between text-p-sm text-ink-gray-6">
            {{ __('Contorno no texto') }}
            <input type="checkbox" :checked="layoutAtual.textoContorno" @change="atualizarLayout({ textoContorno: $event.target.checked })" />
          </label>
          <label class="flex items-center justify-between text-p-sm text-ink-gray-6">
            {{ __('Sombra no texto') }}
            <input type="checkbox" :checked="layoutAtual.textoSombra" @change="atualizarLayout({ textoSombra: $event.target.checked })" />
          </label>
        </div>
      </div>

      <!-- Logo -->
      <div class="mt-4 border-t border-outline-gray-1 pt-3">
        <button type="button" class="mb-2 flex w-full items-center justify-between text-p-sm font-medium text-ink-gray-7" @click="secoes.logo = !secoes.logo">
          {{ __('Logo') }}
          <LucideChevronDown class="size-3.5 transition-transform" :class="secoes.logo ? '' : '-rotate-90'" />
        </button>
        <div v-if="secoes.logo" class="flex flex-col gap-2">
          <div v-if="!logoUrl" class="text-p-sm text-ink-gray-4">
            {{ __('Configure o logo da marca em Configurações → Marca pra poder usar aqui.') }}
          </div>
          <template v-else>
            <label class="flex items-center justify-between text-p-sm text-ink-gray-6">
              {{ __('Logo automático no slide') }}
              <input type="checkbox" :checked="layoutAtual.logoAtivo" @change="atualizarLayout({ logoAtivo: $event.target.checked })" />
            </label>
            <div v-if="layoutAtual.logoAtivo" class="grid grid-cols-2 gap-1">
              <button
                v-for="p in POSICOES_LOGO"
                :key="p.valor"
                type="button"
                class="rounded border px-1 py-1.5 text-[10px]"
                :class="layoutAtual.logoPosicao === p.valor ? 'border-ink-gray-9 bg-surface-gray-3 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2'"
                @click="atualizarLayout({ logoPosicao: p.valor })"
              >
                {{ p.rotulo }}
              </button>
            </div>
          </template>
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
        <template v-else-if="(objetoSelecionado.type === 'rect' || objetoSelecionado.type === 'circle' || objetoSelecionado.type === 'polygon') && objetoSelecionado.papel !== 'glass'">
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
        <template v-else-if="objetoSelecionado.type === 'image' && objetoSelecionado.papel !== 'logo'">
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
import LucideUndo2 from '~icons/lucide/undo-2'
import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideArrowRight from '~icons/lucide/arrow-right'
import LucideQuote from '~icons/lucide/quote'
import LucideListOrdered from '~icons/lucide/list-ordered'
import LucideStar from '~icons/lucide/star'
import { Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Canvas, Textbox, Rect, Circle, Polygon, FabricImage, Line, Shadow } from 'fabric'
import {
  TAMANHOS, POSICOES, POSICOES_LOGO, FUNDO_PADROES, SOMBRA_ESTILOS, FONTES,
  layoutPadraoDe, corDeFundo, corFundoFinal, construirSlide, construirBlocoTexto,
  aplicarPadraoFundo, aplicarSombra, aplicarLogo, aplicarFundoImagem, aplicarImagemCitacao, elementosCitacao, estiloTextoPara,
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
  logoUrl: { type: String, default: '' },
})
const emit = defineEmits(['salvo', 'aplicar-layout-proximo', 'aplicar-layout-todos'])

const PROPRIEDADES_EXTRA = ['papel']

const canvasEl = ref(null)
const canvasArea = ref(null)
const fileInput = ref(null)
const fileInputExtra = ref(null)
const objetoSelecionado = ref(null)
const camadas = ref([])
const salvando = ref(false)
const gerandoConteudo = ref(false)
const refinando = ref(false)
const enviandoFundo = ref(false)
const enviandoCitacao = ref(false)
const instrucaoRefinar = ref('')
const tituloEdit = ref(props.slide.titulo || '')
const corpoEdit = ref(props.slide.corpo || '')
const corFundoAtual = ref(props.corMarca)
const secoes = reactive({ texto: true, layout: false, sombra: false, fundo: false, tipografia: false, logo: false, citacaoImagem: false })

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
let alvoExtra = null
let linhaGuiaV = null
let linhaGuiaH = null

// Desfazer: pilha de estados anteriores do canvas (só desse slide - zera ao
// trocar de slide). Cada ação "registra o passo" ANTES de mudar o canvas,
// guardando pra onde voltar; um debounce curto evita empilhar um passo por
// tecla digitada ou por cada pixel de um arrasto de slider.
let pilhaDesfazer = []
const LIMITE_DESFAZER = 25
const JANELA_DEBOUNCE_MS = 600
let ultimoRegistroDesfazer = 0
const podeDesfazer = ref(false)

function registrarPasso() {
  if (!canvas) return
  const agora = Date.now()
  if (agora - ultimoRegistroDesfazer < JANELA_DEBOUNCE_MS) return
  ultimoRegistroDesfazer = agora
  pilhaDesfazer.push(JSON.stringify(canvas.toObject(PROPRIEDADES_EXTRA)))
  if (pilhaDesfazer.length > LIMITE_DESFAZER) pilhaDesfazer.shift()
  podeDesfazer.value = true
}

async function desfazer() {
  if (!canvas || !pilhaDesfazer.length) return
  const estado = pilhaDesfazer.pop()
  await canvas.loadFromJSON(JSON.parse(estado))
  ajustarEscalaTela()
  canvas.renderAll()
  atualizarCamadas()
  const tituloObj = canvas.getObjects().find((o) => o.papel === 'titulo')
  const corpoObj = canvas.getObjects().find((o) => o.papel === 'corpo')
  if (tituloObj) { props.slide.titulo = tituloObj.text; tituloEdit.value = tituloObj.text }
  if (corpoObj) { props.slide.corpo = corpoObj.text; corpoEdit.value = corpoObj.text }
  podeDesfazer.value = pilhaDesfazer.length > 0
  // o próximo registro não deve respeitar o debounce do passo que acabou de ser desfeito
  ultimoRegistroDesfazer = 0
}

function tamanhoAtivo() {
  return TAMANHOS[props.tipo] || TAMANHOS.Carrossel
}

// Guias de alinhamento (igual Canva/Figma): quando o centro do elemento que
// está sendo arrastado chega perto do centro do card (na horizontal ou na
// vertical), gruda ali e mostra uma linha pontilhada - some ao soltar.
function limparGuias() {
  if (linhaGuiaV) { canvas.remove(linhaGuiaV); linhaGuiaV = null }
  if (linhaGuiaH) { canvas.remove(linhaGuiaH); linhaGuiaH = null }
}

function aoMoverObjeto(e) {
  const obj = e.target
  if (!obj) return
  limparGuias()
  const { w, h } = tamanhoAtivo()
  const limiar = Math.max(w, h) * 0.008
  const b = obj.getBoundingRect()
  const centroX = b.left + b.width / 2
  const centroY = b.top + b.height / 2
  const alvoX = w / 2
  const alvoY = h / 2

  if (Math.abs(centroX - alvoX) < limiar) {
    obj.left += alvoX - centroX
    linhaGuiaV = new Line([alvoX, 0, alvoX, h], {
      stroke: '#ff1744', strokeWidth: w * 0.006, strokeDashArray: [w * 0.014, w * 0.009],
      shadow: new Shadow({ color: 'rgba(255,23,68,.5)', blur: w * 0.01 }),
      selectable: false, evented: false, excludeFromExport: true, originX: 'left', originY: 'top',
    })
    canvas.add(linhaGuiaV)
  }
  if (Math.abs(centroY - alvoY) < limiar) {
    obj.top += alvoY - centroY
    linhaGuiaH = new Line([0, alvoY, w, alvoY], {
      stroke: '#ff1744', strokeWidth: w * 0.006, strokeDashArray: [w * 0.014, w * 0.009],
      shadow: new Shadow({ color: 'rgba(255,23,68,.5)', blur: w * 0.01 }),
      selectable: false, evented: false, excludeFromExport: true, originX: 'left', originY: 'top',
    })
    canvas.add(linhaGuiaH)
  }
  obj.setCoords()
  canvas.renderAll()
}

// Calcula o zoom pra caber no espaço disponível da tela (sem cortar o card nem
// deixar ele minúsculo), em vez de um zoom fixo que so funciona num tamanho de
// janela especifico.
function calcularEscala() {
  const { w, h } = tamanhoAtivo()
  const area = canvasArea.value
  const larguraDisponivel = (area?.clientWidth || 480) - 64
  const alturaDisponivel = (area?.clientHeight || 640) - 120
  const escala = Math.min(larguraDisponivel / w, alturaDisponivel / h, 0.9)
  return Math.max(escala, 0.1)
}

// Só encolhe o TAMANHO NA TELA (CSS) - a resolução real do canvas (onde os
// objetos são desenhados) nunca muda, o navegador só exibe o desenho cheio
// menor. NÃO usar canvas.setZoom aqui: zoom encolhe onde os objetos são
// desenhados DENTRO da resolução cheia (que continua do tamanho normal) -
// then o CSS encolhe de novo por cima, resultando no conteúdo espremido
// num cantinho e o resto do card em branco.
function ajustarEscalaTela() {
  if (!canvas) return
  const { w, h } = tamanhoAtivo()
  const escala = calcularEscala()
  canvas.setDimensions({ width: w * escala, height: h * escala }, { cssOnly: true })
}

function rotuloObjeto(o) {
  if (o.papel === 'titulo') return __('Título')
  if (o.papel === 'corpo') return __('Subtítulo')
  if (o.papel === 'logo') return __('Logo')
  if (o.type === 'textbox') return (o.text || __('Texto')).slice(0, 24)
  if (o.type === 'image') return __('Imagem')
  if (o.type === 'rect') return __('Forma')
  if (o.type === 'circle') return __('Círculo')
  if (o.type === 'polygon') return __('Elemento')
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
  } else if (obj?.type === 'rect' || obj?.type === 'circle' || obj?.type === 'polygon') {
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
    // loadFromJSON não mexe no tamanho do canvas (nem resolução real nem tela) -
    // só o zoom da tela precisa ser reaplicado depois, senão o card fica do
    // tamanho cheio (1080px) na tela em vez de caber no espaço disponível
    await canvas.loadFromJSON(props.slide.canvas)
    ajustarEscalaTela()
    corFundoAtual.value = layoutAtual.fundoCor || (typeof canvas.backgroundColor === 'string' ? canvas.backgroundColor : props.corMarca)
    canvas.renderAll()
  } else {
    construirSlide(canvas, {
      tipo: props.tipo, modelo: props.modelo, slide: props.slide,
      corMarca: props.corMarca, corDestaque: props.corDestaque, corNeutra: props.corNeutra, nomeMarca: props.nomeMarca,
    })
    ajustarEscalaTela()
    corFundoAtual.value = layoutAtual.fundoCor || corDeFundo(props.modelo, props.corMarca)
    if (layoutAtual.fundoImagem) {
      await aplicarFundoImagem(canvas, { url: layoutAtual.fundoImagem, w, h })
      canvas.renderAll()
    }
    if (props.modelo === 'citacao' && layoutAtual.citacaoImagem) {
      await aplicarImagemCitacao(canvas, { url: layoutAtual.citacaoImagem, posicao: layoutAtual.imagemPosicao, w, h })
      canvas.renderAll()
    }
    if (layoutAtual.logoAtivo && props.logoUrl) {
      await aplicarLogo(canvas, { logoUrl: props.logoUrl, posicao: layoutAtual.logoPosicao, w, h })
      canvas.renderAll()
    }
  }
  atualizarCamadas()
}

onMounted(() => {
  canvas = new Canvas(canvasEl.value, { width: tamanhoAtivo().w, height: tamanhoAtivo().h })
  ajustarEscalaTela()
  canvas.on('selection:created', aoSelecionar)
  canvas.on('selection:updated', aoSelecionar)
  canvas.on('selection:cleared', aoLimparSelecao)
  canvas.on('object:modified', atualizarCamadas)
  canvas.on('object:moving', aoMoverObjeto)
  canvas.on('object:modified', limparGuias)
  canvas.on('mouse:up', limparGuias)
  canvas.on('before:transform', registrarPasso)
  canvas.on('text:editing:entered', registrarPasso)
  montarCanvas()
  window.addEventListener('resize', ajustarEscalaTela)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', ajustarEscalaTela)
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
  pilhaDesfazer = []
  podeDesfazer.value = false
  ultimoRegistroDesfazer = 0
  montarCanvas()
})

// ------------------------------------------------------------------ texto & IA

function aoEditarTexto() {
  registrarPasso()
  props.slide.titulo = tituloEdit.value
  props.slide.corpo = corpoEdit.value
  delete props.slide.canvas
  reaplicarTexto()
}

async function gerarConteudoSlide() {
  gerandoConteudo.value = true
  try {
    const r = await call('crm.api.conteudo.gerar_texto_slide', { conversa: props.conversa, indice: props.indice })
    registrarPasso()
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
    registrarPasso()
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
  aplicarPadraoFundo(canvas, { padrao: layoutAtual.fundoPadrao, w, h, clara: ['citacao', 'padrao', 'twitter'].includes(props.modelo) })
  canvas.renderAll()
}

function reaplicarSombra() {
  if (!canvas) return
  removerPorPapel('sombra')
  const { w, h } = tamanhoAtivo()
  aplicarSombra(canvas, { estilo: layoutAtual.sombraEstilo, opacidade: layoutAtual.sombraOpacidade, w, h })
  canvas.renderAll()
}

function reaplicarFundoBase() {
  if (!canvas) return
  const { w, h } = tamanhoAtivo()
  canvas.backgroundColor = corFundoFinal(canvas, { layout: layoutAtual, corBase: corFundoAtual.value, corDestaque: props.corDestaque, w, h })
  canvas.renderAll()
}

async function reaplicarLogo() {
  if (!canvas) return
  removerPorPapel('logo')
  if (layoutAtual.logoAtivo && props.logoUrl) {
    const { w, h } = tamanhoAtivo()
    await aplicarLogo(canvas, { logoUrl: props.logoUrl, posicao: layoutAtual.logoPosicao, w, h })
  }
  canvas.renderAll()
  atualizarCamadas()
}

async function reaplicarFundoImagem() {
  if (!canvas) return
  removerPorPapel('fundo-imagem')
  const { w, h } = tamanhoAtivo()
  if (layoutAtual.fundoImagem) {
    await aplicarFundoImagem(canvas, { url: layoutAtual.fundoImagem, w, h })
  }
  canvas.renderAll()
  atualizarCamadas()
}

async function reaplicarImagemCitacao() {
  if (!canvas || props.modelo !== 'citacao') return
  removerPorPapel('citacao-imagem', 'marca')
  const { w, h } = tamanhoAtivo()
  if (layoutAtual.citacaoImagem) {
    await aplicarImagemCitacao(canvas, { url: layoutAtual.citacaoImagem, posicao: layoutAtual.imagemPosicao, w, h })
  } else {
    elementosCitacao(canvas, { w, h, imagemPosicao: layoutAtual.imagemPosicao, temImagem: false })
  }
  canvas.renderAll()
  atualizarCamadas()
}

function atualizarLayout(mudancas) {
  registrarPasso()
  Object.assign(layoutAtual, mudancas)
  props.slide.layout = { ...layoutAtual }
  if ('fundoPadrao' in mudancas) reaplicarFundoPadrao()
  if ('sombraEstilo' in mudancas || 'sombraOpacidade' in mudancas) reaplicarSombra()
  if ('fundoGradiente' in mudancas || 'fundoCor2' in mudancas) reaplicarFundoBase()
  if ('logoAtivo' in mudancas || 'logoPosicao' in mudancas) reaplicarLogo()
  if ('fundoImagem' in mudancas) reaplicarFundoImagem()
  if ('citacaoImagem' in mudancas || 'imagemPosicao' in mudancas) reaplicarImagemCitacao()
  reaplicarTexto()
}

function aplicarNoProximo() {
  emit('aplicar-layout-proximo', { indice: props.indice, layout: { ...layoutAtual } })
  toast.success(__('Layout aplicado no próximo slide'))
}

function aplicarEmTodos() {
  emit('aplicar-layout-todos', { layout: { ...layoutAtual } })
  toast.success(__('Layout aplicado em todos os slides'))
}

// ------------------------------------------------------------------ ferramentas gerais

function adicionarTexto() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const t = new Textbox(__('Novo texto'), { left: w * 0.1, top: w * 0.1, width: w * 0.6, fontSize: Math.round(w * 0.04), fill: '#ffffff', fontFamily: 'Poppins', originX: 'left', originY: 'top' })
  canvas.add(t)
  canvas.setActiveObject(t)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarForma() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const r = new Rect({ left: w * 0.1, top: w * 0.1, width: w * 0.3, height: w * 0.2, fill: props.corDestaque, originX: 'left', originY: 'top' })
  canvas.add(r)
  canvas.setActiveObject(r)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarSeta() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const tam = w * 0.2
  const pontos = [
    { x: 0, y: tam * 0.32 }, { x: tam * 0.6, y: tam * 0.32 }, { x: tam * 0.6, y: 0 },
    { x: tam, y: tam * 0.5 }, { x: tam * 0.6, y: tam }, { x: tam * 0.6, y: tam * 0.68 }, { x: 0, y: tam * 0.68 },
  ]
  const seta = new Polygon(pontos, { left: w * 0.1, top: w * 0.1, fill: props.corDestaque, originX: 'left', originY: 'top' })
  canvas.add(seta)
  canvas.setActiveObject(seta)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarAspas() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const aspas = new Textbox('"', {
    left: w * 0.1, top: w * 0.06, width: w * 0.3, originX: 'left', originY: 'top',
    fontSize: Math.round(w * 0.22), fontFamily: 'Playfair Display', fontWeight: 'bold', fill: props.corDestaque,
  })
  canvas.add(aspas)
  canvas.setActiveObject(aspas)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarNumeracao() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const d = w * 0.12
  const circulo = new Circle({ left: w * 0.1, top: w * 0.1, radius: d / 2, fill: props.corDestaque, originX: 'left', originY: 'top' })
  const numero = new Textbox('1', {
    left: w * 0.1, top: w * 0.1 + d * 0.22, width: d, originX: 'left', originY: 'top',
    fontSize: Math.round(d * 0.5), fontFamily: 'Poppins', fontWeight: 'bold', fill: '#ffffff', textAlign: 'center',
  })
  canvas.add(circulo, numero)
  canvas.setActiveObject(numero)
  canvas.renderAll()
  atualizarCamadas()
}

function adicionarEstrela() {
  registrarPasso()
  const { w } = tamanhoAtivo()
  const raioExt = w * 0.09
  const raioInt = raioExt * 0.42
  const pontos = []
  for (let i = 0; i < 10; i++) {
    const raio = i % 2 === 0 ? raioExt : raioInt
    const angulo = (Math.PI / 5) * i - Math.PI / 2
    pontos.push({ x: raioExt + raio * Math.cos(angulo), y: raioExt + raio * Math.sin(angulo) })
  }
  const estrela = new Polygon(pontos, { left: w * 0.1, top: w * 0.1, fill: props.corDestaque, originX: 'left', originY: 'top' })
  canvas.add(estrela)
  canvas.setActiveObject(estrela)
  canvas.renderAll()
  atualizarCamadas()
}

function removerSelecionado() {
  if (!objetoSelecionado.value) return
  registrarPasso()
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
  const url = await uploadArquivo(file)
  if (!url) return
  const img = await FabricImage.fromURL(url, { crossOrigin: 'anonymous' })
  registrarPasso()
  const { w } = tamanhoAtivo()
  if (alvoUpload && alvoUpload.type === 'image') {
    img.set({ left: alvoUpload.left, top: alvoUpload.top, scaleX: alvoUpload.scaleX, scaleY: alvoUpload.scaleY, originX: 'left', originY: 'top' })
    canvas.remove(alvoUpload)
    canvas.add(img)
    canvas.setActiveObject(img)
  } else {
    img.scaleToWidth(w * 0.5)
    img.set({ left: w * 0.25, top: w * 0.25, originX: 'left', originY: 'top' })
    canvas.add(img)
    canvas.setActiveObject(img)
  }
  canvas.renderAll()
  atualizarCamadas()
}

// Upload que não vira objeto solto no canvas - só guarda a URL no layout
// (imagem de fundo do slide inteiro, ou a foto da caixa da citação).
async function uploadArquivo(file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '0')
  const resp = await fetch('/api/method/upload_file', {
    method: 'POST',
    headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    body: formData,
  })
  const data = await resp.json()
  return data?.message?.file_url || ''
}

function abrirUploadFundo() {
  alvoExtra = 'fundo'
  fileInputExtra.value?.click()
}

function abrirUploadCitacao() {
  alvoExtra = 'citacao'
  fileInputExtra.value?.click()
}

async function onFileSelecionadoExtra(ev) {
  const file = ev.target.files?.[0]
  ev.target.value = ''
  if (!file || !alvoExtra) return
  const carregando = alvoExtra === 'fundo' ? enviandoFundo : enviandoCitacao
  carregando.value = true
  try {
    const url = await uploadArquivo(file)
    if (!url) {
      toast.error(__('Não consegui enviar a imagem agora.'))
      return
    }
    if (alvoExtra === 'fundo') atualizarLayout({ fundoImagem: url })
    else atualizarLayout({ citacaoImagem: url })
  } finally {
    carregando.value = false
    alvoExtra = null
  }
}

function removerFundoImagem() {
  atualizarLayout({ fundoImagem: '' })
}

function removerImagemCitacao() {
  atualizarLayout({ citacaoImagem: '' })
}

function aplicarFonte() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  registrarPasso()
  objetoSelecionado.value.set({ fontFamily: propTexto.value.fontFamily })
  canvas.renderAll()
}
function aplicarTamanho() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  registrarPasso()
  objetoSelecionado.value.set({ fontSize: Number(propTexto.value.fontSize) || 32 })
  canvas.renderAll()
}
function aplicarCorTexto() {
  if (objetoSelecionado.value?.type !== 'textbox') return
  registrarPasso()
  objetoSelecionado.value.set({ fill: propTexto.value.fill })
  canvas.renderAll()
}
function aplicarCorForma() {
  if (!['rect', 'circle', 'polygon'].includes(objetoSelecionado.value?.type)) return
  registrarPasso()
  objetoSelecionado.value.set({ fill: propForma.value.fill })
  canvas.renderAll()
}
function aplicarCorFundo() {
  registrarPasso()
  layoutAtual.fundoCor = corFundoAtual.value
  props.slide.layout = { ...layoutAtual }
  reaplicarFundoBase()
}

function selecionarCamada(i) {
  const obj = camadas.value[i]?.obj
  if (!obj) return
  canvas.setActiveObject(obj)
  canvas.renderAll()
  aoSelecionar()
}

function baixarPng() {
  // sem zoom, a resolução real do canvas já é a cheia (1080px+) - sem multiplicador
  const url = canvas.toDataURL({ format: 'png' })
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
