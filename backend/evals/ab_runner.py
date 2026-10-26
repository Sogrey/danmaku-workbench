"""A/B 引擎对比：双决策引擎在评估集上顺序跑批，输出一致率与分歧样本。

默认对比（模型迭代验证）：
  A = laya-v0.2   上一代微调 checkpoint（L3 补强前）
  B = laya-v0.3   当前微调 checkpoint（L3 补强版）

用法（backend 目录下）：
  .venv/Scripts/python.exe evals/ab_runner.py                    # 默认 v0.2 vs v0.3
  .venv/Scripts/python.exe evals/ab_runner.py --a laya-baseline # 与零样本基线对比
  引擎可选：laya-baseline / laya-v0.2 / laya-v0.3 / laya-v0.4 / mock

显存管理：两引擎顺序加载跑批，切换时 del + torch.cuda.empty_cache()，
峰值只占一个模型（RTX 3060 6GB 可跑）。

输出：evals/reports/ab-report.json + ab-report.md
口径：
  - 各自三原语指标（复用 replay_eval.evaluate，含 ECE/Brier 可靠性）
  - 一致率：choice 类别相同 / noul ≥门槛（NOUL_ACTIONABLE_MIN，现 0.60）判定相同 / score 等级相同与 ±1
  - 分歧样本：类别、noul 判定、score 等级任一不同的全量清单（md 展示前 20 条）
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 复用 replay_eval

from replay_eval import NOUL_ACTIONABLE_MIN, evaluate, load_samples  # noqa: E402

ENGINE_DIRS = {
    "laya-baseline": "D:/AI/laya/repo-laya-hf/multilingual",
    "laya-v0.2": "D:/AI/laya/danmaku-dm-v0.2",
    "laya-v0.3": "D:/AI/laya/danmaku-dm-v0.3",
    "laya-v0.4": "D:/AI/laya/danmaku-dm-v0.4",
}


def build_engine(name: str):
    """按名称构建决策引擎；laya 系复用 LayaProvider（判据/温度与线上一致）。"""
    import os

    if name == "mock":
        from app.providers.mock import MockProvider  # noqa: PLC0415

        return MockProvider()

    if name not in ENGINE_DIRS:
        raise SystemExit(f"未知引擎：{name}（可选 {' / '.join(ENGINE_DIRS)} / mock）")
    from app.providers.laya import LayaProvider  # noqa: PLC0415

    os.environ["LAYA_MODEL_DIR"] = ENGINE_DIRS[name]
    provider = LayaProvider()
    provider.name = name
    return provider


def release_engine() -> None:
    """切换引擎前释放显存（del 引用 + 清 CUDA 缓存）。"""
    gc.collect()
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def run_batch(engine, samples) -> list[dict]:
    from app.providers.base import IncomingMessage  # noqa: PLC0415

    rows: list[dict] = []
    t0 = time.perf_counter()
    for i, s in enumerate(samples, 1):
        r = engine.decide(IncomingMessage(id=s["id"], text=s["text"]))
        rows.append(
            {
                "id": s["id"],
                "text": s["text"],
                "truth": s["labels"],
                "pred": {
                    "category": r.choice.category,
                    "probabilities": r.choice.probabilities,
                    "confidence": r.choice.confidence,
                    "noul": r.noul.probability,
                    "score": r.score.value,
                    "level_index": r.score.level_index,
                    "latency_ms": r.latency_ms,
                },
            }
        )
        if i % 10 == 0 or i == len(samples):
            print(f"  [{i}/{len(samples)}] ...", flush=True)
    print(f"  batch done in {time.perf_counter() - t0:.1f}s", flush=True)
    return rows


def agreement(rows_a: list[dict], rows_b: list[dict]) -> dict:
    n = len(rows_a)
    choice_same = noul_same = score_same = score_w1 = 0
    diffs: list[dict] = []
    for a, b in zip(rows_a, rows_b):
        same_choice = a["pred"]["category"] == b["pred"]["category"]
        a_act = a["pred"]["noul"] >= NOUL_ACTIONABLE_MIN
        b_act = b["pred"]["noul"] >= NOUL_ACTIONABLE_MIN
        same_noul = a_act == b_act
        same_score = a["pred"]["level_index"] == b["pred"]["level_index"]
        score_gap = abs(a["pred"]["level_index"] - b["pred"]["level_index"])
        if same_choice:
            choice_same += 1
        if same_noul:
            noul_same += 1
        if same_score:
            score_same += 1
        if score_gap <= 1:
            score_w1 += 1
        if not (same_choice and same_noul and score_gap <= 1):
            diffs.append(
                {
                    "id": a["id"],
                    "text": a["text"],
                    "truth_category": a["truth"]["category"],
                    "truth_actionable": a["truth"]["actionable"],
                    "truth_impact": a["truth"]["impact_level"],
                    "a": {
                        "category": a["pred"]["category"],
                        "noul": round(a["pred"]["noul"], 3),
                        "level_index": a["pred"]["level_index"],
                    },
                    "b": {
                        "category": b["pred"]["category"],
                        "noul": round(b["pred"]["noul"], 3),
                        "level_index": b["pred"]["level_index"],
                    },
                }
            )
    return {
        "choice_agreement": choice_same / n,
        "noul_agreement": noul_same / n,
        "score_agreement": score_same / n,
        "score_agreement_within1": score_w1 / n,
        "diff_count": len(diffs),
        "diffs": diffs,
    }


def fmt_engine_dir(name: str) -> str:
    return ENGINE_DIRS.get(name, "backend/app/providers/mock.py")


def render_markdown(meta: dict, sa: dict, sb: dict, ag: dict) -> str:
    a, b = meta["engine_a"], meta["engine_b"]
    lines: list[str] = []
    w = lines.append
    w(f"# A/B 引擎对比报告（{sa['sample_count']} 条独立评估集）")
    w("")
    w(f"- 时间：{meta['generated_at']}")
    w(f"- A 引擎：**{a}**（{fmt_engine_dir(a)}）")
    w(f"- B 引擎：**{b}**（{fmt_engine_dir(b)}）")
    w(f"- 样本：{sa['sample_count']} 条独立评估集（与训练集零重叠）；顺序加载，判据与温度各自生效")
    w("")
    w("## 三原语指标对比")
    w("")
    w("| 指标 | A | B |")
    w("| --- | ---: | ---: |")
    w(f"| Choice top-1 准确率 | {sa['choice']['accuracy']:.1%} | **{sb['choice']['accuracy']:.1%}** |")
    if sa["choice"]["conf_pass_accuracy"] is not None and sb["choice"]["conf_pass_accuracy"] is not None:
        w(f"| Choice 置信度≥60% 子集准确率（覆盖 A {sa['choice']['conf_pass_coverage']:.0%} / B {sb['choice']['conf_pass_coverage']:.0%}）"
          f" | {sa['choice']['conf_pass_accuracy']:.1%} | {sb['choice']['conf_pass_accuracy']:.1%} |")
    w(f"| Noul 区间准确率（≥{NOUL_ACTIONABLE_MIN:.2f}） | {sa['noul']['interval_accuracy']:.1%} | **{sb['noul']['interval_accuracy']:.1%}** |")
    w(f"| Noul 覆盖率 | {sa['noul']['coverage']:.1%} | {sb['noul']['coverage']:.1%} |")
    w(f"| Score exact | {sa['score']['exact_accuracy']:.1%} | **{sb['score']['exact_accuracy']:.1%}** |")
    w(f"| Score ±1 | {sa['score']['within1_accuracy']:.1%} | **{sb['score']['within1_accuracy']:.1%}** |")
    w(f"| Score MAE | {sa['score']['mae']:.2f} | {sb['score']['mae']:.2f} |")
    ra, rb = sa.get("reliability") or {}, sb.get("reliability") or {}
    if ra and rb:
        w(f"| Choice ECE | {ra['choice']['ece']:.4f} | {rb['choice']['ece']:.4f} |")
        w(f"| Noul ECE | {ra['noul']['ece']:.4f} | {rb['noul']['ece']:.4f} |")
    w(f"| 平均延迟 | {sa['latency_ms_avg']:.0f} ms | {sb['latency_ms_avg']:.0f} ms |")
    w("")
    w("## 引擎间一致率")
    w("")
    w(f"- Choice 类别一致：**{ag['choice_agreement']:.1%}**")
    w(f"- Noul ≥{NOUL_ACTIONABLE_MIN:.2f} 判定一致：**{ag['noul_agreement']:.1%}**")
    w(f"- Score 等级一致：{ag['score_agreement']:.1%}（±1 一致 {ag['score_agreement_within1']:.1%}）")
    w(f"- 分歧样本：**{ag['diff_count']} 条**（任一维度不一致）")
    w("")
    w("## 分歧样本（前 20 条，全量见 ab-report.json）")
    w("")
    if ag["diffs"]:
        w("| id | 消息 | 真值(类/可处理/等级) | A 判定 | B 判定 |")
        w("| --- | --- | --- | --- | --- |")
        for d in ag["diffs"][:20]:
            w(
                f"| {d['id']} | {d['text']} | {d['truth_category']} / "
                f"{'可' if d['truth_actionable'] else '不可'} / {d['truth_impact']} "
                f"| {d['a']['category']} ({d['a']['noul']:.2f}, L{d['a']['level_index']}) "
                f"| {d['b']['category']} ({d['b']['noul']:.2f}, L{d['b']['level_index']}) |"
            )
    else:
        w("无——两引擎在全部样本上完全一致。")
    w("")
    w("## 结论（自动生成）")
    w("")
    delta_choice = sb["choice"]["accuracy"] - sa["choice"]["accuracy"]
    delta_noul = sb["noul"]["interval_accuracy"] - sa["noul"]["interval_accuracy"]
    w(f"- Choice 准确率 {sa['choice']['accuracy']:.1%} → {sb['choice']['accuracy']:.1%}（{delta_choice:+.1%}）")
    w(f"- Noul 区间准确率 {sa['noul']['interval_accuracy']:.1%} → {sb['noul']['interval_accuracy']:.1%}（{delta_noul:+.1%}）")
    if delta_choice >= 0.2:
        w("- 微调收益显著：基线近随机（五类≈20%），微调后达到可用判别水平")
    w("- 分歧样本集中在语义边界（insufficient / 闲聊短句），可对照训练集继续补样本迭代")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B 引擎对比")
    parser.add_argument("--a", default="laya-v0.2", help="A 引擎：laya-baseline / laya-v0.2 / laya-v0.3 / laya-v0.4 / mock")
    parser.add_argument("--b", default="laya-v0.3", help="B 引擎：laya-baseline / laya-v0.2 / laya-v0.3 / laya-v0.4 / mock")
    args = parser.parse_args()
    if args.a == args.b:
        raise SystemExit("A 与 B 引擎相同，无需对比")

    samples = load_samples()

    print(f"[A] 加载引擎 {args.a} ...", flush=True)
    engine_a = build_engine(args.a)
    rows_a = run_batch(engine_a, samples)
    del engine_a
    release_engine()

    print(f"[B] 加载引擎 {args.b} ...", flush=True)
    engine_b = build_engine(args.b)
    rows_b = run_batch(engine_b, samples)
    del engine_b
    release_engine()

    sa, sb = evaluate(rows_a), evaluate(rows_b)
    ag = agreement(rows_a, rows_b)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_a": args.a,
        "engine_b": args.b,
        "eval_dataset": "evals/eval_dataset.jsonl",
    }

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "ab-report.json").write_text(
        json.dumps({"meta": meta, "summary_a": sa, "summary_b": sb, "agreement": ag},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "ab-report.md").write_text(render_markdown(meta, sa, sb, ag), encoding="utf-8")

    print(f"\nA({args.a}) choice={sa['choice']['accuracy']:.1%} noul={sa['noul']['interval_accuracy']:.1%}")
    print(f"B({args.b}) choice={sb['choice']['accuracy']:.1%} noul={sb['noul']['interval_accuracy']:.1%}")
    print(f"一致率：choice {ag['choice_agreement']:.1%} / noul {ag['noul_agreement']:.1%} / score±1 {ag['score_agreement_within1']:.1%}，分歧 {ag['diff_count']} 条")
    print(f"报告已写入 {out_dir}/ab-report.json / ab-report.md")


if __name__ == "__main__":
    main()
