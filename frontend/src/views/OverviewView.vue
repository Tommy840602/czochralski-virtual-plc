<script setup>
import { computed } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { GROUP_LABELS, fmt, fmtPct } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const { data, loading, error } = useAsync(api.summary)

const GROUP_KEY = { g1: 0, g2: 1, g3: 2, g4: 3 }

const groupOption = computed(() => {
  const rows = data.value?.byGroup ?? []
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        itemStyle: { borderColor: t.bg, borderWidth: 2 },
        label: { color: t.textStrong, formatter: '{b}\n{c}' },
        data: rows.map((r) => ({
          name: GROUP_LABELS[r.GROUP] || r.GROUP,
          value: r.ingots,
          itemStyle: { color: t.series[GROUP_KEY[r.GROUP] ?? 0] },
        })),
      },
    ],
  }
})

const furnaceOption = computed(() => {
  const rows = data.value?.byFurnace ?? []
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['晶棒數', '異常數'], textStyle: { color: t.text }, top: 4 },
    xAxis: { type: 'category', data: rows.map((r) => r.DATABASE_NAME.replace('Furnace_', '')) },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { name: '晶棒數', type: 'bar', data: rows.map((r) => r.ingots), itemStyle: { color: t.series[0] } },
      { name: '異常數', type: 'bar', data: rows.map((r) => r.faults), itemStyle: { color: t.series[2] } },
    ],
  }
})

const phaseOption = computed(() => {
  const rows = data.value?.breaksByPhase ?? []
  const t = chartTheme.value
  const order = { NECK: 0, CROWN: 1, BODY: 2, TAIL: 3 }
  const sorted = [...rows].sort((a, b) => (order[a.phase] ?? 9) - (order[b.phase] ?? 9))
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: sorted.map((r) => r.phase) },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      {
        type: 'bar',
        data: sorted.map((r) => r.breaks),
        itemStyle: { color: t.series[1], borderRadius: [3, 3, 0, 0] },
        label: { show: true, position: 'top', color: t.text },
      },
    ],
  }
})

const faultRate = computed(() =>
  data.value ? data.value.faultIngots / data.value.totalIngots : 0,
)
const breakRate = computed(() =>
  data.value ? data.value.breakSegments / data.value.totalSegments : 0,
)
</script>

<template>
  <div class="page-head">
    <h2>總覽</h2>
    <p>全體晶棒與製程階段的分布概況</p>
  </div>

  <StateBlock :loading="loading" :error="error">
    <div class="stat-row" style="margin-bottom: 16px">
      <div class="stat">
        <div class="label">晶棒總數</div>
        <div class="value">{{ fmt(data.totalIngots, 0) }}</div>
      </div>
      <div class="stat">
        <div class="label">含異常晶棒</div>
        <div class="value">{{ fmt(data.faultIngots, 0) }}</div>
        <div class="sub">佔比 {{ fmtPct(faultRate) }}</div>
      </div>
      <div class="stat">
        <div class="label">製程切段總數</div>
        <div class="value">{{ fmt(data.totalSegments, 0) }}</div>
      </div>
      <div class="stat">
        <div class="label">斷線段數</div>
        <div class="value">{{ fmt(data.breakSegments, 0) }}</div>
        <div class="sub">佔比 {{ fmtPct(breakRate) }}</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 1.4fr">
      <div class="card">
        <h3 style="margin-top: 0; font-size: 14px">分組分布</h3>
        <EChart :option="groupOption" height="300px" />
      </div>
      <div class="card">
        <h3 style="margin-top: 0; font-size: 14px">各爐台晶棒與異常數</h3>
        <EChart :option="furnaceOption" height="300px" />
      </div>
    </div>

    <div class="card" style="margin-top: 14px">
      <h3 style="margin-top: 0; font-size: 14px">斷線發生的製程階段</h3>
      <EChart :option="phaseOption" height="260px" />
    </div>
  </StateBlock>
</template>
