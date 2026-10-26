# A/B 引擎对比报告（230 条独立评估集）

- 时间：2026-10-26T17:27:35.278228+00:00
- A 引擎：**laya-v0.3**（D:/AI/laya/danmaku-dm-v0.3）
- B 引擎：**laya-v0.6**（D:/AI/laya/danmaku-dm-v0.6）
- 样本：230 条独立评估集（与训练集零重叠）；顺序加载，判据与温度各自生效

## 三原语指标对比

| 指标 | A | B |
| --- | ---: | ---: |
| Choice top-1 准确率 | 74.8% | **76.5%** |
| Choice 置信度≥60% 子集准确率（覆盖 A 40% / B 45%） | 90.2% | 92.3% |
| Noul 区间准确率（≥0.60） | 90.4% | **89.6%** |
| Noul 覆盖率 | 72.2% | 71.3% |
| Score exact | 58.7% | **63.0%** |
| Score ±1 | 95.7% | **95.7%** |
| Score MAE | 0.55 | 0.50 |
| Choice ECE | 0.0303 | 0.0287 |
| Noul ECE | 0.0429 | 0.0271 |
| 平均延迟 | 74 ms | 47 ms |

## 引擎间一致率

- Choice 类别一致：**85.7%**
- Noul ≥0.60 判定一致：**93.9%**
- Score 等级一致：73.5%（±1 一致 98.7%）
- 分歧样本：**45 条**（任一维度不一致）

## 分歧样本（前 20 条，全量见 ab-report.json）

| id | 消息 | 真值(类/可处理/等级) | A 判定 | B 判定 |
| --- | --- | --- | --- | --- |
| ev-0011 | 能不能把讲解速度放慢一点，新手跟不上 | feedback / 可 / 1 | feedback (0.92, L1) | feedback (0.59, L1) |
| ev-0019 | 潜水了很久，今天必须冒个泡 | chat / 可 / 0 | insufficient (0.25, L2) | insufficient (0.92, L1) |
| ev-0020 | 这才是我想要的课，讲得透 | chat / 可 / 0 | technical (0.91, L0) | chat (0.94, L0) |
| ev-0024 | 散会去吃饭，回放见 | chat / 可 / 0 | technical (0.34, L0) | chat (0.95, L0) |
| ev-0037 | 为什么我的和演示不一样 | insufficient / 不可 / 1 | chat (0.83, L1) | insufficient (0.86, L0) |
| ev-0038 | 同样的操作，别人可以我不行 | insufficient / 不可 / 2 | insufficient (0.20, L1) | technical (0.08, L1) |
| ev-0044 | 刚才那段代码跑到第三行报错了 | technical / 可 / 2 | insufficient (0.95, L1) | technical (0.97, L2) |
| ev-0052 | 三个原语的提问顺序会影响概率输出吗 | technical / 可 / 1 | feedback (0.94, L1) | technical (0.96, L1) |
| ev-0059 | 如果两个类别的概率一样高，程序该选哪个 | technical / 可 / 1 | technical (0.81, L1) | technical (0.57, L1) |
| ev-0061 | 官方有没有提供批量异步的调用接口 | technical / 可 / 1 | technical (0.73, L1) | technical (0.58, L0) |
| ev-0069 | 请求里的 examples 字段必须传吗，不传会怎样 | technical / 可 / 1 | technical (0.77, L1) | feedback (0.75, L1) |
| ev-0076 | 我的脚本跑到一半抛了 KeyError: answers | technical / 可 / 2 | insufficient (0.64, L1) | technical (0.91, L1) |
| ev-0081 | 服务跑一天内存涨了 2G，这种泄漏怎么排查 | technical / 可 / 2 | technical (0.97, L0) | spam (0.95, L0) |
| ev-0090 | 返回的 confidence 是校准前还是校准后的值 | technical / 可 / 1 | technical (0.99, L1) | technical (0.35, L1) |
| ev-0099 | 又掉线了，一直显示重新连接中 | feedback / 可 / 3 | technical (0.99, L1) | technical (0.95, L3) |
| ev-0107 | 直播中断了，页面上提示网络错误 | feedback / 可 / 3 | technical (0.99, L3) | feedback (0.98, L2) |
| ev-0114 | 画质糊成一团，编辑器行号都数不清 | feedback / 可 / 3 | feedback (0.97, L2) | technical (0.95, L1) |
| ev-0120 | 字幕错别字有点多，影响理解 | feedback / 可 / 1 | feedback (0.97, L1) | feedback (0.44, L1) |
| ev-0137 | 直播间标题写错时间了，白等半小时 | feedback / 可 / 1 | feedback (1.00, L1) | feedback (0.97, L3) |
| ev-0138 | 弹幕面板挡住命令行了，能调透明度吗 | feedback / 可 / 1 | technical (0.98, L2) | feedback (0.96, L1) |

## 结论（自动生成）

- Choice 准确率 74.8% → 76.5%（+1.7%）
- Noul 区间准确率 90.4% → 89.6%（-0.9%）
- 分歧样本集中在语义边界（insufficient / 闲聊短句），可对照训练集继续补样本迭代