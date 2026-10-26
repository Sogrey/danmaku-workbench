# Laya 微调训练指南

> danmaku-workbench v0.3 · 基于实测的训练全流程文档（环境 → 数据 → 训练 → 校准 → 应用 → 调优）
>
> 正文记录 2026-10-25 首训（v0.2）实测数据，§7.5 记录 v0.3 L3 补强迭代；均为 RTX 3060 Laptop（6GB）真实训练记录，可直接复现。

---

## 1. 训练目标与原理

### 1.1 为什么必须微调

Laya 官方明确：**基础 checkpoint 是"值得特化的快底座"，不是零样本决策引擎**。零样本在 typed-decisions 基准上仅 0.362（低于 0.461 多数类基线），微调后 0.766。本项目实测同样印证：

| 弹幕样本 | 零样本输出 | 微调后输出 |
| --- | --- | --- |
| `SDK 安装一直报错 ModuleNotFoundError 装不上` | technical 0.572 ✅（有先验） | technical（正确） |
| `这个怎么弄` | **technical 0.682 ❌** | **insufficient ✅**（学会"指代无内容"边界） |
| `老师说话声音有点小` | feedback 0.428（与 technical 0.364 几乎不分） | feedback（高置信） |

### 1.2 训练什么

对 `laya-multilingual`（mmBERT-base **322M**，ModernBERT 架构 22 层 / 256k 词表 / RoPE 8k）做 **LoRA 参数高效微调**，使其掌握弹幕工作台的三个判断原语（与前端 `criteria.ts` 判据一一对应）：

| 原语 | 问题 | 目标 |
| --- | --- | --- |
| **Choice** | 这条弹幕属于哪一类？ | 五类：technical / feedback / chat / spam / insufficient |
| **Noul** | 对象和诉求是否清楚到足以开始处理？ | P(true)，自定义 true/false 描述规避官方 issue #156 标签主导 |
| **Score** | 对当前跟课的影响等级？ | 0~3 四级（稍后处理 / 正常答疑 / 优先协助 / 立即关注） |

### 1.3 训练方法要点

- **LoRA 注入**：`inject_adapter_in_model` 低级注入（非 `get_peft_model`——后者假设 HF 标准接口，与自定义 `DecisionModel` 不兼容），r=8 / α=32 / target=`Wqkv`（ModernBERT fused QKV 命名）/ dropout 0.05
- **决策头全训**：head（2 层 transformer）+ type_emb + scorer 解冻全训；act_head 无标签保持冻结
- **损失 = -proper_reward**（严格恰当评分规则：log score + spherical + score 原语的 RPS）——报告诚实概率是最大化奖励的唯一途径，**校准友好**（这正是 Laya 的 RLCD 训练目标在监督场景的等价形式）
- **选项顺序洗牌**：复用官方 `encode_record` 内置逻辑，choice/noul 训练时随机化选项顺序，消除位置偏置
- **显存三件套**：bf16 autocast + encoder 梯度检查点 + token 预算封顶（`max_tokens_per_batch`），使 6GB 消费卡可训

---

## 2. 环境准备

### 2.1 硬件要求（实测基准）

| 资源 | 最低 | 本次实测 | 说明 |
| --- | --- | --- | --- |
| GPU 显存 | **5 GB 空闲** | RTX 3060 Laptop 6GB（训练时占用 **3.7GB**） | LoRA 路线；全参微调需 >10GB，本项目不需要 |
| 内存 | **≥6 GB 空闲** | 6.3GB 空闲时启动 | 模型加载 + 编码峰值约 3GB；内存不足先关后台 |
| 磁盘 | ~10 GB | 权重 614MB + venv ~5GB + checkpoint 614MB | 建议非 C 盘（本项目放 `D:\AI\laya`） |
| GPU 架构 | Ampere+（sm_86） | RTX 3060（cc 8.6） | bf16 需要 Ampere 及以上 |

### 2.2 软件栈

| 组件 | 版本（实测） | 备注 |
| --- | --- | --- |
| Python | 3.12.13 | venv 隔离，不动全局与 GPT-SoVITS 环境 |
| torch | **2.14.1+cu126** | ⚠️ PyPI 上 Windows 默认是 CPU 版，必须走 CUDA 轮子（见下） |
| transformers | 5.20.2 | ModernBERT 架构要求 ≥5.0 |
| peft | 0.21.2 | LoRA 注入 |
| safetensors | 0.8.0 | checkpoint 读写 |
| numpy | 2.5.4 | — |

