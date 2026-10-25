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
  passRate: 0.756,
  medianTopProb: 0.83,
  note: '校准后主概率 median 0.83，60% 门槛下通过率 75.6%，沿用课程原版门槛',
}

/** 评估回放摘要（45 条独立评估集，2026-10-25，HTTP 回放，平均 90ms/条） */
export const EVAL_REPLAY = {
  generatedAt: '2026-10-25',
  sampleCount: 45,
  avgLatencyMs: 90,
  choice: {
    accuracy: 0.822,
    confPassCoverage: 0.489,
    confPassAccuracy: 0.909,
  },
  noul: {
    intervalAccuracy: 0.867,
    coverage: 0.578,
    passedAccuracy: 0.923,
    meanProbTruthActionable: 0.725,
    meanProbTruthInsufficient: 0.266,
  },
  score: {
    exactAccuracy: 0.556,
    within1Accuracy: 0.978,
    mae: 0.55,
  },
}

/** Choice 混淆矩阵（行=真值，列=预测；顺序同 CATEGORY_ORDER） */
export const CONFUSION_LABELS = ['technical', 'feedback', 'chat', 'spam', 'insufficient'] as const
export const CONFUSION_MATRIX: number[][] = [
  [10, 0, 0, 0, 0],
  [1, 9, 0, 0, 0],
  [0, 0, 6, 0, 2],
  [0, 0, 0, 8, 0],
  [4, 1, 0, 0, 4],
]

/** 错误样本画像（13 条错误的分布结论） */
export const ERROR_PROFILE = {
  total: 13,
  findings: [
    'technical 10/10、spam 8/10 全对，主力类别可靠',
    '主要混淆在 insufficient 边界：4 条被判 technical（如「到第三步就不行了」缺上下文）',
    '2 条闲聊被判 insufficient（如「666」，短文本信息量低）',
    'Score ±1 容差命中 97.8%，等级方向基本不偏，exact 弱与官方结论一致',
  ],
}
