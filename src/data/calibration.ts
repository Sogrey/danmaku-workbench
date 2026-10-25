/**
 * 校准与评估数据（静态快照，全部来自 danmaku-dm-v0.2 checkpoint 实测）
 *
 * 数据来源（重跑后需同步更新本模块）：
 *  - 分桶温度：D:/AI/laya/danmaku-dm-v0.2/calibration_report.json（calibrate.py 产出）
 *  - 门槛量化：v0.2 温度校准后的分位分析（2026-10-25）
 *  - 评估回放：backend/evals/reports/eval-report.json（replay_eval.py 产出，
 *    http 模式，45 条独立评估集，与训练集零重叠）
 *
 * 注意：分桶温度的校准目标是 NLL（决策一致性），不是 ECE；
 * T>1 会拉平概率分布，ECE 变化仅作参考。
 */

/** 微调训练概要（finetune_history.json / TRAINING.md） */
export const TRAINING_SUMMARY = {
  model: 'laya-finetuned-v0.2',
  baseModel: 'Laya multilingual（mmBERT-base 322M）',
  method: 'LoRA r=8 / α=32（target Wqkv）+ 决策头全训',
  epochs: 12,
  trainSamples: 322,
  evalAcc: 0.77,
  evalAccByPrimitive: { choice: 0.822, noul: 0.867, score: 0.622 },
  calibratedAt: '2026-10-25',
}

/** 分桶温度（calibrate.py 分桶 NLL 黄金分割拟合；出厂温度全部为 1.0） */
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
  { bucket: 'choice:3-5', primitive: 'choice', name: 'Choice 五分类', n: 45, temperature: 3.0665, nll: 0.7072 },
  { bucket: 'noul:2', primitive: 'noul', name: 'Noul 信息充分性', n: 45, temperature: 3.8094, nll: 0.4562 },
  { bucket: 'score:3-5', primitive: 'score', name: 'Score 优先级', n: 45, temperature: 4.5357, nll: 0.9531 },
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
    threshold: 0.65,
    coverage: 0.556,
    accuracy: 0.92,
    adopted: true,
    note: '量化最优平衡：多放行 18% 覆盖率，仅损失 2% 区间准确率',
  },
  {
    threshold: 0.8,
    coverage: 0.378,
    accuracy: 0.94,
    adopted: false,
    note: '更保守：区间准确率 +2%，但 62% 的消息被推向人工确认',
  },
]

/** Choice 门槛说明（60% 保持不变） */
export const CHOICE_THRESHOLD = {
  threshold: 0.6,
  passRate: 0.687,
  medianTopProb: 0.83,
  note: '230 条评估上 60% 门槛覆盖 68.7%，区间内分类准确率 83.5%，沿用课程原版门槛',
}

/** 评估回放摘要（230 条独立评估集 = 45 初版 + 185 扩充（含 22 条直播中断类），2026-10-25，--local 回放） */
export const EVAL_REPLAY = {
  generatedAt: '2026-10-25',
  sampleCount: 230,
  avgLatencyMs: 101,
  choice: {
    accuracy: 0.765,
    confPassCoverage: 0.413,
    confPassAccuracy: 0.916,
  },
  noul: {
    intervalAccuracy: 0.857,
    coverage: 0.665,
    passedAccuracy: 0.941,
    meanProbTruthActionable: 0.764,
    meanProbTruthInsufficient: 0.305,
  },
  score: {
    exactAccuracy: 0.574,
    within1Accuracy: 0.961,
    mae: 0.56,
  },
}

/** Choice 混淆矩阵（行=真值，列=预测；顺序同 CATEGORY_ORDER） */
export const CONFUSION_LABELS = ['technical', 'feedback', 'chat', 'spam', 'insufficient'] as const
export const CONFUSION_MATRIX: number[][] = [
  [58, 2, 0, 0, 0],
  [12, 46, 0, 0, 2],
  [9, 2, 28, 5, 4],
  [3, 0, 1, 19, 0],
  [10, 3, 1, 0, 25],
]

/** 错误样本画像（74 条错误的分布结论，2026-10-25） */
export const ERROR_PROFILE = {
  total: 74,
  findings: [
    'technical 58/60、spam 19/23 全对，主力类别可靠',
    '★ 22 条等级 3（直播中断类）真值样本 0 条被判中（19 条判 L2）——训练集 L3 占比不足，重训需补该类样本',
    'feedback 12 条被判 technical（黑屏/闪退/报错类描述常带技术词）；insufficient 10 条判 technical（上下文依赖型）',
    'chat 48 条中 9 判 technical、5 判 spam（如「课程官方群怎么加」被误判引流）',
    'Score ±1 容差命中 96.1%，等级方向基本不偏，exact 弱与官方结论一致',
  ],
}

