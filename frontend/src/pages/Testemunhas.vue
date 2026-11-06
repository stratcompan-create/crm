<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Testemunhas') }}</div>
    </template>
    <template #right-header>
      <Button
        :label="aba === 'busca' ? __('Ver quem repete') : __('Voltar para a busca')"
        variant="ghost"
        @click="trocarAba"
      >
        <template #prefix><span class="lucide-triangle-alert size-4" aria-hidden="true" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex-1 overflow-y-auto p-5">
    <!-- ============================ busca ============================ -->
    <template v-if="aba === 'busca'">
      <div class="rounded-lg border border-outline-gray-2 p-4">
        <div class="text-p-sm-semibold text-ink-gray-8">
          {{ __('Quem trabalhou onde, e quando') }}
        </div>
        <div class="mt-3 flex flex-wrap items-end gap-3">
          <div class="w-64">
            <FormControl
              v-model="filtro.local"
              type="text"
              :label="__('Onde trabalhou')"
              :placeholder="__('Agência Centro')"
              list="locais-cadastrados"
            />
            <datalist id="locais-cadastrados">
              <option v-for="l in locais" :key="l" :value="l" />
            </datalist>
          </div>
          <FormControl v-model="filtro.de" type="date" :label="__('De')" />
          <FormControl v-model="filtro.ate" type="date" :label="__('Até')" />
          <FormControl
            v-model="filtro.termo"
            type="text"
            class="w-48"
            :label="__('Nome ou observação')"
          />
          <Button variant="solid" :label="__('Buscar')" @click="buscar" />
          <Button variant="ghost" :label="__('Limpar')" @click="limpar" />
        </div>
        <label class="mt-3 flex items-center gap-2 text-p-sm text-ink-gray-7">
          <input v-model="filtro.so_disponiveis" type="checkbox" @change="buscar" />
          {{ __('Só quem está disponível para depor') }}
        </label>
      </div>

      <div v-if="carregando" class="p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Buscando...') }}
      </div>
      <template v-else>
        <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
          <div class="text-p-sm text-ink-gray-6">
            {{ resultado.length }} {{ __('testemunha(s) encontrada(s)') }}
          </div>
          <div v-if="semPeriodo" class="text-p-xs text-amber-700 dark:text-amber-400">
            {{ semPeriodo }} {{ __('sem período cadastrado — entram na busca por precaução') }}
          </div>
        </div>

        <div
          v-if="!resultado.length"
          class="mt-3 rounded-lg border border-outline-gray-2 p-8 text-center"
        >
          <div class="text-p-base text-ink-gray-7">{{ __('Ninguém com esse recorte.') }}</div>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{ __('As testemunhas vêm do cadastro de partes de cada caso. Complete o local e o período na ficha para elas aparecerem aqui.') }}
          </p>
        </div>

        <div v-else class="mt-3 space-y-2">
          <div
            v-for="t in resultado"
            :key="t.parte"
            class="rounded-lg border p-4"
            :class="t.muito_usada
              ? 'border-amber-300 dark:border-amber-900'
              : 'border-outline-gray-2'"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-p-base-semibold text-ink-gray-9">{{ t.nome }}</span>
                  <span
                    v-if="t.muito_usada"
                    class="rounded-full bg-amber-100 px-2 py-0.5 text-p-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                  >
                    {{ __('em') }} {{ t.casos }} {{ __('casos') }}
                  </span>
                  <span
                    v-if="!t.disponivel"
                    class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-5"
                  >
                    {{ __('indisponível') }}
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-p-xs text-ink-gray-5">
                  <span v-if="t.local_trabalho">{{ t.local_trabalho }}</span>
                  <span v-if="t.periodo_inicio || t.periodo_fim">
                    {{ dataBr(t.periodo_inicio) || '?' }} — {{ dataBr(t.periodo_fim) || __('ainda lá') }}
                  </span>
                  <span v-else class="text-amber-600 dark:text-amber-400">
                    {{ __('sem período') }}
                  </span>
                  <span v-if="t.telefone">{{ t.telefone }}</span>
                </div>
                <div class="mt-1 text-p-xs text-ink-gray-5">
                  <a class="hover:underline" :href="`/crm/deals/${t.deal}`">{{ t.caso }}</a>
                </div>
                <div v-if="t.observacoes" class="mt-1 text-p-sm text-ink-gray-7">
                  {{ t.observacoes }}
                </div>
              </div>
              <Button :label="__('Editar ficha')" variant="subtle" @click="abrirEdicao(t)" />
            </div>
          </div>
        </div>

        <div
          v-if="resultado.some((t) => t.muito_usada)"
          class="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/40"
        >
          <p class="text-p-xs text-amber-800 dark:text-amber-300">{{ avisoRepetidas }}</p>
        </div>
      </template>
    </template>

    <!-- ============================ repetidas ============================ -->
    <template v-else>
      <div class="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/40">
        <div class="text-p-sm-semibold text-amber-900 dark:text-amber-200">
          {{ __('Testemunhas que aparecem em muitos casos') }}
        </div>
        <p class="mt-1 text-p-xs text-amber-800 dark:text-amber-300">{{ avisoRepetidas }}</p>
        <p class="mt-1 text-p-xs text-amber-800 dark:text-amber-300">
          {{ __('O limite é de {0} casos e fica em Configurações → Automações.').replace('{0}', limiteAlerta) }}
        </p>
      </div>

      <div v-if="carregando" class="p-6 text-center text-p-sm text-ink-gray-5">
        {{ __('Carregando...') }}
      </div>
      <div
        v-else-if="!repetidas.length"
        class="mt-4 rounded-lg border border-outline-gray-2 p-8 text-center"
      >
        <div class="text-p-base text-ink-gray-7">
          {{ __('Nenhuma testemunha repetida acima do limite.') }}
        </div>
      </div>
      <div v-else class="mt-4 space-y-2">
        <div
          v-for="(r, i) in repetidas"
          :key="i"
          class="rounded-lg border border-outline-gray-2 p-4"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-p-base-semibold text-ink-gray-9">{{ r.nome }}</span>
            <span
              class="rounded-full bg-amber-100 px-2 py-0.5 text-p-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300"
            >
              {{ r.quantidade }} {{ __('casos') }}
            </span>
            <span v-if="r.documento" class="text-p-xs text-ink-gray-5">{{ r.documento }}</span>
          </div>
          <div v-if="r.locais.length" class="mt-1 text-p-xs text-ink-gray-5">
            {{ r.locais.join(' · ') }}
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <a
              v-for="c in r.casos"
              :key="c.parte"
              class="rounded-full bg-surface-gray-2 px-2.5 py-1 text-p-xs text-ink-gray-7 hover:bg-surface-gray-3"
              :href="`/crm/deals/${c.deal}`"
            >{{ c.caso }}</a>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- editar ficha -->
  <Dialog
    v-model="showEdicao"
    :options="{ title: __('Ficha da testemunha'), size: 'lg', actions: [
      { label: __('Salvar'), variant: 'solid', onClick: salvar },
    ] }"
  >
    <template #body-content>
      <div class="mb-3 text-p-sm text-ink-gray-6">{{ edicao.nome }}</div>
      <div class="space-y-3">
        <FormControl
          v-model="edicao.local_trabalho"
          type="text"
          :label="__('Onde trabalhou (agência, unidade, setor)')"
        />
        <div class="grid grid-cols-2 gap-3">
          <FormControl v-model="edicao.periodo_inicio" type="date" :label="__('Trabalhou de')" />
          <FormControl v-model="edicao.periodo_fim" type="date" :label="__('Até')" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <FormControl v-model="edicao.telefone" type="text" :label="__('Telefone')" />
          <FormControl v-model="edicao.email" type="text" :label="__('E-mail')" />
        </div>
        <FormControl
          v-model="edicao.observacoes"
          type="textarea"
          :label="__('Observações')"
        />
        <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
          <input v-model="edicao.disponivel" type="checkbox" />
          {{ __('Disponível para depor') }}
        </label>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const aba = ref('busca')
