import { ref, computed } from 'vue'

const KEY = 'plc-theme'

const stored = localStorage.getItem(KEY)
const initial =
  stored ||
  (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')

export const theme = ref(initial)

function apply(t) {
  document.documentElement.setAttribute('data-theme', t)
}
apply(initial) // 首次渲染前就套上，避免閃白

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(KEY, theme.value)
  apply(theme.value)
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

// 圖表用色從 CSS 變數讀出，主題切換時 computed 重算 → 相依它的圖表 option 重繪
export const chartTheme = computed(() => {
  theme.value // 建立相依
  return {
    text: cssVar('--chart-text'),
    textStrong: cssVar('--text'),
    bg: cssVar('--bg'),
    surface: cssVar('--surface'),
    grid: cssVar('--chart-grid'),
    axis: cssVar('--chart-axis'),
    ttBg: cssVar('--chart-tt-bg'),
    ttBorder: cssVar('--chart-tt-border'),
    faint: cssVar('--text-faint'),
    accent: cssVar('--accent'),
    ok: cssVar('--ok'),
    warn: cssVar('--warn'),
    danger: cssVar('--danger'),
    series: [1, 2, 3, 4, 5, 6].map((i) => cssVar(`--series-${i}`)),
    band: cssVar('--band-fill'),
  }
})
