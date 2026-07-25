export const GROUP_LABELS = {
  g1: '單次·無異常',
  g2: '單次·有異常',
  g3: '多次·有異常',
  g4: '多次·無異常',
}

export function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (typeof value !== 'number') return value
  return value.toLocaleString('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  })
}

export function fmtTime(iso) {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 19)
}

export function fmtPct(value, digits = 1) {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

const ENDED_LABELS = {
  ADVANCE: '正常推進',
  COMPLETE: '完成',
  BREAK: '斷線',
  REGRESSION: '回退',
}
export const endedByLabel = (v) => ENDED_LABELS[v] || v
