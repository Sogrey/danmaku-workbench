#!/usr/bin/env python3
"""标注集构建脚本（v0.2 阶段 1.1）

从手工种子样本 (seed_samples.json) 出发，做标签安全的表述变体扩充，
产出 Laya typed-decision 微调所需的中间格式 JSONL：

    backend/training/train_dataset.jsonl   训练集（种子 + 变体）
    backend/evals/eval_dataset.jsonl       评估集（独立手工样本，不参与变体）

标注一致性规则（校验器强制）：
  - category 必须属于五类白名单
  - impact_level 必须在 0~3
  - spam / insufficient 的 actionable 必须为 false（推广不需要处理流程；
    信息不足定义上即无法开始处理）
  - 变体只做不改变语义的前后缀变换，标签完全继承种子

用法：
    python backend/training/build_dataset.py
    python backend/training/build_dataset.py --seed 42 --variants-per-seed 2

后续对接 Laya 微调时，在本文件 to_laya_format() 中把中间格式转换为
Laya 官方 finetune 数据格式（以实际版本文档为准），数据层无需改动。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_FILE = Path(__file__).resolve().parent / "seed_samples.json"
DEFAULT_OUT_TRAIN = Path(__file__).resolve().parent / "train_dataset.jsonl"
DEFAULT_OUT_EVAL = REPO_ROOT / "backend" / "evals" / "eval_dataset.jsonl"
DEFAULT_OUT_STATS = Path(__file__).resolve().parent / "dataset_stats.json"

CATEGORIES = ["technical", "feedback", "chat", "spam", "insufficient"]

# 每条种子派生的变体数（按类别）
VARIANTS_PER_SEED: dict[str, int] = {
    "technical": 2,
    "feedback": 2,
    "chat": 2,
    "spam": 1,
    "insufficient": 2,
}

# 标签安全的前后缀池（按类别收敛，避免不自然组合）
PREFIXES: dict[str, list[str]] = {
    "default": ["老师，", "请问", "问一下，", "弱弱问一句，", "up主，"],
    "spam": [],                       # 推广不加礼貌前缀
    "chat": ["老师，", "up主，"],      # 问候/赞叹不加"请问"
    "insufficient": ["老师，", "请问", "问一下，", "弱弱问一句，"],
}
SUFFIXES: dict[str, list[str]] = {
    "default": ["谢谢", "！！", "谢谢老师", "麻烦了", "~", "，急"],
    "spam": ["速来", "限时", ""],
    "chat": ["谢谢", "！！", "谢谢老师", "~"],   # 赞叹类不加"麻烦了/，急"
    "insufficient": ["谢谢", "！！", "~", "，急"],  # 求助诉求保留急迫语气
}

# 一致性约束
ACTIONABLE_MUST_FALSE = {"spam", "insufficient"}


class ValidationError(RuntimeError):
    pass


def validate_sample(sample: dict[str, Any], idx: int, source: str) -> None:
    """校验单条样本的标注一致性。"""
    text = sample.get("text", "")
    category = sample.get("category")
    actionable = sample.get("actionable")
    level = sample.get("impact_level")

    if not isinstance(text, str) or not text.strip():
        raise ValidationError(f"[{source}#{idx}] text 为空")
    if category not in CATEGORIES:
        raise ValidationError(f"[{source}#{idx}] 非法 category: {category}")
    if not isinstance(actionable, bool):
        raise ValidationError(f"[{source}#{idx}] actionable 必须为 bool")
    if not isinstance(level, int) or level not in range(4):
        raise ValidationError(f"[{source}#{idx}] impact_level 必须为 0~3: {level}")
    if category in ACTIONABLE_MUST_FALSE and actionable:
        raise ValidationError(
            f"[{source}#{idx}] category={category} 的 actionable 必须为 false: {text!r}"
        )


def make_variants(
    base_id: str, sample: dict[str, Any], count: int, rng: random.Random
) -> list[dict[str, Any]]:
    """为单条种子生成标签安全的表述变体（标签完全继承）。

    sample 为标准化结构：{ id, text, labels: {category, actionable, impact_level}, meta }
    """
    category = sample["labels"]["category"]
    prefixes = PREFIXES.get(category, PREFIXES["default"])
    suffixes = SUFFIXES.get(category, SUFFIXES["default"])

    variants: list[dict[str, Any]] = []
    seen = {sample["text"]}
    attempts = 0
    while len(variants) < count and attempts < 20:
        attempts += 1
        prefix = rng.choice(prefixes) if prefixes else ""
        suffix = rng.choice(suffixes) if suffixes else ""
        text = f"{prefix}{sample['text']}{suffix}"
        if text in seen:
            continue
        seen.add(text)
        variants.append(
            {
                "text": text,
                "labels": {
                    "category": category,
                    "actionable": sample["labels"]["actionable"],
                    "impact_level": sample["labels"]["impact_level"],
                },
                "meta": {
                    "source": "variant",
                    "base_id": base_id,
                    "note": sample.get("meta", {}).get("note", ""),
                },
            }
        )
    return variants


def build_dataset(seed_file: Path, variant_seed: int) -> tuple[list[dict], list[dict], dict]:
    data = json.loads(seed_file.read_text(encoding="utf-8"))

    train_seeds = data["train_seeds"]
    eval_samples = data["eval_samples"]

    for i, s in enumerate(train_seeds):
        validate_sample(s, i, "train_seeds")
    for i, s in enumerate(eval_samples):
        validate_sample(s, i, "eval_samples")

    rng = random.Random(variant_seed)

    train: list[dict[str, Any]] = []
    seen_texts: set[str] = set()

    # 1) 种子样本入库
    for i, s in enumerate(train_seeds, start=1):
        if s["text"] in seen_texts:
            raise ValidationError(f"train_seeds 文本重复: {s['text']!r}")
        seen_texts.add(s["text"])
        train.append(
            {
                "id": f"dm-{i:04d}",
                "text": s["text"],
                "labels": {
                    "category": s["category"],
                    "actionable": s["actionable"],
                    "impact_level": s["impact_level"],
                },
                "meta": {"source": "seed", "note": s.get("note", "")},
            }
        )

    # 2) 变体扩充
    for entry in list(train):
        if entry["meta"]["source"] != "seed":
            continue
        n = VARIANTS_PER_SEED.get(entry["labels"]["category"], 1)
        for v in make_variants(entry["id"], entry, n, rng):
            if v["text"] in seen_texts:
                continue
            seen_texts.add(v["text"])
            train.append(
                {
                    "id": f"dm-{len(train) + 1:04d}",
                    "text": v["text"],
                    "labels": v["labels"],
                    "meta": v["meta"],
                }
            )

    # 3) 评估集（独立样本，不扩充）
    seen_eval: set[str] = set()
    evalset: list[dict[str, Any]] = []
    for s in eval_samples:
        if s["text"] in seen_eval:
            raise ValidationError(f"eval_samples 文本重复: {s['text']!r}")
        seen_eval.add(s["text"])
        evalset.append(
            {
                "id": f"ev-{len(evalset) + 1:04d}",
                "text": s["text"],
                "labels": {
                    "category": s["category"],
                    "actionable": s["actionable"],
                    "impact_level": s["impact_level"],
                },
                "meta": {"source": "eval", "note": s.get("note", "")},
            }
        )

    stats = compute_stats(train, evalset)
    return train, evalset, stats


def compute_stats(train: list[dict], evalset: list[dict]) -> dict:
    def _dist(rows: list[dict]) -> dict:
        cats = Counter(r["labels"]["category"] for r in rows)
        levels = Counter(r["labels"]["impact_level"] for r in rows)
        act = Counter(r["labels"]["actionable"] for r in rows)
        return {
            "total": len(rows),
            "category": {c: cats.get(c, 0) for c in CATEGORIES},
            "impact_level": {str(l): levels.get(l, 0) for l in range(4)},
            "actionable": {"true": act.get(True, 0), "false": act.get(False, 0)},
        }

    return {
        "train": _dist(train),
        "eval": _dist(evalset),
        "train_source": dict(Counter(r["meta"]["source"] for r in train)),
    }


def to_laya_format(samples: list[dict]) -> list[dict]:
    """中间格式 → Laya finetune 格式的转换插槽。

    TODO(v0.2 阶段 1.2)：按 Laya 官方微调文档补全字段映射。
    预期方向：state=弹幕文本，questions 含五类 choice criteria /
    noul(actionable) / score(impact_level 四级)。
    """
    raise NotImplementedError("待 1.2 阶段按 Laya 官方微调格式补全")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="构建弹幕五类判据微调标注集")
    parser.add_argument("--seed", type=int, default=42, help="变体随机种子（保证可复现）")
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_FILE)
    parser.add_argument("--out-train", type=Path, default=DEFAULT_OUT_TRAIN)
    parser.add_argument("--out-eval", type=Path, default=DEFAULT_OUT_EVAL)
    parser.add_argument("--out-stats", type=Path, default=DEFAULT_OUT_STATS)
    args = parser.parse_args()

    try:
        train, evalset, stats = build_dataset(args.seed_file, args.seed)
    except ValidationError as e:
        print(f"❌ 标注校验失败：{e}", file=sys.stderr)
        return 1

    write_jsonl(args.out_train, train)
    write_jsonl(args.out_eval, evalset)
    args.out_stats.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✅ 标注集构建完成（variant seed = {args.seed}）")
    print(f"   train → {args.out_train.relative_to(REPO_ROOT)}  {stats['train']['total']} 条")
    print(f"   eval  → {args.out_eval.relative_to(REPO_ROOT)}  {stats['eval']['total']} 条")
    print(f"   stats → {args.out_stats.relative_to(REPO_ROOT)}")
    print("\n训练集分布：")
    for cat, n in stats["train"]["category"].items():
        print(f"   {cat:14s} {n:4d}")
    print(f"   impact_level    {stats['train']['impact_level']}")
    print(f"   actionable      {stats['train']['actionable']}")
    print(f"   来源            {stats['train_source']}")
    print("\n评估集分布：")
    for cat, n in stats["eval"]["category"].items():
        print(f"   {cat:14s} {n:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
