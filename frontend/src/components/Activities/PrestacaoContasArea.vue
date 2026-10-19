<template>
  <div class="flex flex-col gap-5 py-4 text-ink-gray-8">
    <div v-if="dados.loading && !dados.data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <template v-else-if="dados.data">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div class="flex flex-col gap-1">
          <div class="text-p-base-medium text-ink-gray-9">{{ __('Prestação de contas ao cliente') }}</div>
          <div class="max-w-xl text-xs text-ink-gray-5">
            {{ __('Registre aqui o que o escritório recebe em nome do cliente (alvará, acordo, RPV, precatório). O CRM calcula os honorários, desconta as custas adiantadas e mostra quanto repassar.') }}
          </div>
        </div>
        <div class="flex items-end gap-2">
          <div class="flex w-36 flex-col gap-1">
            <span class="text-xs text-ink-gray-6">{{ __('Êxito combinado (%)') }}</span>
            <FormControl v-model="percentual" type="number" />
          </div>
          <Button variant="subtle" :label="__('Salvar %')" :loading="salvandoPct" @click="salvarPercentual" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div v-for="c in cards" :key="c.label" class="rounded-lg border border-outline-gray-2 p-3">
          <div class="text-xs text-ink-gray-5">{{ c.label }}</div>
          <div class="mt-1 text-lg font-semibold" :class="c.cor">{{ brl(c.valor) }}</div>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <Button variant="solid" iconLeft="lucide-plus" :label="__('Registrar recebimento')" @click="abrirNovo" />
        <Button variant="subtle" iconLeft="lucide-receipt" :label="__('Nova custa do caso')" @click="custa.show = true" />
        <Button
          v-if="dados.data.recebimentos.length"
          variant="subtle"
          iconLeft="lucide-file-text"
          :label="__('Demonstrativo em PDF')"
          :loading="gerandoPdf"
          @click="pdf()"
        />
      </div>

      <!-- recebimentos -->
      <div class="flex flex-col gap-2">
        <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Recebimentos') }}</div>
        <div v-if="!dados.data.recebimentos.length" class="rounded-lg border border-dashed border-outline-gray-3 p-5 text-center text-p-sm text-ink-gray-5">
          {{ __('Nenhum valor recebido neste caso ainda.') }}
        </div>
        <div v-for="r in dados.data.recebimentos" :key="r.name" class="rounded-lg border border-outline-gray-2 p-3">
          <div class="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div class="text-p-base-medium text-ink-gray-9">{{ __(r.origem) }} · {{ dataBr(r.data) }}</div>
              <div class="mt-1 grid grid-cols-2 gap-x-6 gap-y-0.5 text-p-sm text-ink-gray-6 sm:grid-cols-4">
                <span>{{ __('Recebido') }}: <b class="text-ink-gray-8">{{ brl(r.valor_bruto) }}</b></span>
                <span>{{ __('Honorários') }} ({{ r.percentual_honorarios }}%): <b class="text-ink-gray-8">{{ brl(r.valor_honorarios) }}</b></span>
                <span>{{ __('Custas descontadas') }}: <b class="text-ink-gray-8">{{ brl(r.despesas_reembolsadas) }}</b></span>
                <span>{{ __('Do cliente') }}: <b class="text-ink-gray-9">{{ brl(r.valor_repasse) }}</b></span>
              </div>
              <div v-if="r.parceiros.length" class="mt-1 text-xs text-ink-gray-5">
                {{ __('Divisão:') }}
                <span v-for="p in r.parceiros" :key="p.parceiro" class="mr-2">{{ p.parceiro }} {{ brl(p.valor) }}{{ p.pago ? ' ✓' : '' }}</span>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-1">
              <span
                class="rounded px-2 py-0.5 text-xs"
                :class="r.repasse_status === 'Repassado' ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-amber-2 text-ink-amber-3'"
              >
                {{ r.repasse_status === 'Repassado' ? __('Repassado em {0}', [dataBr(r.repasse_data)]) : __('A repassar') }}
              </span>
              <Button v-if="r.repasse_status !== 'Repassado'" size="sm" variant="subtle" :label="__('Marcar repassado')" @click="repassar(r)" />
              <Button size="sm" variant="ghost" icon="file-text" :title="__('Demonstrativo deste recebimento')" @click="pdf(r.name)" />
              <Button size="sm" variant="ghost" icon="edit-2" @click="abrirEdicao(r)" />
              <Button size="sm" variant="ghost" theme="red" icon="trash-2" @click="excluir(r)" />
            </div>
          </div>
        </div>
      </div>

      <!-- custas -->
      <div class="flex flex-col gap-2">
        <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Custas e despesas do caso') }}</div>
        <div v-if="!dados.data.despesas.length" class="text-p-sm text-ink-gray-5">{{ __('Nenhuma custa lançada neste caso.') }}</div>
        <div
          v-for="d in dados.data.despesas"
          :key="d.name"
          class="flex flex-wrap items-center justify-between gap-2 rounded border border-outline-gray-1 px-3 py-2 text-p-sm"
        >
          <span>{{ dataBr(d.data_vencimento) }} · {{ d.descricao }} · <b>{{ brl(d.valor) }}</b></span>
          <span v-if="d.recebimento" class="text-xs text-ink-green-3">{{ __('Descontada do cliente') }}</span>
          <label v-else class="flex items-center gap-1.5 text-xs text-ink-gray-6">
            <input type="checkbox" :checked="!!d.reembolsavel" @change="(e) => alternarReembolso(d, e.target.checked)" />
            {{ __('Cobrar do cliente') }}
          </label>
        </div>
      </div>
    </template>

    <!-- recebimento -->
    <Dialog v-model="form.show" :options="{ title: form.name ? __('Editar recebimento') : __('Registrar recebimento'), size: 'xl' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <FormControl v-model="form.data" type="date" :label="__('Data')" />
            <FormControl v-model="form.origem" type="select" :label="__('Origem')" :options="origens" />
            <FormControl v-model="form.valor_bruto" type="number" :label="__('Valor recebido (R$)')" />
          </div>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <FormControl v-model="form.percentual_honorarios" type="number" :label="__('Honorários (%)')" />
            <FormControl v-model="form.repasse_status" type="select" :label="__('Repasse')" :options="['A repassar', 'Repassado'].map((v) => ({ label: __(v), value: v }))" />
            <FormControl v-model="form.repasse_forma" type="select" :label="__('Forma do repasse')" :options="formas" />
          </div>
          <div class="rounded-lg bg-surface-gray-2 p-3 text-p-sm">
            <div>{{ __('Honorários') }}: <b>{{ brl(previa.honorarios) }}</b></div>
            <div>{{ __('Custas adiantadas a descontar') }}: <b>{{ brl(previa.custas) }}</b></div>
            <div class="text-p-base">{{ __('Valor do cliente (a repassar)') }}: <b>{{ brl(previa.repasse) }}</b></div>
          </div>
          <div class="flex flex-col gap-2">
            <div class="text-p-sm text-ink-gray-6">{{ __('Divisão dos honorários com parceiros ou correspondentes (opcional)') }}</div>
            <div v-for="(p, i) in form.parceiros" :key="i" class="grid grid-cols-12 items-end gap-2">
              <FormControl v-model="p.parceiro" class="col-span-5" type="text" :placeholder="__('Nome')" />
              <FormControl v-model="p.oab" class="col-span-3" type="text" :placeholder="__('OAB')" />
              <FormControl v-model="p.percentual" class="col-span-3" type="number" :placeholder="__('% dos honorários')" />
              <Button class="col-span-1" variant="ghost" icon="x" @click="form.parceiros.splice(i, 1)" />
            </div>
            <div>
              <Button size="sm" variant="subtle" iconLeft="lucide-plus" :label="__('Adicionar parceiro')" @click="form.parceiros.push({ parceiro: '', oab: '', percentual: '' })" />
            </div>
          </div>
          <FormControl v-model="form.observacoes" type="textarea" :rows="2" :label="__('Observações')" />
          <ErrorMessage v-if="erro" :message="erro" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end">
          <Button variant="solid" :label="__('Salvar')" :loading="salvando" @click="salvar" />
        </div>
      </template>
    </Dialog>

    <!-- custa -->
    <Dialog v-model="custa.show" :options="{ title: __('Nova custa do caso'), size: 'md' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <FormControl v-model="custa.descricao" type="text" :label="__('Descrição')" :placeholder="__('Ex.: custas iniciais, perícia, certidões')" />
          <div class="grid grid-cols-2 gap-3">
            <FormControl v-model="custa.valor" type="number" :label="__('Valor (R$)')" />
            <FormControl v-model="custa.data" type="date" :label="__('Pago em')" />
          </div>
          <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
            <input v-model="custa.reembolsavel" type="checkbox" />
            {{ __('O escritório adiantou: cobrar do cliente na prestação de contas') }}
          </label>
          <ErrorMessage v-if="erroCusta" :message="erroCusta" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end">
          <Button variant="solid" :label="__('Lançar custa')" :loading="salvandoCusta" @click="salvarCusta" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({ doctype: String, docname: String })

