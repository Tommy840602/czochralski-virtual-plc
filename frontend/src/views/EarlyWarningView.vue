<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt, fmtPct } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const overview = useAsync(api.ewOverview)
const regPath = useAsync(api.ewRegPath)
const leadCurve = useAsync(api.ewLeadCurve)

// BODY 斷線前置時間衰減：配對世代(含CI帶) vs naive
const leadOption = computed(() => {
  const d = leadCurve.data.value
  if (!d || !d.available) return {}
  const t = chartTheme.value
  const xs = d.matched.map((r) => r.lead)
  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v) => (v == null ? '—' : Number(v).toFixed(3)),
    },
    legend: { data: ['配對世代 (誠實)', 'naive (混淆)', '隨機 0.5'], textStyle: { color: t.text }, top: 2 },
    grid: { left: 46, right: 20, top: 34, bottom: 42 },
    xAxis: {
      type: 'category', data: xs, name: '提前時間 (分鐘)',
      axisLine: { lineStyle: { color: t.axis } },
    },
    yAxis: { type: 'value', min: 0.5, max: 1, name: 'OOF AUC', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      // 配對 95% CI 帶（lo + (hi-lo) 堆疊）
      { name: '_lo', type: 'line', stack: 'ci', showSymbol: false, lineStyle: { opacity: 0 }, data: d.matched.map((r) => r.lo), silent: true, tooltip: { show: false } },
      { name: '_ci', type: 'line', stack: 'ci', showSymbol: false, lineStyle: { opacity: 0 }, areaStyle: { color: t.band }, data: d.matched.map((r) => +(r.hi - r.lo).toFixed(4)), silent: true, tooltip: { show: false } },
      { name: '配對世代 (誠實)', type: 'line', data: d.matched.map((r) => r.auc), lineStyle: { color: t.series[5], width: 2.5 }, symbol: 'circle', symbolSize: 7 },
      { name: 'naive (混淆)', type: 'line', data: d.naive.map((r) => r.auc), lineStyle: { color: t.series[2], type: 'dashed', width: 1.5 }, symbol: 'circle' },
      { name: '隨機 0.5', type: 'line', data: xs.map(() => 0.5), lineStyle: { color: t.faint, type: 'dotted', width: 1 }, symbol: 'none' },
    ],
  }
})

const lambda = ref(100)
const threshold = ref(null)

const model = useAsync(
  () => api.ewModel({ lam: lambda.value, threshold: threshold.value ?? undefined }),
  { immediate: false },
)
let deb
watch([lambda, threshold], () => {
  clearTimeout(deb)
  deb = setTimeout(() => model.run(), 200)
}, { immediate: true })

const LAMBDAS = [1, 2, 5, 10, 20, 50, 100, 200, 500]

// 過擬合曲線：train vs OOF AUC + 單特徵基線
const regOption = computed(() => {
  const d = regPath.data.value
  if (!d) return {}
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['訓練 AUC', 'OOF AUC', '單特徵基線'], textStyle: { color: t.text }, top: 2 },
    grid: { left: 48, right: 20, top: 34, bottom: 40 },
    xAxis: {
      type: 'category', data: d.path.map((r) => r.lambda), name: 'λ (正則化)',
      axisLine: { lineStyle: { color: t.axis } },
    },
    yAxis: { type: 'value', min: 0.5, max: 1, splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { name: '訓練 AUC', type: 'line', data: d.path.map((r) => r.trainAuc), lineStyle: { color: t.series[1] }, symbol: 'circle' },
      { name: 'OOF AUC', type: 'line', data: d.path.map((r) => r.oofAuc), lineStyle: { color: t.series[5], width: 2 }, symbol: 'circle' },
      {
        name: '單特徵基線', type: 'line', data: d.path.map(() => d.baseline.auc),
        lineStyle: { color: t.series[2], type: 'dashed', width: 1 }, symbol: 'none',
      },
    ],
  }
})

const rocOption = computed(() => {
  const d = model.data.value
  if (!d) return {}
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 46, right: 18, top: 26, bottom: 40 },
    xAxis: { type: 'value', min: 0, max: 1, name: 'FPR', splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'value', min: 0, max: 1, name: 'TPR', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { type: 'line', showSymbol: false, data: d.roc.map((p) => [p.fpr, p.tpr]), lineStyle: { color: t.series[5], width: 2 }, areaStyle: { color: t.band } },
      { type: 'line', showSymbol: false, data: [[0, 0], [1, 1]], lineStyle: { color: t.faint, type: 'dashed', width: 1 } },
    ],
  }
})

