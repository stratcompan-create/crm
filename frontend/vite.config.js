import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'



// Textos fixos em inglês dentro dos componentes do frappe-ui (lista, seletor, calendário...).
// Traduzidos na hora do build, pelo mesmo motivo do plugin abaixo.
const UI_TEXT_PT = {
  'Select all': 'Selecionar tudo',
  'Select All': 'Selecionar tudo',
  'Clear All': 'Limpar tudo',
  Clear: 'Limpar',
  'No results found': 'Nenhum resultado encontrado',
  'No results': 'Nenhum resultado',
  'No Data': 'Sem dados',
  'Load More': 'Carregar mais',
  Search: 'Buscar',
  Today: 'Hoje',
  Now: 'Agora',
  Day: 'Dia',
  Week: 'Semana',
  Month: 'Mês',
  'All day': 'Dia inteiro',
  'Select date': 'Selecionar data',
  'Select time': 'Selecionar hora',
  'Select month': 'Selecionar mês',
  'Select year': 'Selecionar ano',
  'Select range': 'Selecionar período',
  'Select option': 'Selecionar',
  'Select an option': 'Selecione uma opção',
  Shortcuts: 'Atalhos',
  Close: 'Fechar',
  Loading: 'Carregando',
  Cancel: 'Cancelar',
  Confirm: 'Confirmar',
  Save: 'Salvar',
  Submit: 'Enviar',
  Edit: 'Editar',
  Remove: 'Remover',
  Copy: 'Copiar',
  Back: 'Voltar',
  Title: 'Título',
  Date: 'Data',
  Color: 'Cor',
  Person: 'Pessoa',
  Venue: 'Local',
  'Start Time': 'Início',
  'End Time': 'Fim',
}

function translateFrappeUiTemplate(code) {
  const i = code.indexOf('<script')
  const tpl = i === -1 ? code : code.slice(0, i)
  const rest = i === -1 ? '' : code.slice(i)
  let out = tpl
  for (const [en, pt] of Object.entries(UI_TEXT_PT)) {
    const e = en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    out = out.replace(new RegExp('>(\\s*)' + e + '(\\s*)<', 'g'), '>$1' + pt + '$2<')
    out = out.replace(new RegExp('((?:label|placeholder|title|text|tooltip|aria-label)=")' + e + '"', 'g'), '$1' + pt + '"')
  }
  out = out.replace('<div>of</div>', '<div>de</div>')
  return out + rest
}

