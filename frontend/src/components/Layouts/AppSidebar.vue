<template>
  <!-- The notifications panel is absolutely positioned at `left: 100%`, so it
       needs a positioning context that is not the Sidebar itself (Sidebar sets
       overflow-x-hidden, which would clip the panel away).

       It also paints the sidebar surface: Sidebar's own `bg-surface-sidebar` is
       transparent in dark mode, and nothing behind it sets a background, so the
       column falls through to the white page canvas. The token cannot be
       overridden on the Sidebar element itself — `bg-surface-sidebar` is emitted
       after `bg-surface-gray-1` in the utilities layer and would win. -->
  <div v-if="showSidebarColumn" class="stratcompany-sidebar relative flex h-full bg-white">
    <Sidebar
      v-model:collapsed="sidebarCollapsedModel"
      :disable-collapse="mobile"
      :width="mobile ? '260px' : undefined"
      class="border-r border-outline-gray-1"
    >
      <div class="flex h-full flex-col p-2">
        <UserDropdown :isCollapsed="isCollapsed" />

        <!-- overflow-y-auto forces overflow-x to clip too, which would slice the
             active row's shadow. Widen the scroll box to the sidebar edges and
             pad the content back in so the shadow has room. -->
        <div class="-mx-2 mt-2 flex flex-1 flex-col gap-1 overflow-y-auto px-2">
          <CollapsibleSection
            v-if="isCrmSection"
            v-for="section in allViews"
            :key="section.name"
            :label="section.name"
            :hideLabel="section.hideLabel"
            :opened="section.opened"
          >
            <template #header="{ opened, hide, toggle }">
              <SidebarLabel
                v-if="!hide"
                divider
                class="mb-1 mt-4 select-none"
                :class="!isCollapsed && 'cursor-pointer'"
                @click="toggle()"
              >
                <span class="flex items-center gap-1.5">
                  <span
                    class="lucide-chevron-right -ml-0.5 size-4 shrink-0 text-ink-gray-9 transition-transform duration-300 ease-in-out"
                    :class="{ 'rotate-90': opened }"
                    aria-hidden="true"
                  />
                  <span class="truncate">{{ __(section.name) }}</span>
                </span>
              </SidebarLabel>
            </template>
            <nav class="flex flex-col gap-1">
              <SidebarItem
                v-for="link in section.views"
                :key="link.key"
                :to="link.to"
                :label="__(link.label)"
                :active="activeItem === link.key"
                @click="selectItem($event, link.key)"
              >
                <template #prefix>
                  <Icon :icon="link.icon" class="size-4 text-ink-gray-7" />
                </template>
                <Tooltip
                  :text="__(link.label)"
                  placement="right"
                  :hoverDelay="1.5"
                  :disabled="isCollapsed"
                >
                  <span class="truncate text-sm">{{ __(link.label) }}</span>
                </Tooltip>
              </SidebarItem>
            </nav>
          </CollapsibleSection>

          <nav v-if="isFinanceiroSection" class="flex flex-col gap-1">
            <SidebarItem
              v-for="link in financeiroLinks"
              :key="link.key"
              :to="link.to"
              :label="__(link.label)"
              :active="activeItem === link.key"
              @click="selectItem($event, link.key)"
            >
              <template #prefix>
                <Icon :icon="link.icon" class="size-4 text-ink-gray-7" />
              </template>
              <Tooltip
                :text="__(link.label)"
                placement="right"
                :hoverDelay="1.5"
                :disabled="isCollapsed"
              >
                <span class="truncate text-sm">{{ __(link.label) }}</span>
              </Tooltip>
            </SidebarItem>
          </nav>

          <div v-if="isVisaoGeralSection" class="flex flex-col gap-1">
            <div class="mb-1 mt-4 flex items-center justify-between px-1">
              <SidebarLabel class="select-none">{{ __('Arquivos') }}</SidebarLabel>
              <div class="flex items-center gap-0.5">
                <a
                  v-if="isAgency"
                  :href="vscodeUri"
                  class="rounded p-1 hover:bg-surface-gray-2"
                  :title="__('Abrir no VS Code')"
                >
                  <span class="lucide-code size-3.5" aria-hidden="true" />
                </a>
                <button
                  type="button"
                  class="rounded p-1 hover:bg-surface-gray-2"
                  :title="__('Nova Pasta')"
                  @click="startExplorerRootFolder"
                >
                  <span class="lucide-folder-plus size-3.5" aria-hidden="true" />
                </button>
                <FileUploader :uploadArgs="{ folder: 'Home' }" @success="loadExplorerRoot">
                  <template #default="{ openFileSelector }">
                    <button
                      type="button"
                      class="rounded p-1 hover:bg-surface-gray-2"
                      :title="__('Enviar Arquivo')"
                      @click="openFileSelector"
                    >
                      <span class="lucide-upload size-3.5" aria-hidden="true" />
                    </button>
                  </template>
                </FileUploader>
              </div>
            </div>

            <div
              v-if="creatingExplorerRootFolder"
              class="flex items-center gap-1.5 py-1 pl-2"
            >
              <span class="lucide-folder size-4 shrink-0" aria-hidden="true" />
              <input
                ref="explorerRootFolderInputRef"
                v-model="explorerRootFolderName"
                type="text"
                class="form-input w-32 text-p-sm"
                :placeholder="__('Nome da pasta')"
                @keydown.enter="confirmExplorerRootFolder"
                @keydown.esc="creatingExplorerRootFolder = false"
                @blur="confirmExplorerRootFolder"
              />
            </div>

            <div v-if="loadingExplorerRoot" class="px-2 py-1 text-p-sm">
              {{ __('Carregando...') }}
            </div>
            <FileTreeNode
              v-for="node in explorerRootNodes"
              :key="node.name"
              :node="node"
              :depth="0"
            />
            <div
              v-if="!loadingExplorerRoot && !explorerRootNodes.length && !creatingExplorerRootFolder"
              class="px-2 py-1 text-p-sm italic opacity-80"
            >
              {{ __('Nenhum arquivo ainda') }}
            </div>
          </div>
        </div>

        <div v-if="!mobile" class="mt-auto flex flex-col gap-1 pt-2">
          <div class="mb-1 flex flex-col gap-2">
            <SignupBanner
              v-if="isDemoSite"
              :isSidebarCollapsed="isCollapsed"
              :afterSignup="() => capture('signup_from_demo_site')"
            />
            <TrialBanner
              v-if="isFCSite"
              :isSidebarCollapsed="isCollapsed"
              :afterUpgrade="() => capture('upgrade_plan_from_trial_banner')"
            />
          </div>
          <SidebarItem
            v-if="isManager() && isDemoDataCreated"
            :label="__('Clear Demo Data')"
            class="!text-ink-red-6 hover:!bg-surface-red-2"
            @click="() => clearDemoData()"
          >
            <template #prefix>
              <BrushCleaningIcon class="size-4" />
            </template>
          </SidebarItem>
          <SidebarItem
            v-if="!isVisaoGeralSection"
            :label="isCollapsed ? __('Expand') : __('Collapse')"
            @click="isSidebarCollapsed = !isSidebarCollapsed"
          >
            <template #prefix>
              <CollapseSidebar
                class="size-4 text-ink-gray-7 duration-300 ease-in-out"
                :class="{ '[transform:rotateY(180deg)]': isCollapsed }"
              />
            </template>
          </SidebarItem>
        </div>
      </div>
    </Sidebar>
  </div>

  <template v-if="!mobile">
    <Settings />
    <HelpModal
      v-if="showHelpModal"
      v-model="showHelpModal"
      v-model:articles="articles"
      :logo="CRMLogo"
      :afterSkip="(step) => capture('onboarding_step_skipped_' + step)"
      :afterSkipAll="() => capture('onboarding_steps_skipped')"
      :afterReset="(step) => capture('onboarding_step_reset_' + step)"
      :afterResetAll="() => capture('onboarding_steps_reset')"
      docsLink="https://docs.frappe.io/crm"
    />
    <IntermediateStepModal
      v-model="showIntermediateModal"
      :currentStep="currentStep"
    />
  </template>
