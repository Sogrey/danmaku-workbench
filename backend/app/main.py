"""Jev 直播弹幕工作台 · 决策服务（FastAPI）

职责：接收前端 POST /api/decide，调用可插拔的决策 Provider
（mock / laya 微调 checkpoint / jev 官方 API），把后端 dataclass
显式映射为前端 DecisionResult 期望的 camelCase JSON。

运行（真实模型）：
    cd backend
    .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8313
    # 环境变量 DECISION_PROVIDER=laya（默认 mock）；可选 LAYA_DEVICE=cuda|cpu
启动时会预热加载 Provider（laya 首次加载约 10s，之后每条弹幕 ~几十 ms）。
前端切换：把 src/decision/index.ts 的 ACTIVE_PROVIDER 改为 'http'。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .providers import IncomingMessage, get_provider


@asynccontextmanager
async def lifespan(_: FastAPI):
    provider = get_provider()  # 预热：启动时完成模型加载，避免首条弹幕等待
    print(f"[decision] provider ready: {provider.name}", flush=True)
    yield


app = FastAPI(
    title="Jev 直播弹幕工作台 · 决策服务",
    version="0.2.0",
    description="弹幕意图判断（Choice/Noul/Score）· Provider 可插拔（mock / laya / jev）",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecideRequestBody(BaseModel):
    message: dict[str, Any]


@app.get("/api/health")
def health() -> dict[str, Any]:
    provider = get_provider()
    return {"ok": True, "provider": provider.name}


@app.post("/api/decide")
def decide(body: DecideRequestBody) -> dict[str, Any]:
    provider = get_provider()
    msg = IncomingMessage(
        id=str(body.message.get("id", "")),
        author=str(body.message.get("author", "现场观众")),
        time=str(body.message.get("time", "")),
        text=str(body.message.get("text", "")),
    )
    result = provider.decide(msg)
    # 与前端 DecisionResult TS 类型对齐：dataclass 显式映射为 camelCase
    return {
        "messageId": result.message_id,
        "provider": result.provider,
        "choice": {
            "category": result.choice.category,
            "probabilities": result.choice.probabilities,
            "confidence": result.choice.confidence,
        },
        "noul": {"probability": result.noul.probability},
        "score": {
            "value": result.score.value,
            "level": result.score.level,
            "levelIndex": result.score.level_index,
        },
        "latencyMs": result.latency_ms,
        "judgedAt": result.judged_at,
    }
