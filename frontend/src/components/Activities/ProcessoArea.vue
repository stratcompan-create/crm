<template>
  <div class="flex flex-col gap-6 py-4 text-ink-gray-8">
    <div v-if="dados.loading && !dados.data" class="py-10 text-center text-p-sm text-ink-gray-5">{{ __('Carregando...') }}</div>
    <template v-else-if="dados.data">
      <div v-if="dados.data.encerrado" class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-gray-2 px-4 py-3 text-p-sm">
        <span>
          {{ __('Caso encerrado em {0}', [dataBr(dados.data.encerrado_em)]) }} · {{ __(dados.data.motivo_encerramento) }}
          <span v-if="dados.data.documentos_devolvidos"> · {{ __('documentos devolvidos') }}</span>
        </span>
        <div class="flex gap-2">
          <Button size="sm" variant="subtle" iconLeft="lucide-file-text" :label="__('Termo de encerramento')" @click="termo" />
          <Button size="sm" variant="ghost" :label="__('Reabrir')" @click="reabrir" />
        </div>
      </div>

      <!-- portal do cliente -->
      <section class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-outline-gray-2 px-4 py-3">
        <div>
          <div class="text-p-base-medium text-ink-gray-9">{{ __('Portal do cliente') }}</div>
          <div class="text-xs text-ink-gray-5">
            {{ __('Um link só do cliente: ele vê os andamentos, os documentos que faltam e os pagamentos em aberto, sem ligar para o escritório.') }}
          </div>
        </div>
        <div class="flex gap-2">
          <Button variant="subtle" iconLeft="lucide-link" :label="__('Copiar link')" @click="copiarPortal(false)" />
          <Button v-if="dados.data.tem_portal" variant="ghost" :label="__('Trocar link')" @click="copiarPortal(true)" />
        </div>
      </section>

      <div v-if="dados.data.pesquisa" class="rounded-lg bg-surface-gray-2 px-4 py-2 text-p-sm">
        <template v-if="dados.data.pesquisa.respondida_em">
          {{ __('Avaliação do cliente: {0}/10', [dados.data.pesquisa.nota]) }}<span v-if="dados.data.pesquisa.indicaria"> · {{ __('indicaria o escritório') }}</span>
          <div v-if="dados.data.pesquisa.comentario" class="text-ink-gray-6">“{{ dados.data.pesquisa.comentario }}”</div>
        </template>
        <template v-else>{{ __('Pesquisa de satisfação enviada, aguardando resposta.') }}</template>
      </div>

      <!-- número -->
      <section class="flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Processo') }}</div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-5">
          <FormControl v-model="proc.numero" class="sm:col-span-2" type="text" :placeholder="__('Nº CNJ (0000000-00.0000.0.00.0000)')" />
          <FormControl v-model="proc.tribunal" class="sm:col-span-2" type="text" :placeholder="__('Tribunal / vara')" />
          <Button variant="subtle" :label="__('Salvar')" :loading="salvandoProc" @click="salvarProcesso" />
        </div>
        <div v-if="dados.data.aviso_numero" class="text-xs text-ink-amber-6">{{ dados.data.aviso_numero }}</div>
        <div class="text-xs text-ink-gray-5">{{ __('Prazos processuais continuam no seu software jurídico. Aqui fica só o que ajuda a atender o cliente.') }}</div>
      </section>

      <!-- partes -->
      <section class="flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Partes e envolvidos') }}</div>
        <div v-for="p in dados.data.partes" :key="p.name" class="rounded border border-outline-gray-2 px-3 py-2">
          <div class="flex items-center justify-between gap-2 text-p-sm">
            <span><b>{{ p.nome }}</b> · {{ __(p.tipo) }}<span v-if="p.documento"> · {{ p.documento }}</span></span>
            <Button size="sm" variant="ghost" theme="red" icon="trash-2" @click="removerParte(p)" />
          </div>
          <div v-for="(c, i) in p.conflitos" :key="i" class="mt-1 rounded bg-surface-red-2 px-2 py-1 text-xs text-ink-red-4">
            ⚠ {{ __('Possível conflito de interesses: {0} {1}', [p.nome, c.motivo]) }}
          </div>
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-12">
          <FormControl v-model="parte.nome" class="sm:col-span-4" type="text" :placeholder="__('Nome')" />
          <FormControl v-model="parte.tipo" class="sm:col-span-3" type="select" :options="(dados.data.tipos_parte || []).map((t) => ({ label: __(t), value: t }))" />
          <FormControl v-model="parte.documento" class="sm:col-span-3" type="text" :placeholder="__('CPF ou CNPJ (opcional)')" />
          <Button class="sm:col-span-2" variant="subtle" iconLeft="lucide-plus" :label="__('Adicionar')" :loading="salvandoParte" @click="adicionarParte" />
        </div>
      </section>

      <!-- andamentos -->
      <section class="flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Andamentos para o cliente') }}</div>
        <div class="text-xs text-ink-gray-5">{{ __('Escreva em linguagem simples. O último andamento marcado para o cliente é o que ele vê quando pergunta como está o processo.') }}</div>
        <div class="flex flex-col gap-2">
          <textarea
            v-model="andamento.texto"
            rows="2"
            class="w-full rounded border border-outline-gray-2 bg-transparent px-3 py-2 text-p-sm"
            :placeholder="__('Ex.: A audiência foi marcada para 20/11. Vamos te avisar a hora e o local.')"
          />
          <div class="flex items-center justify-between gap-2">
            <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
              <input v-model="andamento.visivel" type="checkbox" /> {{ __('Mostrar ao cliente') }}
            </label>
            <Button variant="subtle" iconLeft="lucide-plus" :label="__('Registrar andamento')" :loading="salvandoAnd" @click="adicionarAndamento" />
          </div>
        </div>
        <div v-for="a in dados.data.andamentos" :key="a.name" class="flex items-start justify-between gap-2 border-t border-outline-gray-1 pt-2 text-p-sm">
          <div>
            <span class="text-ink-gray-5">{{ dataBr(a.data) }}</span>
            <span v-if="!a.visivel_cliente" class="ml-1 rounded bg-surface-gray-2 px-1.5 text-xs text-ink-gray-5">{{ __('interno') }}</span>
            <div>{{ a.texto }}</div>
          </div>
          <Button size="sm" variant="ghost" theme="red" icon="trash-2" @click="removerAndamento(a)" />
        </div>
      </section>

      <!-- encerramento -->
      <section v-if="!dados.data.encerrado" class="flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Encerrar o caso') }}</div>
        <div v-if="dados.data.pendencias.length" class="rounded bg-surface-amber-2 px-3 py-2 text-xs text-ink-amber-6">
          {{ __('Antes de encerrar:') }} {{ dados.data.pendencias.join(' · ') }}
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <FormControl v-model="enc.motivo" type="select" :options="[{ label: __('Como terminou?'), value: '' }, ...dados.data.motivos.map((m) => ({ label: __(m), value: m }))]" />
          <label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
            <input v-model="enc.devolvidos" type="checkbox" /> {{ __('Documentos originais devolvidos') }}
          </label>
          <Button variant="subtle" :label="__('Encerrar caso')" :loading="encerrando" @click="encerrar(false)" />
        </div>
        <FormControl v-model="enc.obs" type="textarea" :rows="2" :placeholder="__('Observações do encerramento (opcional)')" />
      </section>

      <!-- registro de acesso (LGPD), só para gestor -->
      <section v-if="acessos.data?.length" class="flex flex-col gap-1">
        <div class="text-p-sm font-medium text-ink-gray-7">{{ __('Quem abriu este caso (últimos 90 dias)') }}</div>
        <div class="text-xs text-ink-gray-6">
          <span v-for="a in acessos.data" :key="a.usuario" class="mr-3">{{ a.nome }} · {{ __('{0}x', [a.vezes]) }} · {{ __('último em {0}', [dataBr(a.ultimo)]) }}</span>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const props = defineProps({ doctype: String, docname: String })