### 2.3 CUDA torch 安装（国内网络要点）

```powershell
# 标准（网络通畅时）
python -m venv backend\.venv
backend\.venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu126

# 国内网络实测：pytorch.org 约 1.4MB/s（2.6GB 需 30 分钟）且易中断。
# 应对方案（本项目实战）：
#   1) 4 段 Range 并行下载（curl -r，速度叠加至 6.8MB/s）+ 断点续传
#   2) 残缺段从阿里云镜像补齐：https://mirrors.aliyun.com/pytorch-wheels/cu126/
#   3) 合并后 pip install 本地 whl（--index-url 用阿里 PyPI 源装依赖）
# 权重/model 下载请用 ModelScope（实测 17MB/s）：
#   https://modelscope.cn/models/convaiinnovations/laya/resolve/master/multilingual/model.safetensors
```

### 2.4 基线模型资产（`D:\AI\laya` 布局）

```
D:\AI\laya\
├─ repo-laya-hf\                    # HF 仓库 ConvaiInnovations/laya（gitcode/hf-mirror 克隆，GIT_LFS_SKIP_SMUDGE=1）
│  ├─ rl_common.py                  # ★ 官方训练基建（build_sequence/encode_record/proper_reward/collate_items）
│  ├─ rl_agent_api.py               # RLAgent 推理类（system_one，Jev 兼容）
│  ├─ multilingual\                 # 微调基线 checkpoint
│  │  ├─ model.safetensors          # 614MB（ModelScope 下载）
│  │  ├─ rl_agent_config.json       # 出厂温度全 1.0、temperature_by_options 为空 ← 校准必做的原因
│  │  ├─ encoder\config.json        # mmBERT 架构配置（build_model 用）
│  │  └─ tokenizer\                 # tokenizer.json 34MB（256k 词表）
│  └─ ...
├─ danmaku-dm-v0.2\                 # v0.2 首训产物（§5 实测；保留可回退）
└─ danmaku-dm-v0.3\                 # ★ 当前引擎（L3 补强迭代产物，§7.5）
```

### 2.5 环境自检清单

```powershell
backend\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.is_bf16_supported())"
# 期望：2.14.1+cu126 True True
nvidia-smi --query-gpu=memory.free --format=csv,noheader   # ≥5000 MiB
```

---

## 3. 训练数据说明

### 3.1 标注 Schema（`seed_samples.json`）

每条样本三标签，与三原语一一对应：

```json
{
  "text": "pip install 报错了",
  "category": "technical",       // Choice：五类之一
  "actionable": true,            // Noul：对象和诉求是否清楚到足以开始处理
  "impact_level": 2,             // Score：0~3 影响等级
  "note": "边界对照样本：有具体环节，区别于'报错了'"
}
```

### 3.2 标注规则（写进 `seed_samples.json` 的 `annotation_rules`）

1. `impact_level` **只依据消息内容**，不因催促语气、感叹号、作者身份而提升（与课程 policy.py 防注入原则一致）
2. 「这个/那个/刚才」等指代若指向待处理问题对象且无具体内容 → `insufficient`
3. 视听类反馈在弹幕场景下对象天然是直播间（「字太小」= 直播画面字号），默认信息充分
4. 推广消息一律 `actionable=false`（不进入答疑/助教流程，转人工审核）
5. 课程运营类询问（如「什么时候有回放」）现有五类无专属候选，暂标 chat 并在 note 标注为「候选缺口观察样本」

### 3.3 数据构成与分布

| 数据集 | 规模 | 构成 |
| --- | --- | --- |
| 训练集 `train_dataset.jsonl` | **322 条** | 114 手工种子 + 208 标签安全变体 |
| 评估集 `eval_dataset.jsonl` | **45 条** | **独立手写，不参与变体扩充**（保证评估有效性） |

训练集分布：

```
category：technical 90 · feedback 66 · chat 63 · spam 40 · insufficient 63
impact_level：0级139 · 1级108 · 2级63 · 3级12（⚠️ 3级样本天然稀少，见 §7.1）
actionable：true 219 · false 103
```

> **v0.3 迭代后现状**（§7.5 实战案例）：训练集 379 条（133 种子 + 246 变体，3 级占 15.8%），评估集 230 条。

