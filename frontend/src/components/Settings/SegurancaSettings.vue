<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="text-2xl-semibold leading-none">{{ __('Segurança e dados') }}</h2>
      <p class="text-p-base text-ink-gray-6">{{ __('Proteção do acesso, cópia de todos os dados do escritório e pedidos de titulares (LGPD).') }}</p>
    </div>

    <section class="mx-2 flex flex-col gap-2 rounded-lg border border-outline-gray-2 p-4">
      <div class="text-p-base-medium text-ink-gray-9">{{ __('Login em duas etapas') }}</div>
      <p class="text-p-sm text-ink-gray-6">
        {{ __('Além da senha, cada pessoa digita um código do aplicativo autenticador do celular (Google Authenticator, Microsoft Authenticator...). No próximo login, cada usuário vê um QR code para configurar.') }}
      </p>
      <div class="flex items-center gap-3">
        <span class="text-p-sm" :class="estado.data?.dois_fatores ? 'text-ink-green-3' : 'text-ink-gray-5'">
          {{ estado.data?.dois_fatores ? __('Ligado') : __('Desligado') }}
        </span>
        <Button
          :variant="estado.data?.dois_fatores ? 'subtle' : 'solid'"
          :label="estado.data?.dois_fatores ? __('Desligar') : __('Ligar login em duas etapas')"
          :disabled="estado.data?.demonstracao"
          :loading="mudando2fa"
          @click="alternar2fa"
        />
      </div>
      <p v-if="estado.data?.demonstracao" class="text-xs text-ink-gray-5">{{ __('No site de demonstração fica desligado, porque o acesso é automático.') }}</p>
    </section>

    <section class="mx-2 flex flex-col gap-2 rounded-lg border border-outline-gray-2 p-4">
      <div class="text-p-base-medium text-ink-gray-9">{{ __('Todos os dados do escritório') }}</div>
      <p class="text-p-sm text-ink-gray-6">
        {{ __('Uma planilha com atendimentos, casos, honorários, despesas, recebimentos, partes, andamentos, tarefas, horas e contatos. Os dados são seus: baixe quando quiser.') }}
      </p>
      <div><Button variant="subtle" iconLeft="lucide-download" :label="__('Baixar planilha com tudo')" :loading="exportando" @click="exportarTudo" /></div>
    </section>

    <section class="mx-2 flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-4">
      <div class="text-p-base-medium text-ink-gray-9">{{ __('Pedidos de titulares (LGPD)') }}</div>
      <p class="text-p-sm text-ink-gray-6">
        {{ __('Quando alguém pedir para ver os próprios dados ou para apagá-los, busque a pessoa aqui. Ao anonimizar, os dados pessoais somem e o financeiro fica, porque o escritório é obrigado a guardar esses registros.') }}
      </p>
      <div class="flex gap-2">
        <FormControl v-model="busca" type="text" class="flex-1" :placeholder="__('Nome, e-mail ou telefone')" @keydown.enter="buscar" />
        <Button variant="subtle" :label="__('Buscar')" :loading="buscando" @click="buscar" />
      </div>
      <div v-for="t in titulares" :key="t.tipo + t.name" class="flex flex-wrap items-center justify-between gap-2 rounded border border-outline-gray-1 px-3 py-2 text-p-sm">
        <span><b>{{ t.rotulo }}</b> · {{ t.papel }}<span v-if="t.detalhe" class="text-ink-gray-5"> · {{ t.detalhe }}</span></span>
        <div class="flex gap-1">
          <Button size="sm" variant="subtle" :label="__('Exportar dados')" @click="exportarTitular(t)" />
          <Button size="sm" variant="ghost" theme="red" :label="__('Anonimizar')" @click="anonimizar(t)" />
        </div>
      </div>
      <p v-if="buscou && !titulares.length" class="text-p-sm text-ink-gray-5">{{ __('Ninguém encontrado.') }}</p>
    </section>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { ref } from 'vue'

const estado = createResource({ url: 'crm.api.seguranca.estado', auto: true })

function baixar(r, tipo = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
  const bytes = Uint8Array.from(atob(r.arquivo), (c) => c.charCodeAt(0))
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([bytes], { type: tipo }))
  a.download = r.nome
  a.click()
}
const erro = (e, p) => toast.error(e?.messages?.[0] || p)

const mudando2fa = ref(false)
async function alternar2fa() {
  const ligar = !estado.data?.dois_fatores
  if (ligar && !window.confirm(__('Ligar o login em duas etapas para toda a equipe? Cada pessoa vai precisar do aplicativo autenticador no celular.'))) return
  mudando2fa.value = true
  try {
    await call('crm.api.seguranca.definir_dois_fatores', { ativo: ligar ? 1 : 0 })
    toast.success(ligar ? __('Login em duas etapas ligado') : __('Login em duas etapas desligado'))
    estado.reload()
  } catch (e) {
    erro(e, __('Não foi possível alterar.'))
  } finally {
    mudando2fa.value = false
  }
}

const exportando = ref(false)
async function exportarTudo() {
  exportando.value = true
  try {
    baixar(await call('crm.api.seguranca.exportar_tudo'))
  } catch (e) {
    erro(e, __('Não foi possível exportar.'))
  } finally {
    exportando.value = false
  }
}

const busca = ref('')
const titulares = ref([])
const buscando = ref(false)
const buscou = ref(false)
async function buscar() {
  buscando.value = true
  try {
    titulares.value = await call('crm.api.seguranca.buscar_titular', { q: busca.value })
    buscou.value = true
  } finally {
    buscando.value = false
  }
}
async function exportarTitular(t) {
  try {
    baixar(await call('crm.api.seguranca.exportar_titular', { tipo: t.tipo, name: t.name }))
  } catch (e) {
    erro(e, __('Não foi possível exportar.'))
  }
}
async function anonimizar(t) {
  const conf = window.prompt(__('Isto apaga os dados pessoais de {0} e não pode ser desfeito. Digite ANONIMIZAR para confirmar.', [t.rotulo]))
  if (!conf) return
  try {
    await call('crm.api.seguranca.anonimizar_titular', { tipo: t.tipo, name: t.name, confirmacao: conf })
    toast.success(__('Dados anonimizados'))
    buscar()
  } catch (e) {
    erro(e, __('Não foi possível anonimizar.'))
  }
}
</script>
