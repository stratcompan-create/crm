<template>
  <LayoutHeader>
    <template #left-header>
      <div class="flex items-center gap-2">
        <div class="text-lg font-semibold text-ink-gray-9">{{ __('Audiências') }}</div>
        <span
          v-if="pendentes"
          class="rounded-full bg-amber-100 px-2 py-0.5 text-p-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300"
        >
          {{ pendentes }} {{ __('sem confirmar') }}
        </span>
      </div>
    </template>
    <template #right-header>
      <Button variant="solid" :label="__('Nova audiência')" @click="abrirNova">
        <template #prefix><span class="lucide-plus size-4" aria-hidden="true" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 overflow-hidden">
    <!-- lista -->
    <aside class="w-80 shrink-0 overflow-y-auto border-r border-outline-gray-2 p-3">
      <div v-if="carregando" class="p-3 text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <div v-else-if="!lista.length" class="p-3 text-p-sm text-ink-gray-5">
        {{ __('Nenhuma audiência marcada. Comece por "Nova audiência".') }}
      </div>
      <button
        v-for="a in lista"
        :key="a.name"
        type="button"
        class="mb-2 w-full rounded-lg border p-3 text-left transition"
        :class="[
          selecionada === a.name ? 'bg-surface-gray-1' : 'hover:bg-surface-gray-1',
          a.risco ? 'border-red-300 dark:border-red-900' : 'border-outline-gray-2',
        ]"
        @click="selecionar(a.name)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ __(a.tipo) }}</span>
          <span v-if="a.risco" class="text-p-xs font-semibold text-red-600 dark:text-red-400">
            {{ __('falta confirmar') }}
          </span>
        </div>
        <div class="mt-1 text-p-base-medium text-ink-gray-9">{{ a.quando }}</div>
        <div class="mt-0.5 truncate text-p-xs text-ink-gray-5">{{ a.caso }}</div>
        <div class="mt-1.5 flex items-center gap-2 text-p-xs tabular-nums">
          <span class="text-emerald-600 dark:text-emerald-400">
            {{ a.confirmados }} {{ __('ok') }}
          </span>
          <span v-if="a.aguardando" class="text-amber-600 dark:text-amber-400">
            {{ a.aguardando }} {{ __('aguardando') }}
          </span>
          <span v-if="a.recusaram" class="text-red-600 dark:text-red-400">
            {{ a.recusaram }} {{ __('não vão') }}
          </span>
        </div>
      </button>
    </aside>

    <!-- detalhe -->
    <section class="flex-1 overflow-y-auto p-5">
      <div v-if="!detalhe" class="p-8 text-center text-p-sm text-ink-gray-5">
        {{ __('Escolha uma audiência na lista.') }}
      </div>
      <template v-else>
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="text-xl font-semibold text-ink-gray-9">{{ detalhe.quando }}</div>
            <div class="mt-1 text-p-sm text-ink-gray-6">
              {{ __(detalhe.tipo) }} · {{ __(detalhe.modalidade) }}
              <span v-if="detalhe.vara"> · {{ detalhe.vara }}</span>
            </div>
            <div class="mt-0.5 text-p-sm text-ink-gray-5">{{ detalhe.caso }}</div>
          </div>
          <div class="flex gap-2">
            <Button :label="__('Remarcar')" variant="subtle" @click="abrirRemarcar" />
            <Button
              v-if="detalhe.status === 'Agendada' || detalhe.status === 'Adiada'"
              :label="__('Cancelar')"
              variant="subtle"
              theme="red"
              @click="cancelar"
            />
          </div>
        </div>

        <div v-if="detalhe.local" class="mt-3 text-p-sm text-ink-gray-7">
          <span class="text-ink-gray-5">{{ __('Local') }}:</span> {{ detalhe.local }}
        </div>
        <div v-if="detalhe.link_virtual" class="mt-1 text-p-sm text-ink-gray-7">
          <span class="text-ink-gray-5">{{ __('Sala virtual') }}:</span>
          <a class="ml-1 underline" :href="detalhe.link_virtual" target="_blank" rel="noopener">
            {{ detalhe.link_virtual }}
          </a>
        </div>

        <div class="mt-3 flex flex-wrap gap-2 text-p-xs">
          <span class="rounded-full px-2 py-0.5" :class="detalhe.lembrete_7d ? chipOk : chipOff">
            {{ detalhe.lembrete_7d ? __('aviso de 7 dias enviado') : __('aviso de 7 dias ainda não saiu') }}
          </span>
          <span class="rounded-full px-2 py-0.5" :class="detalhe.lembrete_1d ? chipOk : chipOff">
            {{ detalhe.lembrete_1d ? __('aviso da véspera enviado') : __('aviso da véspera ainda não saiu') }}
          </span>
        </div>

        <!-- quem vai -->
        <h2 class="mt-6 text-p-sm-semibold text-ink-gray-8">{{ __('Quem precisa comparecer') }}</h2>
        <div class="mt-2 space-y-2">
          <div
            v-for="p in detalhe.pessoas"
            :key="p.name"
            class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-outline-gray-2 p-3"
          >
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="rounded-full px-2 py-0.5 text-p-xs" :class="corConf(p.confirmacao)">
                  {{ __(p.confirmacao) }}
                </span>
                <span class="text-p-base-medium text-ink-gray-9">{{ p.nome }}</span>
                <span class="text-p-xs text-ink-gray-5">{{ __(p.tipo) }}</span>
              </div>
              <div class="mt-1 flex flex-wrap gap-x-3 text-p-xs text-ink-gray-5">
                <span v-if="p.telefone">{{ p.telefone }}</span>
                <span v-if="p.email">{{ p.email }}</span>
                <span v-if="!p.email" class="text-amber-600 dark:text-amber-400">
                  {{ __('sem e-mail — o aviso vira tarefa de ligação') }}
                </span>
                <span v-if="p.respondido_em">
                  {{ __('respondeu em') }} {{ p.respondido_em.slice(0, 16).replace('T', ' ') }}
                </span>
                <span v-if="p.avisos_enviados">
                  {{ p.avisos_enviados }} {{ __('aviso(s) enviado(s)') }}
                </span>
              </div>
              <div v-if="p.observacao_resposta" class="mt-1 text-p-xs italic text-ink-gray-6">
                "{{ p.observacao_resposta }}"
              </div>
            </div>
            <div class="flex shrink-0 gap-2">
              <Button :label="__('Cobrar agora')" variant="subtle" @click="cobrar(p)" />
              <Button
                v-if="p.confirmacao === 'Aguardando'"
                :label="__('Confirmou por telefone')"
                variant="subtle"
                @click="confirmarManual(p)"
              />
              <Button variant="ghost" @click="removerPessoa(p)">
                <template #icon><span class="lucide-trash-2 size-4" aria-hidden="true" /></template>
              </Button>
            </div>
          </div>
          <Button :label="__('Acrescentar pessoa')" variant="subtle" @click="abrirPessoa" />
        </div>

        <!-- o que o cliente recebe -->
        <h2 class="mt-6 text-p-sm-semibold text-ink-gray-8">
          {{ __('O que o cliente recebe no aviso') }}
        </h2>
        <p class="mt-1 text-p-xs text-ink-gray-5">
          {{ __('Texto fixo, em linguagem simples. Não gasta crédito de IA e não promete resultado.') }}
        </p>
        <ul class="mt-2 list-disc space-y-1 rounded-lg bg-surface-gray-1 p-4 pl-8 text-p-sm text-ink-gray-7">
          <li v-for="(o, i) in detalhe.orientacoes_padrao" :key="i">{{ o }}</li>
          <li v-if="detalhe.orientacoes" class="font-medium">{{ detalhe.orientacoes }}</li>
        </ul>
      </template>
    </section>
  </div>

  <!-- nova audiência -->
  <Dialog
    v-model="showNova"
    :options="{ title: __('Nova audiência'), size: '2xl', actions: [
      { label: __('Marcar audiência'), variant: 'solid', onClick: criar },
    ] }"
  >
    <template #body-content>
      <div class="space-y-3">
        <div>
          <FormControl
            v-model="buscaCaso"
            type="text"
            :label="__('Caso')"
            :placeholder="__('Digite o nome do cliente ou o número do processo')"
            @input="buscarCasos"
          />
          <div v-if="nova.deal" class="mt-1 text-p-xs text-ink-gray-6">
            {{ __('Selecionado') }}: <b>{{ nova.caso }}</b>
          </div>
          <div
            v-else-if="casos.length"
            class="mt-1 max-h-40 overflow-y-auto rounded-lg border border-outline-gray-2"
          >
            <button
              v-for="c in casos"
              :key="c.name"
              type="button"
              class="block w-full px-3 py-2 text-left text-p-sm hover:bg-surface-gray-1"
              @click="escolherCaso(c)"
            >
              {{ c.rotulo }}
              <span v-if="c.processo" class="text-ink-gray-5">· {{ c.processo }}</span>
            </button>
          </div>
        </div>
        <FormControl
          v-model="nova.data_hora"
          type="datetime-local"
          :label="__('Data e hora')"
        />
        <div class="grid grid-cols-2 gap-3">
          <FormControl v-model="nova.tipo" type="select" :label="__('Tipo')" :options="tipos" />
          <FormControl
            v-model="nova.modalidade"
            type="select"
            :label="__('Modalidade')"
            :options="modalidades"
          />
        </div>
        <FormControl
          v-if="nova.modalidade === 'Videoconferência'"
          v-model="nova.link_virtual"
          type="text"
          :label="__('Link da sala virtual')"
        />
        <template v-else>
          <FormControl v-model="nova.local" type="text" :label="__('Local (endereço do fórum)')" />
        </template>
        <FormControl v-model="nova.vara" type="text" :label="__('Vara')" />
        <FormControl
          v-model="nova.orientacoes_extras"
          type="textarea"
          :label="__('Orientação extra ao cliente (opcional)')"
        />
        <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
          <input v-model="nova.trazer_testemunhas" type="checkbox" />
          {{ __('Convocar as testemunhas já cadastradas no caso') }}
        </label>
        <p class="text-p-xs text-ink-gray-5">
          {{ __('O cliente entra sempre. Os avisos saem 7 dias antes e na véspera, com confirmação em um toque pelo link.') }}
        </p>
      </div>
    </template>
  </Dialog>

  <!-- remarcar -->
  <Dialog
    v-model="showRemarcar"
    :options="{ title: __('Remarcar audiência'), actions: [
      { label: __('Remarcar'), variant: 'solid', onClick: remarcar },
    ] }"
  >
    <template #body-content>
      <FormControl v-model="novaData" type="datetime-local" :label="__('Nova data e hora')" />
      <p class="mt-3 text-p-xs text-amber-700 dark:text-amber-400">
        {{ __('Remarcar zera as confirmações e faz os avisos saírem de novo com a data nova.') }}
      </p>
    </template>
  </Dialog>

  <!-- pessoa -->
  <Dialog
    v-model="showPessoa"
    :options="{ title: __('Acrescentar pessoa'), actions: [
      { label: __('Acrescentar'), variant: 'solid', onClick: adicionarPessoa },
    ] }"
  >
    <template #body-content>
      <div class="space-y-3">
        <FormControl v-model="pessoa.nome" type="text" :label="__('Nome')" />
        <FormControl
          v-model="pessoa.tipo"
          type="select"
          :label="__('Quem é')"
          :options="tiposPessoa"
        />
        <FormControl v-model="pessoa.telefone" type="text" :label="__('Telefone')" />
        <FormControl v-model="pessoa.email" type="text" :label="__('E-mail')" />
        <p class="text-p-xs text-ink-gray-5">
          {{ __('Sem e-mail o CRM não finge que avisou: abre uma tarefa para alguém ligar.') }}
        </p>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const lista = ref([])
