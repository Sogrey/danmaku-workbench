/**
 * Jev 直播弹幕工作台 —— 核心类型定义
 *
 * 与 TypeSafe Jev 官方 API 的三原语对齐：
 *   Choice → ChoiceResult   （从预设选项中选择一项 + 概率分布）
 *   Noul  → NoulResult      （布尔命题成立的概率）
 *   Score → ScoreResult     （有序等级上的加权评分）
 */

/** 消息五分类（对应课程中的 Choice criteria） */
export type CategoryId = 'technical' | 'feedback' | 'chat' | 'spam' | 'insufficient'

/** 分流去向 */
export type RouteTarget = 'instructor' | 'assistant' | 'confirm' | 'none'

/** 弹幕消息状态 */
export type MessageStatus = 'pending' | 'judging' | 'done' | 'failed'

/** 一条弹幕消息 */
export interface DanmakuMessage {
  id: string
  author: string
  /** HH:mm:ss */
  time: string
  text: string
  status: MessageStatus
  /** 判断完成后回填的类别 */
  label?: CategoryId
  /** 判断结果（模型/引擎返回） */
  decision?: DecisionResult
  /** 分流结果（程序规则） */
  disposition?: Disposition
  /** 是否为用户手动录入 */
  manual?: boolean
}

/** Choice 原语：类别 + 全候选概率分布 + 置信度 */
export interface ChoiceResult {
  category: CategoryId
  probabilities: Record<CategoryId, number>
  /** 置信度 = 概率分布集中度（≠ 准确率） */
  confidence: number
}

/** Noul 原语：信息充分性概率 */
export interface NoulResult {
  /** P(信息足够开始处理)，达到 80% 才进入讲师/助教待办 */
  probability: number
}

/** Score 原语：对当前跟课影响的优先级评分 */
export interface ScoreResult {
  /** 0 ~ 3 的加权分 */
  value: number
  /** 等级名（对应 SCORE_LEVEL_NAMES） */
  level: string
  /** 等级下标 0-3 */
  levelIndex: number
}

/** 一次完整的决策结果（Provider 输出，与模型无关） */
export interface DecisionResult {
  messageId: string
  /** 决策引擎标识：mock / http / jev / laya ... */
  provider: string
  choice: ChoiceResult
  noul: NoulResult
  score: ScoreResult
  /** 决策耗时（ms），仅用于展示 */
  latencyMs: number
  /** 判断完成时间 */
  judgedAt: string
}

/** 程序分流结果（代码规则，不是模型输出） */
export interface Disposition {
  target: RouteTarget
  /** 分流依据（面向人解释） */
  reason: string
}

/** 处理记录（分类与记录页 / 待办队列使用） */
export interface WorkRecord {
  id: string
  /** 进入队列时间 */
  time: string
  author: string
  text: string
  decision: DecisionResult
  disposition: Disposition
  /** 待办是否已被人工标记完成 */
  done: boolean
}
