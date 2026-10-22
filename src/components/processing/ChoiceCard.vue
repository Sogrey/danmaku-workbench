<script setup lang="ts">
import { computed } from 'vue'
import type { DecisionResult } from '@/types'
import { CATEGORIES, CATEGORY_ORDER } from '@/config/criteria'

const props = defineProps<{
  decision?: DecisionResult
  loading?: boolean
}>()

defineEmits<{ details: [] }>()

const main = computed(() => {
  if (!props.decision) return null
  const cat = props.decision.choice.category
  return { def: CATEGORIES[cat], p: props.decision.choice.probabilities[cat] }
})

const segments = computed(() => {
  if (!props.decision) return []
  return CATEGORY_ORDER.map((c) => ({
    id: c,
    color: CATEGORIES[c].color,
    width: `${(props.decision!.choice.probabilities[c] * 100).toFixed(2)}%`,
  }))
})
</script>

<template>
  <div class="card">
    <div class="card-head">
      <div class="card-title">
        <span class="icon">🎯</span>
        <div>
          <b>Choice · 分类</b>
          <small>观众需要什么帮助</small>
        </div>
      </div>
      <span v-if="!loading && decision" class="link" @click="$emit('details')">
        查看判断详情 ↗
      </span>
    </div>

    <!-- loading -->
    <template v-if="loading">
      <div class="skeleton" style="height: 26px; width: 60%"></div>
      <div class="skeleton" style="height: 8px"></div>
      <div class="skeleton" style="height: 12px; width: 85%"></div>
    </template>

    <!-- 结果 -->
    <template v-else-if="main">
      <div class="result-row">
        <span class="chip result-chip" :class="`chip-${main.def.id}`">{{ main.def.name }}</span>
        <span class="prob">{{ (main.p * 100).toFixed(1) }}<small>%</small></span>
      </div>
      <div class="bar"><div class="bar-fill" :class="`bar-fill-${main.def.id === 'feedback' ? 'green' : main.def.id === 'technical' ? 'blue' : main.def.id === 'spam' ? 'red' : main.def.id === 'insufficient' ? 'orange' : ''}`" :style="{ width: `${main.p * 100}%` }"></div></div>
      <p class="desc">{{ main.def.description }}</p>
      <div class="dist">
        <div class="dist-bar">
          <span
            v-for="s in segments"
            :key="s.id"
            class="seg"
            :style="{ width: s.width, background: s.color }"
          ></span>
        </div>
        <p class="dist-hint">五类候选概率分布 · 置信度 {{ (decision!.choice.confidence * 100).toFixed(1) }}%（集中度 ≠ 准确率）</p>
      </div>
    </template>

    <!-- 等待 -->
    <p v-else class="waiting">等待判断：识别技术提问、听课反馈及其他课堂消息。</p>
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
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 9px;
}
.card-title b {
  display: block;
  font-size: 13.5px;
  color: var(--text);
}
.card-title small {
  display: block;
  font-size: 11.5px;
  color: var(--text-3);
  margin-top: 1px;
}
.icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: #eff4ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex: none;
}
.result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.result-chip { font-size: 13px; padding: 3px 12px; }
.prob {
  font-size: 22px;
  font-weight: 800;
  color: var(--primary-deep);
  font-variant-numeric: tabular-nums;
}
.prob small { font-size: 12px; font-weight: 700; margin-left: 1px; }
.desc {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.55;
}
.dist-bar {
  display: flex;
  height: 6px;
  border-radius: 4px;
  overflow: hidden;
  background: #edf1f7;
}
.seg { display: block; transition: width 0.5s; }
.dist-hint {
  margin-top: 5px;
  font-size: 11px;
  color: var(--text-3);
}
.waiting {
  font-size: 12px;
  color: var(--text-3);
  line-height: 1.6;
}
</style>
