<template>
  <div
    v-if="saldo.data?.ativo"
    class="mx-5 mt-5 flex flex-col gap-2 rounded-lg border border-outline-gray-2 p-4"
  >
    <div class="flex items-center justify-between gap-3">
      <div class="flex flex-col">
        <span class="text-p-base-medium text-ink-gray-8">{{ __('Crédito de IA') }}</span>
        <span class="text-p-sm text-ink-gray-6">{{ textoSaldo }}</span>
      </div>
      <Button variant="subtle" :label="__('Renovar crédito')" @click="showDialog = true" />
    </div>
    <div class="h-2 w-full overflow-hidden rounded-full bg-surface-gray-2">
      <div
        class="h-2 rounded-full transition-all"
        :class="pct >= 90 ? 'bg-ink-red-4' : pct >= 60 ? 'bg-ink-amber-4' : 'bg-ink-green-4'"
        :style="{ width: pct + '%' }"
      />
    </div>
  </div>

  <Dialog v-model="showDialog" :options="{ title: __('Renovar crédito de IA'), size: 'sm' }">
    <template #body-content>
      <p class="mb-4 text-p-sm text-ink-gray-6">
        {{ __('Escolha o valor da recarga. O pagamento é feito direto no link, por Pix ou cartão.') }}
      </p>
      <div class="flex flex-col gap-3">
        <button
          v-for="(faixa, i) in saldo.data?.faixas || []"
          :key="i"
          type="button"
          class="flex flex-col gap-2 rounded-lg border border-outline-gray-2 px-4 py-3 text-left hover:border-outline-gray-4"
          :disabled="comprando"
          @click="comprar(i)"
        >
          <div class="flex items-center justify-between">
            <span class="text-p-base-medium text-ink-gray-8">{{ faixa.rotulo }}</span>
            <span class="text-p-sm text-ink-gray-6">{{ formatarReais(faixa.centavos) }}</span>
          </div>
          <div class="flex flex-col gap-0.5">
            <span v-for="cap in faixa.capacidades || []" :key="cap.label" class="text-p-sm text-ink-gray-5">
              {{ __('até {0} {1}', [cap.quantidade.toLocaleString('pt-BR'), cap.label]) }}
            </span>
          </div>
        </button>
      </div>
    </template>
  </Dialog>
</template>
<script setup>
import { Button, Dialog, call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const saldo = createResource({ url: 'crm.api.credito_ia.obter_saldo', auto: true })
const showDialog = ref(false)
const comprando = ref(false)

function formatarReais(centavos) {
  return (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// a barra enche conforme o saldo cai - sem um "teto" explicito, usa a maior
// faixa de recarga como referencia de 100%, pra barra sempre fazer sentido
// visualmente mesmo depois de varias recargas de valores diferentes.
const pct = computed(() => {
  const faixas = saldo.data?.faixas || []
  const teto = Math.max(1, ...faixas.map((f) => f.centavos))
  const restante = Math.max(0, saldo.data?.saldo_centavos ?? 0)
  return Math.max(0, Math.min(100, 100 - Math.round((restante / teto) * 100)))
})

const textoSaldo = computed(() => {
  const centavos = saldo.data?.saldo_centavos ?? 0
  if (centavos <= 0) return __('Saldo esgotado - a IA parou de responder')
  return __('Saldo disponível: {0}', [formatarReais(centavos)])
})

async function comprar(indice) {
  comprando.value = true
  try {
    const res = await call('crm.api.credito_ia.gerar_link_credito', { indice })
    window.location.href = res.link
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível gerar o link de pagamento'))
  } finally {
    comprando.value = false
  }
}
</script>
