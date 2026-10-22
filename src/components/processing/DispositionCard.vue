<script setup lang="ts">
import type { Disposition, ScoreResult } from '@/types'
import { CATEGORIES, TARGET_NAMES } from '@/config/criteria'

const props = defineProps<{
  disposition: Disposition
  score: ScoreResult
}>()

defineEmits<{ chain: [] }>()

const ICONS: Record<string, string> = {
  instructor: '🙋',
  assistant: '🛠️',
  confirm: '❓',
  none: '💬',
}
</script>

<template>
  <div class="card disposition" :class="`target-${disposition.target}`">
    <div class="card-head">
      <div class="card-title">
        <span class="icon">{{ ICONS[disposition.target] }}</span>
        <div>
          <b>处理安排</b>
          <small>由谁跟进这条消息（程序规则）</small>
        </div>
      </div>
      <span class="link" @click="$emit('chain')">查看链路 ↗</span>
    </div>

    <div class="verdict">
      <template v-if="disposition.target === 'instructor'">
        ✅ 已加入 <b>讲师待答</b>，技术问题将集中给讲师答疑。
      </template>
      <template v-else-if="disposition.target === 'assistant'">
        ✅ 已加入 <b>助教处理</b>，请助教检查声音、画面或跟课情况，处理后标记完成。
      </template>
      <template v-else-if="disposition.target === 'confirm'">
        ⏳ 已加入 <b>待确认</b>，模糊或疑似干扰消息，先由人工核对。
      </template>
      <template v-else>💬 保留在直播弹幕区，不进入待办。</template>
    </div>

    <div class="reason">
      <p class="reason-title">分流依据</p>
      <p class="reason-text">{{ disposition.reason }}</p>
    </div>

    <div class="meta-row">
      <span class="badge badge-plain">去向：<b>{{
        TARGET_NAMES[disposition.target] ?? '留在弹幕区'
      }}</b></span>
      <span class="badge badge-plain">优先级：<b>{{ score.value.toFixed(2) }} / 3</b></span>
    </div>
  </div>
</template>

<style scoped>
.card {
  flex: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 13px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  background: #fff;
}
.card.target-instructor { border-color: #c7dbfe; background: linear-gradient(180deg, #f5f9ff, #fff); }
.card.target-assistant { border-color: #a7f3d0; background: linear-gradient(180deg, #f2fdf9, #fff); }
.card.target-confirm { border-color: #fde68a; background: linear-gradient(180deg, #fffdf5, #fff); }
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.card-title { display: flex; align-items: center; gap: 9px; }
.card-title b { display: block; font-size: 13.5px; color: var(--text); }
.card-title small { display: block; font-size: 11.5px; color: var(--text-3); margin-top: 1px; }
.icon {
  width: 32px; height: 32px; border-radius: 9px;
  background: #f2f5fa;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex: none;
}
.verdict {
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.6;
}
.verdict b { color: var(--primary-deep); }
.reason {
  border-radius: 8px;
  background: #f6f8fc;
  border: 1px dashed var(--border-strong);
  padding: 8px 10px;
}
.reason-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-3);
  margin-bottom: 3px;
}
.reason-text {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.55;
}
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-row .badge b { margin-left: 4px; color: var(--text); }
</style>