const dados = createResource({
  url: 'crm.api.prestacao_contas.resumo',
  makeParams: () => ({ deal: props.docname }),
  auto: true,
  onSuccess: (d) => (percentual.value = d.percentual_exito),
})
watch(() => props.docname, () => dados.reload())

const hoje = () => new Date().toISOString().slice(0, 10)
const brl = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const dataBr = (d) => (d ? String(d).slice(0, 10).split('-').reverse().join('/') : '')

const origens = ['Alvará judicial', 'Acordo', 'RPV', 'Precatório', 'Pagamento da parte contrária', 'Outro'].map((v) => ({ label: __(v), value: v }))
const formas = ['', 'PIX', 'Transferência', 'Boleto', 'Dinheiro', 'Cheque'].map((v) => ({ label: v ? __(v) : '—', value: v }))

const cards = computed(() => {
  const t = dados.data?.totais || {}
  return [
    { label: __('Recebido em nome do cliente'), valor: t.recebido, cor: 'text-ink-gray-9' },
    { label: __('Honorários do escritório'), valor: t.honorarios, cor: 'text-ink-green-3' },
    { label: __('A repassar ao cliente'), valor: t.a_repassar, cor: 'text-ink-amber-3' },
    { label: __('Custas a descontar'), valor: t.custas_a_descontar, cor: 'text-ink-gray-7' },
  ]
})

