<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <div class="text-p-base-medium text-ink-gray-8">{{ __('Prévia do documento') }}</div>
      <Button v-if="showPdf" variant="subtle" size="sm" iconLeft="lucide-file-text" :label="__('Ver como PDF')" :loading="loading" @click="openPdf" />
    </div>

    <!-- capa -->
    <div class="pv" :style="coverBox">
      <div v-if="!dark" class="absolute rounded-sm" :style="frame" />
      <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
        <div class="pv-name" :style="{ ...coverName, fontFamily: fam.titulo }">{{ name }}</div>
        <div class="pv-label" :style="{ color: pal.A, fontFamily: fam.subtitulo }">{{ __('PROPOSTA COMERCIAL') }}</div>
        <div class="pv-sub" :style="{ color: dark ? '#dfe7ea' : muted, fontFamily: fam.subtitulo }">{{ __('Site institucional e CRM') }}</div>
      </div>
      <div class="pv-foot" :style="{ color: dark ? pal.A : muted, fontFamily: fam.subtitulo }">{{ brand }} × {{ name }}</div>
    </div>

    <!-- página interna -->
    <div class="pv" :style="{ background: pageBg }">
      <div class="pv-head" :style="{ color: headInk, fontFamily: fam.subtitulo }">
        <span><i class="pv-dia" :style="{ borderColor: pal.A }" />{{ name }}</span><span>02 / 06</span>
      </div>
      <div class="pv-body">
        <div class="pv-eyebrow" :style="{ color: headInk, fontFamily: fam.subtitulo }">{{ __('INTRODUÇÃO AO PROJETO') }}</div>
        <div class="pv-title" :style="{ color: titleInk, fontFamily: fam.titulo }">{{ __('Um projeto para') }} <i :style="{ color: muted }">{{ name }}</i></div>
        <p class="pv-text" :style="{ color: style === 'cor' ? '#f2efe8' : '#1f2d33', fontFamily: fam.texto }">
          {{ __('Um texto de exemplo para mostrar como os parágrafos aparecem no documento, com a fonte escolhida.') }}
        </p>
        <div class="pv-cards">
          <div v-for="t in [__('Site'), __('CRM')]" :key="t" class="pv-card" :style="cardStyle">
            <b :style="{ color: titleInk, fontFamily: fam.titulo }">{{ t }}</b>
            <div :style="{ background: inkFade }" />
          </div>
        </div>
        <div class="pv-band" :style="{ ...bandStyle, fontFamily: fam.numeros }">
          <div v-for="n in [['60', __('DIAS')], ['2', __('ENTREGAS')], ['100%', __('SOB MEDIDA')]]" :key="n[1]">
            <b>{{ n[0] }}</b><small :style="{ color: bandLabel, fontFamily: fam.subtitulo }">{{ n[1] }}</small>
          </div>
        </div>
      </div>
    </div>
    <p class="text-xs text-ink-gray-5">{{ __('Aproximação instantânea. Para ver o documento exato, use "Ver como PDF".') }}</p>
  </div>
</template>

<script setup>
import { Button, call, createResource, toast } from 'frappe-ui'
import { computed, ref } from 'vue'

// carrega as fontes dos documentos uma vez só, no navegador
let fontsLoaded = false
function loadFonts(catalog) {
  if (fontsLoaded || !catalog?.fontes) return
  fontsLoaded = true
  const css = catalog.fontes
    .flatMap((f) =>
      f.arquivos.map(
        (a) => `@font-face{font-family:'${f.css}';font-weight:${a.peso};font-style:${a.estilo};src:url('${a.url}') format('truetype');font-display:swap}`,
      ),
    )
    .join('\n')
  const el = document.createElement('style')
  el.textContent = css
  document.head.appendChild(el)
}
const catalog = createResource({ url: 'crm.api.tipografia.get_catalog', auto: true, onSuccess: loadFonts })

const props = defineProps({
  cor: { type: String, default: '' },
  destaque: { type: String, default: '' },
  neutra: { type: String, default: '' },
  estilo: { type: String, default: '' },
  nome: { type: String, default: '' },
  showPdf: { type: Boolean, default: true },
  fontes: { type: Object, default: () => ({}) },
})

