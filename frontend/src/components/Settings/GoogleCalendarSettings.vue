<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="flex h-5 gap-2 text-2xl-semibold leading-none">
        {{ __('Google Agenda') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Cruza o agendamento online do CRM com o Google Agenda do escritório: não oferece horários já ocupados, e cria o evento de verdade quando alguém marca uma reunião.',
          )
        }}
      </p>
    </div>

    <div v-if="status.loading && !status.data" class="px-2 text-p-sm text-ink-gray-5">
      {{ __('Carregando...') }}
    </div>

    <div v-else-if="!status.data?.habilitado" class="mx-2 rounded-lg border border-outline-gray-2 p-5 text-p-base text-ink-gray-7">
      {{ __('O Google Agenda ainda não foi habilitado neste servidor. Fale com o suporte.') }}
    </div>

    <!-- Não conectado -->
    <div v-else-if="!status.data?.conectado" class="mx-2 flex flex-col gap-4 rounded-lg border border-outline-gray-2 p-5">
      <p class="text-p-base text-ink-gray-7">
        {{
          __(
            'Ao conectar, o CRM só enxerga os horários ocupados e os eventos que ele mesmo cria - nunca lê o conteúdo dos seus outros compromissos.',
          )
        }}
      </p>
      <div>
        <Button variant="solid" :label="__('Conectar Google Agenda')" :loading="connecting" @click="connect" />
      </div>
    </div>

    <!-- Conectado -->
    <div v-else class="mx-2 flex flex-col gap-5">
      <div class="flex items-center justify-between rounded-lg border border-outline-gray-2 p-4">
        <div class="flex flex-col">
          <span class="text-p-base-medium text-ink-gray-8">{{ __('Conectado') }}</span>
          <span class="text-p-sm text-ink-gray-6">{{ status.data.email || '' }}</span>
        </div>
        <Button variant="subtle" theme="red" :label="__('Desconectar')" :loading="disconnecting" @click="disconnect" />
      </div>

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Não oferecer horários ocupados') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('O agendamento online some as horas que já estiverem ocupadas no seu Google Agenda, além das já marcadas pelo próprio CRM.') }}
          </div>
        </div>
        <FormControl type="checkbox" :model-value="!!status.data.bloquear_ocupado" @update:model-value="(v) => saveOption('bloquear_ocupado', v)" />
      </div>

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Criar evento ao confirmar reunião') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Toda reunião marcada pelo /agendar também vira um evento de verdade no seu Google Agenda.') }}
          </div>
        </div>
        <FormControl type="checkbox" :model-value="!!status.data.criar_eventos" @update:model-value="(v) => saveOption('criar_eventos', v)" />
      </div>
    </div>
  </div>
</template>
<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { ref } from 'vue'

const status = createResource({ url: 'crm.api.gcalendar.get_status', auto: true })
const connecting = ref(false)
const disconnecting = ref(false)

async function connect() {
  connecting.value = true
  try {
    const res = await call('crm.api.gcalendar.start_auth')
    window.location.href = res.url
  } catch (e) {
    connecting.value = false
    toast.error(e?.messages?.[0] || __('Não foi possível iniciar a conexão'))
  }
}

async function disconnect() {
  if (!window.confirm(__('Desconectar o Google Agenda?'))) return
  disconnecting.value = true
  try {
    await call('crm.api.gcalendar.disconnect')
    await status.reload()
    toast.success(__('Google Agenda desconectado'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao desconectar'))
  } finally {
    disconnecting.value = false
  }
}

async function saveOption(key, value) {
  await call('crm.api.gcalendar.save_options', { [key]: value ? 1 : 0 })
  await status.reload()
}
</script>