// percentual do caso
const percentual = ref(0)
const salvandoPct = ref(false)
async function salvarPercentual() {
  salvandoPct.value = true
  try {
    await call('crm.api.prestacao_contas.salvar_percentual', { deal: props.docname, percentual: percentual.value })
    toast.success(__('Percentual salvo'))
    dados.reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível salvar.'))
  } finally {
    salvandoPct.value = false
  }
}

// recebimento
const vazio = () => ({
  show: true, name: '', data: hoje(), origem: 'Alvará judicial', valor_bruto: '',
  percentual_honorarios: dados.data?.percentual_exito || '', repasse_status: 'A repassar', repasse_forma: '',
  observacoes: '', parceiros: [], custasDoRecebimento: 0,
})
const form = reactive({ show: false, parceiros: [] })
const erro = ref('')
const salvando = ref(false)
function abrirNovo() {
  erro.value = ''
  Object.assign(form, vazio(), { custasDoRecebimento: dados.data?.totais?.custas_a_descontar || 0 })
}
function abrirEdicao(r) {
  erro.value = ''
  Object.assign(form, vazio(), {
    name: r.name, data: r.data, origem: r.origem, valor_bruto: r.valor_bruto,
    percentual_honorarios: r.percentual_honorarios, repasse_status: r.repasse_status, repasse_forma: r.repasse_forma,
    observacoes: r.observacoes, parceiros: r.parceiros.map((p) => ({ ...p })),
    custasDoRecebimento: r.despesas_reembolsadas + (dados.data?.totais?.custas_a_descontar || 0),
  })
}
const previa = computed(() => {
  const bruto = Number(form.valor_bruto) || 0
  const honorarios = Math.round(bruto * (Number(form.percentual_honorarios) || 0)) / 100
  const custas = Number(form.custasDoRecebimento) || 0
  return { honorarios, custas, repasse: bruto - honorarios - custas }
})
async function salvar() {
  salvando.value = true
  erro.value = ''
  try {
    const { show, custasDoRecebimento, ...resto } = form
    await call('crm.api.prestacao_contas.salvar_recebimento', { dados: JSON.stringify({ ...resto, deal: props.docname }) })
    form.show = false
    toast.success(__('Recebimento salvo'))
    dados.reload()
  } catch (e) {
    erro.value = e?.messages?.[0] || __('Não foi possível salvar.')
  } finally {
    salvando.value = false
  }
}
async function repassar(r) {
  await call('crm.api.prestacao_contas.marcar_repasse', { recebimento: r.name })
  toast.success(__('Repasse registrado'))
  dados.reload()
}
async function excluir(r) {
  if (!window.confirm(__('Excluir este recebimento? O honorário gerado também sai do Financeiro.'))) return
  await call('crm.api.prestacao_contas.excluir_recebimento', { recebimento: r.name })
  dados.reload()
}

// PDF
const gerandoPdf = ref(false)
async function pdf(recebimento) {
  gerandoPdf.value = true
  try {
    const r = await call('crm.api.prestacao_contas.demonstrativo_pdf', { deal: props.docname, recebimento: recebimento || null })
    const bytes = Uint8Array.from(atob(r.pdf), (c) => c.charCodeAt(0))
    window.open(URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' })), '_blank')
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível gerar o PDF.'))
  } finally {
    gerandoPdf.value = false
  }
}

// custas
const custa = reactive({ show: false, descricao: '', valor: '', data: hoje(), reembolsavel: true })
const erroCusta = ref('')
const salvandoCusta = ref(false)
async function salvarCusta() {
  salvandoCusta.value = true
  erroCusta.value = ''
  try {
    await call('crm.api.prestacao_contas.nova_custa', {
      deal: props.docname, descricao: custa.descricao, valor: custa.valor, data: custa.data, reembolsavel: custa.reembolsavel ? 1 : 0,
    })
    Object.assign(custa, { show: false, descricao: '', valor: '', data: hoje(), reembolsavel: true })
    dados.reload()
  } catch (e) {
    erroCusta.value = e?.messages?.[0] || __('Não foi possível lançar.')
  } finally {
    salvandoCusta.value = false
  }
}
async function alternarReembolso(d, marcado) {
  try {
    await call('crm.api.prestacao_contas.marcar_reembolsavel', { despesa: d.name, reembolsavel: marcado ? 1 : 0 })
    dados.reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível alterar.'))
    dados.reload()
  }
}
</script>
