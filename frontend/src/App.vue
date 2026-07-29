<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { theme, toggleTheme } from '@/composables/theme'

// 每頁一個語意化 stroke 圖標（inner SVG，24×24），hover 時彈跳動畫
const links = [
  { to: '/plc', label: 'PLC Runtime', icon: '<path d="M4 4h16v16H4z"/><path d="M8 8h3v3H8zM13 8h3M13 11h3M8 15h8"/>' },
  { to: '/overview', label: '總覽', icon: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>' },
  { to: '/explore', label: '晶棒探索', icon: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>' },
  { to: '/precursor', label: '前兆分析', icon: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>' },
  { to: '/earlywarning', label: '預警模型', icon: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>' },
  { to: '/profile', label: '輪廓監控', icon: '<path d="M3 12h3l2-7 4 15 3-11 2 4h4"/>' },
  { to: '/control', label: '控制調參', icon: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>' },
  { to: '/quality', label: '品質分析', icon: '<line x1="6" y1="20" x2="6" y2="15"/><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/>' },
  { to: '/risk', label: '運營風險', icon: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>' },
  { to: '/access', label: '帳號申請', permission: 'access:manage', icon: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>' },
]

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <RouterView v-if="route.meta.public" />

  <div v-else class="app-shell">
    <aside class="sidebar">
        <div class="brand">
        <div class="brand-icon-wrap">
          <img
            src="/plc.png"
            alt="CZ Virtual PLC"
            class="brand-icon"
          />
        </div>

        <div class="brand-text">
          <h1>CZ PLC</h1>
          <span class="brand-subtitle">設備控制平台</span>
        </div>
      </div>

      <nav style="flex: 1">
        <RouterLink v-for="l in links.filter((item) => !item.permission || auth.can(item.permission))" :key="l.to" :to="l.to" class="nav-link">
          <svg
            class="nav-icon"
            viewBox="0 0 24 24"
            width="17"
            height="17"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            v-html="l.icon"
          />
          <span>{{ l.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <span class="muted" style="font-size: 12px; display: flex; align-items: center; gap: 6px">
          <span class="user-dot" />
          <span>
            {{ auth.username || '使用者' }}
            <small v-if="auth.role">{{ auth.role }}</small>
          </span>
        </span>
        <div style="display: flex; gap: 6px">
          <button
            class="icon-btn"
            :title="theme === 'dark' ? '切換日間' : '切換夜間'"
            @click="toggleTheme"
          >
            <svg v-if="theme === 'dark'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
            </svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
            </svg>
          </button>
          <button class="btn" style="font-size: 12px; padding: 6px 10px" @click="logout">登出</button>
        </div>
      </div>
    </aside>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 88px;
  padding: 16px 14px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border);
}

/*
 * 如果 plc.png 圖片本身四周有透明空白，
 * wrapper + scale 可以讓實際圖案看起來更大。
 */
.brand-icon-wrap {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.brand-icon {
  width: 34px;
  height: 34px;
  display: block;
  object-fit: contain;
  transform: scale(1.15);
  transform-origin: center;
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-text h1 {
  margin: 0;
  display: flex;
  flex-direction: column;
  color: var(--text);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.22;
  letter-spacing: 0.1px;
}

.brand-text h1 span {
  display: block;
  white-space: nowrap;
}

.brand-subtitle {
  display: block;
  margin-top: 5px;
  color: var(--text-faint);
  font-size: 11px;
  line-height: 1.3;
  white-space: nowrap;
}

/* 導航：圖標 + 文字；圖標 hover 彈跳、active 高亮 */
.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nav-icon {
  flex-shrink: 0;
  opacity: 0.72;
  transition: transform 0.2s ease, opacity 0.15s ease, color 0.12s ease;
}
.nav-link:hover .nav-icon {
  opacity: 1;
  animation: nav-pop 0.45s ease;
}
.nav-link.router-link-active .nav-icon {
  opacity: 1;
  color: var(--accent);
  transform: scale(1.08);
}
@keyframes nav-pop {
  0% { transform: scale(1) rotate(0deg); }
  35% { transform: scale(1.3) rotate(-7deg); }
  70% { transform: scale(0.95) rotate(4deg); }
  100% { transform: scale(1.08) rotate(0deg); }
}
@media (prefers-reduced-motion: reduce) {
  .nav-link:hover .nav-icon { animation: none; }
}

.sidebar-foot {
  padding-top: 14px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.user-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--ok);
}

.sidebar-foot .muted small {
  display: block;
  margin-top: 2px;
  color: var(--text-faint);
  font: 9px ui-monospace, monospace;
}
</style>
