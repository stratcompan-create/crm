<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Prospecção') }}</div>
    </template>
    <template #right-header>
      <span class="mr-1 text-p-sm text-ink-gray-5">{{ saveState }}</span>
      <Button :label="__('Baixar semana')" @click="downloadCsv">
        <template #prefix><span class="lucide-download size-4" aria-hidden="true" /></template>
      </Button>
      <Button :label="__('Configurar')" @click="openConfig">
        <template #prefix><span class="lucide-settings size-4" aria-hidden="true" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
    <!-- KPIs -->
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div v-for="k in kpis" :key="k.label" class="rounded-lg border border-outline-gray-2 bg-surface-base p-4">
        <div class="flex items-center gap-2 text-p-sm text-ink-gray-6">
          <span class="size-2 rounded-sm" :style="{ background: k.color }" />{{ k.label }}
        </div>
        <div class="mt-1 text-3xl font-semibold tabular-nums text-ink-gray-9">{{ k.value }}</div>
        <div class="mt-0.5 text-p-sm tabular-nums" :class="k.cls">{{ k.sub }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-5">
      <!-- Registro do dia -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5 xl:col-span-2">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-p-lg-medium text-ink-gray-9">{{ __('Registro do dia') }}</h2>
          <div class="flex items-center gap-1">
            <span v-if="selDate === today" class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-7">{{ __('hoje') }}</span>
            <Button variant="ghost" @click="shiftDay(-1)"><span class="lucide-chevron-left size-4" aria-hidden="true" /></Button>
            <input :value="selDate" type="date" class="rounded border border-outline-gray-3 bg-surface-base px-2 py-1 text-p-sm text-ink-gray-9" @change="setDate($event.target.value)" />
            <Button variant="ghost" @click="shiftDay(1)"><span class="lucide-chevron-right size-4" aria-hidden="true" /></Button>
          </div>
        </div>

        <div v-for="st in stages" :key="st.key" class="flex items-center justify-between border-b border-outline-gray-1 py-2.5 last:border-0">
          <div>
            <div class="text-p-base-medium text-ink-gray-9">{{ __(st.label) }}</div>
            <div v-if="st.hint" class="text-p-xs text-ink-gray-5">{{ __(st.hint) }}</div>
          </div>
          <div v-if="st.derived" class="min-w-16 rounded-full bg-surface-gray-2 px-3 py-1 text-center text-p-base-medium tabular-nums text-ink-gray-9">
            {{ respTotal(selDay) }}
          </div>
          <div v-else class="flex items-center overflow-hidden rounded-full border border-outline-gray-3">
            <button class="size-8 text-lg hover:bg-surface-gray-2" @click="bump(st.key, -1)">−</button>
            <span class="min-w-10 text-center text-p-base-medium tabular-nums text-ink-gray-9">{{ selDay[st.key] || 0 }}</span>
            <button class="size-8 text-lg hover:bg-surface-gray-2" @click="bump(st.key, 1)">+</button>
          </div>
        </div>

        <div class="mb-2 mt-4 text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Respostas positivas por canal') }}</div>
        <div class="flex flex-wrap gap-2">
          <div v-for="c in cfg.canais" :key="c" class="flex items-center overflow-hidden rounded-full border border-outline-gray-3 text-p-sm">
            <button class="h-8 w-7 hover:bg-surface-gray-2" @click="bumpMap('respostas', c, -1)">−</button>
            <span class="px-1.5 text-ink-gray-8">{{ __(c) }}</span>
            <span class="min-w-5 text-center font-medium tabular-nums text-ink-gray-9">{{ (selDay.respostas || {})[c] || 0 }}</span>
            <button class="h-8 w-7 hover:bg-surface-gray-2" @click="bumpMap('respostas', c, 1)">+</button>
          </div>
          <div v-if="adding === 'canais'" class="flex items-center gap-1">
            <input v-model="newName" type="text" :placeholder="__('Nome do canal (ex: Ligação)')" class="h-8 w-44 rounded-full border border-outline-gray-3 bg-surface-base px-3 text-p-sm text-ink-gray-9" @vue:mounted="({ el }) => el.focus()" @keydown.enter="confirmAdd('canais')" @keydown.esc="adding = null" />
            <Button variant="solid" :label="__('Criar')" @click="confirmAdd('canais')" />
            <Button variant="ghost" @click="adding = null">×</Button>
          </div>
          <button v-else class="h-8 rounded-full border border-dashed border-outline-gray-3 px-3 text-p-sm text-ink-gray-6 hover:border-[var(--stratcompany-accent)] hover:text-ink-gray-9" @click="startAdd('canais')">+ {{ __('Novo canal') }}</button>
        </div>
        <div class="mt-1 text-p-xs text-ink-gray-4">{{ __('Leads criados no CRM com essa origem já entram na conta automaticamente.') }}</div>

        <div class="mb-2 mt-4 text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Objeções do dia') }}</div>
        <div class="flex flex-wrap gap-2">
          <div v-for="o in cfg.objecoes" :key="o" class="flex items-center overflow-hidden rounded-full border border-outline-gray-3 text-p-sm">
            <button class="h-8 w-7 hover:bg-surface-gray-2" @click="bumpMap('objecoes', o, -1)">−</button>
            <span class="px-1.5 text-ink-gray-8">{{ __(o) }}</span>
            <span class="min-w-5 text-center font-medium tabular-nums text-ink-gray-9">{{ (selDay.objecoes || {})[o] || 0 }}</span>
            <button class="h-8 w-7 hover:bg-surface-gray-2" @click="bumpMap('objecoes', o, 1)">+</button>
          </div>
          <div v-if="adding === 'objecoes'" class="flex items-center gap-1">
            <input v-model="newName" type="text" :placeholder="__('Nome da objeção (ex: Já tem agência)')" class="h-8 w-52 rounded-full border border-outline-gray-3 bg-surface-base px-3 text-p-sm text-ink-gray-9" @vue:mounted="({ el }) => el.focus()" @keydown.enter="confirmAdd('objecoes')" @keydown.esc="adding = null" />
            <Button variant="solid" :label="__('Criar')" @click="confirmAdd('objecoes')" />
            <Button variant="ghost" @click="adding = null">×</Button>
          </div>
          <button v-else class="h-8 rounded-full border border-dashed border-outline-gray-3 px-3 text-p-sm text-ink-gray-6 hover:border-[var(--stratcompany-accent)] hover:text-ink-gray-9" @click="startAdd('objecoes')">+ {{ __('Nova objeção') }}</button>
        </div>
      </section>

      <!-- Funil + fontes + objeções -->
      <div class="flex flex-col gap-4 xl:col-span-3">
        <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-p-lg-medium text-ink-gray-9">{{ __('Funil de conversão') }}</h2>
            <div class="flex rounded-full border border-outline-gray-3 p-0.5 text-p-sm">
              <button v-for="p in periods" :key="p.key" class="rounded-full px-3 py-1"
                :class="period === p.key ? 'bg-[var(--stratcompany-accent)] text-white' : 'text-ink-gray-7'" @click="period = p.key">
                {{ __(p.label) }}
              </button>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <div v-for="row in funnel" :key="row.key" class="grid grid-cols-[9rem_1fr] items-center gap-3">
              <div class="text-p-sm text-ink-gray-7">{{ __(row.label) }}</div>
              <div class="flex items-center gap-3">
                <div class="flex h-7 min-w-[2.5rem] items-center justify-center rounded bg-[var(--stratcompany-accent)] px-2 text-p-sm font-medium tabular-nums text-white transition-all" :style="{ width: row.width + '%' }">{{ row.value }}</div>
                <span class="whitespace-nowrap text-p-xs tabular-nums text-ink-gray-5">{{ row.conv }}</span>
              </div>
            </div>
          </div>
        </section>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
            <h2 class="mb-3 text-p-lg-medium text-ink-gray-9">{{ __('Fontes') }}</h2>
            <div v-if="!sources.length" class="text-p-sm italic text-ink-gray-4">{{ __('Sem registros no período.') }}</div>
            <div v-for="s in sources" :key="s.k" class="mb-2.5">
              <div class="flex justify-between text-p-sm"><span class="text-ink-gray-8">{{ __(s.k) }}</span><b class="tabular-nums text-ink-gray-9">{{ s.v }}</b></div>
              <div class="mt-1 h-2 overflow-hidden rounded-full bg-surface-gray-2"><div class="h-2 rounded-full bg-[var(--stratcompany-accent)]" :style="{ width: s.pct + '%' }" /></div>
            </div>
          </section>
          <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
            <h2 class="mb-3 text-p-lg-medium text-ink-gray-9">{{ __('Objeções') }}</h2>
            <div v-if="!objections.length" class="text-p-sm italic text-ink-gray-4">{{ __('Sem registros no período.') }}</div>
            <div v-for="s in objections" :key="s.k" class="mb-2.5">
              <div class="flex justify-between text-p-sm"><span class="text-ink-gray-8">{{ __(s.k) }}</span><b class="tabular-nums text-ink-gray-9">{{ s.v }}</b></div>
              <div class="mt-1 h-2 overflow-hidden rounded-full bg-surface-gray-2"><div class="h-2 rounded-full bg-ink-amber-4" :style="{ width: s.pct + '%' }" /></div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <!-- Metas + constância -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
        <div class="mb-3 flex items-baseline justify-between">
          <h2 class="text-p-lg-medium text-ink-gray-9">{{ __('Metas') }}</h2>
          <span class="text-p-sm text-ink-gray-5">{{ cfg.meta_diaria }} {{ __('leads/dia') }}</span>
        </div>
        <div v-for="m in meters" :key="m.title" class="mb-4 last:mb-0">
          <div class="flex items-baseline justify-between text-p-sm">
            <span class="font-medium text-ink-gray-9">{{ __(m.title) }} <span class="font-normal text-ink-gray-5">· {{ m.sub }}</span></span>
            <span class="tabular-nums text-ink-gray-6"><b class="text-ink-gray-9">{{ m.value }}</b> / {{ m.goal }}</span>
          </div>
          <div class="mt-1.5 h-3 overflow-hidden rounded-full bg-surface-gray-2"><div class="h-3 rounded-full transition-all" :style="{ width: Math.min(100, m.pct) + '%', background: m.color }" /></div>
          <div class="mt-1 text-p-xs tabular-nums text-ink-gray-5">{{ m.pct }}% {{ __('da meta') }}<span v-if="m.pct >= 100"> ✓</span></div>
        </div>
      </section>
      <section class="rounded-lg border border-outline-gray-2 bg-surface-base p-5">
        <h2 class="mb-3 text-p-lg-medium text-ink-gray-9">{{ __('Leads abordados · 14 dias') }}</h2>
        <svg viewBox="0 0 520 128" width="100%" preserveAspectRatio="none" class="block" role="img" :aria-label="__('Leads abordados por dia')">
          <line :x1="8" :x2="512" :y1="spark.goalY" :y2="spark.goalY" stroke="currentColor" class="text-ink-gray-4" stroke-dasharray="4 4" />
          <path :d="spark.area" fill="var(--stratcompany-accent)" opacity="0.15" />
          <path :d="spark.line" fill="none" stroke="var(--stratcompany-accent)" stroke-width="2" stroke-linejoin="round" />
          <circle v-if="spark.last" :cx="spark.last[0]" :cy="spark.last[1]" r="3.5" fill="var(--stratcompany-accent)" />
          <text v-for="l in spark.labels" :key="l.x" :x="l.x" y="126" font-size="8.5" text-anchor="middle" fill="currentColor" class="text-ink-gray-5">{{ l.t }}</text>
        </svg>
        <div class="mt-2 text-p-xs text-ink-gray-5">{{ __('abordados por dia') }} · {{ __('linha tracejada = meta') }} ({{ cfg.meta_diaria }})</div>
      </section>
    </div>
  </div>

  <!-- Configurar -->
  <div v-if="showConfig" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="closeConfig">
    <div class="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg bg-surface-elevation-2 p-5 shadow-2xl">
      <h3 class="mb-4 text-lg font-semibold text-ink-gray-9">{{ __('Configurar prospecção') }}</h3>
      <label class="mb-1 block text-p-sm font-medium text-ink-gray-7">{{ __('Meta diária de leads abordados') }}</label>
      <input v-model.number="draft.meta" type="number" min="1" class="mb-4 w-full rounded border border-outline-gray-3 bg-surface-base px-3 py-2 text-p-base text-ink-gray-9" />
      <div v-for="grp in [{ key: 'canais', label: 'Canais de resposta', ph: 'Novo canal (ex: LinkedIn)' }, { key: 'objecoes', label: 'Tipos de objeção', ph: 'Nova objeção (ex: Sem interesse)' }]" :key="grp.key" class="mb-4">
        <label class="mb-1 block text-p-sm font-medium text-ink-gray-7">{{ __(grp.label) }}</label>
        <div class="mb-2 flex flex-wrap gap-2">
          <span v-for="(v, i) in draft[grp.key]" :key="v" class="flex items-center gap-1 rounded-full border border-outline-gray-3 py-0.5 pl-3 pr-1 text-p-sm text-ink-gray-8">
            {{ v }}<button class="size-5 rounded-full text-ink-gray-5 hover:bg-surface-gray-3" @click="draft[grp.key].splice(i, 1)">×</button>
          </span>
        </div>
        <div class="flex gap-2">
          <input v-model="draft.new[grp.key]" type="text" :placeholder="grp.ph" class="flex-1 rounded border border-outline-gray-3 bg-surface-base px-3 py-2 text-p-base text-ink-gray-9" @keydown.enter="addTag(grp.key)" />
          <Button :label="__('Adicionar')" @click="addTag(grp.key)" />
        </div>
      </div>
      <div class="mt-5 flex justify-end gap-2">
        <Button :label="__('Cancelar')" @click="showConfig = false" />
        <Button variant="solid" :label="__('Salvar')" @click="saveConfig" />
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Button, call, createResource } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const stages = [
  { key: 'abordados', label: 'Abordados', hint: 'leads prospectados' },
  { key: 'respostas', label: 'Respostas +', hint: 'soma dos canais abaixo', derived: true },
  { key: 'agendadas', label: 'Reuniões agendadas' },
  { key: 'realizadas', label: 'Reuniões realizadas' },
  { key: 'propostas', label: 'Propostas enviadas' },
  { key: 'fechamentos', label: 'Fechamentos', hint: 'inclui negócios ganhos no CRM' },
]
const COUNT_KEYS = ['abordados', 'agendadas', 'realizadas', 'propostas', 'fechamentos']
const periods = [
  { key: 'today', label: 'Hoje' },
  { key: 'week', label: 'Semana' },
  { key: 'month', label: 'Mês' },
]