</template>

<script setup>
import BrushCleaningIcon from '~icons/lucide/brush-cleaning'
import AccountsIcon from '~icons/lucide/building-2'
import TeamIcon from '~icons/lucide/users'
import TargetIcon from '~icons/lucide/target'
import ProspectIcon from '~icons/lucide/radar'
import ReportIcon from '~icons/lucide/bar-chart-3'
import CalculatorIcon from '~icons/lucide/calculator'
import ReceiptIcon from '~icons/lucide/receipt'
import RepeatIcon from '~icons/lucide/repeat'
import HeartPulseIcon from '~icons/lucide/heart-pulse'
import EstimatorIcon from '~icons/lucide/ruler'
import InstagramIcon from '@/components/Icons/InstagramIcon.vue'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import CRMLogo from '@/components/Icons/CRMLogo.vue'
import InviteIcon from '@/components/Icons/InviteIcon.vue'
import ConvertIcon from '@/components/Icons/ConvertIcon.vue'
import CommentIcon from '@/components/Icons/CommentIcon.vue'
import EmailIcon from '@/components/Icons/EmailIcon.vue'
import StepsIcon from '@/components/Icons/StepsIcon.vue'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import Icon from '@/components/Icon.vue'
import PinIcon from '@/components/Icons/PinIcon.vue'
import UserDropdown from '@/components/UserDropdown.vue'
import SquareAsterisk from '@/components/Icons/SquareAsterisk.vue'
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import MoneyIcon from '@/components/Icons/MoneyIcon.vue'
import DealsIcon from '@/components/Icons/DealsIcon.vue'
import ContactsIcon from '@/components/Icons/ContactsIcon.vue'
import OrganizationsIcon from '@/components/Icons/OrganizationsIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import CollapseSidebar from '@/components/Icons/CollapseSidebar.vue'
import Settings from '@/components/Settings/Settings.vue'
import { viewsStore } from '@/stores/views'
import { usersStore } from '@/stores/users'
import { sessionStore } from '@/stores/session'
import {
  showSettings,
  activeSettingsPage,
  mobileSidebarOpened,
} from '@/composables/settings'
import { showChangePasswordModal } from '@/composables/modals'
import { useBroadcast } from '@/composables/useBroadcast.js'
import { call, Sidebar, SidebarItem, SidebarLabel, Tooltip, FileUploader, toast } from 'frappe-ui'
import FileTreeNode from '@/components/FileTreeNode.vue'
import {
  SignupBanner,
  TrialBanner,
  HelpModal,
  useOnboarding,
  showHelpModal,
  minimize,
  IntermediateStepModal,
  useTelemetry,
} from 'frappe-ui/frappe'
import router from '@/router'
import { useStorage } from '@vueuse/core'
import { useDemoData } from '@/composables/demoData'
import { ref, reactive, computed, markRaw, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  mobile: { type: Boolean, default: false },
})

