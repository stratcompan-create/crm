<template>
  <Dialog v-model:open="show" :size="'sm'">
    <template #body>
      <div class="p-4 pt-5">
        <div class="flex justify-center">
          <div class="flex flex-col items-center">
            <img v-if="brand.logo" :src="brand.logo" class="mb-3 size-12 rounded object-contain" />
            <CRMLogo v-else class="mb-3 size-12" />
            <h3 class="text-2xl-semibold text-ink-gray-9">{{ brand.name || __('CRM') }}</h3>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import CRMLogo from '@/components/Icons/CRMLogo.vue'
import { getSettings } from '@/stores/settings'

let show = defineModel({ type: Boolean })

const { brand } = getSettings()
</script>
