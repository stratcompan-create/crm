<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Prescrição') }}</div>
    </template>
    <template #right-header>
      <Button :label="__('Como funciona o prazo')" variant="ghost" @click="showAjuda = true">
        <template #prefix><span class="lucide-circle-help size-4" aria-hidden="true" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <!-- o aviso que precisa estar na cara de quem usa -->
    <div class="mb-5 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/40">
      <div class="text-p-sm-medium text-amber-900 dark:text-amber-200">
        {{ __('Uso interno do escritório') }}
      </div>
      <p class="mt-1 text-p-xs text-amber-800 dark:text-amber-300">{{ aviso }}</p>
    </div>

    <!-- resumo -->
    <div class="mb-5 grid grid-cols-2 gap-3 md:grid-cols-5">
      <button
        v-for="n in niveis"
        :key="n.chave"
        type="button"
        class="rounded-lg border p-3 text-left transition"
        :class="n.chave === 'vencido' && resumo.vencido
          ? 'border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/40'
          : 'border-outline-gray-2 hover:bg-surface-gray-1'"
        @click="filtroNivel = filtroNivel === n.chave ? '' : n.chave"
      >
        <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ __(n.rotulo) }}</div>
        <div class="mt-1 text-2xl font-semibold tabular-nums" :class="n.cor">
          {{ resumo[n.chave] || 0 }}
        </div>
        <div v-if="filtroNivel === n.chave" class="mt-0.5 text-p-xs text-ink-gray-5">
          {{ __('filtrando') }}
        </div>
      </button>
      <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
        <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">
          {{ __('Já saiu do alcance') }}
        </div>
        <div class="mt-1 text-2xl font-semibold tabular-nums text-ink-gray-9">
          {{ reais(custoTotal) }}
        </div>
        <div class="mt-0.5 text-p-xs text-ink-gray-5">{{ __('somando a fila (estimativa)') }}</div>
      </div>
    </div>

    <!-- controles -->
    <div class="mb-4 flex flex-wrap items-end gap-3">
      <FormControl
        v-model="busca"
        type="text"
        class="w-64"
        :placeholder="__('Buscar por nome ou telefone')"
        @keyup.enter="carregar"
      />
      <Button :label="__('Buscar')" @click="carregar" />
      <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
        <input v-model="incluirVencidos" type="checkbox" @change="carregar" />
        {{ __('Mostrar prazos vencidos') }}
      </label>
      <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
        <input v-model="incluirSemData" type="checkbox" @change="carregar" />
        {{ __('Mostrar quem está sem data de saída') }}
      </label>
      <span class="text-p-xs text-ink-gray-5">
        {{ __('Prazo de {0} anos · pedido alcança {1} anos para trás').replace('{0}', config.anos || 2).replace('{1}', config.retroativo_anos || 5) }}
      </span>
    </div>

    <div v-if="carregando" class="p-6 text-center text-p-sm text-ink-gray-5">
      {{ __('Carregando a fila...') }}
    </div>
    <div
      v-else-if="!visiveis.length"
      class="rounded-lg border border-outline-gray-2 p-8 text-center"
    >
      <div class="text-p-base text-ink-gray-7">{{ __('Nenhum atendimento nessa faixa.') }}</div>
      <p class="mt-1 text-p-sm text-ink-gray-5">
        {{ __('A data da saída é preenchida no atendimento. Sem ela o radar não tem como contar o prazo.') }}
      </p>
    </div>

    <!-- a fila -->
    <div v-else class="space-y-3">
      <div
        v-for="item in visiveis"
        :key="item.lead"
        class="rounded-lg border p-4"
        :class="corBorda(item.nivel)"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="rounded-full px-2 py-0.5 text-p-xs" :class="corChip(item.nivel)">
                {{ __(item.rotulo) }}
              </span>
              <a
                class="truncate text-p-base-semibold text-ink-gray-9 hover:underline"
                :href="`/crm/leads/${item.lead}`"
              >{{ item.nome }}</a>
            </div>
            <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-p-xs text-ink-gray-5">
              <span v-if="item.telefone">{{ item.telefone }}</span>
              <span v-if="item.servico">{{ item.servico }}</span>
              <span v-if="item.data_saida">{{ __('saiu em') }} {{ dataBr(item.data_saida) }}</span>
              <span v-if="item.limite">{{ __('prazo até') }} {{ dataBr(item.limite) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="text-2xl font-semibold tabular-nums" :class="corTexto(item.nivel)">
                {{ item.dias_restantes === null ? '—' : Math.abs(item.dias_restantes) }}
              </div>
              <div class="text-p-xs text-ink-gray-5">
                {{ item.dias_restantes === null
                  ? __('sem data')
                  : item.dias_restantes < 0
                    ? __('dias atrás do prazo')
                    : __('dias restantes') }}
              </div>
            </div>
            <Button :label="__('Datas')" variant="subtle" @click="abrirEdicao(item)" />
          </div>
        </div>

        <div class="mt-3 grid gap-3 md:grid-cols-3">
          <div class="rounded-lg bg-surface-gray-1 p-3">
            <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Cabe no pedido hoje') }}
            </div>
            <div class="mt-0.5 text-p-base-semibold tabular-nums text-ink-gray-9">
              {{ item.meses_no_pedido === null ? '—' : item.meses_no_pedido + ' ' + __('meses') }}
            </div>
          </div>
          <div class="rounded-lg bg-surface-gray-1 p-3">
            <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Já saiu do alcance') }}
            </div>
            <div class="mt-0.5 text-p-base-semibold tabular-nums text-ink-gray-9">
              {{ item.meses_perdidos === null ? '—' : item.meses_perdidos + ' ' + __('meses') }}
              <span v-if="item.custo_espera" class="text-ink-gray-6">
                · {{ reais(item.custo_espera) }}
              </span>
            </div>
          </div>
          <div class="rounded-lg bg-surface-gray-1 p-3">
            <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">
              {{ __('Custo de cada mês parado') }}
            </div>
            <div class="mt-0.5 text-p-base-semibold tabular-nums text-ink-gray-9">
              {{ item.perde_por_mes ? reais(item.perde_por_mes) : __('não perde mais') }}
            </div>
          </div>
        </div>

        <p class="mt-3 text-p-sm leading-relaxed text-ink-gray-7">{{ item.explicacao }}</p>
        <p v-if="item.avisado_em" class="mt-1 text-p-xs text-ink-gray-5">
          {{ __('Tarefa de aviso criada em') }} {{ dataBr(item.avisado_em) }}
        </p>
      </div>
    </div>
  </div>

  <!-- editar datas -->
  <Dialog
    v-model="showEdicao"
    :options="{ title: __('Datas do vínculo'), size: 'lg', actions: [
      { label: __('Salvar'), variant: 'solid', onClick: salvar },
    ] }"
  >
    <template #body-content>
      <p class="mb-4 text-p-sm text-ink-gray-6">
        {{ __('A data da saída define o prazo. A admissão serve para saber quanto do contrato ainda cabe no pedido.') }}
      </p>
      <div class="space-y-3">
        <FormControl
          v-model="edicao.data_admissao"
          type="date"
          :label="__('Data da admissão')"
        />
        <FormControl v-model="edicao.data_saida" type="date" :label="__('Data da saída')" />
        <FormControl
          v-model="edicao.valor_mes_estimado"
          type="number"
          :label="__('Valor estimado por mês (R$)')"
          :description="__('Referência interna para priorizar a fila. Não aparece para o cliente.')"
        />
      </div>
      <div v-if="previa" class="mt-4 rounded-lg bg-surface-gray-1 p-3 text-p-sm text-ink-gray-7">
        {{ previa }}
      </div>
    </template>
  </Dialog>

  <!-- como funciona -->
  <Dialog
    v-model="showAjuda"
    :options="{ title: __('Como funciona o prazo'), size: '2xl' }"
  >
    <template #body-content>
      <div class="space-y-4">
        <div v-for="b in ajuda" :key="b.titulo">
          <div class="text-p-base-semibold text-ink-gray-9">{{ b.titulo }}</div>
          <p class="mt-1 text-p-sm leading-relaxed text-ink-gray-7">{{ b.texto }}</p>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const fila = ref([])
