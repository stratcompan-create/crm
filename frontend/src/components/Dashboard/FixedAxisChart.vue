<!--
  Thin wrapper around frappe-ui's AxisChart that fixes an upstream legend
  bug: `eChartOptions.ts` hardcodes `legend.textStyle.padding` to
  `[0, 0, 0, -5]` — a small negative left offset that was fine for short
  English series names, but shifts each label left enough to overlap the
  previous legend item once labels run longer (e.g. translated to
  Portuguese). We can't patch frappe-ui's own node_modules durably (it
  gets reinstalled on every `yarn install` / deploy), so this recomputes
  the same options via the publicly exported `useAxisChartOptions` hook
  and corrects just the broken padding before handing off to ECharts.
-->
<template>
  <ECharts :options="options" :error="error" />
</template>

<script setup>
import { computed, ref } from 'vue'
import { ECharts, useAxisChartOptions } from 'frappe-ui'

const props = defineProps({ config: { type: Object, required: true } })

const error = ref('')
const options = computed(() => {
  try {
    const config = {
      ...props.config,
      dir:
        props.config.dir ??
        (typeof document !== 'undefined' &&
        document.documentElement.dir === 'rtl'
          ? 'rtl'
          : 'ltr'),
    }
    const opts = useAxisChartOptions(config)
    if (opts.legend) {
      opts.legend = {
        ...opts.legend,
        itemGap: 20,
        textStyle: { ...opts.legend.textStyle, padding: [0, 0, 0, 0] },
      }
    }
    return opts
  } catch (e) {
    error.value = e.message
    return {}
  }
})
</script>
