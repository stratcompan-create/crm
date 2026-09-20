<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Instagram" />
    </template>
    <template #right-header>
      <Button
        :label="__('Configurações')"
        @click="openInstagramSettings"
      >
        <template #prefix>
          <SettingsIcon class="size-4" />
        </template>
      </Button>
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="messages"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Instagram Message"
    :options="{ allowedViews: ['list'] }"
  />
  <ListView
    v-if="messages.data && rows.length"
    :columns="columns"
    :rows="rows"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      onRowClick: (row) => router.push({ name: 'Lead', params: { leadId: row.lead } }),
      rowCount: messages.data.row_count,
      totalCount: messages.data.total_count,
    }"
    row-key="name"
  >
    <ListHeader class="mx-3 sm:mx-5" @columnWidthUpdated="() => triggerResize++">
      <ListHeaderItem v-for="column in columns" :key="column.key" :item="column" />
    </ListHeader>
    <ListRows
      v-slot="{ column, item, row }"
      class="mx-3 sm:mx-5"
      :rows="rows"
      doctype="CRM Instagram Message"
    >
      <div v-if="column.key === 'timestamp'" class="truncate text-base">
        <Tooltip :text="item?.label">
          <div>{{ item?.timeAgo }}</div>
        </Tooltip>
      </div>
      <div
        v-else-if="column.key === 'message'"
        class="flex w-full items-center gap-2 overflow-hidden"
      >
        <ListRowItem :item="item" :align="column.align" class="min-w-0 flex-1 overflow-hidden" />
        <Button
          class="shrink-0"
          variant="ghost"
          size="sm"
          :label="__('Responder')"
          @click.stop="openReply(row)"
        />
      </div>
      <ListRowItem
        v-else-if="column.key === 'direction'"
        :item="__(item)"
        :align="column.align"
        class="overflow-hidden"
      />
      <ListRowItem v-else :item="item" :align="column.align" class="overflow-hidden" />
    </ListRows>
    <ListFooter
      class="border-t px-3 py-2 sm:px-5"
      v-model="messages.data.page_length_count"
      :options="{
        rowCount: messages.data.row_count,
        totalCount: messages.data.total_count,
      }"
      @loadMore="() => loadMore++"
    />
  </ListView>
  <EmptyState v-else-if="messages.data && !rows.length" name="Instagram" :icon="ChatIcon" />

  <Dialog v-model="showReplyDialog" :options="{ title: __('Responder no Instagram'), size: 'sm' }">
    <template #body-content>
      <p class="mb-3 text-p-sm text-ink-gray-6">
        {{ __('Enviando pro lead') }}: {{ replyTarget?.lead }}
      </p>
      <FormControl
        type="textarea"
        v-model="replyMessage"
        :placeholder="__('Escreva sua resposta...')"
        rows="4"
      />
      <ErrorMessage v-if="replyError" class="mt-2" :message="replyError" />
    </template>
    <template #actions>
      <Button
        variant="solid"
        :label="__('Enviar')"
        :loading="sending"
        @click="sendReply"
      />
    </template>
  </Dialog>
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import ListRows from '@/components/ListViews/ListRows.vue'
import ChatIcon from '@/components/Icons/InstagramIcon.vue'
import SettingsIcon from '@/components/Icons/SettingsIcon.vue'
import { formatDate } from '@/utils'
import { timestampCell } from '@/composables/useTimelinePreferences'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRowItem,
  ListFooter,
  Dialog,
  FormControl,
  ErrorMessage,
  Tooltip,
  call,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const messages = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (!messages.value?.data?.data) return []
  return parseRows(messages.value.data.data, messages.value.data.columns)
})

const columns = computed(() => messages.value?.data?.columns || [])

function openInstagramSettings() {
  showSettings.value = true
  activeSettingsPage.value = 'Instagram'
}

function parseRows(data, columns = []) {
  return data.map((msg) => {
    let _row = {}
    messages.value?.data.rows.forEach((fieldname) => {
      _row[fieldname] = msg[fieldname]
      let fieldType = columns?.find((col) => (col.key || col.value) == fieldname)?.type
      if (fieldType === 'Datetime') {
        _row[fieldname] = timestampCell(msg[fieldname])
      }
    })
    return _row
  })
}

const showReplyDialog = ref(false)
const replyTarget = ref(null)
const replyMessage = ref('')
const replyError = ref('')
const sending = ref(false)

function openReply(row) {
  replyTarget.value = row
  replyMessage.value = ''
  replyError.value = ''
  showReplyDialog.value = true
}

async function sendReply() {
  if (!replyMessage.value.trim()) return
  sending.value = true
  replyError.value = ''
  try {
    await call('crm.api.instagram.send_reply', {
      lead: replyTarget.value.lead,
      message: replyMessage.value,
    })
    showReplyDialog.value = false
    messages.value.reload()
  } catch (e) {
    replyError.value = e.messages?.join(', ') || e.message || __('Falha ao enviar')
  } finally {
    sending.value = false
  }
}
</script>
