<template>
  <div class="mp" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mp-avatar" />
      <div class="mp-el" style="top: 10cqw; left: 27cqw; width: 45cqw; height: 6cqw; background: #ffffff" />
      <div class="mp-el" style="top: 18cqw; left: 27cqw; width: 30cqw; height: 5cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 32cqw; left: 9cqw; width: 82cqw; height: 8cqw; background: #ffffff" />
      <div class="mp-el" style="top: 42cqw; left: 9cqw; width: 55cqw; height: 8cqw; background: #ffffff" />
      <div class="mp-el" style="top: 56cqw; left: 9cqw; width: 82cqw; height: 4cqw; background: #c7d3d6" />
      <div class="mp-el" style="top: 63cqw; left: 9cqw; width: 65cqw; height: 4cqw; background: #c7d3d6" />
      <div class="mp-image" style="top: 74cqw; bottom: 9cqw; background: rgba(255,255,255,.2)" />
    </template>
    <template v-else-if="modelo === 'citacao'">
      <div class="mp-el" style="top: 9cqw; left: 9cqw; width: 82cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 19cqw; left: 9cqw; width: 55cqw; height: 8cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 34cqw; left: 9cqw; width: 82cqw; height: 4cqw; background: #999999" />
      <div class="mp-el" style="top: 41cqw; left: 9cqw; width: 65cqw; height: 4cqw; background: #999999" />
      <div class="mp-image" style="top: 52cqw; bottom: 9cqw; background: #e4e4e4" />
    </template>
    <template v-else>
      <div class="mp-el" style="top: 12cqw; left: 9cqw; width: 40cqw; height: 4cqw; background: #ffffff; opacity: .85" />
      <div class="mp-el" style="top: 34cqw; left: 9cqw; width: 82cqw; height: 9cqw; background: #ffffff" />
      <div class="mp-el" style="top: 45cqw; left: 9cqw; width: 55cqw; height: 9cqw; background: #ffffff" />
      <div class="mp-el" style="top: 62cqw; left: 9cqw; width: 75cqw; height: 4cqw" :style="{ background: corDestaque }" />
      <div class="mp-el" style="top: 69cqw; left: 9cqw; width: 55cqw; height: 4cqw" :style="{ background: corDestaque }" />
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
.mp-avatar {
  position: absolute;
  top: 9cqw;
  left: 9cqw;
  width: 16cqw;
  height: 16cqw;
  border-radius: 50%;
  background: #ffffff;
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