/* ---------- datas ---------- */
const pad = (n) => (n < 10 ? '0' : '') + n
const fmt = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const parseD = (s) => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
const addDays = (s, n) => {
  const d = parseD(s)
  d.setDate(d.getDate() + n)
  return fmt(d)
}
const today = fmt(new Date())
const mondayOf = (s) => {
  const d = parseD(s)
  d.setDate(d.getDate() + (d.getDay() === 0 ? -6 : 1 - d.getDay()))
  return fmt(d)
}
function monthDates(s) {
  const d = parseD(s)
  const out = []
  const dt = new Date(d.getFullYear(), d.getMonth(), 1)
  while (dt.getMonth() === d.getMonth()) {
    out.push(fmt(dt))
    dt.setDate(dt.getDate() + 1)
  }
  return out
}
const businessDays = (s) => monthDates(s).filter((x) => ![0, 6].includes(parseD(x).getDay())).length
const monthName = (s) =>
  parseD(s).toLocaleDateString('pt-BR', { month: 'long' })
function periodDates(p, ref) {
  if (p === 'today') return [ref]
  if (p === 'week') return Array.from({ length: 7 }, (_, i) => addDays(mondayOf(ref), i))
  return monthDates(ref)
}
function prevDates(p, ref) {
  if (p === 'today') return [addDays(ref, -1)]
  if (p === 'week') return periodDates('week', addDays(mondayOf(ref), -1))
  const d = parseD(ref)
  return monthDates(fmt(new Date(d.getFullYear(), d.getMonth() - 1, 1)))
}

