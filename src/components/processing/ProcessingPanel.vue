<script setup lang="ts">
import { computed } from 'vue'
import ChoiceCard from './ChoiceCard.vue'
import NoulCard from './NoulCard.vue'
import ScoreCard from './ScoreCard.vue'
import DispositionCard from './DispositionCard.vue'
import { useWorkbenchStore } from '@/stores/workbench'
import { useUiStore } from '@/stores/ui'
import { TARGET_NAMES } from '@/config/criteria'

const wb = useWorkbenchStore()
const ui = useUiStore()

const msg = computed(() => wb.currentMessage)
const record = computed(() =>
  msg.value ? wb.records.find((r) => r.id === msg.value!.id) ?? null : null,
)

const phase = computed<'empty' | 'loading' | 'done' | 'failed' | 'pending'>(() => {
  const m = msg.value
  if (!m) return 'empty'
  if (m.status === 'judging' || m.status === 'pending') return 'loading'
  if (m.status === 'failed') return 'failed'
  return 'done'
})

function openDetails() {
  if (record.value) ui.openDrawer(record.value)
}

function goRecords() {
  ui.switchView('records')
}
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div>
        <div class="panel-title"><span class="no">02</span> 当前消息处理</div>
        <div class="panel-sub">选择一条弹幕，查看消息类型和处理去向。</div>
      </div>
      <span v-if="phase === 'done'" class="badge badge-ok">判断完成</span>
    </header>

    <!-- 当前消息 -->
    <div class="current-msg" v-if="msg">
      <span class="badge badge-plain current-tag">当前弹幕</span>
      <div class="current-text">{{ msg.text }}</div>
    </div>

    <!-- 空态 -->
    <div v-if="phase === 'empty'" class="empty big">
      <div class="empty-icon">🖱️</div>
      选择左侧一条弹幕，<br />查看消息类型和处理去向
    </div>

    <!-- 失败降级（保留原文 · 可重试） -->
    <template v-if="phase === 'failed'">
      <div class="error-card">
        <div class="error-title">真实请求失败：DecisionEngineError</div>
        <p class="error-text">
          此条保持未判断，不会进入任何待办队列；原文已在左侧保留，可稍后重试。
        </p>
        <button class="retry-btn" @click="wb.retryMessage(msg!.id)">稍后重试判断</button>
      </div>
      <div class="rule-bar">
        <p>分类概率 ≥ 60% 且处理条件概率 ≥ 80%，进入讲师/助教待办；其余进入待确认流程。</p>
      </div>
    </template>

    <!-- 判断中 -->
    <template v-if="phase === 'loading'">
      <ChoiceCard :loading="true" />
      <NoulCard :loading="true" />
      <ScoreCard :loading="true" />
      <div class="judge-status">
        <span class="chip-dot" style="background: var(--primary)"></span>
        正在判断中…（决策引擎 {{ wb.providerDesc }}）
      </div>
    </template>

    <!-- 判断完成 -->
    <template v-if="phase === 'done' && msg && msg.decision">
      <ChoiceCard :decision="msg.decision" @details="openDetails" />
      <NoulCard :decision="msg.decision" />
      <ScoreCard :decision="msg.decision" />
      <DispositionCard :disposition="msg.disposition!" :score="msg.decision.score" @chain="openDetails" />
      <div class="rule-bar">
        <p>
          分类概率 ≥ 60% 且处理条件概率 ≥ 80%，进入讲师/助教待办；其余进入用户确认流程。
        </p>
        <span class="link" @click="goRecords">查看分类规则与记录 ↗</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  padding: 14px;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  flex: none;
}
.panel-sub {
  margin-top: 3px;
  font-size: 12px;
  color: var(--text-3);
}
.current-msg {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #f4f8ff, #eef4ff);
  border: 1px solid #d9e6ff;
}
.current-tag { align-self: flex-start; font-size: 11px; padding: 2px 8px; }
.current-text {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--text);
  word-break: break-word;
}
.empty.big {
  flex: 1;
  justify-content: center;
  gap: 10px;
  font-size: 13px;
  line-height: 1.7;
}
.error-card {
  flex: none;
  border: 1px solid #fecaca;
  background: var(--red-soft);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.error-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #b91c1c;
}
.error-text {
  font-size: 12.5px;
  color: #7f1d1d;
  line-height: 1.6;
}
.retry-btn {
  align-self: flex-start;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 700;
  color: #b91c1c;
  border: 1px solid #fca5a5;
  background: #fff;
  transition: all 0.18s;
}
.retry-btn:hover { background: #fee2e2; }
.judge-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-2);
  padding: 4px 2px;
}
.judge-status .chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: chip-pulse 1s ease-in-out infinite;
}
.rule-bar {
  flex: none;
  margin-top: 2px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: #f6f8fc;
  border: 1px dashed var(--border-strong);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.rule-bar p {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.5;
}
</style>
