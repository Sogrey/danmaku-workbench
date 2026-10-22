<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { CATEGORIES } from '@/config/criteria'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()
const listEl = ref<HTMLElement | null>(null)

const AVATAR_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee']

function avatarColor(id: string) {
  let h = 0
  for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

/** 状态标签 */
import { computed } from 'vue'
const statusChip = (m: (typeof wb.messages)[number]) => {
  switch (m.status) {
    case 'pending':
      return { cls: 'chip-chat', text: '待判断' }
    case 'judging':
      return { cls: 'chip-judging', text: '正在查看', dot: true }
    case 'failed':
      return { cls: 'chip-failed', text: '判断失败 · 点击重试' }
    case 'done': {
      const cat = CATEGORIES[m.label!]
      return { cls: `chip-${cat.id}`, text: cat.name }
    }
  }
}

/** 跟随最新：滚动到底部 */
watch(
  () => wb.visibleMessages.length,
  async () => {
    if (!wb.following) return
    await nextTick()
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  },
)

function onRowClick(id: string) {
  const msg = wb.messages.find((m) => m.id === id)
  if (msg?.status === 'failed') {
    wb.retryMessage(id)
  }
  wb.selectMessage(id)
}
</script>

<template>
  <div class="list-wrap">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="segmented">
        <button :class="{ on: wb.filter === 'all' }" @click="wb.filter = 'all'">全部弹幕</button>
        <button :class="{ on: wb.filter === 'technical' }" @click="wb.filter = 'technical'">
          只看技术提问
        </button>
      </div>
      <label class="follow">
        <input type="checkbox" v-model="wb.following" />
        跟随最新
      </label>
    </div>

    <!-- 消息列表 -->
    <div class="list" ref="listEl">
      <div v-if="wb.visibleMessages.length === 0" class="empty">
        <div class="empty-icon">💬</div>
        本场还没有弹幕，开始直播后查看观众消息，<br />也可以在下方录入一条提问。
      </div>

      <button
        v-for="m in wb.visibleMessages"
        :key="m.id"
        class="msg"
        :class="{ selected: wb.selectedId === m.id }"
        @click="onRowClick(m.id)"
      >
        <span class="avatar" :style="{ background: avatarColor(m.id) }">{{ m.author[0] }}</span>
        <div class="msg-body">
          <div class="msg-meta">
            <span class="author">{{ m.author }}</span>
            <span class="time">{{ m.time }}</span>
            <span v-if="m.manual" class="manual-tag">手动录入</span>
          </div>
          <div class="msg-text">{{ m.text }}</div>
        </div>
        <span class="chip" :class="statusChip(m).cls">
          <span v-if="statusChip(m).dot" class="chip-dot"></span>
          {{ statusChip(m).text }}
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.list-wrap {
  flex: 1;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: none;
}
.segmented {
  display: inline-flex;
  background: #f0f3f9;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 2px;
}
.segmented button {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  transition: all 0.18s;
}
.segmented button.on {
  background: #fff;
  color: var(--primary-deep);
  box-shadow: 0 1px 4px rgba(23, 35, 60, 0.1);
}
.follow {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-2);
  cursor: pointer;
  user-select: none;
}
.follow input {
  accent-color: var(--primary);
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-right: 4px;
}
.msg {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  text-align: left;
  transition: all 0.16s;
}
.msg:hover {
  background: #f6f9ff;
}
.msg.selected {
  background: var(--primary-soft);
  border-color: #c7dbfe;
}
.avatar {
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 7px;
}
.author {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-2);
}
.time {
  font-size: 11px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
.manual-tag {
  font-size: 10px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 4px;
  padding: 0 4px;
}
.msg-text {
  margin-top: 2px;
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.45;
  word-break: break-word;
}
</style>
