/**
 * 决策引擎入口 —— 在这里切换 Mock / HTTP（真实模型）
 *
 * ▶ 当前后段：ACTIVE_PROVIDER = 'http'（真实 Laya 微调模型，eval_acc 0.770）
 * ▶ 后端：uvicorn app.main:app --port 8313（backend/.venv，需 DECISION_PROVIDER=laya）
 *   启动时预热加载 checkpoint（首次约 1 分钟），之后每条弹幕推理 ~几十 ms
 * ▶ 无后端时切回 'mock'：不依赖决策服务，全流程仍可跑通
 */
import type { DecisionProvider, ProviderKind } from './provider'
import { createMockProvider } from './mock-provider'
import { createHttpProvider } from './http-provider'

export const ACTIVE_PROVIDER: ProviderKind = 'http'

let instance: DecisionProvider | null = null

export function getProvider(): DecisionProvider {
  if (!instance) {
    instance = ACTIVE_PROVIDER === 'http' ? createHttpProvider() : createMockProvider()
  }
  return instance
}

export { DecisionEngineError } from './provider'
export type { DecisionProvider, ProviderKind } from './provider'
