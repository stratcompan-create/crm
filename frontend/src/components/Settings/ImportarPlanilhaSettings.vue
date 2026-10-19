<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto px-6 py-8 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="text-2xl-semibold leading-none">{{ __('Importar planilha') }}</h2>
      <p class="text-p-base text-ink-gray-6">
        {{ __('Traga o que o escritório já usa no Excel sem redigitar nada. O CRM reconhece as colunas sozinho, mostra uma prévia e só grava quando você confirmar. Nada é apagado: quem já existe no CRM é ignorado.') }}
      </p>
    </div>

    <!-- 1. tipo -->
    <div class="mx-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="t in tipos.data || []"
        :key="t.tipo"
        type="button"
        class="flex flex-col gap-1 rounded-lg border px-4 py-3 text-left transition"
        :class="tipo === t.tipo ? 'border-outline-gray-5 bg-surface-gray-2' : 'border-outline-gray-2 hover:bg-surface-gray-1'"
        @click="escolherTipo(t.tipo)"
      >
        <span class="text-p-base-medium text-ink-gray-9">{{ t.titulo }}</span>
        <span class="text-xs text-ink-gray-5">{{ t.descricao }}</span>
      </button>
    </div>

    <div v-if="tipo" class="mx-2 flex flex-wrap items-center gap-2">
      <Button variant="subtle" iconLeft="lucide-download" :label="__('Baixar planilha modelo')" :loading="baixando" @click="baixarModelo" />
      <Button variant="solid" iconLeft="lucide-upload" :label="arquivo.nome ? __('Trocar planilha') : __('Escolher planilha (.xlsx ou .csv)')" @click="$refs.input.click()" />
      <span v-if="arquivo.nome" class="truncate text-p-sm text-ink-gray-6">{{ arquivo.nome }}</span>
      <input ref="input" type="file" accept=".xlsx,.csv" class="hidden" @change="escolherArquivo" />
    </div>
    <p v-if="tipo && !arquivo.nome" class="mx-2 -mt-3 text-xs text-ink-gray-5">
      {{ __('Pode usar a sua própria planilha: os nomes das colunas não precisam ser iguais aos do modelo.') }}
    </p>

    <ErrorMessage v-if="erro" class="mx-2" :message="erro" />
    <div v-if="analisando" class="mx-2 text-p-sm text-ink-gray-5">{{ __('Lendo a planilha…') }}</div>

    <!-- 2. colunas + prévia -->
    <template v-if="analise && !resultado">
      <div class="mx-2 flex flex-wrap gap-2 text-p-sm">
        <span class="rounded bg-surface-gray-2 px-2 py-1">{{ __('{0} linhas na planilha', [analise.total]) }}</span>
        <span class="rounded bg-surface-green-2 px-2 py-1 text-ink-green-3">{{ __('{0} prontas para importar', [analise.validas]) }}</span>
        <span v-if="analise.com_erro" class="rounded bg-surface-amber-2 px-2 py-1 text-ink-amber-3">{{ __('{0} com problema (serão puladas)', [analise.com_erro]) }}</span>
      </div>

      <div class="mx-2 flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Colunas reconhecidas') }}</div>
        <p class="text-xs text-ink-gray-5">{{ __('Confira de qual coluna da sua planilha vem cada informação. Se algo estiver errado, é só trocar.') }}</p>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="c in campos" :key="c.campo" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ c.rotulo }}<span v-if="c.obrigatorio" class="text-ink-red-3"> *</span></span>
            <FormControl
              type="select"
              :options="opcoesColuna"
              :modelValue="String(mapa[c.campo] ?? -1)"
              @update:modelValue="(v) => trocarColuna(c.campo, v)"
            />
          </div>
        </div>
        <ErrorMessage
          v-if="analise.obrigatorios_faltando?.length"
          :message="__('Escolha a coluna de: {0}', [analise.obrigatorios_faltando.join(', ')])"
        />
      </div>

      <div class="mx-2 flex flex-col gap-2">
        <div class="text-p-base-medium text-ink-gray-9">{{ __('Prévia') }}</div>
        <div class="overflow-x-auto rounded-lg border border-outline-gray-2">
          <table class="w-full text-left text-p-sm">
            <thead class="bg-surface-gray-2 text-ink-gray-6">
              <tr>
                <th class="px-3 py-2">{{ __('Linha') }}</th>
                <th v-for="c in camposUsados" :key="c.campo" class="whitespace-nowrap px-3 py-2">{{ c.rotulo }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="p in analise.previa" :key="p.linha">
                <tr class="border-t border-outline-gray-1" :class="p.erros.length ? 'bg-surface-amber-1' : ''">
                  <td class="px-3 py-2 text-ink-gray-5">{{ p.linha }}</td>
                  <td v-for="c in camposUsados" :key="c.campo" class="max-w-[220px] truncate px-3 py-2">{{ mostrar(p.valores[c.campo]) }}</td>
                </tr>
                <tr v-if="p.erros.length" class="bg-surface-amber-1">
                  <td></td>
                  <td :colspan="camposUsados.length" class="px-3 pb-2 text-xs text-ink-amber-3">{{ p.erros.join(' · ') }}</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <div class="mx-2 flex items-center justify-end gap-2">
        <Button variant="ghost" :label="__('Cancelar')" @click="recomecar" />
        <Button
          variant="solid"
          iconLeft="lucide-check"
          :label="__('Importar {0} linhas', [analise.validas])"
          :loading="importando"
          :disabled="!analise.validas || analise.obrigatorios_faltando?.length > 0"
          @click="importar"
        />
      </div>
    </template>

    <!-- 3. resultado -->
    <div v-if="resultado" class="mx-2 flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-4">
      <div class="text-p-base-medium text-ink-gray-9">{{ __('Importação concluída') }}</div>
      <div class="flex flex-wrap gap-2 text-p-sm">
        <span class="rounded bg-surface-green-2 px-2 py-1 text-ink-green-3">{{ __('{0} registros criados', [resultado.criados]) }}</span>
        <span v-if="resultado.ignorados" class="rounded bg-surface-gray-2 px-2 py-1">{{ __('{0} já existiam (ignorados)', [resultado.ignorados]) }}</span>
        <span v-if="resultado.com_erro" class="rounded bg-surface-amber-2 px-2 py-1 text-ink-amber-3">{{ __('{0} linhas não entraram', [resultado.com_erro]) }}</span>
      </div>
      <div v-if="resultado.problemas?.length" class="flex flex-col gap-1 text-xs text-ink-gray-6">
        <div v-for="p in resultado.problemas" :key="p.linha">{{ __('Linha {0}: {1}', [p.linha, p.motivo]) }}</div>
      </div>
      <div>
        <Button variant="subtle" iconLeft="lucide-upload" :label="__('Importar outra planilha')" @click="recomecar" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button, ErrorMessage, FormControl, call, createResource, toast } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const tipos = createResource({ url: 'crm.api.importacao.tipos', auto: true })