function mix(a, b, r) {
  const p = (h, i) => parseInt(h.slice(i, i + 2), 16)
  const c = (i) => Math.round(p(a, i) * (1 - r) + p(b, i) * r)
  return '#' + [1, 3, 5].map((i) => c(i).toString(16).padStart(2, '0')).join('')
}
const valid = (v, f) => (/^#[0-9a-fA-F]{6}$/.test((v || '').trim()) ? v.trim() : f)

const style = computed(() => props.estilo || 'escuro')
const pal = computed(() => ({
  C: valid(props.cor, '#042d3c'),
  A: valid(props.destaque, '#8aa1a9'),
  N: valid(props.neutra, '#f4f2ed'),
}))
const dark = computed(() => ['escuro', 'cor'].includes(style.value))
const name = computed(() => __('Cliente Exemplo'))
const brand = computed(() => props.nome || __('Seu Escritório'))

const pageBg = computed(() => ({ escuro: pal.value.N, claro: pal.value.N, branco: '#ffffff', cor: pal.value.C })[style.value])
const muted = computed(() => (style.value === 'cor' ? mix(pal.value.C, '#ffffff', 0.62) : mix(pal.value.C, '#ffffff', 0.35)))
const titleInk = computed(() => (style.value === 'cor' ? pal.value.N : pal.value.C))
const headInk = computed(() => (style.value === 'cor' ? mix(pal.value.C, '#ffffff', 0.62) : '#6b7c82'))
const inkFade = computed(() => (style.value === 'cor' ? 'rgba(242,239,232,.28)' : 'rgba(31,45,51,.18)'))

const coverBox = computed(() =>
  dark.value
    ? { background: `radial-gradient(circle at 50% 50%, ${mix(pal.value.C, '#ffffff', 0.16)}, ${mix(pal.value.C, '#000000', 0.35)})` }
    : { background: style.value === 'branco' ? '#ffffff' : pal.value.N },
)
const frame = computed(() => ({ inset: '4cqw', border: `0.35cqw solid ${mix(style.value === 'branco' ? '#ffffff' : pal.value.N, pal.value.C, 0.3)}` }))
const coverName = computed(() => ({
  color: dark.value ? mix(pal.value.A, '#ffffff', 0.55) : pal.value.C,
  borderBottom: `0.5cqw solid ${dark.value ? mix(pal.value.A, '#ffffff', 0.55) : pal.value.A}`,
}))

const cardStyle = computed(() => {
  const C = pal.value.C
  const bg = { escuro: '#ffffff', claro: '#ffffff', branco: mix(pal.value.N, '#ffffff', 0.55), cor: mix(C, '#ffffff', 0.08) }[style.value]
  return { background: bg, borderLeft: `0.8cqw solid ${pal.value.A}` }
})
const bandStyle = computed(() => {
  const C = pal.value.C
  const map = {
    escuro: { background: C, color: '#ffffff' },
    claro: { background: mix(pal.value.N, C, 0.1), color: C },
    branco: { background: mix('#ffffff', C, 0.1), color: C },
    cor: { background: mix(C, '#000000', 0.28), color: pal.value.N },
  }
  return map[style.value]
})
const bandLabel = computed(() => (style.value === 'escuro' ? pal.value.A : muted.value))

const fam = computed(() => {
  const data = catalog.data
  const pick = (role) => {
    const key = props.fontes?.[role] || data?.padrao?.[role]
    const f = data?.fontes?.find((x) => x.chave === key)
    const serif = f ? f.categoria.startsWith('Serifada') : ['titulo', 'numeros'].includes(role)
    return f ? `'${f.css}', ${serif ? 'Georgia, serif' : 'Arial, sans-serif'}` : serif ? 'Georgia, serif' : 'Arial, sans-serif'
  }
  return { titulo: pick('titulo'), subtitulo: pick('subtitulo'), texto: pick('texto'), numeros: pick('numeros') }
})

const loading = ref(false)
async function openPdf() {
  loading.value = true
  try {
    const r = await call('crm.api.estilo.preview_pdf', {
      cor: props.cor,
      destaque: props.destaque,
      neutra: props.neutra,
      estilo: props.estilo,
      nome: props.nome,
      fonte_titulo: props.fontes?.titulo || '',
      fonte_subtitulo: props.fontes?.subtitulo || '',
      fonte_texto: props.fontes?.texto || '',
      fonte_numeros: props.fontes?.numeros || '',
    })
    const bytes = Uint8Array.from(atob(r.pdf), (c) => c.charCodeAt(0))
    window.open(URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' })), '_blank')
  } catch (e) {
    toast.error(e?.messages?.[0] || __('Não foi possível gerar a prévia em PDF.'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.pv {
  container-type: inline-size;
  position: relative;
  aspect-ratio: 298 / 210;
  overflow: hidden;
  border-radius: 6px;
  border: 1px solid #d7dde0;
  font-family: Georgia, 'Lora', serif;
}
.pv-name { font-size: 6.4cqw; text-transform: uppercase; letter-spacing: 0.03em; padding-bottom: 1cqw; }
.pv-label { font-size: 1.7cqw; letter-spacing: 0.4em; font-weight: 700; margin-top: 5cqw; font-family: Arial, sans-serif; }
.pv-sub { font-size: 2.2cqw; margin-top: 2cqw; font-family: Arial, sans-serif; }
.pv-foot { position: absolute; left: 5cqw; bottom: 4cqw; font-size: 1.5cqw; letter-spacing: 0.2em; font-family: Arial, sans-serif; text-transform: uppercase; }
.pv-head { position: absolute; top: 4cqw; left: 5cqw; right: 5cqw; display: flex; justify-content: space-between; font-size: 1.5cqw; letter-spacing: 0.25em; font-family: Arial, sans-serif; text-transform: uppercase; }
.pv-dia { display: inline-block; width: 1.6cqw; height: 1.6cqw; border: 0.25cqw solid; margin-right: 1.6cqw; transform: rotate(45deg); }
.pv-body { position: absolute; top: 11cqw; left: 5cqw; right: 5cqw; }
.pv-eyebrow { font-size: 1.5cqw; letter-spacing: 0.3em; font-family: Arial, sans-serif; margin-bottom: 1.6cqw; }
.pv-title { font-size: 5cqw; font-weight: 700; line-height: 1.1; margin-bottom: 3cqw; }
.pv-title i { font-weight: 400; }
.pv-text { font-size: 2.1cqw; line-height: 1.55; margin: 0 0 1cqw; max-width: 62%; }
.pv-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 2cqw; margin: 3cqw 0; }
.pv-card { padding: 2cqw 2.4cqw; font-family: Arial, sans-serif; }
.pv-card b { font-size: 2.3cqw; display: block; margin-bottom: 1.2cqw; }
.pv-card > div { height: 1.1cqw; width: 80%; border-radius: 1cqw; }
.pv-band { display: grid; grid-template-columns: repeat(3, 1fr); padding: 2.4cqw 3cqw; font-family: Georgia, serif; }
.pv-band b { display: block; font-size: 4cqw; font-weight: 400; }
.pv-band small { font-size: 1.3cqw; letter-spacing: 0.22em; font-family: Arial, sans-serif; }
</style>
