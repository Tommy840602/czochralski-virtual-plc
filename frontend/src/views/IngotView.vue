<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { GROUP_LABELS, fmt, fmtTime, endedByLabel } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const props = defineProps({ ingotNo: { type: String, required: true } })

// 相位色帶：低透明度，日夜皆可讀
const PHASE_ALPHA = {
  NECK: 'rgba(91,155,209,0.12)',
  CROWN: 'rgba(214,154,76,0.12)',
  BODY: 'rgba(79,174,116,0.11)',
  TAIL: 'rgba(215,106,99,0.12)',
}

const meta = useAsync(() => api.meta())
const detail = useAsync(() => api.ingotDetail(props.ingotNo))

const selected = ref(['D_mean', 'Heater Power SV', 'Seed lift'])
const segmentSeq = ref(null)

const series = useAsync(
  () =>
    api.series(props.ingotNo, {
      signal: selected.value,
      segmentSeq: segmentSeq.value ?? undefined,
    }),
  { immediate: false },
)

watch([selected, segmentSeq], () => series.run(), { deep: true, immediate: true })

function toggleSignal(name) {
  const i = selected.value.indexOf(name)
  if (i >= 0) {
    if (selected.value.length > 1) selected.value = selected.value.filter((s) => s !== name)
  } else if (selected.value.length < 6) {
    selected.value = [...selected.value, name]
  }
}

const chartOption = computed(() => {
  const s = series.data.value
  if (!s) return {}
  const t = chartTheme.value
  const colors = t.series

  // 每個訊號一條線、各自獨立 y 軸（量綱差異大），共用時間 x 軸
  const yAxes = s.series.map((sig, i) => ({
    type: 'value',
    show: i < 2, // 只畫前兩個軸避免壅塞，其餘靠 tooltip
    position: i === 0 ? 'left' : 'right',
    axisLine: { lineStyle: { color: colors[i % colors.length] } },
    splitLine: { show: i === 0, lineStyle: { color: t.grid } },
    scale: true,
  }))

  const lines = s.series.map((sig, i) => ({
    name: sig.name,
    type: 'line',
    yAxisIndex: i,
    showSymbol: false,
    lineStyle: { width: 1.3, color: colors[i % colors.length] },
    data: sig.points,
  }))

  // 製程階段色帶：用 markArea 疊在第一條線上
  const bands = (s.modes || [])
    .filter((m) => m.phase)
    .map((m) => [
      { xAxis: m.start, itemStyle: { color: PHASE_ALPHA[m.phase] } },
      { xAxis: m.end },
    ])
  if (lines.length && bands.length) {
    lines[0].markArea = { silent: true, data: bands }
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      valueFormatter: (v) => (v == null ? '—' : Number(v).toFixed(2)),
    },
    legend: { data: s.series.map((x) => x.name), textStyle: { color: t.text }, top: 4 },
    grid: { left: 60, right: 60, top: 44, bottom: 60 },
    xAxis: { type: 'time', axisLine: { lineStyle: { color: t.axis } } },
    yAxis: yAxes,
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 18, bottom: 24, borderColor: t.axis },
    ],
    series: lines,
  }
})

const phaseLegend = computed(() => Object.entries(PHASE_ALPHA))
</script>

