<template>
  <div class="flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
    <!-- Topo -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div v-if="isManager()" class="flex items-center gap-1 rounded-lg bg-surface-gray-2 p-1">
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
      <span v-else />
      <Button variant="solid" iconLeft="plus" :label="__('Nova abordagem')" @click="openApproach" />
    </div>

    <!-- Precisa de você agora -->
    <div class="mt-5 text-base-semibold text-ink-gray-8">{{ __('Precisa de você agora') }}</div>

    <div class="mt-2 rounded-lg border border-outline-gray-2">
      <div class="border-b border-outline-gray-1 px-4 py-2.5 text-p-base-medium text-ink-gray-8">
        {{ __('Follow-ups para enviar') }}
        <span class="ml-1 text-p-sm text-ink-gray-5">({{ followups.data?.length || 0 }})</span>
      </div>
      <div v-if="!followups.data?.length" class="px-4 py-5 text-p-sm text-ink-gray-5">
        {{
          __(
            'Nenhum follow-up pendente. Quando alguém abordado ficar sem responder além do prazo, o CRM cria o follow-up aqui, já com a mensagem pronta.',
          )
        }}
      </div>
      <div v-for="f in followups.data || []" :key="f.task" class="border-b border-outline-gray-1 px-4 py-3 last:border-b-0">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="text-base-medium text-ink-gray-9">{{ f.nome }}</span>
            <span v-if="f.usuario" class="ml-1 text-p-sm text-ink-gray-5">@{{ f.usuario }}</span>
            <div class="text-xs text-ink-gray-5">
              {{ f.canal }} · {{ f.abordagem || __('sem tipo de abordagem') }} ·
              {{ __('follow-up {0}', [f.numero]) }}
            </div>
          </div>
          <Button variant="ghost" :label="__('Abrir lead')" @click="openLead(f.lead)" />
        </div>
        <FormControl v-model="drafts[f.task]" type="textarea" :rows="3" class="mt-2" />
        <div class="mt-2 flex flex-wrap gap-2">
          <Button variant="solid" :label="f.canal === 'WhatsApp' ? __('Copiar e abrir o WhatsApp') : __('Copiar e abrir o Instagram')" @click="sendFollowup(f)" />
          <Button :label="__('Copiar mensagem')" @click="copy(drafts[f.task])" />
          <Button variant="subtle" :label="__('Marcar como feito')" @click="done(f)" />
        </div>
      </div>
    </div>

    <div v-if="isManager()" class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div class="rounded-lg border border-outline-gray-2">
        <div class="border-b border-outline-gray-1 px-4 py-2.5 text-p-base-medium text-ink-gray-8">
          {{ __('Esperando a sua resposta') }}
        </div>
        <div v-if="!data?.aguardando_nos?.length" class="px-4 py-5 text-p-sm text-ink-gray-5">
          {{ __('Ninguém esperando resposta agora.') }}
        </div>
        <div
          v-for="p in data?.aguardando_nos || []"
          :key="p.lead"
          class="flex items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-2.5 last:border-b-0"
        >
          <div class="min-w-0">
            <div class="truncate text-p-base text-ink-gray-9">
              {{ p.nome }} <span v-if="p.usuario" class="text-ink-gray-5">@{{ p.usuario }}</span>
            </div>
            <div class="text-xs text-ink-gray-5">
              <span :class="tempClass(p.temperatura)" class="mr-1 rounded px-1.5 py-0.5 font-medium">{{ __(p.temperatura) }}</span>
              {{ __('espera há {0}', [waited(p.espera_horas)]) }}
              <span v-if="p.objecao"> · {{ __('objeção: {0}', [__(p.objecao)]) }}</span>
            </div>
            <div class="text-xs text-ink-gray-6">{{ p.proxima }}</div>
          </div>
          <Button variant="subtle" :label="__('Responder')" @click="$emit('abrir-conversa', p.lead)" />
        </div>
      </div>

      <div class="rounded-lg border border-outline-gray-2">
        <div class="border-b border-outline-gray-1 px-4 py-2.5 text-p-base-medium text-ink-gray-8">
          {{ __('Abordados que ainda não responderam') }}
        </div>
        <div v-if="!data?.sem_resposta?.length" class="px-4 py-5 text-p-sm text-ink-gray-5">
          {{ __('Nenhuma abordagem sem resposta.') }}
        </div>
        <div
          v-for="p in data?.sem_resposta || []"
          :key="p.lead"
          class="flex items-center justify-between gap-3 border-b border-outline-gray-1 px-4 py-2.5 last:border-b-0"
        >
          <div class="min-w-0">
            <div class="truncate text-p-base text-ink-gray-9">
              {{ p.nome }} <span v-if="p.usuario" class="text-ink-gray-5">@{{ p.usuario }}</span>
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ p.canal }} · {{ p.abordagem || __('sem tipo') }} · {{ __('há {0} dias', [p.dias]) }} ·
              {{ __('{0} follow-up(s)', [p.followups]) }}
            </div>
          </div>
          <Button variant="ghost" :label="__('Abrir lead')" @click="openLead(p.lead)" />
        </div>
      </div>
    </div>

    <!-- Números (gestor) -->
    <template v-if="isManager()">
      <div v-if="resource.error" class="mt-6 rounded-lg border border-outline-gray-2 bg-surface-red-2 p-4 text-p-sm text-ink-red-6">
        {{ resource.error.messages?.[0] || __('Não foi possível carregar os números agora.') }}
      </div>
      <div v-else-if="!data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
      <template v-else>
        <div class="mt-6 text-base-semibold text-ink-gray-8">{{ __('Conversão da prospecção') }}</div>
        <div class="mt-2 grid grid-cols-2 gap-3 lg:grid-cols-3">
          <div v-for="k in kpis" :key="k.label" class="rounded-lg border border-outline-gray-2 p-4">
            <div class="text-p-sm text-ink-gray-6">{{ k.label }}</div>
            <div class="mt-1 text-2xl font-semibold text-ink-gray-9">{{ k.value }}</div>
            <div class="mt-1 text-p-sm" :class="k.tone">{{ k.sub }}</div>
          </div>
        </div>

        <div class="mt-6 rounded-lg border border-outline-gray-2 p-4">
          <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Funil') }}</div>
          <div v-for="s in funnel" :key="s.label" class="mb-2.5">
            <div class="flex justify-between text-p-sm">
              <span class="text-ink-gray-7">{{ s.label }}</span>
              <span class="text-ink-gray-6">{{ s.value }}<span v-if="s.rate !== null"> · {{ s.rate }}%</span></span>
            </div>
            <div class="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-gray-2">
              <div class="h-full rounded-full bg-[#042d3c]" :style="{ width: s.width + '%' }" />
            </div>
          </div>
          <div class="mt-3 text-xs text-ink-gray-5">
            {{ __('Abordagens contam todos os canais registrados; as respostas são só as do Instagram.') }}
          </div>
        </div>

        <div class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div class="rounded-lg border border-outline-gray-2 p-4">
            <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Qual abordagem funciona') }}</div>
            <div v-if="!data.por_abordagem.length" class="text-p-sm text-ink-gray-5">
              {{ __('Registre abordagens com o tipo (site, conteúdo, CRM...) para comparar aqui.') }}
            </div>
            <table v-else class="w-full text-p-sm">
              <thead>
                <tr class="text-left text-ink-gray-5">
                  <th class="pb-1 font-medium">{{ __('Abordagem') }}</th>
                  <th class="pb-1 text-right font-medium">{{ __('Abordados') }}</th>
                  <th class="pb-1 text-right font-medium">{{ __('Responderam') }}</th>
                  <th class="pb-1 text-right font-medium">{{ __('Taxa') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in data.por_abordagem" :key="r.abordagem" class="border-t border-outline-gray-1">
                  <td class="py-1.5 text-ink-gray-8">{{ r.abordagem }}</td>
                  <td class="py-1.5 text-right text-ink-gray-7">{{ r.abordados }}</td>
                  <td class="py-1.5 text-right text-ink-gray-7">{{ r.responderam }}</td>
                  <td class="py-1.5 text-right font-medium text-ink-gray-9">{{ r.taxa }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="rounded-lg border border-outline-gray-2 p-4">
            <div class="mb-3 text-p-base-medium text-ink-gray-8">{{ __('Objeções mais ouvidas') }}</div>
            <div v-if="!data.objecoes.length" class="text-p-sm text-ink-gray-5">{{ __('Sem objeções registradas no período.') }}</div>
            <div v-for="o in data.objecoes" :key="o.nome" class="mb-2 flex justify-between text-p-sm">
              <span class="text-ink-gray-8">{{ o.nome }}</span>
              <span class="font-medium text-ink-gray-9">{{ o.total }}</span>
            </div>
          </div>
        </div>

        <!-- Configuração do follow-up -->
        <div class="mt-6 rounded-lg border border-outline-gray-2">
          <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left" @click="showConfig = !showConfig">
            <span class="text-p-base-medium text-ink-gray-8">{{ __('Como o follow-up automático funciona') }}</span>
            <span :class="showConfig ? 'lucide-chevron-up' : 'lucide-chevron-down'" class="size-4 text-ink-gray-5" aria-hidden="true" />
          </button>
          <div v-if="showConfig && cfg" class="flex flex-col gap-4 border-t border-outline-gray-1 px-4 py-4">
            <p class="text-p-sm text-ink-gray-6">
              {{
                __(
                  'O CRM confere de hora em hora quem foi abordado e não respondeu. Passado o prazo, cria a tarefa de follow-up no lead, com a mensagem pronta. A Meta não permite mandar sozinho para quem não respondeu, então o envio é com um clique.',
                )
              }}
            </p>
            <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
              <input v-model="cfg.ativado" type="checkbox" :true-value="1" :false-value="0" />
              {{ __('Follow-up automático ligado') }}
            </label>
            <div class="grid grid-cols-3 gap-3">
              <div class="flex flex-col gap-1">
                <span class="text-p-sm text-ink-gray-6">{{ __('1º follow-up após (dias)') }}</span>
                <FormControl v-model="cfg.primeiro_dias" type="number" />
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-p-sm text-ink-gray-6">{{ __('Seguintes após (dias)') }}</span>
                <FormControl v-model="cfg.segundo_dias" type="number" />
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-p-sm text-ink-gray-6">{{ __('Máximo por pessoa') }}</span>
                <FormControl v-model="cfg.maximo" type="number" />
              </div>
            </div>
            <div>
              <Button variant="solid" :label="__('Salvar prazos')" @click="saveCfg" />
            </div>

            <div class="text-p-base-medium text-ink-gray-8">{{ __('Mensagens por tipo de abordagem') }}</div>
            <div v-for="a in cfg.abordagens" :key="a.nome" class="rounded-lg border border-outline-gray-1 p-3">
              <div class="mb-1 text-p-sm font-medium text-ink-gray-8">{{ a.nome }}</div>
              <FormControl v-model="a.mensagem" type="textarea" :rows="3" />
              <div class="mt-2 flex gap-2">
                <Button variant="subtle" :label="__('Salvar mensagem')" @click="saveAbordagem(a)" />
                <Button variant="ghost" theme="red" :label="__('Excluir')" @click="removeAbordagem(a)" />
              </div>
            </div>
            <div class="rounded-lg border border-dashed border-outline-gray-2 p-3">
              <div class="mb-1 text-p-sm font-medium text-ink-gray-8">{{ __('Novo tipo de abordagem') }}</div>
              <FormControl v-model="novo.nome" type="text" :placeholder="__('Ex.: Tráfego pago')" class="mb-2" />
              <FormControl v-model="novo.mensagem" type="textarea" :rows="3" :placeholder="__('Oi, {nome}! ...')" />
              <div class="mt-2">
                <Button variant="subtle" :label="__('Adicionar')" @click="addAbordagem" />
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>

    <!-- Nova abordagem -->
    <Dialog v-model="showApproach" :options="{ title: __('Nova abordagem'), size: 'md' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <p class="text-p-sm text-ink-gray-6">
            {{ __('Registre quem você acabou de abordar. O CRM cria o lead, conta na Prospecção de hoje e passa a acompanhar se a pessoa responde.') }}
          </p>
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-7">{{ __('Canal') }}</span>
            <FormControl
              v-model="approach.canal"
              type="select"
              :options="[
                { label: 'Instagram', value: 'Instagram' },
                { label: 'WhatsApp', value: 'WhatsApp' },
              ]"
            />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-7">{{ __('Nome') }}</span>
            <FormControl v-model="approach.nome" type="text" :placeholder="__('Nome da pessoa ou da empresa')" />
          </div>
          <div v-if="approach.canal === 'Instagram'" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-7">{{ __('@ do Instagram') }}</span>
            <FormControl v-model="approach.usuario" type="text" placeholder="@perfil" />
          </div>
          <div v-else class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-7">{{ __('Telefone com DDD') }}</span>
            <FormControl v-model="approach.telefone" type="text" placeholder="(87) 99999-0000" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-7">{{ __('Tipo de abordagem') }}</span>
            <FormControl v-model="approach.abordagem" type="select" :options="tipoOptions" />
          </div>
          <ErrorMessage v-if="approachError" :message="approachError" />
        </div>
      </template>
      <template #actions>
        <Button variant="solid" :label="__('Registrar abordagem')" :loading="registering" @click="registerApproach" />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

defineEmits(['abrir-conversa'])

const router = useRouter()
const { isManager } = usersStore()
const periods = [7, 14, 30]
const days = ref(30)

const resource = createResource({
  url: 'crm.api.instagram_conversas.get_conversation_metrics',
  makeParams: () => ({ days: days.value }),
})
const data = computed(() => resource.data)

const followups = createResource({ url: 'crm.api.followup.get_pending_followups', auto: true })
const drafts = reactive({})
watch(
  () => followups.data,
  (list) => (list || []).forEach((f) => (drafts[f.task] ??= f.mensagem)),
  { immediate: true },
)

onMounted(() => {
  if (isManager()) {
    resource.fetch()
    loadCfg()
  }
})
function setDays(p) {
  days.value = p
  resource.fetch()
}

const fmt = new Intl.NumberFormat('pt-BR')
const n = (v) => fmt.format(Number(v) || 0)

function variation(cur, prev) {
  if (!prev) return { sub: '', tone: 'text-ink-gray-5' }
  const pct = Math.round(((cur - prev) / prev) * 100)
  if (pct === 0) return { sub: __('igual ao período anterior'), tone: 'text-ink-gray-5' }
  return { sub: `${pct > 0 ? '▲ +' : '▼ '}${pct}% ${__('vs. período anterior')}`, tone: pct > 0 ? 'text-ink-green-6' : 'text-ink-red-6' }
}

const kpis = computed(() => {
  const d = data.value
  if (!d) return []
  const a = d.atual
  const b = d.anterior
  return [
    { label: __('Abordagens'), value: n(a.abordados), ...variation(a.abordados, b.abordados) },
    { label: __('Respostas no Instagram'), value: n(a.respostas), ...variation(a.respostas, b.respostas) },
    {
      label: __('Taxa de resposta'),
      value: d.taxa_resposta === null ? '—' : `${d.taxa_resposta}%`,
      sub: __('respostas ÷ abordagens'),
      tone: 'text-ink-gray-5',
    },
    { label: __('Reuniões agendadas'), value: n(a.agendadas), ...variation(a.agendadas, b.agendadas) },
    { label: __('Propostas enviadas'), value: n(a.propostas), ...variation(a.propostas, b.propostas) },
    { label: __('Fechamentos'), value: n(a.fechamentos), ...variation(a.fechamentos, b.fechamentos) },
    { label: __('Conversas ativas'), value: n(d.conversas), sub: __('{0} leads novos', [d.leads_novos]), tone: 'text-ink-gray-5' },
    {
      label: __('Tempo até a 1ª resposta'),
      value: d.tempo_primeira_resposta_h === null ? '—' : waited(d.tempo_primeira_resposta_h),
      sub: __('média das conversas do período'),
      tone: 'text-ink-gray-5',
    },
    { label: __('Follow-ups criados'), value: n(d.followups_criados), sub: __('{0} em aberto', [d.followups_abertos]), tone: 'text-ink-gray-5' },
  ]
})

const funnel = computed(() => {
  const d = data.value
  if (!d) return []
  const a = d.atual
  const steps = [
    [__('Abordados'), a.abordados],
    [__('Responderam'), a.respostas],
    [__('Reuniões agendadas'), a.agendadas],
    [__('Reuniões realizadas'), a.realizadas],
    [__('Propostas enviadas'), a.propostas],
    [__('Fechamentos'), a.fechamentos],
  ]
  const max = Math.max(1, ...steps.map((s) => s[1]))
  return steps.map(([label, value], i) => ({
    label,
    value: n(value),
    width: Math.max(value ? 2 : 0, Math.round((value / max) * 100)),
    rate: i > 0 && steps[i - 1][1] ? Math.round((value / steps[i - 1][1]) * 100) : null,
  }))
})

function waited(hours) {
  if (hours === null || hours === undefined) return '—'
  if (hours < 1) return __('menos de 1h')
  if (hours < 48) return `${Math.round(hours)}h`
  return __('{0} dias', [Math.round(hours / 24)])
}
const tempClass = (t) =>
  ({ Quente: 'bg-surface-red-2 text-ink-red-6', Morno: 'bg-surface-amber-2 text-ink-amber-3', Frio: 'bg-surface-gray-2 text-ink-gray-6' })[t] || 'bg-surface-gray-2'

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text || '')
    toast.success(__('Mensagem copiada'))
  } catch (e) {
    toast.error(__('Não foi possível copiar'))
  }
}

