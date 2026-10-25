# 评估集回放报告（Laya danmaku-dm-v0.2）

- 时间：2026-10-25T10:46:33.825584+00:00
- 模式：http（provider：laya-finetuned-v0.2）
- 样本：45 条独立评估集（eval_dataset.jsonl，与训练集零重叠）
- 平均延迟：90 ms/条

## 三原语指标

| 原语 | 指标 | 数值 |
| --- | --- | --- |
| Choice | top-1 准确率 | **82.2%** |
| Choice | 置信度 ≥60% 子集准确率（覆盖率 48.9%） | 90.9% |
| Noul | 区间准确率（阈值 0.65） | **86.7%** |
| Noul | 覆盖率（判为可处理比例） | 57.8% |
| Noul | 通过区间内准确率 | 92.3% |
| Noul | 真值可处理 / 不可处理的平均概率 | 0.725 / 0.266 |
| Score | 等级 exact 命中 | **55.6%** |
| Score | 等级 ±1 容差命中 | 97.8% |
| Score | 与真值等级的 MAE | 0.55 |

## Choice 混淆矩阵（行=真值，列=预测）

| 真值 \ 预测 | technical | feedback | chat | spam | insufficient |
| --- | --- | --- | --- | --- | --- |
| technical | 10 | 0 | 0 | 0 | 0 |
| feedback | 1 | 9 | 0 | 0 | 0 |
| chat | 0 | 0 | 6 | 0 | 2 |
| spam | 0 | 0 | 0 | 8 | 0 |
| insufficient | 4 | 1 | 0 | 0 | 4 |

## 错误样本（13 条）

| id | 消息 | 真值→预测(类别) | 置信度 | noul 判定 | Score 真值→预测 |
| --- | --- | --- | --- | --- | --- |
| ev-0003 | 官方 API 在国内能直接访问吗 | technical→technical | 0.89 | ✗(0.61) | 1→0 |
| ev-0007 | demo 项目的代码能开源到内网 git 吗 | technical→technical | 0.67 | ✗(0.39) | 0→0 |
| ev-0013 | 共享的代码区反光了，看不清关键字 | feedback→technical | 0.73 | ✓(0.85) | 1→2 |
| ev-0019 | 潜水了很久，今天必须冒个泡 | chat→insufficient | 0.37 | ✓(0.84) | 0→1 |
| ev-0021 | 下期直播什么时候开 | chat→chat | 0.22 | ✗(0.03) | 0→1 |
| ev-0022 | 666 | chat→insufficient | 0.43 | ✓(0.67) | 0→1 |
| ev-0024 | 散会去吃饭，回放见 | chat→chat | 0.12 | ✗(0.04) | 0→0 |
| ev-0035 | 就是这个报错，帮我看看 | insufficient→technical | 0.51 | ✓(0.27) | 1→1 |
| ev-0036 | 到第三步就不行了 | insufficient→technical | 0.38 | ✓(0.07) | 2→1 |
| ev-0037 | 为什么我的和演示不一样 | insufficient→technical | 0.14 | ✗(0.73) | 1→1 |
| ev-0038 | 同样的操作，别人可以我不行 | insufficient→insufficient | 0.13 | ✓(0.11) | 2→0 |
| ev-0041 | 跟上上一位同学的问题一样 | insufficient→technical | 0.22 | ✓(0.09) | 1→0 |
| ev-0042 | 这一页过一下，太快了 | insufficient→feedback | 0.85 | ✗(0.82) | 1→0 |
