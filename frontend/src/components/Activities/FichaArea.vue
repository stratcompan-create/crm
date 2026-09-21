<template>
  <div class="flex h-full flex-col overflow-y-auto pb-10 pt-4">
    <div v-if="!ficha.data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <div v-else class="mx-auto flex w-full max-w-4xl flex-col gap-5">
      <!-- Cabeçalho -->
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-lg-semibold text-ink-gray-9">{{ __('Ficha da reunião') }}</div>
          <div class="mt-0.5 text-p-sm text-ink-gray-6">
            {{ __('{0} de {1} pontos alinhados', [done, total]) }}
          </div>
          <div class="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-surface-gray-2">
            <div class="h-full rounded-full bg-[#042d3c] transition-all" :style="{ width: (done / total) * 100 + '%' }" />
          </div>
        </div>
        <Button variant="solid" iconLeft="lucide-file-text" :label="__('Colar transcrição da reunião')" @click="openTranscript" />
      </div>

      <!-- O que o CRM já sabe -->
      <div v-if="ficha.data.auto.length" class="rounded-lg bg-surface-gray-2 px-4 py-3">
        <div class="mb-2 text-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('O CRM já sabe') }}</div>
        <div class="flex flex-wrap gap-x-6 gap-y-1.5">
          <div v-for="a in ficha.data.auto" :key="a.label" class="text-p-sm">
            <span class="text-ink-gray-5">{{ __(a.label) }}:</span>
            <span class="ml-1 font-medium text-ink-gray-8">{{ a.valor }}</span>
          </div>
        </div>
      </div>

      <!-- Campos -->
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div
          v-for="f in ficha.data.rotulos"
          :key="f.chave"
          class="rounded-lg border p-3"
          :class="form[f.chave]?.trim() ? 'border-outline-gray-2' : 'border-outline-amber-2 bg-surface-amber-1'"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <span class="text-p-base-medium text-ink-gray-8">{{ __(f.rotulo) }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="form[f.chave]?.trim() ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-amber-2 text-ink-amber-3'"
            >
              {{ form[f.chave]?.trim() ? __('Alinhado') : __('Falta alinhar') }}
            </span>
          </div>
          <FormControl
            v-model="form[f.chave]"
            type="textarea"
            :rows="3"
            :placeholder="__('Escreva aqui ou cole a transcrição para preencher sozinho')"
            @blur="save"
          />
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3">
        <span class="text-p-sm text-ink-gray-5">{{ saved ? __('Salvo') : saving ? __('Salvando...') : '' }}</span>
        <Button
          v-if="doctype === 'CRM Deal'"
          variant="subtle"
          iconLeft="lucide-arrow-right"
          :label="__('Levar para a proposta')"
          :loading="applying"
          @click="toProposal"
        />
      </div>
    </div>

    <!-- Transcrição -->
    <Dialog v-model="showTranscript" :options="{ title: __('Transcrição da reunião'), size: '2xl' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Cole aqui a transcrição. O CRM preenche só os pontos que foram realmente conversados; o que não foi tratado fica como "Falta alinhar".') }}
          </p>
          <div v-if="!ficha.data?.ia" class="rounded-md bg-surface-amber-1 px-3 py-2 text-p-sm text-ink-amber-3">
            {{
              ficha.data?.pode_configurar
                ? __('A IA ainda não está ligada. Cadastre a chave em Configurações → Automações para preencher sozinho.')
                : __('A IA ainda não está ligada. Peça a um gestor para cadastrar a chave em Configurações → Automações.')
            }}
          </div>
          <FormControl v-model="transcript" type="textarea" :rows="12" :placeholder="__('Cole a transcrição da reunião aqui')" />
          <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
            <input v-model="overwrite" type="checkbox" />
            {{ __('Substituir o que já está preenchido na ficha') }}
          </label>
          <p class="text-xs text-ink-gray-5">
            {{ __('O texto é enviado à Anthropic (Claude) apenas para montar a ficha. Avise o cliente que a reunião foi gravada e transcrita.') }}
          </p>
          <ErrorMessage v-if="error" :message="error" />
        </div>
      </template>
      <template #actions>
        <Button variant="solid" :label="__('Preencher a ficha')" :loading="filling" :disabled="!ficha.data?.ia" @click="fill" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({ doctype: String, docname: String })

const ficha = createResource({
  url: 'crm.api.ficha.get_ficha',
  makeParams: () => ({ doctype: props.doctype, name: props.docname }),
  auto: true,
  onSuccess(data) {
    Object.assign(form, data.campos)
  },
})
watch(() => props.docname, () => ficha.reload())

const form = reactive({})
const total = computed(() => ficha.data?.rotulos?.length || 7)
const done = computed(() => (ficha.data?.rotulos || []).filter((f) => form[f.chave]?.trim()).length)

const saving = ref(false)
const saved = ref(false)
async function save() {
  saving.value = true
  saved.value = false
  try {
    await call('crm.api.ficha.save_ficha', { doctype: props.doctype, name: props.docname, campos: { ...form } })
    saved.value = true
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível salvar a ficha.'))
  } finally {
    saving.value = false
  }
}

// transcrição
const showTranscript = ref(false)
const transcript = ref('')
const overwrite = ref(false)
const filling = ref(false)
const error = ref('')
function openTranscript() {
  error.value = ''
  showTranscript.value = true
}
async function fill() {
  filling.value = true
  error.value = ''
  try {
    const r = await call('crm.api.ficha.fill_from_transcript', {
      doctype: props.doctype,
      name: props.docname,
      transcricao: transcript.value,
      sobrescrever: overwrite.value ? 1 : 0,
    })
    Object.assign(form, r.campos)
    showTranscript.value = false
    transcript.value = ''
    const labels = Object.fromEntries((ficha.data.rotulos || []).map((f) => [f.chave, f.rotulo]))
    toast.success(
      r.faltando.length
        ? __('Ficha preenchida. Falta alinhar: {0}', [r.faltando.map((k) => labels[k]).join(', ')])
        : __('Ficha preenchida por completo.'),
    )
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível preencher a ficha.')
  } finally {
    filling.value = false
  }
}

// proposta
const applying = ref(false)
async function toProposal() {
  applying.value = true
  try {
    await save()
    const r = await call('crm.api.ficha.apply_to_proposal', { deal: props.docname })
    toast.success(
      r.alterados
        ? __('Proposta preenchida com a ficha. Confira na aba Orçamento.')
        : __('A proposta já estava preenchida. Nada foi alterado.'),
    )
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível levar a ficha para a proposta.'))
  } finally {
    applying.value = false
  }
}
</script>
