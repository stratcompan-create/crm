<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Influenciadoras') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 overflow-hidden">
    <!-- Lista -->
    <div class="flex w-80 shrink-0 flex-col overflow-y-auto border-r border-outline-gray-1">
      <div class="flex flex-col gap-2 border-b border-outline-gray-1 p-3">
        <Button variant="solid" class="w-full" iconLeft="plus" :label="__('Nova influenciadora')" @click="openCreate" />
        <FormControl
          v-if="(influenciadoras.data || []).length > 4"
          type="text"
          :placeholder="__('Buscar por nome, @ ou nicho...')"
          v-model="search"
        />
      </div>
      <div v-if="influenciadoras.loading" class="p-6 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <div
        v-for="i in filtered"
        :key="i.name"
        class="flex cursor-pointer items-start gap-3 border-b border-outline-gray-1 p-3 transition-colors"
        :class="isActive(i) ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
        @click="select(i)"
      >
        <Avatar :label="i.nome" :theme="themeFor(i.nome)" size="xl">
          <span class="text-xs font-semibold">{{ initials(i.nome) }}</span>
        </Avatar>
        <div class="flex flex-1 flex-col gap-1 overflow-hidden">
          <div class="truncate text-p-base-medium text-ink-gray-8">{{ i.nome }}</div>
          <div class="flex flex-wrap items-center gap-1.5">
            <span v-if="i.instagram" class="text-p-sm text-ink-gray-5">{{ formatHandle(i.instagram) }}</span>
            <Badge v-if="i.nicho" :label="i.nicho" variant="subtle" theme="gray" />
          </div>
          <div class="flex items-center gap-2 text-xs text-ink-gray-4">
            <span v-if="i.seguidores_aprox">{{ __('{0} seguidores', [formatCompacto(i.seguidores_aprox)]) }}</span>
            <span v-if="i.seguidores_aprox && i.parcerias">·</span>
            <span v-if="i.parcerias">{{ __('{0} parceria(s)', [i.parcerias]) }}</span>
          </div>
        </div>
      </div>
      <div v-if="!influenciadoras.loading && !filtered.length && !(influenciadoras.data || []).length" class="flex flex-col items-center gap-2 p-10 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-4">
          <FeatherIcon name="users" class="h-6 w-6" />
        </div>
        <div class="text-p-sm text-ink-gray-5">{{ __('Nenhuma influenciadora cadastrada ainda.') }}</div>
      </div>
      <div v-else-if="!influenciadoras.loading && !filtered.length" class="p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Nenhum resultado para essa busca.') }}
      </div>
    </div>

    <!-- Detalhe -->
    <div class="flex flex-1 flex-col overflow-y-auto">
      <template v-if="active">
        <div class="border-b border-outline-gray-1 p-5">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
              <Avatar :label="active.nome" :theme="themeFor(active.nome)" size="2xl">
                <span class="text-base font-semibold">{{ initials(active.nome) }}</span>
              </Avatar>
              <div>
                <div class="text-lg-semibold text-ink-gray-9">{{ active.nome }}</div>
                <div class="mt-0.5 flex flex-wrap items-center gap-2 text-p-sm text-ink-gray-5">
                  <span v-if="active.instagram">{{ formatHandle(active.instagram) }}</span>
                  <Badge v-if="active.nicho" :label="active.nicho" variant="subtle" theme="gray" />
                  <span v-if="active.seguidores_aprox">{{ __('{0} seguidores', [formatCompacto(active.seguidores_aprox)]) }}</span>
                </div>
                <p v-if="active.observacoes" class="mt-1.5 max-w-md text-p-sm text-ink-gray-6">{{ active.observacoes }}</p>
              </div>
            </div>
            <div class="flex shrink-0 gap-2">
              <Button variant="outline" :label="__('Editar')" @click="openEdit(active)" />
              <Button variant="outline" theme="red" :label="__('Excluir')" @click="confirmDeleteInfluenciadora(active)" />
            </div>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-3">
            <div class="rounded-lg bg-surface-gray-2 px-4 py-2.5">
              <div class="text-lg-semibold text-ink-gray-9">{{ statsParcerias.total }}</div>
              <div class="text-p-sm text-ink-gray-5">{{ __('Parcerias') }}</div>
            </div>
            <div class="rounded-lg bg-surface-gray-2 px-4 py-2.5">
              <div class="text-lg-semibold text-ink-gray-9">{{ formatCurrency(statsParcerias.valorTotal) }}</div>
              <div class="text-p-sm text-ink-gray-5">{{ __('Negociado no total') }}</div>
            </div>
            <div class="rounded-lg bg-surface-green-1 px-4 py-2.5">
              <div class="text-lg-semibold text-ink-green-7">{{ formatCurrency(statsParcerias.valorConfirmado) }}</div>
              <div class="text-p-sm text-ink-gray-5">{{ __('Fechado/entregue') }}</div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between px-5 pt-5">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Parcerias') }}</div>
          <Button variant="solid" size="sm" iconLeft="plus" :label="__('Nova parceria')" @click="openCreateParceria" />
        </div>

        <div class="flex flex-col gap-2.5 px-5 py-4">
          <div v-if="parcerias.loading" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
          <div
            v-for="p in parcerias.data || []"
            :key="p.name"
            class="cursor-pointer rounded-lg border border-outline-gray-2 p-3.5 pl-4 transition-colors hover:bg-surface-gray-1"
            :class="statusBorderClass(p.status)"
            @click="openEditParceria(p)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Avatar :label="p.marca" :theme="themeFor(p.marca)" size="sm">
                  <span class="text-xs font-semibold">{{ initials(p.marca) }}</span>
                </Avatar>
                <span class="text-p-base-medium text-ink-gray-8">{{ p.marca }}</span>
              </div>
              <Badge :label="statusLabel(p.status)" :theme="statusTheme(p.status)" variant="subtle" />
            </div>
            <div class="mt-2 flex flex-wrap gap-3 text-p-sm text-ink-gray-5">
              <span v-if="p.valor" class="font-medium text-ink-gray-7">{{ formatCurrency(p.valor) }}</span>
              <span v-if="p.prazo_entrega">{{ __('Entrega: {0}', [formatData(p.prazo_entrega)]) }}</span>
              <span v-if="p.data_gravacao">{{ __('Gravação: {0}', [formatData(p.data_gravacao)]) }}</span>
            </div>
            <p v-if="p.briefing" class="mt-1.5 truncate text-p-sm text-ink-gray-4">{{ p.briefing }}</p>
          </div>
          <div v-if="!parcerias.loading && !(parcerias.data || []).length" class="flex flex-col items-center gap-2 py-10 text-center">
            <div class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-4">
              <FeatherIcon name="briefcase" class="h-5 w-5" />
            </div>
            <div class="text-p-sm text-ink-gray-5">{{ __('Nenhuma parceria ainda.') }}</div>
          </div>
        </div>
      </template>
      <EmptyState
        v-else
        name="Influenciadora"
        :title="__('Selecione uma influenciadora')"
        :description="__('Escolha na lista ao lado, ou cadastre uma nova.')"
        icon="users"
      />
    </div>
  </div>

  <!-- Criar/editar influenciadora -->
  <Dialog v-model="showInfluenciadoraForm" :options="{ title: editingInfluenciadora ? __('Editar influenciadora') : __('Nova influenciadora'), size: 'sm' }">
    <template #body-content>
      <div class="flex flex-col gap-3">
        <FormControl type="text" :label="__('Nome')" v-model="formInf.nome" />
        <FormControl type="text" :label="__('Instagram (@)')" v-model="formInf.instagram" />
        <FormControl type="text" :label="__('Nicho')" v-model="formInf.nicho" />
        <FormControl type="number" :label="__('Seguidores (aprox.)')" v-model="formInf.seguidores_aprox" />
        <FormControl type="textarea" :rows="2" :label="__('Observações')" v-model="formInf.observacoes" />
      </div>
    </template>
    <template #actions>
      <Button variant="solid" :label="__('Salvar')" :loading="savingInf" @click="saveInfluenciadora" />
    </template>
  </Dialog>

  <!-- Confirmar exclusão de influenciadora -->
  <Dialog v-model="showDeleteInfluenciadora" :options="{ title: __('Excluir influenciadora'), size: 'sm' }">
    <template #body-content>
      <p class="text-p-sm text-ink-gray-7">
        {{ __('Isso apaga {0} e todas as parcerias dela. Não dá pra desfazer.', [deleteTarget?.nome]) }}
      </p>
    </template>
    <template #actions>
      <Button variant="solid" theme="red" :label="__('Excluir')" :loading="deletingInf" @click="deleteInfluenciadora" />
    </template>
  </Dialog>

  <!-- Criar/editar parceria -->
  <Dialog v-model="showParceriaForm" :options="{ title: editingParceria ? __('Editar parceria') : __('Nova parceria'), size: 'sm' }">
    <template #body-content>
      <div class="flex flex-col gap-3">
        <FormControl type="text" :label="__('Marca / empresa parceira')" v-model="formParc.marca" />
        <FormControl type="select" :label="__('Status')" v-model="formParc.status" :options="statusOptions" />
        <FormControl type="number" :label="__('Valor')" v-model="formParc.valor" />
        <FormControl type="date" :label="__('Data de gravação')" v-model="formParc.data_gravacao" />
        <FormControl type="date" :label="__('Prazo de entrega')" v-model="formParc.prazo_entrega" />
        <FormControl type="textarea" :rows="2" :label="__('Briefing / direcionamento')" v-model="formParc.briefing" />
        <FormControl type="textarea" :rows="2" :label="__('Observações')" v-model="formParc.observacoes" />
      </div>
    </template>
    <template #actions>
      <Button v-if="editingParceria" variant="ghost" theme="red" :label="__('Excluir')" :loading="deletingParc" @click="deleteParceria" />
      <Button variant="solid" :label="__('Salvar')" :loading="savingParc" @click="saveParceria" />
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import { Avatar, Badge, Button, Dialog, FeatherIcon, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const influenciadoras = createResource({ url: 'crm.api.influenciadoras.listar_influenciadoras', auto: true })

const search = ref('')
const filtered = computed(() => {
  const list = influenciadoras.data || []
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((i) => [i.nome, i.instagram, i.nicho].filter(Boolean).some((v) => String(v).toLowerCase().includes(q)))
})

const active = ref(null)
const parcerias = createResource({
  url: 'crm.api.influenciadoras.listar_parcerias',
  makeParams: () => ({ influenciadora: active.value?.name }),
})

function isActive(i) {
  return active.value?.name === i.name
}
function select(i) {
  active.value = i
  parcerias.fetch()
}

const statsParcerias = computed(() => {
  const list = parcerias.data || []
  const valorTotal = list.reduce((s, p) => s + (Number(p.valor) || 0), 0)
  const valorConfirmado = list
    .filter((p) => ['Fechada', 'Em produção', 'Entregue'].includes(p.status))
    .reduce((s, p) => s + (Number(p.valor) || 0), 0)
  return { total: list.length, valorTotal, valorConfirmado }
})

// ------------------------------------------------------------------ visual helpers

const AVATAR_THEMES = ['blue', 'green', 'amber', 'violet', 'red', 'gray']
function themeFor(text) {
  const code = String(text || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return AVATAR_THEMES[code % AVATAR_THEMES.length]
}
function initials(text) {
  const parts = String(text || '').trim().split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}
function formatHandle(v) {
  v = String(v || '').trim()
  if (!v) return ''
  return v.startsWith('@') ? v : `@${v}`
}
function formatCompacto(n) {
  n = Number(n) || 0
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'K'
  return String(n)
}
function formatCurrency(v) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0)
}
function formatData(v) {
  if (!v) return ''
  const [ano, mes, dia] = String(v).slice(0, 10).split('-')
  return `${dia}/${mes}/${ano}`
}

