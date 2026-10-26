"""评估集回放：独立评估集（230 条）批量过决策引擎，输出准确率报告。

两种运行模式：
  http（默认）：复用运行中的决策服务（uvicorn 8313，DECISION_PROVIDER=laya）。
                启动时校验 /api/health 的 provider 名，防止误测 mock；
                模型已加载，230 条约 25 秒跑完。
  local：进程内直接加载 checkpoint（服务未启动时用，模型加载约 80s）。

用法（backend 目录下）：
  .venv/Scripts/python.exe evals/replay_eval.py            # http 模式
  .venv/Scripts/python.exe evals/replay_eval.py --local   # 进程内模式
  可选 --base 覆盖服务地址；--model-dir 覆盖 checkpoint（仅 local 模式）。

输出：evals/reports/eval-report.json + eval-report.md
口径：
  - choice：top-1 准确率 + 5×5 混淆矩阵 + 置信度 ≥60% 门槛子集准确率
  - noul：P(可处理) ≥ 0.60 判 actionable，与真值一致的区间准确率 + 覆盖率
  - score：等级 exact / ±1 命中率 + 与真值等级的 MAE
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 与 src/config/criteria.ts THRESHOLDS、app/main.py 保持一致
CHOICE_CONF_MIN = 0.60
NOUL_ACTIONABLE_MIN = 0.60
CATEGORIES = ["technical", "feedback", "chat", "spam", "insufficient"]
DEFAULT_BASE = "http://127.0.0.1:8313"
DEFAULT_MODEL_DIR = "D:/AI/laya/danmaku-dm-v0.3"


def load_samples() -> list[dict]:
    path = Path(__file__).parent / "eval_dataset.jsonl"
    samples: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            samples.append(json.loads(line))
    if not samples:
        raise SystemExit("评估集为空：eval_dataset.jsonl")
    return samples


def check_http_provider(base: str) -> str:
    """校验运行中的服务确实是 laya（防止拿 mock 结果写评估报告）。"""
    try:
        with urllib.request.urlopen(base + "/api/health", timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as err:  # noqa: BLE001
        raise SystemExit(
            f"决策服务不可达（{base}）：{err}\n"
            "请先启动：DECISION_PROVIDER=laya uvicorn app.main:app --port 8313\n"
            "或改用 --local 进程内模式。"
        ) from err
    name = str(data.get("provider", ""))
    if "laya" not in name:
        raise SystemExit(f"服务 provider={name}，非 laya 微调模型——请用 DECISION_PROVIDER=laya 启动后重试")
    return name


def decide_http(text: str, sid: str, base: str) -> dict:
    payload = json.dumps(
        {"message": {"id": sid, "author": "评估回放", "time": "", "text": text}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/decide", data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_local_decider(model_dir: str):
    """进程内加载 LayaProvider（复用判据/温度配置，与线上一致）。"""
    from app.providers.base import IncomingMessage  # noqa: PLC0415
    from app.providers.laya import LayaProvider  # noqa: PLC0415

    provider = LayaProvider()

    def decide(text: str, sid: str) -> dict:
        r = provider.decide(IncomingMessage(id=sid, author="评估回放", text=text))
        # 与 main.py 相同的 camelCase 映射，保证两条链路口径一致
        return {
            "messageId": r.message_id,
            "provider": r.provider,
            "choice": {
                "category": r.choice.category,
                "probabilities": r.choice.probabilities,
                "confidence": r.choice.confidence,
            },
            "noul": {"probability": r.noul.probability},
            "score": {"value": r.score.value, "level": r.score.level, "levelIndex": r.score.level_index},
            "latencyMs": r.latency_ms,
            "judgedAt": r.judged_at,
        }

    return decide, provider


def evaluate(rows: list[dict]) -> dict:
    n = len(rows)

    # ---------- Choice ----------
    correct = sum(1 for r in rows if r["pred"]["category"] == r["truth"]["category"])
    confusion = {c: {k: 0 for k in CATEGORIES} for c in CATEGORIES}
    for r in rows:
        confusion[r["truth"]["category"]][r["pred"]["category"]] += 1
    conf_pass = [r for r in rows if r["pred"]["confidence"] >= CHOICE_CONF_MIN]
    choice_pass_acc = (
        sum(1 for r in conf_pass if r["pred"]["category"] == r["truth"]["category"]) / len(conf_pass)
        if conf_pass
        else None
    )

    # ---------- Noul ----------
    noul_ok = [
        (r["pred"]["noul"] >= NOUL_ACTIONABLE_MIN) == bool(r["truth"]["actionable"]) for r in rows
    ]
    noul_pos = [r for r in rows if r["pred"]["noul"] >= NOUL_ACTIONABLE_MIN]
    pos_probs = [r["pred"]["noul"] for r in rows if r["truth"]["actionable"]]
    neg_probs = [r["pred"]["noul"] for r in rows if not r["truth"]["actionable"]]

    # ---------- Score ----------
    exact = sum(1 for r in rows if r["pred"]["level_index"] == r["truth"]["impact_level"])
    within1 = sum(1 for r in rows if abs(r["pred"]["level_index"] - r["truth"]["impact_level"]) <= 1)
    mae = sum(abs(r["pred"]["score"] - r["truth"]["impact_level"]) for r in rows) / n

    # ---------- 校准（reliability 分桶 / ECE / Brier）----------
    N_BINS = 5  # 5 等宽桶：230 条下兼顾分桶稳定性与粒度

    def _bins(conf_fn, correct_fn):
        out = []
        for i in range(N_BINS):
            lo, hi = i / N_BINS, (i + 1) / N_BINS
            members = [
                r for r in rows
                if (lo <= conf_fn(r) < hi) or (i == N_BINS - 1 and conf_fn(r) >= hi)
            ]
            if members:
                confs = [conf_fn(r) for r in members]
                accs = [1.0 if correct_fn(r) else 0.0 for r in members]
                out.append({
                    "range": [round(lo, 2), round(hi, 2)],
                    "n": len(members),
                    "avg_confidence": round(sum(confs) / len(confs), 4),
                    "accuracy": round(sum(accs) / len(accs), 4),
                })
            else:
                out.append({"range": [round(lo, 2), round(hi, 2)], "n": 0, "avg_confidence": None, "accuracy": None})
        ece = sum(
            b["n"] / n * abs(b["accuracy"] - b["avg_confidence"]) for b in out if b["n"] > 0
        )
        return out, ece

    choice_bins, choice_ece = _bins(
        lambda r: r["pred"]["probabilities"][r["pred"]["category"]],
        lambda r: r["pred"]["category"] == r["truth"]["category"],
    )
    noul_bins, noul_ece = _bins(
        lambda r: r["pred"]["noul"],
        lambda r: bool(r["truth"]["actionable"]),
    )
    # 多类 Brier（choice）：1/K × Σ(p_c − y_c)²；二类 Brier（noul）：(p − y)²
    choice_brier = sum(
        sum((r["pred"]["probabilities"][c] - (1.0 if c == r["truth"]["category"] else 0.0)) ** 2 for c in CATEGORIES)
        for r in rows
    ) / (n * len(CATEGORIES))
    noul_brier = sum(
        (r["pred"]["noul"] - (1.0 if r["truth"]["actionable"] else 0.0)) ** 2 for r in rows
    ) / n
    # score 按预测等级分组：预测均值 vs 实际等级均值（分箱校准的等级版）
    score_by_level = []
    for lv in range(4):
        members = [r for r in rows if r["pred"]["level_index"] == lv]
        if members:
            score_by_level.append({
                "pred_level": lv,
                "n": len(members),
                "mean_truth": round(sum(r["truth"]["impact_level"] for r in members) / len(members), 3),
                "mean_pred": round(sum(r["pred"]["score"] for r in members) / len(members), 3),
                "mae": round(sum(abs(r["pred"]["score"] - r["truth"]["impact_level"]) for r in members) / len(members), 3),
            })

    errors = [
        {
            "id": r["id"],
            "text": r["text"],
            "truth_category": r["truth"]["category"],
            "pred_category": r["pred"]["category"],
            "confidence": round(r["pred"]["confidence"], 4),
            "noul_ok": (r["pred"]["noul"] >= NOUL_ACTIONABLE_MIN) == bool(r["truth"]["actionable"]),
            "noul": round(r["pred"]["noul"], 4),
            "truth_impact": r["truth"]["impact_level"],
            "pred_impact": r["pred"]["level_index"],
        }
        for r in rows
        if r["pred"]["category"] != r["truth"]["category"]
        or (r["pred"]["noul"] >= NOUL_ACTIONABLE_MIN) != bool(r["truth"]["actionable"])
        or abs(r["pred"]["level_index"] - r["truth"]["impact_level"]) > 1
    ]

    return {
        "thresholds": {"choice_confidence_min": CHOICE_CONF_MIN, "noul_actionable_min": NOUL_ACTIONABLE_MIN},
        "choice": {
            "accuracy": correct / n,
            "confusion": confusion,
            "conf_pass_count": len(conf_pass),
            "conf_pass_coverage": len(conf_pass) / n,
            "conf_pass_accuracy": choice_pass_acc,
        },
        "noul": {
            "interval_accuracy": sum(noul_ok) / n,
            "coverage": len(noul_pos) / n,
            "interval_accuracy_when_passed": (
                sum(1 for r in noul_pos if bool(r["truth"]["actionable"])) / len(noul_pos)
                if noul_pos
                else None
            ),
            "mean_prob_truth_actionable": sum(pos_probs) / len(pos_probs) if pos_probs else None,
            "mean_prob_truth_insufficient": sum(neg_probs) / len(neg_probs) if neg_probs else None,
        },
        "score": {
            "exact_accuracy": exact / n,
            "within1_accuracy": within1 / n,
            "mae": mae,
        },
        "reliability": {
            "bins_count": N_BINS,
            "choice": {"bins": choice_bins, "ece": round(choice_ece, 4), "brier": round(choice_brier, 4)},
            "noul": {"bins": noul_bins, "ece": round(noul_ece, 4), "brier": round(noul_brier, 4)},
            "score_by_pred_level": score_by_level,
        },
        "errors": errors,
        "latency_ms_avg": sum(r["pred"]["latency_ms"] for r in rows) / n,
        "sample_count": n,
    }


def render_markdown(meta: dict, s: dict) -> str:
    lines: list[str] = []
    a = lines.append
    label = Path(meta["model_dir"]).name if meta.get("model_dir") else meta["provider"]
    a(f"# 评估集回放报告（{label}）")
    a("")
    a(f"- 时间：{meta['generated_at']}")
    a(f"- 模式：{meta['mode']}（provider：{meta['provider']}）")
    a(f"- 样本：{s['sample_count']} 条独立评估集（eval_dataset.jsonl，与训练集零重叠）")
    a(f"- 平均延迟：{s['latency_ms_avg']:.0f} ms/条")
    a("")
    a("## 三原语指标")
    a("")
    a("| 原语 | 指标 | 数值 |")
    a("| --- | --- | --- |")
    ch = s["choice"]
    a(f"| Choice | top-1 准确率 | **{ch['accuracy']:.1%}** |")
    if ch["conf_pass_accuracy"] is not None:
        a(f"| Choice | 置信度 ≥60% 子集准确率（覆盖率 {ch['conf_pass_coverage']:.1%}） | {ch['conf_pass_accuracy']:.1%} |")
    no = s["noul"]
    a(f"| Noul | 区间准确率（阈值 {NOUL_ACTIONABLE_MIN:.2f}） | **{no['interval_accuracy']:.1%}** |")
    a(f"| Noul | 覆盖率（判为可处理比例） | {no['coverage']:.1%} |")
    if no["interval_accuracy_when_passed"] is not None:
        a(f"| Noul | 通过区间内准确率 | {no['interval_accuracy_when_passed']:.1%} |")
    if no["mean_prob_truth_actionable"] is not None and no["mean_prob_truth_insufficient"] is not None:
        a(f"| Noul | 真值可处理 / 不可处理的平均概率 | {no['mean_prob_truth_actionable']:.3f} / {no['mean_prob_truth_insufficient']:.3f} |")
    sc = s["score"]
    a(f"| Score | 等级 exact 命中 | **{sc['exact_accuracy']:.1%}** |")
    a(f"| Score | 等级 ±1 容差命中 | {sc['within1_accuracy']:.1%} |")
    a(f"| Score | 与真值等级的 MAE | {sc['mae']:.2f} |")
    rel = s.get("reliability") or {}
    if rel:
        ch_r = rel["choice"]
        no_r = rel["noul"]
        a(f"| Choice | ECE（{rel['bins_count']} 等宽桶） | **{ch_r['ece']:.4f}** |")
        a(f"| Choice | 多类 Brier | {ch_r['brier']:.4f} |")
        a(f"| Noul | ECE（{rel['bins_count']} 等宽桶） | **{no_r['ece']:.4f}** |")
        a(f"| Noul | Brier | {no_r['brier']:.4f} |")
    a("")
    a("## Choice 混淆矩阵（行=真值，列=预测）")
    a("")
    a("| 真值 \\ 预测 | " + " | ".join(CATEGORIES) + " |")
    a("| --- | " + " | ".join("---" for _ in CATEGORIES) + " |")
    for truth_cat in CATEGORIES:
        a(f"| {truth_cat} | " + " | ".join(str(confusion_cell) for confusion_cell in s["choice"]["confusion"][truth_cat].values()) + " |")
    a("")
    a(f"## 错误样本（{len(s['errors'])} 条）")
    a("")
    if s["errors"]:
        a("| id | 消息 | 真值→预测(类别) | 置信度 | noul 判定 | Score 真值→预测 |")
        a("| --- | --- | --- | --- | --- | --- |")
        for e in s["errors"]:
            a(
                f"| {e['id']} | {e['text']} | {e['truth_category']}→{e['pred_category']} "
                f"| {e['confidence']:.2f} | {'✓' if e['noul_ok'] else '✗'}({e['noul']:.2f}) "
                f"| {e['truth_impact']}→{e['pred_impact']} |"
            )
    else:
        a("无——choice / noul / score(±1) 全部命中。")
    a("")

    if rel:
        a(f"## 校准可靠性（{rel['bins_count']} 等宽桶）")
        a("")
        a("可靠性分桶：模型输出概率（x）与实际频率（y）越对齐 ECE 越小，")
        a("对角线为完美校准；置信度门槛建立在该概率语义之上。")
        a("")
        a("### Choice（top-1 概率 vs 实际正确率）")
        a("")
        a("| 概率区间 | n | 平均置信度 | 实际正确率 | 差距(acc−conf) |")
        a("| --- | --- | --- | --- | --- |")
        for b in rel["choice"]["bins"]:
            if b["n"] > 0:
                gap = b["accuracy"] - b["avg_confidence"]
                a(f"| {b['range'][0]:.1f}–{b['range'][1]:.1f} | {b['n']} | {b['avg_confidence']:.3f} | {b['accuracy']:.3f} | {gap:+.3f} |")
        a("")
        a("### Noul（可处理概率 vs 实际可处理率）")
        a("")
        a("| 概率区间 | n | 平均概率 | 实际可处理率 | 差距 |")
        a("| --- | --- | --- | --- | --- |")
        for b in rel["noul"]["bins"]:
            if b["n"] > 0:
                gap = b["accuracy"] - b["avg_confidence"]
                a(f"| {b['range'][0]:.1f}–{b['range'][1]:.1f} | {b['n']} | {b['avg_confidence']:.3f} | {b['accuracy']:.3f} | {gap:+.3f} |")
        a("")
        if rel.get("score_by_pred_level"):
            a("### Score（按预测等级分组：预测均值 vs 实际等级均值）")
            a("")
            a("| 预测等级 | n | 预测均值 | 实际均值 | MAE |")
            a("| --- | --- | --- | --- | --- |")
            for b in rel["score_by_pred_level"]:
                a(f"| {b['pred_level']} | {b['n']} | {b['mean_pred']:.2f} | {b['mean_truth']:.2f} | {b['mae']:.2f} |")
            a("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="评估集回放")
    parser.add_argument("--mode", choices=["http", "local"], default=None, help="默认自动：服务可达则 http")
    parser.add_argument("--local", action="store_true", help="等价于 --mode=local")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    mode = args.mode or ("local" if args.local else "http")
    samples = load_samples()

    if mode == "http":
        provider_name = check_http_provider(args.base)

        def decide(text: str, sid: str) -> dict:
            return decide_http(text, sid, args.base)
    else:
        import os

        os.environ.setdefault("LAYA_MODEL_DIR", args.model_dir)
        local_decide, local_provider = build_local_decider(args.model_dir)
        provider_name = f"{local_provider.name}(local)"
        decide = local_decide

    rows: list[dict] = []
    t0 = time.perf_counter()
    for i, s in enumerate(samples, 1):
        d = decide(s["text"], s["id"])
        rows.append(
            {
                "id": s["id"],
                "text": s["text"],
                "truth": s["labels"],
                "note": s.get("meta", {}).get("note", ""),
                "pred": {
                    "category": d["choice"]["category"],
                    "probabilities": d["choice"]["probabilities"],
                    "confidence": d["choice"]["confidence"],
                    "noul": d["noul"]["probability"],
                    "score": d["score"]["value"],
                    "level_index": d["score"]["levelIndex"],
                    "latency_ms": d["latencyMs"],
                },
            }
        )
        print(f"[{i}/{len(samples)}] {s['id']} {d['choice']['category']} noul={d['noul']['probability']:.2f} score={d['score']['value']:.2f}", flush=True)

    summary = evaluate(rows)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "provider": provider_name,
        "model_dir": args.model_dir if mode == "local" else None,
        "eval_dataset": "evals/eval_dataset.jsonl",
    }
    report = {"meta": meta, "summary": summary, "rows": rows}

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "eval-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "eval-report.md").write_text(render_markdown(meta, summary), encoding="utf-8")

    print(f"\n回放完成：{len(rows)} 条 / {time.perf_counter() - t0:.1f}s")
    print(f"Choice acc = {summary['choice']['accuracy']:.1%} | "
          f"Noul acc = {summary['noul']['interval_accuracy']:.1%} (cov {summary['noul']['coverage']:.1%}) | "
          f"Score exact = {summary['score']['exact_accuracy']:.1%} ±1 = {summary['score']['within1_accuracy']:.1%}")
    print(f"报告已写入 {out_dir}/eval-report.json / eval-report.md")


if __name__ == "__main__":
    main()
