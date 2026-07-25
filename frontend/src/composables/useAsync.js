import { ref, shallowRef, watchEffect } from 'vue'

// 把「非同步取值 + loading/error 狀態」收斂成一個 composable，
// 各頁面不必各自重寫 try/catch 樣板。傳入的 reactive getter 變動時自動重取。
export function useAsync(fetcher, { immediate = true } = {}) {
  const data = shallowRef(null)
  const loading = ref(false)
  const error = ref(null)
  let token = 0

  async function run(...args) {
    const current = ++token
    loading.value = true
    error.value = null
    try {
      const result = await fetcher(...args)
      if (current === token) data.value = result
    } catch (e) {
      if (current === token) error.value = e.message || String(e)
    } finally {
      if (current === token) loading.value = false
    }
  }

  if (immediate) run()
  return { data, loading, error, run }
}

// 依賴 reactive 來源自動重取的版本
export function useAutoAsync(fetcher) {
  const state = useAsync(fetcher, { immediate: false })
  watchEffect(() => state.run())
  return state
}
