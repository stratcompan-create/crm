<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="text-2xl-semibold leading-none">{{ __('Automações') }}</h2>
      <p class="text-p-base text-ink-gray-6">
        {{ __('O CRM cuida sozinho do que se repete: cobrar, agendar, pedir avaliação e resumir a semana. Ajuste aqui como ele deve agir.') }}
      </p>
    </div>

    <div v-if="!cfg" class="px-2 text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <div v-else class="mx-2 flex flex-col gap-5 pb-8">
      <!-- Ao ganhar um negócio -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="text-base-semibold text-ink-gray-9">{{ __('Quando um negócio é ganho') }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ __('O CRM cria as cobranças no Financeiro, gera o contrato em PDF a partir do orçamento, cadastra a conta do cliente e abre as tarefas de início.') }}
        </p>
        <div class="mt-3 grid grid-cols-2 gap-3">
          <Field :label="__('Número de parcelas')"><FormControl v-model="cfg.parcelas_padrao" type="number" /></Field>
          <Field :label="__('Dias entre as parcelas')"><FormControl v-model="cfg.parcelas_intervalo" type="number" /></Field>
        </div>
        <label class="mt-3 flex items-center gap-2 text-p-sm text-ink-gray-7">
          <input v-model="cfg.onboarding_ativo" type="checkbox" :true-value="1" :false-value="0" />
          {{ __('Criar tarefas de início (boas-vindas, kickoff e acessos)') }}
        </label>
      </section>

      <!-- Cobrança -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">{{ __('Lembretes de cobrança') }}</div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Antes do vencimento, no dia e quando atrasar, o cliente recebe o lembrete por e-mail. A mensagem aparece na linha do tempo do negócio. Sem e-mail do cliente, o CRM cria uma tarefa para você cobrar.') }}
            </p>
          </div>
          <Toggle v-model="cfg.cobranca_ativa" />
        </div>
        <div class="mt-3 grid grid-cols-2 gap-3">
          <Field :label="__('Avisar quantos dias antes')"><FormControl v-model="cfg.cobranca_dias_antes" type="number" /></Field>
          <Field :label="__('Cobrar após o vencimento (dias)')"><FormControl v-model="cfg.cobranca_dias_atraso" type="text" placeholder="1,7,15" /></Field>
        </div>
        <Field class="mt-3" :label="__('Assunto')"><FormControl v-model="cfg.cobranca_assunto" type="text" /></Field>
        <Field class="mt-3" :label="__('Mensagem')"><FormControl v-model="cfg.cobranca_mensagem" type="textarea" :rows="4" /></Field>
        <div class="mt-1 text-xs text-ink-gray-5">{{ __('Use {nome}, {valor}, {descricao}, {situacao} e {vencimento}.') }}</div>
      </section>

      <!-- Pós-venda -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">{{ __('Pós-venda') }}</div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Depois que o negócio é ganho, o cliente recebe o pedido de avaliação e, mais tarde, o pedido de indicação. Cada um é enviado uma única vez.') }}
            </p>
          </div>
          <Toggle v-model="cfg.posvenda_ativo" />
        </div>
        <div class="mt-3 grid grid-cols-2 gap-3">
          <Field :label="__('Pedir avaliação após (dias)')"><FormControl v-model="cfg.posvenda_avaliacao_dias" type="number" /></Field>
          <Field :label="__('Pedir indicação após (dias)')"><FormControl v-model="cfg.posvenda_indicacao_dias" type="number" /></Field>
        </div>
        <Field class="mt-3" :label="__('Link para a avaliação (Google, por exemplo)')">
          <FormControl v-model="cfg.posvenda_avaliacao_link" type="text" placeholder="https://" />
        </Field>
        <Field class="mt-3" :label="__('Mensagem do pedido de avaliação')"><FormControl v-model="cfg.posvenda_avaliacao_mensagem" type="textarea" :rows="3" /></Field>
        <Field class="mt-3" :label="__('Mensagem do pedido de indicação')"><FormControl v-model="cfg.posvenda_indicacao_mensagem" type="textarea" :rows="3" /></Field>
        <div class="mt-1 text-xs text-ink-gray-5">{{ __('Use {nome} e, na avaliação, {link}.') }}</div>
      </section>

      <!-- Agendamento -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">{{ __('Agendamento de reunião') }}</div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Uma página pública onde a pessoa escolhe um horário livre. Ela vira lead, a reunião aparece nas tarefas e um lembrete sai 24 horas antes.') }}
            </p>
          </div>
          <Toggle v-model="cfg.agenda_ativa" />
        </div>
        <div class="mt-3 flex items-center gap-2 rounded-md bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-7">
          <span class="min-w-0 flex-1 truncate">{{ cfg.agenda_link_publico }}</span>
          <Button variant="subtle" :label="__('Copiar link')" @click="copy(cfg.agenda_link_publico)" />
        </div>
        <div class="mt-3 grid grid-cols-2 gap-3">
          <Field :label="__('Título da reunião')"><FormControl v-model="cfg.agenda_titulo" type="text" /></Field>
          <Field :label="__('Duração (minutos)')"><FormControl v-model="cfg.agenda_duracao" type="number" /></Field>
          <Field :label="__('Começa às')"><FormControl v-model="cfg.agenda_inicio" type="text" placeholder="09:00" /></Field>
          <Field :label="__('Termina às')"><FormControl v-model="cfg.agenda_fim" type="text" placeholder="18:00" /></Field>
          <Field :label="__('Dias da semana (1 = segunda, 7 = domingo)')"><FormControl v-model="cfg.agenda_dias" type="text" placeholder="1,2,3,4,5" /></Field>
          <Field :label="__('Antecedência mínima (horas)')"><FormControl v-model="cfg.agenda_antecedencia" type="number" /></Field>
          <Field :label="__('Mostrar quantos dias à frente')"><FormControl v-model="cfg.agenda_dias_a_frente" type="number" /></Field>
          <Field :label="__('Link da reunião (Meet, Zoom...)')"><FormControl v-model="cfg.agenda_link" type="text" placeholder="https://" /></Field>
        </div>
        <Field class="mt-3" :label="__('Aviso na página (opcional)')"><FormControl v-model="cfg.agenda_mensagem" type="textarea" :rows="2" /></Field>
      </section>

      <!-- Inteligência artificial -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="text-base-semibold text-ink-gray-9">{{ __('Inteligência artificial (Claude)') }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ __('Com a chave da Anthropic cadastrada, a Ficha da reunião se preenche sozinha a partir da transcrição e cada conversa do Instagram ganha três respostas escritas para ela. A chave é sua: o uso é cobrado direto na sua conta da Anthropic, e cada uso custa centavos.') }}
        </p>
        <div class="mt-3 flex items-center gap-2 text-p-sm">
          <span :class="ai.configurada ? 'text-ink-green-3' : 'text-ink-amber-3'">
            {{ ai.configurada ? __('Chave cadastrada') : __('Nenhuma chave cadastrada') }}
          </span>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <FormControl v-model="aiKey" class="flex-1" type="password" placeholder="sk-ant-..." autocomplete="off" />
          <Button variant="subtle" :label="__('Salvar chave')" :disabled="!aiKey" :loading="aiSaving" @click="saveKey(aiKey)" />
          <Button v-if="ai.configurada" variant="ghost" theme="red" :label="__('Remover')" @click="saveKey('')" />
        </div>
      </section>
      <!-- Resumo semanal -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">{{ __('Resumo semanal') }}</div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Toda segunda-feira, às 8h, o CRM monta o resumo da semana anterior (de segunda a domingo) em PDF, com prospecção, financeiro e pendências. Ele fica guardado aqui para baixar quando quiser.') }}
            </p>
          </div>
          <Toggle v-model="cfg.relatorio_ativo" />
        </div>
        <label class="mt-3 flex items-center gap-2 text-p-sm text-ink-gray-7">
          <input v-model="cfg.relatorio_email" type="checkbox" :true-value="1" :false-value="0" />
          {{ __('Enviar também por e-mail (com o PDF anexado), para ler pelo celular') }}
        </label>
        <Field class="mt-3" :label="__('Quem recebe por e-mail (um por linha; vazio = gestores)')">
          <FormControl v-model="cfg.relatorio_destinatarios" type="textarea" :rows="2" />
        </Field>
        <div class="mt-3 flex flex-col gap-1">
          <div v-for="r in reports" :key="r.name" class="flex items-center justify-between rounded-md border border-outline-gray-1 px-3 py-2 text-p-sm">
            <span class="text-ink-gray-8">{{ __('Semana de {0} a {1}', [fmt(r.inicio), fmt(r.fim)]) }}</span>
            <a v-if="r.arquivo" :href="r.arquivo" target="_blank" class="font-medium text-ink-gray-9 underline">{{ __('Baixar PDF') }}</a>
          </div>
          <div v-if="!reports.length" class="text-p-sm text-ink-gray-5">{{ __('Nenhum resumo gerado ainda. O primeiro sai na próxima segunda-feira às 8h.') }}</div>
        </div>
        <div class="mt-2"><Button variant="subtle" :label="__('Gerar o resumo da última semana agora')" :loading="sending" @click="sendNow" /></div>
      </section>
      <div class="sticky bottom-0 flex justify-end bg-surface-white py-2">
        <Button variant="solid" :label="__('Salvar automações')" :loading="saving" @click="save" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import { h, defineComponent, onMounted, ref } from 'vue'

