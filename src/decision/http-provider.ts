/**
 * HTTP 决策 Provider —— 指向后端 FastAPI 决策服务（/api/decide）
 *
 * 后端 providers 目录下预留了 JevProvider / LayaProvider 插槽：
 *   - Jev：typesafe_sdk 调 POST https://api.typesafe.ai/v1/systemone
 *     （注意官方 API 存在地区限制：key 有效仍可能返回 451）
 *   - Laya：自托管 laya-serve（与 Jev 同 wire 协议），数据不出内网
 * 切换方式：把 src/decision/index.ts 中 ACTIVE_PROVIDER 改为 'http'。
 */
import type { DanmakuMessage, DecisionResult } from '@/types'
import type { DecisionProvider } from './provider'
import { DecisionEngineError } from './provider'

export function createHttpProvider(base = '/api/decide'): DecisionProvider {
  return {
    name: 'http-decision-service',
    kind: 'http',

    async decide(message: DanmakuMessage): Promise<DecisionResult> {
      let res: Response
      try {
        res = await fetch(base, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: {
              id: message.id,
              author: message.author,
              time: message.time,
              text: message.text,
            },
          }),
        })
      } catch (err) {
        // 网络层失败：对齐原工作台的降级文案（保留原文、可稍后重试）
        throw new DecisionEngineError('真实请求失败：决策服务不可达', err)
      }
      if (!res.ok) {
        throw new DecisionEngineError(`真实请求失败：决策服务返回 HTTP ${res.status}`)
      }
      const data = (await res.json()) as DecisionResult
      return data
    },

    describe() {
      return 'HTTP 决策服务（backend/app/providers：Mock / Jev / Laya 可插拔）'
    },
  }
}