/* ---------- estado ---------- */
const selDate = ref(today)
const period = ref('week')
const saveState = ref('')
const cfg = reactive({ meta_diaria: 20, canais: [], objecoes: [] })
const days = reactive({})
const auto = reactive({})

const overview = createResource({
  url: 'crm.api.prospeccao.get_overview',
  auto: true,
  onSuccess(data) {
    cfg.meta_diaria = data.config.meta_diaria
    cfg.canais = data.config.canais
    cfg.objecoes = data.config.objecoes
    for (const k of Object.keys(days)) delete days[k]
    for (const k of Object.keys(auto)) delete auto[k]
    Object.assign(days, data.days)
    Object.assign(auto, data.auto)
  },
})

const blank = () => ({ abordados: 0, agendadas: 0, realizadas: 0, propostas: 0, fechamentos: 0, respostas: {}, objecoes: {} })

// Valor efetivo do dia = o que você registrou, ou o que o CRM já sabe sozinho (o maior).
function eff(date) {
  const m = days[date] || blank()
  const a = auto[date] || {}
  const respostas = { ...(m.respostas || {}) }
  for (const [k, v] of Object.entries(a.respostas || {})) {
    if (cfg.canais.includes(k)) respostas[k] = Math.max(respostas[k] || 0, v)
  }
  return { ...m, fechamentos: Math.max(m.fechamentos || 0, a.fechamentos || 0), respostas }
}
const respTotal = (d) => Object.values(d.respostas || {}).reduce((s, n) => s + (n || 0), 0)
const selDay = computed(() => eff(selDate.value))

