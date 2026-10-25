# ROADMAP · 开发路线图

> 基于当前状态（v0.1.0）规划。每个任务标注**计划生成/修改的文件**，里程碑给出验收标准。

---

## 📍 当前状态（v0.2.0 · 2026-10-25）

| 维度 | 状态 |
| --- | --- |
| 前端三栏工作台 | ✅ 完成（直播窗弹幕动画 / Choice·Noul·Score 判断卡 / 三队列待办 / 记录页 / JSON 详情抽屉） |
| 决策引擎 | ✅ **Laya multilingual LoRA 微调版**（mmBERT 322M，eval_acc 0.770：choice 0.822 / noul 0.867 / score 0.622） |
| 校准 | ✅ 分桶温度拟合完成（choice:3-5 T=3.07 / noul:2 T=3.81 / score:3-5 T=4.54）；noul 门槛校准后量化为 65% |
| 决策抽象层 | ✅ Provider 接口 + 双门槛分流规则（60% / 65%），模型可插拔 |
| 后端 | ⚙️ FastAPI **骨架**（未启动；jev_stub / laya_stub 插槽就绪，`DECISION_PROVIDER=mock\|jev\|laya`） |
| 质量 | ✅ vue-tsc 零错误；vite build 成功；训练 12 epochs 4.5 分钟（RTX 3060 3.7GB 显存） |
| 仓库 | ✅ 已推送 [github.com/Sogrey/danmaku-workbench](https://github.com/Sogrey/danmaku-workbench) main |
| 已知边界 | score 是最弱原语（0.622，对应官方基准一致）；act_probability 无信号不用于门控；判断记录仅存内存 |

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

- [ ] 判断记录持久化：IndexedDB（前端）或 SQLite（后端），刷新不丢
- [ ] E2E 测试：Playwright 关键路径（发送→判断→分流→待办→标记完成）
- [ ] CI：GitHub Actions（push 触发 `vue-tsc` + `vite build` + ruff 检查后端）
- [ ] Docker 部署（前端静态 + 后端服务编排）
- [ ] 验收：CI 绿；E2E 通过率 100%

**计划生成/修改文件：**

```
src/stores/persistence.ts                ← IndexedDB 持久化（新增）
tests/e2e/*.spec.ts                     ← Playwright 用例（新增）
.github/workflows/ci.yml                 ← CI 流水线（新增）
Dockerfile / docker-compose.yml          ← 容器编排（新增）
backend/app/db.py                        ← SQLite 记录表（新增）
```

---

## 📊 阶段四：决策质量工程（v0.4）

> 方向：把 Laya/Jev 文章的评估体系落进系统——阈值不是拍的，是校准出来的。

- [ ] 校准评估集：人工标注 200~500 条（覆盖五类长尾），存 `backend/evals/`
- [ ] 置信度校准曲线：ECE 计算 + 前端可视化（drawer 增加校准页签）
- [x] 阈值调优工具：按「自动化覆盖率 vs 误分流率」曲线给出 60%/65% 的数据依据（已在 v0.2 预演：noul 门槛 0.8→0.65 依据校准分位实测）
- [ ] A/B 引擎对比模式：双 Provider 并行跑批，输出一致率与分歧样本
- [ ] 验收：ECE ≤ 0.1；给出阈值选择的量化依据文档

**计划生成/修改文件：**

```
backend/evals/calibration_report.md      ← 校准分析报告（新增）
backend/evals/ab_runner.py               ← 双引擎对比（新增）
src/components/CalibrationView.vue       ← 校准曲线页（新增）
src/components/pages/RecordsView.vue     ← 挂校准入口（修改）
docs/threshold-tuning.md                ← 阈值依据文档（新增）
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
