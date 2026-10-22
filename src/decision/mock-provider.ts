/**
 * Mock 决策引擎 —— 关键词规则模拟 Jev 三原语输出
 *
 * 输出结构与真实 Jev /v1/systemone 返回完全同构：
 *   Choice（类别+概率分布+置信度） / Noul（信息充分性概率） / Score（0~3 加权分）
 * 并模拟 300~900ms 的决策延迟，便于还原真实体验。
 */
import type { CategoryId, DanmakuMessage, DecisionResult } from '@/types'
import type { DecisionProvider } from './provider'
import { DecisionEngineError } from './provider'
import { CATEGORY_ORDER } from '@/config/criteria'
import { countHits, HIGH_IMPACT, KEYWORDS } from './keywords'

const rand = (min: number, max: number) => min + Math.random() * (max - min)
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/** 三选项近似公式推广到 K 个候选：confidence ≈ (max_p × K − 1) / (K − 1) */
function confidenceOf(probabilities: number[]): number {
  const max = Math.max(...probabilities)
  const k = probabilities.length
  return clamp((max * k - 1) / (k - 1), 0, 1)
}

interface Judgment {
  category: CategoryId
  hits: Record<CategoryId, number>
  noul: number
  score: number
}

function judgeText(text: string): Judgment {
  const t = text.trim()

  const hits: Record<CategoryId, number> = {
    technical: countHits(t, KEYWORDS.technical),
    feedback: countHits(t, KEYWORDS.feedback),
    chat: countHits(t, KEYWORDS.chat),
    spam: countHits(t, KEYWORDS.spam),
    insufficient: countHits(t, KEYWORDS.insufficient),
  }

  // 1) 推广干扰优先拦截
  if (hits.spam > 0) {
    return { category: 'spam', hits, noul: rand(0.55, 0.8), score: rand(0.1, 0.35) }
  }

  // 2) 明确的听课反馈
  if (hits.feedback > 0) {
    const highImpact = countHits(t, HIGH_IMPACT) > 0
    return {
      category: 'feedback',
      hits,
      noul: t.length >= 8 ? rand(0.82, 0.97) : rand(0.6, 0.85),
      score: highImpact ? rand(2.6, 3.0) : rand(0.9, 1.6),
    }
  }

  // 3) 技术提问
  if (hits.technical > 0) {
    // 短文本 + 模糊指代开头 → 对象不明，仍属信息不足（对齐原版："这个怎么弄"进待补信息区）
    if (t.length <= 10 && /^(这个|那个|刚才|它|他|这|那)/.test(t) && hits.technical <= 2) {
      return { category: 'insufficient', hits, noul: rand(0.25, 0.55), score: rand(0.0, 0.5) }
    }
    const highImpact = countHits(t, HIGH_IMPACT) > 0
    return {
      category: 'technical',
      hits,
      noul: t.length >= 10 ? rand(0.82, 0.96) : rand(0.45, 0.75),
      score: highImpact ? rand(2.1, 2.9) : rand(0.8, 1.6),
    }
  }

  // 4) 普通聊天
  if (hits.chat > 0) {
    return { category: 'chat', hits, noul: rand(0.85, 0.97), score: rand(0.0, 0.3) }
  }

  // 5) 短文本 + 模糊指代 → 信息不足
  if (t.length <= 8 || hits.insufficient >= 2) {
    return { category: 'insufficient', hits, noul: rand(0.25, 0.55), score: rand(0.0, 0.5) }
  }

  // 6) 兜底：较长的无类别文本视为聊天
  return { category: 'chat', hits, noul: rand(0.7, 0.9), score: rand(0.0, 0.4) }
}

function buildProbabilities(main: CategoryId, strength: number): Record<CategoryId, number> {
  // 主类别概率 = 基线 + 命中强度 + 抖动；其余类别按固定先验分摊
  const base = 0.62 + 0.05 * strength + rand(-0.05, 0.3)
  const mainP = clamp(base, 0.55, 0.99)

  const priors: Partial<Record<CategoryId, number>> = {
    technical: 0.3,
    feedback: 0.22,
    chat: 0.26,
    spam: 0.04,
    insufficient: 0.18,
  }
  delete priors[main]

  const restTotal = 1 - mainP
  const priorSum = (Object.values(priors) as number[]).reduce((a, b) => a + b, 0)

  const probabilities = {} as Record<CategoryId, number>
  for (const cat of CATEGORY_ORDER) {
    probabilities[cat] = cat === main ? mainP : (priors[cat] as number) / priorSum * restTotal
  }
  // 归一化浮点误差
  const sum = CATEGORY_ORDER.reduce((a, c) => a + probabilities[c], 0)
  for (const cat of CATEGORY_ORDER) probabilities[cat] = probabilities[cat] / sum
  probabilities[main] = mainP
  return probabilities
}

function scoreLevelIndex(value: number): number {
  return clamp(Math.round(value), 0, 3)
}

export function createMockProvider(): DecisionProvider {
  return {
    name: 'mock-rule-engine',
    kind: 'mock',

    async decide(message: DanmakuMessage): Promise<DecisionResult> {
      // 模拟决策延迟（Jev 官方口径 70~500ms，加上网络往返取 300~900ms）
      await new Promise((r) => setTimeout(r, rand(300, 900)))

      // 模拟网络/服务异常（便于演示失败降级）：可从 UI 触发
      if ((message as DanmakuMessage & { forceError?: boolean }).forceError) {
        throw new DecisionEngineError('模拟决策服务异常（forceError）')
      }

      const started = performance.now()
      const j = judgeText(message.text)
      const probabilities = buildProbabilities(j.category, Math.min(4, Math.max(...Object.values(j.hits))))
      const scoreValue = clamp(j.score, 0, 3)

      return {
        messageId: message.id,
        provider: 'mock-rule-engine',
        choice: {
          category: j.category,
          probabilities,
          confidence: confidenceOf(CATEGORY_ORDER.map((c) => probabilities[c])),
        },
        noul: { probability: clamp(j.noul, 0, 1) },
        score: {
          value: Number(scoreValue.toFixed(2)),
          levelIndex: scoreLevelIndex(scoreValue),
          level: '',
        },
        latencyMs: Math.round(performance.now() - started + rand(300, 900)),
        judgedAt: new Date().toISOString(),
      }
    },

    describe() {
      return 'Mock 规则引擎（关键词模拟 Jev 三原语输出，300~900ms）'
    },
  }
}
