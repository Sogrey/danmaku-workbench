<script setup lang="ts">
import { computed } from 'vue'
import { CATEGORIES, SCORE_LEVELS, TARGET_NAMES, THRESHOLDS } from '@/config/criteria'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

const record = computed(() => ui.drawerRecord)

const pretty = computed(() => {
  if (!record.value) return ''
  const { decision, disposition } = record.value
  return JSON.stringify(
    {
      model_input: { state: record.value.text, lesson_topic: '（见 config/criteria.ts）' },
      questions: {
        category: {
          type: 'choice',
          instructions: '这条弹幕属于哪一类？',
          criteria: Object.fromEntries(
            Object.values(CATEGORIES).map((c) => [c.id, c.description]),
          ),
        },
        actionable: {
          type: 'noul',
          instructions: '信息是否足够开始处理？',
        },
        priority: {
          type: 'score',
          instructions: '对当前跟课的影响等级？',
          criteria: SCORE_LEVELS,
        },
      },
      answers: {
        category: {
          type: 'choice',
          choice: decision.choice.category,
          probabilities: decision.choice.probabilities,
          confidence: decision.choice.confidence,
        },
        actionable: { type: 'noul', noul: decision.noul.probability },
        priority: { type: 'score', score: decision.score.value, level: decision.score.level },
      },
      provider: decision.provider,
      latency_ms: decision.latencyMs,
      routing: {
        target: disposition.target,
        target_name: TARGET_NAMES[disposition.target],
        reason: disposition.reason,
        thresholds: THRESHOLDS,
      },
    },
    null,
    2,
  )
})

function close() {
  ui.closeDrawer()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="record" class="mask" @click.self="close">
        <aside class="drawer">
          <header class="drawer-head">
            <div>
              <h3>判断详情</h3>
              <p class="sub">#{{ record.id }} · {{ record.author }} · {{ record.time }}</p>
            </div>
            <button class="close" @click="close">✕</button>
          </header>

          <div class="drawer-body">
            <section class="block">
              <h4>弹幕原文</h4>
              <p class="origin">{{ record.text }}</p>
            </section>

            <section class="block">
              <h4>分流依据</h4>
              <p class="origin reason">{{ record.disposition.reason }}</p>
              <p class="note">
                阈值规则：分类概率 ≥ {{ THRESHOLDS.classifyProbability * 100 }}% 且处理条件概率 ≥
                {{ THRESHOLDS.actionableProbability * 100 }}% 才进入讲师/助教待办；「听课反馈」是模型选择，「交给助教」是程序规则。
              </p>
            </section>

            <section class="block">
              <h4>请求 / 响应（对齐 Jev /v1/systemone 结构）</h4>
              <pre class="json">{{ pretty }}</pre>
            </section>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 50;
}
.drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(520px, 92vw);
  background: #fff;
  border-radius: 16px 0 0 16px;
  box-shadow: var(--shadow-pop);
  display: flex;
  flex-direction: column;
}
.drawer-head {
  flex: none;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--border);
}
.drawer-head h3 { font-size: 15px; font-weight: 800; }
.sub { margin-top: 3px; font-size: 12px; color: var(--text-3); }
.close {
  width: 30px; height: 30px;
  border-radius: 8px;
  color: var(--text-2);
  font-size: 14px;
  display: flex; align-items: center; justify-content: center;
}
.close:hover { background: #f2f5fa; }
.drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.block h4 {
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text-2);
  margin-bottom: 7px;
}
.origin {
  font-size: 13.5px;
  color: var(--text);
  line-height: 1.6;
  word-break: break-word;
  background: #f6f8fc;
  border-radius: 8px;
  padding: 9px 11px;
}
.reason { background: var(--primary-soft); }
.note {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-3);
  line-height: 1.65;
}
.json {
  background: #0d1830;
  color: #c9e0ff;
  border-radius: 10px;
  padding: 13px 14px;
  font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
  font-size: 11.5px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}

/* 过渡 */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.22s ease;
}
.drawer-enter-active .drawer,
.drawer-leave-active .drawer {
  transition: transform 0.26s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer,
.drawer-leave-to .drawer {
  transform: translateX(100%);
}
</style>