const route = useRoute()

// Meu Site and Instagram are full-page, single-destination views (like
// Dashboard/Financeiro used to be) with no contextual nav list of their
// own, so this column would otherwise render as an empty white strip
// next to them.
const HIDDEN_SIDEBAR_ROUTES = ['MeuSite', 'Instagram']
const showSidebarColumn = computed(
  () => !HIDDEN_SIDEBAR_ROUTES.includes(route.name),
)

const { getPinnedViews, getPublicViews } = viewsStore()
const { capture } = useTelemetry()
const { clearDemoData, isDemoDataCreated } = useDemoData()
const { send } = useBroadcast()

const isSidebarCollapsed = useStorage('isSidebarCollapsed', false)

// The mobile drawer pins the sidebar open, so it is never visually collapsed
// even when the stored rail state says otherwise.
// Na Visão Geral a barra lateral é o explorador de arquivos: fica sempre aberta.
const sidebarCollapsedModel = computed({
  get: () => isSidebarCollapsed.value && route.name !== 'Dashboard',
  set: (v) => {
    if (route.name !== 'Dashboard') isSidebarCollapsed.value = v
  },
})
const isCollapsed = computed(() => sidebarCollapsedModel.value && !props.mobile)

const isFCSite = ref(window.is_fc_site)
const isDemoSite = ref(window.is_demo_site)

