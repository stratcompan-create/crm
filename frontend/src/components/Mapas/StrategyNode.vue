<template>
  <!-- Nota adesiva -->
  <div
    v-if="type === 'sticky'"
    class="min-w-[160px] max-w-[260px] whitespace-pre-wrap break-words rounded-md p-3 text-sm shadow-md"
    :style="{ background: colors.bg, color: colors.ink, outline: selected ? '2px solid ' + colors.border : 'none' }"
  >
    {{ data.label }}
    <Handle v-for="h in handles" :id="h.id" :key="h.id" type="source" :position="h.pos" />
  </div>

  <!-- Texto solto -->
  <div
    v-else-if="type === 'text'"
    class="max-w-[320px] whitespace-pre-wrap break-words px-1 text-lg font-semibold"
    :style="{ color: colors.ink, outline: selected ? '2px dashed ' + colors.border : 'none' }"
  >
    {{ data.label }}
    <Handle v-for="h in handles" :id="h.id" :key="h.id" type="source" :position="h.pos" />
  </div>

  <!-- Bloco com ícone -->
  <div
    v-else
    class="flex min-w-[190px] max-w-[240px] items-start gap-2.5 rounded-xl border-2 px-3 py-2.5 shadow-sm"
    :style="{ borderColor: colors.border, background: colors.bg, boxShadow: selected ? '0 0 0 3px ' + colors.border + '55' : '' }"
  >
    <span
      class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg"
      :style="{ background: colors.border, color: '#fff' }"
    >
      <span :class="iconCls" class="size-4" aria-hidden="true" />
    </span>
    <div class="min-w-0">
      <div class="break-words text-sm font-semibold leading-snug" :style="{ color: colors.ink }">{{ data.label }}</div>
      <div v-if="data.note" class="mt-0.5 whitespace-pre-wrap break-words text-xs leading-snug text-gray-600">{{ data.note }}</div>
    </div>
    <Handle v-for="h in handles" :id="h.id" :key="h.id" type="source" :position="h.pos" />
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'
import { colorOf, iconClass } from './mapIcons'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean,
})

const colors = computed(() => colorOf(props.data?.color))
const iconCls = computed(() => iconClass(props.data?.icon))
const handles = [
  { id: 'top', pos: Position.Top },
  { id: 'right', pos: Position.Right },
  { id: 'bottom', pos: Position.Bottom },
  { id: 'left', pos: Position.Left },
]
</script>
