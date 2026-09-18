<template>
  <LayoutHeader>
    <template #left-header>
      <div class="text-lg font-semibold text-ink-gray-9">{{ __('Calculadora') }}</div>
    </template>
  </LayoutHeader>

  <div class="flex flex-1 items-start justify-center overflow-y-auto p-8">
    <div class="w-full max-w-xs rounded-xl border border-outline-gray-2 bg-surface-white p-4 shadow-sm">
      <!-- Visor -->
      <div class="mb-4 rounded-lg bg-surface-gray-1 px-4 py-5 text-right">
        <div class="truncate text-p-sm text-ink-gray-5">{{ expression || ' ' }}</div>
        <div class="truncate text-3xl font-semibold text-ink-gray-9">{{ display }}</div>
      </div>

      <!-- Botões -->
      <div class="grid grid-cols-4 gap-2">
        <button class="calc-btn calc-btn-muted col-span-2" @click="clearAll">{{ __('C') }}</button>
        <button class="calc-btn calc-btn-muted" @click="backspace">⌫</button>
        <button class="calc-btn calc-btn-op" @click="chooseOperator('÷')">÷</button>

        <button class="calc-btn" @click="inputDigit('7')">7</button>
        <button class="calc-btn" @click="inputDigit('8')">8</button>
        <button class="calc-btn" @click="inputDigit('9')">9</button>
        <button class="calc-btn calc-btn-op" @click="chooseOperator('×')">×</button>

        <button class="calc-btn" @click="inputDigit('4')">4</button>
        <button class="calc-btn" @click="inputDigit('5')">5</button>
        <button class="calc-btn" @click="inputDigit('6')">6</button>
        <button class="calc-btn calc-btn-op" @click="chooseOperator('-')">-</button>

        <button class="calc-btn" @click="inputDigit('1')">1</button>
        <button class="calc-btn" @click="inputDigit('2')">2</button>
        <button class="calc-btn" @click="inputDigit('3')">3</button>
        <button class="calc-btn calc-btn-op" @click="chooseOperator('+')">+</button>

        <button class="calc-btn col-span-2" @click="inputDigit('0')">0</button>
        <button class="calc-btn" @click="inputDecimal">,</button>
        <button class="calc-btn calc-btn-equals" @click="calculate">=</button>
      </div>
    </div>
  </div>
</template>
<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { ref } from 'vue'

const display = ref('0')
const expression = ref('')
const previousValue = ref(null)
const pendingOperator = ref(null)
const waitingForNewValue = ref(false)

function inputDigit(digit) {
  if (waitingForNewValue.value) {
    display.value = digit
    waitingForNewValue.value = false
  } else {
    display.value = display.value === '0' ? digit : display.value + digit
  }
}

function inputDecimal() {
  if (waitingForNewValue.value) {
    display.value = '0,'
    waitingForNewValue.value = false
    return
  }
  if (!display.value.includes(',')) {
    display.value += ','
  }
}

function toNumber(str) {
  return parseFloat(str.replace(',', '.')) || 0
}

function formatNumber(num) {
  // Avoid ugly floating point tails (0.1 + 0.2 = 0.30000000000004) while
  // still allowing decimals the user actually typed.
  const rounded = Math.round(num * 1e10) / 1e10
  return String(rounded).replace('.', ',')
}

function operate(a, b, op) {
  switch (op) {
    case '+':
      return a + b
    case '-':
      return a - b
    case '×':
      return a * b
    case '÷':
      return b === 0 ? 0 : a / b
    default:
      return b
  }
}

function chooseOperator(op) {
  const current = toNumber(display.value)

  if (pendingOperator.value !== null && !waitingForNewValue.value) {
    const result = operate(previousValue.value, current, pendingOperator.value)
    display.value = formatNumber(result)
    previousValue.value = result
  } else {
    previousValue.value = current
  }

  expression.value = `${formatNumber(previousValue.value)} ${op}`
  pendingOperator.value = op
  waitingForNewValue.value = true
}

function calculate() {
  if (pendingOperator.value === null) return
  const current = toNumber(display.value)
  const result = operate(previousValue.value, current, pendingOperator.value)

  expression.value = `${formatNumber(previousValue.value)} ${pendingOperator.value} ${formatNumber(current)} =`
  display.value = formatNumber(result)
  previousValue.value = null
  pendingOperator.value = null
  waitingForNewValue.value = true
}

function backspace() {
  if (display.value.length <= 1 || waitingForNewValue.value) {
    display.value = '0'
    return
  }
  display.value = display.value.slice(0, -1) || '0'
}

function clearAll() {
  display.value = '0'
  expression.value = ''
  previousValue.value = null
  pendingOperator.value = null
  waitingForNewValue.value = false
}
</script>

<style scoped>
.calc-btn {
  border-radius: 0.5rem;
  padding: 0.85rem 0;
  font-size: 1.1rem;
  font-weight: 500;
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-8, #1f2937);
  transition: transform 0.1s ease, background 0.15s ease;
}
.calc-btn:hover {
  background: var(--surface-gray-3, #e5e7eb);
}
.calc-btn:active {
  transform: scale(0.93);
}
.calc-btn-muted {
  background: var(--surface-gray-1, #f9fafb);
  color: var(--ink-gray-6, #4b5563);
}
.calc-btn-op {
  background: #eef1f1;
  color: #4a5c62;
  font-weight: 600;
}
.calc-btn-op:hover {
  background: #dfe5e6;
}
.calc-btn-equals {
  background: var(--stratcompany-accent, #8aa1a9);
  color: white;
  font-weight: 600;
}
.calc-btn-equals:hover {
  filter: brightness(0.9);
}
</style>