// Only the classic CRM routes (Leads, Deals, Contacts...) show this nav list —
// Dashboard, Instagram and Financeiro moved to the horizontal TopNav and are
// each a single destination, so they don't need a sidebar list under them.
const CRM_ROUTE_NAMES = [
  'Leads',
  'Lead',
  'Deals',
  'Deal',
  'Notes',
  'Tasks',
  'Contacts',
  'Contact',
  'Organizations',
  'Organization',
  'Call Logs',
  'Calendar',
  'Contas',
  'WhatsApp',
  'Equipe',
  'Prospeccao',
]
const isCrmSection = computed(() => CRM_ROUTE_NAMES.includes(route.name))

// The Financeiro tab gets its own small, fixed sidebar (Honorários, Metas,
// and whatever else lands under it) instead of the CRM saved-views list.
const FINANCEIRO_ROUTE_NAMES = [
  'Financeiro',
  'Financeiro Despesas',
  'Financeiro Recorrencia',
  'Financeiro Metas',
  'Financeiro Relatorios',
  'Financeiro Saude',
  'Financeiro Calculadora',
  'Financeiro Estimador',
]
const isFinanceiroSection = computed(() =>
  FINANCEIRO_ROUTE_NAMES.includes(route.name),
)
const financeiroLinks = [
  {
    label: 'Honorários',
    icon: MoneyIcon,
    key: 'Financeiro',
    to: { name: 'Financeiro' },
  },
  {
    label: 'Despesas',
    icon: ReceiptIcon,
    key: 'Financeiro Despesas',
    to: { name: 'Financeiro Despesas' },
  },
  {
    label: 'Recorrência',
    icon: RepeatIcon,
    key: 'Financeiro Recorrencia',
    to: { name: 'Financeiro Recorrencia' },
  },
  {
    label: 'Metas',
    icon: TargetIcon,
    key: 'Financeiro Metas',
    to: { name: 'Financeiro Metas' },
  },
  {
    label: 'Relatórios',
    icon: ReportIcon,
    key: 'Financeiro Relatorios',
    to: { name: 'Financeiro Relatorios' },
  },
  {
    label: 'Saúde Financeira',
    icon: HeartPulseIcon,
    key: 'Financeiro Saude',
    to: { name: 'Financeiro Saude' },
  },
  {
    label: 'Calculadora',
    icon: CalculatorIcon,
    key: 'Financeiro Calculadora',
    to: { name: 'Financeiro Calculadora' },
  },
  {
    label: 'Estimador de Projeto',
    icon: EstimatorIcon,
    key: 'Financeiro Estimador',
    to: { name: 'Financeiro Estimador' },
  },
]

// Visão Geral: a VS Code-style file explorer lives directly in the sidebar
// rail instead of the main content area — same pattern as the Financeiro
// sub-nav above, just backed by Frappe's own File/Folder API instead of a
// static link list.
const isVisaoGeralSection = computed(() => route.name === 'Dashboard')

// Opens the local MazyOS project folder in VS Code via its custom URI
// scheme — only meaningful on this machine/dev setup, not something a
// resold client CRM would carry over.
const vscodeUri = 'vscode://file/C:/Users/THIAGO/Desktop/MazyOS'

const explorerRootNodes = ref([])
const loadingExplorerRoot = ref(false)
const creatingExplorerRootFolder = ref(false)
const explorerRootFolderName = ref('')
const explorerRootFolderInputRef = ref(null)

async function loadExplorerRoot() {
  loadingExplorerRoot.value = true
  try {
    const res = await call('frappe.core.api.file.get_files_in_folder', { folder: 'Home' })
    explorerRootNodes.value = (res?.files || []).slice().sort((a, b) => {
      if (a.is_folder !== b.is_folder) return a.is_folder ? -1 : 1
      return a.file_name.localeCompare(b.file_name)
    })
  } finally {
    loadingExplorerRoot.value = false
  }
}

async function startExplorerRootFolder() {
  creatingExplorerRootFolder.value = true
  explorerRootFolderName.value = ''
  await nextTick()
  explorerRootFolderInputRef.value?.focus()
}

async function confirmExplorerRootFolder() {
  if (!creatingExplorerRootFolder.value) return
  const name = explorerRootFolderName.value.trim()
  creatingExplorerRootFolder.value = false
  if (!name) return
  try {
    await call('frappe.core.api.file.create_new_folder', { file_name: name, folder: 'Home' })
    await loadExplorerRoot()
  } catch (e) {
    toast.error(e.messages?.[0] || __('Falha ao criar pasta'))
  }
}

