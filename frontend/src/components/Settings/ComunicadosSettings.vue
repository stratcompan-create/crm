<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="text-2xl-semibold leading-none">{{ __('Comunicados aos clientes') }}</h2>
      <p class="text-p-base text-ink-gray-6">
        {{ __('Avise quem já é cliente quando sair uma lei ou decisão que afeta o caso dele. Só para a sua carteira e em tom informativo: comunicado não é anúncio nem captação.') }}
      </p>
    </div>
    <div class="mx-2 flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-4">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormControl v-model="f.area" type="select" :label="__('Clientes da área')" :options="areas" />
        <FormControl v-model="f.situacao" type="select" :label="__('Quais clientes')" :options="situacoes" />
      </div>
      <div v-if="previa.data" class="text-p-sm text-ink-gray-6">
        {{ __('{0} cliente(s) · {1} com e-mail', [previa.data.total, previa.data.com_email]) }}
        <span v-if="!previa.data.tem_conta_email" class="text-ink-amber-3"> · {{ __('sem e-mail de envio configurado: baixe a lista para avisar pelo WhatsApp') }}</span>
      </div>
      <FormControl v-model="f.titulo" type="text" :label="__('Assunto')" :placeholder="__('Ex.: Nova regra do INSS pode afetar o seu pedido')" />
      <FormControl v-model="f.mensagem" type="textarea" :rows="6" :label="__('Mensagem')"
        :placeholder="__('Olá, {nome}! Saiu uma mudança que pode afetar o seu caso... Vamos analisar e entramos em contato.')" />
      <p class="text-xs text-ink-gray-5">{{ __('Use {nome} para o primeiro nome do cliente. Não prometa resultado.') }}</p>
      <div class="flex flex-wrap gap-2">
        <Button variant="solid" iconLeft="lucide-send" :label="__('Enviar por e-mail')" :loading="enviando" :disabled="!previa.data?.tem_conta_email" @click="enviar" />
        <Button variant="subtle" iconLeft="lucide-download" :label="__('Baixar lista (nome, telefone, e-mail)')" @click="baixarLista" />
      </div>
    </div>
    <div v-if="historico.data?.length" class="mx-2 flex flex-col gap-1">
      <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Enviados') }}</div>
      <div v-for="(h, i) in historico.data" :key="i" class="text-p-sm text-ink-gray-6">
        {{ String(h.enviado_em).slice(0, 10).split('-').reverse().join('/') }} · {{ h.titulo }} · {{ __('{0} e-mails', [h.enviados]) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const f = reactive({ area: '', situacao: 'Ativos', titulo: '', mensagem: '' })
const situacoes = [
  { label: __('Clientes com caso ativo'), value: 'Ativos' },
  { label: __('Clientes com caso encerrado'), value: 'Encerrados' },
  { label: __('Todos os clientes'), value: 'Todos' },
]
const servicos = createResource({ url: 'crm.api.opcoes.opcoes', params: { doctype: 'CRM Honorario', campo: 'servico' }, auto: true })
const areas = ref([{ label: __('Todas as áreas'), value: '' }])
watch(() => servicos.data, (d) => (areas.value = [{ label: __('Todas as áreas'), value: '' }, ...(d || []).map((a) => ({ label: a, value: a }))]))
const previa = createResource({ url: 'crm.api.inteligencia.previa_comunicado', makeParams: () => ({ area: f.area, situacao: f.situacao }), auto: true })
watch(() => [f.area, f.situacao], () => previa.reload())
const historico = createResource({ url: 'crm.api.inteligencia.historico_comunicados', auto: true })

const enviando = ref(false)
async function enviar() {
  if (!window.confirm(__('Enviar para {0} cliente(s) com e-mail?', [previa.data?.com_email || 0]))) return
  enviando.value = true
  try {
    const r = await call('crm.api.inteligencia.enviar_comunicado', { ...f })
    toast.success(__('{0} e-mail(s) na fila de envio', [r.enviados]))
    historico.reload()
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível enviar.'))
  } finally {
    enviando.value = false
  }
}
async function baixarLista() {
  const r = await call('crm.api.inteligencia.lista_comunicado', { area: f.area, situacao: f.situacao })
  const bytes = Uint8Array.from(atob(r.arquivo), (c) => c.charCodeAt(0))
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
  a.download = r.nome
  a.click()
}
</script>
