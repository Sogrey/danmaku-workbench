<script setup lang="ts">
import { computed } from 'vue'
import type { DecisionResult } from '@/types'
import { SCORE_LEVELS } from '@/config/criteria'

const props = defineProps<{
  decision?: DecisionResult
  loading?: boolean
}>()

const score = computed(() => props.decision?.score)
const pct = computed(() => ((score.value?.value ?? 0) / 3) * 100)
const urgencyColor = computed(() => {
  const v = score.value?.levelIndex ?? 0
  return v >= 3 ? 'bar-fill-red' : v === 2 ? 'bar-fill-orange' : 'bar-fill-blue'
})
</script>

<template>
  <div class="card">
    <div class="card-head">
      <div class="card-title">
        <span class="icon">📊</span>
        <div>
          <b>Score · 优先级</b>
          <small>对当前跟课影响多大</small>
        </div>
      </div>
      <span v-if="!loading && score" class="badge badge-plain">等级 {{ score.levelIndex }}/3</span>
    </div>

    <template v-if="loading">
      <div class="skeleton" style="height: 26px; width: 45%"></div>
      <div class="skeleton" style="height: 8px"></div>
      <div class="skeleton" style="height: 12px; width: 80%"></div>
    </template>

    <template v-else-if="score">
      <div class="result-row">
        <span class="score">
          {{ score.value.toFixed(2) }}<small> / 3</small>
        </span>
        <span class="level-name">{{ score.level }}</span>
      </div>
      <div class="scale">
        <div class="bar"><div class="bar-fill" :class="urgencyColor" :style="{ width: pct + '%' }"></div></div>
        <div class="ticks">
          <span v-for="n in ['0', '1', '2', '3']" :key="n">{{ n }}</span>
        </div>
      </div>
      <p class="desc">{{ SCORE_LEVELS[score.levelIndex] }}</p>
      <p class="note">同一队列按分数从高到低排序，同分按接收顺序；评分供人工参考。</p>
    </template>

    <p v-else class="waiting">等待优先级判断，根据对当前跟课的影响安排先后。</p>
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
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.card-title { display: flex; align-items: center; gap: 9px; }
.card-title b { display: block; font-size: 13.5px; color: var(--text); }
.card-title small { display: block; font-size: 11.5px; color: var(--text-3); margin-top: 1px; }
.icon {
  width: 32px; height: 32px; border-radius: 9px;
  background: #fff7ed;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex: none;
}
.result-row { display: flex; align-items: baseline; justify-content: space-between; }
.score {
  font-size: 22px;
  font-weight: 800;
  color: var(--primary-deep);
  font-variant-numeric: tabular-nums;
}
.score small { font-size: 12px; color: var(--text-3); font-weight: 700; }
.level-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-deep);
  background: var(--primary-soft);
  border: 1px solid #c7dbfe;
  border-radius: 999px;
  padding: 3px 12px;
}
.scale { display: flex; flex-direction: column; gap: 4px; }
.ticks {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--text-3);
  padding: 0 2px;
  font-variant-numeric: tabular-nums;
}
.desc { font-size: 12px; color: var(--text-2); line-height: 1.55; }
.note { font-size: 11px; color: var(--text-3); }
.waiting { font-size: 12px; color: var(--text-3); line-height: 1.6; }
</style>