const carregando = ref(false)
const resultado = ref([])
const repetidas = ref([])
const locais = ref([])
const limiteAlerta = ref(3)
const avisoRepetidas = ref('')

const filtro = reactive({ local: '', de: '', ate: '', termo: '', so_disponiveis: false })

const showEdicao = ref(false)
const edicao = reactive({
  parte: '',
  nome: '',
  local_trabalho: '',
  periodo_inicio: '',
  periodo_fim: '',
  telefone: '',
  email: '',
  observacoes: '',
  disponivel: true,
})

const semPeriodo = computed(() => resultado.value.filter((t) => t.sem_periodo).length)

function dataBr(iso) {
  if (!iso) return ''
  const p = String(iso).slice(0, 10).split('-')
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : iso
}

async function buscar() {
  carregando.value = true
  try {
    const r = await call('crm.api.testemunhas.buscar', {
      local: filtro.local,
      de: filtro.de,
      ate: filtro.ate,
      termo: filtro.termo,
      so_disponiveis: filtro.so_disponiveis ? 1 : 0,
    })
    resultado.value = r.testemunhas || []
    limiteAlerta.value = r.limite_alerta || 3
    avisoRepetidas.value = r.aviso_repetidas || ''
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível buscar'))
  } finally {
    carregando.value = false
  }
}

function limpar() {
  Object.assign(filtro, { local: '', de: '', ate: '', termo: '', so_disponiveis: false })
  buscar()
}

async function carregarRepetidas() {
  carregando.value = true
  try {
    const r = await call('crm.api.testemunhas.repetidas')
    repetidas.value = r.repetidas || []
    limiteAlerta.value = r.limite_alerta || 3
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível carregar'))
  } finally {
    carregando.value = false
  }
}

function trocarAba() {
  aba.value = aba.value === 'busca' ? 'repetidas' : 'busca'
  if (aba.value === 'repetidas') carregarRepetidas()
  else buscar()
}

function abrirEdicao(t) {
  Object.assign(edicao, {
    parte: t.parte,
    nome: t.nome,
    local_trabalho: t.local_trabalho || '',
    periodo_inicio: t.periodo_inicio || '',
    periodo_fim: t.periodo_fim || '',
    telefone: t.telefone || '',
    email: t.email || '',
    observacoes: t.observacoes || '',
    disponivel: !!t.disponivel,
  })
  showEdicao.value = true
}

async function salvar(close) {
  try {
    await call('crm.api.testemunhas.atualizar', {
      parte: edicao.parte,
      local_trabalho: edicao.local_trabalho,
      periodo_inicio: edicao.periodo_inicio,
      periodo_fim: edicao.periodo_fim,
      telefone: edicao.telefone,
      email: edicao.email,
      observacoes: edicao.observacoes,
      disponivel: edicao.disponivel ? 1 : 0,
    })
    toast.success(__('Ficha salva'))
    close?.()
    await buscar()
    await carregarLocais()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Não foi possível salvar'))
  }
}

async function carregarLocais() {
  try {
    locais.value = await call('crm.api.testemunhas.locais')
  } catch (e) {
    locais.value = []
  }
}

onMounted(async () => {
  await buscar()
  await carregarLocais()
})
</script>
