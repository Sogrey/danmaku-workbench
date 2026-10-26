/**
 * 校准与评估数据（静态快照，v0.3 数据来自 danmaku-dm-v0.3 checkpoint 实测）
 *
 * 数据来源（重跑后需同步更新本模块）：
 *  - 分桶温度：D:/AI/laya/danmaku-dm-v0.3/calibration_report.json（calibrate.py 产出）
 *  - 门槛量化：threshold_scan.py 230 条扫描（noul 0.60 于 2026-10-26 业务采纳）
 *  - 评估回放：backend/evals/reports/eval-report.json（replay_eval.py --local 产出，
 *    230 条独立评估集，与训练集零重叠）
 *
 * 注意：分桶温度的校准目标是 NLL（决策一致性），不是 ECE；
 * T>1 会拉平概率分布，ECE 变化仅作参考。
 */

/** 微调训练概要（finetune_history.json / TRAINING.md）—— v0.3 = L3 补强版 */
export const TRAINING_SUMMARY = {
  model: 'laya-finetuned-v0.3',
  baseModel: 'Laya multilingual（mmBERT-base 322M）',
  method: 'LoRA r=8 / α=32 + 决策头全训 · L3 补强（379 条，L3 占 15.8%）',
  epochs: 12,
  bestEpoch: 7,
  trainSamples: 379,
  evalAcc: 0.7667,
  evalAccByPrimitive: { choice: 0.7565, noul: 0.8957, score: 0.6478 },
  calibratedAt: '2026-10-25',
}

/** 分桶温度（calibrate.py 分桶 NLL 黄金分割拟合；出厂温度全部为 1.0）—— v0.3 校准 */
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
  { bucket: 'choice:3-5', primitive: 'choice', name: 'Choice 五分类', n: 230, temperature: 2.8837, nll: 0.7599 },
  { bucket: 'noul:2', primitive: 'noul', name: 'Noul 信息充分性', n: 230, temperature: 1.7171, nll: 0.3733 },
  { bucket: 'score:3-5', primitive: 'score', name: 'Score 优先级', n: 230, temperature: 3.6716, nll: 0.901 },
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
    coverage: 0.722,
    accuracy: 0.904,
    adopted: true,
    note: '当前采用（2026-10-26 业务采纳，v0.3 扫描）：覆盖 72.2%，区间一致 90.4%（最优），通过内实际 94.0%',
  },
  {
    threshold: 0.65,
    coverage: 0.704,
    accuracy: 0.896,
    adopted: false,
    note: '上一代门槛（v0.2 期量化）：覆盖 70.4%，区间一致 89.6%，通过内实际 94.4%',
  },
  {
    threshold: 0.8,
    coverage: 0.639,
    accuracy: 0.83,
    adopted: false,
    note: '对照：v0.3 下覆盖降至 63.9% 且一致率跌至 83.0%——大样本两度证伪',
  },
]

/** Choice 门槛说明（60% 保持不变） */
export const CHOICE_THRESHOLD = {
  threshold: 0.6,
  passRate: 0.7,
  medianTopProb: 0.9163,
  note: 'v0.3 实测：60% 门槛覆盖 70.0%，区间内分类准确率 86.3%，仍处膝点，沿用课程原版门槛',
}

/** 评估回放摘要（v0.3 · 230 条独立评估集，2026-10-26，--local 回放） */
export const EVAL_REPLAY = {
  generatedAt: '2026-10-26',
  sampleCount: 230,
  avgLatencyMs: 99,
  choice: {
    accuracy: 0.748,
    confPassCoverage: 0.4,
    confPassAccuracy: 0.902,
  },
  noul: {
    intervalAccuracy: 0.904,
    coverage: 0.722,
    passedAccuracy: 0.94,
    meanProbTruthActionable: 0.874,
    meanProbTruthInsufficient: 0.329,
  },
  score: {
    exactAccuracy: 0.587,
    within1Accuracy: 0.957,
    mae: 0.55,
  },
}

/** Choice 混淆矩阵（v0.3，行=真值，列=预测；顺序同 CATEGORY_ORDER） */
export const CONFUSION_LABELS = ['technical', 'feedback', 'chat', 'spam', 'insufficient'] as const
export const CONFUSION_MATRIX: number[][] = [
  [57, 1, 0, 0, 2],
  [10, 49, 0, 0, 1],
  [8, 10, 23, 2, 5],
  [2, 0, 1, 20, 0],
  [8, 6, 2, 0, 23],
]