watch(
  isVisaoGeralSection,
  (active) => {
    if (active && !explorerRootNodes.value.length) loadExplorerRoot()
  },
  { immediate: true },
)

// Coisas que só fazem sentido para a agência (CRM de advogado não mostra).
const isAgency = computed(() => (window.crm_profile || 'agencia') === 'agencia')

const links = [
  {
    label: 'Leads',
    icon: LeadsIcon,
    to: 'Leads',
  },
  {
    label: 'Prospecção',
    icon: ProspectIcon,
    to: 'Prospeccao',
    condition: () => isManager() && isAgency.value,
  },
  {
    label: 'Deals',
    icon: DealsIcon,
    to: 'Deals',
  },
  {
    label: 'Contacts',
    icon: ContactsIcon,
    to: 'Contacts',
  },
  {
    label: 'WhatsApp',
    icon: WhatsAppIcon,
    to: 'WhatsApp',
  },
  {
    label: 'Contas',
    icon: AccountsIcon,
    to: 'Contas',
    condition: () => isAgency.value,
  },
  {
    label: 'Equipe',
    icon: TeamIcon,
    to: 'Equipe',
  },
  {
    label: 'Tasks',
    icon: TaskIcon,
    to: 'Tasks',
  },
  {
    label: 'Calendar',
    icon: CalendarIcon,
    to: 'Calendar',
    condition: () => !props.mobile,
  },
]

const allViews = computed(() => {
  let _views = [
    {
      name: 'All Views',
      hideLabel: true,
      opened: true,
      views: links
        .filter((link) => {
          if (link.condition) {
            return link.condition()
          }
          return true
        })
        .map((link) => ({
          label: link.label,
          icon: link.icon,
          key: link.to,
          to: { name: link.to },
        })),
    },
  ]
  if (getPublicViews().length) {
    _views.push({
      name: 'Public Views',
      opened: true,
      views: parseView(getPublicViews()),
    })
  }

  if (getPinnedViews().length) {
    _views.push({
      name: 'Pinned Views',
      opened: true,
      views: parseView(getPinnedViews()),
    })
  }
  return _views
})

function parseView(views) {
  return views.map((view) => {
    return {
      label: view.label,
      icon: getIcon(view.route_name, view.icon),
      key: view.name,
      to: {
        name: view.route_name,
        params: { viewType: view.type || 'list' },
        query: { view: view.name },
      },
    }
  })
}

function getIcon(routeName, icon) {
  if (icon) return icon

  switch (routeName) {
    case 'Leads':
      return LeadsIcon
    case 'Financeiro':
      return MoneyIcon
    case 'Instagram':
      return InstagramIcon
    case 'Deals':
      return DealsIcon
    case 'Contacts':
      return ContactsIcon
    case 'Organizations':
      return OrganizationsIcon
    case 'Notes':
      return NoteIcon
    case 'Call Logs':
      return PhoneIcon
    default:
      return PinIcon
  }
}

// A saved view's key is its name; a plain nav item's key is its route name.
function currentRouteKey() {
  return route.query.view || route.name
}

// Set the highlight on click rather than waiting for the route, since route
// components are lazily imported and the first visit waits on a chunk fetch.
// Modified clicks open a new tab without navigating this one, so they must not
// move the highlight here.
const activeItem = ref(currentRouteKey())

function selectItem(event, key) {
  if (
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey ||
    event.button === 1
  ) {
    return
  }
  activeItem.value = key
  // Selecting the row for the route already open leaves the URL unchanged, so
  // the drawer's navigation watcher never fires. Close it here too.
  if (props.mobile) {
    mobileSidebarOpened.value = false
  }
}

watch(
  () => [route.name, route.query.view],
  () => (activeItem.value = currentRouteKey()),
)


// onboarding
const { user } = sessionStore()
const { users, isManager } = usersStore()
const { isOnboardingStepsCompleted, setUp } = useOnboarding('frappecrm')