const prOption = computed(() => {
  const d = model.data.value
  if (!d) return {}
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 46, right: 18, top: 26, bottom: 40 },
    xAxis: { type: 'value', min: 0, max: 1, name: 'Recall', splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'value', min: 0, max: 1, name: 'Precision', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { type: 'line', showSymbol: false, data: d.pr.map((p) => [p.recall, p.precision]), lineStyle: { color: t.series[0], width: 2 } },
    ],
  }
})

// 風險分數分布：case vs control 直方
const distOption = computed(() => {
  const d = model.data.value
  if (!d) return {}
  const t = chartTheme.value
  const bins = 20
  const hist = (arr) => {
    const h = new Array(bins).fill(0)
    arr.forEach((v) => { h[Math.min(bins - 1, Math.floor(v * bins))]++ })
    return h
  }
  const x = Array.from({ length: bins }, (_, i) => ((i + 0.5) / bins).toFixed(2))
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['異常 case', '正常 control'], textStyle: { color: t.text }, top: 2 },
    grid: { left: 40, right: 16, top: 32, bottom: 52 },
    xAxis: { type: 'category', data: x, name: '風險分數' },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      { name: '異常 case', type: 'bar', stack: 'a', data: hist(d.distribution.case), itemStyle: { color: t.series[2] } },
      { name: '正常 control', type: 'bar', stack: 'a', data: hist(d.distribution.control), itemStyle: { color: t.series[0] } },
    ],
    markLine: {},
  }
})

const contribOption = computed(() => {
  const d = model.data.value
  if (!d) return {}
  const t = chartTheme.value
  const rows = [...d.contributions].reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 150, right: 30, top: 8, bottom: 30 },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'category', data: rows.map((r) => r.feature), axisLabel: { color: t.text, fontSize: 10 } },
    series: [
      {
        type: 'bar',
        data: rows.map((r) => ({ value: r.coef, itemStyle: { color: r.coef >= 0 ? t.series[2] : t.series[0] } })),
      },
    ],
  }
})

const op = computed(() => model.data.value?.operating)
</script>

