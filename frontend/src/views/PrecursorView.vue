<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const overview = useAsync(api.precursorOverview)

const filters = reactive({ signals: [], features: [], minDiscriminance: 0 })
const ranking = useAsync(
  () =>
    api.precursorRanking({
      signal: filters.signals,
      feature: filters.features,
      minDiscriminance: filters.minDiscriminance,
    }),
  { immediate: false },
)
watch(filters, () => ranking.run(), { deep: true, immediate: true })

const selectedKey = ref(null)
const detail = useAsync(() => api.precursorDetail(selectedKey.value), { immediate: false })
watch(selectedKey, (k) => k && detail.run())

// 選第一列作為預設細節
watch(
  () => ranking.data.value,
  (rows) => {
    if (rows && rows.length && !selectedKey.value) selectedKey.value = rows[0].key
  },
)

function toggle(list, value) {
  const i = list.indexOf(value)
  if (i >= 0) list.splice(i, 1)
  else list.push(value)
}

// AUC 條形圖：越偏離 0.5 越有鑑別力，兩側對稱著色
const rankOption = computed(() => {
  const rows = (ranking.data.value ?? []).slice(0, 20).reverse()
  const t = chartTheme.value
  return {
    grid: { left: 150, right: 40, top: 10, bottom: 30 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p) => {
        const r = rows[p[0].dataIndex]
        return `${r.signal}::${r.feature}<br/>AUC ${r.auc.toFixed(3)} · ${r.direction}<br/>q=${r.q?.toExponential(2) ?? '—'}`
      },
    },
    xAxis: { type: 'value', min: 0, max: 1, splitLine: { lineStyle: { color: t.grid } } },
    yAxis: {
      type: 'category',
      data: rows.map((r) => `${r.signal}·${r.feature}`),
      axisLabel: { color: t.text, fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((r) => ({
          value: r.auc,
          itemStyle: { color: r.auc >= 0.5 ? t.series[2] : t.series[0] },
        })),
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ xAxis: 0.5 }],
          lineStyle: { color: t.faint, type: 'dashed' },
          label: { formatter: '0.5', color: t.faint },
        },
      },
    ],
  }
})

const rocOption = computed(() => {
  const d = detail.data.value
  if (!d) return {}
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 24, top: 30, bottom: 44 },
    xAxis: { type: 'value', min: 0, max: 1, name: 'FPR', splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'value', min: 0, max: 1, name: 'TPR', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      {
        type: 'line',
        showSymbol: false,
        data: d.roc.map((p) => [p.fpr, p.tpr]),
        lineStyle: { color: t.series[0], width: 2 },
        areaStyle: { color: 'rgba(91,155,209,0.14)' },
      },
      {
        type: 'line',
        showSymbol: false,
        data: [[0, 0], [1, 1]],
        lineStyle: { color: t.faint, type: 'dashed', width: 1 },
      },
    ],
  }
})

// case / control 分布：以箱型圖並列
const distOption = computed(() => {
  const d = detail.data.value
  if (!d) return {}
  const box = (s) => [s.min, s.q1, s.median, s.q3, s.max]
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'item' },
    xAxis: { type: 'category', data: ['異常 (case)', '正常 (control)'] },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: t.grid } } },
    series: [
      {
        type: 'boxplot',
        data: [box(d.distribution.case), box(d.distribution.control)],
        itemStyle: { color: 'rgba(215,106,99,0.28)', borderColor: t.series[2] },
      },
    ],
  }
})
</script>

<template>
  <div class="page-head">
    <h2>前兆分析</h2>
    <p>斷線前視窗特徵的鑑別力（Mann-Whitney AUC，BH-FDR 校正）</p>
  </div>

  <StateBlock :loading="overview.loading.value" :error="overview.error.value">
    <div v-if="overview.data.value" class="stat-row" style="margin-bottom: 16px">
      <div class="stat">
        <div class="label">異常視窗 (case)</div>
        <div class="value">{{ overview.data.value.nCase }}</div>
      </div>
      <div class="stat">
        <div class="label">正常視窗 (control)</div>
        <div class="value">{{ overview.data.value.nControl }}</div>
      </div>
      <div class="stat">
        <div class="label">候選特徵數</div>
        <div class="value">{{ overview.data.value.nFeatures }}</div>
      </div>
      <div class="stat">
        <div class="label">視窗長度</div>
        <div class="value">{{ overview.data.value.windowLength }}</div>
        <div class="sub">取樣點</div>
      </div>
    </div>

    <!-- 篩選 -->
    <div class="card" style="margin-bottom: 14px">
      <div class="muted" style="font-size: 11px; margin-bottom: 4px">特徵類型</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px">
        <div
          v-for="f in overview.data.value?.features || []"
          :key="f.value"
          class="chip"
          :class="{ active: filters.features.includes(f.value) }"
          @click="toggle(filters.features, f.value)"
        >
          {{ f.label }}
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 10px">
        <span class="muted" style="font-size: 12px">最低鑑別力 {{ filters.minDiscriminance.toFixed(2) }}</span>
        <input v-model.number="filters.minDiscriminance" type="range" min="0" max="0.8" step="0.05" style="flex: 1; max-width: 300px" />
      </div>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 14px">
      <!-- 排行 -->
      <div class="card">
        <h3 style="margin-top: 0; font-size: 14px">鑑別力排行 Top 20</h3>
        <StateBlock :loading="ranking.loading.value" :error="ranking.error.value" :empty="ranking.data.value?.length === 0">
          <EChart v-if="ranking.data.value?.length" :option="rankOption" height="440px" />
        </StateBlock>
      </div>

      <!-- 細節 -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h3 style="margin: 0; font-size: 14px">特徵細節</h3>
          <select v-if="ranking.data.value?.length" v-model="selectedKey">
            <option v-for="r in ranking.data.value.slice(0, 40)" :key="r.key" :value="r.key">
              {{ r.signal }}::{{ r.feature }}
            </option>
          </select>
        </div>
        <StateBlock :loading="detail.loading.value" :error="detail.error.value">
          <div v-if="detail.data.value">
            <div class="stat-row" style="margin: 10px 0">
              <div class="stat">
                <div class="label">AUC（定向後）</div>
                <div class="value" style="font-size: 22px">{{ fmt(detail.data.value.orientedAuc, 3) }}</div>
                <div class="sub">{{ detail.data.value.flipped ? 'case 偏低' : 'case 偏高' }}</div>
              </div>
              <div class="stat">
                <div class="label">p 值</div>
                <div class="value" style="font-size: 22px">{{ detail.data.value.p?.toExponential(1) }}</div>
              </div>
            </div>
            <div style="font-size: 12px" class="muted">ROC 曲線</div>
            <EChart :option="rocOption" height="220px" />
            <div style="font-size: 12px" class="muted">case / control 分布</div>
            <EChart :option="distOption" height="220px" />
          </div>
        </StateBlock>
      </div>
    </div>
  </StateBlock>
</template>
