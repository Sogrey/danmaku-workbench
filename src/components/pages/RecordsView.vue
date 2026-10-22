<script setup lang="ts">
import { computed } from 'vue'
import type { WorkRecord } from '@/types'
import { ASSIGNMENT, CATEGORIES, SCORE_LEVEL_NAMES, TARGET_NAMES, THRESHOLDS } from '@/config/criteria'
import { useWorkbenchStore } from '@/stores/workbench'
import { useUiStore } from '@/stores/ui'

const wb = useWorkbenchStore()
const ui = useUiStore()

const records = computed(() => [...wb.records].reverse())

function catOf(r: WorkRecord) {
  return CATEGORIES[r.decision.choice.category]
}

function download(name: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

function exportJson() {
  download(
    `danmaku-records-${new Date().toISOString().slice(0, 10)}.json`,
    JSON.stringify(wb.records, null, 2),
    'application/json',
  )
}

const CSV_HEAD = 'time,author,text,category,category_prob,actionable_prob,priority,score,target,status'

function csvEscape(v: string) {
  return `"${v.replace(/"/g, '""')}"`
}

function exportCsv() {
  const rows = wb.records.map((r) =>
    [
      r.time,
      r.author,
      csvEscape(r.text),
      r.decision.choice.category,
      (r.decision.choice.probabilities[r.decision.choice.category] * 100).toFixed(1) + '%',
      (r.decision.noul.probability * 100).toFixed(1) + '%',
      r.decision.score.level,
      r.decision.score.value.toFixed(2),
      TARGET_NAMES[r.disposition.target] ?? '留在弹幕区',
      r.done ? '已处理' : '待处理',
    ].join(','),
  )
  download(
    `danmaku-records-${new Date().toISOString().slice(0, 10)}.csv`,
    '\uFEFF' + [CSV_HEAD, ...rows].join('\n'),
    'text/csv',
  )
}
</script>

<template>
  <div class="records">
    <!-- 规则卡 -->
    <section class="rules card">
      <header class="rules-head">
        <div>
          <h2>分类规则与阈值</h2>
          <p>五类候选（Choice criteria）· 信息充分性（Noul）· 优先级刻度（Score）· 程序分流</p>
        </div>
        <div class="threshold-badges">
          <span class="badge badge-ok">分类概率 ≥ {{ THRESHOLDS.classifyProbability * 100 }}%</span>
          <span class="badge badge-ok">处理条件概率 ≥ {{ THRESHOLDS.actionableProbability * 100 }}%</span>
          <span class="badge badge-plain">引擎：{{ wb.providerDesc }}</span>
        </div>
      </header>

      <div class="rules-grid">
        <div v-for="a in ASSIGNMENT" :key="a.category" class="rule-item">
          <span class="chip" :class="`chip-${a.category}`">{{ CATEGORIES[a.category].name }}</span>
          <p class="rule-desc">{{ CATEGORIES[a.category].description }}</p>
          <div class="rule-route">
            <span>{{ a.handler }}</span>
            <span class="arrow">→</span>
            <b>{{ a.target }}</b>
          </div>
        </div>
      </div>

      <div class="score-legend">
        <span class="legend-title">Score 等级刻度：</span>
        <span v-for="(name, i) in SCORE_LEVEL_NAMES" :key="i" class="legend-item">
          <b>{{ i }}</b> {{ name }}
        </span>
      </div>
    </section>

    <!-- 记录表 -->
    <section class="card table-card">
      <header class="table-head">
        <div>
          <h2>判断记录</h2>
          <p>共 {{ records.length }} 条 · 失败 {{ wb.failedCount }} 条（在课堂互动页点击可重试）</p>
        </div>
        <div class="table-actions">
          <button class="btn ghost" :disabled="records.length === 0" @click="exportCsv">
            导出 CSV
          </button>
          <button class="btn solid" :disabled="records.length === 0" @click="exportJson">
            导出 JSON
          </button>
        </div>
      </header>

      <div class="table-wrap">
        <table v-if="records.length > 0">
          <thead>
            <tr>
              <th>时间</th>
              <th>观众</th>
              <th class="col-text">消息</th>
              <th>类别</th>
              <th>类别概率</th>
              <th>条件概率</th>
              <th>优先级</th>
              <th>去向</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.id">
              <td class="mono">{{ r.time }}</td>
              <td>{{ r.author }}</td>
              <td class="col-text">{{ r.text }}</td>
              <td>
                <span class="chip" :class="`chip-${catOf(r).id}`">{{ catOf(r).name }}</span>
              </td>
              <td class="mono">
                {{ (r.decision.choice.probabilities[r.decision.choice.category] * 100).toFixed(1) }}%
              </td>
              <td class="mono">{{ (r.decision.noul.probability * 100).toFixed(1) }}%</td>
              <td class="mono">{{ r.decision.score.value.toFixed(2) }}</td>
              <td>
                <span class="badge badge-plain">{{
                  TARGET_NAMES[r.disposition.target] ?? '留在弹幕区'
                }}</span>
              </td>
              <td>
                <span class="badge" :class="r.done ? 'badge-plain' : 'badge-ok'">
                  {{ r.done ? '已处理' : '待处理' }}
                </span>
              </td>
              <td><span class="link" @click="ui.openDrawer(r)">详情</span></td>
            </tr>
          </tbody>
        </table>

        <div v-else class="empty">
          <div class="empty-icon">📋</div>
          暂无判断记录。回到「课堂互动」开始直播或手动发送弹幕，<br />
          每条消息的类别、概率、优先级与去向都会记录在这里。
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.records {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card {
  flex: none;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  padding: 16px 18px;
}
h2 { font-size: 15.5px; font-weight: 800; }
.rules-head, .table-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 13px;
  flex-wrap: wrap;
}
.rules-head p, .table-head p { margin-top: 3px; font-size: 12px; color: var(--text-3); }
.threshold-badges, .table-actions { display: flex; gap: 8px; align-items: center; }

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.rule-item {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #fbfcfe;
}
.rule-desc { font-size: 12px; color: var(--text-2); line-height: 1.5; flex: 1; }
.rule-route {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-2);
}
.rule-route b { color: var(--primary-deep); font-size: 12.5px; }

.score-legend {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-2);
}
.legend-title { font-weight: 700; }
.legend-item b {
  display: inline-block;
  min-width: 16px;
  text-align: center;
  background: #f2f5fa;
  border-radius: 4px;
  margin-right: 3px;
  font-size: 11px;
  color: var(--primary-deep);
}

.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}
th {
  text-align: left;
  padding: 8px 10px;
  color: var(--text-3);
  font-size: 11.5px;
  font-weight: 700;
  border-bottom: 1px solid var(--border-strong);
  white-space: nowrap;
}
td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  vertical-align: middle;
}
tr:hover td { background: #f8faff; }
.col-text { max-width: 260px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mono { font-variant-numeric: tabular-nums; white-space: nowrap; }
.btn {
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  font-weight: 700;
  transition: all 0.18s;
}
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn.ghost {
  color: var(--text-2);
  border: 1px solid var(--border-strong);
  background: #fff;
}
.btn.ghost:not(:disabled):hover { border-color: var(--primary); color: var(--primary-deep); }
.btn.solid {
  color: #fff;
  background: linear-gradient(135deg, #4f8bff, var(--primary));
  box-shadow: 0 3px 10px rgba(47, 107, 255, 0.28);
}
.btn.solid:not(:disabled):hover { transform: translateY(-1px); }
</style>
