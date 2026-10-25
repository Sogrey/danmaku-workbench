/**
 * 程序分流规则 —— 「模型判断，代码决策」的代码侧
 *
 * 规则（阈值常量见 criteria.ts，随校准数据更新）：
 *   分类概率 ≥ 60% 且 处理条件概率 ≥ 65% → 进入讲师/助教待办
 *   其余 → 待确认（人工核对）
 * 普通聊天保留在直播弹幕区，不进入待办。
 */
import type { DecisionResult, Disposition } from '@/types'
import { CATEGORIES, THRESHOLDS } from '@/config/criteria'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`
const ACT_PCT = `${THRESHOLDS.actionableProbability * 100}%`
const CLS_PCT = `${THRESHOLDS.classifyProbability * 100}%`

export function routeDecision(decision: DecisionResult): Disposition {
  const { choice, noul } = decision
  const def = CATEGORIES[choice.category]
  const mainP = choice.probabilities[choice.category]

  // 门槛一：类别概率未达 60% → 一律待确认（哪怕方向对了，也要人工核对）
  if (mainP < THRESHOLDS.classifyProbability) {
    return {
      target: 'confirm',
      reason: `识别为「${def.name}」但分类概率 ${pct(mainP)} 未达 ${CLS_PCT} 门槛，先进入待确认人工核对。`,
    }
  }

  switch (choice.category) {
    case 'technical':
      if (noul.probability >= THRESHOLDS.actionableProbability) {
        return {
          target: 'instructor',
          reason: `技术提问（${pct(mainP)}）且信息充分（${pct(noul.probability)} ≥ ${ACT_PCT}），进入讲师待答。`,
        }
      }
      return {
        target: 'confirm',
        reason: `技术提问（${pct(mainP)}）但处理条件概率 ${pct(noul.probability)} < ${ACT_PCT}，先待确认、等待补充上下文。`,
      }

    case 'feedback':
      if (noul.probability >= THRESHOLDS.actionableProbability) {
        return {
          target: 'assistant',
          reason: `听课反馈（${pct(mainP)}）且信息充分（${pct(noul.probability)} ≥ ${ACT_PCT}），进入助教处理。`,
        }
      }
      return {
        target: 'confirm',
        reason: `听课反馈（${pct(mainP)}）但处理条件概率 ${pct(noul.probability)} < ${ACT_PCT}，先待确认。`,
      }

    case 'chat':
      return {
        target: 'none',
        reason: `普通聊天（${pct(mainP)}），保留在直播弹幕区，不进入待办。`,
      }

    case 'spam':
      return {
        target: 'confirm',
        reason: `疑似推广干扰（${pct(mainP)}），交人工审核。`,
      }

    case 'insufficient':
      return {
        target: 'confirm',
        reason: `信息不足（${pct(mainP)}），对象或诉求不明，待确认后请观众补充上下文。`,
      }
  }
}
