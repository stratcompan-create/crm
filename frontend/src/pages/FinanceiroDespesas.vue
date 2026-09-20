<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Financeiro Despesas" />
    </template>
    <template #right-header>
      <Button
        variant="solid"
        :label="__('Nova despesa')"
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

  <DespesaModal v-model="showDespesa" :name="editing" @saved="despesas.reload()" />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import ReceiptIcon from '~icons/lucide/receipt'
import DespesaModal from '@/components/Modals/DespesaModal.vue'
import { getMeta } from '@/stores/meta'
import { formatDate } from '@/utils'
import { timestampCell } from '@/composables/useTimelinePreferences'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  ListFooter,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const brl = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v) || 0)

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
        _row[fieldname] = brl(despesa[fieldname])
      } else if (['Date', 'Datetime'].includes(fieldType) && !['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = formatDate(despesa[fieldname], '', true, fieldType == 'Datetime')
      } else if (['modified', 'creation'].includes(fieldname)) {
        _row[fieldname] = timestampCell(despesa[fieldname])
      }
    })
    return _row
  })
}

const showDespesa = ref(false)
const editing = ref('')

function createDespesa() {
  editing.value = ''
  showDespesa.value = true
}

function editDespesa(name) {
  editing.value = name
  showDespesa.value = true
}
</script>
