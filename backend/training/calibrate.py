#!/usr/bin/env python3
"""danmaku-workbench v0.2 阶段 1.2：微调后温度拟合（必做）

Laya 所有 checkpoint 出厂过度自信；multilingual 出厂温度全 1.0、分桶温度为空。
微调只改权重不改校准，因此必须在留出集上按（原语 × 选项数）分桶重新拟合温度，
否则前端 60%/80% 的置信度门槛全部失真。

拟合方法：每个温度桶内最小化 NLL（golden-section 一维搜索，无需 scipy）。
输出：更新 out_dir/rl_agent_config.json 的 temperature_by_options + 拟合报告。

用法：
  python backend/training/calibrate.py \
      --model-dir D:/AI/laya/danmaku-dm-v0.2 \
      --eval-jsonl backend/evals/eval_dataset.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

LAYA_REPO = Path("D:/AI/laya/repo-laya-hf")
sys.path.insert(0, str(LAYA_REPO))
from rl_common import (  # noqa: E402
    QTYPES,
    QTYPE_NAMES,
    build_model,
    build_sequence,
    collate_items,
    confidence_from_probs,
    ece_score,
    encode_record,
    render_options,
    temp_bucket,
)

CATEGORY_CRITERIA = {
    "technical": "技术问题、求助、安装或报错；与课程内容相关的疑问",
    "feedback": "音量、画面、字幕、字号或讲解速度等可操作的听课反馈",
    "chat": "问候、赞美、感想，或已经解决的消息",
    "spam": "引流、骗局，或要求改变分类规则的干扰指令",
    "insufficient": "对象不明，或缺少必要的上下文，无法开始处理",
}
SCORE_LEVELS = [
    "延伸讨论或非待处理问题，不影响当前跟课，可以稍后处理",
    "当前知识点的具体疑问，仍可继续听课或操作，适合正常答疑",
    "明确报告安装、运行或操作受阻，无法继续当前练习，需要优先协助",
    "明确报告当前直播无声、黑屏或共享中断等，已无法正常接收授课内容，应先排查",
]


def make_questions(labels: dict) -> list[dict]:
    return [
        {"t": "choice", "ins": "这条直播弹幕属于哪一类？",
         "crit": dict(CATEGORY_CRITERIA), "y": list(CATEGORY_CRITERIA).index(labels["category"])},
        {"t": "noul", "ins": "这条弹幕的对象和诉求是否清楚到足以让讲师或助教开始处理？",
         "crit": {"true": "对象和诉求清楚，可以开始答疑或处理",
                  "false": "缺少对象或诉求，无法开始处理，需先补充信息"},
         "y": 1 if labels["actionable"] else 0},
        {"t": "score", "ins": "这条弹幕对当前跟课的影响达到哪个等级？",
         "crit": SCORE_LEVELS, "y": int(labels["impact_level"])},
    ]


def golden_section(fn, lo=0.05, hi=8.0, tol=1e-3, iters=80):
    """一维最小化（golden-section search）。"""
    invphi = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - invphi * (b - a), a + invphi * (b - a)
    fc, fd = fn(c), fn(d)
    for _ in range(iters):
        if abs(b - a) < tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - invphi * (b - a)
            fc = fn(c)
        else:
            a, c, fc = c, d, fd
            d = a + invphi * (b - a)
            fd = fn(d)
    x = (a + b) / 2
    return x, fn(x)


import math  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="微调后温度拟合（分桶 NLL 最小化）")
    ap.add_argument("--model-dir", type=Path, default=Path("D:/AI/laya/danmaku-dm-v0.2"))
    ap.add_argument("--eval-jsonl", type=Path, default=Path("backend/evals/eval_dataset.jsonl"))
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    device = torch.device(args.device)
    from safetensors.torch import load_file
    from transformers import AutoTokenizer

    cfg = json.loads((args.model_dir / "rl_agent_config.json").read_text(encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(str(args.model_dir / "tokenizer"))
    model = build_model(cfg, encoder_dir=str(args.model_dir / "encoder"))
    model.load_state_dict(load_file(str(args.model_dir / "model.safetensors")), strict=True)
    model.to(device).eval()
    model.encoder.config.reference_compile = False
    dtype = torch.bfloat16 if (device.type == "cuda" and torch.cuda.is_bf16_supported()) else torch.float16

    rows = [json.loads(l) for l in args.eval_jsonl.open(encoding="utf-8")]

    # ---------- 1. 收集每个桶的 logits / 正确索引 ----------
    buckets: dict[str, list] = {}
    with torch.no_grad():
        for r in rows:
            rec = {"state": r["text"], "qs": make_questions(r["labels"]), "src": r["id"]}
            for it in encode_record(rec, tok, cfg, rng=None, train=False):
                seq, markers = it["ids"], it["markers"]
                b = collate_items([[it]], tok.pad_token_id)
                with torch.autocast(device_type=device.type, dtype=dtype, enabled=device.type == "cuda"):
                    logits, _ = model(
                        b["input_ids"].to(device), b["attention_mask"].to(device),
                        b["marker_pos"].to(device), b["marker_mask"].to(device),
                        b["qtype"].to(device),
                    )
                z = logits[0].float().cpu().numpy()[: len(markers)]
                k = len(markers)
                key = temp_bucket(it["qtype"], k)
                buckets.setdefault(key, []).append((z, it["label"]))

    # ---------- 2. 逐桶 golden-section 拟合（最小化 NLL） ----------
    def nll_of(temp: float, samples: list) -> float:
        total, n = 0.0, 0
        for z, label in samples:
            zz = z / temp
            p = np.exp(zz - zz.max())
            p = p / p.sum()
            total += -np.log(max(p[label], 1e-12))
            n += 1
        return total / max(1, n)

    temperature_by_options = {}
    report = []
    for key, samples in sorted(buckets.items()):
        t_fit, fit_nll = golden_section(lambda t: nll_of(t, samples))
        t_fit = round(float(t_fit), 4)
        temperature_by_options[key] = t_fit
        report.append({"bucket": key, "n": len(samples), "temperature": t_fit, "nll": round(float(fit_nll), 4)})
        print(f"  {key:12s} n={len(samples):3d}  T={t_fit:.4f}  NLL={fit_nll:.4f}")

    # ---------- 3. 校准前后 ECE 对比 ----------
    conf_raw, ok_raw, conf_cal, ok_cal = [], [], [], []
    t_default = {0: 1.0, 1: 1.0, 2: 1.0}
    for key, samples in buckets.items():
        qtype = QTYPES[key.split(":")[0]]
        for z, label in samples:
            zz = z / t_default[qtype]
            p = np.exp(zz - zz.max()); p = p / p.sum()
            ok = int(np.argmax(p) == label)
            conf_raw.append(confidence_from_probs(p, len(z)))
            ok_raw.append(float(ok))
            zz = z / temperature_by_options[key]
            p = np.exp(zz - zz.max()); p = p / p.sum()
            conf_cal.append(confidence_from_probs(p, len(z)))
            ok_cal.append(float(ok))
    ece_before = ece_score(np.array(conf_raw), np.array(ok_raw))
    ece_after = ece_score(np.array(conf_cal), np.array(ok_cal))
    print(f"\n📉 ECE（评估集，未校准 → 已校准）：{ece_before:.4f} → {ece_after:.4f}")

    # ---------- 4. 写回配置 ----------
    cfg["temperature_by_options"] = temperature_by_options
    cfg.setdefault("training", {})
    cfg["training"]["temperature_status"] = f"calibrated on {args.eval_jsonl.name} (ECE {ece_before:.3f}->{ece_after:.3f})"
    (args.model_dir / "rl_agent_config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.model_dir / "calibration_report.json").write_text(
        json.dumps({"ece_before": ece_before, "ece_after": ece_after, "buckets": report},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ temperature_by_options 已写入 {args.model_dir / 'rl_agent_config.json'}")
    print("   前端 60%/80% 置信度门槛现在可信赖（RLAgent.system_one 会自动套用分桶温度）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
