<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'

const data = ref({ requests: [], audit: [] })
const loading = ref(false)
const error = ref('')
const message = ref('')

const requests = computed(() => data.value.requests || [])
const audit = computed(() => data.value.audit || [])

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.accessRequests()
  } catch (e) {
    error.value = e.message || '帳號申請讀取失敗'
  } finally {
    loading.value = false
  }
}

async function decide(item, decision) {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    await api.decideAccessRequest(item.username, decision)
    message.value = `${item.username} 已${decision === 'approve' ? '核准' : '拒絕'}`
    await refresh()
  } catch (e) {
    error.value = e.message || '帳號申請處理失敗'
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section>
    <div class="page-head access-head">
      <div>
        <h2>帳號申請治理</h2>
        <p>ACCESS GOVERNANCE · PENDING 帳號必須由 PLC Lead 核准後才可登入。</p>
      </div>
      <button class="btn" :disabled="loading" @click="refresh">
        {{ loading ? '更新中…' : '重新整理' }}
      </button>
    </div>

    <p v-if="error" class="notice error">⚠ {{ error }}</p>
    <p v-if="message" class="notice success">✓ {{ message }}</p>

    <article class="card">
      <div class="section-title">
        <div>
          <span>PENDING REQUESTS</span>
          <h3>待核准帳號</h3>
        </div>
        <b>{{ requests.length }}</b>
      </div>

      <div v-if="requests.length" class="request-list">
        <div v-for="item in requests" :key="item.username" class="request-row">
          <div>
            <strong>{{ item.name }}</strong>
            <code>{{ item.username }}</code>
          </div>
          <span>{{ item.email }}</span>
          <span class="badge warn">{{ item.role }}</span>
          <time>{{ new Date(item.createdAt).toLocaleString('zh-TW', { hour12: false }) }}</time>
          <div class="actions">
            <button class="btn primary" :disabled="loading" @click="decide(item, 'approve')">核准</button>
            <button class="btn" :disabled="loading" @click="decide(item, 'reject')">拒絕</button>
          </div>
        </div>
      </div>
      <div v-else class="empty">目前沒有待核准帳號</div>
    </article>

    <article class="card audit-card">
      <div class="section-title">
        <div>
          <span>IMMUTABLE IDENTITY AUDIT</span>
          <h3>申請與核准紀錄</h3>
        </div>
      </div>
      <div class="audit-list">
        <div v-for="event in audit" :key="`${event.createdAt}-${event.subject}-${event.eventType}`" class="audit-row">
          <time>{{ new Date(event.createdAt).toLocaleString('zh-TW', { hour12: false }) }}</time>
          <code>{{ event.subject }}</code>
          <span>{{ event.eventType }}</span>
          <b :class="event.outcome === 'REJECTED' ? 'danger-text' : 'ok-text'">{{ event.outcome }}</b>
          <small>{{ event.actor }}</small>
        </div>
        <div v-if="!audit.length" class="empty">尚無身份治理紀錄</div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.access-head,
.section-title,
.request-row,
.audit-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.access-head,
.section-title {
  justify-content: space-between;
}
.section-title span {
  color: var(--accent);
  font: 9px ui-monospace, monospace;
  letter-spacing: 0.12em;
}
.section-title h3 {
  margin: 3px 0 0;
  font-size: 15px;
}
.section-title > b {
  font: 700 24px ui-monospace, monospace;
}
.request-list,
.audit-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}
.request-row {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(180px, 1.2fr) 90px 180px auto;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-2);
}
.request-row strong,
.request-row code {
  display: block;
}
.request-row code,
.audit-row code {
  color: var(--accent);
  font-size: 11px;
}
.request-row time,
.audit-row time,
.audit-row small {
  color: var(--text-faint);
  font-size: 10px;
}
.actions {
  display: flex;
  gap: 6px;
}
.audit-card {
  margin-top: 14px;
}
.audit-row {
  display: grid;
  grid-template-columns: 180px 1fr 150px 100px 1fr;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
}
.notice {
  padding: 9px 11px;
  border: 1px solid;
  border-radius: 6px;
}
.notice.error {
  color: var(--danger);
  border-color: var(--danger);
}
.notice.success {
  color: var(--ok);
  border-color: var(--ok);
}
.empty {
  padding: 32px 10px;
  color: var(--text-faint);
  text-align: center;
}
.ok-text { color: var(--ok); }
.danger-text { color: var(--danger); }
@media (max-width: 1050px) {
  .request-row,
  .audit-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