### 3.4 两项关键数据设计

- **成对边界对照样本（10 组）**：教会模型"指代是否具体"这条分界线，例如
  - `报错了`（insufficient）↔ `pip install 报错了`（technical）
  - `刚才你说的那里没听懂`（insufficient）↔ `刚才讲的 confidence 那段没听懂`（technical）
- **标签安全的变体扩充**：只做不改变语义的前后缀变换（称呼/礼貌语/语气词），前后缀池**按类别收敛**避免不自然组合（如 chat 不加「请问」前缀）；标签完全继承种子；`--seed 42` 可复现

### 3.5 数据再生产与校验

```powershell
python backend\training\build_dataset.py          # 重建 322+45，输出分布统计 + dataset_stats.json
```

构建器内置**标注一致性校验**（违规即拒绝生成）：类别白名单、等级 0~3、`spam/insufficient` 强制 `actionable=false`、文本唯一性。

---

## 4. 如何开始训练

### 4.1 启动命令与参数

```powershell
cd danmaku-workbench
backend\.venv\Scripts\python.exe backend\training\finetune.py --out-dir D:/AI/laya/danmaku-dm-v0.2
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--model-dir` | `D:/AI/laya/repo-laya-hf/multilingual` | 基线 checkpoint |
| `--train-jsonl / --eval-jsonl` | training/evals 目录 | 数据集 |
| `--epochs` | 12 | 小数据多轮；本次 12 轮无过拟合（最优在最后一轮） |
| `--lr` | 2e-4 | LoRA 常规学习率（社区实测稳定值） |
| `--lora-r / --lora-alpha` | 8 / 32 | α=4r，适配器初始尺度与残差相当 |
| `--max-tokens` | 4096 | 每子批 padded token 预算；**显存不足时降到 2048** |
| `--seed` | 42 | 训练全程可复现 |

### 4.2 训练流程与日志解读

```
✅ 基线加载完成：jhu-clsp/mmBERT-base（max_len=1024, head_max_len=256）
🧮 LoRA 注入完成，可训练参数：X.XXM          ← 仅 adapter + 决策头
📊 训练 322 条 / 评估 45 条
🚀 训练：12 epochs，约 N steps（warmup 10%）
[epoch 07/12] loss=-0.3398 eval_acc=0.748 choice=0.800 noul=0.867 score=0.578 ECE=0.170 elapsed=163s
[epoch 12/12] loss=-0.4080 eval_acc=0.770 choice=0.822 noul=0.867 score=0.622 ECE=0.216 elapsed=273s
   💾 新最优，已快照（raw）
✅ 训练完成：best eval_acc=0.770（epoch 12）
   💾 已 merge 22 层 LoRA → 原生键名 state_dict（169 项）
   ✅ 标准 checkpoint 已保存到 D:\AI\laya\danmaku-dm-v0.2
```

- `loss` 为负是正常的（`-proper_reward`，log score 部分为负对数似然）
- 每 epoch 结束在**独立评估集**上算整体/分原语准确率与 ECE（温度按 1.0）
- **快照机制**：训练中 best epoch 只保存 raw state_dict（含 LoRA 键），训练结束后一次性 merge——避免「中途 merge 导致 LoRA 分支失效」的陷阱

### 4.3 训练时长参考（RTX 3060 Laptop）

| 规模 | 耗时 |
| --- | --- |
| 322 样本 × 12 epochs（本项目） | **4.5 分钟**，显存 3.7GB |
| 推算：1000 样本 × 12 epochs | 约 15 分钟 |

### 4.4 训练后必做：温度校准

```powershell
backend\.venv\Scripts\python.exe backend\training\calibrate.py --model-dir D:/AI/laya/danmaku-dm-v0.2
```

**为什么必做**：multilingual 出厂温度全 1.0、分桶温度为空；微调只改权重不改校准。不校准则置信度不可信，前端 60%/65% 门槛全部失真。

---

## 5. 训练结果（本次实测）

### 5.1 指标

| 指标 | 值 | 参照 |
| --- | --- | --- |
| **eval_acc（整体）** | **0.770** | 官方 typed-decisions 微调基线 0.766 / Jev 1.13 0.727（任务不同，仅供参考） |
| choice（五分类） | 0.822 | — |
| noul（信息充分性） | 0.867 | 官方原语均值 noul 0.857 |
| score（优先级） | 0.622 | 官方原语均值 score 0.723（**最弱原语**，两者结论一致） |
| ECE（未校准） | 0.216 | 校准前的置信度不可直接使用 |

