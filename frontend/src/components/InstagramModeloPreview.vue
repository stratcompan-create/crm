<template>
  <div class="mp" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mp-row">
        <div class="mp-avatar" />
        <div class="mp-col">
          <div class="mp-line mp-line-strong" style="width: 60%; background: #ffffff" />
          <div class="mp-line" style="width: 40%" :style="{ background: corDestaque }" />
        </div>
      </div>
      <div class="mp-line mp-title" style="width: 85%; background: #ffffff" />
      <div class="mp-line mp-title" style="width: 55%; background: #ffffff" />
      <div class="mp-line" style="width: 90%; background: #c7d3d6" />
      <div class="mp-line" style="width: 70%; background: #c7d3d6" />
      <div class="mp-image" style="background: rgba(255,255,255,.18)" />
    </template>
    <template v-else-if="modelo === 'citacao'">
      <div class="mp-line mp-title" style="width: 85%" :style="{ background: corDestaque }" />
      <div class="mp-line mp-title" style="width: 55%" :style="{ background: corDestaque }" />
      <div class="mp-line" style="width: 90%; background: #999999" />
      <div class="mp-line" style="width: 70%; background: #999999" />
      <div class="mp-image" style="background: #e4e4e4" />
    </template>
    <template v-else>
      <div class="mp-line" style="width: 45%; background: #ffffff; opacity: .85" />
      <div class="mp-line mp-title" style="width: 85%; background: #ffffff" />
      <div class="mp-line mp-title" style="width: 55%; background: #ffffff" />
      <div class="mp-line" style="width: 80%" :style="{ background: corDestaque }" />
      <div class="mp-line" style="width: 60%" :style="{ background: corDestaque }" />
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
  aspect-ratio: 1 / 1;
  border-radius: 10%;
  padding: 10cqw 9cqw;
  display: flex;
  flex-direction: column;
  gap: 5cqw;
  overflow: hidden;
}
.mp-row { display: flex; align-items: center; gap: 4cqw; margin-bottom: 2cqw; }
.mp-avatar { width: 16cqw; height: 16cqw; border-radius: 50%; background: #ffffff; flex-shrink: 0; }
.mp-col { display: flex; flex-direction: column; gap: 2.5cqw; flex: 1; }
.mp-line { height: 6cqw; border-radius: 2cqw; }
.mp-line-strong { height: 6cqw; }
.mp-title { height: 9cqw; }
.mp-image { margin-top: auto; height: 26cqw; border-radius: 8%; }
</style>