async function sendFollowup(f) {
  const text = drafts[f.task] || f.mensagem
  await copy(text)
  let url = f.link
  if (url && url.includes('wa.me')) url = `${url.split('?')[0]}?text=${encodeURIComponent(text)}`
  if (url) window.open(url, '_blank')
  else toast.error(__('Sem @ ou telefone para abrir a conversa.'))
}

async function done(f) {
  await call('crm.api.followup.complete_followup', { task: f.task })
  toast.success(__('Follow-up concluído'))
  followups.reload()
  if (isManager()) resource.fetch()
}

function openLead(name) {
  router.push({ name: 'Lead', params: { leadId: name } })
}

// ---- nova abordagem
const showApproach = ref(false)
const registering = ref(false)
const approachError = ref('')
const tipos = createResource({ url: 'crm.api.followup.get_abordagens', auto: true })
const tipoOptions = computed(() => [{ label: __('Sem tipo definido'), value: '' }, ...(tipos.data || []).map((t) => ({ label: t, value: t }))])
const approach = reactive({ canal: 'Instagram', nome: '', usuario: '', telefone: '', abordagem: '' })

function openApproach() {
  approachError.value = ''
  showApproach.value = true
}

async function registerApproach() {
  registering.value = true
  approachError.value = ''
  try {
    const res = await call('crm.api.followup.register_approach', { ...approach })
    toast.success(res.status === 'criado' ? __('Abordagem registrada e lead criado') : __('Abordagem registrada no lead que já existia'))
    Object.assign(approach, { nome: '', usuario: '', telefone: '' })
    showApproach.value = false
    if (isManager()) resource.fetch()
  } catch (e) {
    approachError.value = e?.messages?.[0] || __('Não foi possível registrar.')
  } finally {
    registering.value = false
  }
}

