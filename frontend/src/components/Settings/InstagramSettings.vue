<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8 text-ink-gray-8">
    <div class="flex justify-between px-2">
      <div class="flex flex-col gap-1">
        <h2 class="flex h-5 gap-2 text-2xl-semibold leading-none">
          {{ __('Instagram') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('Mensagens do Instagram viram leads no CRM automaticamente.') }}
        </p>
      </div>
      <Button
        :loading="settings.save.loading"
        :label="__('Salvar')"
        variant="solid"
        @click="save"
      />
    </div>

    <div v-if="settings.get.loading" class="px-2 text-p-sm text-ink-gray-5">
      {{ __('Carregando...') }}
    </div>

    <div v-else class="flex flex-1 flex-col gap-5 overflow-y-auto px-2">
      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Ativado') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Enquanto desativado, o CRM ignora mensagens do Instagram.') }}
          </div>
        </div>
        <FormControl type="checkbox" v-model="settings.doc.enabled" />
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex flex-col gap-1.5">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('Endereço do webhook') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Cole este endereço na configuração de Webhooks do app, no painel da Meta.') }}
        </div>
        <div class="flex gap-2">
          <FormControl type="text" class="flex-1" :model-value="webhookUrl" readonly />
          <Button :label="__('Copiar')" @click="copy(webhookUrl)" />
        </div>
      </div>

      <div class="flex flex-col gap-1.5">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('Token de verificação do webhook') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{
            __(
              'Use o mesmo valor aqui e na configuração de Webhooks da Meta — precisa ser idêntico nos dois lugares.',
            )
          }}
        </div>
        <div class="flex gap-2">
          <FormControl type="text" class="flex-1" v-model="settings.doc.verify_token" />
          <Button :label="__('Gerar um novo')" @click="generateVerifyToken" />
          <Button
            v-if="settings.doc.verify_token"
            :label="__('Copiar')"
            @click="copy(settings.doc.verify_token)"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex flex-col gap-1.5">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('Token de acesso') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Gerado em Meus Apps → Instagram → Configuração da API, na conta conectada.') }}
        </div>
        <FormControl type="password" v-model="settings.doc.access_token" :placeholder="__('Colar aqui')" />
      </div>

      <div class="flex flex-col gap-1.5">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('Chave secreta do app') }}</div>
        <div class="text-p-sm text-ink-gray-5">
          {{ __('Em Configurações do app → Básico, no painel da Meta.') }}
        </div>
        <FormControl type="password" v-model="settings.doc.app_secret" :placeholder="__('Colar aqui')" />
      </div>

      <div v-if="settings.doc.instagram_business_account_id" class="flex flex-col gap-1.5">
        <div class="text-p-base-medium text-ink-gray-7">{{ __('ID da conta conectada') }}</div>
        <div class="text-p-sm text-ink-gray-6">{{ settings.doc.instagram_business_account_id }}</div>
      </div>

      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <Button :label="__('Testar conexão')" :loading="testing" @click="test" />
          <span v-if="settings.doc.token_expires_on" class="text-p-sm text-ink-gray-5">
            {{ __('Token válido até {0}', [formatDate(settings.doc.token_expires_on)]) }}
          </span>
        </div>
        <div
          v-if="result"
          class="rounded-lg border p-3 text-p-sm"
          :class="
            result.ok
              ? 'border-outline-gray-2 bg-surface-green-2 text-ink-green-6'
              : 'border-outline-gray-2 bg-surface-red-2 text-ink-red-6'
          "
        >
          <template v-if="result.ok">
            {{ __('Conectado à conta @{0} do Instagram.', [result.username]) }}
          </template>
          <template v-else>{{ result.message }}</template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createDocumentResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

const settings = createDocumentResource({
  doctype: 'CRM Instagram Settings',
  name: 'CRM Instagram Settings',
  auto: true,
})

const webhookUrl = computed(() => `${window.location.origin}/api/method/crm.api.instagram.webhook`)

function generateVerifyToken() {
  settings.doc.verify_token = Array.from(crypto.getRandomValues(new Uint8Array(18)))
    .map((b) => b.toString(36))
    .join('')
    .slice(0, 24)
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text || '')
    toast.success(__('Copiado'))
  } catch (e) {
    toast.error(__('Não foi possível copiar'))
  }
}

function save() {
  settings.save.submit(null, {
    onSuccess: () => toast.success(__('Configurações salvas')),
  })
}

const testing = ref(false)
const result = ref(null)

async function test() {
  testing.value = true
  result.value = null
  try {
    result.value = await call('crm.api.instagram.test_connection')
  } catch (e) {
    result.value = { ok: false, message: e?.messages?.[0] || __('Não foi possível testar agora') }
  } finally {
    testing.value = false
  }
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('pt-BR')
}
</script>