async function getFirstLead() {
  let firstLead = localStorage.getItem('firstLead' + user)
  if (firstLead) return firstLead
  return await call('crm.api.onboarding.get_first_lead')
}

async function getFirstDeal() {
  let firstDeal = localStorage.getItem('firstDeal' + user)
  if (firstDeal) return firstDeal
  return await call('crm.api.onboarding.get_first_deal')
}

const showIntermediateModal = ref(false)
const currentStep = ref({})

const steps = reactive([
  {
    name: 'setup_your_password',
    title: __('Setup your password'),
    icon: markRaw(SquareAsterisk),
    completed: false,
    onClick: () => {
      minimize.value = true
      showChangePasswordModal.value = true
      capture('onboarding_step_clicked_setup_password')
    },
  },
  {
    name: 'create_first_lead',
    title: __('Create your first lead'),
    icon: markRaw(LeadsIcon),
    completed: false,
    onClick: () => {
      minimize.value = true
      router.push({ name: 'Leads' })
      send('trigger_lead_create', true)
      capture('onboarding_step_clicked_create_first_lead')
    },
  },
  {
    name: 'invite_your_team',
    title: __('Invite your team'),
    icon: markRaw(InviteIcon),
    completed: false,
    onClick: () => {
      minimize.value = true
      showSettings.value = true
      activeSettingsPage.value = 'Invite User'
      capture('onboarding_step_clicked_invite_your_team')
    },
    condition: () => isManager(),
  },
  {
    name: 'convert_lead_to_deal',
    title: __('Convert lead to deal'),
    icon: markRaw(ConvertIcon),
    completed: false,
    dependsOn: 'create_first_lead',
    onClick: async () => {
      minimize.value = true
      capture('onboarding_step_clicked_convert_lead_to_deal')
      currentStep.value = {
        title: __('Convert lead to deal'),
        buttonLabel: __('Convert'),
        videoURL: '/assets/crm/videos/convertToDeal.mov',
        onClick: async () => {
          showIntermediateModal.value = false
          currentStep.value = {}

          let lead = await getFirstLead()
          if (lead) {
            router.push({ name: 'Lead', params: { leadId: lead } })
          } else {
            router.push({ name: 'Leads' })
          }
        },
      }
      showIntermediateModal.value = true
    },
  },
  {
    name: 'create_first_task',
    title: __('Create your first task'),
    icon: markRaw(TaskIcon),
    completed: false,
    onClick: async () => {
      minimize.value = true
      let deal = await getFirstDeal()
      capture('onboarding_step_clicked_create_first_task')

      if (deal) {
        router.push({
          name: 'Deal',
          params: { dealId: deal },
          hash: '#tasks',
        })
      } else {
        router.push({ name: 'Tasks' })
      }
    },
  },
  {
    name: 'create_first_note',
    title: __('Create your first note'),
    icon: markRaw(NoteIcon),
    completed: false,
    onClick: async () => {
      minimize.value = true
      let deal = await getFirstDeal()
      capture('onboarding_step_clicked_create_first_note')

      if (deal) {
        router.push({
          name: 'Deal',
          params: { dealId: deal },
          hash: '#notes',
        })
      } else {
        router.push({ name: 'Notes' })
      }
    },
  },
  {
    name: 'add_first_comment',
    title: __('Add your first comment'),
    icon: markRaw(CommentIcon),
    completed: false,
    dependsOn: 'create_first_lead',
    onClick: async () => {
      minimize.value = true
      let deal = await getFirstDeal()
      capture('onboarding_step_clicked_add_first_comment')

      if (deal) {
        router.push({
          name: 'Deal',
          params: { dealId: deal },
          hash: '#comments',
        })
      } else {
        router.push({ name: 'Leads' })
      }
    },
  },
  {
    name: 'send_first_email',
    title: __('Send email'),
    icon: markRaw(EmailIcon),
    completed: false,
    dependsOn: 'create_first_lead',
    onClick: async () => {
      minimize.value = true
      let deal = await getFirstDeal()
      capture('onboarding_step_clicked_send_first_email')

      if (deal) {
        router.push({
          name: 'Deal',
          params: { dealId: deal },
          hash: '#emails',
        })
      } else {
        router.push({ name: 'Leads' })
      }
    },
  },
  {
    name: 'change_deal_status',
    title: __('Change deal status'),
    icon: markRaw(StepsIcon),
    completed: false,
    dependsOn: 'convert_lead_to_deal',
    onClick: async () => {
      minimize.value = true
      capture('onboarding_step_clicked_change_deal_status')

      currentStep.value = {
        title: __('Change deal status'),
        buttonLabel: __('Change'),
        videoURL: '/assets/crm/videos/changeDealStatus.mov',
        onClick: async () => {
          showIntermediateModal.value = false
          currentStep.value = {}

          let deal = await getFirstDeal()
          if (deal) {
            router.push({
              name: 'Deal',
              params: { dealId: deal },
              hash: '#activity',
            })
          } else {
            router.push({ name: 'Leads' })
          }
        },
      }
      showIntermediateModal.value = true
    },
  },
])

