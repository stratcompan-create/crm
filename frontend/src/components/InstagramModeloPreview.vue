<template>
  <div class="mp" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mp-avatar-bio" style="top: 40.4cqw; left: 18.6cqw; width: 4.5cqw; height: 4.5cqw; background: #3a3a3a" />
      <div class="mp-el" style="top: 39.8cqw; left: 25.5cqw; width: 34cqw; height: 4.5cqw; background: #1c1c1c" />
      <div class="mp-el" style="top: 46.4cqw; left: 25.5cqw; width: 24cqw; height: 3cqw; background: #8a8a8a" />
      <div class="mp-el" style="top: 54cqw; left: 18.6cqw; width: 68cqw; height: 3cqw; background: #8a8a8a" />
      <div class="mp-el" style="top: 58.5cqw; left: 18.6cqw; width: 50cqw; height: 3cqw; background: #8a8a8a" />
    </template>
    <template v-else-if="modelo === 'citacao'">
      <div class="mp-el" style="top: 9cqw; left: 9cqw; width: 82cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 19cqw; left: 9cqw; width: 55cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 34cqw; left: 9cqw; width: 82cqw; height: 4cqw; background: #999999" />
      <div class="mp-el" style="top: 41cqw; left: 9cqw; width: 65cqw; height: 4cqw; background: #999999" />
      <div class="mp-image" style="top: 52cqw; bottom: 9cqw; background: #e4e4e4" />
    </template>
    <template v-else>
      <div class="mp-el" style="top: 5.5cqw; left: 6cqw; width: 20cqw; height: 2.4cqw; background: #4a4a4a" />
      <div class="mp-el" style="top: 5.5cqw; right: 6cqw; width: 14cqw; height: 2.4cqw; background: #4a4a4a" />
      <div class="mp-el" style="top: 57cqw; left: 14cqw; width: 80cqw; height: 7.5cqw; background: #1c1c1c" />
      <div class="mp-el" style="top: 66cqw; left: 14cqw; width: 62cqw; height: 7.5cqw; background: #1c1c1c" />
      <div class="mp-el" style="top: 81cqw; left: 14cqw; width: 55cqw; height: 2.8cqw; background: #6b6b6b" />
      <div class="mp-el" style="top: 93cqw; left: 6cqw; width: 18cqw; height: 2cqw; background: #8a8a8a" />
    </template>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { COR_CLARA_PADRAO } from '@/utils/instagramTemplates'

const props = defineProps({
  modelo: { type: String, default: 'padrao' },
  corMarca: { type: String, default: '#042d3c' },
  corDestaque: { type: String, default: '#8aa1a9' },
})

const fundo = computed(() => {
  if (props.modelo === 'citacao') return '#ffffff'
  if (props.modelo === 'padrao' || props.modelo === 'twitter') return COR_CLARA_PADRAO
  return props.corMarca
})
</script>
<style scoped>
.mp {
  container-type: inline-size;
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 10%;
  overflow: hidden;
}
.mp-avatar-bio {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
.mp-el {
  position: absolute;
  border-radius: 2cqw;
}
.mp-image {
  position: absolute;
  left: 9cqw;
  right: 9cqw;
  bottom: 9cqw;
  border-radius: 8%;
}
</style>