const pendentes = ref(0)
const detalhe = ref(null)
const selecionada = ref('')
const carregando = ref(true)
const tipos = ref([])
const modalidades = ref([])
const tiposPessoa = ref([])

const showNova = ref(false)
const showRemarcar = ref(false)
const showPessoa = ref(false)
const novaData = ref('')
const buscaCaso = ref('')
const casos = ref([])

const chipOk = 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
const chipOff = 'bg-surface-gray-2 text-ink-gray-5'

const nova = reactive({
  deal: '',
  caso: '',
  data_hora: '',
  tipo: 'Una',
  modalidade: 'Presencial',
  local: '',
  vara: '',
  link_virtual: '',
  orientacoes_extras: '',
  trazer_testemunhas: true,
})
const pessoa = reactive({ nome: '', tipo: 'Testemunha', telefone: '', email: '' })

function corConf(c) {
  return {
    Confirmado: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    Aguardando: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    'Não poderá ir': 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  }[c]
}

async function carregar() {
  carregando.value = true
  try {
    const r = await call('crm.api.audiencia.listar')
    lista.value = r.audiencias || []
    pendentes.value = r.pendentes || 0
    tipos.value = r.tipos || []
    modalidades.value = r.modalidades || []
    tiposPessoa.value = r.tipos_pessoa || []
    if (selecionada.value && !lista.value.some((a) => a.name === selecionada.value)) {
      detalhe.value = null
      selecionada.value = ''
    }
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível carregar as audiências'))
  } finally {
    carregando.value = false
  }
}

