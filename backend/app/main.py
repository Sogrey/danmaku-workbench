"""Jev 直播弹幕工作台 · 决策服务（FastAPI 骨架）

职责：接收前端 POST /api/decide，调用可插拔的决策 Provider
（当前 mock，后续 Jev / Laya），返回与前端 DecisionResult 类型
对齐的结构化判断（camelCase JSON）。

运行：
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --host 127.0.0.1 --port 8313 --reload
前端切换：把 src/decision/index.ts 的 ACTIVE_PROVIDER 改为 'http'。
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .providers import IncomingMessage, get_provider

app = FastAPI(
    title="Jev 直播弹幕工作台 · 决策服务",
    version="0.1.0",
    description="弹幕意图判断（Choice/Noul/Score）· Provider 可插拔（mock / jev / laya）",
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
    # 与前端 DecisionResult TS 类型对齐（camelCase）
    return {
        "messageId": result.message_id,
        "provider": result.provider,
        "choice": result.choice,
        "noul": result.noul,
        "score": result.score,
        "latencyMs": result.latency_ms,
        "judgedAt": result.judged_at,
    }
