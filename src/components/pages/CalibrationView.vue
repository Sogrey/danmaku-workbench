<script setup lang="ts">
import { computed } from 'vue'
import {
  AB_COMPARISON,
  CHOICE_THRESHOLD,
  CONFUSION_LABELS,
  CONFUSION_MATRIX,
  ERROR_PROFILE,
  EVAL_REPLAY,
  NOUL_THRESHOLD_OPTIONS,
  RELIABILITY,
  TEMPERATURE_BUCKETS,
  TRAINING_SUMMARY,
  type ReliabilityBin,
} from '@/data/calibration'
import { THRESHOLDS } from '@/config/criteria'

const pct = (v: number) => (v * 100).toFixed(1) + '%'

/** 混淆矩阵行/列总数，用于显示每类命中占比 */
const rowTotals = computed(() => CONFUSION_MATRIX.map((row) => row.reduce((a, b) => a + b, 0)))

// ---------- 可靠性曲线（SVG 坐标换算） ----------
const PLOT = { size: 220, pad: 28 }
const plotArea = PLOT.size - PLOT.pad * 2

interface RelPoint {
  x: number
  y: number
  r: number
  n: number
  conf: number
  acc: number
}

function relPoints(bins: ReliabilityBin[]): RelPoint[] {
  return bins
    .filter((b): b is ReliabilityBin & { avgConfidence: number; accuracy: number } =>
      b.n > 0 && b.avgConfidence !== null && b.accuracy !== null)
    .map((b) => ({
      x: PLOT.pad + b.avgConfidence * plotArea,
      y: PLOT.size - PLOT.pad - b.accuracy * plotArea,
      r: 3.2 + b.n * 0.42,
      n: b.n,
      conf: b.avgConfidence,
      acc: b.accuracy,
    }))
}

const choicePoints = computed(() => relPoints(RELIABILITY.choice.bins))
const noulPoints = computed(() => relPoints(RELIABILITY.noul.bins))
const poly = (pts: RelPoint[]) => pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

