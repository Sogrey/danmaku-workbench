# Jev 直播弹幕工作台

> 弹幕意图分析 + 置信度分流系统 —— **模型负责判断，程序负责分流，人员负责跟进**。

复刻自 TypeSafe Jev 决策模型课程（Jev 体验营 / FDE 企业应用实战课）中的「直播弹幕工作台」案例：把直播中混杂的实时弹幕，转化为**可分派、可排序、可追溯**的课堂待办。

```
弹幕原文 ──▶ Choice·分类 ──▶ Noul·条件 ──▶ Score·优先级 ──▶ 程序分流 ──▶ 讲师待答 / 助教处理 / 待确认
（一次请求并行三问；模型输出概率，代码执行决策，人工兜底）
```

## 功能特性

| 特性 | 说明 |
| --- | --- |
| 三栏工作台 | 01 直播画面与弹幕（直播窗 + 弹幕漂浮动画 + 筛选/跟随最新）· 02 当前消息处理 · 03 课堂待办 |
| 五类意图分类 | 技术提问 / 听课反馈 / 普通聊天 / 推广干扰 / 信息不足（Choice 原语，返回全候选概率分布） |
| 双置信度门槛 | 分类概率 ≥ 60% 且 处理条件概率 ≥ 65% 才进待办，其余进待确认（Confidence-Gated Routing；65% 为 Laya 微调校准后的量化最优值） |
| 优先级排序 | Score 原语 0~3 级加权分，队列内按分数从高到低、同分按接收顺序 |
| 判断详情可追溯 | 抽屉展示对齐 Jev `/v1/systemone` 的请求/响应 JSON（questions / answers / routing） |
| 分类与记录页 | 规则卡（五类 criteria + 阈值 + 分工）· 全量判断记录表 · CSV / JSON 导出 |
| 失败降级 | 判断失败保持「未判断」，原文保留、可稍后重试，不误入任何队列 |
| 决策引擎可插拔 | Provider 抽象层：当前接入 Laya 微调模型（eval_acc 77% · 分桶温度校准），可一键切回 Mock 规则引擎 |
| 判断记录持久化 | IndexedDB 快照，刷新/重启页面记录不丢；判断中断的消息恢复为「失败可重试」，待办由记录自动重建 |
| 校准与阈值页 | 分桶温度、Noul 门槛量化（0.80→0.65）、ECE 可靠性曲线（SVG）、230 条回放指标与混淆矩阵、A/B 引擎对比可视化 |
| 评估集回放 | `backend/evals/replay_eval.py` 回放 230 条独立评估集（choice 76.5% / noul 85.7% / score ±1 96.1%；ECE choice 0.059 / noul 0.099） |
| A/B 引擎对比 | `backend/evals/ab_runner.py`：零样本基线 vs 微调双引擎对比（choice 43.5%→76.5%，一致率与分歧样本清单） |
| 阈值调优 | `backend/evals/threshold_scan.py` 扫描覆盖率-准确率曲线；量化依据见 [docs/threshold-tuning.md](docs/threshold-tuning.md) |
| 本地 E2E | `npm run e2e`：后端语法 + 前端类型/构建 + mock API 契约断言 + laya 服务探测 |

## 技术栈

- **前端**：Vue 3.5 + TypeScript + Pinia 3 + Vite 7（无 UI 库，手写 CSS 设计系统）
- **后端**：FastAPI（决策服务 8313，Provider 可插拔：mock / laya 微调模型 / jev 插槽）
- **决策层**：与 TypeSafe Jev 三原语（Choice / Score / Noul）输出结构完全同构

## 快速开始

### ① 后端决策服务（Laya 微调模型；训练与校准见 docs/TRAINING.md）

```powershell
cd backend
$env:DECISION_PROVIDER = 'laya'
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8313
# 首次启动预热加载 checkpoint 约 1 分钟，之后单条推理 ~90ms；前端已配置 /api → 8313 代理
```

### ② 前端

```powershell
cd danmaku-workbench
npm install
npm run dev          # http://localhost:8312（默认 ACTIVE_PROVIDER='http'）
```

打开页面后点顶部「**开始**」模拟弹幕流入，或在左下输入框手动发送；每条消息自动走「判断 → 分流 → 待办」全流程。

