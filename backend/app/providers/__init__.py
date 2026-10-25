"""决策 Provider 注册表：按环境变量 DECISION_PROVIDER 切换。

可选值：mock（默认）/ laya（微调 checkpoint，进程内推理）/ jev（官方 API，暂缓）

v0.2 已接入真实模型：
    DECISION_PROVIDER=laya → 加载 D:/AI/laya/danmaku-dm-v0.2
    （LoRA 微调 + 分桶温度校准，eval_acc 0.770），首次加载约 10s，
    之后单条弹幕推理 ~几十 ms（GPU）。

模型 614MB 只允许进程内加载一次：本模块对 Provider 实例做模块级
单例缓存，health / decide 共享同一实例。DECISION_PROVIDER 在进程
生命周期内视为不变（修改环境变量需重启 uvicorn）。
"""
from __future__ import annotations

import os

from .base import DecisionProvider, IncomingMessage
from .mock import MockProvider

_provider: DecisionProvider | None = None


def get_provider() -> DecisionProvider:
    """获取决策 Provider 单例（首次调用时初始化，之后直接复用）。"""
    global _provider
    if _provider is not None:
        return _provider
    kind = os.environ.get("DECISION_PROVIDER", "mock").lower()
    if kind == "mock":
        _provider = MockProvider()
    elif kind == "laya":
        from .laya import LayaProvider

        _provider = LayaProvider()
    elif kind == "jev":
        from .jev_stub import JevProvider

        _provider = JevProvider()
    else:
        raise ValueError(f"未知的决策引擎：{kind}（可选 mock / jev / laya）")
    return _provider


__all__ = ["get_provider", "DecisionProvider", "IncomingMessage"]
