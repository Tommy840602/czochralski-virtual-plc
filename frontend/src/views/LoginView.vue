<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('admin')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const data = await api.login(username.value, password.value)
    auth.setSession(data)
    router.replace(route.query.redirect || '/overview')
  } catch (e) {
    error.value = e.message || '登入失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <aside class="disclaimer">
      <h2>⚠ 聲明 Disclaimer</h2>
      <p class="disclaimer-lead">本專案為個人面試展示用途，所有製程資料皆為模擬 / 亂數生成。</p>
      <ol>
        <li>本專案為個人面試展示用途，所有爐子模具圖、設備示意圖與熱場模擬圖皆由 AI 生成或基於模擬情境自行設計，並非取自任何公司、客戶、供應商或第三方之內部圖面、實機照片、工程文件或專有設計資料。</li>
        <li>展示中之分析報告與技術說明為 AI 輔助產生之模擬內容，未引用、改寫、揭露或還原任何內部技術文件、SOP、製程規範、設備手冊或商業資料。所有製程參數、感測數值、爐台狀態、警報事件、品質數據與報表內容皆為亂數生成或模擬資料，僅供系統架構與技術能力展示，不代表任何實際產線、設備、製程、配方或生產條件。</li>
        <li>本專案所展示之軟體架構、資料流程、系統模組、通訊方式、服務切分、資料庫設計與部署方式皆為模擬設計，僅用於展示個人開發與系統設計能力，與任何實際公司、產線、設備或既有系統之真實架構無關。</li>
        <li>本專案之命名、畫面配置、功能模組、資料表欄位、API 設計、系統架構圖與展示流程，皆為個人基於公開技術知識與模擬需求自行設計，未參考、複製、改寫、還原或對應任何特定公司、客戶、供應商或既有系統之內部架構、程式碼、資料模型、網路拓樸、權限設計、製程邏輯或維運流程。</li>
        <li>本專案不具備實際生產控制用途，亦不應視為可直接導入現場之正式工控系統、MES、SCADA、EAP 或品質管理系統。</li>
      </ol>
    </aside>

    <form class="login-card" @submit.prevent="submit">
      <div class="login-brand">
        <h1>PLC Research Platform</h1>
        <span>可程式邏輯控制器研究平台</span>
      </div>

      <label>帳號</label>
      <input v-model="username" type="text" autocomplete="username" placeholder="使用者名稱" />

      <label>密碼</label>
      <input v-model="password" type="password" autocomplete="current-password" placeholder="密碼" />

      <div v-if="error" class="error" style="margin: 4px 0">⚠ {{ error }}</div>

      <button class="btn primary" type="submit" :disabled="loading || !password" style="margin-top: 6px">
        {{ loading ? '登入中…' : '登入' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 48px 24px;
  background: var(--bg);
}
.disclaimer {
  width: 480px;
  flex-shrink: 0;
  font-size: 11.5px;
  color: var(--text-dim);
}
.disclaimer h2 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 620;
  letter-spacing: 0.4px;
  color: var(--warn);
}
.disclaimer-lead {
  margin: 0 0 14px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.disclaimer ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.75;
}
.disclaimer li {
  margin-bottom: 10px;
}
.disclaimer li:last-child {
  margin-bottom: 0;
}

/* 窄螢幕改為上下堆疊 */
@media (max-width: 860px) {
  .login-wrap {
    flex-direction: column;
    gap: 28px;
  }
  .disclaimer {
    width: 100%;
    max-width: 420px;
    order: 2;
  }
}
.login-card {
  width: 320px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 30px 28px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 5px;
}
/* 頂部一條 accent，取代花俏漸層 */
.login-card::before {
  content: '';
  display: block;
  height: 2px;
  width: 34px;
  background: var(--accent);
  border-radius: 2px;
  margin: 0 auto 18px;
}
.login-brand {
  text-align: center;
  margin-bottom: 18px;
}
.login-brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 620;
}
.login-brand span {
  font-size: 10.5px;
  color: var(--text-faint);
  letter-spacing: 0.4px;
  text-transform: uppercase;
}
.login-card label {
  font-size: 11px;
  color: var(--text-faint);
  letter-spacing: 0.4px;
  text-transform: uppercase;
  margin-top: 10px;
}
.login-card input {
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  color: var(--text);
  border-radius: 6px;
  padding: 9px 11px;
  font-size: 13.5px;
  outline: none;
}
.login-card input:focus {
  border-color: var(--accent);
}
.login-card .btn.primary {
  padding: 10px;
  font-size: 13.5px;
  margin-top: 8px;
}
</style>