const dataBr = (d) => (d ? String(d).slice(0, 10).split('-').reverse().join('/') : '')

const proc = reactive({ numero: '', tribunal: '' })
const dados = createResource({
  url: 'crm.api.processo.dados',
  makeParams: () => ({ deal: props.docname }),
  auto: true,
  onSuccess: (d) => Object.assign(proc, { numero: d.numero_processo, tribunal: d.tribunal }),
})
watch(() => props.docname, () => {
  dados.reload()
  acessos.reload()
})

// quem não é gestor recebe erro de permissão: aí o bloco simplesmente não aparece
const acessos = createResource({
  url: 'crm.api.seguranca.quem_acessou',
  makeParams: () => ({ deal: props.docname }),
  auto: true,
  onError: () => {},
})

function erroDe(e, padrao) {
  toast.error(e?.messages?.[0] || padrao)
}

async function copiarPortal(novo) {
  if (novo && !window.confirm(__('Trocar o link? O link antigo para de funcionar.'))) return
  try {
    const r = await call('crm.api.portal.link_portal', { deal: props.docname, novo: novo ? 1 : 0 })
    await navigator.clipboard.writeText(r.link)
    toast.success(__('Link do portal copiado. Mande para o cliente.'))
    dados.reload()
  } catch (e) {
    erroDe(e, __('Não foi possível gerar o link.'))
  }
}

