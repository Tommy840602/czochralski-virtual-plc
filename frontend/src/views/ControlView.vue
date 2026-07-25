<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { fmt, endedByLabel } from '@/composables/format'
import { chartTheme } from '@/composables/theme'
import EChart from '@/components/EChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const defaults = useAsync(api.controlDefaults)

// 晶棒挑選：預設抓有長 BODY 段的清單
const ingotList = useAsync(() => api.ingots({ group: ['g4', 'g1'], pageSize: 40 }))
const ingotNo = ref('')
watch(
  () => ingotList.data.value,
  (d) => {
    if (d && d.items.length && !ingotNo.value) ingotNo.value = d.items[0].INGOT_NO
  },
)

const gains = reactive({ gp: 0.0004, gv: 0.16, gd: -0.1064 })
const ermMode = ref('default')

const replay = useAsync(
  () =>
    api.controlReplay({
      ingot: ingotNo.value,
      gp: gains.gp,
      gv: gains.gv,
      gd: gains.gd,
      ermMode: ermMode.value,
    }),
  { immediate: false },
)

let deb
watch(
  [ingotNo, () => gains.gp, () => gains.gv, () => gains.gd, ermMode],
  () => {
    if (!ingotNo.value) return
    clearTimeout(deb)
    deb = setTimeout(() => replay.run(), 200)
  },
  { immediate: true },
)

function reset() {
  gains.gp = 0.0004
  gains.gv = 0.16
  gains.gd = -0.1064
  ermMode.value = 'default'
}

// Er_M 曲線圖：原始 vs 單調修正
const ermOption = computed(() => {
  const curve = defaults.data.value?.ermCurve ?? []
  const t = chartTheme.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['原始 Er_M', '單調修正'], textStyle: { color: t.text }, top: 4 },
    grid: { left: 44, right: 20, top: 36, bottom: 40 },
    xAxis: { type: 'value', name: 'e = 直徑−目標', min: -3, max: 3, splitLine: { lineStyle: { color: t.grid } } },
    yAxis: { type: 'value', name: 'Er_M', splitLine: { lineStyle: { color: t.grid } } },
    series: [
      {
        name: '原始 Er_M', type: 'line', showSymbol: false, step: false,
        data: curve.map((p) => [p.e, p.default]),
        lineStyle: { color: t.series[2], width: 2 },
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(214,154,76,0.14)' },
          data: [[{ xAxis: 1 }, { xAxis: 2 }], [{ xAxis: -2 }, { xAxis: -1 }]],
        },
      },
      {
        name: '單調修正', type: 'line', showSymbol: false,
        data: curve.map((p) => [p.e, p.monotone]),
        lineStyle: { color: t.series[3], width: 2, type: 'dashed' },
      },
    ],
  }
})

const timeOpt = (title, keys, colorIdx, names) =>
  computed(() => {
    const s = replay.data.value?.series
    if (!s) return {}
    const t = chartTheme.value
    const colors = colorIdx.map((c) => (typeof c === 'number' ? t.series[c] : c === 'faint' ? t.faint : c))
    return {
      title: { text: title, textStyle: { color: t.text, fontSize: 12 }, left: 6, top: 2 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : Number(v).toFixed(4)) },
      legend: { data: names, textStyle: { color: t.text }, top: 2, right: 10 },
      grid: { left: 60, right: 20, top: 34, bottom: 40 },
      xAxis: { type: 'time', axisLine: { lineStyle: { color: t.axis } } },
      yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: t.grid } } },
      dataZoom: [{ type: 'inside' }],
      series: keys.map((k, i) => ({
        name: names[i], type: 'line', showSymbol: false,
        lineStyle: { color: colors[i], width: 1.4, type: k === 'target' ? 'dashed' : 'solid' },
        data: s[k],
      })),
    }
  })

const diaOption = timeOpt('直徑 vs 目標', ['diameter', 'target'], [0, 'faint'], ['直徑', '目標'])
const mvOption = timeOpt('MV 指令：新增益 vs 當前 recipe', ['mvNew', 'mvBase'], [3, 2], ['新增益', '當前 recipe'])
const slOption = timeOpt('拉速指令（示意積分）：新 vs 當前 vs 實測', ['slNew', 'slBase', 'slActual'], [3, 1, 'faint'], ['新', '當前', '實測'])

const st = computed(() => replay.data.value?.stats)
</script>

