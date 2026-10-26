/**
 * 校准与评估数据（静态快照，v0.6 数据来自 danmaku-dm-v0.6 checkpoint 实测）
 *
 * 数据来源（重跑后需同步更新本模块）：
 *  - 分桶温度：D:/AI/laya/danmaku-dm-v0.6/calibration_report.json（calibrate.py 产出）
 *  - 门槛量化：threshold_scan.py 230 条扫描（noul 0.60 于 2026-10-26 业务采纳，v0.6 复扫维持）
 *  - 评估回放：backend/evals/reports/eval-report.json（replay_eval.py --local 产出，
 *    230 条独立评估集，与训练集零重叠）
 *
 * 注意：分桶温度的校准目标是 NLL（决策一致性），不是 ECE；
 * T>1 会拉平概率分布，ECE 变化仅作参考。
 */

/** 微调训练概要（finetune_history.json / TRAINING.md）—— v0.6 = L3 补强 + chat 口径修正版 */
export const TRAINING_SUMMARY = {
  model: 'laya-finetuned-v0.6',
  baseModel: 'Laya multilingual（mmBERT-base 322M）',
  method: 'LoRA r=8 / α=32 + 决策头全训 · L3 补强 + chat 口径修正（466 条，L3 占 19.3%）',
  epochs: 12,
  bestEpoch: 12,
  trainSamples: 466,
  evalAcc: 0.771,
  evalAccByPrimitive: { choice: 0.7696, noul: 0.9087, score: 0.6348 },
  calibratedAt: '2026-10-27',
}

/** 分桶温度（calibrate.py 分桶 NLL 黄金分割拟合；出厂温度全部为 1.0）—— v0.6 校准 */
export interface TemperatureBucket {
  /** 原语与候选规模标识，如 choice:3-5 */
  bucket: string
  primitive: 'choice' | 'noul' | 'score'
  name: string
  /** 拟合样本数 */
  n: number
  /** 校准温度（出厂 1.0） */
  temperature: number
  /** 校准后分桶 NLL */
  nll: number
}

export const TEMPERATURE_BUCKETS: TemperatureBucket[] = [
  { bucket: 'choice:3-5', primitive: 'choice', name: 'Choice 五分类', n: 230, temperature: 3.6397, nll: 0.7245 },
  { bucket: 'noul:2', primitive: 'noul', name: 'Noul 信息充分性', n: 230, temperature: 2.5844, nll: 0.2868 },
  { bucket: 'score:3-5', primitive: 'score', name: 'Score 优先级', n: 230, temperature: 5.4651, nll: 0.8684 },
]

/** Noul 门槛量化对比（校准后在独立评估分位上的测算） */
export interface ThresholdOption {
  /** 门槛值 */
  threshold: number
  /** 自动化覆盖率：noul ≥ 门槛 的样本占比 */
  coverage: number
  /** 通过区间内的判断准确率 */
  accuracy: number
  adopted: boolean
  note: string
}

export const NOUL_THRESHOLD_OPTIONS: ThresholdOption[] = [
  {
    threshold: 0.6,
    coverage: 0.713,
    accuracy: 0.896,
    adopted: true,
    note: '当前采用（2026-10-26 业务采纳，v0.6 复扫维持）：覆盖 71.3%，区间一致 89.6%，通过内实际 93.9%；0.50–0.60 为 89.6%–90.4% 平台区',
  },
  {
    threshold: 0.65,
    coverage: 0.696,
    accuracy: 0.896,
    adopted: false,
    note: '上一代门槛：覆盖 69.6%，一致率同为 89.6%、通过内 95.0%——覆盖更低，不回撤',
  },
  {
    threshold: 0.5,
    coverage: 0.739,
    accuracy: 0.904,
    adopted: false,
    note: '平台下沿对照：覆盖 +2.6pp 但通过内准确率 -1.0pp（92.9%），差异噪声级，维持 0.60',
  },
  {
    threshold: 0.8,
    coverage: 0.63,
    accuracy: 0.839,
    adopted: false,
    note: '对照：v0.6 下覆盖降至 63.0% 且一致率跌至 83.9%——大样本三代证伪',
  },
]

