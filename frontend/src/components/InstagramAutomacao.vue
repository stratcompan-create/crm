<template>
  <div class="flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
    <div v-if="!cfg" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <div v-else class="mx-auto flex max-w-3xl flex-col gap-5">
      <!-- Boas-vindas -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">{{ __('Boas-vindas no primeiro contato') }}</div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Quando alguém escreve para você pela primeira vez, recebe esta mensagem na hora. Só é enviada uma vez por pessoa, e não vai para quem você mesmo abordou.') }}
            </p>
          </div>
          <label class="flex shrink-0 items-center gap-2 text-p-sm text-ink-gray-7">
            <input v-model="cfg.boas_vindas_ativa" type="checkbox" :true-value="1" :false-value="0" @change="saveWelcome" />
            {{ cfg.boas_vindas_ativa ? __('Ligada') : __('Desligada') }}
          </label>
        </div>
        <FormControl v-model="cfg.boas_vindas_mensagem" type="textarea" :rows="4" class="mt-3" />
        <div class="mt-1 text-xs text-ink-gray-5">{{ __('Use {nome} para o CRM colocar o nome da pessoa.') }}</div>
        <div class="mt-2"><Button variant="solid" :label="__('Salvar mensagem')" @click="saveWelcome(true)" /></div>
      </section>

      <!-- Palavra-chave -->
      <section class="rounded-lg border border-outline-gray-2 p-4">
        <div class="text-base-semibold text-ink-gray-9">{{ __('Palavra-chave nos comentários') }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ __('Você grava o vídeo e chama para a ação no final: "comente ESCRITÓRIO". Quem comentar a palavra recebe a mensagem no direct na hora e já entra como lead no CRM, com o comentário registrado na conversa. Acentos e letras maiúsculas não importam.') }}
        </p>

        <div v-if="!cfg.gatilhos.length" class="mt-3 rounded-md bg-surface-gray-2 px-3 py-3 text-p-sm text-ink-gray-6">
          {{ __('Nenhuma palavra cadastrada ainda.') }}
        </div>
        <div v-for="g in cfg.gatilhos" :key="g.palavra" class="mt-3 rounded-lg border border-outline-gray-1 p-3">
          <div class="mb-2 flex items-center justify-between">
            <span class="rounded bg-surface-gray-2 px-2 py-0.5 text-p-sm font-medium text-ink-gray-9">{{ g.palavra }}</span>
            <label class="flex items-center gap-2 text-p-sm text-ink-gray-6">
              <input v-model="g.ativa" type="checkbox" :true-value="1" :false-value="0" @change="saveGatilho(g)" />
              {{ g.ativa ? __('Ativa') : __('Pausada') }}
            </label>
          </div>
          <FormControl v-model="g.mensagem" type="textarea" :rows="3" />
          <div class="mt-2 flex gap-2">
            <Button variant="subtle" :label="__('Salvar')" @click="saveGatilho(g, true)" />
            <Button variant="ghost" theme="red" :label="__('Excluir')" @click="removeGatilho(g)" />
          </div>
        </div>

        <div class="mt-3 rounded-lg border border-dashed border-outline-gray-2 p-3">
          <div class="mb-2 text-p-sm font-medium text-ink-gray-8">{{ __('Nova palavra-chave') }}</div>
          <FormControl v-model="novo.palavra" type="text" :placeholder="__('Ex.: escritório')" class="mb-2" />
          <FormControl v-model="novo.mensagem" type="textarea" :rows="3" :placeholder="cfg.mensagem_exemplo" />
          <div class="mt-2"><Button variant="subtle" :label="__('Adicionar palavra')" @click="addGatilho" /></div>
        </div>
      </section>

      <section class="rounded-lg bg-surface-gray-2 p-4 text-p-sm text-ink-gray-6">
        <div class="mb-1 font-medium text-ink-gray-8">{{ __('Bom saber') }}</div>
        <ul class="list-disc space-y-1 pl-5">
          <li>{{ __('O Instagram só permite responder a quem escreveu ou comentou. Não dá para mandar mensagem para quem apenas começou a seguir o perfil.') }}</li>
          <li>{{ __('Cada comentário gera no máximo uma mensagem, e a mesma pessoa não recebe a mesma palavra duas vezes em 24 horas.') }}</li>
          <li>{{ __('Tudo o que é enviado fica registrado na conversa do lead, na aba Mensagens.') }}</li>
          <li>{{ __('Resposta automática a stories ainda não está disponível.') }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const cfg = ref(null)
const novo = reactive({ palavra: '', mensagem: '' })

async function load() {
  cfg.value = await call('crm.api.instagram_automacao.get_automation_settings')
}
onMounted(load)

function errorText(e) {
  return e?.messages?.[0] || __('Não foi possível salvar.')
}

async function saveWelcome(showToast) {
  try {
    await call('crm.api.instagram_automacao.save_welcome', {
      ativa: cfg.value.boas_vindas_ativa,
      mensagem: cfg.value.boas_vindas_mensagem,
    })
    if (showToast === true) toast.success(__('Boas-vindas salvas'))
    else toast.success(cfg.value.boas_vindas_ativa ? __('Boas-vindas ligadas') : __('Boas-vindas desligadas'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

async function saveGatilho(g, showToast) {
  try {
    await call('crm.api.instagram_automacao.save_gatilho', { palavra: g.palavra, mensagem: g.mensagem, ativa: g.ativa })
    if (showToast === true) toast.success(__('Palavra salva'))
  } catch (e) {
    toast.error(errorText(e))
  }
}

async function removeGatilho(g) {
  if (!window.confirm(__('Excluir a palavra "{0}"?', [g.palavra]))) return
  await call('crm.api.instagram_automacao.delete_gatilho', { palavra: g.palavra })
  await load()
}

async function addGatilho() {
  try {
    await call('crm.api.instagram_automacao.save_gatilho', { palavra: novo.palavra, mensagem: novo.mensagem, ativa: 1 })
    Object.assign(novo, { palavra: '', mensagem: '' })
    await load()
    toast.success(__('Palavra adicionada'))
  } catch (e) {
    toast.error(errorText(e))
  }
}
</script>
