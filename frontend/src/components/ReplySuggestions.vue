<template>
  <div v-if="data?.ativo" class="border-t border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5">
    <div class="flex items-center justify-between gap-2">
      <button type="button" class="flex items-center gap-2 text-left" @click="open = !open">
        <span :class="open ? 'lucide-chevron-down' : 'lucide-chevron-right'" class="size-4 text-ink-gray-5" aria-hidden="true" />
        <span class="text-p-sm font-medium text-ink-gray-8">{{ __('Sugestões de resposta') }}</span>
        <span
          v-if="data.tema"
          class="rounded-full px-2 py-0.5 text-xs font-medium"
          :class="{
            'bg-surface-red-2 text-ink-red-6': data.tom === 'negative',
            'bg-surface-green-2 text-ink-green-3': data.tom === 'positive',
            'bg-surface-amber-2 text-ink-amber-3': data.tom === 'neutral',
          }"
        >
          {{ __(data.tema) }}
        </span>
      </button>
      <Button
        v-if="open && data.ia"
        variant="subtle"
        size="sm"
        iconLeft="lucide-sparkles"
        :label="__('Sob medida com IA')"
        :loading="loadingAi"
        @click="generateAi"
      />
    </div>

    <div v-if="open" class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
      <div
        v-for="(s, i) in all"
        :key="i"
        class="flex flex-col justify-between gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-2.5"
      >
        <div>
          <div class="mb-1 flex items-center gap-1.5 text-xs font-medium text-ink-gray-6">
            <span v-if="s.origem === 'ia'" class="lucide-sparkles size-3" aria-hidden="true" />
            {{ s.titulo }}
          </div>
          <div class="line-clamp-5 text-p-sm text-ink-gray-8">{{ s.texto }}</div>
        </div>
        <Button variant="subtle" size="sm" :label="__('Usar e editar')" @click="$emit('usar', s.texto)" />
      </div>
    </div>
    <p v-if="open" class="mt-2 text-xs text-ink-gray-5">
      {{ __('Nada é enviado sozinho: a sugestão vai para a caixa de resposta e você ajusta antes de enviar.') }}
      <span v-if="!data.ia">{{ __('Um gestor pode ligar a IA em Configurações → Automações para gerar respostas sob medida.') }}</span>
    </p>
    <ErrorMessage v-if="error" class="mt-1" :message="error" />
  </div>
</template>

<script setup>
import { Button, ErrorMessage, call, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({ lead: String, version: [Number, String] })
defineEmits(['usar'])

const open = ref(true)
const error = ref('')
const loadingAi = ref(false)
const aiOptions = ref([])

const suggestions = createResource({
  url: 'crm.api.sugestoes.get_suggestions',
  makeParams: () => ({ lead: props.lead }),
  onSuccess() {
    aiOptions.value = []
  },
})
const data = computed(() => suggestions.data)
const all = computed(() => [...aiOptions.value, ...(data.value?.sugestoes || [])])

watch(
  () => [props.lead, props.version],
  () => props.lead && suggestions.fetch(),
  { immediate: true },
)

async function generateAi() {
  loadingAi.value = true
  error.value = ''
  try {
    const r = await call('crm.api.sugestoes.generate_ai_suggestions', { lead: props.lead })
    aiOptions.value = r.sugestoes
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível gerar as sugestões agora.')
  } finally {
    loadingAi.value = false
  }
}
</script>
