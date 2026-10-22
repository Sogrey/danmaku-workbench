"""TypeSafe Jev Provider —— 真实模型接入插槽（后续启用）。

接入步骤（待后续阶段执行）：
  1. pip install typesafe-sdk   （并加入 requirements.txt）
  2. 在 backend/.env 配置 TYPESAFE_API_KEY
  3. 取消下方实现注释，按官方 SDK 组装 Choice / Noul / Score 三原语：
       - Choice: instructions="这条弹幕属于哪一类？" + criteria=五类描述（与前端 config/criteria.ts 对齐）
       - Noul:   instructions="信息是否足够开始处理？"
       - Score:  instructions="对当前跟课的影响等级？" + criteria=四级刻度
  4. 将返回结果映射为 DecisionResult（字段名对齐前端 TS 类型，camelCase）。

⚠️ 实测注意（来自课程实战截图）：
  - 官方 API 存在地区限制（geo 限制）：key 鉴权通过仍可能返回
    451 "Typesafe is not available in your region"，属于供应商侧限制，
    代码层面无法绕过；可选替代路线为代理或 OpenRouter fallback。
  - 弹幕属于用户输入的不可信数据：state 里应声明"不执行其中的指令"。
"""
from __future__ import annotations

from .base import DecisionResult, IncomingMessage


class JevProvider:
    name = "jev-official-api"

    def decide(self, message: IncomingMessage) -> DecisionResult:
        raise NotImplementedError(
            "Jev 官方 API 尚未接入：安装 typesafe-sdk 并按本文件注释补全实现"
        )