const timers = {}
function persist(date) {
  saveState.value = __('salvando…')
  clearTimeout(timers[date])
  timers[date] = setTimeout(async () => {
    const d = days[date]
    try {
      await call('crm.api.prospeccao.save_day', {
        date,
        ...COUNT_KEYS.reduce((o, k) => ({ ...o, [k]: d[k] || 0 }), {}),
        respostas: JSON.stringify(d.respostas || {}),
        objecoes: JSON.stringify(d.objecoes || {}),
      })
      saveState.value = __('salvo')
    } catch (e) {
      saveState.value = __('erro ao salvar')
    }
  }, 400)
}
function ensureDay(date) {
  if (!days[date]) days[date] = blank()
  return days[date]
}
function bump(key, delta) {
  const date = selDate.value
  const cur = eff(date)[key] || 0
  const d = ensureDay(date)
  for (const k of COUNT_KEYS) d[k] = eff(date)[k] || 0
  d[key] = Math.max(0, cur + delta)
  persist(date)
}
function bumpMap(field, name, delta) {
  const date = selDate.value
  const e = eff(date)
  const d = ensureDay(date)
  for (const k of COUNT_KEYS) d[k] = e[k] || 0
  d.respostas = { ...e.respostas }
  d.objecoes = { ...(d.objecoes || {}) }
  const next = Math.max(0, ((field === 'respostas' ? e.respostas : d.objecoes)[name] || 0) + delta)
  if (next === 0) delete d[field][name]
  else d[field][name] = next
  persist(date)
}
const shiftDay = (n) => (selDate.value = addDays(selDate.value, n))
const setDate = (v) => {
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) selDate.value = v
}

