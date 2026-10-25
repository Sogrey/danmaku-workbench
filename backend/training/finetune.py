#!/usr/bin/env python3
"""danmaku-workbench v0.2 阶段 1.2：Laya multilingual LoRA 微调脚本

在 6GB 显存（RTX 3060 Laptop）约束下，对 laya-multilingual（mmBERT-base 322M）
做 LoRA 微调，使其学会弹幕工作台的三原语判据：

  - category  (choice) 五类：技术提问/听课反馈/普通聊天/推广干扰/信息不足
  - actionable(noul)   信息是否足够开始处理（true/false 描述自定义，规避 issue #156 标签主导）
  - priority  (score)  对当前跟课的影响 0~3 四级

技术要点（对应调研结论与本机硬件）：
  1. LoRA r=8 / alpha=32 / target=Wqkv,o_proj（ModernBERT fused 命名）/ lr=2e-4
     —— 社区实测稳定配置；决策头（head/type_emb/scorer）全训，act_head 无标签冻结。
  2. 损失 = -proper_reward（log score + spherical + score 原语的 RPS），
     严格恰当评分规则：报告诚实概率是最大化奖励的唯一途径（校准友好）。
  3. bf16 autocast + encoder gradient checkpointing + token 预算封顶（max_tokens_per_batch）
     —— 3060 6GB 可行三件套；选项顺序在训练时随机洗牌（官方 encode_record 内置）。
  4. 训练完成后 LoRA merge 回主干，保存为 RLAgent 可直接加载的 checkpoint 目录。
  5. 微调后必须跑 calibrate.py 重拟合分桶温度（multilingual 出厂温度全 1.0）。

用法（在 backend/.venv 激活后）：
  python backend/training/finetune.py \
      --model-dir D:/AI/laya/repo-laya-hf/multilingual \
      --train-jsonl backend/training/train_dataset.jsonl \
      --eval-jsonl  backend/evals/eval_dataset.jsonl \
      --out-dir D:/AI/laya/danmaku-dm-v0.2
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch

# ---------------------------------------------------------------- 官方基建（HF 仓库自带）
LAYA_REPO = Path("D:/AI/laya/repo-laya-hf")
sys.path.insert(0, str(LAYA_REPO))
from rl_common import (  # noqa: E402
    QTYPES,
    build_model,
    collate_items,
    confidence_from_probs,
    encode_record,
    ece_score,
    make_token_batches,
    proper_reward,
    seed_all,
)

# ---------------------------------------------------------------- 判据（与前端 config/criteria.ts 对齐）
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


def make_questions(row: dict) -> list[dict]:
    """一条标注样本 -> 三个 Laya 内部问题（t/ins/crit + 标签 y）。"""
    labels = row["labels"]
    return [
        {
            "t": "choice",
            "ins": "这条直播弹幕属于哪一类？",
            "crit": dict(CATEGORY_CRITERIA),
            "y": list(CATEGORY_CRITERIA).index(labels["category"]),
        },
        {
            "t": "noul",
            "ins": "这条弹幕的对象和诉求是否清楚到足以让讲师或助教开始处理？",
            # 自定义 true/false 描述，缓解官方 issue #156（false:/true: 标签主导）
            "crit": {
                "true": "对象和诉求清楚，可以开始答疑或处理",
                "false": "缺少对象或诉求，无法开始处理，需先补充信息",
            },
            "y": 1 if labels["actionable"] else 0,
        },
        {
            "t": "score",
            "ins": "这条弹幕对当前跟课的影响达到哪个等级？",
            "crit": SCORE_LEVELS,
            "y": int(labels["impact_level"]),
        },
    ]


def row_to_record(row: dict) -> dict:
    return {"state": row["text"], "qs": make_questions(row), "src": row["id"]}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


# ---------------------------------------------------------------- 评估
@torch.no_grad()
def evaluate(model, tok, cfg, records, device, dtype, max_tokens=16384):
    """返回 (总体acc, 分原语acc, ece, 详情列表)——温度按 1.0（未校准）。"""
    model.eval()
    items, meta = [], []
    for rec in records:
        for it in encode_record(rec, tok, cfg, rng=None, train=False):
            items.append(it)
            meta.append(it)
    from rl_common import predict_items

    preds = predict_items(model, items, pad_id=tok.pad_token_id, device=device,
                          max_tokens=max_tokens, dtype=dtype, progress="")
    correct_all, conf_all = [], []
    per_type = {"choice": [0, 0], "noul": [0, 0], "score": [0, 0]}
    details = []
    for it, pr in zip(items, preds):
        k = len(it["markers"])
        z = pr["logits"][:k]
        p = np.exp(z - z.max())
        p = p / p.sum()
        qtype_name = {0: "choice", 1: "score", 2: "noul"}[it["qtype"]]
        if qtype_name == "score":
            exp = float((np.arange(k) * p).sum())
            ok = round(exp) == it["label"]
        else:
            ok = int(p.argmax()) == it["label"]
        per_type[qtype_name][0] += int(ok)
        per_type[qtype_name][1] += 1
        correct_all.append(float(ok))
        conf_all.append(confidence_from_probs(p, k))
        details.append({"src": it["src"], "qtype": qtype_name, "ok": bool(ok),
                        "p": [round(float(x), 4) for x in p], "label": it["label"]})
    acc = float(np.mean(correct_all)) if correct_all else float("nan")
    ece = ece_score(np.array(conf_all), np.array(correct_all)) if correct_all else float("nan")
    per = {t: (c / n if n else float("nan")) for t, (c, n) in per_type.items()}
    model.train()
    return acc, per, ece, details


# ---------------------------------------------------------------- 训练
def main() -> int:
    ap = argparse.ArgumentParser(description="Laya multilingual LoRA 微调（弹幕五类判据）")
    ap.add_argument("--model-dir", type=Path, default=Path("D:/AI/laya/repo-laya-hf/multilingual"))
    ap.add_argument("--train-jsonl", type=Path, default=Path("backend/training/train_dataset.jsonl"))
    ap.add_argument("--eval-jsonl", type=Path, default=Path("backend/evals/eval_dataset.jsonl"))
    ap.add_argument("--out-dir", type=Path, default=Path("D:/AI/laya/danmaku-dm-v0.2"))
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--max-tokens", type=int, default=4096, help="每子批 padded token 预算（3060 6GB 建议 4096）")
    ap.add_argument("--warmup-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    seed_all(args.seed)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        print("❌ CUDA 不可用：请确认 venv 内已安装 CUDA 版 torch（pip show torch 查看 +cu126 标记）")
        return 1

    from safetensors.torch import load_file
    from transformers import AutoTokenizer

    # ---------- 1. 加载基线模型（multilingual checkpoint） ----------
    cfg = json.loads((args.model_dir / "rl_agent_config.json").read_text(encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(str(args.model_dir / "tokenizer"))
    model = build_model(cfg, encoder_dir=str(args.model_dir / "encoder"))
    state = load_file(str(args.model_dir / "model.safetensors"))
    missing, unexpected = model.load_state_dict(state, strict=False)
    if unexpected:
        print(f"⚠️ 未预期的键: {unexpected}")
    if missing:
        print(f"⚠️ 缺失的键: {missing}")
    model.to(device)
    print(f"✅ 基线加载完成：{cfg['encoder']}（max_len={cfg['max_len']}, head_max_len={cfg['head_max_len']}）")

    # ---------- 2. 注入 LoRA（低级 inject，不创建 PeftModel wrapper，兼容自定义 DecisionModel） ----------
    from peft import LoraConfig, inject_adapter_in_model

    lora_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        target_modules=["Wqkv", "o_proj"],  # ModernBERT fused 命名
    )
    inject_adapter_in_model(lora_cfg, model)

    # LoRA adapter 可训练，主干冻结；决策头（head/type_emb/scorer）解冻全训，act_head 无标签保持冻结
    for name, p in model.named_parameters():
        p.requires_grad_("lora_" in name)
    for name, p in model.named_parameters():
        if ("head." in name or "type_emb" in name or "scorer" in name) and "act_head" not in name:
            p.requires_grad_(True)

    params = [p for p in model.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    print(f"🧮 LoRA 注入完成，可训练参数：{n_train / 1e6:.2f}M")

    # encoder 梯度检查点（省激活显存）
    if hasattr(model.encoder, "gradient_checkpointing_enable"):
        model.encoder.gradient_checkpointing_enable()
        model.encoder.config.use_cache = False
    # 决策头自身的检查点开关（rl_common 内置）
    model.head_checkpointing = True

    # ---------- 3. 数据 ----------
    train_rows = load_jsonl(args.train_jsonl)
    eval_rows = load_jsonl(args.eval_jsonl)
    train_records = [row_to_record(r) for r in train_rows]
    eval_records = [row_to_record(r) for r in eval_rows]
    print(f"📊 训练 {len(train_records)} 条 / 评估 {len(eval_records)} 条")

    rng = random.Random(args.seed)
    np_rng = np.random.RandomState(args.seed)
    encoded = {}  # rec_idx -> items（encode 一次，逐 epoch 复用；顺序洗牌在 encode 内部完成）

    def enc_items(rec_idx: int, train: bool):
        if rec_idx not in encoded:
            encoded[rec_idx] = encode_record(
                train_records[rec_idx], tok, cfg,
                rng=random.Random(args.seed * 1000 + rec_idx) if train else None,
                train=train,
            )
        return encoded[rec_idx]

    # token 长度统计（用于分桶批处理）
    lengths, nseq = [], []
    for i in range(len(train_records)):
        items = enc_items(i, train=True)
        lengths.append(max((len(it["ids"]) for it in items), default=0))
        nseq.append(len(items))

    # ---------- 4. 优化器 ----------
    params = [p for p in model.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    print(f"🧮 可训练参数：{n_train / 1e6:.2f}M")
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)

    steps_per_epoch = math.ceil(len(train_records) / max(1, args.max_tokens // max(lengths)))  # 粗估
    total_steps = args.epochs * max(1, steps_per_epoch)
    warmup = max(4, int(args.warmup_frac * total_steps))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt,
        lambda s: s / warmup if s < warmup else max(0.05, 1.0 - (s - warmup) / max(1, total_steps - warmup)),
    )
    print(f"🚀 训练：{args.epochs} epochs，约 {total_steps} steps（warmup {warmup}）")

    dtype = torch.bfloat16 if (device.type == "cuda" and torch.cuda.is_bf16_supported()) else torch.float16
    print(f"   AMP dtype: {dtype}")

    # ---------- 5. 训练循环 ----------
    best_acc, best_epoch, t0 = -1.0, 0, time.time()
    history = []
    for epoch in range(1, args.epochs + 1):
        batches = make_token_batches(np.array(lengths), np.array(nseq),
                                     max_tokens=args.max_tokens, max_seqs=64, rng=np_rng)
        model.train()
        ep_loss, n_updates = 0.0, 0
        for batch in batches:
            # 每批重新 encode（选项顺序随 rng 洗牌），组内 items 保持在一起
            groups = []
            for rec_idx in batch:
                items = encode_record(train_records[rec_idx], tok, cfg,
                                     rng=random.Random(rng.random()), train=True)
                if items:
                    groups.append(items)
            if not groups:
                continue
            # pack_groups 控制子批不超过 token 预算
            from rl_common import pack_groups

            for sub in pack_groups(groups, args.max_tokens, 64):
                b = collate_items(sub, tok.pad_token_id)
                if b is None:
                    continue
                input_ids = b["input_ids"].to(device)
                attn = b["attention_mask"].to(device)
                mpos = b["marker_pos"].to(device)
                mmask = b["marker_mask"].to(device)
                qtype = b["qtype"].to(device)
                target = b["target"].to(device)
                with torch.autocast(device_type=device.type, dtype=dtype, enabled=device.type == "cuda"):
                    logits, _ = model(input_ids, attn, mpos, mmask, qtype)
                    q = torch.softmax(logits.float(), dim=-1)
                    reward = proper_reward(q, target.float(), qtype, mmask)
                    loss = -reward.mean()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                ep_loss += loss.item()
                n_updates += 1

        # ---------- epoch 评估 ----------
        acc, per, ece, _ = evaluate(model, tok, cfg, eval_records, device, dtype)
        history.append({"epoch": epoch, "loss": ep_loss / max(1, n_updates),
                        "eval_acc": acc, "eval_ece": ece, "per_type": per})
        print(f"[epoch {epoch:02d}/{args.epochs}] loss={ep_loss / max(1, n_updates):.4f} "
              f"eval_acc={acc:.3f} choice={per['choice']:.3f} noul={per['noul']:.3f} "
              f"score={per['score']:.3f} ECE={ece:.3f} elapsed={time.time() - t0:.0f}s")
        if acc > best_acc:
            best_acc = acc
            best_epoch = epoch
            args.out_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), args.out_dir / "best_raw.pth")
            print("   💾 新最优，已快照（raw）")

    # ---------- 6. 训练结束：加载最优快照 -> merge LoRA -> 保存标准 checkpoint ----------
    print(f"\n✅ 训练完成：best eval_acc={best_acc:.3f}（epoch {best_epoch}）")
    if (args.out_dir / "best_raw.pth").exists():
        model.load_state_dict(torch.load(args.out_dir / "best_raw.pth", weights_only=True))
    finalize_checkpoint(model, cfg, args, best_epoch, best_acc, history)
    (args.out_dir / "best_raw.pth").unlink(missing_ok=True)
    print("▶️ 下一步：python backend/training/calibrate.py 重拟合分桶温度（必做）")
    return 0


def merged_native_state_dict(model) -> dict:
    """merge LoRA 后输出「原生键名」的 state_dict（RLAgent 可直接加载）。

    peft inject 后键名带 base_layer/lora_A 前缀，且 merge 仅改变数值不改结构；
    这里逐层取 base_layer 合并权重，重构原生键名。
    """
    try:
        from peft.tuners.lora.layer import Linear as LoraLinear
    except ImportError:
        from peft.tuners.lora import Linear as LoraLinear

    sd = {}
    lora_prefixes = []
    n_merged = 0
    for name, m in model.named_modules():
        if isinstance(m, LoraLinear):
            m.merge()
            n_merged += 1
            lora_prefixes.append(name + ".")
            sd[name + ".weight"] = m.base_layer.weight.detach().cpu().clone()
            if getattr(m.base_layer, "bias", None) is not None:
                sd[name + ".bias"] = m.base_layer.bias.detach().cpu().clone()
    for name, p in model.named_parameters():
        if any(name.startswith(pre) for pre in lora_prefixes):
            continue
        sd[name] = p.detach().cpu().clone()
    # buffers（如 temperature）不在 named_parameters 中，需单独收集
    for name, buf in model.named_buffers():
        if any(name.startswith(pre) for pre in lora_prefixes):
            continue
        sd[name] = buf.detach().cpu().clone()
    print(f"   💾 已 merge {n_merged} 层 LoRA → 原生键名 state_dict（{len(sd)} 项）")
    return sd


def finalize_checkpoint(model, cfg, args, best_epoch: int, best_acc: float, history):
    """保存 RLAgent 可加载的完整 checkpoint 目录。"""
    from safetensors.torch import save_file

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    save_file(merged_native_state_dict(model), str(out_dir / "model.safetensors"))
    new_cfg = dict(cfg)
    new_cfg["training"] = {
        "updates": int(best_epoch),
        "epochs_completed": best_epoch,
        "hours": 0.0,
        "world_size": 1,
        "fine_tuned_from_checkpoint": True,
        "base": "convaiinnovations/laya/multilingual",
        "task": "danmaku-workbench five-category triage",
        "lora": {"r": args.lora_r, "alpha": args.lora_alpha, "target": ["Wqkv", "o_proj"]},
        "best_eval_acc": round(best_acc, 4),
        "temperature_status": "PENDING calibrate.py",
    }
    (out_dir / "rl_agent_config.json").write_text(
        json.dumps(new_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (out_dir / "encoder").exists():
        shutil.copytree(args.model_dir / "encoder", out_dir / "encoder")
    if not (out_dir / "tokenizer").exists():
        shutil.copytree(args.model_dir / "tokenizer", out_dir / "tokenizer")
    (out_dir / "finetune_history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✅ 标准 checkpoint 已保存到 {out_dir}")


if __name__ == "__main__":
    sys.exit(main())
