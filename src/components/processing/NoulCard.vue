<script setup lang="ts">
import { computed } from 'vue'
import type { DecisionResult } from '@/types'
import { THRESHOLDS } from '@/config/criteria'

const props = defineProps<{
  decision?: DecisionResult
  loading?: boolean
}>()

const prob = computed(() => props.decision?.noul.probability ?? 0)
const pass = computed(() => prob.value >= THRESHOLDS.actionableProbability)
</script>

<template>
  <div class="card">
    <div class="card-head">
      <div class="card-title">
        <span class="icon">⚖️</span>
        <div>
          <b>Noul · 条件</b>
          <small>信息是否足够开始处理</small>
        </div>
      </div>
      <span v-if="!loading && decision" class="badge" :class="pass ? 'badge-ok' : 'badge-plain'">
        {{ pass ? '≥ 80% 可入待办' : '< 80% 先确认' }}
      </span>
    </div>

    <template v-if="loading">
      <div class="skeleton" style="height: 26px; width: 40%"></div>
      <div class="skeleton" style="height: 8px"></div>
      <div class="skeleton" style="height: 12px; width: 90%"></div>
    </template>

    <template v-else-if="decision">
      <div class="result-row">
        <span class="prob" :class="{ ok: pass }">{{ (prob * 100).toFixed(1) }}<small>%</small></span>
        <span class="verdict">{{ pass ? '信息足够，可以开始处理' : '对象或诉求不完全清楚，先补充确认' }}</span>
      </div>
      <div class="bar threshold">
        <div class="bar-fill" :class="pass ? 'bar-fill-green' : 'bar-fill-orange'" :style="{ width: `${prob * 100}%` }"></div>
        <span class="threshold-mark" :style="{ left: THRESHOLDS.actionableProbability * 100 + '%' }"></span>
      </div>
      <p class="desc">
        Noul 表示「信息足够开始处理」的概率；达到 80% 才进入讲师或助教待办，其余先确认。
      </p>
    </template>

    <p v-else class="waiting">等待处理条件判断，对象和诉求清楚，才能开始答疑或处理听课问题。</p>
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
.card-title { display: flex; align-items: center; gap: 9px; }
.card-title b { display: block; font-size: 13.5px; color: var(--text); }
.card-title small { display: block; font-size: 11.5px; color: var(--text-3); margin-top: 1px; }
.icon {
  width: 32px; height: 32px; border-radius: 9px;
  background: #ecfdf5;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex: none;
}
.result-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.prob {
  font-size: 22px;
  font-weight: 800;
  color: var(--orange);
  font-variant-numeric: tabular-nums;
}
.prob.ok { color: var(--green); }
.prob small { font-size: 12px; font-weight: 700; margin-left: 1px; }
.verdict { font-size: 12px; color: var(--text-2); text-align: right; }
.bar { position: relative; }
.threshold-mark {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 14px;
  background: var(--text-2);
  border-radius: 2px;
  opacity: 0.6;
}
.desc { font-size: 12px; color: var(--text-2); line-height: 1.55; }
.waiting { font-size: 12px; color: var(--text-3); line-height: 1.6; }
</style>