### 5.2 分桶温度（NLL 拟合，写入 checkpoint）

```
choice:3-5   T=3.0665   （压自信：五类分布过锐）
noul:2       T=3.8094
score:3-5    T=4.5357
```

温度 >1 表示压平概率——微调后模型方向判断准（77%+）但 logits 过锐，NLL 拟合让**概率输出**匹配真实频率（Guo 2017 temperature scaling 标准方法）。

### 5.3 门槛量化（校准后 45 条评估集实测）

| 门槛 | 通过率 | 区间内准确率 | 决策 |
| --- | --- | --- | --- |
| choice ≥ 0.60 | 75.6%（median 0.83） | — | ✅ 保持 |
| noul ≥ 0.65 | **55.6%** | **92%** | ✅ **采用**（前端 `THRESHOLDS.actionableProbability` 0.80→0.65） |
| noul ≥ 0.80 | 37.8% | 94% | ❌ 仅多 2% 准确率，自动化覆盖率损失 18% |

### 5.4 产物目录（`D:\AI\laya\danmaku-dm-v0.2`，不进 git）

```
model.safetensors          # merge 后权重（169 项，含 temperature buffer）
rl_agent_config.json        # 含 temperature_by_options + training 记录
calibration_report.json     # 各桶温度/NLL + ECE 前后对比
finetune_history.json       # 每 epoch loss/acc/ECE 曲线
encoder/ · tokenizer/       # 架构与分词器（自基线复制）
```

---

## 6. 应用训练结果

### 6.1 直接推理（RLAgent）

```python
import sys; sys.path.insert(0, "D:/AI/laya/repo-laya-hf")
from rl_agent_api import RLAgent

agent = RLAgent("D:/AI/laya/danmaku-dm-v0.3")   # 当前默认引擎；自动加载校准温度
result = agent.system_one(
    "老师说话声音有点小，调高一点吧",
    {"category": {"type": "choice", "instructions": "这条直播弹幕属于哪一类？",
                  "criteria": {"technical": "...", "feedback": "...", ...}},
     "actionable": {"type": "noul", "instructions": "..."},
     "priority": {"type": "score", "instructions": "...", "criteria": [四级]}})
print(result["answers"]["category"])   # choice + probabilities + confidence（已校准）
```

### 6.2 HTTP 服务（Jev 兼容）

```powershell
# 方式一：官方 laya-serve（Jev 客户端只需换 base URL）
backend\.venv\Scripts\pip.exe install "laya[serve]"
# 方式二：本项目 backend FastAPI（POST /api/decide，可同时挂 mock/jev/laya）
```

### 6.3 接入 danmaku-workbench（三步）

1. 后端 `backend/app/providers/laya.py` 补全（调 RLAgent，字段映射为前端 camelCase 契约）
2. 启动后端：`uvicorn app.main:app --port 8313`，`DECISION_PROVIDER=laya`
3. 前端 `src/decision/index.ts`：`ACTIVE_PROVIDER = 'http'` → 重启 `npm run dev`，**UI / 分流规则 / 记录逻辑零改动**

> 阈值语义提醒：校准后概率是「真实频率」。若将来重调 `THRESHOLDS`，请参照 §5.3 的方法在评估集上重算覆盖率-准确率权衡，勿拍脑袋。

---

## 7. 调优指南

### 7.1 数据侧（收益最大）

| 手段 | 说明 | 优先级 |
| --- | --- | --- |
| **补充 3 级样本** | 当前仅 12 条（断流/黑屏类天然稀少），score 弱与此相关；目标 ≥40 条或对 3 级加权 | ⭐⭐⭐ |
| 真实弹幕回流 | 系统上线后把「待确认」中被人工改判的样本回流进训练集（主动学习闭环） | ⭐⭐⭐ |
| 扩充评估集 | 45 条对温度拟合偏小（本次 noul 温度被 6 个错误样本拉高）；目标 ≥200 条 | ⭐⭐ |
| 候选缺口 | 「什么时候有回放」类运营询问暂标 chat；可考虑新增第六类「课程事务」 | ⭐ |