/* ---------- agregação ---------- */
function aggregate(dates) {
  const a = { abordados: 0, agendadas: 0, realizadas: 0, propostas: 0, fechamentos: 0, respostas: 0, resp: {}, obj: {} }
  for (const dt of dates) {
    const d = eff(dt)
    for (const k of COUNT_KEYS) a[k] += d[k] || 0
    a.respostas += respTotal(d)
    for (const [k, v] of Object.entries(d.respostas || {})) a.resp[k] = (a.resp[k] || 0) + v
    for (const [k, v] of Object.entries(d.objecoes || {})) a.obj[k] = (a.obj[k] || 0) + v
  }
  return a
}
const agg = computed(() => aggregate(periodDates(period.value, selDate.value)))
const prevAgg = computed(() => aggregate(prevDates(period.value, selDate.value)))

const pctDelta = (cur, prev) => (prev === 0 ? (cur > 0 ? 100 : 0) : Math.round(((cur - prev) / prev) * 100))
const periodGoal = computed(() =>
  period.value === 'today'
    ? cfg.meta_diaria
    : period.value === 'week'
      ? cfg.meta_diaria * 5
      : cfg.meta_diaria * businessDays(selDate.value),
)
const kpis = computed(() => {
  const a = agg.value
  const b = prevAgg.value
  const delta = (cur, prev) => {
    const d = pctDelta(cur, prev)
    return {
      sub: `${d > 0 ? '▲' : d < 0 ? '▼' : '·'} ${Math.abs(d)}% ${__('vs período anterior')}`,
      cls: d > 0 ? 'text-ink-green-6' : d < 0 ? 'text-ink-red-6' : 'text-ink-gray-5',
    }
  }
  return [
    { label: __('Abordados'), value: a.abordados, color: 'var(--stratcompany-accent)', sub: `${__('meta')} ${periodGoal.value} · ${periodGoal.value ? Math.round((a.abordados / periodGoal.value) * 100) : 0}%`, cls: 'text-ink-gray-5' },
    { label: __('Respostas +'), value: a.respostas, color: '#25A667', ...delta(a.respostas, b.respostas) },
    { label: __('Reuniões'), value: a.realizadas, color: '#A9884E', ...delta(a.realizadas, b.realizadas) },
    { label: __('Fechamentos'), value: a.fechamentos, color: '#0C8A3E', ...delta(a.fechamentos, b.fechamentos) },
  ]
})

