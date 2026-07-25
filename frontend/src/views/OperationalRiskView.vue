<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt, fmtPct } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const board = useAsync(api.riskBoard)
const hazard = useAsync(api.riskHazardCurve)

const tierFilter = ref('all')
const selected = ref(null)

const ingot = useAsync(() => api.riskIngot(selected.value), { immediate: false })
watch(selected, (v) => v && ingot.run())

const TIER = { high: { label: '高', cls: 'danger' }, mid: { label: '中', cls: 'warn' }, low: { label: '低', cls: 'dim' } }

const filtered = computed(() => {
  const items = board.data.value?.items ?? []
  const rows = tierFilter.value === 'all' ? items : items.filter((r) => r.tier === tierFilter.value)
  return rows.slice(0, 60)
})

// 时间风险先验曲线
const hazardOption = computed(() => {
  const d = hazard.data.value
  if (!d) return {}
  const t = chartTheme.value
  const marks = selected.value && ingot.data.value
    ? ingot.data.value.segments.filter((s) => s.durationMin).map((s) => ({
        xAxis: s.durationMin,
        lineStyle: { color: s.broke ? t.series[2] : t.series[4], type: 'solid', width: 1.5 },
        label: { formatter: `段${s.segmentSeq}`, color: t.text, fontSize: 10 },
      }))
    : []
  return {
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : `${(v * 100).toFixed(0)}%`) },
    grid: { left: 48, right: 20, top: 16, bottom: 42 },
    xAxis: { type: 'value', name: '生長時間 (分)', axisLine: { lineStyle: { color: t.axis } }, splitLine: { show: false } },
    yAxis: { type: 'value', min: 0, max: 1, name: '累積斷線先驗', axisLabel: { formatter: (v) => `${v * 100}%` }, splitLine: { lineStyle: { color: t.grid } } },
    series: [{
      type: 'line', showSymbol: false, data: d.curve.map((p) => [p.t, p.hazard]),
      lineStyle: { color: t.series[1], width: 2 }, areaStyle: { color: t.band },
      markLine: marks.length ? { silent: true, symbol: 'none', data: marks } : undefined,
    }],
  }
})

const v = computed(() => board.data.value?.validation)
</script>

<template>
  <div class="page-head">
    <h2>運營風險</h2>
    <p>
      把站得住的訊號合成風險回顧。<strong>兩組件分開標示</strong>：監控偵測（回溯性）與時間先驗（可即時）。
      <strong style="color: var(--warn)">回溯性審視用途，非即時預測。</strong>
    </p>
  </div>

  <StateBlock :loading="board.loading.value" :error="board.error.value">
    <!-- 验证摘要 -->
    <div v-if="v" class="stat-row" style="margin-bottom: 14px">
      <div class="stat">
        <div class="label">監控偵測 AUC</div>
        <div class="value" style="color: var(--accent-strong)">{{ fmt(board.data.value.monitorAuc, 3) }}</div>
        <div class="sub">PC1/PC2 融合，分組 CV</div>
      </div>
      <div class="stat">
        <div class="label">高風險層 精確率</div>
        <div class="value">{{ fmtPct(v.highTierPrecision, 0) }}</div>
        <div class="sub">{{ v.highTierCount }} 段中實際斷線</div>
      </div>
      <div class="stat">
        <div class="label">斷線召回率</div>
        <div class="value">{{ fmtPct(v.recallOfBreaks, 0) }}</div>
        <div class="sub">{{ v.totalBreaks }} 斷線中被標記（現行 OOC 僅 5%）</div>
      </div>
      <div class="stat">
        <div class="label">6 小時時間先驗</div>
        <div class="value">{{ hazard.data.value ? fmtPct(hazard.data.value.milestones.find((m) => m.t === 360)?.hazard, 0) : '—' }}</div>
        <div class="sub">生長至 6h 的累積斷線率</div>
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1.3fr 1fr; gap: 14px">
      <!-- 风险看板 -->
      <div class="card scroll-x">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
          <h3 style="margin: 0">風險看板（依監控風險排序）</h3>
          <div style="display: flex; gap: 5px">
            <div v-for="tf in ['all', 'high', 'mid', 'low']" :key="tf" class="chip"
              :class="{ active: tierFilter === tf }" @click="tierFilter = tf">
              {{ tf === 'all' ? '全部' : TIER[tf].label }}
            </div>
          </div>
        </div>
        <table>
          <thead>
            <tr><th>晶棒</th><th>段</th><th>分級</th><th>監控風險</th><th>時間先驗</th><th>結果</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in filtered" :key="r.ingotNo + '-' + r.segmentSeq"
              :class="{ selected: selected === r.ingotNo }" @click="selected = r.ingotNo">
              <td class="mono">{{ r.ingotNo }}</td>
              <td>{{ r.segmentSeq }}</td>
              <td><span class="badge" :class="TIER[r.tier].cls">{{ TIER[r.tier].label }}</span></td>
              <td>
                <div style="display: flex; align-items: center; gap: 6px">
                  <div style="flex: 1; height: 5px; background: var(--surface-2); border-radius: 3px; min-width: 40px">
                    <div :style="{ width: fmtPct(r.monitorRisk, 0), height: '100%', background: 'var(--accent)', borderRadius: '3px' }" />
                  </div>
                  <span class="mono" style="font-size: 11px">{{ fmt(r.monitorRisk, 2) }}</span>
                </div>
              </td>
              <td class="mono muted">{{ r.timeHazard != null ? fmtPct(r.timeHazard, 0) : '—' }}</td>
              <td><span class="badge" :class="r.broke ? 'danger' : 'ok'">{{ r.broke ? '斷線' : '正常' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 时间先验曲线 + 选中晶棒 -->
      <div class="grid" style="align-content: start">
        <div class="card">
          <h3>時間風險先驗（Kaplan-Meier）</h3>
          <p class="muted" style="font-size: 12px; margin: -4px 0 6px">
            生長時數的累積斷線先驗（可即時算）。<span v-if="selected">紅/綠豎線＝{{ selected }} 各段位置。</span>
          </p>
          <EChart :option="hazardOption" height="230px" />
        </div>

        <div v-if="selected" class="card scroll-x">
          <h3>{{ selected }} · 段風險明細</h3>
          <StateBlock :loading="ingot.loading.value" :error="ingot.error.value">
            <table v-if="ingot.data.value">
              <thead><tr><th>段</th><th>時長(分)</th><th>監控風險</th><th>時間先驗</th><th>結果</th></tr></thead>
              <tbody>
                <tr v-for="s in ingot.data.value.segments" :key="s.segmentSeq">
                  <td>{{ s.segmentSeq }}</td>
                  <td class="mono">{{ fmt(s.durationMin, 0) }}</td>
                  <td class="mono">{{ fmt(s.monitorRisk, 2) }}</td>
                  <td class="mono muted">{{ s.timeHazard != null ? fmtPct(s.timeHazard, 0) : '—' }}</td>
                  <td><span class="badge" :class="s.broke ? 'danger' : 'ok'">{{ s.broke ? '斷線' : '正常' }}</span></td>
                </tr>
              </tbody>
            </table>
          </StateBlock>
        </div>
        <div v-else class="card">
          <p class="muted" style="font-size: 12px; margin: 0">← 點看板任一列，查看該晶棒各段風險明細與時間位置。</p>
        </div>
      </div>
    </div>

    <p v-if="board.data.value" class="muted" style="font-size: 11.5px; margin-top: 12px">{{ board.data.value.note }}</p>
  </StateBlock>
</template>