async function selecionar(name) {
  selecionada.value = name
  try {
    detalhe.value = await call('crm.api.audiencia.obter', { audiencia: name })
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível abrir a audiência'))
  }
}

function abrirNova() {
  Object.assign(nova, {
    deal: '',
    caso: '',
    data_hora: '',
    tipo: 'Una',
    modalidade: 'Presencial',
    local: '',
    vara: '',
    link_virtual: '',
    orientacoes_extras: '',
    trazer_testemunhas: true,
  })
  buscaCaso.value = ''
  casos.value = []
  showNova.value = true
  buscarCasos()
}

let timer = null
function buscarCasos() {
  nova.deal = ''
  clearTimeout(timer)
  timer = setTimeout(async () => {
    try {
      casos.value = await call('crm.api.audiencia.buscar_casos', { termo: buscaCaso.value })
    } catch (e) {
      casos.value = []
    }
  }, 250)
}

function escolherCaso(c) {
  nova.deal = c.name
  nova.caso = c.rotulo
  buscaCaso.value = c.rotulo
  casos.value = []
}

async function criar(close) {
  if (!nova.deal) {
    toast.error(__('Escolha o caso.'))
    return
  }
  if (!nova.data_hora) {
    toast.error(__('Informe a data e a hora.'))
    return
  }
  try {
    const r = await call('crm.api.audiencia.criar', {
      deal: nova.deal,
      data_hora: nova.data_hora.replace('T', ' '),
      tipo: nova.tipo,
      modalidade: nova.modalidade,
      local: nova.local,
      vara: nova.vara,
      link_virtual: nova.link_virtual,
      orientacoes_extras: nova.orientacoes_extras,
      trazer_testemunhas: nova.trazer_testemunhas ? 1 : 0,
    })
    toast.success(__('Audiência marcada'))
    close?.()
    await carregar()
    await selecionar(r.name)
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível marcar'))
  }
}

