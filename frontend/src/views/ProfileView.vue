<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt, fmtPct, endedByLabel } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const confusion = useAsync(api.profileConfusion)
const onlyOoc = ref(true)
const scores = useAsync(() => api.profileScores({ onlyOoc: onlyOoc.value }), { immediate: false })
watch(onlyOoc, () => scores.run(), { immediate: true })

const selected = ref(null)
const profile = useAsync(
  () => api.profileIngot(selected.value.INGOT_NO, selected.value.SEGMENT_SEQ),
  { immediate: false },
)
watch(selected, (v) => v && profile.run())

watch(
  () => scores.data.value,
  (d) => {
    if (d && d.items.length && !selected.value) selected.value = d.items[0]
  },
)

// 包絡帶 + 實際輪廓疊圖
const profileOption = computed(() => {
  const p = profile.data.value
  if (!p) return {}
  const band = p.band
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : Number(v).toFixed(2)) },
    legend: { data: ['正常帶', '本段輪廓'], textStyle: { color: t.text }, top: 4 },
    grid: { left: 52, right: 24, top: 40, bottom: 44 },
    xAxis: {
      type: 'value', min: 0, max: 1, name: '製程進度',
      splitLine: { lineStyle: { color: t.grid } },
    },
    yAxis: { type: 'value', scale: true, name: p.signal, splitLine: { lineStyle: { color: t.grid } } },
    series: [
      // 下界 + (上界-下界) 堆疊成半透明帶
      {
        name: '正常帶', type: 'line', stack: 'band', showSymbol: false,
        lineStyle: { opacity: 0 }, data: band.map((b) => [b.u, b.lo]),
      },
      {
        name: '正常帶上界', type: 'line', stack: 'band', showSymbol: false,
        lineStyle: { opacity: 0 }, areaStyle: { color: t.band },
        data: band.map((b) => [b.u, b.hi - b.lo]),
      },
      {
        name: '平均', type: 'line', showSymbol: false,
        lineStyle: { color: t.series[3], type: 'dashed', width: 1 },
        data: band.map((b) => [b.u, b.mean]),
      },
      {
        name: '本段輪廓', type: 'line', showSymbol: false,
        lineStyle: { color: t.series[2], width: 1.8 },
        connectNulls: false,
        data: p.profile.map((x) => [x.u, x.value]),
      },
    ],
  }
})

const c = computed(() => confusion.data.value)
</script>

<template>
  <div class="page-head">
    <h2>輪廓監控</h2>
    <p>以正常製程的功率包絡帶偵測偏離；T² / SPE / LEVEL 管制越界即為 OOC</p>
  </div>

  <div class="grid" style="grid-template-columns: 1.1fr 1fr; gap: 14px; margin-bottom: 14px">
    <!-- 混淆矩陣 -->
    <div class="card">
      <h3 style="margin-top: 0; font-size: 14px">OOC 告警 vs. 實際斷線</h3>
      <StateBlock :loading="confusion.loading.value" :error="confusion.error.value">
        <div v-if="c" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px">
          <div class="stat" style="border-color: color-mix(in srgb, var(--ok) 45%, transparent)">
            <div class="label">命中（OOC ∧ 斷線）</div>
            <div class="value" style="color: var(--ok)">{{ c.truePositive }}</div>
          </div>
          <div class="stat" style="border-color: color-mix(in srgb, var(--warn) 45%, transparent)">
            <div class="label">誤報（OOC ∧ 未斷）</div>
            <div class="value" style="color: var(--warn)">{{ c.falsePositive }}</div>
          </div>
          <div class="stat" style="border-color: color-mix(in srgb, var(--danger) 45%, transparent)">
            <div class="label">漏報（未OOC ∧ 斷線）</div>
            <div class="value" style="color: var(--danger)">{{ c.falseNegative }}</div>
          </div>
          <div class="stat">
            <div class="label">正確排除</div>
            <div class="value muted">{{ c.trueNegative }}</div>
          </div>
        </div>
        <div v-if="c" class="muted" style="font-size: 12.5px; margin-top: 10px">
          精確率 {{ fmtPct(c.precision) }} · 召回率 {{ fmtPct(c.recall) }} · 母體斷線率 {{ fmtPct(c.breakRate) }}
          <div style="margin-top: 4px">
            高精確、低召回：越界必有問題，但多數斷線並不先觸發功率越界——單一輪廓指標覆蓋有限。
          </div>
        </div>
      </StateBlock>
    </div>

    <!-- OOC 列表 -->
    <div class="card scroll-x">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
        <h3 style="margin: 0; font-size: 14px">越界段落</h3>
        <label class="muted" style="font-size: 12px">
          <input type="checkbox" v-model="onlyOoc" /> 僅顯示 OOC
        </label>
      </div>
      <StateBlock :loading="scores.loading.value" :error="scores.error.value" :empty="scores.data.value?.items.length === 0">
        <table v-if="scores.data.value">
          <thead>
            <tr><th>晶棒</th><th>段</th><th>T²</th><th>SPE</th><th>結束</th></tr>
          </thead>
          <tbody>
            <tr
              v-for="row in scores.data.value.items.slice(0, 40)"
              :key="row.INGOT_NO + '-' + row.SEGMENT_SEQ"
              :class="{ selected: selected && selected.INGOT_NO === row.INGOT_NO && selected.SEGMENT_SEQ === row.SEGMENT_SEQ }"
              @click="selected = row"
            >
              <td class="mono">{{ row.INGOT_NO }}</td>
              <td>{{ row.SEGMENT_SEQ }}</td>
              <td>{{ fmt(row.T2, 2) }}</td>
              <td>{{ fmt(row.SPE, 1) }}</td>
              <td>
                <span class="badge" :class="row.ENDED_BY === 'BREAK' ? 'danger' : 'dim'">
                  {{ endedByLabel(row.ENDED_BY) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </StateBlock>
    </div>
  </div>

  <!-- 輪廓疊圖 -->
  <div class="card">
    <h3 style="margin-top: 0; font-size: 14px">
      功率輪廓對比
      <span v-if="profile.data.value" class="muted" style="font-weight: 400">
        · {{ profile.data.value.ingotNo }} 段{{ profile.data.value.segmentSeq }}
        （{{ profile.data.value.phase }}，越界比例 {{ fmtPct(profile.data.value.outsideRatio) }}）
      </span>
    </h3>
    <StateBlock :loading="profile.loading.value" :error="profile.error.value">
      <div v-if="profile.data.value">
        <div class="stat-row" style="margin-bottom: 10px">
          <div v-for="(lim, key) in profile.data.value.limits" :key="key" class="stat">
            <div class="label">{{ lim.label }}</div>
            <div class="value" style="font-size: 18px">
              {{ fmt(profile.data.value.score[key === 'LEVEL_RESID' ? 'LEVEL_RESID' : key], 2) }}
            </div>
            <div class="sub">界線 {{ fmt(lim.limit, 2) }}</div>
          </div>
        </div>
        <EChart :option="profileOption" height="360px" />
      </div>
    </StateBlock>
  </div>
</template>
