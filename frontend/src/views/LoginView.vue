<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const localDemoMode = import.meta.env.DEV
const demoAccounts = [
  {
    username: localDemoMode ? 'admin' : 'plc.operator',
    department: 'PLC',
    role: 'Operator',
    access: '製程監看、Sequence 啟停與標準操作',
  },
  {
    username: 'plc.engineer',
    department: 'PLC',
    role: 'Engineer',
    access: '控制分析、聯鎖診斷與 Runtime RESET',
  },
  {
    username: 'plc.lead',
    department: 'PLC',
    role: 'Lead',
    access: '完整 PLC 管理、工程與權限治理',
  },
]
const defaultAccount = demoAccounts[0]
const disclosureItems = [
  '本專案為個人面試展示用途，所有爐子模具圖、設備示意圖與熱場模擬圖皆由 AI 生成或基於模擬情境自行設計，並非取自任何公司、客戶、供應商或第三方之內部圖面、實機照片、工程文件或專有設計資料。',
  '展示中之分析報告與技術說明為 AI 輔助產生之模擬內容，未引用、改寫、揭露或還原任何內部技術文件、SOP、製程規範、設備手冊或商業資料。所有製程參數、感測數值、爐台狀態、警報事件、品質數據與報表內容皆為亂數生成或模擬資料。',
  '本專案所展示之軟體架構、資料流程、系統模組、通訊方式、服務切分、資料庫設計與部署方式皆為模擬設計，僅用於展示個人開發與系統設計能力。',
  '本專案之命名、畫面配置、功能模組、資料表欄位、API 設計與展示流程皆為個人基於公開技術知識與模擬需求自行設計，未對應任何實際公司或產線。',
  '本專案不具備實際生產控制用途，亦不應視為可直接導入現場之正式工控系統、MES、SCADA、EAP 或品質管理系統。',
]

const username = ref(defaultAccount.username)
const password = ref(localDemoMode ? 'admin0000' : '')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const mode = ref('login')
const registrationComplete = ref(false)
const registration = reactive({
  name: '',
  username: '',
  email: '',
  role: 'Operator',
  password: '',
  confirmPassword: '',
})
const roleOptions = [
  { role: 'Operator', access: '製程監看、Sequence 啟停與標準操作' },
  { role: 'Engineer', access: '控制分析、聯鎖診斷與 Runtime RESET' },
  { role: 'Lead', access: '完整 PLC 管理、工程與權限治理' },
]

function setMode(value) {
  mode.value = value
  error.value = ''
  registrationComplete.value = false
}

function selectAccount(account) {
  username.value = account.username
  if (!localDemoMode) password.value = ''
  error.value = ''
}

async function submit() {
  if (loading.value) return
  error.value = ''
  loading.value = true
  try {
    const data = await api.login(username.value.trim(), password.value)
    auth.setSession(data)
    router.replace(route.query.redirect || '/plc')
  } catch (e) {
    error.value = e.message || '登入失敗'
  } finally {
    loading.value = false
  }
}

