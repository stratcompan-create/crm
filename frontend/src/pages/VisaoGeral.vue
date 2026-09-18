<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Visão Geral') }}</div>
    </template>
  </LayoutHeader>

  <EmptyState
    name="Arquivos"
    :icon="FolderIcon"
    :title="__('Seus arquivos')"
    :description="__('Use a barra lateral à esquerda para navegar, criar pastas e enviar arquivos — igual num explorador de arquivos.')"
  />
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import FolderIcon from '~icons/lucide/folder'
</script>