/** Choice 门槛说明（60% 保持不变） */
export const CHOICE_THRESHOLD = {
  threshold: 0.6,
  passRate: 0.73,
  medianTopProb: 0.7913,
  note: 'v0.6 实测：60% 门槛覆盖 73.0%，区间内分类准确率 86.3%，仍处膝点，沿用课程原版门槛',
}

/** 评估回放摘要（v0.6 · 230 条独立评估集，2026-10-27，--local 回放） */
export const EVAL_REPLAY = {
  generatedAt: '2026-10-27',
  sampleCount: 230,
  avgLatencyMs: 98,
  choice: {
    accuracy: 0.765,
    confPassCoverage: 0.452,
    confPassAccuracy: 0.923,
  },
  noul: {
    intervalAccuracy: 0.896,
    coverage: 0.713,
    passedAccuracy: 0.939,
    meanProbTruthActionable: 0.873,
    meanProbTruthInsufficient: 0.259,
  },
  score: {
    exactAccuracy: 0.63,
    within1Accuracy: 0.957,
    mae: 0.5,
  },
}

/** Choice 混淆矩阵（v0.6，行=真值，列=预测；顺序同 CATEGORY_ORDER） */
export const CONFUSION_LABELS = ['technical', 'feedback', 'chat', 'spam', 'insufficient'] as const
export const CONFUSION_MATRIX: number[][] = [
  [58, 1, 0, 1, 0],
  [8, 51, 0, 0, 1],
  [7, 6, 26, 5, 4],
  [2, 0, 2, 19, 0],
  [12, 5, 0, 0, 22],
]

/** 错误样本画像（74 条错误，v0.6） */
export const ERROR_PROFILE = {
  total: 74,
  findings: [
    '★ 跷跷板破局：L3 命中 9 → 13/22（59%）同时 noul 保持 89.6%——v0.4 曾以 noul 崩至 79.6% 换 L3，v0.6 两项兼得',
    'L3 误报 2 条（ev-0129 麦克风太远 / ev-0137 标题写错时间，真值 L1 升格），排序偏高由待确认队列人工兜底——采纳的唯一让步；漏判 9 条中 7 条判 L2 仍进「优先协助」不漏处理',
    'technical 58/60、spam 19/23 主力保持；chat→feedback 收敛至 6 条（v0.3 为 10），新增 chat→spam 5 条（课程群询问/弹幕礼仪类）',
    'insufficient→technical 12 条为最大错误源（指代不明 vs 环境差异的语义边界，待真实弹幕回流扩充）',
    'Score exact 58.7% → 63.0%（±1 95.7% 持平）；ECE choice 0.030 → 0.029 / noul 0.043 → 0.027，双历史最佳',
  ],
}

/**
 * 校准可靠性分桶（5 等宽桶，来自 replay_eval.py --local 重跑，2026-10-26）：
 * x = 模型输出概率，y = 实际频率；对角线为完美校准；ECE = Σ n/N × |acc − conf|。
 */
export interface ReliabilityBin {
  range: [number, number]
  n: number
  /** 桶内平均模型概率 */
  avgConfidence: number | null
  /** 桶内实际频率（choice=正确率；noul=真值可处理率） */
  accuracy: number | null
}

