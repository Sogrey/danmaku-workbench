<script setup lang="ts">
import { ref } from 'vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()
const draft = ref('')

function send() {
  if (!draft.value.trim()) return
  wb.pushMessage(draft.value, true)
  draft.value = ''
}
</script>

<template>
  <div class="input-area">
    <div class="input-row">
      <input
        v-model="draft"
        class="input"
        type="text"
        placeholder="输入技术问题或声音、画面等听课反馈..."
        maxlength="120"
        @keydown.enter.prevent="send"
      />
      <button class="send-btn" :disabled="!draft.trim()" @click="send">发送</button>
    </div>
    <p class="hint">技术提问由讲师答疑 · 听课问题由助教跟进</p>
  </div>
</template>

<style scoped>
.input-area {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.input-row {
  display: flex;
  gap: 8px;
}
.input {
  flex: 1;
  min-width: 0;
  height: 38px;
  padding: 0 13px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: #f8fafd;
  outline: none;
  font-size: 13px;
  transition: all 0.18s;
}
.input:focus {
  background: #fff;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(47, 107, 255, 0.12);
}
.input::placeholder {
  color: var(--text-3);
}
.send-btn {
  flex: none;
  height: 38px;
  padding: 0 20px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #4f8bff, var(--primary));
  transition: all 0.18s;
}
.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.send-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(47, 107, 255, 0.3);
}
.hint {
  font-size: 11.5px;
  color: var(--text-3);
  padding-left: 2px;
}
</style>
