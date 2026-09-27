<template>
  <div class="mg" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mg-avatar" />
      <div class="mg-el mg-nome" style="top: 9cqw; left: 27cqw; right: 9cqw; color: #ffffff">{{ nomeMarca || __('Sua marca') }}</div>
      <div class="mg-el mg-titulo" style="top: 24cqw; left: 9cqw; right: 9cqw; color: #ffffff">{{ __('Título chamativo aqui') }}</div>
      <div class="mg-el mg-texto" style="top: 42cqw; left: 9cqw; right: 9cqw; color: #c7d3d6">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado, já com a cor e o nome da sua marca.') }}
      </div>
      <div class="mg-image" style="top: 66cqw; bottom: 9cqw; background: rgba(255,255,255,.14); border: 1px dashed rgba(255,255,255,.35)">
        <span class="mg-image-label" style="color: rgba(255,255,255,.75)">{{ __('sua foto aqui') }}</span>
      </div>
    </template>
    <template v-else-if="modelo === 'citacao'">
      <div class="mg-el mg-titulo" style="top: 9cqw; left: 9cqw; right: 9cqw" :style="{ color: corDestaque }">
        {{ __('Frase de impacto aqui') }}
      </div>
      <div class="mg-el mg-texto" style="top: 30cqw; left: 9cqw; right: 9cqw; color: #666666">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado pela IA, no estilo mais clean.') }}
      </div>
      <div class="mg-image" style="top: 52cqw; bottom: 9cqw; background: #e4e4e4; border: 1px dashed #b7b7b7">
        <span class="mg-image-label" style="color: #8a8a8a">{{ __('sua foto aqui') }}</span>
      </div>
    </template>
    <template v-else>
      <div class="mg-el mg-nome" style="top: 9cqw; left: 9cqw; right: 9cqw; color: #ffffff; opacity: .85">{{ nomeMarca || __('Sua marca') }}</div>
      <div class="mg-el mg-titulo" style="top: 26cqw; left: 9cqw; right: 9cqw; color: #ffffff">{{ __('Título chamativo aqui') }}</div>
      <div class="mg-el mg-texto" style="top: 50cqw; left: 9cqw; right: 9cqw" :style="{ color: corDestaque }">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado pela IA.') }}
      </div>
    </template>
  </div>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelo: { type: String, default: 'padrao' },
  corMarca: { type: String, default: '#042d3c' },
  corDestaque: { type: String, default: '#8aa1a9' },
  nomeMarca: { type: String, default: '' },
})

const fundo = computed(() => (props.modelo === 'citacao' ? '#ffffff' : props.corMarca))
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
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.mg-avatar {
  position: absolute;
  top: 9cqw;
  left: 9cqw;
  width: 15cqw;
  height: 15cqw;
  border-radius: 50%;
  background: #ffffff;
}
.mg-el {
  position: absolute;
  font-family: Arial, sans-serif;
  line-height: 1.3;
}
.mg-nome { font-size: 4.6cqw; font-weight: 700; }
.mg-titulo { font-size: 7.2cqw; font-weight: 700; }
.mg-texto { font-size: 3.6cqw; }
.mg-image {
  position: absolute;
  left: 9cqw;
  right: 9cqw;
  border-radius: 8%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mg-image-label {
  font-family: Arial, sans-serif;
  font-size: 3.4cqw;
  font-style: italic;
}
</style>
