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
        v-if="open && data.ia && custom.length"
        variant="subtle"
        size="sm"
        iconLeft="lucide-refresh-cw"
        :label="__('Gerar outras')"
        :loading="loadingAi"
        @click="generate(true)"
      />
    </div>

    <template v-if="open">
      <!-- gerando -->
      <div v-if="loadingAi && !custom.length" class="mt-2 flex items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-4 text-p-sm text-ink-gray-6">
        <span class="lucide-sparkles size-4 animate-pulse" aria-hidden="true" />
        {{ __('Escrevendo três respostas para esta conversa...') }}
      </div>

      <!-- sob medida -->
      <div v-if="custom.length" class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
        <div
          v-for="(s, i) in custom"
          :key="'c' + i"
          class="flex flex-col justify-between gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-2.5"
        >
          <div>
            <div class="mb-1 flex items-center gap-1.5 text-xs font-medium text-ink-gray-6">
              <span class="lucide-sparkles size-3" aria-hidden="true" />
              {{ s.titulo }}
            </div>
            <div class="whitespace-pre-wrap text-p-sm text-ink-gray-8">{{ s.texto }}</div>
          </div>
          <Button variant="subtle" size="sm" :label="__('Usar e editar')" @click="$emit('usar', s.texto)" />
        </div>
      </div>

      <!-- modelos prontos: só quando não há IA, ou se a pessoa quiser ver -->
      <div v-if="showTemplates">
        <div v-if="custom.length" class="mb-1 mt-3 text-xs font-medium text-ink-gray-5">{{ __('Modelos prontos') }}</div>
        <div class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
          <div
            v-for="(s, i) in data.modelos"
            :key="'m' + i"
            class="flex flex-col justify-between gap-2 rounded-lg border border-outline-gray-2 bg-surface-white p-2.5"
          >
            <div>
              <div class="mb-1 text-xs font-medium text-ink-gray-6">{{ s.titulo }}</div>
              <div class="line-clamp-5 text-p-sm text-ink-gray-8">{{ s.texto }}</div>
            </div>
            <Button variant="subtle" size="sm" :label="__('Usar e editar')" @click="$emit('usar', s.texto)" />
          </div>
        </div>
      </div>

      <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-gray-5">
        <span>{{ __('Nada é enviado sozinho: a sugestão vai para a caixa de resposta e você ajusta antes de enviar.') }}</span>
        <button v-if="custom.length" type="button" class="underline" @click="templatesOpen = !templatesOpen">
          {{ templatesOpen ? __('Esconder modelos prontos') : __('Ver modelos prontos') }}
        </button>
      </div>
      <p v-if="!data.ia" class="mt-1 text-xs text-ink-amber-3">
        {{ __('Estes são modelos gerais. Para respostas escritas para cada conversa, um gestor precisa ligar a IA em Configurações → Automações.') }}
      </p>
      <ErrorMessage v-if="error" class="mt-1" :message="error" />
    </template>
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
const generated = ref([])
const templatesOpen = ref(false)

const suggestions = createResource({
  url: 'crm.api.sugestoes.get_suggestions',
  makeParams: () => ({ lead: props.lead }),
  onSuccess(d) {
    generated.value = []
    error.value = ''
    templatesOpen.value = false
    // com a IA ligada, cada mensagem nova do lead ganha três respostas próprias
    if (d?.ativo && d.ia && !d.sob_medida?.length) generate(false)
  },
})
const data = computed(() => suggestions.data)
const custom = computed(() => (generated.value.length ? generated.value : data.value?.sob_medida || []))
const showTemplates = computed(
  () => !!data.value?.modelos?.length && (!data.value.ia || templatesOpen.value || (!custom.value.length && !loadingAi.value)),
)

watch(
  () => [props.lead, props.version],
  () => props.lead && suggestions.fetch(),
  { immediate: true },
)

async function generate(force) {
  const lead = props.lead
  loadingAi.value = true
  error.value = ''
  try {
    const r = await call('crm.api.sugestoes.generate_ai_suggestions', { lead, force: force ? 1 : 0 })
    if (lead === props.lead) generated.value = r.sugestoes || []
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível gerar as sugestões agora.')
  } finally {
    loadingAi.value = false
  }
}
</script>
