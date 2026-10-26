# A/B 引擎对比报告（230 条独立评估集）

- 时间：2026-10-26T15:37:18.738268+00:00
- A 引擎：**laya-v0.2**（D:/AI/laya/danmaku-dm-v0.2）
- B 引擎：**laya-v0.3**（D:/AI/laya/danmaku-dm-v0.3）
- 样本：230 条独立评估集（与训练集零重叠）；顺序加载，判据与温度各自生效

## 三原语指标对比

| 指标 | A | B |
| --- | ---: | ---: |
| Choice top-1 准确率 | 76.5% | **74.8%** |
| Choice 置信度≥60% 子集准确率（覆盖 A 41% / B 40%） | 91.6% | 90.2% |
| Noul 区间准确率（≥0.60） | 87.0% | **90.4%** |
| Noul 覆盖率 | 70.4% | 72.2% |
| Score exact | 57.4% | **58.7%** |
| Score ±1 | 96.1% | **95.7%** |
| Score MAE | 0.56 | 0.55 |
| Choice ECE | 0.0593 | 0.0303 |
| Noul ECE | 0.0992 | 0.0429 |
| 平均延迟 | 87 ms | 98 ms |

## 引擎间一致率

- Choice 类别一致：**86.1%**
- Noul ≥0.60 判定一致：**89.6%**
- Score 等级一致：73.0%（±1 一致 99.1%）
- 分歧样本：**48 条**（任一维度不一致）

## 分歧样本（前 20 条，全量见 ab-report.json）

| id | 消息 | 真值(类/可处理/等级) | A 判定 | B 判定 |
| --- | --- | --- | --- | --- |
| ev-0003 | 官方 API 在国内能直接访问吗 | technical / 可 / 1 | technical (0.61, L0) | technical (0.53, L1) |
| ev-0019 | 潜水了很久，今天必须冒个泡 | chat / 可 / 0 | insufficient (0.83, L1) | insufficient (0.25, L2) |
| ev-0020 | 这才是我想要的课，讲得透 | chat / 可 / 0 | chat (0.86, L0) | technical (0.91, L0) |
| ev-0021 | 下期直播什么时候开 | chat / 可 / 0 | chat (0.03, L1) | technical (0.95, L2) |
| ev-0024 | 散会去吃饭，回放见 | chat / 可 / 0 | chat (0.04, L0) | technical (0.34, L0) |
| ev-0037 | 为什么我的和演示不一样 | insufficient / 不可 / 1 | technical (0.73, L1) | chat (0.83, L1) |
| ev-0040 | 看一下我的报错 | insufficient / 不可 / 1 | insufficient (0.61, L2) | technical (0.44, L2) |
| ev-0041 | 跟上上一位同学的问题一样 | insufficient / 不可 / 1 | technical (0.09, L0) | insufficient (0.10, L0) |
| ev-0044 | 刚才那段代码跑到第三行报错了 | technical / 可 / 2 | technical (0.80, L2) | insufficient (0.95, L1) |
| ev-0069 | 请求里的 examples 字段必须传吗，不传会怎样 | technical / 可 / 1 | feedback (0.78, L1) | technical (0.77, L1) |
| ev-0073 | 想接到公司内部的工单系统，用哪个回调钩子 | technical / 可 / 1 | technical (0.65, L0) | technical (0.26, L1) |
| ev-0076 | 我的脚本跑到一半抛了 KeyError: answers | technical / 可 / 2 | technical (0.86, L1) | insufficient (0.64, L1) |
| ev-0101 | 我这边彻底听不到了，群里说还有声 | feedback / 可 / 3 | insufficient (0.04, L0) | feedback (0.01, L3) |
| ev-0108 | 只能听到回声，老师的声音完全听不见 | feedback / 可 / 3 | feedback (0.40, L2) | feedback (0.95, L3) |
| ev-0111 | 弹幕能发出去，但直播画面是黑的 | feedback / 可 / 3 | feedback (0.52, L2) | feedback (1.00, L3) |
| ev-0113 | 手机看直播直接闪退，重进还是黑屏 | feedback / 可 / 3 | technical (0.48, L2) | feedback (1.00, L2) |
| ev-0121 | 讲义配色太浅，后排看不清代码 | feedback / 可 / 1 | technical (0.90, L1) | feedback (0.98, L1) |
| ev-0129 | 麦克风离嘴太远，听不清楚在说什么 | feedback / 可 / 1 | insufficient (0.55, L1) | insufficient (0.89, L2) |
| ev-0135 | 鼠标指针太小，看不清指到哪一行 | feedback / 可 / 1 | technical (0.84, L1) | feedback (0.72, L2) |
| ev-0138 | 弹幕面板挡住命令行了，能调透明度吗 | feedback / 可 / 1 | feedback (0.83, L1) | technical (0.98, L2) |

## 结论（自动生成）

- Choice 准确率 76.5% → 74.8%（-1.7%）
- Noul 区间准确率 87.0% → 90.4%（+3.5%）
- 分歧样本集中在语义边界（insufficient / 闲聊短句），可对照训练集继续补样本迭代