// Ícones e cores dos blocos do Mapa de estratégia.
// As classes de ícone ficam escritas por extenso para o Tailwind gerar cada uma no build.
export const MAP_ICONS = [
  { name: 'megaphone', cls: 'lucide-megaphone' },
  { name: 'message-circle', cls: 'lucide-message-circle' },
  { name: 'camera', cls: 'lucide-camera' },
  { name: 'mail', cls: 'lucide-mail' },
  { name: 'phone', cls: 'lucide-phone' },
  { name: 'globe', cls: 'lucide-globe' },
  { name: 'search', cls: 'lucide-search' },
  { name: 'user', cls: 'lucide-user' },
  { name: 'users', cls: 'lucide-users' },
  { name: 'calendar', cls: 'lucide-calendar' },
  { name: 'clock', cls: 'lucide-clock' },
  { name: 'file-text', cls: 'lucide-file-text' },
  { name: 'folder-open', cls: 'lucide-folder-open' },
  { name: 'briefcase', cls: 'lucide-briefcase' },
  { name: 'scale', cls: 'lucide-scale' },
  { name: 'gavel', cls: 'lucide-gavel' },
  { name: 'target', cls: 'lucide-target' },
  { name: 'trending-up', cls: 'lucide-trending-up' },
  { name: 'layers', cls: 'lucide-layers' },
  { name: 'refresh-cw', cls: 'lucide-refresh-cw' },
  { name: 'dollar-sign', cls: 'lucide-dollar-sign' },
  { name: 'credit-card', cls: 'lucide-credit-card' },
  { name: 'shopping-cart', cls: 'lucide-shopping-cart' },
  { name: 'gift', cls: 'lucide-gift' },
  { name: 'heart', cls: 'lucide-heart' },
  { name: 'star', cls: 'lucide-star' },
  { name: 'check-circle', cls: 'lucide-check-circle' },
  { name: 'flag', cls: 'lucide-flag' },
  { name: 'lightbulb', cls: 'lucide-lightbulb' },
  { name: 'rocket', cls: 'lucide-rocket' },
  { name: 'zap', cls: 'lucide-zap' },
  { name: 'bell', cls: 'lucide-bell' },
  { name: 'circle', cls: 'lucide-circle' },
]

export const iconClass = (name) => (MAP_ICONS.find((i) => i.name === name) || MAP_ICONS[MAP_ICONS.length - 1]).cls

export const MAP_COLORS = {
  blue: { label: 'Azul', border: '#3b82f6', bg: '#eff6ff', ink: '#1d4ed8' },
  green: { label: 'Verde', border: '#22a06b', bg: '#ecfdf3', ink: '#146c43' },
  amber: { label: 'Laranja', border: '#e0900f', bg: '#fff7e6', ink: '#a15c00' },
  red: { label: 'Vermelho', border: '#dc4c4c', bg: '#fff0f0', ink: '#a12a2a' },
  purple: { label: 'Roxo', border: '#8b5cf6', bg: '#f5f0ff', ink: '#5b32b4' },
  gray: { label: 'Cinza', border: '#8a97a0', bg: '#f4f6f7', ink: '#42505a' },
  yellow: { label: 'Amarelo', border: '#e6c200', bg: '#fef3a6', ink: '#5b4b00' },
}

export const colorOf = (name) => MAP_COLORS[name] || MAP_COLORS.blue
