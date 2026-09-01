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
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import MoneyIcon from '@/components/Icons/MoneyIcon.vue'
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

const { getFormattedCurrency } = getMeta('CRM Honorario')

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
        _row[fieldname] = getFormattedCurrency(fieldname, honorario)
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
    title: 'Honorário',
    callbacks: honorarioCallbacks,
  })
}

function editHonorario(name) {
  showModal({
    name,
    doctype: 'CRM Honorario',
    title: 'Honorário',
    callbacks: honorarioCallbacks,
  })
}
</script>
