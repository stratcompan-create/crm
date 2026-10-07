<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Contas" />
    </template>
    <template #right-header>
      <Button variant="solid" :label="__('Criar')" iconLeft="plus" @click="createAccount" />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="accounts"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Client Account"
    :options="{ allowedViews: ['list'] }"
  />
  <ListView
    v-if="accounts.data && rows.length"
    :columns="columns"
    :rows="rows"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: accounts.data.row_count,
      totalCount: accounts.data.total_count,
    }"
    row-key="name"
  >
    <ListHeader class="mx-3 sm:mx-5" @columnWidthUpdated="() => triggerResize++">
      <ListHeaderItem v-for="column in columns" :key="column.key" :item="column" />
    </ListHeader>
    <ListRows v-slot="{ column, item, row }" class="mx-3 sm:mx-5" :rows="rows" doctype="CRM Client Account">
      <Button
        v-if="column.key === 'acoes'"
        class="shrink-0"
        variant="ghost"
        size="sm"
        :disabled="!row.url"
        :label="__('Abrir')"
        @click.stop="openAccount(row.url)"
      />
      <ListRowItem
        v-else
        :item="item"
        :align="column.align"
        class="overflow-hidden"
        @click.stop="editAccount(row.name)"
      />
    </ListRows>
    <ListFooter
      class="border-t px-3 py-2 sm:px-5"
      v-model="accounts.data.page_length_count"
      :options="{
        rowCount: accounts.data.row_count,
        totalCount: accounts.data.total_count,
      }"
      @loadMore="() => loadMore++"
    />
  </ListView>
  <EmptyState
    v-else-if="accounts.data && !rows.length"
    name="Contas"
    :icon="AccountsIcon"
    :title="__('Nenhuma conta ainda')"
    :description="__('Cadastre os CRMs dos seus clientes aqui para acessar o link de cada um rapidamente.')"
  />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import AccountsIcon from '~icons/lucide/building-2'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { timestampCell } from '@/composables/useTimelinePreferences'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  ListFooter,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const accounts = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (!accounts.value?.data?.data) return []
  return parseRows(accounts.value.data.data, accounts.value.data.columns)
})

// coluna extra, so pra renderizar o botao "Abrir" - nao existe um campo
// "acoes" no doctype, essa coluna nunca tem ListRowItem, so o botao (ver
// o v-if/v-else no ListRows acima). Fica por ultimo na linha, depois de
// "Ultima modificacao", em vez de empurrado pra baixo do endereco do CRM.
const columns = computed(() => {
  const cols = accounts.value?.data?.columns || []
  if (!cols.length) return cols
  return [...cols, { key: 'acoes', label: __('Ações'), type: 'Data', width: '8rem' }]
})

function parseRows(data, columns = []) {
  return data.map((acc) => {
    let _row = {}
    accounts.value?.data.rows.forEach((fieldname) => {
      _row[fieldname] = acc[fieldname]
      let fieldType = columns?.find((col) => (col.key || col.value) == fieldname)?.type
      if (fieldType === 'Datetime') {
        _row[fieldname] = timestampCell(acc[fieldname])
      }
    })
    return _row
  })
}

function openAccount(url) {
  window.open(url, '_blank', 'noopener')
}

const { showModal } = useDoctypeModal()

const accountCallbacks = {
  afterInsert: () => accounts.value.reload(),
  afterUpdate: () => accounts.value.reload(),
}

function createAccount() {
  showModal({
    doctype: 'CRM Client Account',
    title: 'Conta',
    callbacks: accountCallbacks,
  })
}

function editAccount(name) {
  showModal({
    name,
    doctype: 'CRM Client Account',
    title: 'Conta',
    callbacks: accountCallbacks,
  })
}
</script>