<template>
  <div class="page-head">
    <h2>控制調參沙盒</h2>
    <p>
      開環 replay：同一記錄工況下比較不同增益的控制器 MV 指令。
      <strong style="color: var(--warn)">不預測改變後的直徑</strong>——被控對象在此閉環資料下不可辨識，此頁只顯示控制器「當下會下多大指令」。
    </p>
  </div>

  <StateBlock :loading="defaults.loading.value" :error="defaults.error.value">
    <!-- 控制面板 -->
    <div class="card" style="margin-bottom: 14px">
      <div class="controls" style="margin-bottom: 14px">
        <select v-model="ingotNo" style="min-width: 160px">
          <option v-for="it in ingotList.data.value?.items || []" :key="it.INGOT_NO" :value="it.INGOT_NO">
            {{ it.INGOT_NO }} · {{ it.GROUP.toUpperCase() }}
          </option>
        </select>
        <div class="chip" :class="{ active: ermMode === 'default' }" @click="ermMode = 'default'">Er_M 原始</div>
        <div class="chip" :class="{ active: ermMode === 'monotone' }" @click="ermMode = 'monotone'">Er_M 單調修正</div>
        <button class="btn" @click="reset">重置為當前 recipe</button>
      </div>

      <div class="grid" style="grid-template-columns: repeat(3, 1fr); gap: 18px">
        <div>
          <label class="muted" style="font-size: 12px">Gp（誤差·比例）= K·Kc = <b class="mono">{{ gains.gp.toFixed(5) }}</b></label>
          <input v-model.number="gains.gp" type="range" min="0" max="0.002" step="0.00005" style="width: 100%" />
          <div class="muted" style="font-size: 11px">當前 0.0004 · 無振盪→可上調以壓慢漂移</div>
        </div>
        <div>
          <label class="muted" style="font-size: 12px">Gv（變化率·微分）= <b class="mono">{{ gains.gv.toFixed(4) }}</b></label>
          <input v-model.number="gains.gv" type="range" min="0" max="0.5" step="0.005" style="width: 100%" />
          <div class="muted" style="font-size: 11px">當前 0.16</div>
        </div>
        <div>
          <label class="muted" style="font-size: 12px">Gd（平滑率·阻尼）= <b class="mono">{{ gains.gd.toFixed(4) }}</b></label>
          <input v-model.number="gains.gd" type="range" min="-0.3" max="0" step="0.005" style="width: 100%" />
          <div class="muted" style="font-size: 11px">當前 −0.1064</div>
        </div>
      </div>
    </div>

    <!-- 統計列 -->
    <div v-if="st" class="stat-row" style="margin-bottom: 14px">
      <div class="stat">
        <div class="label">直徑誤差 std (mm)</div>
        <div class="value" style="font-size: 20px">{{ fmt(st.errorStd, 3) }}</div>
        <div class="sub">此段實測，與增益無關</div>
      </div>
      <div class="stat">
        <div class="label">控制激進程度</div>
        <div class="value" style="font-size: 20px">{{ fmt(st.aggressiveness, 2) }}×</div>
        <div class="sub">MV RMS 相對當前 recipe</div>
      </div>
      <div class="stat">
        <div class="label">Er_M 死區時間</div>
        <div class="value" style="font-size: 20px">{{ fmt(st.deadZonePct, 1) }}%</div>
        <div class="sub">1≤|e|<2，比例增益卡平</div>
      </div>
      <div class="stat">
        <div class="label">±2 跳變點徘徊</div>
        <div class="value" style="font-size: 20px">{{ fmt(st.nearJumpPct, 1) }}%</div>
        <div class="sub">chatter 風險</div>
      </div>
    </div>

    <StateBlock :loading="replay.loading.value" :error="replay.error.value">
      <div v-if="replay.data.value" class="grid" style="gap: 14px">
        <div class="card"><EChart :option="diaOption" height="220px" /></div>
        <div class="row" style="align-items: stretch">
          <div class="card" style="flex: 1"><EChart :option="mvOption" height="240px" /></div>
          <div class="card" style="flex: 1"><EChart :option="slOption" height="240px" /></div>
        </div>
        <div class="card">
          <h3 style="margin: 0 0 4px; font-size: 14px">Er_M 非線性：原始 vs 單調修正</h3>
          <p class="muted" style="font-size: 12px; margin: 0 0 6px">
            橙色區＝增益死區（1&lt;|e|&lt;2，比例推力不增長，佔運行 ~11%）；原始在 e=±2 有 ±1 跳變。
            單調版消去死區與跳變，不需被控對象模型即可改善中等誤差恢復。
          </p>
          <EChart :option="ermOption" height="260px" />
        </div>
      </div>
    </StateBlock>
  </StateBlock>
</template>
