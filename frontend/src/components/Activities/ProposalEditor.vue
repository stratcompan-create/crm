<template>
  <div class="pb-10">
    <div class="my-3 flex items-center justify-between sm:mt-8">
      <div class="flex flex-col">
        <div class="flex items-center text-2xl-semibold text-ink-gray-8">
          {{ __('Conteúdo da Proposta Comercial') }}
          <Badge
            v-if="isDirty"
            class="ml-3"
            :label="__('Não Salvo')"
            theme="orange"
          />
        </div>
        <div class="text-p-sm text-ink-gray-5">
          {{
            __(
              'Preencha só as seções que quiser. Seções vazias não aparecem no PDF. Os valores vêm do orçamento acima.',
            )
          }}
        </div>
      </div>
      <div class="flex gap-2">
        <Dropdown :options="templateOptions" placement="right">
          <Button :label="__('Modelos')">
            <template #prefix>
              <span class="lucide-layout-template size-4" aria-hidden="true" />
            </template>
          </Button>
        </Dropdown>
        <Button
          variant="solid"
          :label="__('Salvar proposta')"
          :disabled="!isDirty"
          :loading="saving"
          @click="save"
        />
      </div>
    </div>

    <div
      v-if="avisos.length"
      class="mb-3 flex flex-col gap-1 rounded-lg border border-outline-amber-2 bg-surface-amber-2 p-3 text-p-sm text-ink-amber-3"
    >
      <div v-for="(aviso, i) in avisos" :key="i">⚠ {{ aviso }}</div>
    </div>

    <div v-if="loading" class="py-6 text-p-sm text-ink-gray-5">
      {{ __('Carregando...') }}
    </div>

    <div v-else class="flex flex-col gap-2">
      <div
        v-for="section in SECTIONS"
        :key="section.key"
        class="rounded-lg border border-outline-gray-2"
      >
        <button
          type="button"
          class="flex w-full items-center justify-between px-4 py-3 text-left"
          @click="toggle(section.key)"
        >
          <span class="flex items-center gap-2 text-base-medium text-ink-gray-8">
            {{ section.label }}
            <span
              v-if="filled(section)"
              class="rounded bg-surface-green-2 px-1.5 py-0.5 text-xs text-ink-green-6"
            >
              {{ __('preenchida') }}
            </span>
          </span>
          <span
            :class="[
              open[section.key] ? 'lucide-chevron-up' : 'lucide-chevron-down',
              'size-4 text-ink-gray-5',
            ]"
            aria-hidden="true"
          />
        </button>

        <div
          v-if="open[section.key]"
          class="flex flex-col gap-4 border-t border-outline-gray-2 px-4 py-4"
        >
          <template v-for="field in section.fields" :key="field.k">
            <div v-if="field.type === 'estilo'" class="flex flex-col gap-2">
              <div class="text-p-sm font-medium text-ink-gray-7">{{ field.label }}</div>
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
                <button
                  v-for="s in STYLE_OPTIONS"
                  :key="s.key"
                  type="button"
                  class="rounded-lg border p-2 text-left"
                  :class="(data.capa.tema || '') === s.key ? 'border-ink-gray-9 bg-surface-gray-2' : 'border-outline-gray-2'"
                  @click="data.capa.tema = s.key"
                >
                  <div class="mb-1.5 flex h-10 overflow-hidden rounded" :style="{ background: preview(s.key || 'escuro').page, border: '1px solid #d7dde0' }">
                    <div class="w-1/3" :style="{ background: preview(s.key || 'escuro').block }" />
                  </div>
                  <div class="text-xs font-medium text-ink-gray-8">{{ s.label }}</div>
                </button>
              </div>
              <p class="text-xs text-ink-gray-5">
                {{ __('Escolha qual cor predomina neste documento. "Padrão do escritório" usa o estilo definido em Configurações → Marca.') }}
              </p>
            </div>

            <div v-else-if="field.type === 'list'" class="flex flex-col gap-2">
              <div class="text-p-sm font-medium text-ink-gray-7">
                {{ field.label }}
              </div>
              <div
                v-for="(row, idx) in data[section.key][field.k]"
                :key="idx"
                class="flex items-start gap-2 rounded border border-outline-gray-1 p-2"
              >
                <div class="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-2">
                  <FormControl
                    v-for="sub in field.item"
                    :key="sub.k"
                    v-model="row[sub.k]"
                    :type="sub.type || 'text'"
                    :rows="sub.type === 'textarea' ? 3 : undefined"
                    :placeholder="sub.label"
                    :class="sub.wide ? 'sm:col-span-2' : ''"
                  />
                </div>
                <Button
                  variant="ghost"
                  icon="lucide-trash-2"
                  @click="data[section.key][field.k].splice(idx, 1)"
                />
              </div>
              <div>
                <Button
                  variant="subtle"
                  iconLeft="plus"
                  :label="__('Adicionar item')"
                  @click="addRow(section.key, field)"
                />
              </div>
            </div>

            <div v-else class="flex flex-col gap-1">
              <div class="text-p-sm font-medium text-ink-gray-7">
                {{ field.label }}
              </div>
              <FormControl
                v-model="data[section.key][field.k]"
                :type="field.type"
                :rows="field.type === 'textarea' ? 6 : undefined"
              />
              <div v-if="field.hint" class="text-xs text-ink-gray-5">
                {{ field.hint }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, Dropdown, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'
import { getSettings } from '@/stores/settings'

const props = defineProps({
  deal: { type: String, required: true },
})

const RICH = __(
  'Use uma linha em branco para separar parágrafos e **texto** para negrito.',
)

const STYLE_OPTIONS = [
  { key: '', label: __('Padrão do escritório') },
  { key: 'escuro', label: __('Cor da marca nos destaques') },
  { key: 'claro', label: __('Fundo neutro') },
  { key: 'branco', label: __('Fundo branco') },
  { key: 'cor', label: __('Cor da marca em tudo') },
]
const { _settings: brand } = getSettings()
function preview(key) {
  const C = brand.doc?.brand_color || '#042d3c'
  const N = brand.doc?.brand_neutral || '#f4f2ed'
  return {
    escuro: { page: N, block: C },
    claro: { page: N, block: `color-mix(in srgb, ${C} 10%, ${N})` },
    branco: { page: '#ffffff', block: `color-mix(in srgb, ${C} 10%, #ffffff)` },
    cor: { page: C, block: `color-mix(in srgb, #000000 28%, ${C})` },
  }[key]
}

const CARD = [
  { k: 'titulo', label: __('Título') },
  { k: 'texto', label: __('Texto'), type: 'textarea', wide: true },
]
const NUMBER = [
  { k: 'valor', label: __('Valor (ex.: ~6–7)') },
  { k: 'rotulo', label: __('Legenda') },
]
const TITLE = [
  { k: 'titulo', label: __('Título'), type: 'text' },
  { k: 'destaque', label: __('Parte em destaque (fica em itálico)'), type: 'text' },
]

const SECTIONS = [
  {
    key: 'capa',
    label: __('Capa'),
    fields: [
      { k: 'subtitulo', label: __('Subtítulo'), type: 'text' },
      { k: 'tema', label: __('Estilo de cor do documento'), type: 'estilo' },
    ],
  },
  {
    key: 'intro',
    label: __('Introdução ao projeto'),
    fields: [
      ...TITLE,
      { k: 'texto', label: __('Texto'), type: 'textarea', hint: RICH },
      { k: 'cartoes_titulo', label: __('Título dos cartões'), type: 'text' },
      { k: 'cartoes', label: __('Cartões (até 4)'), type: 'list', item: CARD },
      { k: 'numeros', label: __('Faixa de números (até 4)'), type: 'list', item: NUMBER },
    ],
  },
  {
    key: 'diagnostico',
    label: __('Diagnóstico'),
    fields: [
      ...TITLE,
      { k: 'subtitulo', label: __('Subtítulo'), type: 'text' },
      { k: 'numeros', label: __('Números (até 5)'), type: 'list', item: NUMBER },
      { k: 'faixa_titulo', label: __('Título da faixa escura'), type: 'text' },
      { k: 'faixa_texto', label: __('Texto da faixa escura'), type: 'textarea', hint: RICH },
      { k: 'cartoes', label: __('Cartões (até 4)'), type: 'list', item: CARD },
      { k: 'conclusao', label: __('Conclusão'), type: 'textarea', hint: RICH },
    ],
  },
  {
    key: 'escopo',
    label: __('Escopo do projeto'),
    fields: [
      ...TITLE,
      {
        k: 'itens',
        label: __('Itens do escopo'),
        type: 'list',
        item: CARD,
      },
    ],
  },
  {
    key: 'cronograma',
    label: __('Cronograma'),
    fields: [
      ...TITLE,
      { k: 'subtitulo', label: __('Subtítulo'), type: 'text' },
      {
        k: 'etapas',
        label: __('Etapas (até 6)'),
        type: 'list',
        item: [
          { k: 'marco', label: __('Marco (ex.: D1–D7)') },
          { k: 'titulo', label: __('Título') },
          { k: 'texto', label: __('Texto'), type: 'textarea', wide: true },
        ],
      },
      { k: 'faixa_titulo', label: __('Título da faixa'), type: 'text' },
      { k: 'faixa_texto', label: __('Texto da faixa'), type: 'textarea', hint: RICH },
      { k: 'nota', label: __('Nota'), type: 'textarea', hint: RICH },
    ],
  },
  {
    key: 'orcamento',
    label: __('Onde o investimento é aplicado'),
    fields: [
      ...TITLE,
      { k: 'subtitulo', label: __('Subtítulo'), type: 'text' },
      { k: 'cartoes', label: __('Cartões (até 4)'), type: 'list', item: CARD },
      { k: 'faixa_titulo', label: __('Título da faixa'), type: 'text' },
      { k: 'faixa_texto', label: __('Texto da faixa'), type: 'textarea', hint: RICH },
    ],
  },
  {
    key: 'ciclos',
    label: __('Visão de ciclos'),
    fields: [
      ...TITLE,
      { k: 'subtitulo', label: __('Subtítulo'), type: 'text' },
      {
        k: 'blocos',
        label: __('Ciclos (até 2)'),
        type: 'list',
        item: [
          { k: 'rotulo', label: __('Rótulo (ex.: Ciclo 1 · agora)') },
          { k: 'titulo', label: __('Título') },
          { k: 'detalhe', label: __('Detalhe (ex.: R$ 2.000/mês)') },
          { k: 'texto', label: __('Texto'), type: 'textarea', wide: true },
          { k: 'pontos', label: __('Pontos (um por linha)'), type: 'textarea', wide: true },
        ],
      },
      { k: 'citacao', label: __('Frase de fechamento'), type: 'text' },
    ],
  },
  {
    key: 'investimento',
    label: __('Investimento'),
    fields: [
      ...TITLE,
      { k: 'plano_rotulo', label: __('Rótulo do plano'), type: 'text' },
      { k: 'plano_titulo', label: __('Nome do plano'), type: 'text' },
      { k: 'plano_texto', label: __('Descrição do plano (em branco = itens do orçamento)'), type: 'textarea' },
      { k: 'valor_sufixo', label: __('Complemento do valor (ex.: / mês)'), type: 'text' },
      { k: 'recomendado_titulo', label: __('Título do plano recomendado'), type: 'text' },
      { k: 'recomendado_texto', label: __('Texto do plano recomendado'), type: 'textarea', hint: RICH },
      { k: 'fases_titulo', label: __('Título das fases futuras'), type: 'text' },
      { k: 'fases_texto', label: __('Texto das fases futuras'), type: 'textarea', hint: RICH },
      {
        k: 'condicoes',
        label: __('Condições e regras de escopo'),
        type: 'list',
        item: [
          { k: 'titulo', label: __('Título') },
          { k: 'texto', label: __('Texto'), type: 'textarea', wide: true },
        ],
      },
      {
        k: 'validade_dias',
        label: __('Validade em dias (calcula a data limite e cria uma tarefa de acompanhamento)'),
        type: 'number',
      },
      { k: 'validade', label: __('Texto da validade (usado se os dias ficarem vazios)'), type: 'text' },
    ],
  },
]

const avisos = ref([])
const templates = ref([])
const data = reactive({})
const open = reactive({})
const loading = ref(true)
const saving = ref(false)
const snapshot = ref('')

const isDirty = computed(() => !loading.value && JSON.stringify(data) !== snapshot.value)

function toggle(key) {
  open[key] = !open[key]
}

function addRow(sectionKey, field) {
  const row = {}
  field.item.forEach((sub) => (row[sub.k] = ''))
  data[sectionKey][field.k].push(row)
}

function filled(section) {
  const sec = data[section.key] || {}
  return section.fields.some((f) => {
    const v = sec[f.k]
    if (f.type === 'list') {
      return (v || []).some((row) => Object.values(row).some((x) => String(x || '').trim()))
    }
    return String(v || '').trim() && !(section.key === 'investimento' && (f.k === 'titulo' || f.k === 'destaque' || f.k === 'valor_sufixo'))
  })
}

async function load() {
  loading.value = true
  const res = await call('crm.api.proposta.get_proposal', { deal: props.deal })
  Object.keys(data).forEach((k) => delete data[k])
  Object.assign(data, res)
  snapshot.value = JSON.stringify(data)
  loading.value = false
}

async function save() {
  saving.value = true
  try {
    const res = await call('crm.api.proposta.save_proposal', {
      deal: props.deal,
      data: JSON.stringify(data),
    })
    snapshot.value = JSON.stringify(data)
    avisos.value = res?.avisos || []
    if (avisos.value.length) toast.warning(avisos.value[0])
    else toast.success(__('Proposta salva'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao salvar'))
  } finally {
    saving.value = false
  }
}

async function loadTemplates() {
  templates.value = (await call('crm.api.proposta.list_templates')) || []
}

async function useTemplate(name) {
  if (!window.confirm(__('Substituir o conteúdo atual pelo modelo "{0}"?', [name]))) return
  const res = await call('crm.api.proposta.get_template', { nome: name })
  Object.keys(data).forEach((k) => delete data[k])
  Object.assign(data, res)
  toast.success(__('Modelo aplicado. Revise e salve a proposta.'))
}

async function saveAsTemplate() {
  const name = window.prompt(__('Nome do modelo'))
  if (!name || !name.trim()) return
  try {
    await call('crm.api.proposta.save_template', {
      nome: name.trim(),
      data: JSON.stringify(data),
    })
    toast.success(__('Modelo salvo'))
    await loadTemplates()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao salvar'))
  }
}

async function removeTemplate(name) {
  if (!window.confirm(__('Apagar o modelo "{0}"?', [name]))) return
  await call('crm.api.proposta.delete_template', { nome: name })
  toast.success(__('Modelo apagado'))
  await loadTemplates()
}

const templateOptions = computed(() => {
  const groups = []
  if (templates.value.length) {
    groups.push({
      group: __('Começar de um modelo'),
      items: templates.value.map((n) => ({ label: n, onClick: () => useTemplate(n) })),
    })
  }
  groups.push({
    group: __('Gerenciar'),
    items: [
      { label: __('Salvar como modelo…'), onClick: saveAsTemplate },
      ...templates.value.map((n) => ({
        label: __('Apagar modelo: {0}', [n]),
        onClick: () => removeTemplate(n),
      })),
    ],
  })
  return groups
})

onMounted(() => {
  load()
  loadTemplates()
})
defineExpose({ isDirty })
</script>
