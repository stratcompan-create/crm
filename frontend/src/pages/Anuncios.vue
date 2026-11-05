<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Anúncios') }}</div>
    </template>
    <template #right-header>
      <Button :label="__('O que significa cada termo')" variant="ghost" @click="showGlossario = true">
        <template #prefix><span class="lucide-book-open size-4" aria-hidden="true" /></template>
      </Button>
      <Button variant="solid" :label="__('Nova campanha')" @click="abrirNova">
        <template #prefix><span class="lucide-plus size-4" aria-hidden="true" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 overflow-hidden">
    <!-- lista -->
    <aside class="w-72 shrink-0 overflow-y-auto border-r border-outline-gray-2 p-3">
      <div v-if="!campanhas.length" class="p-3 text-p-sm text-ink-gray-5">
        {{ __('Nenhuma campanha ainda. Comece por "Nova campanha".') }}
      </div>
      <button
        v-for="c in campanhas"
        :key="c.name"
        type="button"
        class="mb-2 w-full rounded-lg border p-3 text-left transition"
        :class="selecionada === c.name
          ? 'border-[var(--stratcompany-accent)] bg-surface-gray-1'
          : 'border-outline-gray-2 hover:bg-surface-gray-1'"
        @click="selecionar(c.name)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ c.plataforma }}</span>
          <span class="rounded-full px-2 py-0.5 text-p-xs" :class="corStatus(c.status)">{{ __(c.status) }}</span>
        </div>
        <div class="mt-1 line-clamp-2 text-p-base-medium text-ink-gray-9">{{ c.titulo }}</div>
        <div class="mt-0.5 text-p-xs tabular-nums text-ink-gray-5">
          {{ c.orcamento_diario_centavos ? reais(c.orcamento_diario_centavos) + __(' por dia') : __('sem orçamento definido') }}
        </div>
      </button>
    </aside>

    <!-- detalhe -->
    <section class="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
      <div v-if="!atual" class="m-auto max-w-md text-center">
        <div class="text-p-lg-medium text-ink-gray-8">{{ __('Monte uma campanha e entenda cada escolha') }}</div>
        <p class="mt-2 text-p-sm text-ink-gray-6">
          {{ __('Você escreve o que vende e para quem. A IA monta a estrutura, explica em linguagem simples por que escolheu cada coisa e traduz os termos técnicos. A campanha nasce pausada: nada gasta dinheiro sem você ligar.') }}
        </p>
        <Button class="mt-4" variant="solid" :label="__('Nova campanha')" @click="abrirNova" />
      </div>

      <template v-else>
        <!-- cabeçalho da campanha -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-p-lg-medium text-ink-gray-9">{{ atual.titulo }}</h2>
                <span class="rounded-full px-2 py-0.5 text-p-xs" :class="corStatus(atual.status)">{{ __(atual.status) }}</span>
              </div>
              <div class="mt-1 text-p-sm text-ink-gray-6">
                {{ atual.plataforma }} · {{ __(atual.objetivo) }} ·
                {{ atual.orcamento_diario_centavos ? reais(atual.orcamento_diario_centavos) + __(' por dia') : __('sem orçamento') }}
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <Button
                v-if="atual.status === 'Rascunho'"
                variant="solid"
                :label="__('Aprovar')"
                :loading="trabalhando"
                @click="aprovar"
              />
              <Button :label="__('Exportar')" :loading="trabalhando" @click="exportar">
                <template #prefix><span class="lucide-download size-4" aria-hidden="true" /></template>
              </Button>
              <Button v-if="atual.status === 'Aprovada'" :label="__('Publicar')" :loading="trabalhando" @click="publicar" />
              <Button variant="ghost" :label="__('Arquivar')" @click="arquivar" />
            </div>
          </div>
          <p v-if="atual.resumo_ia" class="mt-3 border-t border-outline-gray-1 pt-3 text-p-base text-ink-gray-7">
            {{ atual.resumo_ia }}
          </p>
        </div>

        <!-- revisão OAB -->
        <div
          v-if="atual.revisao_oab && (atual.revisao_oab.apontamentos || []).length"
          class="rounded-lg border border-outline-red-2 bg-surface-red-1 p-4"
        >
          <div class="flex items-center gap-2 text-p-base-medium text-ink-red-4">
            <span class="lucide-shield-alert size-4" aria-hidden="true" />
            {{ __('A revisão da OAB apontou problemas nesses textos') }}
          </div>
          <ul class="mt-2 space-y-1 text-p-sm text-ink-gray-7">
            <li v-for="(a, i) in atual.revisao_oab.apontamentos" :key="i">
              <span class="font-medium">“{{ a.texto }}”</span> — {{ __(a.motivo) }} ({{ a.termo }})
            </li>
          </ul>
          <p class="mt-2 text-p-xs text-ink-gray-6">
            {{ __('Enquanto isso não for corrigido, a campanha não pode ser aprovada. Publicidade de advogado não pode prometer resultado (Provimento 205/2021 da OAB).') }}
          </p>
        </div>

        <!-- avisos de limite -->
        <div v-if="(atual.avisos_limite || []).length" class="rounded-lg border border-outline-gray-2 bg-surface-amber-1 p-4">
          <div class="text-p-base-medium text-ink-gray-8">{{ __('Textos fora do limite do Google') }}</div>
          <ul class="mt-1 space-y-1 text-p-sm text-ink-gray-7">
            <li v-for="(a, i) in atual.avisos_limite" :key="i">{{ a }}</li>
          </ul>
        </div>

        <!-- mentoria -->
        <div v-if="(atual.mentoria || []).length" class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
          <div class="flex items-center gap-2">
            <h3 class="text-p-lg-medium text-ink-gray-9">{{ __('Por que a campanha ficou assim') }}</h3>
            <span class="text-p-xs text-ink-gray-5">✦ {{ __('explicado pela IA') }}</span>
          </div>
          <div class="mt-3 grid gap-3 md:grid-cols-2">
            <div v-for="(m, i) in atual.mentoria" :key="i" class="rounded-lg border border-outline-gray-1 p-3">
              <div class="text-p-base-medium text-ink-gray-9">{{ m.escolha }}</div>
              <p class="mt-1 text-p-sm text-ink-gray-7">{{ m.porque }}</p>
              <div v-if="(m.termos || []).length" class="mt-2 flex flex-wrap gap-1">
                <button
                  v-for="t in m.termos"
                  :key="t"
                  type="button"
                  class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-7 hover:bg-surface-gray-3"
                  @click="showGlossario = true"
                >
                  {{ t }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- primeiros passos e avisos -->
        <div class="grid gap-4 md:grid-cols-2">
          <div v-if="(atual.estrutura.primeiros_passos || []).length" class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
            <h3 class="text-p-base-medium text-ink-gray-9">{{ __('O que olhar na primeira semana') }}</h3>
            <ol class="mt-2 list-decimal space-y-1 pl-5 text-p-sm text-ink-gray-7">
              <li v-for="(p, i) in atual.estrutura.primeiros_passos" :key="i">{{ p }}</li>
            </ol>
          </div>
          <div v-if="(atual.estrutura.avisos || []).length" class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
            <h3 class="text-p-base-medium text-ink-gray-9">{{ __('Antes de ligar, saiba') }}</h3>
            <ul class="mt-2 list-disc space-y-1 pl-5 text-p-sm text-ink-gray-7">
              <li v-for="(a, i) in atual.estrutura.avisos" :key="i">{{ a }}</li>
            </ul>
          </div>
        </div>

        <!-- estrutura -->
        <div class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
          <h3 class="text-p-lg-medium text-ink-gray-9">
            {{ atual.plataforma === 'Google' ? __('Grupos de anúncio') : __('Conjuntos de anúncio') }}
          </h3>
          <div v-if="!(atual.estrutura.grupos || []).length" class="mt-2 text-p-sm text-ink-gray-5">
            {{ __('Essa campanha ainda está vazia.') }}
          </div>
          <div v-for="(g, gi) in atual.estrutura.grupos || []" :key="gi" class="mt-4 rounded-lg border border-outline-gray-1 p-4">
            <div class="text-p-base-medium text-ink-gray-9">{{ g.nome }}</div>
            <p v-if="g.intencao" class="mt-0.5 text-p-sm text-ink-gray-6">{{ __('Quem cai aqui:') }} {{ g.intencao }}</p>
            <p v-if="g.publico" class="mt-0.5 text-p-sm text-ink-gray-6">{{ __('Público:') }} {{ g.publico }}</p>

            <div v-if="(g.palavras_chave || []).length" class="mt-3">
              <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ __('Palavras-chave') }}</div>
              <div class="mt-1 flex flex-wrap gap-1">
                <span v-for="(p, pi) in g.palavras_chave" :key="pi" class="rounded border border-outline-gray-2 px-2 py-0.5 text-p-sm text-ink-gray-8">
                  {{ typeof p === 'string' ? p : p.texto }}
                  <span v-if="p.correspondencia" class="text-ink-gray-5">· {{ p.correspondencia }}</span>
                </span>
              </div>
            </div>

            <div v-if="(g.negativas || []).length" class="mt-3">
              <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ __('Negativas (impedem o anúncio de aparecer)') }}</div>
              <div class="mt-1 flex flex-wrap gap-1">
                <span v-for="(n, ni) in g.negativas" :key="ni" class="rounded bg-surface-gray-2 px-2 py-0.5 text-p-sm text-ink-gray-7">{{ n }}</span>
              </div>
            </div>

            <div v-for="(a, ai) in g.anuncios || []" :key="ai" class="mt-3 rounded-md bg-surface-gray-1 p-3">
              <div class="text-p-xs uppercase tracking-wide text-ink-gray-5">{{ __('Anúncio') }} {{ ai + 1 }}</div>
              <p v-if="a.texto_principal" class="mt-1 text-p-sm text-ink-gray-8">{{ a.texto_principal }}</p>
              <div v-for="(t, ti) in a.titulos || []" :key="'t' + ti" class="mt-1 text-p-base-medium text-ink-gray-9">
                {{ t }} <span class="text-p-xs tabular-nums text-ink-gray-5">({{ t.length }})</span>
              </div>
              <div v-for="(d, di) in a.descricoes || []" :key="'d' + di" class="mt-1 text-p-sm text-ink-gray-7">
                {{ d }} <span class="text-p-xs tabular-nums text-ink-gray-5">({{ d.length }})</span>
              </div>
              <div v-if="a.cta" class="mt-2 inline-block rounded bg-surface-gray-3 px-2 py-0.5 text-p-xs text-ink-gray-7">{{ a.cta }}</div>
            </div>
          </div>
        </div>
      </template>
    </section>
  </div>

  <!-- nova campanha -->
  <Dialog v-model="showNova" :options="{ title: __('Nova campanha'), size: 'xl' }">
    <template #body-content>
      <div class="space-y-4">
        <div class="grid gap-3 sm:grid-cols-2">
          <FormControl type="select" :label="__('Plataforma')" v-model="nova.plataforma" :options="['Google', 'Meta']" />
          <FormControl
            type="select"
            :label="__('Objetivo')"
            v-model="nova.objetivo"
            :options="['Contatos', 'Visitas ao site', 'Mensagens no WhatsApp', 'Reconhecimento', 'Seguidores']"
          />
        </div>
        <FormControl
          type="number"
          :label="__('Orçamento por dia (R$)')"
          v-model="nova.orcamento"
          :description="__('Quanto você aceita gastar por dia. Pode deixar em branco e a IA sugere.')"
        />
        <FormControl
          v-if="status.juridico"
          type="text"
          :label="__('Área do direito')"
          v-model="nova.area"
          :description="__('Ex.: trabalhista, previdenciário, família.')"
        />
        <FormControl
          type="select"
          :label="__('De onde parte')"
          v-model="nova.origem"
          :options="['Briefing', 'Publicação do Instagram']"
        />
        <FormControl
          v-if="nova.origem === 'Publicação do Instagram'"
          type="text"
          :label="__('Referência da publicação')"
          v-model="nova.origem_referencia"
          :description="__('O link ou o código do Reel que vai virar anúncio.')"
        />
        <FormControl
          type="textarea"
          :rows="5"
          :label="__('Briefing')"
          v-model="nova.briefing"
          :placeholder="__('O que você faz, para quem, em que cidade e o que a pessoa deve fazer depois de clicar.')"
        />
        <div v-if="!status.ia_configurada" class="rounded-md bg-surface-amber-1 p-3 text-p-sm text-ink-gray-7">
          {{ __('A chave da IA não está configurada neste site, então a montagem automática está indisponível. Você pode criar a campanha à mão e preencher os grupos depois.') }}
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Criar à mão')" @click="criarManual" />
        <Button
          variant="solid"
          :label="'✦ ' + __('Montar com IA')"
          :loading="trabalhando"
          :disabled="!status.ia_configurada"
          @click="gerar"
        />
      </div>
    </template>
  </Dialog>

  <!-- glossário -->
  <Dialog v-model="showGlossario" :options="{ title: __('O que significa cada termo'), size: '2xl' }">
    <template #body-content>
      <div class="space-y-3">
        <div v-for="(texto, termo) in glossario" :key="termo" class="border-b border-outline-gray-1 pb-2 last:border-0">
          <div class="text-p-base-medium text-ink-gray-9">{{ termo }}</div>
          <p class="text-p-sm text-ink-gray-7">{{ texto }}</p>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const campanhas = ref([])