/**
 * 校准可靠性分桶（5 等宽桶，来自 replay_eval.py --local 重跑，2026-10-25）：
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
    ece: 0.0593,
    brier: 0.0739,
    bins: [
      { range: [0, 0.2] as [number, number], n: 0, avgConfidence: null, accuracy: null },
      { range: [0.2, 0.4] as [number, number], n: 14, avgConfidence: 0.3654, accuracy: 0.2857 },
      { range: [0.4, 0.6] as [number, number], n: 58, avgConfidence: 0.5062, accuracy: 0.6897 },
      { range: [0.6, 0.8] as [number, number], n: 60, avgConfidence: 0.705, accuracy: 0.7167 },
      { range: [0.8, 1.0] as [number, number], n: 98, avgConfidence: 0.9203, accuracy: 0.9082 },
    ] as ReliabilityBin[],
  },
  noul: {
    ece: 0.0992,
    brier: 0.1092,
    bins: [
      { range: [0, 0.2] as [number, number], n: 35, avgConfidence: 0.0762, accuracy: 0.1714 },
      { range: [0.2, 0.4] as [number, number], n: 17, avgConfidence: 0.2975, accuracy: 0.2353 },
      { range: [0.4, 0.6] as [number, number], n: 16, avgConfidence: 0.4815, accuracy: 0.5 },
      { range: [0.6, 0.8] as [number, number], n: 52, avgConfidence: 0.7216, accuracy: 0.8846 },
      { range: [0.8, 1.0] as [number, number], n: 110, avgConfidence: 0.8578, accuracy: 0.9455 },
    ] as ReliabilityBin[],
  },
  /** 按预测等级分组：预测均值 vs 实际等级均值（无样本被判等级 3） */
  scoreByPredLevel: [
    { predLevel: 0, n: 69, meanPred: 0.308, meanTruth: 0.275, mae: 0.44 },
    { predLevel: 1, n: 119, meanPred: 1.025, meanTruth: 0.798, mae: 0.514 },
    { predLevel: 2, n: 42, meanPred: 1.762, meanTruth: 2.024, mae: 0.906 },
  ],
}

/** A/B 引擎对比（230 条独立评估集，ab_runner.py，2026-10-25） */
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
  generatedAt: '2026-10-25',
  engineA: {
    name: 'laya-baseline',
    desc: '零样本 multilingual 基线（出厂温度 1.0，未微调）',
    choiceAcc: 0.435,
    noulAcc: 0.643,
    noulCoverage: 0.791,
    scoreExact: 0.096,
    scoreWithin1: 0.591,
    mae: 1.19,
    choiceEce: 0.2227,
    noulEce: 0.1834,
    latencyMs: 96,
  } as AbEngine,
  engineB: {
    name: 'laya-finetuned',
    desc: 'LoRA 微调 + 分桶温度校准（danmaku-dm-v0.2）',
    choiceAcc: 0.765,
    noulAcc: 0.857,
    noulCoverage: 0.665,
    scoreExact: 0.574,
    scoreWithin1: 0.961,
    mae: 0.56,
    choiceEce: 0.0593,
    noulEce: 0.0992,
    latencyMs: 100,
  } as AbEngine,
  agreement: {
    choice: 0.543,
    noul: 0.63,
    scoreExact: 0.196,
    scoreWithin1: 0.704,
    diffCount: 164,
  },
  findings: [
    '微调增益：choice 43.5%→76.5%（+33.0pp）、noul 64.3%→85.7%（+21.4pp）、score exact 9.6%→57.4%（MAE 1.19→0.56）',
    '校准增益：choice ECE 0.223→0.059、noul ECE 0.183→0.099（准确率与校准质量同步改善）',
    '基线系统性缺陷：score exact 仅 9.6% 且等级分布坍缩，对 Score 原语几乎无理解',
    '基线 noul 覆盖 79.1% 但区间准确率仅 64.3%：近乎「全判可处理」；微调后收敛到 66.5%/85.7%',
    '分歧 164/230 条（71%）：微调实质改变了决策分布，分歧集中在 insufficient / 闲聊 / 直播中断类边界',
  ],
}
