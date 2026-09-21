<template>
  <div class="flex h-full flex-col overflow-y-auto pb-10 pt-4">
    <div v-if="!docs.data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <div v-else class="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <!-- Cabeçalho -->
      <div>
        <div class="text-lg-semibold text-ink-gray-9">{{ __('Documentos do cliente') }}</div>
        <p class="mt-0.5 text-p-sm text-ink-gray-6">
          {{ __('Tudo que chega para este cliente fica guardado em uma pasta só:') }}
          <span class="font-medium text-ink-gray-8">{{ folderLabel }}</span>
          {{ __('(veja também em Arquivos, na Visão Geral).') }}
        </p>
      </div>

      <!-- Pedir documentos -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="text-base-semibold text-ink-gray-9">{{ __('Pedir documentos ao cliente') }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ __('Marque o que você precisa. O cliente recebe um link, envia as fotos ou PDFs pelo celular e tudo cai direto na pasta dele.') }}
        </p>
        <div class="mt-3 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          <label v-for="i in options" :key="i" class="flex items-center gap-2 text-p-sm text-ink-gray-8">
            <input v-model="chosen" type="checkbox" :value="i" />
            {{ i }}
          </label>
        </div>
        <div class="mt-3 flex items-center gap-2">
          <FormControl v-model="extra" class="flex-1" type="text" :placeholder="__('Outro documento (ex.: certidão de casamento)')" @keydown.enter.prevent="addExtra" />
          <Button variant="subtle" :label="__('Adicionar')" :disabled="!extra.trim()" @click="addExtra" />
        </div>
        <FormControl v-model="message" class="mt-3" type="textarea" :rows="2" :placeholder="__('Mensagem para o cliente (opcional)')" />
        <div class="mt-3 flex items-center justify-between gap-3">
          <span class="text-xs text-ink-gray-5">{{ __('O link vale por 14 dias.') }}</span>
          <Button variant="solid" :label="__('Gerar link')" :loading="creating" :disabled="!chosen.length" @click="createLink" />
        </div>
        <ErrorMessage v-if="error" class="mt-2" :message="error" />
      </section>

      <!-- Pedidos -->
      <section v-if="docs.data.pedidos.length" class="flex flex-col gap-3">
        <div class="text-base-semibold text-ink-gray-9">{{ __('Pedidos enviados') }}</div>
        <div v-for="p in docs.data.pedidos" :key="p.name" class="rounded-lg border border-outline-gray-2 p-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-p-sm text-ink-gray-6">
              {{ __('Criado em {0}', [dateBr(p.creation)]) }} ·
              <span :class="p.ativo ? 'text-ink-green-3' : 'text-ink-gray-5'">{{ p.ativo ? __('Ativo até {0}', [dateBr(p.expira_em)]) : __('Encerrado') }}</span>
            </span>
          </div>
          <ul class="mt-2 flex flex-col gap-1">
            <li v-for="i in p.itens" :key="i" class="flex items-center justify-between text-p-sm">
              <span class="text-ink-gray-8">{{ i }}</span>
              <span :class="received(p, i) ? 'font-medium text-ink-green-3' : 'text-ink-amber-3'">
                {{ received(p, i) ? __('Recebido ({0})', [received(p, i)]) : __('Aguardando') }}
              </span>
            </li>
          </ul>
          <div v-if="p.ativo" class="mt-3 flex flex-wrap gap-2">
            <Button variant="subtle" :label="__('Copiar link')" @click="copy(p.link)" />
            <Button v-if="docs.data.tem_email" variant="subtle" :label="__('Enviar por e-mail')" @click="sendEmail(p)" />
            <a v-if="docs.data.telefone" :href="whatsLink(p)" target="_blank" rel="noopener">
              <Button variant="subtle" :label="__('Abrir no WhatsApp')" />
            </a>
            <Button variant="ghost" theme="red" :label="__('Encerrar link')" @click="closeLink(p)" />
          </div>
        </div>
      </section>

      <!-- Arquivos -->
      <section>
        <div class="text-base-semibold text-ink-gray-9">{{ __('Arquivos do cliente') }}</div>
        <div v-if="!docs.data.arquivos.length" class="mt-2 rounded-lg bg-surface-gray-2 px-4 py-5 text-p-sm text-ink-gray-6">
          {{ __('Nenhum arquivo ainda. O que o cliente enviar pelo link, o que você anexar ao negócio e os anexos dos e-mails aparecem aqui.') }}
        </div>
        <div v-else class="mt-2 flex flex-col gap-1.5">
          <a
            v-for="f in docs.data.arquivos"
            :key="f.name"
            :href="f.file_url"
            target="_blank"
            class="flex items-center justify-between gap-3 rounded-lg border border-outline-gray-2 px-3 py-2 hover:bg-surface-gray-1"
          >
            <span class="flex min-w-0 items-center gap-2">
              <span class="lucide-file size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
              <span class="truncate text-p-sm text-ink-gray-8">{{ f.file_name }}</span>
            </span>
            <span class="shrink-0 text-xs text-ink-gray-5">{{ dateBr(f.creation) }} · {{ size(f.file_size) }}</span>
          </a>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { Button, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({ doctype: String, docname: String })

const chosen = ref([])
const extra = ref('')
const message = ref('')
const creating = ref(false)
const error = ref('')
const custom = ref([])

const docs = createResource({
  url: 'crm.api.clientes.get_documents',
  makeParams: () => ({ deal: props.docname }),
  auto: true,
  onSuccess(d) {
    if (!chosen.value.length) chosen.value = [...d.sugestao]
  },
})
watch(() => props.docname, () => docs.reload())

const options = computed(() => [...(docs.data?.sugestao || []), ...custom.value])
const folderLabel = computed(() => (docs.data?.pasta || '').replace(/^Home\//, '').replace(/\//g, ' › '))

function addExtra() {
  const v = extra.value.trim()
  if (!v) return
  if (!options.value.includes(v)) custom.value.push(v)
  if (!chosen.value.includes(v)) chosen.value.push(v)
  extra.value = ''
}

async function createLink() {
  creating.value = true
  error.value = ''
  try {
    const r = await call('crm.api.clientes.create_request', {
      deal: props.docname,
      itens: chosen.value,
      mensagem: message.value,
    })
    await copy(r.link, true)
    message.value = ''
    docs.reload()
  } catch (e) {
    error.value = e?.messages?.[0] || __('Não foi possível criar o link.')
  } finally {
    creating.value = false
  }
}

async function copy(text, created) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(created ? __('Link criado e copiado. É só enviar ao cliente.') : __('Link copiado'))
  } catch (e) {
    toast.error(__('Não foi possível copiar'))
  }
}

async function sendEmail(p) {
  try {
    await call('crm.api.clientes.send_request_email', { pedido: p.name })
    toast.success(__('E-mail enviado ao cliente'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível enviar o e-mail.'))
  }
}

async function closeLink(p) {
  if (!window.confirm(__('Encerrar este link? O cliente não poderá mais enviar por ele.'))) return
  await call('crm.api.clientes.close_request', { pedido: p.name })
  docs.reload()
}

function whatsLink(p) {
  const nome = docs.data.nome ? `Olá, ${docs.data.nome}! ` : 'Olá! '
  const text = `${nome}Para darmos andamento, envie seus documentos por este link seguro: ${p.link}`
  let phone = docs.data.telefone
  if (phone.length <= 11) phone = '55' + phone
  return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`
}

const received = (p, item) => (p.recebidos || []).filter((r) => r.item === item).length
const dateBr = (v) => (v ? String(v).slice(0, 10).split('-').reverse().join('/') : '')
const size = (b) => (!b ? '' : b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB')
</script>
