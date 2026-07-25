import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const KEY = 'plc-auth'

// token 存 localStorage，重整不掉登入。單人本機情境足夠。
export const useAuthStore = defineStore('auth', () => {
  const saved = JSON.parse(localStorage.getItem(KEY) || 'null')
  const token = ref(saved?.token || '')
  const username = ref(saved?.username || '')
  const expiresAt = ref(saved?.expiresAt || 0)

  const isAuthenticated = computed(
    () => !!token.value && expiresAt.value * 1000 > Date.now(),
  )

  function setSession(data) {
    token.value = data.token
    username.value = data.username
    expiresAt.value = data.expiresAt
    localStorage.setItem(KEY, JSON.stringify(data))
  }

  function logout() {
    token.value = ''
    username.value = ''
    expiresAt.value = 0
    localStorage.removeItem(KEY)
  }

  return { token, username, expiresAt, isAuthenticated, setSession, logout }
})