export const RELIABILITY = {
  binsCount: 5,
  choice: {
    ece: 0.0287,
    brier: 0.0702,
    bins: [
      { range: [0, 0.2] as [number, number], n: 0, avgConfidence: null, accuracy: null },
      { range: [0.2, 0.4] as [number, number], n: 15, avgConfidence: 0.362, accuracy: 0.4667 },
      { range: [0.4, 0.6] as [number, number], n: 47, avgConfidence: 0.514, accuracy: 0.5106 },
      { range: [0.6, 0.8] as [number, number], n: 58, avgConfidence: 0.713, accuracy: 0.7759 },
      { range: [0.8, 1.0] as [number, number], n: 110, avgConfidence: 0.92, accuracy: 0.9091 },
    ] as ReliabilityBin[],
  },
  noul: {
    ece: 0.0271,
    brier: 0.0791,
    bins: [
      { range: [0, 0.2] as [number, number], n: 42, avgConfidence: 0.076, accuracy: 0.119 },
      { range: [0.2, 0.4] as [number, number], n: 13, avgConfidence: 0.269, accuracy: 0.3077 },
      { range: [0.4, 0.6] as [number, number], n: 11, avgConfidence: 0.496, accuracy: 0.4545 },
      { range: [0.6, 0.8] as [number, number], n: 19, avgConfidence: 0.703, accuracy: 0.8421 },
      { range: [0.8, 1.0] as [number, number], n: 145, avgConfidence: 0.946, accuracy: 0.9517 },
    ] as ReliabilityBin[],
  },
  /** 按预测等级分组（v0.6）：L3 分箱 n=15、实际均值 2.73（13 命中 + 2 条 L1 升格误报） */
  scoreByPredLevel: [
    { predLevel: 0, n: 76, meanPred: 0.3, meanTruth: 0.21, mae: 0.38 },
    { predLevel: 1, n: 103, meanPred: 0.99, meanTruth: 0.84, mae: 0.5 },
    { predLevel: 2, n: 36, meanPred: 2.0, meanTruth: 1.53, mae: 0.77 },
    { predLevel: 3, n: 15, meanPred: 2.74, meanTruth: 2.73, mae: 0.45 },
  ],
}

/** A/B 引擎对比（v0.3 → v0.6 迭代验证，230 条独立评估集，ab_runner.py，2026-10-27，noul 门槛 0.60） */
export interface AbEngine {
  name: string
  desc: string
  choiceAcc: number
  noulAcc: number
  noulCoverage: number
  scoreExact: number
  scoreWithin1: number
  mae: number
  choiceEce: number
  noulEce: number
  latencyMs: number
}

export const AB_COMPARISON = {
  generatedAt: '2026-10-27',
  engineA: {
    name: 'laya-v0.3',
    desc: '上一代默认引擎（L3 补强版，379 条训练集）',
    choiceAcc: 0.748,
    noulAcc: 0.904,
    noulCoverage: 0.722,
    scoreExact: 0.587,
    scoreWithin1: 0.957,
    mae: 0.55,
    choiceEce: 0.0303,
    noulEce: 0.0429,
    latencyMs: 74,
  } as AbEngine,
  engineB: {
    name: 'laya-v0.6（当前）',
    desc: 'L3 补强 + chat 口径修正版（466 条训练集）+ 重新校准',
    choiceAcc: 0.765,
    noulAcc: 0.896,
    noulCoverage: 0.713,
    scoreExact: 0.63,
    scoreWithin1: 0.957,
    mae: 0.5,
    choiceEce: 0.0287,
    noulEce: 0.0271,
    latencyMs: 47,
  } as AbEngine,
  agreement: {
    choice: 0.857,
    noul: 0.939,
    scoreExact: 0.735,
    scoreWithin1: 0.987,
    diffCount: 45,
  },
  findings: [
    '★ 跷跷板破局：v0.4 曾以 noul 崩至 79.6% 换 L3 命中 15，v0.5 修复 noul 却回吐 L3（命中 8）；v0.6 撤掉过矫正对照后两项兼得（noul 89.6% + L3 命中 13）',
    'choice 74.8% → 76.5%（+1.7pp）、score exact 58.7% → 63.0%（+4.3pp）；Noul ECE 0.043 → 0.027 历史最佳',
    'L3 误报 0 → 2 条（ev-0129/ev-0137，真值 L1 升格），排序偏高由待确认人工兜底——采纳的唯一让步',
    'chat→feedback 10 → 6 条收敛；新增 chat→spam 5 条噪声（课程群询问/弹幕礼仪类）；insufficient→technical 12 条仍是最大错误源',
    '端到端（0.60/0.60）：完全自动正确 48.7% → 51.3%（历史新高）、漏处理 11.3% → 10.0%（历史新低）；一致率 choice 85.7% / noul 93.9% / score±1 98.7%，分歧 45/230',
  ],
}
