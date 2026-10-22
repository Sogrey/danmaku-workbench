"""Laya Provider —— 开源决策引擎接入插槽（后续启用，国内自托管推荐路线）。

背景（选型依据）：
  - Jev 官方 API 在国内存在 451 地区限制，Laya（Apache 2.0，421M）可自托管，
    提供与 Jev 同 wire 协议的 POST /v1/systemone 服务（laya-serve）。
  - 注意工程红线：零样本近随机（必须先微调）、>20 选项架构性崩溃、
    出厂概率过度自信（必须做温度拟合）、中文场景 Router(default="multilingual")。

接入步骤（待后续阶段执行）：
  1. pip install "laya[serve]"；微调 + 温度拟合后自托管 laya-serve
  2. 本 Provider 调用 laya 的 /v1/systemone（OpenAI 兼容 fetch）或直接进程内 import laya
  3. 问题定义与 MockProvider 的五类 criteria / Noul / Score 保持一致
"""
from __future__ import annotations

from .base import DecisionResult, IncomingMessage


class LayaProvider:
    name = "laya-self-hosted"

    def decide(self, message: IncomingMessage) -> DecisionResult:
        raise NotImplementedError(
            "Laya 自托管尚未接入：先完成微调与温度拟合，再按本文件注释补全实现"
        )
