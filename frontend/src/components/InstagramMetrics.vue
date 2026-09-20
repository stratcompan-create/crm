<template>
  <div class="flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
    <!-- Cabeçalho: período e atualização -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-1 rounded-lg bg-surface-gray-2 p-1">
        <button
          v-for="p in periods"
          :key="p"
          type="button"
          class="rounded-md px-3 py-1 text-p-sm"
          :class="days === p ? 'bg-white font-medium text-ink-gray-9 shadow-sm' : 'text-ink-gray-6'"
          @click="setDays(p)"
        >
          {{ __('{0} dias', [p]) }}
        </button>
      </div>
      <div class="flex items-center gap-3 text-p-sm text-ink-gray-5">
        <span v-if="data?.atualizado_em">{{ __('Atualizado às {0}', [hora(data.atualizado_em)]) }}</span>
        <Button :label="__('Atualizar')" :loading="resource.loading" @click="load(true)" />
      </div>
    </div>

    <div v-if="resource.error" class="mt-6 rounded-lg border border-outline-gray-2 bg-surface-red-2 p-4 text-p-sm text-ink-red-6">
      {{ resource.error.messages?.[0] || __('Não foi possível carregar as métricas agora.') }}
    </div>

    <div v-else-if="!data" class="py-16 text-center text-p-sm text-ink-gray-5">
      {{ __('Carregando métricas do Instagram...') }}
    </div>

    <template v-else>
      <div class="mt-3 text-p-sm text-ink-gray-5">
        @{{ data.perfil.usuario }} · {{ __('{0} publicações', [num(data.perfil.publicacoes)]) }} ·
        {{ __('últimos {0} dias comparados aos {0} anteriores', [data.dias]) }}
      </div>

      <!-- KPIs -->
      <div class="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
        <div v-for="k in kpis" :key="k.label" class="rounded-lg border border-outline-gray-2 p-4">
          <div class="text-p-sm text-ink-gray-6">{{ k.label }}</div>
          <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ num(k.value) }}</div>
          <div class="mt-1 text-p-sm" :class="k.tone">{{ k.sub }}</div>
        </div>
      </div>

      <!-- No CRM -->
      <div class="mt-6 text-base-semibold text-ink-gray-8">{{ __('No CRM') }}</div>
      <div class="mt-2 grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-outline-gray-2 p-4">
          <div class="text-p-sm text-ink-gray-6">{{ __('Conversas iniciadas') }}</div>
          <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ num(data.crm.conversas) }}</div>
        </div>
        <div class="rounded-lg border border-outline-gray-2 p-4">
          <div class="text-p-sm text-ink-gray-6">{{ __('Leads novos do Instagram') }}</div>
          <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ num(data.crm.leads_novos) }}</div>
        </div>
        <div class="rounded-lg border border-outline-gray-2 p-4">
          <div class="text-p-sm text-ink-gray-6">{{ __('Mensagens recebidas') }}</div>
          <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ num(data.crm.mensagens_recebidas) }}</div>
        </div>
      </div>

      <!-- Alcance por dia -->
      <div class="mt-6 rounded-lg border border-outline-gray-2 p-4">
        <div class="mb-2 flex items-center justify-between">
          <div class="text-base-semibold text-ink-gray-8">{{ __('Alcance por dia') }}</div>
          <div class="text-p-sm text-ink-gray-5">{{ __('contas diferentes alcançadas') }}</div>
        </div>
        <svg v-if="bars.length" viewBox="0 0 600 150" class="h-40 w-full">
          <g v-for="b in bars" :key="b.date">
            <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="1.5" class="fill-[#8aa1a9]">
              <title>{{ b.title }}</title>
            </rect>
          </g>
          <text x="0" y="148" class="fill-[#7a8a90] text-[9px]">{{ bars[0].label }}</text>
          <text x="600" y="148" text-anchor="end" class="fill-[#7a8a90] text-[9px]">{{ bars[bars.length - 1].label }}</text>
        </svg>
        <div v-else class="py-8 text-center text-p-sm text-ink-gray-5">{{ __('Sem dados no período.') }}</div>
      </div>

      <!-- Posts -->
      <div class="mt-6 flex items-center justify-between">
        <div class="text-base-semibold text-ink-gray-8">{{ __('Últimos posts') }}</div>
        <FormControl v-model="sortBy" type="select" :options="sortOptions" class="w-52" />
      </div>
      <div class="mt-2 overflow-x-auto rounded-lg border border-outline-gray-2">
        <table class="w-full min-w-[640px] text-p-sm">
          <thead>
            <tr class="bg-surface-gray-2 text-left text-ink-gray-6">
              <th class="px-3 py-2 font-medium">{{ __('Post') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Alcance') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Visualizações') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Curtidas') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Comentários') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Salvos') }}</th>
              <th class="px-2 py-2 text-right font-medium">{{ __('Compart.') }}</th>
              <th class="px-3 py-2 text-right font-medium">{{ __('Interação') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in posts" :key="p.id" class="border-t border-outline-gray-1">
              <td class="px-3 py-2">
                <a :href="p.link" target="_blank" rel="noopener" class="flex items-center gap-3">
                  <img
                    v-if="p.imagem"
                    :src="p.imagem"
                    referrerpolicy="no-referrer"
                    loading="lazy"
                    class="size-11 shrink-0 rounded object-cover"
                  />
                  <div v-else class="size-11 shrink-0 rounded bg-surface-gray-2" />
                  <div class="min-w-0">
                    <div class="truncate text-ink-gray-9">{{ p.legenda || __('(sem legenda)') }}</div>
                    <div class="text-xs text-ink-gray-5">{{ __(p.tipo) }} · {{ dataBr(p.data) }}</div>
                  </div>
                </a>
              </td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.alcance) }}</td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.visualizacoes) }}</td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.curtidas) }}</td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.comentarios) }}</td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.salvos) }}</td>
              <td class="px-2 py-2 text-right text-ink-gray-8">{{ num(p.compartilhamentos) }}</td>
              <td class="px-3 py-2 text-right font-medium text-ink-gray-9">{{ p.taxa }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mt-2 text-xs text-ink-gray-5">
        {{ __('Interação = curtidas, comentários, salvos e compartilhamentos divididos pelo alcance do post.') }}
      </div>
    </template>
  </div>
</template>

<script setup>
import { Button, FormControl, createResource } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'

const periods = [7, 14, 30]
const days = ref(30)
const sortBy = ref('recentes')

const resource = createResource({
  url: 'crm.api.instagram_metricas.get_insights',
  makeParams: () => ({ days: days.value, refresh: refreshFlag.value }),
})
const refreshFlag = ref(0)
const data = computed(() => resource.data)

function load(force = false) {
  refreshFlag.value = force ? 1 : 0
  resource.fetch()
}
function setDays(p) {
  days.value = p
  load(false)
}
onMounted(() => load(false))

const fmt = new Intl.NumberFormat('pt-BR')
const num = (v) => fmt.format(Number(v) || 0)
const dataBr = (iso) => (iso ? iso.split('-').reverse().join('/') : '')
const hora = (dt) => (dt || '').slice(11, 16)

function variation(cur, prev) {
  if (!prev) return { sub: __('sem período anterior para comparar'), tone: 'text-ink-gray-5' }
  const pct = Math.round(((cur - prev) / prev) * 100)
  if (pct === 0) return { sub: __('igual ao período anterior'), tone: 'text-ink-gray-5' }
  return {
    sub: `${pct > 0 ? '▲ +' : '▼ '}${pct}% ${__('vs. período anterior')}`,
    tone: pct > 0 ? 'text-ink-green-6' : 'text-ink-red-6',
  }
}

const kpis = computed(() => {
  const d = data.value
  if (!d) return []
  const a = d.atual || {}
  const b = d.anterior || {}
  const fol = d.seguidores_variacao || {}
  const followerSub =
    fol.delta === null || fol.delta === undefined
      ? { sub: __('o crescimento aparece a partir de amanhã'), tone: 'text-ink-gray-5' }
      : {
          sub: `${fol.delta >= 0 ? '▲ +' : '▼ '}${fol.delta} ${__('desde {0}', [dataBr(fol.desde)])}`,
          tone: fol.delta >= 0 ? 'text-ink-green-6' : 'text-ink-red-6',
        }
  return [
    { label: __('Seguidores'), value: d.perfil.seguidores, ...followerSub },
    { label: __('Alcance'), value: a.reach, ...variation(a.reach, b.reach) },
    { label: __('Visualizações'), value: a.views, ...variation(a.views, b.views) },
    { label: __('Visitas ao perfil'), value: a.profile_views, ...variation(a.profile_views, b.profile_views) },
    {
      label: __('Interações'),
      value: a.total_interactions,
      sub: __('{0} curtidas · {1} comentários · {2} salvos · {3} compart.', [
        num(a.likes),
        num(a.comments),
        num(a.saves),
        num(a.shares),
      ]),
      tone: 'text-ink-gray-5',
    },
    { label: __('Cliques no link da bio'), value: a.website_clicks, ...variation(a.website_clicks, b.website_clicks) },
  ]
})

const bars = computed(() => {
  const s = data.value?.serie_alcance || []
  if (!s.length) return []
  const max = Math.max(...s.map((p) => p.value), 1)
  const gap = 3
  const w = 600 / s.length - gap
  return s.map((p, i) => {
    const h = Math.max(2, (p.value / max) * 118)
    return {
      date: p.date,
      x: i * (w + gap),
      y: 128 - h,
      w,
      h,
      label: dataBr(p.date).slice(0, 5),
      title: `${dataBr(p.date)}: ${num(p.value)}`,
    }
  })
})

const sortOptions = [
  { label: __('Mais recentes'), value: 'recentes' },
  { label: __('Maior alcance'), value: 'alcance' },
  { label: __('Mais interações'), value: 'interacoes' },
  { label: __('Maior taxa de interação'), value: 'taxa' },
]
const posts = computed(() => {
  const list = [...(data.value?.posts || [])]
  const by = {
    recentes: (x, y) => (y.data || '').localeCompare(x.data || ''),
    alcance: (x, y) => y.alcance - x.alcance,
    interacoes: (x, y) => y.interacoes - x.interacoes,
    taxa: (x, y) => y.taxa - x.taxa,
  }[sortBy.value]
  return list.sort(by)
})
</script>