const funnel = computed(() => {
  const a = agg.value
  const order = [
    ['abordados', 'Abordados'],
    ['respostas', 'Respostas +'],
    ['agendadas', 'Reuniões agendadas'],
    ['realizadas', 'Reuniões realizadas'],
    ['propostas', 'Propostas enviadas'],
    ['fechamentos', 'Fechamentos'],
  ]
  const max = Math.max(1, a.abordados, a.respostas)
  let prev = null
  return order.map(([key, label], i) => {
    const value = a[key]
    let conv = ''
    if (i > 0 && prev != null) conv = `→ ${prev > 0 ? Math.round((value / prev) * 100) : 0}%`
    if (key === 'fechamentos') conv = `${__('de abordado')}: ${a.abordados > 0 ? ((value / a.abordados) * 100).toFixed(1) : 0}%`
    prev = value
    return { key, label, value, conv, width: Math.min(100, Math.max(value > 0 ? 8 : 2, Math.round((value / max) * 100))) }
  })
})

function ranking(obj) {
  const arr = Object.entries(obj).map(([k, v]) => ({ k, v })).sort((x, y) => y.v - x.v)
  const max = arr[0]?.v || 1
  return arr.map((i) => ({ ...i, pct: Math.round((i.v / max) * 100) }))
}
const sources = computed(() => ranking(agg.value.resp))
const objections = computed(() => ranking(agg.value.obj))

const meters = computed(() => {
  const bd = businessDays(selDate.value)
  const rows = [
    { title: 'Hoje', sub: parseD(selDate.value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }), value: aggregate([selDate.value]).abordados, goal: cfg.meta_diaria },
    { title: 'Semana', sub: '5 dias úteis', value: aggregate(periodDates('week', selDate.value)).abordados, goal: cfg.meta_diaria * 5 },
    { title: 'Mês', sub: `${monthName(selDate.value)} · ${bd} úteis`, value: aggregate(monthDates(selDate.value)).abordados, goal: cfg.meta_diaria * bd },
  ]
  return rows.map((r) => {
    const pct = r.goal > 0 ? Math.round((r.value / r.goal) * 100) : 0
    return { ...r, pct, color: pct >= 100 ? '#0C8A3E' : pct >= 60 ? '#C6871A' : '#C0392B' }
  })
})