onMounted(async () => {
  if (props.mobile) return

  await users.promise

  const filteredSteps = steps.filter((step) => {
    if (step.condition) {
      return step.condition()
    }
    return true
  })

  setUp(filteredSteps)
  // setUp() force-opens the Help/onboarding panel ("Welcome to Frappe CRM" +
  // steps checklist) on every mount for any user who hasn't completed it —
  // not something a resold law-firm CRM should show. Suppress that auto-open;
  // the panel is still reachable normally once onboarding tracking is used
  // elsewhere.
  showHelpModal.value = false
})

// help center
const articles = ref([
  {
    title: __('Introduction'),
    opened: false,
    subArticles: [
      { name: 'introduction', title: __('Introduction') },
      { name: 'setting-up', title: __('Setting Up') },
    ],
  },
  {
    title: __('Settings'),
    opened: false,
    subArticles: [
      { name: 'profile', title: __('Profile') },
      { name: 'custom-branding', title: __('Custom Branding') },
      { name: 'home-actions', title: __('Home Actions') },
      { name: 'invite-users', title: __('Invite Users') },
    ],
  },
  {
    title: __('Masters'),
    opened: false,
    subArticles: [
      { name: 'lead', title: __('Lead') },
      { name: 'deal', title: __('Deal') },
      { name: 'contact', title: __('Contact') },
      { name: 'organization', title: __('Organization') },
      { name: 'note', title: __('Note') },
      { name: 'task', title: __('Task') },
      { name: 'call-log', title: __('Call Log') },
      { name: 'email-template', title: __('Email Template') },
    ],
  },
  {
    title: __('Capturing Leads'),
    opened: false,
    subArticles: [{ name: 'web-form', title: __('Web Form') }],
  },
  {
    title: __('Views'),
    opened: false,
    subArticles: [
      { name: 'view', title: __('Saved View') },
      { name: 'public-view', title: __('Public View') },
      { name: 'pinned-view', title: __('Pinned View') },
    ],
  },
  {
    title: __('Other Features'),
    opened: false,
    subArticles: [
      { name: 'email-communication', title: __('Email Communication') },
      { name: 'comment', title: __('Comment') },
      { name: 'data', title: __('Data') },
      { name: 'service-level-agreement', title: __('Service Level Agreement') },
      { name: 'assignment-rule', title: __('Assignment Rule') },
      { name: 'notification', title: __('Notification') },
    ],
  },
  {
    title: __('Customization'),
    opened: false,
    subArticles: [
      { name: 'custom-fields', title: __('Custom Fields') },
      { name: 'custom-actions', title: __('Custom Actions') },
      { name: 'custom-statuses', title: __('Custom Statuses') },
      { name: 'custom-list-actions', title: __('Custom List Actions') },
      { name: 'quick-entry-layout', title: __('Quick Entry Layout') },
    ],
  },
  {
    title: __('Integration'),
    opened: false,
    subArticles: [
      { name: 'twilio', title: __('Twilio') },
      { name: 'exotel', title: __('Exotel') },
      { name: 'whatsapp', title: __('WhatsApp') },
      { name: 'erpnext', title: __('ERPNext') },
    ],
  },
  {
    title: __('Frappe CRM mobile'),
    opened: false,
    subArticles: [
      { name: 'mobile-app-installation', title: __('Mobile App Installation') },
    ],
  },
])
</script>
