<script setup>
// 統一 loading / error / empty 三態，頁面只要包住內容即可。
defineProps({
  loading: Boolean,
  error: String,
  empty: Boolean,
  emptyText: { type: String, default: '沒有資料' },
})
</script>

<template>
  <div v-if="loading" class="loading">載入中…</div>
  <div v-else-if="error" class="error">⚠ {{ error }}</div>
  <div v-else-if="empty" class="empty">{{ emptyText }}</div>
  <slot v-else />
</template>
