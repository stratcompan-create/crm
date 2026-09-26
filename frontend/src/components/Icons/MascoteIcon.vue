<template>
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="4" width="16" height="13" rx="4" :fill="cor" />
    <circle cx="9" cy="10.5" r="1.3" fill="white" />
    <circle cx="15" cy="10.5" r="1.3" fill="white" />
    <rect x="7" y="18" width="2.6" height="3" rx="1.1" :fill="cor" />
    <rect x="14.4" y="18" width="2.6" height="3" rx="1.1" :fill="cor" />
  </svg>
</template>
<script setup>
defineProps({
  cor: { type: String, default: 'currentColor' },
})
</script>