async function submitRegistration() {
  if (loading.value) return
  error.value = ''
  if (registration.password !== registration.confirmPassword) {
    error.value = '兩次輸入的密碼不一致'
    return
  }
  loading.value = true
  try {
    await api.register({
      name: registration.name.trim(),
      username: registration.username.trim(),
      email: registration.email.trim(),
      role: registration.role,
      password: registration.password,
    })
    registrationComplete.value = true
  } catch (e) {
    error.value = e.message || '帳號申請失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="auth-shell">
    <section class="auth-context">
      <header class="system-header">
        <div class="system-brand">
          <img src="/plc.png" alt="">
          <div>
            <b>CZ VIRTUAL PLC</b>
            <small>CONTROL SYSTEM · CZ-01</small>
          </div>
        </div>
        <div class="runtime-live"><i /> SYSTEM READY</div>
      </header>

      <div class="hero-copy">
        <p>VIRTUAL CONTROL RUNTIME / SIMULATION</p>
        <h1><span>CZ</span> Virtual PLC</h1>
        <h2>把設備訊號轉成可信任的控制決策</h2>
        <p class="hero-description">
          Plant Simulator 經 OPC UA 進入 PLC Input Image，由 Interlock、Sequence
          與 Local Control 執行確定性掃描，再將受控製程資料交付 DCS。
        </p>
      </div>

      <section class="plc-console" aria-label="Virtual PLC runtime architecture">
        <div class="console-topbar">
          <div>
            <i /><i /><i />
          </div>
          <code>RACK CZ01-PLC-A · SLOT 01—04</code>
          <span>RUN</span>
        </div>

        <div class="module-rack">
          <article>
            <div class="module-leds"><i /><i /><i /></div>
            <small>01 / INPUT</small>
            <b>OPC UA</b>
            <span>Plant.* · Status.*</span>
          </article>
          <article>
            <div class="module-leds"><i /><i /></div>
            <small>02 / SAFETY</small>
            <b>INTERLOCK</b>
            <span>E-Stop · Quality · Door</span>
          </article>
          <article>
            <div class="module-leds"><i /><i /><i /></div>
            <small>03 / LOGIC</small>
            <b>SEQUENCE</b>
            <span>MELT → BODY → TAIL</span>
          </article>
          <article>
            <div class="module-leds"><i /><i /></div>
            <small>04 / OUTPUT</small>
            <b>CONTROL</b>
            <span>Actuator command image</span>
          </article>
        </div>

        <div class="signal-flow" aria-hidden="true">
          <span>PLANT</span><i /><b>INPUT IMAGE</b><i /><b>PLC SCAN</b><i /><span>DCS</span>
        </div>
      </section>

      <div class="runtime-metrics">
        <article>
          <small>OPC UA LINK</small>
          <b><i /> ONLINE</b>
          <span>Plant Simulator</span>
        </article>
        <article>
          <small>NOMINAL SCAN</small>
          <b>20 <em>ms</em></b>
          <span>Deterministic cycle</span>
        </article>
        <article>
          <small>SAFETY MODE</small>
          <b>SIMULATION</b>
          <span>Physical output disabled</span>
        </article>
      </div>

      <details class="project-disclosure">
        <summary>
          <span><i /> 模擬展示與資料聲明</span>
          <small>PROJECT NOTICE · 5 ITEMS</small>
        </summary>
        <ol>
          <li v-for="(item, index) in disclosureItems" :key="index">
            <b>{{ String(index + 1).padStart(2, '0') }}</b>
            <p>{{ item }}</p>
          </li>
        </ol>
      </details>

      <footer class="system-footer">
        <span>FASTAPI AUTH · HMAC TOKEN · POSTGRESQL IDENTITY</span>
        <code>SYS/CZ-VPLC/AUTH-01</code>
      </footer>
    </section>

    <section class="auth-form-panel">
      <div class="auth-form-wrap">
        <div class="panel-heading">
          <div>
            <small>IDENTITY GATEWAY</small>
            <b>授權控制站</b>
          </div>
          <span><i /> SECURE CHANNEL</span>
        </div>

        <div class="auth-tabs" role="tablist" aria-label="PLC 登入或申請帳號">
          <button :class="{ active: mode === 'login' }" type="button" role="tab" @click="setMode('login')">登入</button>
          <button :class="{ active: mode === 'register' }" type="button" role="tab" @click="setMode('register')">申請帳號</button>
        </div>

        <form v-if="mode === 'login'" class="auth-form" @submit.prevent="submit">
          <div class="auth-title">
            <small>AUTHORIZED PERSONNEL ONLY</small>
            <h1>登入控制系統</h1>
            <p>使用核准的 CZ Virtual PLC 身份進入設備控制與模擬功能。</p>
          </div>

          <div class="demo-access">
            <div class="demo-access-heading">
              <div>
                <small>INTERVIEW DEMO ACCOUNT</small>
                <b>{{ localDemoMode ? '選擇操作身份，自動帶入本機帳密' : '選擇操作身份，密碼由展示者提供' }}</b>
              </div>
              <span>{{ localDemoMode ? 'LOCAL DEMO' : 'PROTECTED CREDENTIAL' }}</span>
            </div>

            <div class="demo-role-grid">
              <button
                v-for="account in demoAccounts"
                :key="account.username"
                class="role-card"
                :class="{ active: username === account.username }"
                type="button"
                @click="selectAccount(account)"
              >
                <span>{{ account.role.slice(0, 2).toUpperCase() }}</span>
                <div>
                  <b>{{ account.role }}</b>
                  <code>{{ account.username }}</code>
                </div>
                <small>{{ account.access }}</small>
              </button>
            </div>
          </div>

          <label>
            操作帳號
            <input
              v-model="username"
              autocomplete="username"
              placeholder="例如 plc.operator"
              :disabled="loading"
              required
            >
          </label>

          <label>
            密碼
            <div class="password-field">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                :disabled="loading"
                required
              >
              <button type="button" @click="showPassword = !showPassword">
                {{ showPassword ? '隱藏' : '顯示' }}
              </button>
            </div>
          </label>

          <p v-if="error" class="auth-message error">{{ error }}</p>

          <button class="auth-submit" type="submit" :disabled="loading || !username || !password">
            <span>{{ loading ? '驗證中…' : '驗證身份並進入系統' }}</span>
            <b>ENTER ↗</b>
          </button>

          <div class="security-note">
            <b>{{ localDemoMode ? 'LOCAL DEMO ONLY' : 'PROTECTED INTERVIEW DEMO' }}</b>
            <span>{{ localDemoMode ? '本機開發模式可自動填入測試帳密。' : '正式站不公開、不嵌入且不自動填入展示密碼。' }}</span>
          </div>
        </form>

        <form v-else class="auth-form" @submit.prevent="submitRegistration">
          <div class="auth-title">
            <small>ACCESS REQUEST</small>
            <h1>申請控制站權限</h1>
            <p>申請送出後狀態為 PENDING，必須由既有 PLC Lead 核准才能登入。</p>
          </div>

          <div v-if="registrationComplete" class="registration-complete">
            <span>✓</span>
            <h2>申請已送出</h2>
            <p>{{ registration.username }} 正在等待 PLC Lead 核准。</p>
            <button class="auth-submit" type="button" @click="setMode('login')">
              <span>返回登入</span><b>RETURN ↗</b>
            </button>
          </div>

          <template v-else>
            <div class="register-grid">
              <label>
                姓名
                <input v-model="registration.name" autocomplete="name" required>
              </label>
              <label>
                操作帳號
                <input v-model="registration.username" autocomplete="username" placeholder="例如 plc.tommy" required>
              </label>
            </div>

            <label>
              信箱
              <input v-model="registration.email" type="email" autocomplete="email" required>
            </label>

            <fieldset>
              <legend>申請角色</legend>
              <div class="application-role-grid">
                <button
                  v-for="item in roleOptions"
                  :key="item.role"
                  type="button"
                  :class="{ active: registration.role === item.role }"
                  @click="registration.role = item.role"
                >
                  <b>{{ item.role }}</b>
                  <small>{{ item.access }}</small>
                </button>
              </div>
            </fieldset>

            <div class="register-grid">
              <label>
                密碼
                <input v-model="registration.password" type="password" autocomplete="new-password" minlength="12" required>
              </label>
              <label>
                確認密碼
                <input v-model="registration.confirmPassword" type="password" autocomplete="new-password" minlength="12" required>
              </label>
            </div>
            <p class="password-policy">12–72 碼，須包含英文大小寫、數字與符號。</p>

            <p v-if="error" class="auth-message error">{{ error }}</p>
            <button
              class="auth-submit"
              type="submit"
              :disabled="loading || !registration.name || !registration.username || !registration.email || !registration.password"
            >
              <span>{{ loading ? '送出中…' : '送出權限申請' }}</span><b>SUBMIT ↗</b>
            </button>
          </template>
        </form>
      </div>
    </section>
  </main>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(600px, 1.12fr) minmax(500px, 0.88fr);
  background: #060a0d;
  color: #dce9e8;
}

.auth-context {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 32px clamp(36px, 4vw, 72px);
  background:
    linear-gradient(rgba(63, 214, 198, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(63, 214, 198, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 12% 8%, rgba(53, 212, 192, 0.16), transparent 28%),
    radial-gradient(circle at 85% 58%, rgba(43, 108, 126, 0.16), transparent 32%),
    #071114;
  background-size: 42px 42px, 42px 42px, auto, auto, auto;
  border-right: 1px solid #1e3438;
  overflow: auto;
}

.system-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #1c3437;
}

.system-brand {
  display: flex;
  align-items: center;
  gap: 13px;
}

.system-brand img {
  width: 42px;
  height: 42px;
  padding: 7px;
  object-fit: contain;
  border: 1px solid #2e5758;
  border-radius: 10px;
  background: #0b1c1f;
}

.system-brand b,
.system-brand small {
  display: block;
}

.system-brand b {
  font-size: 12px;
  letter-spacing: 0.13em;
}

.system-brand small {
  margin-top: 5px;
  color: #668187;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.12em;
}

.runtime-live,
.panel-heading > span {
  color: #7b9b9f;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.12em;
  white-space: nowrap;
}

.runtime-live i,
.panel-heading > span i,
.runtime-metrics b i,
.project-disclosure summary i {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 7px;
  border-radius: 50%;
  background: #63e6a8;
  box-shadow: 0 0 12px rgba(99, 230, 168, 0.85);
}

.hero-copy {
  max-width: 760px;
}

.hero-copy > p:first-child {
  margin: 0 0 10px;
  color: #47d8c8;
  font: 9px ui-monospace, monospace;
  letter-spacing: 0.18em;
}

.hero-copy h1 {
  margin: 0;
  color: #f2fbfa;
  font-size: clamp(42px, 5vw, 72px);
  font-weight: 650;
  line-height: 0.98;
  letter-spacing: -0.055em;
}

.hero-copy h1 span {
  color: #47d8c8;
}

.hero-copy h2 {
  margin: 16px 0 0;
  color: #b6cdcf;
  font-size: clamp(17px, 1.6vw, 23px);
  font-weight: 500;
  letter-spacing: 0.02em;
}

.hero-description {
  max-width: 700px;
  margin: 15px 0 0;
  color: #789397;
  font-size: 12px;
  line-height: 1.85;
}

.plc-console {
  border: 1px solid #285054;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(5, 14, 17, 0.88);
  box-shadow: 0 26px 80px rgba(0, 0, 0, 0.34);
}

.console-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  min-height: 42px;
  padding: 0 16px;
  border-bottom: 1px solid #203b3f;
  background: #0c1b1e;
}

.console-topbar > div {
  display: flex;
  gap: 5px;
}

.console-topbar > div i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3c6669;
}

