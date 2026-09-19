<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Equipe') }}</div>
    </template>
    <template #right-header>
      <Button
        v-if="isManager()"
        variant="solid"
        :label="__('Adicionar Membro')"
        icon-left="lucide-user-plus"
        @click="addMember"
      />
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <div v-if="loading" class="py-10 text-center text-p-sm text-ink-gray-5">
      {{ __('Carregando...') }}
    </div>

    <div v-else-if="!members.length" class="py-10 text-center text-p-sm text-ink-gray-5">
      {{ __('Nenhum membro da equipe ainda') }}
    </div>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="member in members"
        :key="member.name"
        class="flex flex-col gap-4 rounded-lg border border-outline-gray-2 bg-surface-white p-4"
      >
        <div class="flex items-center gap-3">
          <Avatar :label="member.full_name" :image="member.user_image" size="xl" />
          <div class="flex flex-col overflow-hidden">
            <div class="truncate text-p-base-medium text-ink-gray-9">{{ member.full_name }}</div>
            <div class="truncate text-p-sm text-ink-gray-5">{{ member.email }}</div>
          </div>
          <Badge class="ml-auto shrink-0" :label="roleLabel(member.role)" variant="subtle" />
        </div>

        <div class="border-t border-outline-gray-2 pt-3">
          <div class="mb-2 flex items-center justify-between text-p-sm text-ink-gray-6">
            <span>{{ __('Tarefas') }}</span>
            <span>{{ openTaskCount(member) }} {{ __('em aberto') }}</span>
          </div>
          <div v-if="!tasksByUser[member.name]?.length" class="text-p-sm italic text-ink-gray-4">
            {{ __('Nenhuma tarefa atribuída') }}
          </div>
          <div v-else class="flex flex-col gap-1.5">
            <div
              v-for="task in tasksByUser[member.name].slice(0, 4)"
              :key="task.name"
              class="flex items-center justify-between gap-2 text-p-sm"
            >
              <span class="truncate text-ink-gray-8">{{ task.title }}</span>
              <Badge :label="statusLabel(task.status)" :theme="statusTheme(task.status)" variant="subtle" />
            </div>
            <div v-if="tasksByUser[member.name].length > 4" class="text-p-sm text-ink-gray-5">
              +{{ tasksByUser[member.name].length - 4 }} {{ __('outras') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { usersStore } from '@/stores/users'
import { Avatar, Badge, Button, call } from 'frappe-ui'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { ref, computed, onMounted } from 'vue'

const { crmUsers, users, isManager } = usersStore()

const loading = ref(true)
const allTasks = ref([])

const members = computed(() => crmUsers.value || [])

const tasksByUser = computed(() => {
  const map = {}
  for (const task of allTasks.value) {
    if (!task.assigned_to) continue
    if (!map[task.assigned_to]) map[task.assigned_to] = []
    map[task.assigned_to].push(task)
  }
  return map
})

function openTaskCount(member) {
  const tasks = tasksByUser.value[member.name] || []
  return tasks.filter((t) => !['Done', 'Canceled'].includes(t.status)).length
}

function addMember() {
  // Reuses the CRM's own invite flow (Configurações > Convidar Usuário),
  // which already lets the owner pick the member's role (Vendedor/Gestor/
  // Admin) - the same access-limit control they asked for, for free.
  activeSettingsPage.value = __('Invite User')
  showSettings.value = true
}

const ROLE_LABELS = {
  'System Manager': () => __('Administrador'),
  'Sales Manager': () => __('Gestor de Vendas'),
  'Sales User': () => __('Usuário de Vendas'),
}

function roleLabel(role) {
  return ROLE_LABELS[role]?.() || role || __('Sem função')
}

const STATUS_LABELS = {
  Backlog: () => __('Pendente'),
  Todo: () => __('A Fazer'),
  'In Progress': () => __('Em Andamento'),
  Done: () => __('Concluída'),
  Canceled: () => __('Cancelada'),
}

function statusLabel(status) {
  return STATUS_LABELS[status]?.() || status
}

function statusTheme(status) {
  if (status === 'Done') return 'green'
  if (status === 'Canceled') return 'red'
  if (status === 'In Progress') return 'blue'
  return 'gray'
}

onMounted(async () => {
  await users.promise
  const emails = (crmUsers.value || []).map((u) => u.name)
  if (!emails.length) {
    loading.value = false
    return
  }
  try {
    allTasks.value = await call('frappe.client.get_list', {
      doctype: 'CRM Task',
      filters: { assigned_to: ['in', emails] },
      fields: ['name', 'title', 'status', 'assigned_to', 'due_date'],
      order_by: 'due_date asc',
      limit_page_length: 0,
    })
  } finally {
    loading.value = false
  }
})
</script>
