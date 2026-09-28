<template>
  <div class="mg" :style="{ background: fundo }">
    <template v-if="modelo === 'twitter'">
      <div class="mg-avatar-bio" style="top: 42cqw; left: 18cqw; width: 8cqw; height: 8cqw">
        <span class="mg-avatar-bio-mark">?</span>
      </div>
      <div class="mg-el mg-nome" style="top: 43.3cqw; left: 28cqw; right: 9cqw; color: #ffffff">
        {{ nomeMarca || __('Sua marca') }}
        <span class="mg-verificado" :style="{ background: '#3897f0' }">✓</span>
      </div>
      <div class="mg-el mg-tag" style="top: 49cqw; left: 28cqw; right: 9cqw; color: #9fb0b5">{{ handle }}</div>

      <div class="mg-el mg-texto" style="top: 53cqw; left: 18cqw; right: 14cqw; color: #d0d0d0">
        {{ __('Texto de exemplo mostrando como fica o conteúdo gerado, já com a cor e o nome da sua marca.') }}
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
      <div class="mg-el mg-tag-topo" style="top: 2cqw; left: 6cqw; color: rgba(255,255,255,.7)">{{ handle }}</div>
      <div class="mg-el mg-tag-topo" style="top: 2cqw; right: 6cqw; color: rgba(255,255,255,.7)">{{ __('Carrossel') }}</div>

      <div class="mg-pill" style="top: 50cqw; left: 14cqw; height: 4.8cqw">
        <span class="mg-pill-avatar" />
        <span class="mg-pill-handle">{{ handle }}</span>
      </div>

      <div class="mg-el mg-titulo" style="top: 56.8cqw; left: 14cqw; right: 6cqw; color: #ffffff">
        {{ __('Título chamativo aqui') }}
      </div>
      <div class="mg-el mg-subtitulo" style="top: 81cqw; left: 14cqw; right: 6cqw; color: rgba(255,255,255,.55)">
        {{ __('Subtítulo curto de apoio') }}
      </div>
      <div class="mg-el mg-rodape" style="top: 95cqw; left: 6cqw; color: rgba(255,255,255,.45)">{{ __('Categoria') }}</div>
      <div class="mg-el mg-rodape" style="top: 95cqw; right: 6cqw; color: rgba(255,255,255,.45)">{{ __('Arraste') }}</div>
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
.mg-avatar-bio {
  position: absolute;
  border-radius: 50%;
  background: #2f2f2f;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mg-avatar-bio-mark {
  font-family: Arial, sans-serif;
  font-size: 4cqw;
  color: rgba(255, 255, 255, 0.35);
}
.mg-pill {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 1.2cqw;
  padding: 0 1.4cqw;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}
.mg-pill-avatar {
  width: 3.5cqw;
  height: 3.5cqw;
  min-width: 12px;
  min-height: 12px;
  border-radius: 50%;
  background: #ffffff;
  flex: none;
}
.mg-pill-handle {
  font-family: Arial, sans-serif;
  font-size: 2.1cqw;
  color: #ffffff;
  white-space: nowrap;
}
.mg-verificado {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3cqw;
  height: 3cqw;
  min-width: 13px;
  min-height: 13px;
  border-radius: 50%;
  color: #ffffff;
  font-size: 1.8cqw;
  line-height: 1;
  margin-left: 0.4cqw;
  vertical-align: middle;
}
.mg-el {
  position: absolute;
  font-family: Arial, sans-serif;
  line-height: 1.3;
}
.mg-nome { font-size: 3.6cqw; font-weight: 700; }
.mg-tag { font-size: 2.2cqw; }
.mg-tag-topo { font-size: 2.1cqw; }
.mg-titulo { font-size: 6.5cqw; font-weight: 700; line-height: 1.12; }
.mg-subtitulo { font-size: 2.8cqw; }
.mg-rodape { font-size: 2cqw; }
.mg-texto { font-size: 2.8cqw; line-height: 1.5; }
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