.console-topbar > div i:first-child {
  background: #4dd7c7;
}

.console-topbar code {
  color: #6f8c91;
  font-size: 8px;
  letter-spacing: 0.08em;
}

.console-topbar > span {
  justify-self: end;
  padding: 4px 8px;
  border: 1px solid #2f7356;
  border-radius: 999px;
  color: #7aeca9;
  font: 8px ui-monospace, monospace;
}

.module-rack {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  padding: 12px;
  background: #102327;
}

.module-rack article {
  min-height: 128px;
  padding: 14px;
  border: 1px solid #28474b;
  background:
    linear-gradient(135deg, rgba(70, 215, 198, 0.06), transparent 54%),
    #0a171a;
}

.module-leds {
  display: flex;
  gap: 5px;
  margin-bottom: 24px;
}

.module-leds i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #63e6a8;
  box-shadow: 0 0 7px rgba(99, 230, 168, 0.6);
}

.module-leds i:last-child {
  background: #efbe68;
  box-shadow: 0 0 7px rgba(239, 190, 104, 0.55);
}

.module-rack small,
.module-rack b,
.module-rack span {
  display: block;
}

.module-rack small {
  color: #537479;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.08em;
}

.module-rack b {
  margin-top: 7px;
  color: #d7e9e8;
  font: 600 12px ui-monospace, monospace;
  letter-spacing: 0.08em;
}

