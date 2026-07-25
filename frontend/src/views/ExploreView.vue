<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useAsync } from '@/composables/useAsync'
import { GROUP_LABELS, fmt, fmtTime } from '@/composables/format'
import StateBlock from '@/components/StateBlock.vue'

const router = useRouter()
const { data: facets } = useAsync(api.meta)

const filters = reactive({
  group: [],
  furnace: '',
  hasFault: null,
  q: '',
  page: 1,
  pageSize: 25,
})

const { data, loading, error, run } = useAsync(() =>
  api.ingots({
    group: filters.group,
    furnace: filters.furnace || undefined,
    hasFault: filters.hasFault === null ? undefined : filters.hasFault,
    q: filters.q || undefined,
    page: filters.page,
    pageSize: filters.pageSize,
  }),
)

// 篩選條件變動時回到第一頁並重取；分頁變動只重取
let debounce
watch(
  () => [filters.group.slice(), filters.furnace, filters.hasFault, filters.q],
  () => {
    clearTimeout(debounce)
    debounce = setTimeout(() => {
      filters.page = 1
      run()
    }, 250)
  },
)
watch(() => filters.page, run)

function toggleGroup(g) {
  const i = filters.group.indexOf(g)
  if (i >= 0) filters.group.splice(i, 1)
  else filters.group.push(g)
}

const faultOptions = [
  { label: '全部', value: null },
  { label: '僅有異常', value: true },
  { label: '僅無異常', value: false },
]

function open(row) {
  router.push(`/explore/${row.INGOT_NO}`)
}

function totalPages() {
  return data.value ? Math.max(1, Math.ceil(data.value.total / filters.pageSize)) : 1
}
</script>

<template>
  <div class="page-head">
    <h2>晶棒探索</h2>
    <p>依分組、爐台、異常狀態篩選晶棒，點列進入時序檢視</p>
  </div>

  <div class="controls">
    <div
      v-for="g in ['g1', 'g2', 'g3', 'g4']"
      :key="g"
      class="chip"
      :class="{ active: filters.group.includes(g) }"
      @click="toggleGroup(g)"
    >
      {{ g.toUpperCase() }} · {{ GROUP_LABELS[g] }}
    </div>

    <select v-model="filters.furnace">
      <option value="">全部爐台</option>
      <option v-for="f in facets?.furnaces || []" :key="f" :value="f">
        {{ f.replace('Furnace_', '') }}
      </option>
    </select>

    <select v-model="filters.hasFault">
      <option v-for="o in faultOptions" :key="String(o.value)" :value="o.value">
        {{ o.label }}
      </option>
    </select>

    <input v-model="filters.q" type="text" placeholder="搜尋晶棒編號…" style="min-width: 180px" />
  </div>

  <div class="card scroll-x">
    <StateBlock :loading="loading" :error="error" :empty="data && data.items.length === 0">
      <table v-if="data">
        <thead>
          <tr>
            <th>晶棒編號</th>
            <th>分組</th>
            <th>爐台</th>
            <th>開爐時間</th>
            <th>異常</th>
            <th>嘗試數</th>
            <th>製程/設備故障</th>
            <th>事件數</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in data.items" :key="row.INGOT_NO" @click="open(row)">
            <td class="mono">{{ row.INGOT_NO }}</td>
            <td><span class="badge" :class="row.GROUP">{{ GROUP_LABELS[row.GROUP] }}</span></td>
            <td>{{ row.DATABASE_NAME.replace('Furnace_', '') }}</td>
            <td class="muted">{{ fmtTime(row.CREATETIME) }}</td>
            <td>
              <span v-if="row.HAS_GENERAL_FAULT" class="badge danger">有</span>
              <span v-else class="badge ok">無</span>
            </td>
            <td>{{ fmt(row.ATTEMPT_COUNT, 0) }}</td>
            <td>{{ fmt(row.PROCESS_FAULT_COUNT, 0) }} / {{ fmt(row.EQUIPMENT_FAULT_COUNT, 0) }}</td>
            <td>{{ fmt(row.TOTAL_EVENT_COUNT, 0) }}</td>
          </tr>
        </tbody>
      </table>
    </StateBlock>

    <div v-if="data" class="pagination">
      <span>共 {{ data.total }} 根 · 第 {{ filters.page }}/{{ totalPages() }} 頁</span>
      <button class="btn" :disabled="filters.page <= 1" @click="filters.page--">上一頁</button>
      <button class="btn" :disabled="filters.page >= totalPages()" @click="filters.page++">
        下一頁
      </button>
    </div>
  </div>
</template>
