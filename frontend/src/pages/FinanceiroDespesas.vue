<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Financeiro Despesas" />
    </template>
    <template #right-header>
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="createDespesa"
      />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="despesas"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Despesa"
    :options="{
      allowedViews: ['list'],
    }"
  />
  <ListView
    v-if="despesas.data && rows.length"
    :columns="columns"
    :rows="rows"
    :options="{
      onRowClick: (row) => editDespesa(row.name),
      showTooltip: false,
      resizeColumn: true,
      rowCount: despesas.data.row_count,
      totalCount: despesas.data.total_count,
    }"
    row-key="name"
  >
    <ListHeader class="mx-3 sm:mx-5" @columnWidthUpdated="() => triggerResize++">
      <ListHeaderItem v-for="column in columns" :key="column.key" :item="column" />
    </ListHeader>
    <ListRows v-slot="{ idx, column, item, row }" class="mx-3 sm:mx-5" :rows="rows" doctype="CRM Despesa">
      <ListRowItem :item="item" :align="column.align" class="overflow-hidden" @click="editDespesa(row.name)" />
    </ListRows>
    <ListFooter
      class="border-t px-3 py-2 sm:px-5"
      v-model="despesas.data.page_length_count"
      :options="{
        rowCount: despesas.data.row_count,
        totalCount: despesas.data.total_count,
      }"
      @loadMore="() => loadMore++"
    />
  </ListView>
  <EmptyState v-else-if="despesas.data && !rows.length" name="Despesas" :icon="ReceiptIcon" />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import ReceiptIcon from '~icons/lucide/receipt'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { getMeta } from '@/stores/meta'
import { formatDate } from '@/utils'
import { timestampCell } from '@/composables/useTimelinePreferences'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRows,
  ListRowItem,
  ListFooter,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const { getFormattedCurrency } = getMeta('CRM Despesa')

const despesas = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (!despesas.value?.data?.data) return []
  return parseRows(despesas.value.data.data, despesas.value.data.columns)
})

const columns = computed(() => despesas.value?.data?.columns || [])

function parseRows(data, columns = []) {
  return data.map((despesa) => {
    let _row = {}
    despesas.value?.data.rows.forEach((fieldname) => {
      _row[fieldname] = despesa[fieldname]

      let fieldType = columns?.find((col) => (col.key || col.value) == fieldname)?.type

      if (fieldType === 'Currency') {
        _row[fieldname] = getFormattedCurrency(fieldname, despesa)
      } else if (['Date', 'Datetime'].includes(fieldType) && !['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = formatDate(despesa[fieldname], '', true, fieldType == 'Datetime')
      } else if (['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = timestampCell(despesa[fieldname])
      }
    })
    return _row
  })
}

const { showModal } = useDoctypeModal()

const despesaCallbacks = {
  afterInsert: () => despesas.value.reload(),
  afterUpdate: () => despesas.value.reload(),
}

function createDespesa() {
  showModal({
    doctype: 'CRM Despesa',
    title: __('Despesa'),
    callbacks: despesaCallbacks,
  })
}

function editDespesa(name) {
  showModal({
    name,
    doctype: 'CRM Despesa',
    title: __('Despesa'),
    callbacks: despesaCallbacks,
  })
}
</script>