.module-rack span {
  margin-top: 7px;
  color: #638187;
  font-size: 8px;
  line-height: 1.45;
}

.signal-flow {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 11px 16px 13px;
  border-top: 1px solid #203b3f;
  color: #648287;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.05em;
}

.signal-flow i {
  height: 1px;
  background: linear-gradient(90deg, #24484c, #4dd7c7);
}

.signal-flow b {
  color: #9eb6b8;
  font-weight: 500;
}

.runtime-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.runtime-metrics article {
  padding: 14px 16px;
  border: 1px solid #1f3a3e;
  border-radius: 10px;
  background: rgba(8, 23, 26, 0.72);
}

.runtime-metrics small,
.runtime-metrics b,
.runtime-metrics span {
  display: block;
}

.runtime-metrics small {
  color: #55757a;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.09em;
}

.runtime-metrics b {
  margin-top: 8px;
  color: #d8e9e8;
  font: 600 14px ui-monospace, monospace;
}

.runtime-metrics b i {
  width: 6px;
  height: 6px;
}

.runtime-metrics em {
  color: #69868b;
  font-size: 9px;
  font-style: normal;
}

.runtime-metrics span {
  margin-top: 5px;
  color: #607b80;
  font-size: 8px;
}

.project-disclosure {
  border: 1px solid #1d3639;
  border-radius: 10px;
  background: rgba(7, 20, 23, 0.74);
}

.project-disclosure summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 13px 15px;
  color: #90aaad;
  font-size: 10px;
  cursor: pointer;
  list-style: none;
}

