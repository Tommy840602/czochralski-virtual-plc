// 極薄的 fetch 封裝：統一組 query、帶 token、丟錯、解析 JSON。
const BASE = '/api'

// 由 main.js 注入，避免 client 直接相依 pinia/router（循環相依）
let _getToken = () => ''
let _onUnauthorized = () => {}
export function configureClient({ getToken, onUnauthorized }) {
  _getToken = getToken
  _onUnauthorized = onUnauthorized
}

function buildQuery(params = {}) {
  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) value.forEach((v) => sp.append(key, v))
    else sp.append(key, value)
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

async function request(path, { method = 'GET', params, body } = {}) {
  const headers = {}
  const token = _getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body) headers['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${BASE}${path}${buildQuery(params)}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    // fetch 只有網路層失敗才會 throw（後端未啟動、埠不通等）
    throw new Error('無法連線到後端，請確認後端服務已啟動（埠 8000）')
  }

  if (res.status === 401) {
    _onUnauthorized()
    throw new Error('登入已失效，請重新登入')
  }
  // 5xx（含 dev proxy 在後端未啟動時回的 500）多半是後端沒起或崩了
  if (res.status >= 500) {
    throw new Error('後端無回應（請確認後端服務已啟動，埠 8000）')
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail || detail
    } catch {
      /* 非 JSON 錯誤照原樣 */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const get = (path, params) => request(path, { params })
export const post = (path, body) => request(path, { method: 'POST', body })

export const api = {
  meta: () => get('/meta'),
  summary: () => get('/summary'),
  ingots: (params) => get('/ingots', params),
  ingotDetail: (id) => get(`/ingots/${id}`),
  ingotEvents: (id) => get(`/ingots/${id}/events`),
  series: (id, params) => get(`/ingots/${id}/series`, params),
  compare: (params) => get('/compare', params),
  precursorOverview: () => get('/precursor/overview'),
  precursorRanking: (params) => get('/precursor/ranking', params),
  precursorDetail: (key) => get('/precursor/detail', { key }),
  precursorSweep: (params) => get('/precursor/sweep', params),
  profileBand: () => get('/profile/band'),
  profileScores: (params) => get('/profile/scores', params),
  profileConfusion: () => get('/profile/confusion'),
  profileIngot: (id, segmentSeq) => get(`/profile/ingots/${id}`, { segmentSeq }),
  controlDefaults: () => get('/control/defaults'),
  controlReplay: (params) => get('/control/replay', params),
  ewOverview: () => get('/earlywarning/overview'),
  ewModel: (params) => get('/earlywarning/model', params),
  ewRegPath: () => get('/earlywarning/reg-path'),
  ewLeadCurve: () => get('/earlywarning/lead-curve'),
  qualityPhaseRisk: () => get('/quality/phase-risk'),
  qualityFusion: () => get('/quality/fusion'),
  qualityFurnaceRisk: () => get('/quality/furnace-risk'),
  riskBoard: () => get('/risk/board'),
  riskHazardCurve: () => get('/risk/hazard-curve'),
  riskIngot: (id) => get(`/risk/ingots/${id}`),
  login: (username, password) => post('/auth/login', { username, password }),
}
