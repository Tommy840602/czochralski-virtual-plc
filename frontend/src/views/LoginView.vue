<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const localDemoMode = import.meta.env.DEV
const operatorAccount = {
  username: localDemoMode ? 'admin' : 'plc.operator',
  department: 'PLC',
  role: 'Operator',
  access: 'Sequence、Interlock、Actuator 與製程模擬操作',
}
const disclosureItems = [
  '本專案為個人面試展示用途，所有爐子模具圖、設備示意圖與熱場模擬圖皆由 AI 生成或基於模擬情境自行設計，並非取自任何公司、客戶、供應商或第三方之內部圖面、實機照片、工程文件或專有設計資料。',
  '展示中之分析報告與技術說明為 AI 輔助產生之模擬內容，未引用、改寫、揭露或還原任何內部技術文件、SOP、製程規範、設備手冊或商業資料。所有製程參數、感測數值、爐台狀態、警報事件、品質數據與報表內容皆為亂數生成或模擬資料。',
  '本專案所展示之軟體架構、資料流程、系統模組、通訊方式、服務切分、資料庫設計與部署方式皆為模擬設計，僅用於展示個人開發與系統設計能力。',
  '本專案之命名、畫面配置、功能模組、資料表欄位、API 設計與展示流程皆為個人基於公開技術知識與模擬需求自行設計，未對應任何實際公司或產線。',
  '本專案不具備實際生產控制用途，亦不應視為可直接導入現場之正式工控系統、MES、SCADA、EAP 或品質管理系統。',
]

const username = ref(operatorAccount.username)
const password = ref(localDemoMode ? 'admin0000' : '')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)

function selectOperator() {
  username.value = operatorAccount.username
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
</script>

<template>
  <main class="auth-shell">
    <section class="auth-context">
      <header>
        <div>
          <b>PLC</b>
          <small>VIRTUAL CONTROL RUNTIME</small>
        </div>
      </header>

      <div class="auth-copy">
        <p>INTERVIEW DEMONSTRATION · SIMULATION ONLY</p>
        <span>本系統僅展示個人軟體開發、設備模擬與工控整合能力；不對應任何實際公司、設備或產線。</span>
      </div>

      <section class="project-disclosure" aria-labelledby="disclosure-title">
        <div class="disclosure-heading">
          <small>PROJECT NOTICE</small>
          <h2 id="disclosure-title"># 聲明</h2>
          <span>5 ITEMS</span>
        </div>
        <ol>
          <li v-for="(item, index) in disclosureItems" :key="index">
            <b>{{ String(index + 1).padStart(2, '0') }}</b>
            <p>{{ item }}</p>
          </li>
        </ol>
      </section>

      <footer>
        <i /> FASTAPI AUTH · HMAC TOKEN
        <span>SINGLE OPERATOR POLICY v1</span>
      </footer>
    </section>

    <section class="auth-form-panel">
      <div class="auth-form-wrap">
        <div class="auth-tabs" role="tablist" aria-label="PLC 登入">
          <button class="active" type="button" role="tab" aria-selected="true">登入</button>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <div class="auth-title">
            <small>SECURE OPERATOR SIGN IN</small>
            <h1>登入 CZ Virtual PLC</h1>
            <p>請使用核准的 PLC 操作身份進入設備控制與模擬功能。</p>
          </div>

          <div class="demo-access">
            <div class="demo-access-heading">
              <div>
                <small>INTERVIEW DEMO ACCOUNT</small>
                <b>{{ localDemoMode ? '選擇操作身份，自動帶入本機帳密' : '選擇操作身份，密碼由展示者提供' }}</b>
              </div>
              <span>{{ localDemoMode ? 'LOCAL DEMO' : 'PROTECTED CREDENTIAL' }}</span>
            </div>

            <button class="operator-card active" type="button" @click="selectOperator">
              <span>{{ operatorAccount.department }}</span>
              <b>{{ operatorAccount.role }}</b>
              <code>{{ operatorAccount.username }}</code>
              <small>{{ operatorAccount.access }}</small>
            </button>
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
            {{ loading ? '驗證中…' : '驗證身份並進入系統' }}
            <span>→</span>
          </button>

          <div class="security-note">
            <b>{{ localDemoMode ? 'LOCAL DEMO ONLY' : 'PROTECTED INTERVIEW DEMO' }}</b>
            <span>{{ localDemoMode ? '本機開發模式可自動填入測試帳密。' : '正式站不公開、不嵌入且不自動填入展示密碼。' }}</span>
          </div>
        </form>
      </div>
    </section>
  </main>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(520px, 1.08fr) minmax(500px, 0.92fr);
  background: #1e1e1e;
  color: #d4d4d4;
}