const Field = defineComponent({
  props: { label: String },
  setup(props, { slots }) {
    return () =>
      h('div', { class: 'flex flex-col gap-1' }, [
        h('span', { class: 'text-p-sm text-ink-gray-6' }, props.label),
        slots.default?.(),
      ])
  },
})

const Toggle = defineComponent({
  props: { modelValue: [Number, Boolean] },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h('label', { class: 'flex shrink-0 items-center gap-2 text-p-sm text-ink-gray-7' }, [
        h('input', {
          type: 'checkbox',
          checked: !!Number(props.modelValue),
          onChange: (e) => emit('update:modelValue', e.target.checked ? 1 : 0),
        }),
        Number(props.modelValue) ? __('Ligado') : __('Desligado'),
      ])
  },
})

const cfg = ref(null)
const ai = ref({ configurada: false })
const aiKey = ref('')
const aiSaving = ref(false)
const reports = ref([])
const fmt = (v) => (v ? v.split('-').reverse().slice(0, 2).join('/') : '')
const saving = ref(false)
const sending = ref(false)

onMounted(async () => {
  cfg.value = await call('crm.api.automacoes.get_settings')
  reports.value = await call('crm.api.automacoes.list_weekly_reports')
  ai.value = await call('crm.api.ficha.get_ai_status')
})

async function save() {
  saving.value = true
  try {
    const { agenda_link_publico, ...values } = cfg.value
    await call('crm.api.automacoes.save_settings', { values })
    toast.success(__('Automações salvas'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível salvar.'))
  } finally {
    saving.value = false
  }
}

async function sendNow() {
  sending.value = true
  try {
    await call('crm.api.automacoes.generate_weekly_report_now')
    reports.value = await call('crm.api.automacoes.list_weekly_reports')
    toast.success(__('Resumo gerado. Já dá para baixar na lista.'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível gerar o resumo.'))
  } finally {
    sending.value = false
  }
}
async function saveKey(key) {
  aiSaving.value = true
  try {
    ai.value = await call('crm.api.ficha.save_ai_key', { chave: key })
    aiKey.value = ''
    toast.success(key ? __('Chave salva') : __('Chave removida'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível salvar a chave.'))
  } finally {
    aiSaving.value = false
  }
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(__('Link copiado'))
  } catch (e) {
    toast.error(__('Não foi possível copiar'))
  }
}
</script>