<template>
  <div class="page-head">
    <h2>預警模型</h2>
    <p>
      多變量斷線風險模型（L2 邏輯迴歸，<strong>按晶棒分組交叉驗證</strong>取 out-of-fold 機率）。
      分數為誠實的 OOF 估計，非訓練內表現。
    </p>
  </div>

  <StateBlock :loading="overview.loading.value" :error="overview.error.value">
    <div v-if="overview.data.value" class="stat-row" style="margin-bottom: 14px">
      <div class="stat">
        <div class="label">視窗數</div>
        <div class="value">{{ overview.data.value.nWindows }}</div>
        <div class="sub">{{ overview.data.value.nCase }} case / {{ overview.data.value.nControl }} control</div>
      </div>
      <div class="stat">
        <div class="label">候選特徵</div>
        <div class="value">{{ overview.data.value.nFeatures }}</div>
        <div class="sub">{{ overview.data.value.nSignals }} 訊號 × 7 統計量</div>
      </div>
      <div class="stat" v-if="model.data.value">
        <div class="label">OOF AUC</div>
        <div class="value" :style="{ color: 'var(--accent-strong)' }">{{ fmt(model.data.value.oofAuc, 3) }}</div>
        <div class="sub">單特徵基線 {{ fmt(model.data.value.baseline.auc, 3) }}（{{ model.data.value.baseline.feature }}）</div>
      </div>
      <div class="stat" v-if="op">
        <div class="label">操作點 精確／召回</div>
        <div class="value" style="font-size: 20px">{{ fmtPct(op.precision, 0) }} / {{ fmtPct(op.recall, 0) }}</div>
        <div class="sub">閾值 {{ fmt(model.data.value.threshold, 2) }}</div>
      </div>
    </div>

    <!-- 誠實結論橫幅 -->
    <div
      v-if="model.data.value"
      class="card"
      style="margin-bottom: 14px; border-left: 3px solid var(--warn); display: flex; gap: 10px; align-items: baseline"
    >
      <span class="badge warn">結論</span>
      <span style="font-size: 13px">{{ model.data.value.verdict }}</span>
    </div>

    <!-- BODY 斷線前置時間衰減（配對世代稽核）-->
    <div v-if="leadCurve.data.value && leadCurve.data.value.available" class="card" style="margin-bottom: 14px">
      <h3>BODY 斷線：能提前多久預測？（配對世代）</h3>
      <p class="muted" style="font-size: 12px; margin: -4px 0 6px">
        以「同群體 + 熔料剩餘（生長階段）配對」建立公平世代。<strong>配對線隨提前時間衰減＝真前兆</strong>；
        naive 線持平於高位＝混淆假象。真相：<strong>提前 20 分 AUC ~0.75 尚可用，40–60 分衰減到接近隨機</strong>。
        見 <span class="mono">docs/body_break_confound_audit.md</span>。
      </p>
      <EChart :option="leadOption" height="260px" />
    </div>

    <!-- λ 控制 -->
    <div class="card" style="margin-bottom: 14px">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px">
        <span class="muted" style="font-size: 12px">正則化強度 λ = <b class="mono">{{ lambda }}</b>（大＝更保守、更不過擬合）</span>
      </div>
      <div style="display: flex; gap: 6px; flex-wrap: wrap">
        <div
          v-for="l in LAMBDAS" :key="l" class="chip"
          :class="{ active: lambda === l }" @click="lambda = l"
        >{{ l }}</div>
      </div>
    </div>

    <StateBlock :loading="model.loading.value" :error="model.error.value">
      <div v-if="model.data.value" class="grid" style="gap: 14px">
        <!-- 过拟合曲线 -->
        <div class="card">
          <h3>過擬合曲線：訓練 vs OOF AUC</h3>
          <p class="muted" style="font-size: 12px; margin: -4px 0 6px">
            兩線背離＝過擬合。λ 越大越收斂，但 OOF 始終壓在單特徵基線附近——多加特徵無益。
          </p>
          <EChart :option="regOption" height="260px" />
        </div>

        <div class="row" style="align-items: stretch">
          <div class="card" style="flex: 1"><h3>ROC（OOF）</h3><EChart :option="rocOption" height="240px" /></div>
          <div class="card" style="flex: 1"><h3>Precision-Recall</h3><EChart :option="prOption" height="240px" /></div>
        </div>

        <div class="row" style="align-items: stretch">
          <div class="card" style="flex: 1.2"><h3>風險分數分布</h3><EChart :option="distOption" height="250px" /></div>
          <div class="card" style="flex: 1"><h3>特徵貢獻（標準化係數 Top 15）</h3><EChart :option="contribOption" height="250px" /></div>
        </div>

        <!-- 操作点 + 高风险段 -->
        <div class="row" style="align-items: stretch">
          <div class="card" style="flex: 1">
            <h3>操作點</h3>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px">
              <span class="muted" style="font-size: 12px">告警閾值 {{ fmt(model.data.value.threshold, 2) }}</span>
              <input
                type="range" min="0" max="1" step="0.02"
                :value="model.data.value.threshold"
                @input="threshold = Number($event.target.value)"
                style="flex: 1"
              />
            </div>
            <div v-if="op" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px">
              <div class="stat"><div class="label">命中 TP</div><div class="value" style="color: var(--ok); font-size: 20px">{{ op.tp }}</div></div>
              <div class="stat"><div class="label">誤報 FP</div><div class="value" style="color: var(--warn); font-size: 20px">{{ op.fp }}</div></div>
              <div class="stat"><div class="label">漏報 FN</div><div class="value" style="color: var(--danger); font-size: 20px">{{ op.fn }}</div></div>
              <div class="stat"><div class="label">F1</div><div class="value" style="font-size: 20px">{{ fmt(op.f1, 3) }}</div></div>
            </div>
          </div>

          <div class="card scroll-x" style="flex: 1">
            <h3>最高風險段落 Top 20</h3>
            <table>
              <thead><tr><th>晶棒</th><th>段</th><th>實際</th><th>風險</th></tr></thead>
              <tbody>
                <tr v-for="r in model.data.value.riskScores.slice(0, 20)" :key="r.ingotNo + '-' + r.segmentSeq">
                  <td class="mono">{{ r.ingotNo }}</td>
                  <td>{{ r.segmentSeq }}</td>
                  <td><span class="badge" :class="r.group === 'case' ? 'danger' : 'dim'">{{ r.group === 'case' ? '異常' : '正常' }}</span></td>
                  <td class="mono">{{ fmt(r.risk, 3) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </StateBlock>
  </StateBlock>
</template>