const tipo = ref('')
const arquivo = reactive({ nome: '', base64: '' })
const analise = ref(null)
const mapa = ref({})
const resultado = ref(null)
const erro = ref('')
const analisando = ref(false)
const importando = ref(false)
const baixando = ref(false)
const input = ref(null)

const campos = computed(() => (tipos.data || []).find((t) => t.tipo === tipo.value)?.campos || [])
const camposUsados = computed(() => campos.value.filter((c) => mapa.value[c.campo] !== null && mapa.value[c.campo] !== undefined))
const opcoesColuna = computed(() => [
  { label: __('— não importar —'), value: '-1' },
  ...(analise.value?.colunas || []).map((c, i) => ({ label: c, value: String(i) })),
])

function recomecar() {
  Object.assign(arquivo, { nome: '', base64: '' })
  analise.value = null
  resultado.value = null
  mapa.value = {}
  erro.value = ''
  if (input.value) input.value.value = ''
}

function escolherTipo(t) {
  tipo.value = t
  recomecar()
}

function mostrar(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') return v.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return v.split('-').reverse().join('/')
  return v
}

function escolherArquivo(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    erro.value = __('Arquivo maior que 5 MB. Divida a planilha em partes.')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    arquivo.nome = file.name
    arquivo.base64 = String(reader.result).split(',').pop()
    resultado.value = null
    analisar(null)
  }
  reader.readAsDataURL(file)
}

async function analisar(mapeamento) {
  analisando.value = true
  erro.value = ''
  try {
    const r = await call('crm.api.importacao.analisar', {
      tipo: tipo.value,
      arquivo: arquivo.base64,
      nome_arquivo: arquivo.nome,
      mapeamento: mapeamento ? JSON.stringify(mapeamento) : null,
    })
    analise.value = r
    mapa.value = { ...r.mapeamento }
  } catch (e) {
    analise.value = null
    erro.value = e?.messages?.[0] || __('Não foi possível ler a planilha.')
  } finally {
    analisando.value = false
  }
}

function trocarColuna(campo, valor) {
  const idx = Number(valor)
  mapa.value = { ...mapa.value, [campo]: idx < 0 ? null : idx }
  analisar(mapa.value)
}

async function baixarModelo() {
  baixando.value = true
  try {
    const r = await call('crm.api.importacao.baixar_modelo', { tipo: tipo.value })
    const bytes = Uint8Array.from(atob(r.arquivo), (c) => c.charCodeAt(0))
    const url = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
    const a = document.createElement('a')
    a.href = url
    a.download = r.nome
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    erro.value = e?.messages?.[0] || __('Não foi possível gerar o modelo.')
  } finally {
    baixando.value = false
  }
}

async function importar() {
  if (!window.confirm(__('Importar {0} linhas para o CRM?', [analise.value.validas]))) return
  importando.value = true
  erro.value = ''
  try {
    resultado.value = await call('crm.api.importacao.importar', {
      tipo: tipo.value,
      arquivo: arquivo.base64,
      nome_arquivo: arquivo.nome,
      mapeamento: JSON.stringify(mapa.value),
    })
    toast.success(__('{0} registros importados', [resultado.value.criados]))
  } catch (e) {
    erro.value = e?.messages?.[0] || __('Não foi possível importar.')
  } finally {
    importando.value = false
  }
}
</script>