### 7.2 训练侧

- **epochs/早停**：12 轮时最优在末轮（未过拟合）；数据扩到 500+ 后建议 8 轮 + 观察 eval_acc 平台期
- **LoRA rank**：r=8 已承接判别任务所需低秩子空间；若数据 >2000 条仍欠拟合可试 r=16（α 同步 64）
- **target 扩展**：本次实际注入 `Wqkv`（22 层）；`o_proj` 在 ModernBERT 中命名为 `wo`，可加入 target 验证增益
- **学习率**：2e-4 稳定；仅当 loss 震荡时降到 1e-4

### 7.3 校准与阈值侧

- 温度拟合集与评估集分离；拟合集越大温度越稳（45 条是本次的妥协，扩数据后重跑 `calibrate.py`）
- 重训/数据更新后**必须重跑校准**；量化门槛决策参照 §5.3 的「覆盖率 vs 区间准确率」分析法
- `act_probability` 官方确认无信号（AUROC 0.30），**门控只用 confidence / 概率**

### 7.4 监控（上线后）

- 记录页导出 CSV/JSON → 定期计算：分原语准确率（人工标记回流后）、ECE、待确认队列占比（覆盖率漂移预警）
- ROADMAP v0.4 将内置校准曲线页与 A/B 引擎对比（mock vs laya 分歧样本分析）

### 7.5 重训迭代工作流（补样本迭代 SOP）

> 当评估回放暴露某类系统性问题（如某类准确率低、某等级零命中）时，
> 按本 SOP 完成一轮「补样本 → 重建 → 训练 → 校准 → 验证 → 采纳」，全程约 15 分钟（RTX 3060）。

**七个步骤与命令**（工作目录已标注，注意 finetune/calibrate 在项目根跑，build/replay 在 backend 跑）：

| 步 | 操作 | 命令（workdir） | 预期输出 / 判断标准 |
| --- | --- | --- | --- |
| 1 | 补训练种子 | 手工编辑 `backend/training/seed_samples.json` 的 `train_seeds`（扁平格式） | 新种子措辞不得与 `eval_samples`（230 条）重复；针对性补弱类 |
| 2 | 重建数据集 | `backend` 目录：`.venv\Scripts\python.exe training\build_dataset.py` | **评估集必须仍为 230 条且 id 顺序不变**，否则立即停止排查 |
| 3 | 训练 | 项目根：`backend\.venv\Scripts\python.exe backend\training\finetune.py --out-dir D:/AI/laya/danmaku-dm-v0.N` | **--out-dir 必须新目录**，防覆盖；eval_acc 不回退（≥上轮 -2pp） |
| 4 | 温度校准（必做） | 项目根：`backend\.venv\Scripts\python.exe backend\training\calibrate.py --model-dir D:/AI/laya/danmaku-dm-v0.N` | 三个分桶温度写入新目录 rl_agent_config.json |
| 5 | 回放验证 | `backend` 目录：`.venv\Scripts\python.exe evals\replay_eval.py --local --model-dir D:/AI/laya/danmaku-dm-v0.N` | 看 `reports/eval-report.md`：目标问题类是否修复；choice/noul 不显著回退 |
| 6 | 阈值复扫 | `backend` 目录：`.venv\Scripts\python.exe evals\threshold_scan.py` | 新概率分布下门槛是否需要调整 |
| 7 | 采纳 / 回退 | 启动服务时 `$env:LAYA_MODEL_DIR='D:/AI/laya/danmaku-dm-v0.N'` | 旧 checkpoint 原样保留，指回即回退 |

**实战案例（v0.3 = L3 补强）**：

- 背景：230 条评估集上 22 条等级 3（直播中断类）真值样本 **0 命中**（19 条判 L2）；
  归因：训练集 322 条中 L3 仅 4 种子（含变体约 12 条，占 3.7%）。
- 措施：train_seeds 追加 16 条 L3 种子（黑屏/无声/断流/音画错位等全新措辞）
  + 3 条 L2 对照（受阻可部分跟随 vs 无法接收的边界教学）；L3 占比升至约 12%。
- 判定：eval_acc ≥ 0.70（评估集已扩至 230 条，与 v0.2 首训的 0.770 非同集不直接可比）；
  回放 Score 分箱出现「3 · 立即关注」行且 mean_truth ≥ 2、choice ≥ 75%、noul ≥ 84%、Score ±1 ≥ 96%。