.project-disclosure summary::-webkit-details-marker {
  display: none;
}

.project-disclosure summary::after {
  content: "+";
  color: #4dd7c7;
  font: 16px ui-monospace, monospace;
}

.project-disclosure[open] summary::after {
  content: "−";
}

.project-disclosure summary small {
  margin-left: auto;
  color: #4d6a6f;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.08em;
}

.project-disclosure summary i {
  width: 6px;
  height: 6px;
  background: #efbe68;
  box-shadow: 0 0 9px rgba(239, 190, 104, 0.55);
}

.project-disclosure ol {
  max-height: 260px;
  overflow: auto;
  margin: 0;
  padding: 0 16px 8px;
  border-top: 1px solid #193034;
  list-style: none;
}

.project-disclosure li {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #152b2e;
}

.project-disclosure li:last-child {
  border-bottom: 0;
}

.project-disclosure li > b {
  color: #48cdbf;
  font: 700 8px ui-monospace, monospace;
}

.project-disclosure li > p {
  margin: 0;
  color: #708b8f;
  font-size: 9px;
  line-height: 1.7;
}

.system-footer {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-top: auto;
  color: #425f64;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.07em;
}

.auth-form-panel {
  display: grid;
  place-items: center;
  padding: clamp(24px, 4vw, 64px);
  background:
    radial-gradient(circle at 100% 0, rgba(76, 215, 199, 0.08), transparent 30%),
    linear-gradient(155deg, #0d1418, #080c0f 74%);
  overflow: auto;
}

.auth-form-wrap {
  width: min(560px, 100%);
}

.panel-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.panel-heading small,
.panel-heading b {
  display: block;
}

.panel-heading small {
  color: #48d4c4;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.16em;
}

.panel-heading b {
  margin-top: 6px;
  color: #dfeceb;
  font-size: 18px;
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #26373c;
  border-radius: 12px;
  background: #0a1014;
}

.auth-tabs button {
  border: 0;
  background: transparent;
  color: #718388;
  padding: 11px;
  border-radius: 8px;
  font-size: 11px;
  cursor: pointer;
}

.auth-tabs button.active {
  color: #e9f4f3;
  background: #173236;
  box-shadow: inset 0 0 0 1px #2b5b5f;
}

.auth-form {
  padding: clamp(24px, 3vw, 36px);
  border: 1px solid #2a3b40;
  border-radius: 16px;
  background:
    linear-gradient(145deg, rgba(24, 42, 46, 0.55), rgba(11, 18, 22, 0.88)),
    #0c1317;
  box-shadow: 0 34px 90px rgba(0, 0, 0, 0.42);
}

.auth-title {
  margin-bottom: 24px;
}

.auth-title small {
  color: #49d6c6;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.17em;
}

.auth-title h1 {
  margin: 9px 0;
  color: #f1f8f7;
  font-size: 27px;
  letter-spacing: -0.025em;
}

.auth-title p {
  margin: 0;
  color: #71878b;
  font-size: 10px;
  line-height: 1.65;
}

.demo-access {
  margin-bottom: 20px;
  padding: 14px;
  border: 1px solid #29484c;
  border-radius: 12px;
  background: rgba(8, 23, 26, 0.72);
}

.demo-access-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.demo-access-heading small,
.demo-access-heading b {
  display: block;
}

.demo-access-heading small {
  color: #49d6c6;
  font: 7px ui-monospace, monospace;
  letter-spacing: 0.12em;
}

.demo-access-heading b {
  margin-top: 4px;
  color: #c2d4d5;
  font-size: 8px;
}

.demo-access-heading > span {
  color: #58757a;
  font-size: 7px;
  white-space: nowrap;
}

.demo-role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
  margin-top: 12px;
}

.role-card {
  width: 100%;
  display: grid;
  grid-template-columns: 31px 1fr;
  gap: 6px 9px;
  padding: 10px;
  text-align: left;
  border: 1px solid #253d41;
  border-radius: 9px;
  background: #091417;
  color: #9bc5c6;
  cursor: pointer;
}