const salvandoProc = ref(false)
async function salvarProcesso() {
  salvandoProc.value = true
  try {
    const r = await call('crm.api.processo.salvar_processo', { deal: props.docname, numero_processo: proc.numero, tribunal: proc.tribunal })
    r.aviso ? toast.warning(r.aviso) : toast.success(__('Processo salvo'))
    dados.reload()
  } catch (e) {
    erroDe(e, __('Não foi possível salvar.'))
  } finally {
    salvandoProc.value = false
  }
}

const parte = reactive({ nome: '', tipo: 'Parte contrária', documento: '' })
const salvandoParte = ref(false)
async function adicionarParte() {
  salvandoParte.value = true
  try {
    const r = await call('crm.api.processo.adicionar_parte', { deal: props.docname, ...parte })
    if (r.conflitos?.length) toast.warning(__('Atenção: possível conflito de interesses. Veja o aviso na parte.'))
    Object.assign(parte, { nome: '', documento: '' })
    dados.reload()
  } catch (e) {
    erroDe(e, __('Não foi possível adicionar.'))
  } finally {
    salvandoParte.value = false
  }
}
async function removerParte(p) {
  if (!window.confirm(__('Remover {0}?', [p.nome]))) return
  await call('crm.api.processo.remover_parte', { parte: p.name })
  dados.reload()
}

const andamento = reactive({ texto: '', visivel: true })
const salvandoAnd = ref(false)
async function adicionarAndamento() {
  salvandoAnd.value = true
  try {
    await call('crm.api.processo.adicionar_andamento', { deal: props.docname, texto: andamento.texto, visivel_cliente: andamento.visivel ? 1 : 0 })
    Object.assign(andamento, { texto: '', visivel: true })
    dados.reload()
  } catch (e) {
    erroDe(e, __('Não foi possível registrar.'))
  } finally {
    salvandoAnd.value = false
  }
}
async function removerAndamento(a) {
  if (!window.confirm(__('Remover este andamento?'))) return
  await call('crm.api.processo.remover_andamento', { andamento: a.name })
  dados.reload()
}

const enc = reactive({ motivo: '', devolvidos: false, obs: '' })
const encerrando = ref(false)
async function encerrar(mesmoAssim) {
  if (!enc.motivo) return toast.warning(__('Escolha como o caso terminou.'))
  encerrando.value = true
  try {
    const r = await call('crm.api.processo.encerrar', {
      deal: props.docname, motivo: enc.motivo, documentos_devolvidos: enc.devolvidos ? 1 : 0,
      observacoes: enc.obs, mesmo_com_pendencias: mesmoAssim ? 1 : 0,
    })
    if (!r.ok) {
      if (window.confirm(__('Ainda há pendências: {0}. Encerrar mesmo assim?', [r.pendencias.join('; ')]))) return encerrar(true)
      return
    }
    toast.success(__('Caso encerrado'))
    dados.reload()
  } catch (e) {
    erroDe(e, __('Não foi possível encerrar.'))
  } finally {
    encerrando.value = false
  }
}
async function reabrir() {
  if (!window.confirm(__('Reabrir este caso?'))) return
  await call('crm.api.processo.reabrir', { deal: props.docname })
  dados.reload()
}
async function termo() {
  try {
    const r = await call('crm.api.processo.termo_encerramento_pdf', { deal: props.docname })
    const bytes = Uint8Array.from(atob(r.pdf), (c) => c.charCodeAt(0))
    window.open(URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' })), '_blank')
  } catch (e) {
    erroDe(e, __('Não foi possível gerar o termo.'))
  }
}
</script>