.auth-context {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 34px 48px;
  background:
    radial-gradient(circle at 80% 20%, rgba(63, 182, 173, 0.16), transparent 34%),
    linear-gradient(145deg, #111c1a, #07100f 72%);
  border-right: 1px solid #3c3c3c;
}

.auth-context header b,
.auth-context header small {
  display: block;
}

.auth-context header b {
  font-size: 12px;
  letter-spacing: 0.16em;
}

.auth-context header small {
  margin-top: 5px;
  color: #78918c;
  font: 7px ui-monospace, monospace;
  letter-spacing: 0.13em;
}

.auth-copy {
  margin: 34px 0 22px;
}

.auth-copy > p {
  margin: 0 0 12px;
  color: #4ec9b0;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.18em;
}

.auth-copy > span {
  display: block;
  max-width: 680px;
  color: #8fa39e;
  font-size: 11px;
  line-height: 1.8;
}

.project-disclosure {
  min-height: 0;
  flex: 1;
  border: 1px solid #29443e;
  background: #081311;
}

.disclosure-heading {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 5px 12px;
  align-items: end;
  padding: 14px 18px;
  border-bottom: 1px solid #29443e;
  background: #0b1715;
}

.disclosure-heading small {
  color: #4ec9b0;
  font: 7px ui-monospace, monospace;
  letter-spacing: 0.15em;
}

.disclosure-heading h2 {
  grid-row: 2;
  margin: 0;
  color: #f0f4f3;
  font-size: 18px;
}

.disclosure-heading span {
  grid-column: 2;
  grid-row: 1 / 3;
  color: #68817a;
  font: 7px ui-monospace, monospace;
}

.project-disclosure ol {
  max-height: calc(100vh - 260px);
  overflow: auto;
  margin: 0;
  padding: 0 18px;
  list-style: none;
}

.project-disclosure li {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #1c312c;
}

.project-disclosure li:last-child {
  border-bottom: 0;
}

.project-disclosure li > b {
  color: #4ec9b0;
  font: 700 8px ui-monospace, monospace;
}

.project-disclosure li > p {
  margin: 0;
  color: #9aaba7;
  font-size: 9px;
  line-height: 1.75;
  text-align: justify;
}

.auth-context footer {
  margin-top: 18px;
  color: #68817a;
  font: 7px ui-monospace, monospace;
  letter-spacing: 0.1em;
}

.auth-context footer i {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 7px;
  border-radius: 50%;
  background: #4ec9b0;
  box-shadow: 0 0 9px #4ec9b0;
}

.auth-context footer span {
  float: right;
}

.auth-form-panel {
  display: grid;
  place-items: center;
  padding: 32px;
  background: #252526;
  overflow: auto;
}

.auth-form-wrap {
  width: min(590px, 100%);
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr;
  margin-bottom: 14px;
  border-bottom: 1px solid #3c3c3c;
}

.auth-tabs button {
  border: 0;
  background: transparent;
  color: #858585;
  padding: 12px;
  font-size: 12px;
}

.auth-tabs button.active {
  color: #fff;
  box-shadow: inset 0 -2px #3fb6ad;
}

.auth-form {
  padding: 26px;
  border: 1px solid #3c3c3c;
  background: #1e1e1e;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.33);
}

.auth-title {
  margin-bottom: 18px;
}

.auth-title small {
  color: #4ec9b0;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.15em;
}

.auth-title h1 {
  margin: 7px 0;
  font-size: 22px;
}

.auth-title p {
  margin: 0;
  color: #858585;
  font-size: 10px;
  line-height: 1.5;
}

.demo-access {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #315448;
  background: #0b1715;
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
  color: #4ec9b0;
  font: 7px ui-monospace, monospace;
  letter-spacing: 0.12em;
}

.demo-access-heading b {
  margin-top: 4px;
  color: #dcdcaa;
  font-size: 8px;
}

.demo-access-heading > span {
  color: #78918c;
  font-size: 7px;
  white-space: nowrap;
}

.operator-card {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 9px;
  margin-top: 12px;
  padding: 10px;
  text-align: left;
  border: 1px solid #29443e;
  background: #07100f;
  color: #9bcabb;
  cursor: pointer;
}

.operator-card:hover {
  border-color: #3b6b5e;
  background: #102820;
}

.operator-card.active {
  border-color: #3fb6ad;
  background: #102a2a;
  box-shadow: inset 3px 0 #3fb6ad;
}

.operator-card > span {
  grid-row: 1 / 3;
  display: grid;
  place-items: center;
  min-width: 42px;
  color: #4ec9b0;
  font: 700 9px ui-monospace, monospace;
}

.operator-card b {
  color: #f0f4f3;
  font-size: 10px;
}

.operator-card code {
  color: #9bcabb;
  font: 8px ui-monospace, monospace;
}

.operator-card small {
  grid-column: 1 / -1;
  margin-top: 3px;
  color: #68817a;
  font-size: 8px;
  line-height: 1.4;
}

.auth-form > label {
  display: block;
  margin: 0 0 13px;
  color: #a5a5a5;
  font-size: 10px;
}

.auth-form input {
  width: 100%;
  margin-top: 6px;
  border: 1px solid #4a4a4a;
  background: #111;
  color: #e8e8e8;
  padding: 10px 12px;
  outline: none;
  font-size: 12px;
}

.auth-form input:focus {
  border-color: #3fb6ad;
  box-shadow: 0 0 0 1px #3fb6ad;
}

.password-field {
  display: flex;
}

.password-field input {
  margin: 6px 0 0;
}

.password-field button {
  margin-top: 6px;
  border: 1px solid #4a4a4a;
  border-left: 0;
  background: #252526;
  color: #9d9d9d;
  padding: 0 12px;
  font-size: 9px;
  cursor: pointer;
}

.auth-submit {
  width: 100%;
  display: flex;
  justify-content: space-between;
  border: 1px solid #168d78;
  background: #0e6657;
  color: #fff;
  padding: 12px 14px;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
}

.auth-submit:hover {
  background: #117867;
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
  background: #351c19;
  color: #f5b0a3;
}

.security-note {
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid #29443e;
  background: #0b1715;
}

.security-note b,
.security-note span {
  display: block;
}

.security-note b {
  color: #4ec9b0;
  font: 8px ui-monospace, monospace;
  letter-spacing: 0.1em;
}

.security-note span {
  margin-top: 5px;
  color: #78918c;
  font-size: 8px;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-context {
    min-height: auto;
    padding: 28px;
  }

  .project-disclosure ol {
    max-height: none;
  }

  .auth-form-panel {
    padding: 28px 18px;
  }
}

@media (max-width: 560px) {
  .auth-context {
    padding: 22px;
  }

  .auth-form-panel {
    padding: 20px 12px;
  }

  .auth-form {
    padding: 22px 18px;
  }

  .demo-access-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-disclosure li {
    grid-template-columns: 26px 1fr;
  }

  .project-disclosure li > p {
    text-align: left;
  }

  .auth-context footer span {
    display: block;
    float: none;
    margin-top: 7px;
  }
}
</style>
