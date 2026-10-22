/**
 * 决策引擎 Provider 抽象 —— 「模型后面再引入」的插槽
 *
 * 当前阶段：MockProvider（关键词规则引擎，模拟 300~900ms 决策延迟）
 * 后续阶段：在 backend/app/providers/ 下实现 JevProvider / LayaProvider，
 *          前端只需把 ACTIVE_PROVIDER 切换为 'http' 即可无缝接入，
 *          所有 UI、分流规则、记录逻辑零改动。
 */
import type { DanmakuMessage, DecisionResult } from '@/types'

export type ProviderKind = 'mock' | 'http'

export interface DecisionProvider {
  /** 引擎标识（展示用） */
  readonly name: string
  readonly kind: ProviderKind
  /** 对一条消息做完整判断（Choice + Noul + Score） */
  decide(message: DanmakuMessage): Promise<DecisionResult>
  /** 引擎说明（头部状态区展示） */
  describe(): string
}

export class DecisionEngineError extends Error {
  constructor(
    message: string,
    public readonly cause?: unknown,
  ) {
    super(message)
    this.name = 'DecisionEngineError'
  }
}