.role-card:hover {
  border-color: #3e6669;
  background: #102126;
}

.role-card.active {
  border-color: #47d8c8;
  background: #10282b;
  box-shadow: inset 0 0 0 1px rgba(71, 216, 200, 0.25);
}

.role-card > span {
  grid-row: 1;
  display: grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border: 1px solid #31565a;
  border-radius: 7px;
  color: #4ad8c8;
  font: 700 8px ui-monospace, monospace;
}

.role-card div {
  min-width: 0;
}

.role-card b,
.role-card code {
  display: block;
}

.role-card b {
  color: #edf7f6;
  font-size: 10px;
}

.role-card code {
  margin-top: 3px;
  overflow: hidden;
  color: #6e9296;
  font: 7px ui-monospace, monospace;
  text-overflow: ellipsis;
}

.role-card small {
  grid-column: 1 / -1;
  color: #5d7a7f;
  font-size: 7px;
  line-height: 1.4;
}

.auth-form > label,
.register-grid label {
  display: block;
  margin: 0 0 15px;
  color: #8da2a5;
  font-size: 10px;
}

.auth-form input {
  width: 100%;
  margin-top: 7px;
  border: 1px solid #304449;
  border-radius: 8px;
  background: #080e11;
  color: #eef6f5;
  padding: 12px 13px;
  outline: none;
  font-size: 12px;
}

.register-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

fieldset {
  margin: 0 0 14px;
  padding: 0;
  border: 0;
}

legend {
  margin-bottom: 7px;
  color: #8da2a5;
  font-size: 10px;
}

.application-role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

.application-role-grid button {
  min-height: 82px;
  padding: 10px;
  text-align: left;
  border: 1px solid #2a3d42;
  border-radius: 9px;
  background: #10191d;
  color: #d8e7e6;
  cursor: pointer;
}

.application-role-grid button.active {
  border-color: #47d8c8;
  background: #10282b;
  box-shadow: inset 0 0 0 1px rgba(71, 216, 200, 0.25);
}

.application-role-grid b,
.application-role-grid small {
  display: block;
}

.application-role-grid small {
  margin-top: 7px;
  color: #668287;
  font-size: 8px;
  line-height: 1.4;
}

.password-policy {
  margin: -4px 0 13px;
  color: #668287;
  font-size: 9px;
}

.registration-complete {
  padding: 26px 8px;
  text-align: center;
}

.registration-complete > span {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border: 1px solid #47d8c8;
  border-radius: 50%;
  color: #47d8c8;
  font-size: 22px;
}

.registration-complete p {
  margin-bottom: 20px;
  color: #8bb5b7;
}

.auth-form input:focus {
  border-color: #47d8c8;
  box-shadow: 0 0 0 2px rgba(71, 216, 200, 0.13);
}

.password-field {
  display: flex;
}

.password-field input {
  margin: 6px 0 0;
}

.password-field button {
  margin-top: 6px;
  border: 1px solid #304449;
  border-left: 0;
  border-radius: 0 8px 8px 0;
  background: #152126;
  color: #8aa1a5;
  padding: 0 12px;
  font-size: 9px;
  cursor: pointer;
}

.password-field input {
  border-radius: 8px 0 0 8px;
}

