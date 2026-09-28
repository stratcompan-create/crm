<template>
  <div class="mp" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mp-avatar-bio" style="top: 36cqw; left: 10cqw; width: 15cqw; height: 15cqw" />
      <div class="mp-el" style="top: 40cqw; left: 28cqw; width: 45cqw; height: 5.5cqw; background: #ffffff" />
      <div class="mp-el" style="top: 47cqw; left: 28cqw; width: 30cqw; height: 4cqw; background: #9fb0b5" />
      <div class="mp-el" style="top: 58cqw; left: 10cqw; width: 80cqw; height: 4cqw; background: #666666" />
      <div class="mp-el" style="top: 64cqw; left: 10cqw; width: 60cqw; height: 4cqw; background: #666666" />
    </template>
    <template v-else-if="modelo === 'citacao'">
      <div class="mp-el" style="top: 9cqw; left: 9cqw; width: 82cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 19cqw; left: 9cqw; width: 55cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 34cqw; left: 9cqw; width: 82cqw; height: 4cqw; background: #999999" />
      <div class="mp-el" style="top: 41cqw; left: 9cqw; width: 65cqw; height: 4cqw; background: #999999" />
      <div class="mp-image" style="top: 52cqw; bottom: 9cqw; background: #e4e4e4" />
    </template>
    <template v-else>
      <div class="mp-el" style="top: 4cqw; left: 8cqw; width: 22cqw; height: 3cqw; background: rgba(255,255,255,.75)" />
      <div class="mp-el" style="top: 4cqw; right: 8cqw; width: 16cqw; height: 3cqw; background: rgba(255,255,255,.75)" />
      <div class="mp-pill" style="top: 55cqw; left: 8cqw; width: 30cqw; height: 5.2cqw" />
      <div class="mp-el" style="top: 64cqw; left: 8cqw; width: 84cqw; height: 8cqw; background: #ffffff" />
      <div class="mp-el" style="top: 74cqw; left: 8cqw; width: 65cqw; height: 8cqw; background: #ffffff" />
      <div class="mp-el" style="top: 84cqw; left: 8cqw; width: 60cqw; height: 3cqw; background: rgba(255,255,255,.55)" />
    </template>
  </div>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelo: { type: String, default: 'padrao' },
  corMarca: { type: String, default: '#042d3c' },
  corDestaque: { type: String, default: '#8aa1a9' },
})

const fundo = computed(() => (props.modelo === 'citacao' ? '#ffffff' : props.corMarca))
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
.mp-pill {
  position: absolute;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
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