- 若两轮后 L3 仍零命中：种子加至 25~30 条或 `--epochs 16`。
- **实测结果（全部达标，v0.3 已采纳为默认引擎）**：best epoch 7、eval_acc 0.7667；
  L3 命中 0 → **9 条（41%）且零误报**（被判 L3 的 9 条真值全为 3，分箱 mean_truth=3.0），
  其余 12 条判 L2（不漏处理，仅排序偏低）；choice 76.5%→74.8%、Score ±1 96.1%→95.7%（均容差内微降）、
  noul 85.7%→**89.6%**（覆盖 70.4%）；ECE choice 0.059→**0.030** / noul 0.099→**0.043**；
  分桶温度 choice 2.88 / noul 1.72 / score 3.67（noul 3.81→1.72，模型显著更自信）。

**两个已踩过的坑（重训前必读）**：

1. **build 会覆盖评估集**：`build_dataset.py` 每次用 `seed_samples.json` 的 `eval_samples`
   重写 `eval_dataset.jsonl`——扩充评估集后必须把新样本同步进 `eval_samples`（2026-10-25
   已同步至 230 条），否则扩充结果会被旧数据冲掉。
2. **RoPE inv_freq 污染权重文件**：transformers/peft 升级后，`named_buffers()` 会包含
   rotary_emb 的 `*_inv_freq`，写入文件导致 strict 加载报 unexpected key
   （已在 finetune.py 保存侧过滤修复，2026-10-25）。

---

## 8. 问题排查速查

| 症状 | 原因与解法 |
| --- | --- |
| `DecisionModel.forward() got unexpected 'inputs_embeds'` | 用了 `get_peft_model(task_type=FEATURE_EXTRACTION)`；改 `inject_adapter_in_model` |
| `Missing key(s): "temperature"` | merge 保存时漏了 buffer；用 `named_buffers()` 补收集（已修复） |
| 训练中保存后模型不再更新 | 训练中 merge 导致 LoRA 分支失效；改 raw 快照 + 结束后 merge（已修复） |
| CUDA OOM | `--max-tokens 2048`；关闭其它 GPU 任务（GPT-SoVITS 等）；确认内存 ≥6GB |
| `pip install torch` 装成 CPU 版 | Windows PyPI 默认 CPU 轮子；必须 `--index-url https://download.pytorch.org/whl/cu126` |
| HF/镜像下载慢 | LFS 走 hf-mirror 会失败（CDN 域名解析问题）；用 ModelScope resolve 直链（17MB/s） |
| noul 输出恒偏一侧 | 官方 issue #156；本项目已用自定义 true/false 描述缓解，仍异常则改写为 2-option choice |
| `Unexpected key(s): ...rotary_emb...inv_freq` | transformers/peft 升级后 inv_freq 进 named_buffers 被写入文件；finetune.py 保存侧已过滤（2026-10-25），存量脏文件用 safetensors load→过滤 inv_freq→save 清洗 |

---

## 附：训练相关文件清单

| 文件 | 职责 |
| --- | --- |
| `backend/training/seed_samples.json` | 标注种子层（train_seeds + eval_samples 手工样本与标注规则，单一数据源） |
| `backend/training/build_dataset.py` | 数据构建：一致性校验 + 变体扩充 + 分割 + 统计 |
| `backend/training/finetune.py` | LoRA 微调：注入/损失/批处理/快照/merge 保存 |
| `backend/training/calibrate.py` | 分桶温度拟合（golden-section NLL）+ ECE 对比 + 写回 |
| `backend/training/requirements.txt` | 训练栈版本记录 |
| `backend/training/train_dataset.jsonl` | 训练集（首训 322 条 → v0.3 重建 379 条） |
| `backend/evals/eval_dataset.jsonl` | 独立评估集（首训 45 条 → 现 230 条） |
| `D:/AI/laya/repo-laya-hf/rl_common.py` | 官方训练基建（只读复用，勿改） |
| `D:/AI/laya/danmaku-dm-v0.2/` | v0.2 首训 checkpoint（模型资产，不进 git，保留可回退） |
| `D:/AI/laya/danmaku-dm-v0.3/` | ★ 当前引擎 checkpoint（v0.3 L3 补强；模型资产，不进 git） |

> AI生成
