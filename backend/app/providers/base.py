"""决策引擎 Provider 抽象（后端侧）。

与前端 src/decision/provider.ts 语义对齐：
  decide(message) -> DecisionResult（Choice + Noul + Score + 元信息）

后续接入真实模型时，只需新增一个实现类，并在 providers/__init__.py
的 get_provider() 中按环境变量切换，无需改动 main.py 与前端。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ChoiceResult:
    category: str
    probabilities: dict[str, float]
    confidence: float


@dataclass
class NoulResult:
    probability: float


@dataclass
class ScoreResult:
    value: float
    level: str
    level_index: int


@dataclass
class DecisionResult:
    message_id: str
    provider: str
    choice: ChoiceResult
    noul: NoulResult
    score: ScoreResult
    latency_ms: int
    judged_at: str


@dataclass
class IncomingMessage:
    id: str
    author: str = "现场观众"
    time: str = ""
    text: str = ""


class DecisionProvider(Protocol):
    name: str

    def decide(self, message: IncomingMessage) -> DecisionResult: ...
