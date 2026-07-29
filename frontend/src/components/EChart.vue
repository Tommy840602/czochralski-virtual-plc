<script setup>
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import { use, init } from 'echarts/core'
import { BarChart, BoxplotChart, LineChart, PieChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { chartTheme } from '@/composables/theme'

// 僅註冊工程分析實際使用的圖表與元件，避免把整套 ECharts 打進瀏覽器。
use([
  BarChart,
  BoxplotChart,
  LineChart,
  PieChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
])

// 對 ECharts 的薄封裝：圖表「外框」（文字/軸/格線/tooltip）由當前主題決定，
// 主題切換時 chartTheme 變動 → 重繪。各 view 的 series 用色也讀自 chartTheme。
const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '380px' },
})

const el = shallowRef(null)
let chart = null
let observer = null

function base() {
  const t = chartTheme.value
  return {
    backgroundColor: 'transparent',
    textStyle: { color: t.text, fontFamily: 'inherit' },
    grid: { left: 52, right: 24, top: 40, bottom: 48, containLabel: true },
    tooltip: {
      backgroundColor: t.ttBg,
      borderColor: t.ttBorder,
      textStyle: { color: t.textStrong },
    },
  }
}

function render() {
  if (!chart) return
  chart.setOption({ ...base(), ...props.option }, true)
}

onMounted(() => {
  chart = init(el.value, null, { renderer: 'canvas' })
  render()
  observer = new ResizeObserver(() => chart && chart.resize())
  observer.observe(el.value)
})

watch([() => props.option, chartTheme], render, { deep: true })

onBeforeUnmount(() => {
  observer && observer.disconnect()
  chart && chart.dispose()
})
</script>

<template>
  <div ref="el" class="chart" :style="{ height }" />
</template>