// frappe-ui hardcodes English month/day/hour labels in its Calendar and
// DatePicker sources, so dayjs.locale() alone cannot translate them. Patch the
// strings at build time instead of editing node_modules (lost on reinstall).
function frappeUiPtBrPlugin() {
  const MONTHS_LONG = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
  const MONTHS_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
  const DAYS_SHORT = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
  const DAYS_LONG = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
  const HOURS_24 = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0') + ':00')
  const arr = (a) => '[' + a.map((s) => JSON.stringify(s)).join(', ') + ']'
  const swapArray = (code, name, values) =>
    code.replace(
      new RegExp('(export const ' + name + '\\s*(?::[^=]+)?=\\s*)\\[[^\\]]*\\]'),
      (_, head) => head + arr(values),
    )
  return {
    name: 'frappe-ui-pt-br',
    enforce: 'pre',
    transform(code, id) {
      const file = id.replace(/\\/g, '/')
      if (!file.includes('frappe-ui/src/components/')) return null
      if (file.endsWith('.vue') && !/playground|stories|\.story/.test(file)) {
        let out = translateFrappeUiTemplate(code)
        if (file.endsWith('/ListView/ListView.vue')) {
          out = out
            .replace("'1 row selected'", "'1 linha selecionada'")
            .replace('`${val} rows selected`', '`${val} linhas selecionadas`')
        }
        if (out !== code) return { code: out, map: null }
        return null
      }
      if (file.endsWith('/Calendar/calendarUtils.ts')) {
        code = swapArray(code, 'monthList', MONTHS_LONG)
        code = swapArray(code, 'daysList', DAYS_SHORT)
        code = swapArray(code, 'daysListFull', DAYS_LONG)
        code = swapArray(code, 'twelveHoursFormat', HOURS_24)
        code = code.replace(/'en-US'/g, "'pt-BR'")
        return { code, map: null }
      }
      if (file.endsWith('/DatePicker/utils.ts')) {
        code = swapArray(code, 'months', MONTHS_SHORT)
        return { code, map: null }
      }
      if (file.endsWith('/DatePicker/useDatePicker.ts')) {
        code = code.replace(/'en-US'/g, "'pt-BR'")
        return { code, map: null }
      }
      return null
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
  const isDev = mode === 'development'
  const config = {
    plugins: [
      frappeUiPtBrPlugin(),
      vue(),
      vueJsx(),
      VitePWA({
        registerType: 'autoUpdate',
        workbox: {
          maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        },
        devOptions: {
          enabled: true,
        },
        manifest: {
          display: 'standalone',
          name: 'CRM',
          short_name: 'CRM',
          start_url: '/crm',
          description:
            'CRM para gestão de leads, negócios e atendimento ao cliente.',
          icons: [
            {
              src: '/assets/crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'maskable',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, 'src'),
        // point at the package src dir (not index.ts) so subpath imports like
        // `@framework/ui/components/Notifications` resolve. Importing subpaths avoids the
        // barrel, which `export *`s components (Grid/Phone/FormLayout) that need a newer
        // frappe-ui (`frappe-ui/internals`) than this app pins.
        '@framework/ui': path.resolve(
          import.meta.dirname,
          '../../frappe/ui/src',
        ),
      },
      // ensure the linked framework package reuses the host app's single copy of each peer.
      // `dompurify` is an implicit dep of @framework/ui's sanitize util (not declared in its
      // package.json); dedupe resolves it to the host's copy since the symlinked source has
      // no node_modules of its own.
      // the editor packages must resolve to one copy each: tiptap imports
      // `@tiptap/pm/model` while prosemirror-state/transform/tables import bare
      // `prosemirror-model`, so a nested install of either throws "multiple
      // versions of prosemirror-model were loaded" on mention insert. Unlike
      // optimizeDeps (dev-only) this also applies to the production build.
      dedupe: [
        'vue',
        'vue-router',
        'frappe-ui',
        'dompurify',
        '@tiptap/core',
        '@tiptap/pm',
        '@tiptap/vue-3',
        'prosemirror-model',
        'prosemirror-state',
        'prosemirror-view',
        'prosemirror-transform',
      ],
    },
    optimizeDeps: {
      include: [
        'feather-icons',
        'tailwind.config.js',
        'prosemirror-state',
        'prosemirror-view',
        'lowlight',
        'interactjs',
      ],
    },
    server: {
      fs: {
        // allow the bench `apps/` dir so Vite can serve linked local packages
        // (frappe-ui, @framework/ui) that live in sibling app repos
        allow: [path.resolve(import.meta.dirname, '../..')],
      },
    },
  }

  const frappeui = await importFrappeUIPlugin(isDev, config)
  config.plugins.unshift(
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../crm/www/crm.html',
        emptyOutDir: true,
        sourcemap: false,
      },
    }),
  )

  return config
})

async function importFrappeUIPlugin(isDev, config) {
  if (isDev) {
    try {
      // Check if local frappe-ui has the vite plugin file
      const fs = await import('node:fs')
      const localVitePluginPath = path.resolve(
        import.meta.dirname,
        '../frappe-ui/vite/index.js',
      )

      if (fs.existsSync(localVitePluginPath)) {
        const module = await import('../frappe-ui/vite/index.js')
        console.info('Local frappe-ui vite plugin found, using local plugin')
        config.resolve.alias = getAliases(config)
        return module.default
      } else {
        console.warn('Local frappe-ui vite plugin not found, using npm package')
      }
    } catch (error) {
      console.warn(
        'Local frappe-ui not found, falling back to npm package:',
        error.message,
      )
    }
  }
  // Fall back to npm package if local import fails
  const module = await import('frappe-ui/vite')
  return module.default
}

function getAliases(config) {
  return {
    ...config.resolve.alias,
    'frappe-ui/tailwind': path.resolve(
      import.meta.dirname,
      '../frappe-ui/tailwind/preset.js',
    ),
    'frappe-ui/style.css': path.resolve(
      import.meta.dirname,
      '../frappe-ui/src/style.css',
    ),
    'frappe-ui/frappe': path.resolve(
      import.meta.dirname,
      '../frappe-ui/frappe/index.js',
    ),
    // subpath entries must precede the bare `frappe-ui` key: a plain string alias
    // matches by prefix, so without these subpaths would rewrite under
    // `.../src/index.ts`. `internals` is pulled in by @framework/ui.
    'frappe-ui/icons': path.resolve(
      import.meta.dirname,
      '../frappe-ui/icons/index.ts',
    ),
    'frappe-ui/editor': path.resolve(
      import.meta.dirname,
      '../frappe-ui/src/molecules/editor/index.ts',
    ),
    'frappe-ui/editor-style.css': path.resolve(
      import.meta.dirname,
      '../frappe-ui/src/molecules/editor/style.css',
    ),
    'frappe-ui/internals': path.resolve(
      import.meta.dirname,
      '../frappe-ui/internals.ts',
    ),
    'frappe-ui': path.resolve(import.meta.dirname, '../frappe-ui/src/index.ts'),
  }
}
