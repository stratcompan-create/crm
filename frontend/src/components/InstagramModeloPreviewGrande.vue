<template>
  <div class="mg" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mg-avatar">
        <div class="mg-avatar-mark" :style="{ borderColor: corDestaque }" />
      </div>
      <div class="mg-el mg-nome" style="top: 8.5cqw; left: 25cqw; right: 9cqw; color: #ffffff">
        {{ nomeMarca || __('Sua marca') }}
        <span class="mg-verificado" :style="{ background: '#3897f0' }">✓</span>
      </div>
      <div class="mg-el mg-tag" style="top: 14.5cqw; left: 25cqw; right: 9cqw; color: #9fb0b5">{{ handle }}</div>

      <div class="mg-el mg-titulo" style="top: 27cqw; left: 9cqw; right: 9cqw; color: #ffffff">
        {{ __('Título chamativo aqui') }}
      </div>
      <div class="mg-el mg-texto" style="top: 46cqw; left: 9cqw; right: 12cqw; color: #c7d3d6">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado, já com a cor e o nome da sua marca.') }}
      </div>

      <div class="mg-image" style="top: 68cqw; bottom: 9cqw; left: 9cqw; right: 34cqw; background: rgba(255,255,255,.08); border-color: rgba(255,255,255,.25)">
        <LucideImage class="mg-image-icon" style="color: rgba(255,255,255,.55)" />
        <span class="mg-image-label" style="color: rgba(255,255,255,.65)">{{ __('sua foto aqui') }}</span>
      </div>
    </template>

    <template v-else-if="modelo === 'citacao'">
      <div class="mg-el mg-titulo" style="top: 9cqw; left: 9cqw; right: 9cqw" :style="{ color: corDestaque }">
        {{ __('Frase de impacto aqui') }}
      </div>
      <div class="mg-el mg-texto" style="top: 30cqw; left: 9cqw; right: 9cqw; color: #666666">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado pela IA, no estilo mais clean.') }}
      </div>
      <div class="mg-image" style="top: 54cqw; bottom: 9cqw; left: 9cqw; right: 9cqw; background: #f2f2f2; border-color: #d8d8d8">
        <LucideImage class="mg-image-icon" style="color: #a0a0a0" />
        <span class="mg-image-label" style="color: #8a8a8a">{{ __('sua foto aqui') }}</span>
      </div>
    </template>

    <template v-else>
      <div class="mg-el mg-nome" style="top: 9cqw; left: 9cqw; right: 9cqw; color: #ffffff; opacity: .85">
        {{ nomeMarca || __('Sua marca') }}
      </div>
      <div class="mg-el mg-titulo" style="top: 27cqw; left: 9cqw; right: 9cqw; color: #ffffff">
        {{ __('Título chamativo aqui') }}
      </div>
      <div class="mg-el mg-texto" style="top: 52cqw; left: 9cqw; right: 9cqw" :style="{ color: corDestaque }">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado pela IA.') }}
      </div>
    </template>
  </div>
</template>
<script setup>
import LucideImage from '~icons/lucide/image'
import { computed } from 'vue'

const props = defineProps({
  modelo: { type: String, default: 'padrao' },
  corMarca: { type: String, default: '#042d3c' },
  corDestaque: { type: String, default: '#8aa1a9' },
  nomeMarca: { type: String, default: '' },
})

const fundo = computed(() => (props.modelo === 'citacao' ? '#ffffff' : props.corMarca))
const handle = computed(() => '@' + (props.nomeMarca || 'suamarca').toLowerCase().replace(/\s+/g, ''))
</script>
<style scoped>
.mg {
  container-type: inline-size;
  position: relative;
  width: 100%;
  max-width: 22rem;
  aspect-ratio: 1 / 1;
  border-radius: 6%;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
}
.mg-avatar {
  position: absolute;
  top: 8cqw;
  left: 8cqw;
  width: 14cqw;
  height: 14cqw;
  border-radius: 50%;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mg-avatar-mark {
  width: 45%;
  height: 45%;
  border: 0.9cqw solid;
  transform: rotate(45deg);
}
.mg-verificado {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.4cqw;
  height: 3.4cqw;
  min-width: 14px;
  min-height: 14px;
  border-radius: 50%;
  color: #ffffff;
  font-size: 2cqw;
  line-height: 1;
  margin-left: 0.4cqw;
  vertical-align: middle;
}
.mg-el {
  position: absolute;
  font-family: Arial, sans-serif;
  line-height: 1.3;
}
.mg-nome { font-size: 4.4cqw; font-weight: 700; }
.mg-tag { font-size: 2.8cqw; }
.mg-titulo { font-size: 7cqw; font-weight: 700; line-height: 1.18; }
.mg-texto { font-size: 3.4cqw; line-height: 1.5; }
.mg-image {
  position: absolute;
  border-radius: 9%;
  border: 1px dashed;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2cqw;
}
.mg-image-icon { width: 9cqw; height: 9cqw; }
.mg-image-label {
  font-family: Arial, sans-serif;
  font-size: 3cqw;
  font-style: italic;
}
</style>
