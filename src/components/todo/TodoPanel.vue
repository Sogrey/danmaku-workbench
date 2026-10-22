<script setup lang="ts">
import { computed } from 'vue'
import type { WorkRecord } from '@/types'
import { CATEGORIES, TARGET_NAMES } from '@/config/criteria'
import { useTodoStore } from '@/stores/todo'
import { useUiStore } from '@/stores/ui'

const todo = useTodoStore()
const ui = useUiStore()

const TABS = [
  { key: 'instructor', name: '讲师待答', icon: '🙋' },
  { key: 'assistant', name: '助教处理', icon: '🛠️' },
  { key: 'confirm', name: '待确认', icon: '❓' },
] as const

const queue = computed(() => todo.activeQueue)

const TARGET_TONE: Record<string, string> = {
  instructor: 'tone-instructor',
  assistant: 'tone-assistant',
  confirm: 'tone-confirm',
}

function catChip(r: WorkRecord) {
  return CATEGORIES[r.decision.choice.category]
}
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div>
        <div class="panel-title"><span class="no">03</span> 课堂待办</div>
        <div class="panel-sub">讲师与助教按优先级跟进，同分类按接收顺序。</div>
      </div>
      <span class="badge badge-plain">待办 {{ todo.counts.total }}</span>
    </header>

    <!-- 队列 tabs -->
    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab"
        :class="{ active: todo.activeTab === t.key, [TARGET_TONE[t.key]]: todo.activeTab === t.key }"
        @click="todo.activeTab = t.key"
      >
        {{ t.icon }} {{ t.name }}
        <span class="count">{{ todo.counts[t.key] }}</span>
      </button>
    </div>

    <!-- 队列列表 -->
    <div class="queue">
      <div v-if="queue.length === 0" class="empty">
        <div class="empty-icon">📭</div>
        <template v-if="todo.activeTab === 'instructor'">
          当前没有待回答的技术问题，<br />新提问完成分类后会进入这里。
        </template>
        <template v-else-if="todo.activeTab === 'assistant'">
          暂无需要助教处理的消息。
        </template>
        <template v-else>暂无待确认的消息。</template>
      </div>

      <div v-for="r in queue" :key="r.id" class="todo-card" :class="TARGET_TONE[r.disposition.target]">
        <div class="todo-meta">
          <span class="author">👤 {{ r.author }}</span>
          <span class="time">{{ r.time }}</span>
        </div>
        <p class="todo-text">{{ r.text }}</p>
        <div class="todo-tags">
          <span class="chip" :class="`chip-${catChip(r).id}`">{{ catChip(r).name }}</span>
          <span class="score-tag">{{ r.decision.score.level }} · {{ r.decision.score.value.toFixed(2) }}/3</span>
        </div>
        <div class="todo-actions">
          <button class="done-btn" @click="todo.markDone(r.id)">✅ 标记已处理</button>
          <span class="link" @click="ui.openDrawer(r)">查看链路</span>
        </div>
      </div>
    </div>

    <p class="foot-note">ℹ️ 标记完成后移出待办，仍可从左侧弹幕查看。</p>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  padding: 14px;
}
.panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; flex: none; }
.panel-sub { margin-top: 3px; font-size: 12px; color: var(--text-3); }

.tabs {
  flex: none;
  display: flex;
  gap: 6px;
}
.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 4px;
  border-radius: 9px;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-2);
  background: #f2f5fa;
  border: 1px solid transparent;
  transition: all 0.18s;
}
.tab:hover { background: #eaeef6; }
.tab.active.tone-instructor { color: #1d4ed8; background: #eff6ff; border-color: #c7dbfe; }
.tab.active.tone-assistant { color: #047857; background: #ecfdf5; border-color: #a7f3d0; }
.tab.active.tone-confirm { color: #b45309; background: #fffbeb; border-color: #fde68a; }
.count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(23, 35, 60, 0.08);
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-variant-numeric: tabular-nums;
}
.tab.active .count { background: rgba(255, 255, 255, 0.75); }

.queue {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 4px;
}
.todo-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  background: #fff;
}
.todo-card.tone-instructor { border-left: 3px solid var(--primary); }
.todo-card.tone-assistant { border-left: 3px solid var(--green); }
.todo-card.tone-confirm { border-left: 3px solid var(--orange); }
.todo-meta { display: flex; align-items: center; justify-content: space-between; }
.author { font-size: 12px; font-weight: 700; color: var(--text-2); }
.time { font-size: 11px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.todo-text {
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.5;
  word-break: break-word;
}
.todo-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.score-tag {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--primary-deep);
  background: var(--primary-soft);
  border-radius: 999px;
  padding: 2px 9px;
}
.todo-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 1px; }
.done-btn {
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-deep);
  background: #fff;
  border: 1px solid #c7dbfe;
  transition: all 0.18s;
}
.done-btn:hover { background: var(--primary-soft); transform: translateY(-1px); }
.foot-note { flex: none; font-size: 11.5px; color: var(--text-3); }
</style>
