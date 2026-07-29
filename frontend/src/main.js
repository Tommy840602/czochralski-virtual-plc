import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from './App.vue'
import { configureClient } from './api/client'
import { useAuthStore } from './stores/auth'
import './styles.css'

const routes = [
  { path: '/', redirect: '/plc' },
  { path: '/login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
  { path: '/plc', component: () => import('./views/PlcRuntimeView.vue') },
  { path: '/overview', component: () => import('./views/OverviewView.vue') },
  { path: '/explore', component: () => import('./views/ExploreView.vue') },
  {
    path: '/explore/:ingotNo',
    component: () => import('./views/IngotView.vue'),
    props: true,
  },
  { path: '/precursor', component: () => import('./views/PrecursorView.vue') },
  { path: '/earlywarning', component: () => import('./views/EarlyWarningView.vue') },
  { path: '/profile', component: () => import('./views/ProfileView.vue') },
  { path: '/control', component: () => import('./views/ControlView.vue') },
  { path: '/quality', component: () => import('./views/QualityView.vue') },
  { path: '/risk', component: () => import('./views/OperationalRiskView.vue') },
  { path: '/access', component: () => import('./views/AccessRequestsView.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

const app = createApp(App)
app.use(createPinia())
app.use(router)

const auth = useAuthStore()

// API client 從 auth store 取 token；遇 401 登出並導回登入頁
configureClient({
  getToken: () => auth.token,
  onUnauthorized: () => {
    auth.logout()
    router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
  },
})

// 路由守衛：未登入只能停在 public 頁
router.beforeEach((to) => {
  if (!to.meta.public && !auth.isAuthenticated) {
    return { path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (to.path === '/login' && auth.isAuthenticated) return '/plc'
})

app.mount('#app')