// ---- configuração
const showConfig = ref(false)
const cfg = ref(null)
const novo = reactive({ nome: '', mensagem: '' })

async function loadCfg() {
  cfg.value = await call('crm.api.followup.get_settings')
}
async function saveCfg() {
  await call('crm.api.followup.save_settings', {
    ativado: cfg.value.ativado,
    primeiro_dias: cfg.value.primeiro_dias,
    segundo_dias: cfg.value.segundo_dias,
    maximo: cfg.value.maximo,
  })
  toast.success(__('Prazos salvos'))
}
async function saveAbordagem(a) {
  try {
    await call('crm.api.followup.save_abordagem', { nome: a.nome, mensagem: a.mensagem })
    toast.success(__('Mensagem salva'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao salvar'))
  }
}
async function removeAbordagem(a) {
  if (!window.confirm(__('Excluir a abordagem "{0}"?', [a.nome]))) return
  await call('crm.api.followup.delete_abordagem', { nome: a.nome })
  await loadCfg()
  tipos.reload()
}
async function addAbordagem() {
  try {
    await call('crm.api.followup.save_abordagem', { nome: novo.nome, mensagem: novo.mensagem })
    Object.assign(novo, { nome: '', mensagem: '' })
    await loadCfg()
    tipos.reload()
    toast.success(__('Abordagem adicionada'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao salvar'))
  }
}
</script>
