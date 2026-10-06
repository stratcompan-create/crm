<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Influenciadoras') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 overflow-hidden">
    <!-- Lista -->
    <div class="flex w-80 shrink-0 flex-col overflow-y-auto border-r border-outline-gray-1">
      <div class="border-b border-outline-gray-1 p-3">
        <Button variant="solid" class="w-full" iconLeft="plus" :label="__('Nova influenciadora')" @click="openCreate" />
      </div>
      <div v-if="influenciadoras.loading" class="p-6 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <div
        v-for="i in influenciadoras.data || []"
        :key="i.name"
        class="cursor-pointer border-b border-outline-gray-1 p-3"
        :class="isActive(i) ? 'bg-surface-gray-2' : 'hover:bg-surface-gray-1'"
        @click="select(i)"
      >
        <div class="text-p-base-medium text-ink-gray-8">{{ i.nome }}</div>
        <div class="text-p-sm text-ink-gray-5">{{ [i.instagram, i.nicho].filter(Boolean).join(' · ') }}</div>
        <div class="text-xs text-ink-gray-4">{{ __('{0} parceria(s)', [i.parcerias || 0]) }}</div>
      </div>
      <div v-if="!influenciadoras.loading && !(influenciadoras.data || []).length" class="p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Nenhuma influenciadora cadastrada ainda.') }}
      </div>
    </div>

    <!-- Detalhe -->
    <div class="flex flex-1 flex-col overflow-y-auto">
      <template v-if="active">
        <div class="flex items-center justify-between border-b border-outline-gray-1 p-5">
          <div>
            <div class="text-lg-semibold text-ink-gray-9">{{ active.nome }}</div>
            <div class="text-p-sm text-ink-gray-5">
              {{ [active.instagram, active.nicho, active.seguidores_aprox ? __('{0} seguidores', [formatNumero(active.seguidores_aprox)]) : ''].filter(Boolean).join(' · ') }}
            </div>
          </div>
          <div class="flex gap-2">
            <Button variant="outline" :label="__('Editar')" @click="openEdit(active)" />
            <Button variant="outline" theme="red" :label="__('Excluir')" @click="confirmDeleteInfluenciadora(active)" />
          </div>
        </div>

        <div class="flex items-center justify-between px-5 pt-5">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Parcerias') }}</div>
          <Button variant="solid" size="sm" iconLeft="plus" :label="__('Nova parceria')" @click="openCreateParceria" />
        </div>

        <div class="flex flex-col gap-2 px-5 py-4">
          <div v-if="parcerias.loading" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
          <div
            v-for="p in parcerias.data || []"
            :key="p.name"
            class="cursor-pointer rounded-lg border border-outline-gray-2 p-3 hover:bg-surface-gray-1"
            @click="openEditParceria(p)"
          >
            <div class="flex items-center justify-between">
              <span class="text-p-base-medium text-ink-gray-8">{{ p.marca }}</span>
              <Badge :label="statusLabel(p.status)" :theme="statusTheme(p.status)" variant="subtle" />
            </div>
            <div class="mt-1 flex gap-3 text-p-sm text-ink-gray-5">
              <span v-if="p.valor">{{ formatCurrency(p.valor) }}</span>
              <span v-if="p.prazo_entrega">{{ __('Entrega: {0}', [formatData(p.prazo_entrega)]) }}</span>
              <span v-if="p.data_gravacao">{{ __('Gravação: {0}', [formatData(p.data_gravacao)]) }}</span>
            </div>
          </div>
          <div v-if="!parcerias.loading && !(parcerias.data || []).length" class="py-10 text-center text-p-sm text-ink-gray-5">
            {{ __('Nenhuma parceria ainda.') }}
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
import { Badge, Button, Dialog, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'

const influenciadoras = createResource({ url: 'crm.api.influenciadoras.listar_influenciadoras', auto: true })

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

function formatNumero(n) {
  return (Number(n) || 0).toLocaleString('pt-BR')
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