const statusOptions = [
  { label: __('Negociando'), value: 'Negociando' },
  { label: __('Fechada'), value: 'Fechada' },
  { label: __('Em produção'), value: 'Em produção' },
  { label: __('Entregue'), value: 'Entregue' },
  { label: __('Cancelada'), value: 'Cancelada' },
]
const STATUS_LABELS = {
  Negociando: () => __('Negociando'),
  Fechada: () => __('Fechada'),
  'Em produção': () => __('Em produção'),
  Entregue: () => __('Entregue'),
  Cancelada: () => __('Cancelada'),
}
function statusLabel(s) {
  return STATUS_LABELS[s]?.() || s
}
function statusTheme(s) {
  if (s === 'Entregue') return 'green'
  if (s === 'Fechada') return 'blue'
  if (s === 'Em produção') return 'orange'
  if (s === 'Cancelada') return 'red'
  return 'gray'
}
function statusBorderClass(s) {
  if (s === 'Entregue') return 'border-l-[3px] border-l-green-500'
  if (s === 'Fechada') return 'border-l-[3px] border-l-blue-500'
  if (s === 'Em produção') return 'border-l-[3px] border-l-orange-400'
  if (s === 'Cancelada') return 'border-l-[3px] border-l-red-400'
  return 'border-l-[3px] border-l-gray-300'
}

