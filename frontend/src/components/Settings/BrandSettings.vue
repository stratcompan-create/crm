<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8 text-ink-gray-8">
    <!-- Header -->
    <div class="flex justify-between px-2 text-ink-gray-8">
      <div class="flex flex-col gap-1">
        <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
          {{ __('Brand Settings') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{ __('Configure your brand name, logo and favicon') }}
        </p>
      </div>
      <div class="flex item-center space-x-2 w-3/12 justify-end">
        <Button
          v-if="settings.isDirty"
          :label="__('Update')"
          variant="solid"
          :loading="settings.loading"
          @click="updateSettings"
        />
      </div>
    </div>

    <div class="grid min-h-0 flex-1 gap-6 overflow-y-auto lg:grid-cols-[minmax(0,1fr)_340px]">
    <!-- Fields -->
    <div class="flex flex-col p-2 gap-4">
      <!-- Brand Anm -->
      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7 truncate">
            {{ __('Brand Name') }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Set the name of your brand. Appears in the left sidebar.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <FormControl
            v-model="settings.doc.brand_name"
            type="text"
            size="md"
            :placeholder="__('Enter Brand Name')"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <!-- website url -->
      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7 truncate">
            {{ __('Site do Escritório') }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Usado no botão "Meu Site" do menu superior.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <FormControl
            v-model="settings.doc.website_url"
            type="text"
            size="md"
            :placeholder="__('https://seusite.com')"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7 truncate">
            {{ __('Cor principal da marca') }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Usada nos PDFs de orçamento, proposta comercial e contrato.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input
            type="color"
            :value="settings.doc.brand_color || '#042d3c'"
            class="h-8 w-12 cursor-pointer rounded border border-outline-gray-2 bg-transparent"
            @input="settings.doc.brand_color = $event.target.value"
          />
          <Button
            v-if="settings.doc.brand_color"
            variant="ghost"
            :label="__('Restaurar')"
            @click="settings.doc.brand_color = ''"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7 truncate">
            {{ __('Cor de destaque da marca') }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Usada nos detalhes e linhas dos PDFs.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input
            type="color"
            :value="settings.doc.brand_accent || '#8aa1a9'"
            class="h-8 w-12 cursor-pointer rounded border border-outline-gray-2 bg-transparent"
            @input="settings.doc.brand_accent = $event.target.value"
          />
          <Button
            v-if="settings.doc.brand_accent"
            variant="ghost"
            :label="__('Restaurar')"
            @click="settings.doc.brand_accent = ''"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Cor de fundo neutra') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('O bege, o cinza ou o off-white da marca. Usada como fundo das páginas dos documentos.') }}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input
            type="color"
            :value="settings.doc.brand_neutral || '#f4f2ed'"
            class="h-8 w-12 cursor-pointer rounded border border-outline-gray-2 bg-transparent"
            @input="settings.doc.brand_neutral = $event.target.value"
          />
          <Button
            v-if="settings.doc.brand_neutral"
            variant="ghost"
            :label="__('Restaurar')"
            @click="settings.doc.brand_neutral = ''"
          />
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <div class="flex items-center justify-between gap-8">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Estilo padrão dos documentos') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Qual cor predomina nas propostas, contratos e relatórios. Cada proposta pode escolher outro estilo.') }}
          </div>
        </div>
        <FormControl
          v-model="settings.doc.documento_estilo"
          class="w-64"
          type="select"
          :options="[
            { label: __('Cor da marca nos destaques'), value: 'escuro' },
            { label: __('Fundo neutro'), value: 'claro' },
            { label: __('Fundo branco'), value: 'branco' },
            { label: __('Cor da marca em tudo'), value: 'cor' },
          ]"
        />
      </div>

      <div class="h-px border-t border-outline-elevation-2" />

      <!-- tipografia -->
      <div class="flex flex-col gap-3">
        <div class="flex flex-col">
          <div class="text-p-base-medium text-ink-gray-7">{{ __('Tipografia dos documentos') }}</div>
          <div class="text-p-sm text-ink-gray-5">
            {{ __('Escolha um par pronto ou ajuste a fonte de cada função. A prévia ao lado mostra o resultado.') }}
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="p in fontCatalog.data?.pares || []"
            :key="p.chave"
            type="button"
            :title="p.descricao"
            class="rounded-full border px-3 py-1 text-p-sm"
            :class="presetActive(p) ? 'border-ink-gray-9 bg-surface-gray-2 font-medium text-ink-gray-9' : 'border-outline-gray-2 text-ink-gray-7'"
            @click="applyPreset(p)"
          >
            {{ p.nome }}
          </button>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div v-for="r in fontRoles" :key="r.chave" class="flex flex-col gap-1">
            <span class="text-p-sm text-ink-gray-6">{{ r.nome }} <span class="text-xs text-ink-gray-4">· {{ r.ajuda }}</span></span>
            <FormControl v-model="settings.doc['fonte_' + r.chave]" type="select" :options="fontOptions" />
          </div>
        </div>
      </div>
      <div class="h-px border-t border-outline-elevation-2" />

      <!-- logo -->
      <div class="flex flex-col justify-between gap-4">
        <div class="flex items-center flex-1 gap-5">
          <div
            class="flex items-center justify-center rounded border border-outline-elevation-2 size-20"
          >
            <img
              v-if="settings.doc?.brand_logo"
              :src="settings.doc?.brand_logo"
              alt="Logo"
              class="size-8 rounded"
            />
            <ImageIcon v-else class="size-5 text-ink-gray-4" />
          </div>
          <div class="flex flex-1 flex-col gap-1">
            <span class="text-base-medium">{{ __('Brand Logo') }}</span>
            <span class="text-p-base text-ink-gray-6">
              {{
                __(
                  'Appears in the left sidebar. Recommended size is 32x32 px in PNG or SVG',
                )
              }}
            </span>
          </div>
          <div>
            <ImageUploader
              image_type="image/ico"
              :image_url="settings.doc?.brand_logo"
              @upload="(url) => (settings.doc.brand_logo = url)"
              @remove="() => (settings.doc.brand_logo = '')"
            />
          </div>
        </div>
      </div>

      <!-- favicon -->
      <div class="flex flex-col justify-between gap-4">
        <div class="flex items-center flex-1 gap-5">
          <div
            class="flex items-center justify-center rounded border border-outline-elevation-2 size-20"
          >
            <img
              v-if="settings.doc?.favicon"
              :src="settings.doc?.favicon"
              alt="Favicon"
              class="size-8 rounded"
            />
            <ImageIcon v-else class="size-5 text-ink-gray-4" />
          </div>
          <div class="flex flex-1 flex-col gap-1">
            <span class="text-base-medium">{{ __('Favicon') }}</span>
            <span class="text-p-base text-ink-gray-6">
              {{
                __(
                  'Appears next to the title in your browser tab. Recommended size is 32x32 px in PNG or ICO',
                )
              }}
            </span>
          </div>
          <div>
            <ImageUploader
              image_type="image/ico"
              :image_url="settings.doc?.favicon"
              @upload="(url) => (settings.doc.favicon = url)"
              @remove="() => (settings.doc.favicon = '')"
            />
          </div>
        </div>
      </div>
    </div>
    <aside class="p-2">
      <div class="sticky top-2">
        <DocumentPreview
          :cor="settings.doc.brand_color"
          :destaque="settings.doc.brand_accent"
          :neutra="settings.doc.brand_neutral"
          :estilo="settings.doc.documento_estilo"
          :nome="settings.doc.brand_name"
          :fontes="fontesAtuais"
        />
      </div>
    </aside>
    </div>
  </div>
</template>
<script setup>
import ImageIcon from '~icons/lucide/image'
import DocumentPreview from '@/components/DocumentPreview.vue'
import ImageUploader from '@/components/Controls/ImageUploader.vue'
import { Button, FormControl, createResource } from 'frappe-ui'
import { computed } from 'vue'
import { getSettings } from '@/stores/settings'
import { showSettings } from '@/composables/settings'

const { _settings: settings, setupBrand } = getSettings()

const fontCatalog = createResource({ url: 'crm.api.tipografia.get_catalog', auto: true })
const fontRoles = [
  { chave: 'titulo', nome: __('Título'), ajuda: __('nomes e títulos') },
  { chave: 'subtitulo', nome: __('Subtítulo'), ajuda: __('legendas e faixas') },
  { chave: 'texto', nome: __('Texto'), ajuda: __('parágrafos') },
  { chave: 'numeros', nome: __('Números'), ajuda: __('valores em destaque') },
]
const fontOptions = computed(() => [
  { label: __('Padrão'), value: '' },
  ...(fontCatalog.data?.fontes || []).map((f) => ({ label: `${f.nome} · ${__(f.categoria)}`, value: f.chave })),
])
const fontesAtuais = computed(() => ({
  titulo: settings.doc?.fonte_titulo,
  subtitulo: settings.doc?.fonte_subtitulo,
  texto: settings.doc?.fonte_texto,
  numeros: settings.doc?.fonte_numeros,
}))
function applyPreset(p) {
  for (const r of ['titulo', 'subtitulo', 'texto', 'numeros']) settings.doc['fonte_' + r] = p.fontes[r]
}
function presetActive(p) {
  const def = fontCatalog.data?.padrao || {}
  return ['titulo', 'subtitulo', 'texto', 'numeros'].every(
    (r) => (settings.doc?.['fonte_' + r] || def[r]) === p.fontes[r],
  )
}

function updateSettings() {
  settings.save.submit(null, {
    onSuccess: () => {
      showSettings.value = false
      setupBrand()
    },
  })
}
</script>
