# ROADMAP · 开发路线图

> 基于当前状态（v0.1.0）规划。每个任务标注**计划生成/修改的文件**，里程碑给出验收标准。

---

## 📍 当前状态（v0.2.1 · 2026-10-25）

| 维度 | 状态 |
| --- | --- |
| 前端三栏工作台 | ✅ 完成（直播窗弹幕动画 / Choice·Noul·Score 判断卡 / 三队列待办 / 记录页 / JSON 详情抽屉） |
| 决策引擎 | ✅ **Laya multilingual LoRA 微调版**（mmBERT 322M，eval_acc 0.770：choice 0.822 / noul 0.867 / score 0.622） |
| 校准 | ✅ 分桶温度拟合完成（choice:3-5 T=3.07 / noul:2 T=3.81 / score:3-5 T=4.54）；noul 门槛校准后量化为 65% |
| 决策抽象层 | ✅ Provider 接口 + 双门槛分流规则（60% / 65%），模型可插拔 |
| 后端 | ✅ FastAPI 决策服务接入（laya.py 进程内 GPU 推理 + 分桶校准温度；lifespan 预热 ~90ms/条；`DECISION_PROVIDER=mock\|laya\|jev`） |
| 工程化 | ✅ 判断记录 IndexedDB 持久化（刷新不丢）；npm run e2e 本地 CI；评估集回放（45 条：choice 82.2% / noul 86.7% / score ±1 97.8%）；校准与阈值可视化页 |
| 决策质量 | ✅ ECE 可靠性曲线（choice ECE 0.099 ≤ 0.1 / noul 0.117，Brier 0.068/0.126）；A/B 引擎对比（零样本 choice 44.4% → 微调 82.2%，分歧 34/45 条） |
| 质量 | ✅ vue-tsc 零错误；vite build 成功；训练 12 epochs 4.5 分钟（RTX 3060 3.7GB 显存） |
| 仓库 | ✅ 已推送 [github.com/Sogrey/danmaku-workbench](https://github.com/Sogrey/danmaku-workbench) main |
| 已知边界 | score 是最弱原语（exact 55.6% 但 ±1 容差 97.8%）；边界混淆集中在 insufficient（上下文依赖型短消息）；act_probability 无信号不用于门控 |

---

## 🚀 阶段一：接入真实决策模型（v0.2 · 核心目标）

> 方向：Mock → Laya 自托管（国内推荐）→ 可选 Jev 官方 API。UI / 分流规则 / 记录逻辑零改动。

### 1.1 Laya 自托管接入 ✅（2026-10-25 完成）

> 完整训练流程文档（环境/数据/训练/校准/应用/调优）见 **[TRAINING.md](TRAINING.md)**。

- [x] 标注集构建：114 种子 + 208 变体 = 322 训练样本，45 条独立评估集，含 10 组成对边界对照样本
- [x] 微调：multilingual checkpoint + LoRA r=8/alpha=32（target Wqkv）+ 决策头全训 + 严格恰当评分损失（log+spherical+RPS）+ bf16 + 梯度检查点，RTX 3060 4.5 分钟 / 12 epochs，**eval_acc 0.770**
- [x] 温度拟合校准：分桶 NLL 拟合（choice 3.07 / noul 3.81 / score 4.54），已写入 checkpoint
- [x] 门槛量化：noul 0.80→0.65（校准后区间准确率 92% @ 覆盖率 55.6%，优于 0.8 门槛的 94% @ 37.8%）
- [ ] 后端 laya.py Provider 补全（对接 RLAgent.system_one）
- [ ] 前端切 ACTIVE_PROVIDER='http' 联调
- 验收：typed-decisions ≥ 0.75 ✅ 达成（0.770）

**计划生成/修改文件：**

```
backend/app/providers/laya.py          ← 由 laya_stub.py 补全实现（修改）
backend/.env.example                  ← LAYA_BASE_URL 等配置模板（新增）
backend/training/build_dataset.py     ← 标注集构建脚本（新增）
backend/training/finetune.py          ← 微调入口（新增）
backend/training/calibrate.py         ← 温度拟合校准（新增）
backend/evals/eval_dataset.jsonl      ← 评估集（新增）
backend/evals/run_eval.py              ← 批量评估与校准曲线输出（新增）
src/decision/index.ts                 ← ACTIVE_PROVIDER='http'（修改）
```

### 1.2 Jev 官方 API（可选，受 451 地区限制）

- [ ] `pip install typesafe-sdk`，按三原语组装 questions
- [ ] 代理 / OpenRouter fallback 路线验证
- [ ] 验收：真实请求成功返回并完成全流程分流

**计划生成/修改文件：** `backend/app/providers/jev.py`（修改）、`backend/.env.example`（修改）

---

## 🌐 阶段二：真实弹幕源接入（v0.3）

> 方向：从「模拟器 + 手动输入」升级为真实直播间弹幕流，同时保持模拟源用于开发。

- [ ] 弹幕源 Provider 抽象：`DanmakuSource` 接口（start/stop/onMessage），与决策引擎解耦
- [ ] 模拟源适配（现有 simulator 重构为 source 实现）
- [ ] 平台源适配（需评估平台开放接口与合规边界；无公开接口的平台不硬破解）
- [ ] 后端 WebSocket 网关：转发弹幕事件至前端（替代前端轮询式模拟）
- [ ] 验收：真实直播间弹幕 3 秒内完成判断分流

**计划生成/修改文件：**

```
src/services/danmaku-source/base.ts          ← Source 接口定义（新增）
src/services/danmaku-source/mock-source.ts   ← 模拟源（新增）
src/services/danmaku-source/platform-*.ts   ← 平台适配器（新增，视合规而定）
src/stores/workbench.ts                      ← 接入 Source（修改）
backend/app/ws.py                            ← WebSocket 网关（新增）
backend/app/main.py                          ← 挂载 ws 路由（修改）
```

---

## 🧰 阶段三：工程化完善（v0.3 并行）

- [x] 判断记录持久化：IndexedDB 快照（src/utils/persist.ts；判断中断的消息恢复为「失败可重试」，待办队列由记录重建）✅ 2026-10-25
- [x] E2E 检查：npm run e2e（scripts/e2e-check.ps1：后端语法 + 前端类型/构建 + mock API 契约 8 项断言 + laya 服务探测）✅ 2026-10-25
- [ ] Playwright UI 用例：关键路径（发送→判断→分流→待办→标记完成）
- [ ] CI：GitHub Actions（push 触发 `vue-tsc` + `vite build` + ruff 检查后端）
- [ ] Docker 部署（前端静态 + 后端服务编排）
- [ ] 验收：CI 绿；E2E 通过率 100%（本地 E2E 已达成；云端 CI 待接入）

**计划生成/修改文件：**

```
src/utils/persist.ts                      ← IndexedDB 快照存取（新增 ✅）
scripts/e2e-check.ps1                     ← npm run e2e 本地检查（新增 ✅）
tests/e2e/*.spec.ts                       ← Playwright 用例（待做）
.github/workflows/ci.yml                   ← CI 流水线（待做）
Dockerfile / docker-compose.yml            ← 容器编排（待做）
backend/app/db.py                         ← SQLite 记录表（待做；当前为前端 IndexedDB 方案）
```

---

## 📊 阶段四：决策质量工程（v0.4）

> 方向：把 Laya/Jev 文章的评估体系落进系统——阈值不是拍的，是校准出来的。

- [ ] 校准评估集：扩充至 200~500 条人工标注（当前 45 条独立集已回放：choice 82.2% / noul 86.7% / score ±1 97.8%，报告存 backend/evals/reports/；待补「直播中断类」——当前无样本被判等级 3）
- [x] 评估集回放工具：backend/evals/replay_eval.py（http/local 双模式，provider 校验防误测，产出 JSON+MD 报告）✅ 2026-10-25
- [x] 校准与阈值可视化：CalibrationView（分桶温度表 / noul 门槛 0.80↔0.65 量化对比 / 回放指标与混淆矩阵；数据源 src/data/calibration.ts）✅ 2026-10-25
- [x] ECE 校准曲线：replay_eval.py 增加 reliability 分桶 + ECE/Brier（5 等宽桶：choice ECE **0.099 ≤ 0.1 达标** / noul 0.117 / Brier 0.068、0.126），校准页新增 SVG 可靠性曲线与 Score 分箱校准 ✅ 2026-10-25
- [x] A/B 引擎对比模式：ab_runner.py（零样本基线 vs 微调，顺序加载各自温度生效；choice 44.4%→82.2%、noul 55.6%→86.7%、分歧 34/45 条，基线 score 坍缩在 L2）；校准页新增对比卡 ✅ 2026-10-25
- [x] 阈值调优工具：按「自动化覆盖率 vs 误分流率」曲线给出 60%/65% 的数据依据（已在 v0.2 预演：noul 门槛 0.8→0.65 依据校准分位实测）
- [ ] 验收：ECE ≤ 0.1（choice 0.099 已达标；noul 0.117 接近）；阈值选择量化依据已达成（TRAINING.md + 校准页）

**计划生成/修改文件：**

```
backend/evals/replay_eval.py              ← 评估回放 + ECE/Brier/可靠性分桶（✅）
backend/evals/ab_runner.py                ← 双引擎对比（✅）
backend/evals/reports/eval-report.*       ← 回放报告 JSON+MD（✅）
backend/evals/reports/ab-report.*         ← A/B 对比报告（✅）
src/data/calibration.ts                   ← 校准/评估实测数据模块（✅）
src/components/pages/CalibrationView.vue  ← 校准与阈值页（含可靠性曲线 + A/B 卡）（✅）
docs/threshold-tuning.md                  ← 阈值依据文档（待做；量化依据已并入 TRAINING.md 与校准页）
```

---

## 💼 阶段五：招投标业务迁移（v1.0 · 价值跃迁）

> 方向：把「直播弹幕分诊」的判断模式迁移到招标投标业务，复用整套框架，仅换判据问卷。

| 课程判据 | 招投标迁移 | 原语 |
| --- | --- | --- |
| 五类弹幕分类 | 标讯相关性过滤：强相关 / 弱相关 / 无关 / 需复核 / 信息不足 | Choice |
| 信息充分性 | 商机资料是否足够进入投标流程（资质/业绩/时间齐备度） | Noul |
| 跟课影响优先级 | 商机优先级：金额 × 时限 × 匹配度加权 | Score |
| 60%/65% 双门槛 | 动作安全门：低置信不自动提交/不自动弃标，转人工 | 阈值 |

- [ ] 判据问卷改造（`criteria.ts` 业务无关化，支持多套判据集切换）
- [ ] 数据源：招标平台标讯接入（与 GIS-Agent 图纸分析场景联动）
- [ ] 处理队列映射：讲师待答→商务跟进 / 助教处理→标书准备 / 待确认→人工复核
- [ ] 验收：真实标讯样本批量跑通，误分流率 ≤ 5%

**计划生成/修改文件：**

```
src/config/criteria-bidding.ts           ← 招投标判据集（新增）
src/config/criteria.ts                   ← 改为判据集注册表（修改）
src/decision/routing.ts                  ← 分流策略参数化（修改）
backend/app/providers/                   ← 新增标讯领域微调模型插槽（新增）
docs/bidding-usecase.md                  ← 迁移方案文档（新增）
```

---

## 版本里程碑总览

| 版本 | 主题 | 核心交付 |
| --- | --- | --- |
| v0.1 ✅ | 框架 + UI + Mock | 三栏工作台、决策抽象、双门槛分流 |
| v0.2 | 真实决策模型 | Laya 微调/校准/自托管，Jev 可选 |
| v0.3 | 真实数据流 | 弹幕源 Provider、WebSocket、持久化、CI |
| v0.4 | 决策质量 | 校准曲线、阈值依据、A/B 引擎 |
| v1.0 | 业务落地 | 招投标判据迁移，标讯分诊工作台 |

> AI生成