// ------------------------------------------------------------------ influenciadora: criar/editar/excluir

const showInfluenciadoraForm = ref(false)
const editingInfluenciadora = ref(null)
const formInf = reactive({ nome: '', instagram: '', nicho: '', seguidores_aprox: '', observacoes: '' })
const savingInf = ref(false)

function openCreate() {
  editingInfluenciadora.value = null
  Object.assign(formInf, { nome: '', instagram: '', nicho: '', seguidores_aprox: '', observacoes: '' })
  showInfluenciadoraForm.value = true
}
function openEdit(i) {
  editingInfluenciadora.value = i
  Object.assign(formInf, {
    nome: i.nome, instagram: i.instagram, nicho: i.nicho,
    seguidores_aprox: i.seguidores_aprox, observacoes: i.observacoes,
  })
  showInfluenciadoraForm.value = true
}
async function saveInfluenciadora() {
  if (!formInf.nome.trim()) {
    toast.error(__('Informe o nome.'))
    return
  }
  savingInf.value = true
  try {
    if (editingInfluenciadora.value) {
      await call('crm.api.influenciadoras.atualizar_influenciadora', { name: editingInfluenciadora.value.name, ...formInf })
    } else {
      await call('crm.api.influenciadoras.criar_influenciadora', { ...formInf })
    }
    showInfluenciadoraForm.value = false
    await influenciadoras.reload()
    if (editingInfluenciadora.value) {
      const atualizada = (influenciadoras.data || []).find((x) => x.name === editingInfluenciadora.value.name)
      if (atualizada && active.value?.name === atualizada.name) active.value = atualizada
    }
    toast.success(__('Salvo'))
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não consegui salvar.'))
  } finally {
    savingInf.value = false
  }
}

