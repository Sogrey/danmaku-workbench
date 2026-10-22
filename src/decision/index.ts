/**
 * 决策引擎入口 —— 在这里切换 Mock / HTTP（真实模型）
 *
 * ▶ 当前后段：ACTIVE_PROVIDER = 'mock'（无模型也能跑通全流程）
 * ▶ 接入真实模型（后续步骤）：
 *    1. 启动 backend：uvicorn app.main:app --port 8313
 *    2. 将 ACTIVE_PROVIDER 改为 'http'，重新 npm run dev 即可；
 *       后端默认仍是 mock provider，在 backend/app/providers/__init__.py
 *       中切换 DECISION_PROVIDER=jev / laya 后即为真实模型。
 */
import type { DecisionProvider, ProviderKind } from './provider'
import { createMockProvider } from './mock-provider'
import { createHttpProvider } from './http-provider'

export const ACTIVE_PROVIDER: ProviderKind = 'mock'

let instance: DecisionProvider | null = null

export function getProvider(): DecisionProvider {
  if (!instance) {
    instance = ACTIVE_PROVIDER === 'http' ? createHttpProvider() : createMockProvider()
  }
  return instance
}

export { DecisionEngineError } from './provider'
export type { DecisionProvider, ProviderKind } from './provider'
