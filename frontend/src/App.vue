<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { theme, toggleTheme } from '@/composables/theme'

const sections = [
  {
    label: 'Runtime',
    index: '01',
    links: [
      { to: '/plc', code: 'PLC-01', label: 'PLC Runtime', description: 'Scan / Interlock', icon: '<path d="M4 4h16v16H4z"/><path d="M8 8h3v3H8zM13 8h3M13 11h3M8 15h8"/>' },
      { to: '/overview', code: 'OVW-02', label: '製程總覽', description: 'Fleet Summary', icon: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>' },
      { to: '/explore', code: 'EXP-03', label: '晶棒探索', description: 'Ingot Explorer', icon: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>' },
    ],
  },
  {
    label: 'Control Intelligence',
    index: '02',
    links: [
      { to: '/precursor', code: 'SIG-11', label: '前兆分析', description: 'Signal Features', icon: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>' },
      { to: '/earlywarning', code: 'ML-12', label: '預警模型', description: 'Early Warning', icon: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>' },
      { to: '/profile', code: 'PRF-13', label: '輪廓監控', description: 'Profile Monitor', icon: '<path d="M3 12h3l2-7 4 15 3-11 2 4h4"/>' },
      { to: '/control', code: 'CTL-14', label: '控制調參', description: 'Control Tuning', icon: '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>' },
    ],
  },
  {
    label: 'Quality & Governance',
    index: '03',
    links: [
      { to: '/quality', code: 'QMS-21', label: '品質分析', description: 'Quality Analytics', icon: '<line x1="6" y1="20" x2="6" y2="15"/><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/>' },
      { to: '/risk', code: 'RSK-22', label: '運營風險', description: 'Operational Risk', icon: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>' },
      { to: '/access', code: 'IAM-23', label: '帳號治理', description: 'Access Control', permission: 'access:manage', icon: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>' },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileNavOpen = ref(false)
const now = ref(new Date())
let clockTimer

const visibleSections = computed(() =>
  sections
    .map((section) => ({
      ...section,
      links: section.links.filter((item) => !item.permission || auth.can(item.permission)),
    }))
    .filter((section) => section.links.length),
)

const currentLink = computed(() => {
  const allLinks = visibleSections.value.flatMap((section) =>
    section.links.map((link) => ({ ...link, section: section.label })),
  )
  return allLinks.find((link) => route.path === link.to || route.path.startsWith(`${link.to}/`))
    || { code: 'PLC-00', label: 'CZ Virtual PLC', description: 'Control System', section: 'Runtime' }
})

const clock = computed(() =>
  new Intl.DateTimeFormat('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(now.value),
)

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => window.clearInterval(clockTimer))
watch(() => route.fullPath, () => {
  mobileNavOpen.value = false
})

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <RouterView v-if="route.meta.public" />

  <div v-else class="app-shell" :class="{ 'nav-open': mobileNavOpen }">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon-wrap">
          <img src="/plc.png" alt="CZ Virtual PLC" class="brand-icon" />
          <i class="brand-led" />
        </div>
        <div class="brand-text">
          <span class="brand-kicker">CONTROL SYSTEM · CZ-01</span>
          <h1>CZ Virtual PLC</h1>
          <span class="brand-subtitle">Virtual Control Runtime</span>
        </div>
      </div>

      <div class="system-strip">
        <span><i /> CONTROL CONSOLE</span>
        <b>SIM</b>
      </div>

      <nav class="side-nav">
        <section v-for="section in visibleSections" :key="section.label" class="nav-section">
          <div class="nav-section-title">
            <span>{{ section.index }}</span>
            <b>{{ section.label }}</b>
          </div>
          <RouterLink v-for="l in section.links" :key="l.to" :to="l.to" class="nav-link">
            <svg
              class="nav-icon"
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              v-html="l.icon"
            />
            <span class="nav-copy">
              <b>{{ l.label }}</b>
              <small>{{ l.code }} · {{ l.description }}</small>
            </span>
            <i class="nav-state" />
          </RouterLink>
        </section>
      </nav>

      <div class="sidebar-foot">
        <div class="identity">
          <span class="identity-avatar">{{ (auth.role || 'U').slice(0, 2).toUpperCase() }}</span>
          <span>
            <b>{{ auth.username || '使用者' }}</b>
            <small>{{ auth.role || 'Authorized User' }}</small>
          </span>
        </div>
        <div class="foot-actions">
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
          <button class="logout-btn" title="登出" @click="logout">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M10 17l5-5-5-5M15 12H3M15 3h5v18h-5" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <button
      v-if="mobileNavOpen"
      class="nav-backdrop"
      aria-label="關閉導覽"
      @click="mobileNavOpen = false"
    />

    <div class="workspace">
      <header class="cockpit-bar">
        <div class="route-context">
          <button class="menu-trigger" aria-label="切換導覽" @click="mobileNavOpen = !mobileNavOpen">
            <span /><span /><span />
          </button>
          <span class="route-code">{{ currentLink.code }}</span>
          <span>
            <small>{{ currentLink.section }} / {{ currentLink.description }}</small>
            <b>{{ currentLink.label }}</b>
          </span>
        </div>

        <div class="system-health">
          <span class="health-item"><i /> OPC UA I/O <b>CHANNEL</b></span>
          <span class="health-item"><i /> DCS ROUTE <b>CHANNEL</b></span>
          <span class="health-item clock"><small>LOCAL</small> {{ clock }}</span>
        </div>
      </header>

      <div class="process-rail">
        <span class="rail-node active"><i /> PLANT SIMULATOR</span>
        <em />
        <span class="rail-node active"><i /> OPC UA I/O</span>
        <em />
        <span class="rail-node active"><i /> VIRTUAL PLC</span>
        <em />
        <span class="rail-node"><i /> CZ DCS</span>
      </div>

      <main class="main">
        <div class="page-frame">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 264px minmax(0, 1fr);
  background:
    linear-gradient(rgba(65, 222, 201, 0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(65, 222, 201, 0.018) 1px, transparent 1px),
    var(--bg);
  background-size: 48px 48px;
}

.sidebar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: color-mix(in srgb, var(--surface) 96%, transparent);
  border-right: 1px solid var(--border);
  box-shadow: 12px 0 40px rgba(0, 0, 0, 0.16);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 98px;
  padding: 20px 18px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border);
}

.brand-icon-wrap {
  position: relative;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: var(--surface-2);
}

.brand-icon {
  width: 30px;
  height: 30px;
  display: block;
  object-fit: contain;
}

.brand-led {
  position: absolute;
  right: 4px;
  top: 4px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 8px var(--ok);
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-text h1 {
  margin: 2px 0 0;
  color: var(--text-strong);
  font-size: 15px;
  font-weight: 680;
  line-height: 1.2;
  letter-spacing: 0.4px;
}

.brand-kicker,
.brand-subtitle {
  font: 8px/1.4 var(--mono);
  letter-spacing: 1.25px;
  text-transform: uppercase;
}

.brand-subtitle {
  margin-top: 4px;
  color: var(--text-faint);
}

.brand-kicker {
  color: var(--accent);
}

.system-strip {
  min-height: 37px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  color: var(--text-faint);
  font: 8px var(--mono);
  letter-spacing: 1px;
}

.system-strip span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.system-strip i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 8px var(--ok);
}

.system-strip b {
  padding: 2px 6px;
  color: var(--warn);
  border: 1px solid color-mix(in srgb, var(--warn) 30%, transparent);
  border-radius: 3px;
  font-weight: 500;
}

.side-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 15px 12px 20px;
  scrollbar-width: thin;
}

.nav-section + .nav-section {
  margin-top: 17px;
}

.nav-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px 7px;
  color: var(--text-faint);
  font: 8px var(--mono);
  letter-spacing: 1.25px;
  text-transform: uppercase;
}

.nav-section-title span {
  color: var(--accent);
}

.nav-section-title b {
  font-weight: 500;
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 50px;
  margin: 2px 0;
  padding: 7px 9px;
  color: var(--text-dim);
  border: 1px solid transparent;
  border-radius: 7px;
  transition: 150ms ease;
}

.nav-link:hover {
  color: var(--text-strong);
  background: var(--surface-2);
  border-color: var(--border);
}

.nav-link.router-link-active {
  color: var(--text-strong);
  background:
    linear-gradient(90deg, var(--accent-weak), transparent 76%),
    var(--surface-2);
  border-color: color-mix(in srgb, var(--accent) 28%, var(--border));
}

.nav-link.router-link-active::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 9px;
  bottom: 9px;
  width: 2px;
  border-radius: 2px;
  background: var(--accent);
  box-shadow: 0 0 10px var(--accent-line);
}

.nav-icon {
  flex-shrink: 0;
  opacity: 0.65;
  transition: 150ms ease;
}

.nav-link:hover .nav-icon {
  opacity: 1;
}

.nav-link.router-link-active .nav-icon {
  opacity: 1;
  color: var(--accent);
}

.nav-copy {
  min-width: 0;
  display: grid;
}

.nav-copy b {
  color: inherit;
  font-size: 12.5px;
  font-weight: 580;
}

.nav-copy small {
  overflow: hidden;
  margin-top: 1px;
  color: var(--text-faint);
  font: 8px var(--mono);
  letter-spacing: 0.45px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-state {
  width: 4px;
  height: 4px;
  margin-left: auto;
  border-radius: 50%;
  background: var(--border-strong);
}

.router-link-active .nav-state {
  background: var(--accent);
  box-shadow: 0 0 7px var(--accent);
}

.sidebar-foot {
  min-height: 72px;
  padding: 12px 14px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.identity {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
}

.identity-avatar {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  color: var(--accent);
  background: var(--accent-weak);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-radius: 7px;
  font: 9px var(--mono);
}

.identity > span:last-child {
  min-width: 0;
  display: grid;
}

.identity b {
  overflow: hidden;
  color: var(--text);
  font: 10px var(--mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity small {
  margin-top: 2px;
  color: var(--text-faint);
  font: 8px var(--mono);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.foot-actions {
  display: flex;
  gap: 5px;
}

.logout-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: var(--text-dim);
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  cursor: pointer;
}

.logout-btn:hover {
  color: var(--danger);
  border-color: color-mix(in srgb, var(--danger) 45%, var(--border));
}

.workspace {
  min-width: 0;
}

.cockpit-bar {
  position: sticky;
  top: 0;
  z-index: 30;
  min-height: 68px;
  padding: 0 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(18px);
}

.route-context {
  display: flex;
  align-items: center;
  gap: 12px;
}

.route-context > span:last-child {
  display: grid;
}

.route-context small {
  color: var(--text-faint);
  font: 8px var(--mono);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.route-context b {
  margin-top: 2px;
  color: var(--text-strong);
  font-size: 14px;
  font-weight: 620;
}

.route-code {
  padding: 5px 7px;
  color: var(--accent);
  background: var(--accent-weak);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-radius: 4px;
  font: 9px var(--mono);
  letter-spacing: 0.5px;
}

.system-health {
  display: flex;
  align-items: center;
  gap: 6px;
}

.health-item {
  min-height: 31px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-faint);
  border: 1px solid var(--border);
  border-radius: 5px;
  font: 8px var(--mono);
  letter-spacing: 0.6px;
}

.health-item i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-faint);
  opacity: 0.65;
}

.health-item i.ok {
  background: var(--ok);
  box-shadow: 0 0 7px var(--ok);
  opacity: 1;
}

.health-item b {
  color: var(--text-dim);
  font-weight: 500;
}

.health-item.clock {
  color: var(--text);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.health-item.clock small {
  color: var(--text-faint);
  font-size: 7px;
}

.process-rail {
  min-height: 37px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  color: var(--text-faint);
  background: color-mix(in srgb, var(--surface) 65%, transparent);
  border-bottom: 1px solid var(--border);
  font: 7px var(--mono);
  letter-spacing: 0.85px;
}

.process-rail em {
  width: clamp(16px, 3vw, 52px);
  height: 1px;
  margin: 0 8px;
  background: linear-gradient(90deg, var(--accent-line), var(--border-strong));
}

.rail-node {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.rail-node i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-faint);
}

.rail-node.active {
  color: var(--text-dim);
}

.rail-node.active i {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}

.main {
  width: 100%;
  padding: 28px clamp(20px, 3vw, 44px) 64px;
}

.page-frame {
  width: min(100%, 1540px);
  margin: 0 auto;
}

.menu-trigger {
  display: none;
  width: 34px;
  height: 34px;
  padding: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
}

.menu-trigger span {
  display: block;
  height: 1px;
  margin: 4px 0;
  background: var(--text-dim);
}

.nav-backdrop {
  display: none;
}

@media (max-width: 1050px) {
  .app-shell {
    grid-template-columns: 226px minmax(0, 1fr);
  }

  .system-health .health-item:not(.clock) {
    display: none;
  }
}

@media (max-width: 760px) {
  .app-shell {
    display: block;
  }

  .sidebar {
    position: fixed;
    left: 0;
    width: min(294px, 86vw);
    transform: translateX(-102%);
    transition: transform 180ms ease;
  }

  .nav-open .sidebar {
    transform: translateX(0);
  }

  .nav-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 35;
    padding: 0;
    background: rgba(0, 0, 0, 0.58);
    border: 0;
    backdrop-filter: blur(2px);
    cursor: pointer;
  }

  .cockpit-bar {
    min-height: 62px;
    padding: 0 14px;
  }

  .menu-trigger {
    display: block;
  }

  .route-code,
  .system-health {
    display: none;
  }

  .process-rail {
    padding: 0 14px;
    overflow-x: auto;
  }

  .main {
    padding: 20px 14px 44px;
  }
}
</style>