const showDeleteInfluenciadora = ref(false)
const deleteTarget = ref(null)
const deletingInf = ref(false)
function confirmDeleteInfluenciadora(i) {
  deleteTarget.value = i
  showDeleteInfluenciadora.value = true
}
async function deleteInfluenciadora() {
  deletingInf.value = true
  try {
    await call('crm.api.influenciadoras.excluir_influenciadora', { name: deleteTarget.value.name })
    showDeleteInfluenciadora.value = false
    if (active.value?.name === deleteTarget.value.name) {
      active.value = null
      parcerias.data = []
    }
    await influenciadoras.reload()
    toast.success(__('Influenciadora excluída'))
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não consegui excluir.'))
  } finally {
    deletingInf.value = false
  }
}

// ------------------------------------------------------------------ parceria: criar/editar/excluir

const showParceriaForm = ref(false)
const editingParceria = ref(null)
const formParc = reactive({ marca: '', status: 'Negociando', valor: '', data_gravacao: '', prazo_entrega: '', briefing: '', observacoes: '' })
const savingParc = ref(false)
const deletingParc = ref(false)

function openCreateParceria() {
  editingParceria.value = null
  Object.assign(formParc, { marca: '', status: 'Negociando', valor: '', data_gravacao: '', prazo_entrega: '', briefing: '', observacoes: '' })
  showParceriaForm.value = true
}
function openEditParceria(p) {
  editingParceria.value = p
  Object.assign(formParc, {
    marca: p.marca, status: p.status, valor: p.valor,
    data_gravacao: p.data_gravacao, prazo_entrega: p.prazo_entrega,
    briefing: p.briefing, observacoes: p.observacoes,
  })
  showParceriaForm.value = true
}
async function saveParceria() {
  if (!formParc.marca.trim()) {
    toast.error(__('Informe a marca.'))
    return
  }
  savingParc.value = true
  try {
    if (editingParceria.value) {
      await call('crm.api.influenciadoras.atualizar_parceria', { name: editingParceria.value.name, ...formParc })
    } else {
      await call('crm.api.influenciadoras.criar_parceria', { influenciadora: active.value.name, ...formParc })
    }
    showParceriaForm.value = false
    await parcerias.reload()
    await influenciadoras.reload()
    toast.success(__('Salvo'))
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não consegui salvar.'))
  } finally {
    savingParc.value = false
  }
}
async function deleteParceria() {
  deletingParc.value = true
  try {
    await call('crm.api.influenciadoras.excluir_parceria', { name: editingParceria.value.name })
    showParceriaForm.value = false
    await parcerias.reload()
    await influenciadoras.reload()
    toast.success(__('Parceria excluída'))
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não consegui excluir.'))
  } finally {
    deletingParc.value = false
  }
}
</script>
