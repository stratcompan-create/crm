<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Financeiro" />
    </template>
    <template #right-header>
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="createHonorario"
      />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="honorarios"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Honorario"
    :options="{
      allowedViews: ['list'],
    }"
  />
  <ListView
    v-if="honorarios.data && rows.length"
    :columns="columns"
    :rows="rows"
    :options="{
      onRowClick: (row) => editHonorario(row.name),
      showTooltip: false,
      resizeColumn: true,
      rowCount: honorarios.data.row_count,
      totalCount: honorarios.data.total_count,
    }"
    row-key="name"
  >
    <ListHeader class="mx-3 sm:mx-5" @columnWidthUpdated="() => triggerResize++">
      <ListHeaderItem v-for="column in columns" :key="column.key" :item="column" />
    </ListHeader>
    <ListRows v-slot="{ idx, column, item, row }" class="mx-3 sm:mx-5" :rows="rows" doctype="CRM Honorario">
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden" @click="editHonorario(row.name)" />
      <Button
        v-if="column.key === 'status'"
        class="ml-2 shrink-0"
        variant="ghost"
        size="sm"
        :label="__('Gerar link')"
        @click.stop="gerarLink(row.name)"
      />
    </ListRows>
    <ListFooter
      class="border-t px-3 py-2 sm:px-5"
      v-model="honorarios.data.page_length_count"
      :options="{
        rowCount: honorarios.data.row_count,
        totalCount: honorarios.data.total_count,
      }"
      @loadMore="() => loadMore++"
    />
  </ListView>
  <EmptyState v-else-if="honorarios.data && !rows.length" name="Financeiro" :icon="MoneyIcon" />

  <Dialog v-model="mostrarLink" :options="{ title: __('Link de pagamento'), size: 'sm' }">
    <template #body-content>
      <ErrorMessage v-if="erroLink" :message="erroLink" />
      <div v-else class="flex items-center gap-2">
        <FormControl class="flex-1" type="text" :model-value="linkGerado" readonly />
        <Button variant="solid" :label="__('Copiar')" @click="copiarLink" />
      </div>
      <p v-if="!erroLink" class="mt-2 text-p-sm text-ink-gray-5">
        {{ __('Mande esse link pro cliente. Quando ele pagar, o honorário é marcado como Pago sozinho.') }}
      </p>
    </template>
  </Dialog>
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import MoneyIcon from '@/components/Icons/MoneyIcon.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { getMeta } from '@/stores/meta'
import { formatDate } from '@/utils'
import { timestampCell } from '@/composables/useTimelinePreferences'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  ListFooter,
  Dialog,
  ErrorMessage,
  FormControl,
  call,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const brl = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v) || 0)

const honorarios = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (!honorarios.value?.data?.data) return []
  return parseRows(honorarios.value.data.data, honorarios.value.data.columns)
})

const columns = computed(() => honorarios.value?.data?.columns || [])

function parseRows(data, columns = []) {
  return data.map((honorario) => {
    let _row = {}
    honorarios.value?.data.rows.forEach((fieldname) => {
      _row[fieldname] = honorario[fieldname]

      let fieldType = columns?.find((col) => (col.key || col.value) == fieldname)?.type

      if (fieldType === 'Currency') {
        _row[fieldname] = brl(honorario[fieldname])
      } else if (['Date', 'Datetime'].includes(fieldType) && !['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = formatDate(honorario[fieldname], '', true, fieldType == 'Datetime')
      } else if (['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = timestampCell(honorario[fieldname])
      }
    })
    return _row
  })
}

const { showModal } = useDoctypeModal()

const honorarioCallbacks = {
  afterInsert: () => honorarios.value.reload(),
  afterUpdate: () => honorarios.value.reload(),
}

function createHonorario() {
  showModal({
    doctype: 'CRM Honorario',
    title: __('Honorário'),
    callbacks: honorarioCallbacks,
  })
}

function editHonorario(name) {
  showModal({
    name,
    doctype: 'CRM Honorario',
    title: __('Honorário'),
    callbacks: honorarioCallbacks,
  })
}

const mostrarLink = ref(false)
const linkGerado = ref('')
const erroLink = ref('')

async function gerarLink(name) {
  erroLink.value = ''
  linkGerado.value = ''
  mostrarLink.value = true
  try {
    const r = await call('crm.api.pagamento.gerar_link_pagamento', { honorario: name })
    linkGerado.value = r.link
  } catch (e) {
    erroLink.value = e.messages?.join(', ') || e.message || __('Falha ao gerar o link')
  }
}

async function copiarLink() {
  if (!linkGerado.value) return
  await navigator.clipboard.writeText(linkGerado.value)
}
</script>
