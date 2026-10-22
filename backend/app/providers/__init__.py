"""决策 Provider 注册表：按环境变量 DECISION_PROVIDER 切换。

可选值：mock（默认，当前阶段） / jev / laya
切换真实模型：设置 DECISION_PROVIDER=jev 或 laya，并补全对应 stub 实现。
"""
from __future__ import annotations

import os

from .base import DecisionProvider, IncomingMessage
from .mock import MockProvider


def get_provider() -> DecisionProvider:
    kind = os.environ.get("DECISION_PROVIDER", "mock").lower()
    if kind == "mock":
        return MockProvider()
    if kind == "jev":
        from .jev_stub import JevProvider

        return JevProvider()
    if kind == "laya":
        from .laya_stub import LayaProvider

        return LayaProvider()
    raise ValueError(f"未知的决策引擎：{kind}（可选 mock / jev / laya）")


__all__ = ["get_provider", "DecisionProvider", "IncomingMessage"]