const resumo = reactive({})
const config = reactive({})
const custoTotal = ref(0)
const aviso = ref('')
const ajuda = ref([])
const carregando = ref(true)

const busca = ref('')
const incluirVencidos = ref(true)
const incluirSemData = ref(false)
const filtroNivel = ref('')

const showEdicao = ref(false)
const showAjuda = ref(false)
const edicao = reactive({ lead: '', nome: '', data_saida: '', data_admissao: '', valor_mes_estimado: 0 })
const previa = ref('')

const niveis = [
  { chave: 'vencido', rotulo: 'Vencidos', cor: 'text-red-600 dark:text-red-400' },
  { chave: 'critico', rotulo: 'Críticos', cor: 'text-orange-600 dark:text-orange-400' },
  { chave: 'atencao', rotulo: 'Atenção', cor: 'text-amber-600 dark:text-amber-400' },
  { chave: 'no_prazo', rotulo: 'No prazo', cor: 'text-ink-gray-9' },
  { chave: 'sem_data', rotulo: 'Sem data', cor: 'text-ink-gray-5' },
]

const visiveis = computed(() =>
  filtroNivel.value ? fila.value.filter((x) => x.nivel === filtroNivel.value) : fila.value,
)

function reais(v) {
  return (Number(v) || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

function dataBr(iso) {
  if (!iso) return ''
  const p = String(iso).slice(0, 10).split('-')
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : iso
}

function corChip(nivel) {
  return {
    vencido: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
    critico: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
    atencao: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    no_prazo: 'bg-surface-gray-2 text-ink-gray-7',
    sem_data: 'bg-surface-gray-2 text-ink-gray-5',
  }[nivel]
}

function corBorda(nivel) {
  return {
    vencido: 'border-red-300 dark:border-red-900',
    critico: 'border-orange-300 dark:border-orange-900',
    atencao: 'border-outline-gray-2',
    no_prazo: 'border-outline-gray-2',
    sem_data: 'border-outline-gray-2',
  }[nivel]
}

function corTexto(nivel) {
  return {
    vencido: 'text-red-600 dark:text-red-400',
    critico: 'text-orange-600 dark:text-orange-400',
    atencao: 'text-amber-600 dark:text-amber-400',
    no_prazo: 'text-ink-gray-9',
    sem_data: 'text-ink-gray-5',
  }[nivel]
}

async function carregar() {
  carregando.value = true
  try {
    const r = await call('crm.api.prescricao.listar', {
      busca: busca.value,
      incluir_vencidos: incluirVencidos.value ? 1 : 0,
      incluir_sem_data: incluirSemData.value ? 1 : 0,
    })
    fila.value = r.fila || []
    Object.assign(resumo, r.resumo || {})
    Object.assign(config, r.config || {})
    custoTotal.value = r.custo_total || 0
    aviso.value = r.aviso_interno || ''
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível carregar a fila'))
  } finally {
    carregando.value = false
  }
}

function abrirEdicao(item) {
  Object.assign(edicao, {
    lead: item.lead,
    nome: item.nome,
    data_saida: item.data_saida || '',
    data_admissao: item.data_admissao || '',
    valor_mes_estimado: item.valor_mes_estimado || 0,
  })
  previa.value = item.explicacao || ''
  showEdicao.value = true
}

async function salvar(close) {
  try {
    const r = await call('crm.api.prescricao.salvar', {
      lead: edicao.lead,
      data_saida: edicao.data_saida || '',
      data_admissao: edicao.data_admissao || '',
      valor_mes_estimado: edicao.valor_mes_estimado || 0,
    })
    previa.value = r.explicacao || ''
    toast.success(__('Datas salvas'))
    await carregar()
    close?.()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível salvar'))
  }
}

onMounted(async () => {
  await carregar()
  try {
    const r = await call('crm.api.prescricao.como_funciona')
    ajuda.value = r.blocos || []
  } catch (e) {
    ajuda.value = []
  }
})
</script>
