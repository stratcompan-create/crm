<template>
  <span
    class="inline-flex shrink-0 items-center gap-1 rounded-full bg-surface-violet-2 px-1.5 py-0.5 text-2xs font-medium text-ink-violet-8"
    :title="texto"
  >
    <span class="lucide-sparkles size-2.5" aria-hidden="true" />
    {{ __('IA') }}
  </span>
</template>

<script setup>
defineProps({
  texto: {
    type: String,
    default: () => __('Usa inteligência artificial. Quando o crédito de IA está ligado, essa ação consome o saldo.'),
  },
})
</script>
