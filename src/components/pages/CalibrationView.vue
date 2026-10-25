<script setup lang="ts">
import { computed } from 'vue'
import {
  CHOICE_THRESHOLD,
  CONFUSION_LABELS,
  CONFUSION_MATRIX,
  ERROR_PROFILE,
  EVAL_REPLAY,
  NOUL_THRESHOLD_OPTIONS,
  TEMPERATURE_BUCKETS,
  TRAINING_SUMMARY,
} from '@/data/calibration'
import { THRESHOLDS } from '@/config/criteria'

const pct = (v: number) => (v * 100).toFixed(1) + '%'

/** 混淆矩阵行/列总数，用于显示每类命中占比 */
const rowTotals = computed(() => CONFUSION_MATRIX.map((row) => row.reduce((a, b) => a + b, 0)))
</script>

<template>
  <div class="calibration">
    <!-- 模型与训练概要 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>校准与阈值 · {{ TRAINING_SUMMARY.model }}</h2>
          <p>
            {{ TRAINING_SUMMARY.baseModel }} · {{ TRAINING_SUMMARY.method }} ·
            {{ TRAINING_SUMMARY.epochs }} epochs · {{ TRAINING_SUMMARY.trainSamples }} 条训练样本
            · 校准于 {{ TRAINING_SUMMARY.calibratedAt }}
          </p>
        </div>
        <span class="badge badge-ok">训练 eval_acc {{ pct(TRAINING_SUMMARY.evalAcc) }}</span>
      </header>
      <div class="primitive-grid">
        <div v-for="(acc, key) in TRAINING_SUMMARY.evalAccByPrimitive" :key="key" class="primitive-item">
          <span class="primitive-name">{{ { choice: 'Choice', noul: 'Noul', score: 'Score' }[key] }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: pct(acc as number) }"></div>
          </div>
          <span class="primitive-val">{{ pct(acc as number) }}</span>
        </div>
      </div>
    </section>

    <!-- 分桶温度 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>分桶温度校准</h2>
          <p>出厂温度全部为 1.0（概率过度自信）；按原语分桶做 NLL 黄金分割拟合，产出温度已写入 checkpoint</p>
        </div>
      </header>
      <div class="table-wrap">
        <table class="temp-table">
          <thead>
            <tr>
              <th>原语</th>
              <th>分桶</th>
              <th>拟合样本</th>
              <th>出厂温度</th>
              <th>校准温度</th>
              <th>校准后 NLL</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in TEMPERATURE_BUCKETS" :key="b.bucket">
              <td>{{ b.name }}</td>
              <td class="mono">{{ b.bucket }}</td>
              <td class="mono">{{ b.n }}</td>
              <td class="mono">1.00</td>
              <td>
                <span class="badge badge-ok mono">{{ b.temperature.toFixed(4) }}</span>
              </td>
              <td class="mono">{{ b.nll.toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="foot-note">
        校准目标是分桶 NLL（决策一致性），不是全局 ECE；T &gt; 1 会拉平概率分布，阈值需按校准后分布重新量化。
      </p>
    </section>

    <!-- 门槛量化 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>Noul 门槛量化（0.80 → 0.65）</h2>
          <p>校准后在独立评估分位上对比两档门槛的自动化收益，当前生效 {{ pct(THRESHOLDS.actionableProbability) }}</p>
        </div>
      </header>

      <div class="threshold-compare">
        <div
          v-for="opt in NOUL_THRESHOLD_OPTIONS"
          :key="opt.threshold"
          class="threshold-card"
          :class="{ adopted: opt.adopted }"
        >
          <header>
            <span class="mono th-val">≥ {{ opt.threshold.toFixed(2) }}</span>
            <span v-if="opt.adopted" class="badge badge-ok">当前采用</span>
            <span v-else class="badge badge-plain">对照方案</span>
          </header>

          <div class="metric">
            <div class="metric-head">
              <span>自动化覆盖率</span>
              <b>{{ pct(opt.coverage) }}</b>
            </div>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: pct(opt.coverage) }"></div>
            </div>
          </div>

          <div class="metric">
            <div class="metric-head">
              <span>区间内准确率</span>
              <b>{{ pct(opt.accuracy) }}</b>
            </div>
            <div class="bar-track">
              <div class="bar-fill alt" :style="{ width: pct(opt.accuracy) }"></div>
            </div>
          </div>

          <p class="metric-note">{{ opt.note }}</p>
        </div>
      </div>

      <div class="choice-threshold">
        <span class="chip chip-technical">Choice 门槛 {{ pct(CHOICE_THRESHOLD.threshold) }}</span>
        <p>{{ CHOICE_THRESHOLD.note }}</p>
      </div>
    </section>

    <!-- 评估回放 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>评估集回放（{{ EVAL_REPLAY.sampleCount }} 条）</h2>
          <p>
            独立评估集（与训练集零重叠）批量回放 · {{ EVAL_REPLAY.generatedAt }} ·
            平均 {{ EVAL_REPLAY.avgLatencyMs }}ms/条 · 详见 backend/evals/reports/eval-report.md
          </p>
        </div>
      </header>

      <div class="eval-grid">
        <div class="eval-item">
          <span class="eval-label">Choice top-1</span>
          <b class="eval-val">{{ pct(EVAL_REPLAY.choice.accuracy) }}</b>
          <span class="eval-sub">置信度 ≥60% 子集 {{ pct(EVAL_REPLAY.choice.confPassAccuracy) }}（覆盖 {{ pct(EVAL_REPLAY.choice.confPassCoverage) }}）</span>
        </div>
        <div class="eval-item">
          <span class="eval-label">Noul 区间准确率</span>
          <b class="eval-val">{{ pct(EVAL_REPLAY.noul.intervalAccuracy) }}</b>
          <span class="eval-sub">
            覆盖 {{ pct(EVAL_REPLAY.noul.coverage) }} · 通过区间内 {{ pct(EVAL_REPLAY.noul.passedAccuracy) }} ·
            真值可处理/不可处理均值 {{ EVAL_REPLAY.noul.meanProbTruthActionable.toFixed(2) }} /
            {{ EVAL_REPLAY.noul.meanProbTruthInsufficient.toFixed(2) }}
          </span>
        </div>
        <div class="eval-item">
          <span class="eval-label">Score exact</span>
          <b class="eval-val">{{ pct(EVAL_REPLAY.score.exactAccuracy) }}</b>
          <span class="eval-sub">±1 容差 {{ pct(EVAL_REPLAY.score.within1Accuracy) }} · MAE {{ EVAL_REPLAY.score.mae.toFixed(2) }}</span>
        </div>
      </div>

      <div class="eval-panels">
        <!-- 混淆矩阵 -->
        <div class="confusion-panel">
          <h3>Choice 混淆矩阵（行 = 真值，列 = 预测）</h3>
          <div class="table-wrap">
            <table class="conf-table">
              <thead>
                <tr>
                  <th>真值 \ 预测</th>
                  <th v-for="c in CONFUSION_LABELS" :key="c">{{ c.slice(0, 4) }}</th>
                  <th>合计</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in CONFUSION_MATRIX" :key="CONFUSION_LABELS[i]">
                  <td class="row-label">{{ CONFUSION_LABELS[i] }}</td>
                  <td
                    v-for="(cell, j) in row"
                    :key="j"
                    class="mono"
                    :class="{ hit: i === j && cell > 0, miss: i !== j && cell > 0 }"
                  >
                    {{ cell || '' }}
                  </td>
                  <td class="mono row-total">{{ rowTotals[i] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 错误画像 -->
        <div class="error-panel">
          <h3>错误样本画像（{{ ERROR_PROFILE.total }} 条错误）</h3>
          <ul class="error-list">
            <li v-for="(f, i) in ERROR_PROFILE.findings" :key="i">{{ f }}</li>
          </ul>
          <p class="foot-note">
            结论：主力类别与阻断性场景可靠；边界集中在 insufficient（上下文依赖型短消息），
            生产环境依赖「待确认」人工兜底队列承接。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.calibration {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card {
  flex: none;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  padding: 16px 18px;
}
h2 { font-size: 15.5px; font-weight: 800; }
h3 { font-size: 13px; font-weight: 700; color: var(--text-2); margin-bottom: 8px; }
.sec-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 13px;
  flex-wrap: wrap;
}
.sec-head p { margin-top: 3px; font-size: 12px; color: var(--text-3); }

/* 训练概要三原语 */
.primitive-grid { display: flex; flex-direction: column; gap: 8px; }
.primitive-item { display: flex; align-items: center; gap: 10px; }
.primitive-name { width: 64px; font-size: 12.5px; font-weight: 700; color: var(--text-2); }
.primitive-val { width: 52px; text-align: right; font-size: 12.5px; font-variant-numeric: tabular-nums; }

/* 条形 */
.bar-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: #eef2f8;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #4f8bff, var(--primary));
}
.bar-fill.alt { background: linear-gradient(90deg, #34d399, #10b981); }

/* 分桶温度表 */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
th {
  text-align: left;
  padding: 7px 10px;
  color: var(--text-3);
  font-size: 11.5px;
  font-weight: 700;
  border-bottom: 1px solid var(--border-strong);
  white-space: nowrap;
}
td { padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text); }
.mono { font-variant-numeric: tabular-nums; white-space: nowrap; }
.foot-note { margin-top: 10px; font-size: 11.5px; color: var(--text-3); line-height: 1.6; }

/* 门槛对比 */
.threshold-compare { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.threshold-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fbfcfe;
}
.threshold-card.adopted { border-color: rgba(47, 107, 255, 0.45); background: #f7faff; }
.threshold-card header { display: flex; align-items: center; justify-content: space-between; }
.th-val { font-size: 15px; font-weight: 800; color: var(--primary-deep); }
.metric { display: flex; flex-direction: column; gap: 4px; }
.metric-head { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-2); }
.metric-head b { color: var(--text); font-variant-numeric: tabular-nums; }
.metric-note { font-size: 11.5px; color: var(--text-3); line-height: 1.5; }

.choice-threshold {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-2);
}
.choice-threshold p { flex: 1; }

/* 评估回放 */
.eval-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-bottom: 12px; }
.eval-item {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 11px 13px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #fbfcfe;
}
.eval-label { font-size: 11.5px; font-weight: 700; color: var(--text-3); }
.eval-val { font-size: 21px; font-weight: 800; color: var(--primary-deep); font-variant-numeric: tabular-nums; }
.eval-sub { font-size: 11.5px; color: var(--text-3); line-height: 1.5; }

.eval-panels { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 14px; }
@media (max-width: 960px) { .eval-panels { grid-template-columns: 1fr; } }

/* 混淆矩阵 */
.conf-table td, .conf-table th { text-align: center; padding: 7px 9px; }
.conf-table .row-label, .conf-table th:first-child { text-align: left; white-space: nowrap; }
.conf-table td.hit { background: rgba(16, 185, 129, 0.14); font-weight: 700; color: #047857; }
.conf-table td.miss { background: rgba(239, 68, 68, 0.1); font-weight: 700; color: #b91c1c; }
.row-total { color: var(--text-3); font-weight: 400; }

/* 错误画像 */
.error-list { margin: 0 0 8px; padding-left: 18px; display: flex; flex-direction: column; gap: 5px; }
.error-list li { font-size: 12.5px; color: var(--text-2); line-height: 1.55; }
</style>