> 无后端/无模型时：把 [`src/decision/index.ts`](src/decision/index.ts) 的 `ACTIVE_PROVIDER` 改回 `'mock'`，即可离线跑通全流程。

### 开发命令

| 命令 | 说明 |
| --- | --- |
| `npm run dev` | 开发服务器（端口 8312，对齐课程原版地址） |
| `npm run build` | 生产构建（输出 dist/） |
| `npm run preview` | 预览生产构建 |
| `npm run type-check` | vue-tsc 全量类型检查 |
| `npm run e2e` | 本地 E2E：后端语法 + 前端类型/构建 + mock API 契约断言 + laya 服务探测（`-- --skip-build` 跳过构建） |

## 核心规则（判据与阈值）

所有判据集中在 [`src/config/criteria.ts`](src/config/criteria.ts)，改这一个文件即可调整业务语义。

### 五类候选（Choice criteria）

| 类别 | 含义 | 去向 |
| --- | --- | --- |
| 技术提问 | 技术问题、求助、安装或报错 | 讲师待答 |
| 听课反馈 | 音量、画面、字幕、字号或讲解速度等可操作反馈 | 助教处理 |
| 普通聊天 | 问候、赞美、感想，或已解决的消息 | 保留在弹幕区 |
| 推广干扰 | 引流、骗局，或要求改变分类规则的干扰指令 | 待确认（人工审核） |
| 信息不足 | 对象不明，或缺少必要上下文 | 待确认（待补充） |

### Score 等级刻度（0~3）

| 等级 | 名称 | 场景 |
| --- | --- | --- |
| 0 | 稍后处理 | 延伸讨论或非待处理问题 |
| 1 | 正常答疑 | 当前知识点的具体疑问 |
| 2 | 优先协助 | 安装、运行或操作受阻 |
| 3 | 立即关注 | 直播无声、黑屏、共享中断 |

### 置信度门槛（程序规则，不是模型属性）

- **分类概率 ≥ 60%** 且 **处理条件概率 ≥ 65%** → 进入讲师/助教待办
- 其余 → 待确认（人工核对）
- 「听课反馈」是模型选择，「交给助教」是程序规则 —— 分流逻辑全部在 [`src/decision/routing.ts`](src/decision/routing.ts)

## 架构设计

