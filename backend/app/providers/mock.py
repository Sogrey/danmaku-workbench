"""Mock 决策引擎（后端版）—— 关键词规则模拟 Jev 三原语输出。

与前端 src/decision/mock-provider.ts 保持同构，输出 camelCase JSON
（DecisionResult 序列化后的字段名与前端 TS 类型一一对应）。
"""
from __future__ import annotations

import random
import re
import time
from datetime import datetime, timezone

from .base import DecisionResult, IncomingMessage

CATEGORY_ORDER = ["technical", "feedback", "chat", "spam", "insufficient"]

KEYWORDS = {
    "technical": [
        "怎么", "如何", "为什么", "？", "?", "报错", "error", "安装", "配置", "代码",
        "sdk", "api", "调用", "区别", "差别", "是什么", "支持", "异步", "同步", "print",
        "module", "接口", "请求", "token", "概率", "阈值", "分类", "回复", "写出", "生成",
    ],
    "feedback": [
        "声音", "音量", "画面", "黑屏", "卡", "字幕", "字号", "太小", "放大",
        "断", "麦克风", "听不清", "调高", "调大", "没声音", "听不到", "断流", "花屏",
    ],
    "spam": ["微信", "vx", "加群", "领取", "链接", "优惠", "兼职", "赚钱", "免费领", "私聊", "推广"],
    "chat": ["你好", "哈哈", "嘿嘿", "666", "不错", "赞", "厉害", "辛苦", "谢谢", "看懂了", "牛"],
    "insufficient": ["这个", "那个", "刚才", "它", "他"],
}

HIGH_IMPACT = ["黑屏", "断流", "没声音", "听不到", "无法", "装不上", "报错", "失败", "卡死"]

SCORE_LEVEL_NAMES = ["稍后处理", "正常答疑", "优先协助", "立即关注"]


def _hits(text: str, words: list[str]) -> int:
    return sum(1 for w in words if w in text)


def _judge(text: str) -> tuple[str, float, float]:
    """返回 (主类别, noul 概率, score 分值)"""
    t = text.strip()

    # 短文本 + 模糊指代开头 → 信息不足（优先于技术判断，对齐原版语义）
    if len(t) <= 10 and re.match(r"^(这个|那个|刚才|它|他|这|那)", t) and _hits(t, KEYWORDS["spam"]) == 0 and _hits(t, KEYWORDS["feedback"]) == 0:
        return "insufficient", random.uniform(0.25, 0.55), random.uniform(0.0, 0.5)

    spam_h = _hits(t, KEYWORDS["spam"])
    if spam_h:
        return "spam", random.uniform(0.55, 0.8), random.uniform(0.1, 0.35)

    fb_h = _hits(t, KEYWORDS["feedback"])
    if fb_h:
        high = _hits(t, HIGH_IMPACT) > 0
        noul = random.uniform(0.82, 0.97) if len(t) >= 8 else random.uniform(0.6, 0.85)
        score = random.uniform(2.6, 3.0) if high else random.uniform(0.9, 1.6)
        return "feedback", noul, score

    tech_h = _hits(t, KEYWORDS["technical"])
    if tech_h:
        high = _hits(t, HIGH_IMPACT) > 0
        noul = random.uniform(0.82, 0.96) if len(t) >= 10 else random.uniform(0.45, 0.75)
        score = random.uniform(2.1, 2.9) if high else random.uniform(0.8, 1.6)
        return "technical", noul, score

    if _hits(t, KEYWORDS["chat"]):
        return "chat", random.uniform(0.85, 0.97), random.uniform(0.0, 0.3)

    if len(t) <= 8 or _hits(t, KEYWORDS["insufficient"]) >= 2:
        return "insufficient", random.uniform(0.25, 0.55), random.uniform(0.0, 0.5)

    return "chat", random.uniform(0.7, 0.9), random.uniform(0.0, 0.4)


@dataclass
class MockProvider:
    name: str = "mock-rule-engine"

    def decide(self, message: IncomingMessage) -> DecisionResult:
        started = time.perf_counter()
        # 模拟决策延迟
        time.sleep(random.uniform(0.3, 0.9))

        category, noul, score = _judge(message.text)
        priors = {"technical": 0.3, "feedback": 0.22, "chat": 0.26, "spam": 0.04, "insufficient": 0.18}
        main_p = min(0.99, max(0.55, 0.62 + random.uniform(-0.05, 0.3)))
        rest = 1.0 - main_p
        prior_sum = sum(v for k, v in priors.items() if k != category)
        probs = {
            cat: (main_p if cat == category else priors[cat] / prior_sum * rest)
            for cat in CATEGORY_ORDER
        }
        confidence = min(1.0, max(0.0, (main_p * len(CATEGORY_ORDER) - 1) / (len(CATEGORY_ORDER) - 1)))
        level_index = max(0, min(3, round(score)))

        return DecisionResult(
            message_id=message.id,
            provider=self.name,
            choice={
                "category": category,
                "probabilities": probs,
                "confidence": confidence,
            },
            noul={"probability": noul},
            score={
                "value": round(score, 2),
                "level": SCORE_LEVEL_NAMES[level_index],
                "levelIndex": level_index,
            },
            latency_ms=int((time.perf_counter() - started) * 1000),
            judged_at=datetime.now(timezone.utc).isoformat(),
        )