const selecionada = ref(null)
const atual = ref(null)
const glossario = ref({})
const status = reactive({ juridico: false, ia_configurada: false, publicacao_direta: false })
const trabalhando = ref(false)
const showNova = ref(false)
const showGlossario = ref(false)

const nova = reactive({
  plataforma: 'Google',
  objetivo: 'Contatos',
  orcamento: null,
  area: '',
  origem: 'Briefing',
  origem_referencia: '',
  briefing: '',
})

const reais = (centavos) =>
  'R$ ' + ((centavos || 0) / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function corStatus(s) {
  if (s === 'Aprovada') return 'bg-surface-green-2 text-ink-green-3'
  if (s === 'Publicada (pausada)') return 'bg-surface-blue-2 text-ink-blue-3'
  if (s === 'Arquivada') return 'bg-surface-gray-3 text-ink-gray-6'
  return 'bg-surface-amber-2 text-ink-amber-3'
}

async function carregarLista() {
  campanhas.value = await call('crm.api.anuncios.listar')
}

async function selecionar(name) {
  selecionada.value = name
  atual.value = await call('crm.api.anuncios.obter', { name })
}

function abrirNova() {
  showNova.value = true
}

async function gerar() {
  if (!nova.briefing.trim()) {
    toast.error(__('Escreva o briefing antes.'))
    return
  }
  trabalhando.value = true
  try {
    const doc = await call('crm.api.anuncios.gerar', {
      briefing: nova.briefing,
      plataforma: nova.plataforma,
      objetivo: nova.objetivo,
      orcamento_diario_centavos: Math.round((Number(nova.orcamento) || 0) * 100),
      origem: nova.origem,
      origem_referencia: nova.origem_referencia || null,
      area: nova.area || null,
    })
    showNova.value = false
    await carregarLista()
    selecionada.value = doc.name
    atual.value = doc
    toast.success(__('Campanha montada. Ela está em rascunho e pausada.'))
  } catch (e) {
    toast.error(e.messages?.[0] || e.message || __('Não consegui montar a campanha.'))
  } finally {
    trabalhando.value = false
  }
}

async function criarManual() {
  trabalhando.value = true
  try {
    const r = await call('crm.api.anuncios.criar_manual', {
      titulo: nova.briefing.slice(0, 60) || __('Campanha sem nome'),
      plataforma: nova.plataforma,
      objetivo: nova.objetivo,
      orcamento_diario_centavos: Math.round((Number(nova.orcamento) || 0) * 100),
    })
    showNova.value = false
    await carregarLista()
    await selecionar(r.name)
  } catch (e) {
    toast.error(e.messages?.[0] || e.message)
  } finally {
    trabalhando.value = false
  }
}

async function aprovar() {
  trabalhando.value = true
  try {
    await call('crm.api.anuncios.aprovar', { name: selecionada.value })
    await carregarLista()
    await selecionar(selecionada.value)
    toast.success(__('Campanha aprovada. Ela continua pausada até você publicar.'))
  } catch (e) {
    toast.error(e.messages?.[0] || e.message)
  } finally {
    trabalhando.value = false
  }
}

function baixar(nomeArquivo, conteudo, tipo) {
  const blob = new Blob([conteudo], { type: tipo })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomeArquivo
  a.click()
  URL.revokeObjectURL(url)
}

async function exportar() {
  trabalhando.value = true
  try {
    if (atual.value.plataforma === 'Google') {
      const r = await call('crm.api.anuncios.exportar_google', { name: selecionada.value })
      baixar(r.nome_arquivo, r.csv, 'text/csv;charset=utf-8')
      toast.success(r.instrucao)
    } else {
      const r = await call('crm.api.anuncios.exportar_meta', { name: selecionada.value })
      baixar(r.nome_arquivo, r.texto, 'text/plain;charset=utf-8')
      toast.success(r.instrucao)
    }
  } catch (e) {
    toast.error(e.messages?.[0] || e.message)
  } finally {
    trabalhando.value = false
  }
}

async function publicar() {
  trabalhando.value = true
  try {
    await call('crm.api.anuncios.publicar', { name: selecionada.value })
    await selecionar(selecionada.value)
  } catch (e) {
    toast.error(e.messages?.[0] || e.message)
  } finally {
    trabalhando.value = false
  }
}

async function arquivar() {
  await call('crm.api.anuncios.arquivar', { name: selecionada.value })
  await carregarLista()
  atual.value = null
  selecionada.value = null
}

onMounted(async () => {
  const [s, g] = await Promise.all([
    call('crm.api.anuncios.status'),
    call('crm.api.anuncios.glossario'),
  ])
  Object.assign(status, s)
  glossario.value = g.termos
  await carregarLista()
  if (campanhas.value.length) await selecionar(campanhas.value[0].name)
})
</script>
