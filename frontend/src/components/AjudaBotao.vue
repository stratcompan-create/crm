<template>
  <div>
    <button
      v-if="!aberto"
      type="button"
      class="fixed bottom-6 right-20 z-20 flex size-10 items-center justify-center rounded-full border border-outline-gray-2 bg-white text-lg font-semibold text-ink-gray-7 shadow-lg hover:bg-surface-gray-1"
      :title="__('Ajuda')"
      @click="abrir"
    >
      ?
    </button>
    <div v-else class="fixed inset-y-0 right-0 z-30 flex w-full flex-col border-l border-outline-gray-1 bg-white shadow-xl sm:w-[420px]">
      <div class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-3">
        <div class="text-lg-semibold text-ink-gray-9">{{ __('Ajuda') }}</div>
        <Button variant="ghost" icon="x" @click="aberto = false" />
      </div>
      <div class="flex-1 overflow-y-auto px-4 py-3">
        <template v-if="dados.data">
          <div v-if="dados.data.desta_tela.length" class="mb-2 text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Nesta tela') }}</div>
          <Guia v-for="g in dados.data.desta_tela" :key="g.chave" :guia="g" :aberto="true" />
          <div class="mb-2 mt-4 text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Todos os guias') }}</div>
          <Guia v-for="g in dados.data.outros" :key="g.chave" :guia="g" :aberto="false" />
        </template>
        <div v-else class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, createResource } from 'frappe-ui'
import { defineComponent, h, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const aberto = ref(false)
const dados = createResource({ url: 'crm.api.ajuda.guias', makeParams: () => ({ tela: route.name || '' }) })
function abrir() {
  aberto.value = true
  dados.reload()
}

function embed(url) {
  const m = /(?:youtu\.be\/|v=|embed\/)([\w-]{11})/.exec(url || '')
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}` : ''
}

const Guia = defineComponent({
  props: { guia: Object, aberto: Boolean },
  setup(props) {
    const open = ref(props.aberto)
    return () =>
      h('div', { class: 'mb-2 rounded-lg border border-outline-gray-2' }, [
        h('button', { type: 'button', class: 'flex w-full items-center justify-between px-3 py-2 text-left text-p-sm font-medium text-ink-gray-8', onClick: () => (open.value = !open.value) }, [
          props.guia.titulo,
          h('span', { class: 'text-ink-gray-5' }, open.value ? '−' : '+'),
        ]),
        open.value
          ? h('div', { class: 'px-3 pb-3' }, [
              embed(props.guia.video)
                ? h('iframe', { class: 'mb-2 aspect-video w-full rounded', src: embed(props.guia.video), allowfullscreen: true, title: props.guia.titulo })
                : h('div', { class: 'mb-2 rounded bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-5' }, __('Vídeo em breve')),
              h('ol', { class: 'list-decimal pl-5 text-p-sm text-ink-gray-7' }, props.guia.passos.map((p) => h('li', { class: 'mb-1' }, p))),
            ])
          : null,
      ])
  },
})
</script>
