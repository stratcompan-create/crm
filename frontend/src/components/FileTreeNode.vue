<template>
  <div>
    <div
      class="group flex items-center gap-1.5 rounded px-2 py-1.5 cursor-pointer select-none hover:bg-surface-gray-2"
      :style="{ paddingLeft: depth * 18 + 8 + 'px' }"
      @click="onClick"
    >
      <span
        v-if="node.is_folder"
        class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-5 transition-transform duration-150 ease-in-out"
        :class="{ 'rotate-90': expanded }"
        aria-hidden="true"
      />
      <span v-else class="size-3.5 shrink-0" />

      <span
        v-if="node.is_folder"
        class="size-4 shrink-0"
        :class="expanded ? 'lucide-folder-open' : 'lucide-folder'"
        aria-hidden="true"
      />
      <span v-else class="lucide-file size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />

      <span class="truncate text-p-sm text-ink-gray-8">{{ node.file_name }}</span>

      <Button
        v-if="node.is_folder"
        variant="ghost"
        size="sm"
        class="ml-auto opacity-0 group-hover:opacity-100"
        @click.stop="startNewFolder"
      >
        <template #icon>
          <span class="lucide-folder-plus size-3.5" aria-hidden="true" />
        </template>
      </Button>
    </div>

    <div v-if="node.is_folder && expanded">
      <div
        v-if="creatingFolder"
        class="flex items-center gap-1.5 py-1"
        :style="{ paddingLeft: (depth + 1) * 18 + 30 + 'px' }"
      >
        <span class="lucide-folder size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
        <input
          ref="newFolderInputRef"
          v-model="newFolderName"
          type="text"
          class="form-input w-40 text-p-sm"
          :placeholder="__('Nome da pasta')"
          @keydown.enter="confirmNewFolder"
          @keydown.esc="creatingFolder = false"
          @blur="confirmNewFolder"
        />
      </div>

      <div
        v-if="loading"
        class="text-p-sm text-ink-gray-5"
        :style="{ paddingLeft: (depth + 1) * 18 + 30 + 'px' }"
      >
        {{ __('Carregando...') }}
      </div>
      <FileTreeNode v-for="child in children" :key="child.name" :node="child" :depth="depth + 1" />
      <div
        v-if="!loading && !children.length && !creatingFolder"
        class="text-p-sm italic text-ink-gray-4"
        :style="{ paddingLeft: (depth + 1) * 18 + 30 + 'px' }"
      >
        {{ __('Pasta vazia') }}
      </div>
    </div>
  </div>
</template>
<script setup>
import { Button, call, toast } from 'frappe-ui'
import { ref, nextTick } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
})

const expanded = ref(false)
const loading = ref(false)
const children = ref([])
const loaded = ref(false)
const creatingFolder = ref(false)
const newFolderName = ref('')
const newFolderInputRef = ref(null)

async function loadChildren() {
  loading.value = true
  try {
    const res = await call('frappe.core.api.file.get_files_in_folder', {
      folder: props.node.name,
    })
    children.value = (res?.files || []).slice().sort((a, b) => {
      if (a.is_folder !== b.is_folder) return a.is_folder ? -1 : 1
      return a.file_name.localeCompare(b.file_name)
    })
    loaded.value = true
  } finally {
    loading.value = false
  }
}

async function onClick() {
  if (!props.node.is_folder) {
    window.open(props.node.file_url, '_blank', 'noopener')
    return
  }
  expanded.value = !expanded.value
  if (expanded.value && !loaded.value) {
    await loadChildren()
  }
}

async function startNewFolder() {
  if (!expanded.value) {
    expanded.value = true
    if (!loaded.value) await loadChildren()
  }
  creatingFolder.value = true
  newFolderName.value = ''
  await nextTick()
  newFolderInputRef.value?.focus()
}

async function confirmNewFolder() {
  if (!creatingFolder.value) return
  const name = newFolderName.value.trim()
  creatingFolder.value = false
  if (!name) return
  try {
    await call('frappe.core.api.file.create_new_folder', {
      file_name: name,
      folder: props.node.name,
    })
    await loadChildren()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Falha ao criar pasta'))
  }
}

defineExpose({ reload: loadChildren })
</script>
