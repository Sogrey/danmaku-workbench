# A/B 引擎对比报告（45 条独立评估集）

- 时间：2026-10-25T14:23:33.372354+00:00
- A 引擎：**laya-baseline**（D:/AI/laya/repo-laya-hf/multilingual）
- B 引擎：**laya-finetuned**（D:/AI/laya/danmaku-dm-v0.2）
- 样本：230 条独立评估集（与训练集零重叠）；顺序加载，判据与温度各自生效

## 三原语指标对比

| 指标 | A | B |
| --- | ---: | ---: |
| Choice top-1 准确率 | 43.5% | **76.5%** |
| Choice 置信度≥60% 子集准确率（覆盖 A 33% / B 41%） | 68.4% | 91.6% |
| Noul 区间准确率（≥0.65） | 64.3% | **85.7%** |
| Noul 覆盖率 | 79.1% | 66.5% |
| Score exact | 9.6% | **57.4%** |
| Score ±1 | 59.1% | **96.1%** |
| Score MAE | 1.19 | 0.56 |
| Choice ECE | 0.2227 | 0.0593 |
| Noul ECE | 0.1834 | 0.0992 |
| 平均延迟 | 96 ms | 100 ms |

## 引擎间一致率

- Choice 类别一致：**54.3%**
- Noul ≥0.65 判定一致：**63.0%**
- Score 等级一致：19.6%（±1 一致 70.4%）
- 分歧样本：**164 条**（任一维度不一致）

## 分歧样本（前 20 条，全量见 ab-report.json）

| id | 消息 | 真值(类/可处理/等级) | A 判定 | B 判定 |
| --- | --- | --- | --- | --- |
| ev-0001 | Jev 会自己写出一段回复吗 | technical / 可 / 0 | insufficient (0.54, L2) | technical (0.66, L0) |
| ev-0002 | Choice 和 Noul 能放在同一次请求里吗 | technical / 可 / 1 | insufficient (0.51, L2) | technical (0.83, L0) |
| ev-0003 | 官方 API 在国内能直接访问吗 | technical / 可 / 1 | technical (0.74, L2) | technical (0.61, L0) |
| ev-0004 | 怎么给 Noul 写 criteria 才不歧义 | technical / 可 / 1 | insufficient (0.46, L2) | technical (0.68, L1) |
| ev-0005 | 批量请求返回的顺序和发送一致吗 | technical / 可 / 1 | spam (0.66, L2) | technical (0.88, L0) |
| ev-0006 | 模型会把弹幕里的指令当真吗，会不会被注入 | technical / 可 / 1 | technical (0.58, L2) | technical (0.70, L0) |
| ev-0007 | demo 项目的代码能开源到内网 git 吗 | technical / 可 / 0 | technical (0.57, L2) | technical (0.39, L0) |
| ev-0012 | 直播突然断了，现在只有封面图 | feedback / 可 / 3 | insufficient (0.89, L2) | feedback (0.70, L2) |
| ev-0014 | 音轨只有左边耳朵有声音 | feedback / 可 / 1 | technical (0.80, L2) | feedback (0.88, L2) |
| ev-0016 | 视频一直 480p，切不上 1080 | feedback / 可 / 2 | technical (0.98, L2) | feedback (0.84, L2) |
| ev-0017 | 麦克风声音断了，能听到回声 | feedback / 可 / 2 | technical (0.79, L2) | feedback (0.90, L2) |
| ev-0018 | 老师辛苦，今晚收获很大 | chat / 可 / 0 | chat (0.72, L2) | chat (0.88, L0) |
| ev-0020 | 这才是我想要的课，讲得透 | chat / 可 / 0 | feedback (0.95, L2) | chat (0.86, L0) |
| ev-0021 | 下期直播什么时候开 | chat / 可 / 0 | insufficient (0.95, L2) | chat (0.03, L1) |
| ev-0022 | 666 | chat / 可 / 0 | spam (0.95, L2) | insufficient (0.67, L1) |
| ev-0023 | 已经跟着做完 demo 了，很有成就感 | chat / 可 / 0 | technical (0.96, L2) | chat (0.85, L0) |
| ev-0024 | 散会去吃饭，回放见 | chat / 可 / 0 | technical (0.93, L2) | chat (0.04, L0) |
| ev-0025 | 这直播间氛围真好 | chat / 可 / 0 | spam (0.95, L2) | chat (0.73, L0) |
| ev-0026 | 内部价卖课，比官网便宜一半，私我 | spam / 不可 / 0 | spam (1.00, L2) | spam (0.30, L1) |
| ev-0027 | 薇信号同手机号，送全套付费课程 | spam / 不可 / 0 | spam (1.00, L2) | spam (0.04, L0) |

## 结论（自动生成）

- Choice 准确率 43.5% → 76.5%（+33.0%）
- Noul 区间准确率 64.3% → 85.7%（+21.3%）
- 微调收益显著：基线近随机（五类≈20%），微调后达到可用判别水平
- 分歧样本集中在语义边界（insufficient / 闲聊短句），可对照训练集继续补样本迭代