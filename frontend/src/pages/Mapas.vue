<template>
  <LayoutHeader>
    <template #left-header>
      <div class="flex items-center gap-2">
        <Button v-if="mapId" variant="ghost" icon="lucide-chevron-left" @click="closeMap" />
        <div class="text-lg font-semibold text-ink-gray-9">{{ mapId ? title || __('Mapa') : __('Mapas de estratégia') }}</div>
      </div>
    </template>
    <template #right-header>
      <div v-if="mapId" class="flex items-center gap-2">
        <span class="text-p-sm text-ink-gray-5">{{ saveText }}</span>
        <Button variant="subtle" iconLeft="lucide-image-down" :label="__('Baixar imagem')" @click="exportImage" />
      </div>
      <Button v-else variant="solid" iconLeft="lucide-plus" :label="__('Novo mapa')" @click="openNew" />
    </template>
  </LayoutHeader>

  <!-- Lista -->
  <div v-if="!mapId" class="flex-1 overflow-y-auto px-4 pb-10 pt-5 sm:px-6">
    <div class="mx-auto max-w-4xl">
      <p class="text-p-base text-ink-gray-6">
        {{ __('Desenhe qualquer estratégia: funil, upsell, cross-sell, jornada do cliente. Arraste os blocos, conecte com setas e deixe salvo aqui dentro do CRM.') }}
      </p>
      <div v-if="!maps.data?.length && !maps.loading" class="mt-6 rounded-lg border border-dashed border-outline-gray-3 p-8 text-center">
        <div class="text-base-medium text-ink-gray-8">{{ __('Nenhum mapa ainda') }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ __('Comece de um modelo pronto ou de uma tela em branco.') }}</p>
        <Button class="mt-3" variant="solid" :label="__('Criar o primeiro mapa')" @click="openNew" />
      </div>
      <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="m in maps.data || []"
          :key="m.name"
          class="flex cursor-pointer flex-col justify-between rounded-lg border border-outline-gray-2 p-4 transition hover:shadow-sm"
          @click="openMap(m.name)"
        >
          <div>
            <div class="flex items-center gap-2">
              <span class="lucide-workflow size-4 text-ink-gray-5" aria-hidden="true" />
              <span class="truncate text-p-base-medium text-ink-gray-9">{{ m.titulo }}</span>
            </div>
            <div class="mt-1 text-xs text-ink-gray-5">{{ __('Atualizado em {0}', [dateBr(m.modified)]) }}</div>
          </div>
          <div class="mt-3 flex gap-1" @click.stop>
            <Button variant="ghost" size="sm" :label="__('Duplicar')" @click="duplicate(m)" />
            <Button variant="ghost" size="sm" theme="red" :label="__('Excluir')" @click="remove(m)" />
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Editor -->
  <div v-else class="flex min-h-0 flex-1">
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- barra de ferramentas -->
      <div v-if="canEdit" class="flex flex-wrap items-center gap-2 border-b border-outline-gray-1 px-3 py-2">
        <FormControl v-model="title" class="w-56" type="text" :placeholder="__('Nome do mapa')" @blur="scheduleSave" />
        <span class="mx-1 h-5 border-l border-outline-gray-2" />
        <Button variant="subtle" iconLeft="lucide-square" :label="__('Bloco')" @click="addNode('card')" />
        <Button variant="subtle" iconLeft="lucide-sticky-note" :label="__('Nota')" @click="addNode('sticky')" />
        <Button variant="subtle" iconLeft="lucide-type" :label="__('Texto')" @click="addNode('text')" />
        <Button variant="subtle" iconLeft="lucide-bar-chart-3" :label="__('Dado do CRM')" @click="showData = true" />
        <span class="mx-1 h-5 border-l border-outline-gray-2" />
        <Button variant="ghost" iconLeft="lucide-trash-2" theme="red" :label="__('Apagar seleção')" :disabled="!hasSelection" @click="deleteSelection" />
        <span class="ml-auto hidden text-xs text-ink-gray-5 lg:inline">
          {{ __('Arraste do ponto de um bloco até outro para ligar. Role para dar zoom.') }}
        </span>
      </div>

      <div ref="canvasBox" class="relative min-h-0 flex-1 bg-surface-gray-1">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :nodes-draggable="canEdit"
          :nodes-connectable="canEdit"
          :edges-updatable="canEdit"
          :delete-key-code="canEdit ? ['Backspace', 'Delete'] : null"
          :default-edge-options="edgeDefaults"
          connection-mode="loose"
          :min-zoom="0.2"
          :max-zoom="2"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
          @node-click="({ node }) => select('node', node.id)"
          @node-double-click="({ node }) => node.type === 'data' && openMetric(node)"
          @edge-click="({ edge }) => select('edge', edge.id)"
          @pane-click="select(null, null)"
          @move-end="scheduleSave"
        >
          <template #node-card="p"><StrategyNode v-bind="p" /></template>
          <template #node-sticky="p"><StrategyNode v-bind="p" /></template>
          <template #node-text="p"><StrategyNode v-bind="p" /></template>
          <template #node-data="p"><StrategyNode v-bind="p" /></template>
          <Background :gap="16" pattern-color="#c9d2d8" />
          <Controls :show-interactive="false" position="bottom-left" />
        </VueFlow>
      </div>
    </div>

    <!-- painel de edição -->
    <aside v-if="canEdit && selected" class="w-72 shrink-0 overflow-y-auto border-l border-outline-gray-1 p-4">
      <template v-if="selected.kind === 'node' && selNode">
        <div class="mb-3 text-p-base-medium text-ink-gray-9">{{ { card: __('Bloco'), data: __('Dado do CRM'), sticky: __('Nota') }[selNode.type] || __('Texto') }}</div>
        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ ['card', 'data'].includes(selNode.type) ? __('Título') : __('Texto') }}</span>
            <FormControl v-model="selNode.data.label" :type="['card', 'data'].includes(selNode.type) ? 'text' : 'textarea'" :rows="4" />
          </div>
          <div v-if="selNode.type === 'data'" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Dado exibido') }}</span>
            <FormControl v-model="selNode.data.metric" type="select" :options="metricOptions" />
            <Button class="mt-1" variant="subtle" iconLeft="lucide-external-link" :label="__('Abrir no CRM')" @click="openMetric(selNode)" />
          </div>
          <div v-if="selNode.type === 'card'" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Descrição (opcional)') }}</span>
            <FormControl v-model="selNode.data.note" type="textarea" :rows="3" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Cor') }}</span>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="(c, key) in colorList(selNode.type)"
                :key="key"
                type="button"
                :title="__(c.label)"
                class="size-6 rounded-full border-2"
                :style="{ background: c.bg, borderColor: selNode.data.color === key ? c.border : 'transparent', outline: '1px solid ' + c.border }"
                @click="selNode.data.color = key"
              />
            </div>
          </div>
          <div v-if="['card', 'data'].includes(selNode.type)" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Ícone') }}</span>
            <div class="grid grid-cols-6 gap-1">
              <button
                v-for="i in MAP_ICONS"
                :key="i.name"
                type="button"
                class="flex size-9 items-center justify-center rounded-md border"
                :class="selNode.data.icon === i.name ? 'border-ink-gray-9 bg-surface-gray-2' : 'border-outline-gray-2'"
                :title="i.name"
                @click="selNode.data.icon = i.name"
              >
                <span :class="i.cls" class="size-4" aria-hidden="true" />
              </button>
            </div>
          </div>
          <Button variant="subtle" theme="red" iconLeft="lucide-trash-2" :label="__('Apagar')" @click="deleteSelection" />
        </div>
      </template>
      <template v-else-if="selected.kind === 'edge' && selEdge">
        <div class="mb-3 text-p-base-medium text-ink-gray-9">{{ __('Seta') }}</div>
        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ __('Texto sobre a seta (opcional)') }}</span>
            <FormControl v-model="selEdge.label" type="text" :placeholder="__('Ex.: se responder')" />
          </div>
          <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
            <input v-model="selEdge.animated" type="checkbox" />
            {{ __('Seta animada') }}
          </label>
          <Button variant="subtle" theme="red" iconLeft="lucide-trash-2" :label="__('Apagar seta')" @click="deleteSelection" />
        </div>
      </template>
    </aside>
  </div>

  <!-- Dado do CRM -->
  <Dialog v-model="showData" :options="{ title: __('Dado do CRM'), size: 'lg' }">
    <template #body-content>
      <p class="mb-3 text-p-sm text-ink-gray-6">{{ __('O bloco mostra o número real, sempre atualizado, e abre a lista com um duplo clique.') }}</p>
      <div v-for="(items, group) in catalogGroups" :key="group" class="mb-3">
        <div class="mb-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __(group) }}</div>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="c in items"
            :key="c.key"
            type="button"
            class="rounded-full border border-outline-gray-2 px-3 py-1 text-p-sm text-ink-gray-8 hover:bg-surface-gray-2"
            @click="addDataNode(c)"
          >
            {{ c.label }}
          </button>
        </div>
      </div>
    </template>
  </Dialog>

  <!-- Novo mapa -->
  <Dialog v-model="showNew" :options="{ title: __('Novo mapa'), size: '2xl' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-p-sm text-ink-gray-6">{{ __('Nome (opcional)') }}</span>
          <FormControl v-model="newTitle" type="text" :placeholder="__('Ex.: Funil do plano mensal')" />
        </div>
        <div>
          <div class="mb-2 text-p-sm text-ink-gray-6">{{ __('Como você quer começar?') }}</div>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              v-for="t in templates.data || []"
              :key="t.chave"
              type="button"
              class="rounded-lg border p-3 text-left"
              :class="newTemplate === t.chave ? 'border-ink-gray-9 bg-surface-gray-2' : 'border-outline-gray-2'"
              @click="newTemplate = t.chave"
            >
              <div class="text-p-base-medium text-ink-gray-9">{{ t.titulo }}</div>
              <div class="mt-0.5 text-xs text-ink-gray-5">{{ t.descricao }}</div>
            </button>
          </div>
        </div>
        <ErrorMessage v-if="error" :message="error" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Criar mapa')" :loading="creating" @click="createMap" />
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import StrategyNode from '@/components/Mapas/StrategyNode.vue'
import { MAP_COLORS, MAP_ICONS } from '@/components/Mapas/mapIcons'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { toPng } from 'html-to-image'
import { computed, nextTick, onBeforeUnmount, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const maps = createResource({ url: 'crm.api.mapas.list_maps', auto: true })
const metrics = createResource({ url: 'crm.api.mapas.get_metrics', auto: true, onError() {} })
provide('mapMetrics', metrics)
const metricTimer = setInterval(() => mapId.value && metrics.reload(), 60000)
const showData = ref(false)
const catalogGroups = computed(() => {
  const groups = {}
  for (const c of metrics.data?.catalogo || []) (groups[c.grupo] ||= []).push(c)
  return groups
})
const metricOptions = computed(() => (metrics.data?.catalogo || []).map((c) => ({ label: c.label, value: c.key })))
function addDataNode(c) {
  showData.value = false
  addNode('data', { metric: c.key, label: c.label })
}
function openMetric(node) {
  const item = (metrics.data?.catalogo || []).find((c) => c.key === node.data?.metric)
  if (item?.route) router.push({ name: item.route })
}
const templates = createResource({ url: 'crm.api.mapas.get_templates', auto: true })
const dateBr = (v) => (v ? String(v).slice(0, 10).split('-').reverse().join('/') : '')

// ---- lista / novo
const showNew = ref(false)
const newTitle = ref('')
const newTemplate = ref('funil')
const creating = ref(false)
const error = ref('')
function openNew() {
  error.value = ''
  showNew.value = true
}
async function createMap() {
  creating.value = true
  error.value = ''
  try {
    const r = await call('crm.api.mapas.create_map', { titulo: newTitle.value, modelo: newTemplate.value })
    showNew.value = false
    newTitle.value = ''
    await maps.reload()
    openMap(r.name)
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível criar o mapa.')
  } finally {
    creating.value = false
  }
}
async function duplicate(m) {
  const r = await call('crm.api.mapas.duplicate_map', { name: m.name })
  await maps.reload()
  openMap(r.name)
}
async function remove(m) {
  if (!window.confirm(__('Excluir o mapa "{0}"? Isso não pode ser desfeito.', [m.titulo]))) return
  await call('crm.api.mapas.delete_map', { name: m.name })
  maps.reload()
}

// ---- editor
const mapId = computed(() => route.query.m || '')
const title = ref('')
const canEdit = ref(false)
const nodes = ref([])
const edges = ref([])
const selected = ref(null)
const loaded = ref(false)
const canvasBox = ref(null)

const { getViewport, setViewport, fitView, screenToFlowCoordinate, removeNodes, removeEdges } = useVueFlow()

const edgeDefaults = {
  type: 'smoothstep',
  markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
  style: { strokeWidth: 2 },
}

function openMap(name) {
  router.push({ name: 'Mapas', query: { m: name } })
}
function closeMap() {
  flushSave()
  router.push({ name: 'Mapas' })
  maps.reload()
}

async function loadMap(name) {
  loaded.value = false
  selected.value = null
  const r = await call('crm.api.mapas.get_map', { name })
  title.value = r.titulo
  canEdit.value = r.pode_editar
  nodes.value = r.dados.nodes || []
  edges.value = (r.dados.edges || []).map((e) => ({ ...edgeDefaults, ...e }))
  await nextTick()
  if (r.dados.viewport) setViewport(r.dados.viewport)
  else fitView({ padding: 0.2 })
  await nextTick()
  loaded.value = true
}
watch(
  mapId,
  (name) => {
    if (name) loadMap(name)
    else loaded.value = false
  },
  { immediate: true },
)

// ---- seleção
const selNode = computed(() => (selected.value?.kind === 'node' ? nodes.value.find((n) => n.id === selected.value.id) : null))
const selEdge = computed(() => (selected.value?.kind === 'edge' ? edges.value.find((e) => e.id === selected.value.id) : null))
const hasSelection = computed(() => !!selected.value || nodes.value.some((n) => n.selected) || edges.value.some((e) => e.selected))
function select(kind, id) {
  selected.value = kind ? { kind, id } : null
}
const colorList = (type) => (type === 'sticky' ? { yellow: MAP_COLORS.yellow, blue: MAP_COLORS.blue, green: MAP_COLORS.green, red: MAP_COLORS.red } : MAP_COLORS)

function deleteSelection() {
  const ids = nodes.value.filter((n) => n.selected).map((n) => n.id)
  const eids = edges.value.filter((e) => e.selected).map((e) => e.id)
  if (selected.value?.kind === 'node' && !ids.includes(selected.value.id)) ids.push(selected.value.id)
  if (selected.value?.kind === 'edge' && !eids.includes(selected.value.id)) eids.push(selected.value.id)
  if (ids.length) removeNodes(ids)
  if (eids.length) removeEdges(eids)
  selected.value = null
}

function addNode(kind, extra = {}) {
  const box = canvasBox.value?.getBoundingClientRect()
  const pos = box
    ? screenToFlowCoordinate({ x: box.left + box.width / 2 - 90, y: box.top + box.height / 2 - 30 })
    : { x: 100, y: 100 }
  const id = `n${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`
  const base = {
    card: { label: __('Novo bloco'), note: '', icon: 'circle', color: 'blue' },
    sticky: { label: __('Escreva aqui'), note: '', icon: 'circle', color: 'yellow' },
    text: { label: __('Título'), note: '', icon: 'circle', color: 'gray' },
    data: { label: '', note: '', icon: 'bar-chart-2', color: 'blue', metric: '' },
  }[kind]
  nodes.value = [...nodes.value, { id, type: kind, position: { x: Math.round(pos.x / 16) * 16, y: Math.round(pos.y / 16) * 16 }, data: { ...base, ...extra } }]
  select('node', id)
}

// ---- salvar sozinho
const saveState = ref('')
const saveText = computed(() => ({ saving: __('Salvando...'), saved: __('Salvo'), error: __('Erro ao salvar') })[saveState.value] || '')
let timer = null
function scheduleSave() {
  if (!canEdit.value || !loaded.value || !mapId.value) return
  saveState.value = 'saving'
  clearTimeout(timer)
  timer = setTimeout(doSave, 1200)
}
function flushSave() {
  if (timer) {
    clearTimeout(timer)
    doSave()
  }
}
async function doSave() {
  timer = null
  if (!canEdit.value || !mapId.value) return
  const clean = {
    nodes: nodes.value.map((n) => ({ id: n.id, type: n.type, position: n.position, data: n.data })),
    edges: edges.value.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
      label: e.label || '',
      animated: !!e.animated,
    })),
    viewport: getViewport(),
  }
  try {
    await call('crm.api.mapas.save_map', { name: mapId.value, dados: clean, titulo: title.value })
    saveState.value = 'saved'
  } catch (e) {
    saveState.value = 'error'
    toast.error(e?.messages?.[0] || __('Não foi possível salvar o mapa.'))
  }
}
watch([nodes, edges], scheduleSave, { deep: true })
watch(title, scheduleSave)
onBeforeUnmount(() => {
  flushSave()
  clearInterval(metricTimer)
})

// ---- exportar imagem
async function exportImage() {
  const el = canvasBox.value
  if (!el || !nodes.value.length) return
  selected.value = null
  const view = getViewport()
  await fitView({ padding: 0.15 })
  await nextTick()
  await new Promise((r) => setTimeout(r, 350))
  try {
    const url = await toPng(el, {
      backgroundColor: '#ffffff',
      pixelRatio: 2,
      filter: (n) => !(n.classList && (n.classList.contains('vue-flow__controls') || n.classList.contains('vue-flow__panel'))),
    })
    const a = document.createElement('a')
    a.href = url
    a.download = `${(title.value || 'mapa').replace(/[^\w\-]+/g, '-')}.png`
    a.click()
  } catch (e) {
    toast.error(__('Não foi possível gerar a imagem.'))
  } finally {
    setViewport(view)
  }
}
</script>
