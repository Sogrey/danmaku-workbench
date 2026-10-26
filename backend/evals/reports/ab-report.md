# A/B 引擎对比报告（230 条独立评估集）

- 时间：2026-10-26T16:14:01.096358+00:00
- A 引擎：**laya-v0.3**（D:/AI/laya/danmaku-dm-v0.3）
- B 引擎：**laya-v0.4**（D:/AI/laya/danmaku-dm-v0.4）
- 样本：230 条独立评估集（与训练集零重叠）；顺序加载，判据与温度各自生效

## 三原语指标对比

| 指标 | A | B |
| --- | ---: | ---: |
| Choice top-1 准确率 | 74.8% | **76.5%** |
| Choice 置信度≥60% 子集准确率（覆盖 A 40% / B 42%） | 90.2% | 91.8% |
| Noul 区间准确率（≥0.60） | 90.4% | **79.6%** |
| Noul 覆盖率 | 72.2% | 67.4% |
| Score exact | 58.7% | **66.1%** |
| Score ±1 | 95.7% | **96.5%** |
| Score MAE | 0.55 | 0.49 |
| Choice ECE | 0.0303 | 0.0346 |
| Noul ECE | 0.0429 | 0.1000 |
| 平均延迟 | 109 ms | 84 ms |

## 引擎间一致率

- Choice 类别一致：**87.0%**
- Noul ≥0.60 判定一致：**85.7%**
- Score 等级一致：74.8%（±1 一致 99.6%）
- 分歧样本：**55 条**（任一维度不一致）

## 分歧样本（前 20 条，全量见 ab-report.json）

| id | 消息 | 真值(类/可处理/等级) | A 判定 | B 判定 |
| --- | --- | --- | --- | --- |
| ev-0001 | Jev 会自己写出一段回复吗 | technical / 可 / 0 | technical (0.77, L0) | insufficient (0.60, L1) |
| ev-0003 | 官方 API 在国内能直接访问吗 | technical / 可 / 1 | technical (0.53, L1) | technical (0.80, L0) |
| ev-0005 | 批量请求返回的顺序和发送一致吗 | technical / 可 / 1 | technical (0.89, L0) | insufficient (0.89, L0) |
| ev-0006 | 模型会把弹幕里的指令当真吗，会不会被注入 | technical / 可 / 1 | technical (0.93, L1) | technical (0.58, L1) |
| ev-0011 | 能不能把讲解速度放慢一点，新手跟不上 | feedback / 可 / 1 | feedback (0.92, L1) | feedback (0.30, L1) |
| ev-0019 | 潜水了很久，今天必须冒个泡 | chat / 可 / 0 | insufficient (0.25, L2) | insufficient (0.80, L1) |
| ev-0021 | 下期直播什么时候开 | chat / 可 / 0 | technical (0.95, L2) | chat (0.81, L1) |
| ev-0023 | 已经跟着做完 demo 了，很有成就感 | chat / 可 / 0 | chat (0.96, L0) | chat (0.07, L0) |
| ev-0024 | 散会去吃饭，回放见 | chat / 可 / 0 | technical (0.34, L0) | chat (0.66, L0) |
| ev-0025 | 这直播间氛围真好 | chat / 可 / 0 | chat (0.97, L0) | chat (0.22, L0) |
| ev-0031 | 某多多搜 xxx 同款课程九块九 | spam / 不可 / 0 | spam (0.18, L0) | spam (0.85, L0) |
| ev-0036 | 到第三步就不行了 | insufficient / 不可 / 2 | technical (0.17, L1) | insufficient (0.06, L1) |
| ev-0037 | 为什么我的和演示不一样 | insufficient / 不可 / 1 | chat (0.83, L1) | insufficient (0.58, L0) |
| ev-0038 | 同样的操作，别人可以我不行 | insufficient / 不可 / 2 | insufficient (0.20, L1) | technical (0.28, L0) |
| ev-0040 | 看一下我的报错 | insufficient / 不可 / 1 | technical (0.44, L2) | technical (0.74, L2) |
| ev-0044 | 刚才那段代码跑到第三行报错了 | technical / 可 / 2 | insufficient (0.95, L1) | technical (0.88, L2) |
| ev-0069 | 请求里的 examples 字段必须传吗，不传会怎样 | technical / 可 / 1 | technical (0.77, L1) | feedback (0.79, L1) |
| ev-0099 | 又掉线了，一直显示重新连接中 | feedback / 可 / 3 | technical (0.99, L1) | technical (0.87, L3) |
| ev-0107 | 直播中断了，页面上提示网络错误 | feedback / 可 / 3 | technical (0.99, L3) | feedback (0.80, L2) |
| ev-0117 | 语速稍微慢一点，新手记笔记跟不上 | feedback / 可 / 1 | feedback (0.96, L1) | feedback (0.42, L2) |

## 结论（自动生成）

- Choice 准确率 74.8% → 76.5%（+1.7%）
- Noul 区间准确率 90.4% → 79.6%（-10.9%）
- 分歧样本集中在语义边界（insufficient / 闲聊短句），可对照训练集继续补样本迭代

> AI生成