<template>
  <div class="page-head">
    <RouterLink to="/explore" class="muted" style="font-size: 13px">← 返回列表</RouterLink>
    <h2 style="margin-top: 6px">
      <span class="mono">{{ ingotNo }}</span>
      <span
        v-if="detail.data.value"
        class="badge"
        :class="detail.data.value.meta.GROUP"
        style="margin-left: 10px; vertical-align: middle"
      >
        {{ GROUP_LABELS[detail.data.value.meta.GROUP] }}
      </span>
    </h2>
  </div>

  <StateBlock :loading="detail.loading.value" :error="detail.error.value">
    <div v-if="detail.data.value" class="grid" style="grid-template-columns: 1fr; gap: 14px">
      <!-- 頂部資訊卡 -->
      <div class="stat-row">
        <div class="stat">
          <div class="label">爐台</div>
          <div class="value" style="font-size: 20px">
            {{ detail.data.value.meta.DATABASE_NAME.replace('Furnace_', '') }}
          </div>
          <div class="sub">{{ fmtTime(detail.data.value.meta.CREATETIME) }}</div>
        </div>
        <div class="stat">
          <div class="label">通過型態</div>
          <div class="value" style="font-size: 20px">
            {{ detail.data.value.meta.IS_MULTI_PASS ? '多次' : '單次' }}
          </div>
          <div class="sub">嘗試 {{ fmt(detail.data.value.meta.ATTEMPT_COUNT, 0) }} 次</div>
        </div>
        <div class="stat">
          <div class="label">一般故障</div>
          <div class="value" style="font-size: 20px">
            {{ fmt(detail.data.value.meta.GENERAL_FAULT_COUNT, 0) }}
          </div>
          <div class="sub">
            製程 {{ fmt(detail.data.value.meta.PROCESS_FAULT_COUNT, 0) }} · 設備
            {{ fmt(detail.data.value.meta.EQUIPMENT_FAULT_COUNT, 0) }}
          </div>
        </div>
        <div class="stat">
          <div class="label">切段數</div>
          <div class="value" style="font-size: 20px">
            {{ detail.data.value.segments.length }}
          </div>
          <div class="sub">
            斷線
            {{ detail.data.value.segments.filter((x) => x.ENDED_BY === 'BREAK').length }}
            段
          </div>
        </div>
      </div>

      <!-- 訊號選擇 -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px">
          <h3 style="margin: 0; font-size: 14px">時序訊號（可選 1–6 條）</h3>
          <div class="muted" style="font-size: 12px">
            <template v-for="([ph, col]) in phaseLegend" :key="ph">
              <span :style="{ background: col.replace(/0\.1[12]?/, '0.4'), padding: '1px 7px', borderRadius: '3px', marginLeft: '6px' }">{{ ph }}</span>
            </template>
          </div>
        </div>
        <div v-for="grp in meta.data.value?.signalGroups || []" :key="grp.group" style="margin-bottom: 8px">
          <div class="muted" style="font-size: 11px; margin-bottom: 4px">{{ grp.group }}</div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px">
            <div
              v-for="sig in grp.signals"
              :key="sig"
              class="chip"
              :class="{ active: selected.includes(sig) }"
              @click="toggleSignal(sig)"
            >
              {{ sig }}
            </div>
          </div>
        </div>
      </div>

      <!-- 主圖 -->
      <div class="card">
        <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 6px">
          <select v-model="segmentSeq">
            <option :value="null">全程</option>
            <option v-for="seg in detail.data.value.segments" :key="seg.SEGMENT_SEQ" :value="seg.SEGMENT_SEQ">
              段{{ seg.SEGMENT_SEQ }} · {{ seg.PHASE }} · {{ endedByLabel(seg.ENDED_BY) }}
            </option>
          </select>
          <span v-if="series.data.value" class="muted" style="font-size: 12px">
            {{ fmt(series.data.value.totalPoints, 0) }} 點（顯示上限 {{ series.data.value.maxPoints }}）
          </span>
        </div>
        <StateBlock :loading="series.loading.value" :error="series.error.value">
          <EChart v-if="series.data.value" :option="chartOption" height="420px" />
        </StateBlock>
      </div>

      <!-- 切段表 -->
      <div class="card scroll-x">
        <h3 style="margin-top: 0; font-size: 14px">製程切段</h3>
        <table>
          <thead>
            <tr>
              <th>段</th><th>Pass</th><th>階段</th><th>起</th><th>迄</th>
              <th>時長(分)</th><th>結束方式</th><th>故障數</th><th>乾淨</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="seg in detail.data.value.segments"
              :key="seg.SEGMENT_SEQ"
              :class="{ selected: segmentSeq === seg.SEGMENT_SEQ }"
              @click="segmentSeq = seg.SEGMENT_SEQ"
            >
              <td>{{ seg.SEGMENT_SEQ }}</td>
              <td>{{ seg.PASS_SEQ }}</td>
              <td>{{ seg.PHASE }}</td>
              <td class="muted">{{ fmtTime(seg.START_TIME) }}</td>
              <td class="muted">{{ fmtTime(seg.END_TIME) }}</td>
              <td>{{ fmt(seg.DURATION_MIN, 1) }}</td>
              <td>
                <span
                  class="badge"
                  :class="seg.ENDED_BY === 'BREAK' ? 'danger' : seg.ENDED_BY === 'COMPLETE' ? 'ok' : 'dim'"
                >{{ endedByLabel(seg.ENDED_BY) }}</span>
              </td>
              <td>{{ seg.FAULT_COUNT }}</td>
              <td>
                <span v-if="seg.IS_CLEAN" class="badge ok">✓</span>
                <span v-else class="badge dim">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </StateBlock>
</template>