.auth-submit {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #3fd1c0;
  border-radius: 9px;
  background: linear-gradient(100deg, #147c73, #176b70);
  color: #f3fffd;
  padding: 13px 14px;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(25, 154, 142, 0.18);
}

.auth-submit:hover {
  background: linear-gradient(100deg, #198c82, #197c82);
}

.auth-submit b {
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.08em;
}

.auth-submit:disabled {
  opacity: 0.55;
  cursor: wait;
}

.auth-message {
  padding: 10px;
  border-left: 2px solid;
  font-size: 9px;
  line-height: 1.5;
}

.auth-message.error {
  border-color: #f48771;
  background: #2e1717;
  color: #f5b0a3;
}

.auth-message.success {
  border-color: #4ec9b0;
  background: #102820;
  color: #a6e3d8;
}

.security-note {
  margin-top: 14px;
  padding: 11px 12px;
  border: 1px solid #263f43;
  border-radius: 9px;
  background: #0b181b;
}

.security-note b,
.security-note span {
  display: block;
}

.security-note b {
  color: #47d8c8;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.1em;
}

.security-note span {
  margin-top: 5px;
  color: #668287;
  font-size: 8px;
  line-height: 1.5;
}

@media (max-width: 1080px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-context {
    min-height: auto;
    padding: 28px clamp(24px, 6vw, 64px);
  }

  .hero-copy h1 {
    font-size: clamp(42px, 9vw, 68px);
  }

  .auth-form-panel {
    min-height: 760px;
    padding: 48px 24px;
  }
}

@media (max-width: 640px) {
  .auth-context {
    gap: 19px;
    padding: 22px 18px;
  }

  .auth-form-panel {
    padding: 20px 12px;
  }

  .auth-form {
    padding: 22px 18px;
  }

  .register-grid,
  .application-role-grid,
  .runtime-metrics {
    grid-template-columns: 1fr;
  }

  .demo-access-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .demo-role-grid {
    grid-template-columns: 1fr;
  }

  .module-rack {
    grid-template-columns: 1fr 1fr;
  }

  .signal-flow {
    grid-template-columns: auto 1fr auto;
  }

  .signal-flow > :nth-child(4),
  .signal-flow > :nth-child(5),
  .signal-flow > :nth-child(6),
  .signal-flow > :nth-child(7) {
    display: none;
  }

  .project-disclosure summary small,
  .panel-heading > span {
    display: none;
  }

  .system-footer {
    flex-direction: column;
  }

  .system-header {
    align-items: flex-start;
  }

  .runtime-live {
    padding-top: 8px;
    font-size: 7px;
  }
}

/* PLC identity palette: carbon cabinet, amber HMI indicators. */
.auth-shell {
  background: #0b0a08;
  color: #e4dac9;
}

.auth-context {
  background:
    linear-gradient(rgba(255, 180, 74, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 180, 74, 0.035) 1px, transparent 1px),
    radial-gradient(circle at 12% 8%, rgba(255, 180, 74, 0.17), transparent 28%),
    radial-gradient(circle at 85% 58%, rgba(119, 70, 22, 0.18), transparent 32%),
    #100e0a;
  border-color: #3b3021;
}

.system-header,
.plc-console,
.console-topbar,
.project-disclosure,
.project-disclosure summary,
.system-footer {
  border-color: #403421;
}

.system-brand b,
.hero-copy h1,
.hero-copy h2,
.auth-title h1,
.panel-heading b {
  color: #fff8eb;
}

.system-brand small,
.hero-copy > p:first-child,
.hero-copy h1 span,
.runtime-live,
.auth-title small,
.panel-heading small,
.role-card.active b {
  color: #ffb44a;
}

.runtime-live i,
.module-leds i,
.runtime-metrics b i {
  background: #75d59b;
}

.plc-console {
  background: rgba(19, 16, 11, 0.9);
  box-shadow: 0 26px 80px rgba(0, 0, 0, 0.4);
}

.console-topbar,
.module-rack article,
.runtime-metrics article,
.auth-tabs,
.security-note {
  background: #1a1712;
}

.console-topbar > div i:first-child,
.console-topbar > span,
.signal-flow i,
.password-field button {
  color: #ffb44a;
}

.module-rack article,
.runtime-metrics article,
.role-card,
.auth-form input,
.application-role-grid button,
.security-note {
  border-color: #453925;
}

.module-rack span,
.runtime-metrics span,
.project-disclosure summary,
.project-disclosure li,
.hero-description,
.auth-title p,
.role-card small {
  color: #9e907c;
}

.auth-form-panel {
  background:
    radial-gradient(circle at 100% 0, rgba(255, 180, 74, 0.09), transparent 30%),
    linear-gradient(155deg, #15110c, #0b0a08 74%);
}

.auth-form {
  background:
    linear-gradient(145deg, rgba(54, 43, 27, 0.58), rgba(15, 12, 9, 0.9)),
    #13110e;
  border-color: #4a3c28;
}

.auth-tabs button.active,
.role-card.active,
.application-role-grid button.active,
.auth-form input:focus {
  color: #ffc66f;
  background: #2a2115;
  border-color: #ffb44a;
  box-shadow: inset 0 0 0 1px rgba(255, 180, 74, 0.2);
}

.auth-submit {
  color: #251504;
  background: linear-gradient(100deg, #ffb44a, #db8d37);
  border-color: #ffc66f;
  box-shadow: 0 12px 30px rgba(219, 141, 55, 0.2);
}

.auth-submit:hover {
  background: linear-gradient(100deg, #ffc66f, #e99a3d);
}
</style>