const spark = computed(() => {
  const dates = Array.from({ length: 14 }, (_, i) => addDays(selDate.value, i - 13))
  const vals = dates.map((d) => eff(d).abordados || 0)
  const goal = cfg.meta_diaria
  const max = Math.max(goal, ...vals, 1)
  const W = 520, H = 112, p = 8
  const bw = (W - p * 2) / dates.length
  const pts = vals.map((v, i) => [p + bw * i + bw / 2, H - p - (v / max) * (H - p * 2)])
  const line = 'M' + pts.map((q) => q.map((n) => n.toFixed(1)).join(',')).join(' L')
  const area = `M${p},${H - p} ` + pts.map((q) => `L${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(' ') + ` L${W - p},${H - p} Z`
  return {
    line, area,
    goalY: H - p - (goal / max) * (H - p * 2),
    last: pts[pts.length - 1],
    labels: dates.map((d, i) => ({ x: p + bw * i + bw / 2, t: parseD(d).getDate(), show: i % 2 === 0 || i === dates.length - 1 })).filter((l) => l.show),
  }
})

/* ---------- criar canal / objeção na hora ---------- */
const adding = ref(null)
const newName = ref('')
function startAdd(key) {
  newName.value = ''
  adding.value = key
}
async function confirmAdd(key) {
  const name = newName.value.trim().replace(/[,\n]/g, ' ')
  adding.value = null
  if (!name || cfg[key].some((v) => v.toLowerCase() === name.toLowerCase())) return
  try {
    const res = await call('crm.api.prospeccao.save_config', {
      meta_diaria: cfg.meta_diaria,
      canais: key === 'canais' ? [...cfg.canais, name] : cfg.canais,
      objecoes: key === 'objecoes' ? [...cfg.objecoes, name] : cfg.objecoes,
    })
    Object.assign(cfg, res)
    saveState.value = key === 'canais' ? __('canal criado') : __('objeção criada')
  } catch (e) {
    saveState.value = __('erro ao salvar')
  }
}

/* ---------- configuração ---------- */
const showConfig = ref(false)
const draft = reactive({ meta: 20, canais: [], objecoes: [], new: { canais: '', objecoes: '' } })
function openConfig() {
  draft.meta = cfg.meta_diaria
  draft.canais = [...cfg.canais]
  draft.objecoes = [...cfg.objecoes]
  draft.new.canais = ''
  draft.new.objecoes = ''
  showConfig.value = true
}
const closeConfig = () => (showConfig.value = false)
function addTag(key) {
  const v = draft.new[key].trim()
  if (v && !draft[key].includes(v)) draft[key].push(v)
  draft.new[key] = ''
}
async function saveConfig() {
  addTag('canais')
  addTag('objecoes')
  const res = await call('crm.api.prospeccao.save_config', {
    meta_diaria: draft.meta || 20,
    canais: draft.canais,
    objecoes: draft.objecoes,
  })
  Object.assign(cfg, res)
  showConfig.value = false
}

/* ---------- CSV (formato lido pela skill do relatório semanal) ---------- */
function buildCsv() {
  const keys = new Set([...Object.keys(days), ...Object.keys(auto)])
  const list = [...keys].sort().filter((k) => {
    const d = eff(k)
    return COUNT_KEYS.some((c) => d[c]) || respTotal(d) || Object.keys(d.objecoes || {}).length
  })
  const clean = (t) => String(t).replace(/[,\n]/g, ' ')
  let out = 'FUNIL DIARIO\nData,abordados,agendadas,realizadas,propostas,fechamentos\n'
  for (const k of list) {
    const d = eff(k)
    out += `${k},${COUNT_KEYS.map((c) => d[c] || 0).join(',')}\n`
  }
  out += '\nRESPOSTAS POSITIVAS POR FONTE\nData,Fonte,Quantidade\n'
  for (const k of list) {
    const r = eff(k).respostas || {}
    for (const f of Object.keys(r).sort()) if (r[f] > 0) out += `${k},${clean(f)},${r[f]}\n`
  }
  out += '\nOBJECOES\nData,Tipo\n'
  for (const k of list) {
    const o = eff(k).objecoes || {}
    for (const t of Object.keys(o).sort()) for (let i = 0; i < o[t]; i++) out += `${k},${clean(t)}\n`
  }
  return out
}
function downloadCsv() {
  const blob = new Blob([buildCsv()], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'dashboard_strat.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>
