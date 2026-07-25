<script setup>
import { computed } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt, fmtPct } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const phaseRisk = useAsync(api.qualityPhaseRisk)
const fusion = useAsync(api.qualityFusion)
const furnace = useAsync(api.qualityFurnaceRisk)

const PHASE_ORDER = { NECK: 0, CROWN: 1, BODY: 2, TAIL: 3 }

// 各相位断线率
const phaseOption = computed(() => {
  const d = phaseRisk.data.value
  if (!d) return {}
  const t = chartTheme.value
  const rows = [...d.phases].sort((a, b) => PHASE_ORDER[a.phase] - PHASE_ORDER[b.phase])
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${(v * 100).toFixed(0)}%` },
    grid: { left: 44, right: 20, top: 12, bottom: 30 },
    xAxis: { type: 'category', data: rows.map((r) => r.phase) },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => `${v * 100}%` }, splitLine: { lineStyle: { color: t.grid } } },
    series: [{
      type: 'bar',
      data: rows.map((r) => ({ value: r.breakRate, itemStyle: { color: r.phase === 'BODY' ? t.series[2] : t.series[0] } })),
      label: { show: true, position: 'top', color: t.text, formatter: (p) => `${(p.value * 100).toFixed(0)}%` },
    }],
  }
})

// BODY 生存曲线
const survivalOption = computed(() => {
  const d = phaseRisk.data.value
  if (!d) return {}
  const t = chartTheme.value
  const km = d.curves.BODY || []
  return {
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : v.toFixed ? v.toFixed(2) : v) },
    grid: { left: 48, right: 20, top: 16, bottom: 42 },
    xAxis: { type: 'value', name: '生長時間 (分)', axisLine: { lineStyle: { color: t.axis } }, splitLine: { show: false } },
    yAxis: { type: 'value', min: 0, max: 1, name: '未斷線存活率', splitLine: { lineStyle: { color: t.grid } } },
    series: [{
      type: 'line', step: 'end', showSymbol: false,
      data: km.map((p) => [p.t, p.s]),
      lineStyle: { color: t.series[2], width: 2 },
      areaStyle: { color: t.band },
    }],
  }
})

// 融合 PR 曲线
const prOption = computed(() => {
  const d = fusion.data.value
  if (!d) return {}
  const t = chartTheme.value
  const pr = [...d.fused.prCurve].sort((a, b) => a.recall - b.recall)
  const oc = d.currentOoc
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 46, right: 18, top: 16, bottom: 40 },
    xAxis: { type: 'value', min: 0, max: 1, name: 'Recall', splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'value', min: 0, max: 1, name: 'Precision', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { name: '融合', type: 'line', showSymbol: false, data: pr.map((p) => [p.recall, p.precision]), lineStyle: { color: t.series[5], width: 2 } },
      {
        name: '現行 OOC', type: 'line', data: [[oc.recall, oc.precision]],
        symbol: 'circle', symbolSize: 12, showSymbol: true,
        itemStyle: { color: t.series[2] },
        label: { show: true, formatter: '現行 OOC', position: 'right', color: t.text },
      },
    ],
  }
})

const furnaceOption = computed(() => {
  const d = furnace.data.value
  if (!d) return {}
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => `${(v * 100).toFixed(0)}%` },
    grid: { left: 40, right: 16, top: 12, bottom: 30 },
    xAxis: { type: 'category', data: d.furnaces.map((f) => f.furnace) },
    yAxis: { type: 'value', max: 0.5, axisLabel: { formatter: (v) => `${v * 100}%` }, splitLine: { lineStyle: { color: t.grid } } },
    series: [{ type: 'bar', data: d.furnaces.map((f) => f.breakRate), itemStyle: { color: t.series[0] } }],
  }
})

const hp = computed(() => fusion.data.value?.fused.highPrecisionPoint)
</script>

<template>
  <div class="page-head">
    <h2>品質分析</h2>
    <p>相位斷線風險與生存曲線、監控融合（提升召回）、爐台比較</p>
  </div>

  <!-- 生存分析 -->
  <StateBlock :loading="phaseRisk.loading.value" :error="phaseRisk.error.value">
    <div v-if="phaseRisk.data.value" class="grid" style="grid-template-columns: 1fr 1.5fr; gap: 14px; margin-bottom: 14px">
      <div class="card">
        <h3>各相位斷線率</h3>
        <EChart :option="phaseOption" height="240px" />
        <p class="muted" style="font-size: 12px; margin: 6px 0 0">
          斷線集中在 <strong style="color: var(--danger)">BODY（76%）</strong>；NECK/CROWN 較低，TAIL 幾乎不斷。
        </p>
      </div>
      <div class="card">
        <h3>BODY 生存曲線（Kaplan-Meier）</h3>
        <EChart :option="survivalOption" height="240px" />
        <p class="muted" style="font-size: 12px; margin: 6px 0 0">
          <strong>生長 4 小時內幾乎不斷，之後風險急升</strong>：6 小時已半數斷線、10 小時僅
          {{ fmtPct(phaseRisk.data.value.bodyMilestones.find((m) => m.t === 600)?.survival, 0) }} 存活。
          → 生長時數本身是可用的時間風險指標。
        </p>
      </div>
    </div>

    <div v-if="phaseRisk.data.value" class="stat-row" style="margin-bottom: 14px">
      <div v-for="m in phaseRisk.data.value.bodyMilestones" :key="m.t" class="stat">
        <div class="label">生長 {{ m.t }} 分</div>
        <div class="value" style="font-size: 20px">{{ fmtPct(m.survival, 0) }}</div>
        <div class="sub">仍未斷線</div>
      </div>
    </div>
  </StateBlock>

  <!-- 监控融合 -->
  <div class="card" style="margin-bottom: 14px">
    <h3>監控融合：把召回從 5% 拉起來</h3>
    <StateBlock :loading="fusion.loading.value" :error="fusion.error.value">
      <div v-if="fusion.data.value">
        <p class="muted" style="font-size: 12px; margin: -2px 0 10px">
          現行 OOC 只用 T²/SPE 越界旗標，召回僅 <strong>5%</strong>。但 <strong style="color: var(--accent-strong)">PC2（AUC {{ fmt(fusion.data.value.singles[0].auc, 3) }}）</strong>
          是最強的斷線相關訊號、卻未被使用。納入 PC1/PC2 融合後——
          <span v-if="hp"><strong>相同精確 90% 下，召回可達 {{ fmtPct(hp.recall, 0) }}</strong></span>。
          <span style="color: var(--warn)">注意：profile 監控為回溯性，斷線段常被截短，部分增益可能來自段長差異，須配對驗證。</span>
        </p>
        <div class="row" style="align-items: stretch">
          <div class="card" style="flex: 1.2; background: var(--bg)">
            <div class="muted" style="font-size: 11px; margin-bottom: 6px">Precision-Recall（融合 vs 現行 OOC）</div>
            <EChart :option="prOption" height="240px" />
          </div>
          <div class="card scroll-x" style="flex: 1; background: var(--bg)">
            <div class="muted" style="font-size: 11px; margin-bottom: 6px">各指標單變量鑑別力</div>
            <table>
              <thead><tr><th>指標</th><th>AUC</th><th>現行 OOC 使用</th></tr></thead>
              <tbody>
                <tr v-for="s in fusion.data.value.singles" :key="s.name">
                  <td class="mono">{{ s.name }}</td>
                  <td class="mono">{{ fmt(s.auc, 3) }}</td>
                  <td><span class="badge" :class="['T2','SPE'].includes(s.name) ? 'ok' : 'dim'">{{ ['T2','SPE'].includes(s.name) ? '是' : '否（浪費）' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </StateBlock>
  </div>

  <!-- 炉台比较 -->
  <div class="card">
    <h3>爐台斷線率比較</h3>
    <StateBlock :loading="furnace.loading.value" :error="furnace.error.value">
      <div v-if="furnace.data.value">
        <EChart :option="furnaceOption" height="200px" />
        <p class="muted" style="font-size: 12px; margin: 6px 0 0">{{ furnace.data.value.note }}</p>
      </div>
    </StateBlock>
  </div>
</template>