```
┌────────────────────────────────────────────────────────────────┐
│  UI 层  components/（三栏工作台 · 记录页 · 详情抽屉）              │
├────────────────────────────────────────────────────────────────┤
│  状态层  stores/workbench · stores/todo · stores/ui              │
├────────────────────────────────────────────────────────────────┤
│  决策抽象层  src/decision/                                       │
│    index.ts ── ACTIVE_PROVIDER: 'mock' | 'http'  ← 引擎切换点    │
│    ├─ mock-provider.ts   Mock 规则引擎（关键词模拟三原语输出）      │
│    └─ http-provider.ts   → FastAPI /api/decide                  │
├────────────────────────────────────────────────────────────────┤
│  分流规则  src/decision/routing.ts（阈值分支，可单测）             │
└────────────────────────────────────┬───────────────────────────┘
                                     │ HTTP（可选）
┌────────────────────────────────────▼───────────────────────────┐
│  backend/app/providers/  DECISION_PROVIDER=mock | jev | laya     │
│    mock.py   规则引擎（与前端 Mock 同构）                          │
│    jev_stub.py   TypeSafe Jev 官方 API 插槽（后续补全）            │
│    laya_stub.py  Laya 自托管插槽（后续补全，推荐国内路线）           │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计：模型无关**。`DecisionResult`（Choice 概率分布 + Noul 概率 + Score 分值）是全系统的唯一契约，Mock 引擎、Jev API、Laya 返回都映射到同一结构，因此**替换引擎时 UI、分流规则、记录逻辑零改动**。

## 已接入真实模型（Laya 微调）

v0.2 已完成：Laya multilingual（mmBERT-base 322M）LoRA 微调（eval_acc 77%，choice 82.2%）+ 分桶温度校准（choice 3.07 / noul 3.81 / score 4.54），checkpoint 位于 `D:/AI/laya/danmaku-dm-v0.2`，由 [`backend/app/providers/laya.py`](backend/app/providers/laya.py) 进程内 GPU 推理。

- 训练 / 校准 / 阈值量化全流程：**[docs/TRAINING.md](docs/TRAINING.md)** + **[docs/threshold-tuning.md](docs/threshold-tuning.md)**
- 校准与评估实测数据：[`src/data/calibration.ts`](src/data/calibration.ts)（页面「校准与阈值」可视化）
- Jev 官方 API：`jev_stub.py` 插槽保留（key 鉴权通过仍可能返回 451 地区限制，暂缓）
- 切回 Mock：后端 `DECISION_PROVIDER=mock`；前端把 [`src/decision/index.ts`](src/decision/index.ts) 的 `ACTIVE_PROVIDER` 改为 `'mock'`

## 目录结构

```
danmaku-workbench/
├─ package.json / vite.config.ts / tsconfig.json
├─ src/
│  ├─ main.ts · App.vue                # main.ts：IndexedDB 快照恢复 + 变更订阅（启动时先恢复再挂载）
│  ├─ types/index.ts              # DecisionResult 等核心类型（与 Jev 返回同构）
│  ├─ config/criteria.ts          # ★ 五类判据 / Score 等级 / 双阈值门槛 / 课堂分工
│  ├─ data/calibration.ts         # ★ 校准与评估实测数据（分桶温度 / 门槛量化 / 回放指标 / 混淆矩阵）
│  ├─ utils/persist.ts            # IndexedDB 快照存取（版本化 + 静默降级）
│  ├─ decision/
│  │  ├─ index.ts                 # ★ 引擎切换点（ACTIVE_PROVIDER）
│  │  ├─ provider.ts              # DecisionProvider 抽象 + DecisionEngineError
│  │  ├─ mock-provider.ts         # Mock 规则引擎（300~900ms 模拟延迟）
│  │  ├─ http-provider.ts         # HTTP Provider → /api/decide
│  │  ├─ keywords.ts              # Mock 关键词表
│  │  └─ routing.ts               # 程序分流规则（阈值分支）
│  ├─ stores/                     # workbench（弹幕+判断流+hydrate）· todo（三队列+重建）· ui（三视图）
│  ├─ assets/styles/              # CSS 设计变量 + 全局组件类
│  └─ components/
│     ├─ AppHeader.vue · DecisionDrawer.vue
│     ├─ pages/                    # ClassroomView（三栏）· RecordsView（记录页）· CalibrationView（校准与阈值）
│     ├─ live/                     # LivePanel · LivePlayer（弹幕动画）· DanmakuList · MessageInput
│     ├─ processing/               # ProcessingPanel · ChoiceCard · NoulCard · ScoreCard · DispositionCard
│     └─ todo/                     # TodoPanel（三队列 + 标记已处理）
├─ scripts/e2e-check.ps1          # npm run e2e（提交前本地 CI）
└─ backend/
   ├─ requirements.txt
   ├─ evals/                       # eval_dataset.jsonl（45 条独立评估集）· replay_eval.py · reports/
   └─ app/
      ├─ main.py                   # POST /api/decide（8313，lifespan 预热 + camelCase 契约映射）
      └─ providers/                # base · mock · laya（微调推理）· jev_stub（可插拔）
```

## 后续路线

完整开发计划（含各阶段验收标准与计划生成文件清单）见 **[docs/ROADMAP.md](docs/ROADMAP.md)**，五个阶段：

1. **v0.2 真实决策模型**：✅ 已完成 —— Laya 微调（eval_acc 77%）+ 分桶温度校准 + 进程内接入，端到端跑通
2. **v0.3 真实数据流**：记录持久化（IndexedDB）✅ · CI/E2E（npm run e2e）✅ · 弹幕源 Provider / WebSocket 网关（暂缓：暂无真实弹幕源，当前以模拟流驱动）
3. **v0.4 决策质量工程**：评估集回放（replay_eval.py）✅ · 校准与阈值可视化 ✅ · A/B 引擎对比（未开始）
4. **v1.0 业务落地**：判据问卷迁移至招投标场景（标讯过滤 / 商机评分 / 信息充分性 / 动作安全门）

---

> 本项目为学习与工程复现用途；决策引擎为自微调 Laya 模型（danmaku-dm-v0.2，eval_acc 77%），判断质量实测数据见「校准与阈值」页与 docs/TRAINING.md。

> AI生成