/** 错误样本画像（70 条错误，v0.3） */
export const ERROR_PROFILE = {
  total: 70,
  findings: [
    '★ L3 突破：22 条直播中断类真值样本 0 → 9 命中（41%）且零误报（9 条被判 L3 的真值全部为 3）——L3 补强训练生效',
    '剩余 12 条 L3 判为 L2：仍进「优先协助」队列不漏处理，仅排序略低；下一步补 L2/L3 对照种子可继续提升',
    'technical 57/60、spam 20/23 保持主力可靠；insufficient→technical 降至 8（v0.2 为 10）',
    'chat 25 条外溢（8 判 technical、10 判 feedback——节奏/语速类闲聊被误判为听课反馈、5 判 insufficient）',
    'Score ±1 容差命中 95.7%；ECE choice 0.030 / noul 0.043，校准质量较 v0.2 翻倍改善',
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
    ece: 0.0303,
    brier: 0.0738,
    bins: [
      { range: [0, 0.2] as [number, number], n: 0, avgConfidence: null, accuracy: null },
      { range: [0.2, 0.4] as [number, number], n: 17, avgConfidence: 0.358, accuracy: 0.2941 },
      { range: [0.4, 0.6] as [number, number], n: 52, avgConfidence: 0.521, accuracy: 0.5385 },
      { range: [0.6, 0.8] as [number, number], n: 60, avgConfidence: 0.7095, accuracy: 0.7833 },
      { range: [0.8, 1.0] as [number, number], n: 101, avgConfidence: 0.9163, accuracy: 0.9109 },
    ] as ReliabilityBin[],
  },
  noul: {
    ece: 0.0429,
    brier: 0.0867,
    bins: [
      { range: [0, 0.2] as [number, number], n: 30, avgConfidence: 0.0932, accuracy: 0.0667 },
      { range: [0.2, 0.4] as [number, number], n: 21, avgConfidence: 0.2929, accuracy: 0.3333 },
      { range: [0.4, 0.6] as [number, number], n: 13, avgConfidence: 0.5126, accuracy: 0.2308 },
      { range: [0.6, 0.8] as [number, number], n: 19, avgConfidence: 0.7111, accuracy: 0.9474 },
      { range: [0.8, 1.0] as [number, number], n: 147, avgConfidence: 0.9393, accuracy: 0.9388 },
    ] as ReliabilityBin[],
  },
  /** 按预测等级分组（v0.3）：L3 分箱首次出现，n=9 且实际均值 3.0 */
  scoreByPredLevel: [
    { predLevel: 0, n: 66, meanPred: 0.299, meanTruth: 0.212, mae: 0.401 },
    { predLevel: 1, n: 111, meanPred: 0.956, meanTruth: 0.802, mae: 0.524 },
    { predLevel: 2, n: 44, meanPred: 1.891, meanTruth: 1.568, mae: 0.896 },
    { predLevel: 3, n: 9, meanPred: 2.618, meanTruth: 3.0, mae: 0.382 },
  ],
}

/** A/B 引擎对比（v0.2 → v0.3 迭代验证，230 条独立评估集，ab_runner.py，2026-10-26，noul 门槛 0.60） */
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
  generatedAt: '2026-10-26',
  engineA: {
    name: 'laya-v0.2',
    desc: '上一代微调 checkpoint（L3 补强前，322 条训练集）',
    choiceAcc: 0.765,
    noulAcc: 0.87,
    noulCoverage: 0.704,
    scoreExact: 0.574,
    scoreWithin1: 0.961,
    mae: 0.56,
    choiceEce: 0.0593,
    noulEce: 0.0992,
    latencyMs: 87,
  } as AbEngine,
  engineB: {
    name: 'laya-v0.3（当前）',
    desc: 'L3 补强版（379 条训练集，L3 占 15.8%）+ 重新校准',
    choiceAcc: 0.748,
    noulAcc: 0.904,
    noulCoverage: 0.722,
    scoreExact: 0.587,
    scoreWithin1: 0.957,
    mae: 0.55,
    choiceEce: 0.0303,
    noulEce: 0.0429,
    latencyMs: 98,
  } as AbEngine,
  agreement: {
    choice: 0.861,
    noul: 0.896,
    scoreExact: 0.73,
    scoreWithin1: 0.991,
    diffCount: 48,
  },
  findings: [
    '★ L3 突破：22 条直播中断类真值 0 → 9 命中（41%）且零误报；剩余 12 条判 L2 进「优先协助」，不漏处理',
    'noul 区间准确（@0.60 门槛）87.0% → 90.4%（+3.4pp），覆盖 70.4% → 72.2%；校准质量翻倍（ECE choice 0.059→0.030、noul 0.099→0.043）',
    'choice 76.5% → 74.8%（-1.7pp 容差内）；technical 57/60 主力保持，chat→feedback 误判 10 条为新增噪声',
    '迭代稳定性：一致率 choice 86.1% / noul 89.6% / score±1 99.1%，分歧仅 48/230——两代模型行为高度连续',
    '相对零样本基线（choice 43.5%）微调路线整体增益 +31.3pp，且 v0.3 首次具备最高优先级识别能力',
  ],
}