function abrirRemarcar() {
  novaData.value = (detalhe.value?.data_hora || '').slice(0, 16).replace(' ', 'T')
  showRemarcar.value = true
}

async function remarcar(close) {
  try {
    await call('crm.api.audiencia.atualizar', {
      audiencia: selecionada.value,
      data_hora: novaData.value.replace('T', ' '),
    })
    toast.success(__('Remarcada. As confirmações foram zeradas.'))
    close?.()
    await carregar()
    await selecionar(selecionada.value)
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível remarcar'))
  }
}

async function cancelar() {
  try {
    await call('crm.api.audiencia.atualizar', {
      audiencia: selecionada.value,
      status: 'Cancelada',
    })
    toast.success(__('Audiência cancelada'))
    detalhe.value = null
    selecionada.value = ''
    await carregar()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível cancelar'))
  }
}

async function cobrar(p) {
  try {
    const r = await call('crm.api.audiencia.cobrar', { pessoa: p.name })
    toast.success(r.via === 'email' ? __('Aviso enviado por e-mail') : __('Tarefa de ligação criada'))
    await selecionar(selecionada.value)
    await carregar()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível cobrar'))
  }
}

async function confirmarManual(p) {
  try {
    await call('crm.api.audiencia.marcar_manual', {
      pessoa: p.name,
      confirmacao: 'Confirmado',
      observacao: '',
    })
    toast.success(__('Registrado'))
    await selecionar(selecionada.value)
    await carregar()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível registrar'))
  }
}

function abrirPessoa() {
  Object.assign(pessoa, { nome: '', tipo: 'Testemunha', telefone: '', email: '' })
  showPessoa.value = true
}

async function adicionarPessoa(close) {
  if (!pessoa.nome) {
    toast.error(__('Informe o nome.'))
    return
  }
  try {
    await call('crm.api.audiencia.adicionar_pessoa', {
      audiencia: selecionada.value,
      nome: pessoa.nome,
      tipo: pessoa.tipo,
      telefone: pessoa.telefone,
      email: pessoa.email,
    })
    close?.()
    await selecionar(selecionada.value)
    await carregar()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível acrescentar'))
  }
}

async function removerPessoa(p) {
  try {
    await call('crm.api.audiencia.remover_pessoa', { pessoa: p.name })
    await selecionar(selecionada.value)
    await carregar()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível remover'))
  }
}

onMounted(carregar)
</script>
