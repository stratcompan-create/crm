<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="flex h-5 gap-2 text-2xl-semibold leading-none">
        {{ __('Google Drive') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Guarde propostas, orçamentos, contratos e relatórios do CRM no Google Drive do escritório.',
          )
        }}
      </p>
    </div>

    <div v-if="status.loading && !status.data" class="px-2 text-p-sm text-ink-gray-5">
      {{ __('Carregando...') }}
    </div>

    <div v-else-if="!status.data?.habilitado" class="mx-2 rounded-lg border border-outline-gray-2 p-5 text-p-base text-ink-gray-7">
      {{ __('O Google Drive ainda não foi habilitado neste servidor. Fale com o suporte.') }}
    </div>

    <!-- Não conectado -->
    <div v-else-if="!status.data?.conectado" class="mx-2 flex flex-col gap-4 rounded-lg border border-outline-gray-2 p-5">
      <p class="text-p-base text-ink-gray-7">
        {{
          __(
            'Ao conectar, o CRM cria uma pasta no seu Drive e salva nela os documentos. Ele só enxerga o que ele mesmo criar: os outros arquivos do seu Drive continuam privados.',
          )
        }}
      </p>
      <div>
        <Button variant="solid" :label="__('Conectar Google Drive')" :loading="connecting" @click="connect" />
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
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Nome da pasta no Drive') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('As subpastas (Propostas, Financeiro, Prospecção) são criadas dentro dela.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <FormControl v-model="pasta" type="text" size="md" :placeholder="__('Ex.: Meu Escritório CRM')" />
          <Button variant="subtle" :label="__('Salvar')" :disabled="pasta === (status.data.pasta || '')" @click="savePasta" />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <!-- Cópia de segurança -->
      <div class="flex flex-col gap-3">
        <div class="flex items-start justify-between gap-6">
          <div class="flex flex-col">
            <div class="text-p-base-medium text-ink-gray-7">{{ __('Cópia de segurança no Google Drive') }}</div>
            <div class="text-p-sm text-ink-gray-5">
              {{ __('Toda noite o CRM guarda uma cópia completa (dados, documentos e configurações) na pasta "Backups do CRM" do seu Drive. Se algo acontecer com o servidor, é daí que tudo é recuperado. As últimas {0} cópias ficam guardadas.', [backup.data?.guarda || 10]) }}
            </div>
          </div>
          <label class="flex shrink-0 items-center gap-2 text-p-sm text-ink-gray-7">
            <input type="checkbox" :checked="backup.data?.ativo" @change="toggleBackup($event.target.checked)" />
            {{ backup.data?.ativo ? __('Ligada') : __('Desligada') }}
          </label>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface-gray-2 px-3 py-2.5">
          <span class="text-p-sm" :class="backup.data?.status === 'erro' ? 'text-ink-red-6' : 'text-ink-gray-7'">
            <template v-if="backup.data?.status === 'erro'">{{ __('A última cópia falhou. Tente de novo em alguns minutos.') }}</template>
            <template v-else-if="running">{{ __('Fazendo a cópia agora... isso pode levar alguns minutos.') }}</template>
            <template v-else-if="backup.data?.ultimo_ok">
              {{ __('Última cópia: {0} ({1} MB)', [formatDate(backup.data.ultimo_ok), backup.data.tamanho_mb]) }}
            </template>
            <template v-else>{{ __('A primeira cópia acontece esta noite.') }}</template>
          </span>
          <Button variant="subtle" :label="__('Fazer cópia agora')" :loading="running" @click="runBackup" />
        </div>
        <p class="text-xs text-ink-gray-5">
          {{ __('Os arquivos ficam na sua conta do Google, protegidos por ela. Use verificação em duas etapas na conta para garantir a segurança.') }}
        </p>
      </div>


      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Copiar automaticamente') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{
              __(
                'Todo arquivo gerado no CRM (propostas enviadas, relatório da semana, metas em PDF) também é guardado no Drive.',
              )
            }}
          </div>
        </div>
        <FormControl type="checkbox" :model-value="!!status.data.envio_automatico" @update:model-value="toggleAuto" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { onBeforeUnmount, ref, watch } from 'vue'

const status = createResource({ url: 'crm.api.gdrive.get_status', auto: true })
const pasta = ref('')
const connecting = ref(false)
const disconnecting = ref(false)

watch(
  () => status.data?.pasta,
  (v) => (pasta.value = v || ''),
  { immediate: true },
)

async function connect() {
  connecting.value = true
  try {
    const res = await call('crm.api.gdrive.start_auth')
    window.location.href = res.url
  } catch (e) {
    connecting.value = false
    toast.error(e?.messages?.[0] || __('Não foi possível iniciar a conexão'))
  }
}

async function disconnect() {
  if (!window.confirm(__('Desconectar o Google Drive? Os arquivos já salvos continuam no seu Drive.'))) return
  disconnecting.value = true
  try {
    await call('crm.api.gdrive.disconnect')
    await status.reload()
    toast.success(__('Google Drive desconectado'))
  } finally {
    disconnecting.value = false
  }
}

async function savePasta() {
  try {
    await call('crm.api.gdrive.save_options', { pasta_nome: pasta.value })
    await status.reload()
    toast.success(__('Pasta atualizada'))
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Erro ao salvar'))
  }
}

async function toggleAuto(value) {
  await call('crm.api.gdrive.save_options', { envio_automatico: value ? 1 : 0 })
  await status.reload()
}

const backup = createResource({ url: 'crm.api.gdrive.get_backup_status', auto: true, onError() {} })
const running = ref(false)
let poll = null
function formatDate(v) {
  const [d, t] = String(v).split(' ')
  return d.split('-').reverse().join('/') + (t ? ' às ' + t.slice(0, 5) : '')
}
async function toggleBackup(on) {
  await call('crm.api.gdrive.set_backup_enabled', { ativo: on ? 1 : 0 })
  backup.reload()
}
async function runBackup() {
  running.value = true
  try {
    await call('crm.api.gdrive.run_backup_now')
    toast.success(__('Cópia iniciada. Você pode continuar usando o CRM.'))
    const before = backup.data?.ultimo_ok
    poll = setInterval(async () => {
      await backup.reload()
      if (backup.data?.status === 'erro' || (backup.data?.ultimo_ok && backup.data.ultimo_ok !== before)) {
        running.value = false
        clearInterval(poll)
      }
    }, 8000)
  } catch (e) {
    running.value = false
    toast.error(e?.messages?.[0] || __('Não foi possível iniciar a cópia.'))
  }
}
onBeforeUnmount(() => clearInterval(poll))
</script>