// ---------- A/B 对比 ----------
const AB = AB_COMPARISON
const abMetrics = [
  { label: 'Choice top-1 准确率', a: AB.engineA.choiceAcc, b: AB.engineB.choiceAcc },
  { label: 'Noul 区间准确率', a: AB.engineA.noulAcc, b: AB.engineB.noulAcc },
  { label: 'Score ±1 容差命中', a: AB.engineA.scoreWithin1, b: AB.engineB.scoreWithin1 },
  { label: 'Score exact 命中', a: AB.engineA.scoreExact, b: AB.engineB.scoreExact },
]
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

    <!-- 校准可靠性曲线 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>校准可靠性曲线（{{ RELIABILITY.binsCount }} 等宽桶）</h2>
          <p>
            模型概率（x）与实际频率（y）越贴近对角线校准越好；ECE = Σ n/N × |acc − conf|，
            置信度门槛建立在该概率语义之上 · 详见 backend/evals/reports/eval-report.md
          </p>
        </div>
        <span class="badge badge-ok">Choice ECE {{ RELIABILITY.choice.ece.toFixed(4) }} ≤ 0.1</span>
      </header>

      <div class="rel-grid">
        <figure class="rel-fig">
          <figcaption>
            <span>Choice · top-1 概率 vs 实际正确率</span>
            <span class="badge badge-plain">
              ECE {{ RELIABILITY.choice.ece.toFixed(4) }} · Brier {{ RELIABILITY.choice.brier.toFixed(4) }}
            </span>
          </figcaption>
          <svg :viewBox="`0 0 ${PLOT.size} ${PLOT.size}`" class="rel-svg" role="img">
            <line :x1="PLOT.pad + plotArea / 2" :y1="PLOT.pad" :x2="PLOT.pad + plotArea / 2" :y2="PLOT.size - PLOT.pad" class="grid-line" />
            <line :x1="PLOT.pad" :y1="PLOT.pad + plotArea / 2" :x2="PLOT.size - PLOT.pad" :y2="PLOT.pad + plotArea / 2" class="grid-line" />
            <line :x1="PLOT.pad" :y1="PLOT.size - PLOT.pad" :x2="PLOT.size - PLOT.pad" :y2="PLOT.pad" class="diag" />
            <polyline :points="poly(choicePoints)" class="rel-line" />
            <circle v-for="(p, i) in choicePoints" :key="i" :cx="p.x" :cy="p.y" :r="p.r" class="rel-dot">
              <title>n={{ p.n }}，conf {{ pct(p.conf) }}，acc {{ pct(p.acc) }}</title>
            </circle>
            <text x="10" y="16" class="axis-label axis-left">实际频率 ↑</text>
            <text :x="PLOT.size / 2" :y="PLOT.size - 8" class="axis-label">模型概率 →</text>
          </svg>
          <p class="fig-note">
            0.6–0.8 区间略有过度自信（实际 63.6%），高置信区（0.8–1.0）对齐良好（91.3%）；
            点面积 ∝ 样本数，悬停查看明细。
          </p>
        </figure>

        <figure class="rel-fig">
          <figcaption>
            <span>Noul · 可处理概率 vs 实际可处理率</span>
            <span class="badge badge-plain">
              ECE {{ RELIABILITY.noul.ece.toFixed(4) }} · Brier {{ RELIABILITY.noul.brier.toFixed(4) }}
            </span>
          </figcaption>
          <svg :viewBox="`0 0 ${PLOT.size} ${PLOT.size}`" class="rel-svg" role="img">
            <line :x1="PLOT.pad + plotArea / 2" :y1="PLOT.pad" :x2="PLOT.pad + plotArea / 2" :y2="PLOT.size - PLOT.pad" class="grid-line" />
            <line :x1="PLOT.pad" :y1="PLOT.pad + plotArea / 2" :x2="PLOT.size - PLOT.pad" :y2="PLOT.pad + plotArea / 2" class="grid-line" />
            <line :x1="PLOT.pad" :y1="PLOT.size - PLOT.pad" :x2="PLOT.size - PLOT.pad" :y2="PLOT.pad" class="diag" />
            <polyline :points="poly(noulPoints)" class="rel-line" />
            <circle v-for="(p, i) in noulPoints" :key="i" :cx="p.x" :cy="p.y" :r="p.r" class="rel-dot">
              <title>n={{ p.n }}，prob {{ pct(p.conf) }}，实际 {{ pct(p.acc) }}</title>
            </circle>
            <text x="10" y="16" class="axis-label axis-left">实际频率 ↑</text>
            <text :x="PLOT.size / 2" :y="PLOT.size - 8" class="axis-label">模型概率 →</text>
          </svg>
          <p class="fig-note">
            低概率区判「不可处理」可靠（实际 17~20%）；≥0.65 通过区间实际 81.8%~94.1%，与门槛量化结论吻合
            （0.4–0.6 边界样本仅 1 条，统计意义有限）。
          </p>
        </figure>
      </div>

      <div class="score-calib">
        <h3>Score 分箱校准（按预测等级分组：预测均值 vs 实际等级均值）</h3>
        <div class="table-wrap">
          <table class="temp-table">
            <thead>
              <tr>
                <th>预测等级</th>
                <th>n</th>
                <th>预测均值</th>
                <th>实际等级均值</th>
                <th>MAE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in RELIABILITY.scoreByPredLevel" :key="s.predLevel">
                <td>{{ s.predLevel }} · {{ ['稍后处理', '正常答疑', '优先协助', '立即关注'][s.predLevel] }}</td>
                <td class="mono">{{ s.n }}</td>
                <td class="mono">{{ s.meanPred.toFixed(2) }}</td>
                <td class="mono">{{ s.meanTruth.toFixed(2) }}</td>
                <td class="mono">{{ s.mae.toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="foot-note">
          45 条中无样本被判等级 3（立即关注）：模型对最高优先级偏保守，生产环境建议补「直播中断类」样本迭代。
        </p>
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

    <!-- A/B 引擎对比 -->
    <section class="card">
      <header class="sec-head">
        <div>
          <h2>A/B 引擎对比 · 零样本基线 vs 微调</h2>
          <p>
            45 条独立评估集 · ab_runner.py 顺序跑批（判据与温度各自生效）· {{ AB.generatedAt }} ·
            详见 backend/evals/reports/ab-report.md
          </p>
        </div>
        <div class="ab-badges">
          <span class="badge badge-plain">分歧样本 {{ AB.agreement.diffCount }}/45 条</span>
        </div>
      </header>

      <div class="ab-engines">
        <div class="ab-engine">
          <span class="badge badge-plain">A · {{ AB.engineA.name }}</span>
          <p>{{ AB.engineA.desc }} · 平均 {{ AB.engineA.latencyMs }}ms/条</p>
        </div>
        <div class="ab-engine">
          <span class="badge badge-ok">B · {{ AB.engineB.name }}</span>
          <p>{{ AB.engineB.desc }} · 平均 {{ AB.engineB.latencyMs }}ms/条</p>
        </div>
      </div>

      <div class="ab-metrics">
        <div v-for="m in abMetrics" :key="m.label" class="ab-metric">
          <div class="metric-head">
            <span>{{ m.label }}</span>
            <b>A {{ pct(m.a) }} → B {{ pct(m.b) }}</b>
          </div>
          <div class="bar-track slim">
            <div class="bar-fill ab-a" :style="{ width: pct(m.a) }"></div>
          </div>
          <div class="bar-track slim">
            <div class="bar-fill" :style="{ width: pct(m.b) }"></div>
          </div>
        </div>
      </div>

      <div class="ab-eces">
        <span>校准与偏差（越小越好）：</span>
        <span class="badge badge-plain">Choice ECE {{ AB.engineA.choiceEce.toFixed(4) }} → {{ AB.engineB.choiceEce.toFixed(4) }}</span>
        <span class="badge badge-plain">Noul ECE {{ AB.engineA.noulEce.toFixed(4) }} → {{ AB.engineB.noulEce.toFixed(4) }}</span>
        <span class="badge badge-plain">Score MAE {{ AB.engineA.mae.toFixed(2) }} → {{ AB.engineB.mae.toFixed(2) }}</span>
      </div>

      <div class="ab-agreement">
        <span class="chip chip-technical">类别一致 {{ pct(AB.agreement.choice) }}</span>
        <span class="chip chip-feedback">Noul 判定一致 {{ pct(AB.agreement.noul) }}</span>
        <span class="chip chip-chat">Score ±1 一致 {{ pct(AB.agreement.scoreWithin1) }}</span>
        <span class="chip chip-insufficient">分歧 {{ AB.agreement.diffCount }} 条</span>
      </div>

      <ul class="error-list">
        <li v-for="(f, i) in AB.findings" :key="i">{{ f }}</li>
      </ul>
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

/* 可靠性曲线 */
.rel-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.rel-fig { margin: 0; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; background: #fbfcfe; }
.rel-fig figcaption {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-2);
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.rel-svg {
  width: 100%;
  max-width: 300px;
  display: block;
  margin: 0 auto;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
}
.diag { stroke: #94a3b8; stroke-width: 1.2; stroke-dasharray: 4 3; }
.grid-line { stroke: #eef2f8; stroke-width: 1; }
.rel-line { fill: none; stroke: var(--primary); stroke-width: 1.8; }
.rel-dot { fill: rgba(47, 107, 255, 0.5); stroke: var(--primary); stroke-width: 1.5; }
.axis-label { font-size: 10px; fill: var(--text-3); text-anchor: middle; }
.axis-label.axis-left { text-anchor: start; }
.fig-note { margin-top: 8px; font-size: 11.5px; color: var(--text-3); line-height: 1.55; }
.score-calib { margin-top: 14px; }
.score-calib h3 { font-size: 13px; font-weight: 700; color: var(--text-2); margin-bottom: 8px; }

/* A/B 引擎对比 */
.ab-engines { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; margin-bottom: 14px; }
.ab-engine { border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; background: #fbfcfe; }
.ab-engine p { margin-top: 6px; font-size: 12px; color: var(--text-2); line-height: 1.5; }
.ab-badges { display: flex; gap: 8px; align-items: center; }
.ab-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px 18px; margin-bottom: 12px; }
.ab-metric { display: flex; flex-direction: column; gap: 4px; }
.ab-metric .metric-head { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--text-2); flex-wrap: wrap; }
.ab-metric .metric-head b { color: var(--text); font-variant-numeric: tabular-nums; }
.bar-track.slim { height: 7px; }
.bar-fill.ab-a { background: linear-gradient(90deg, #cbd5e1, #94a3b8); }
.ab-eces { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--text-2); margin-bottom: 12px; }
.ab-agreement { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.ab-metrics + .ab-eces,
.ab-agreement + .error-list { margin-top: 2px; }
</style>
