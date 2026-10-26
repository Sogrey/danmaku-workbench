"""阈值扫描：在评估集回放结果上量化「自动化覆盖率 vs 误分流率」，给出双门槛的数据依据。

用法（backend 目录下，先跑 replay_eval.py 生成 eval-report.json）：
  .venv/Scripts/python.exe evals/threshold_scan.py
可选 --report 覆盖报告路径，--out 输出目录。

输出：evals/reports/threshold-scan.md（+ 控制台摘要）
口径：
  - Noul 门槛扫描：t ∈ 0.50~0.90，步长 0.05
      coverage   = P(noul >= t)                    判为可处理（可自动进待办）的比例
      interval   = P((noul>=t) == truth_actionable) 区间判定与真值一致率
      passed     = P(truth_actionable | noul >= t)  通过区间内的实际可处理率（误放行风险）
  - Choice 门槛扫描：t ∈ 0.50~0.90
      coverage   = P(top1 概率 >= t)
      passed     = P(类别正确 | top1 概率 >= t)      通过区间内的分类准确率
  - 端到端分流模拟：choice≥tc 且 noul≥tn 进对应待办，chat 不进队列，
      spam/insufficient 恒进待确认（与前端 routing.ts 规则一致）：
      auto_ok    = 正确进对队列且类别正确且真值可处理
      auto_wrong = 进了待办但类别错误（去错队列）
      auto_leak  = 真值应处理但被判到待确认/弹幕区（漏处理）
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NOUL_GRID = [round(0.50 + 0.05 * i, 2) for i in range(9)]
CHOICE_GRID = [round(0.50 + 0.05 * i, 2) for i in range(9)]


def load_rows(report_path: Path) -> list[dict]:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return data["rows"]


def ratio(part: int, total: int) -> float:
    return part / total if total else 0.0


def scan_noul(rows: list[dict]) -> list[dict]:
    n = len(rows)
    out = []
    for t in NOUL_GRID:
        passed = [r for r in rows if r["pred"]["noul"] >= t]
        ok = sum(1 for r in rows if (r["pred"]["noul"] >= t) == bool(r["truth"]["actionable"]))
        out.append({
            "threshold": t,
            "coverage": ratio(len(passed), n),
            "interval": ratio(ok, n),
            "passed_acc": ratio(sum(1 for r in passed if r["truth"]["actionable"]), len(passed)),
            "to_confirm": 1 - ratio(len(passed), n),
        })
    return out


def scan_choice(rows: list[dict]) -> list[dict]:
    n = len(rows)
    out = []
    for t in CHOICE_GRID:
        passed = [r for r in rows if r["pred"]["probabilities"][r["pred"]["category"]] >= t]
        ok = sum(1 for r in passed if r["pred"]["category"] == r["truth"]["category"])
        out.append({
            "threshold": t,
            "coverage": ratio(len(passed), n),
            "passed_acc": ratio(ok, len(passed)),
        })
    return out


def simulate_routing(rows: list[dict], tc: float, tn: float) -> dict:
    """与前端 routing.ts 一致的分流模拟，统计三种结果。"""
    n = len(rows)
    auto_ok = auto_wrong = auto_leak = confirm_ok = 0
    for r in rows:
        cat, conf = r["pred"]["category"], r["pred"]["probabilities"][r["pred"]["category"]]
        noul = r["pred"]["noul"]
        truth_ok = bool(r["truth"]["actionable"])
        correct_cat = cat == r["truth"]["category"]

        if cat == "chat":
            # 普通聊天留在弹幕区
            if r["truth"]["category"] == "chat":
                auto_ok += 1
            elif truth_ok:
                auto_leak += 1
            else:
                confirm_ok += 1
            continue

        if conf >= tc and noul >= tn:
            # 进讲师/助教待办
            if correct_cat and truth_ok:
                auto_ok += 1
            elif correct_cat:
                auto_leak += 1  # 类别对但真值不可处理 → 不该进待办（放行过度）
            else:
                auto_wrong += 1
        else:
            # 待确认
            if truth_ok and r["truth"]["category"] != "chat":
                auto_leak += 1  # 真值应处理却被拒到人工确认
            else:
                confirm_ok += 1
    return {
        "choice_min": tc,
        "noul_min": tn,
        "auto_ok": ratio(auto_ok, n),
        "auto_wrong": ratio(auto_wrong, n),
        "auto_leak": ratio(auto_leak, n),
        "confirm_ok": ratio(confirm_ok, n),
        "automation_rate": ratio(auto_ok, n),
    }


def render_markdown(rows: list[dict], noul_scan, choice_scan, sims, adopted: dict) -> str:
    n = len(rows)
    lines: list[str] = []
    w = lines.append
    w("# 阈值扫描报告（自动化覆盖率 vs 误分流率）")
    w("")
    w(f"- 样本：{n} 条独立评估集（eval-report.json rows）")
    w(f"- 当前生效门槛：choice ≥ {adopted['choice_min']:.2f} · noul ≥ {adopted['noul_min']:.2f}")
    w("- 生成工具：backend/evals/threshold_scan.py")
    w("")
    w("## Noul 门槛扫描")
    w("")
    w("| 门槛 | 覆盖率（自动进待办） | 区间判定一致率 | 通过区间实际可处理率 | 推到人工确认 |")
    w("| --- | ---: | ---: | ---: | ---: |")
    for s in noul_scan:
        mark = " **← 当前**" if abs(s["threshold"] - adopted["noul_min"]) < 1e-9 else ""
        w(f"| ≥ {s['threshold']:.2f}{mark} | {s['coverage']:.1%} | {s['interval']:.1%} | {s['passed_acc']:.1%} | {s['to_confirm']:.1%} |")
    w("")
    w("## Choice 门槛扫描（top-1 概率）")
    w("")
    w("| 门槛 | 覆盖率 | 通过区间分类准确率 |")
    w("| --- | ---: | ---: |")
    for s in choice_scan:
        mark = " **← 当前**" if abs(s["threshold"] - adopted["choice_min"]) < 1e-9 else ""
        w(f"| ≥ {s['threshold']:.2f}{mark} | {s['coverage']:.1%} | {s['passed_acc']:.1%} |")
    w("")
    w("## 端到端分流模拟（进对队列 / 进错队列 / 漏到人工）")
    w("")
    w("| choice | noul | 完全自动正确 | 进错队列 | 漏处理/错放行 | 人工确认兜底 |")
    w("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for s in sims:
        mark = " **← 当前**" if (abs(s["choice_min"] - adopted["choice_min"]) < 1e-9 and abs(s["noul_min"] - adopted["noul_min"]) < 1e-9) else ""
        w(f"| {s['choice_min']:.2f} | {s['noul_min']:.2f}{mark} | {s['auto_ok']:.1%} | {s['auto_wrong']:.1%} | {s['auto_leak']:.1%} | {s['confirm_ok']:.1%} |")
    w("")
    w("## 读法")
    w("")
    w("- 「完全自动正确」越高自动化收益越大；「进错队列」是用户体验风险（去错人）；")
    w("  「漏处理/错放行」由待确认队列人工兜底，代价是人力。")
    w("- 门槛选择 = 在三者间取业务可接受的平衡：本系统面向课堂场景，")
    w("  误进错误队列的挫败感高于人工确认成本，故保留双门槛而非全自动化。")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="阈值扫描")
    parser.add_argument("--report", default=str(Path(__file__).parent / "reports" / "eval-report.json"))
    parser.add_argument("--out", default=str(Path(__file__).parent / "reports"))
    args = parser.parse_args()

    rows = load_rows(Path(args.report))
    adopted = {"choice_min": 0.60, "noul_min": 0.60}

    noul_scan = scan_noul(rows)
    choice_scan = scan_choice(rows)

    sims = [
        simulate_routing(rows, 0.60, 0.60),  # 当前
        simulate_routing(rows, 0.60, 0.80),  # noul 更保守
        simulate_routing(rows, 0.70, 0.60),  # choice 更保守
        simulate_routing(rows, 0.50, 0.50),  # 双双放宽
        simulate_routing(rows, 0.70, 0.80),  # 双双收紧
    ]

    md = render_markdown(rows, noul_scan, choice_scan, sims, adopted)
    out_path = Path(args.out) / "threshold-scan.md"
    out_path.write_text(md, encoding="utf-8")

    cur = sims[0]
    print(f"样本 {len(rows)} 条")
    print(f"当前门槛(0.60/0.60)：完全自动 {cur['auto_ok']:.1%} | 进错队列 {cur['auto_wrong']:.1%} | 漏/错放 {cur['auto_leak']:.1%} | 人工兜底 {cur['confirm_ok']:.1%}")
    print(f"noul 0.60 → 覆盖 {noul_scan[2]['coverage']:.1%} 区间一致 {noul_scan[2]['interval']:.1%} 通过内实际 {noul_scan[2]['passed_acc']:.1%}")
    print(f"报告已写入 {out_path}")


if __name__ == "__main__":
    main()
