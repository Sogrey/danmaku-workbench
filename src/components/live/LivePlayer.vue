<script setup lang="ts">
import { computed } from 'vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

const TOTAL_SECONDS = 33

/** 直播窗内漂浮的弹幕（最近 9 条，三轨道轮转） */
const floating = computed(() => wb.messages.slice(-9).map((m, i) => ({
  ...m,
  lane: i % 3,
  duration: 6.5 + ((i * 7) % 5) * 0.6, // 6.5~8.9s，伪随机不重样
})))

const progress = computed(() => ((wb.liveElapsed % TOTAL_SECONDS) / TOTAL_SECONDS) * 100)

const clock = computed(() => {
  const s = TOTAL_SECONDS
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})

function toggleLive() {
  wb.liveRunning ? wb.stopLive() : wb.startLive()
}
</script>

<template>
  <div class="player" :class="{ paused: !wb.liveRunning }">
    <!-- 封面 -->
    <div class="cover">
      <div class="cover-badge">
        <span class="badge badge-live" v-if="wb.liveRunning"><span class="chip-dot"></span>LIVE</span>
        <span class="badge badge-plain" v-else>未开始</span>
      </div>

      <div class="cover-title">
        <h2>Jev：让判断进入业务流程</h2>
        <p>从判断到执行，连接真实的业务场景</p>
      </div>

      <!-- 弹幕轨道 -->
      <div class="danmaku-layer" v-if="wb.liveRunning || floating.length">
        <span
          v-for="m in floating"
          :key="m.id"
          class="danmaku-float"
          :style="{ top: 14 + m.lane * 22 + 'px', '--dur': m.duration + 's' }"
        >
          {{ m.text }}
        </span>
      </div>

      <div class="cover-clock">{{ clock }}</div>
    </div>

    <!-- 控制条 -->
    <div class="controls">
      <button class="ctl-btn" :title="wb.liveRunning ? '暂停' : '播放'" @click="toggleLive">
        <svg v-if="!wb.liveRunning" viewBox="0 0 16 16" width="14" height="14">
          <path d="M4 2.5v11l9-5.5z" fill="currentColor" />
        </svg>
        <svg v-else viewBox="0 0 16 16" width="14" height="14">
          <rect x="3.5" y="3" width="3" height="10" rx="1" fill="currentColor" />
          <rect x="9.5" y="3" width="3" height="10" rx="1" fill="currentColor" />
        </svg>
      </button>

      <div class="progress">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <span class="time">0:00 / {{ clock }}</span>

      <span class="ctl-btn muted" title="音量">
        <svg viewBox="0 0 16 16" width="14" height="14">
          <path d="M2 6v4h3l4 3V3L5 6H2z" fill="currentColor" />
          <path d="M11 5.5a3.5 3.5 0 0 1 0 5" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linecap="round" />
        </svg>
      </span>
      <span class="ctl-btn muted" title="全屏">
        <svg viewBox="0 0 16 16" width="14" height="14">
          <path d="M2 6V2h4M14 6V2h-4M2 10v4h4M14 10v4h-4" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" />
        </svg>
      </span>
    </div>
  </div>
</template>

<style scoped>
.player {
  flex: none;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid #1b2b4d;
  background: #0b1526;
}
.cover {
  position: relative;
  aspect-ratio: 16 / 9;
  background:
    radial-gradient(120% 90% at 20% 0%, #1e3a8a 0%, transparent 55%),
    radial-gradient(100% 100% at 90% 100%, #2f6bff33 0%, transparent 50%),
    linear-gradient(135deg, #0d1830 0%, #101d3c 60%, #0b1526 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover-badge {
  position: absolute;
  top: 10px;
  left: 10px;
}
.cover-badge .badge { font-size: 11px; padding: 2px 8px; }
.cover-clock {
  position: absolute;
  top: 10px;
  right: 12px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.75);
  font-variant-numeric: tabular-nums;
}
.cover-title {
  text-align: center;
  padding: 0 18px;
  pointer-events: none;
}
.cover-title h2 {
  color: #fff;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 1px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.45);
}
.cover-title p {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
  letter-spacing: 2px;
}

/* 弹幕漂浮层 */
.danmaku-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.danmaku-float {
  position: absolute;
  left: 100%;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  text-shadow:
    0 0 4px rgba(0, 0, 0, 0.8),
    0 1px 2px rgba(0, 0, 0, 0.9);
  animation: danmaku-slide var(--dur, 8s) linear forwards;
}
@keyframes danmaku-slide {
  from { left: 100%; }
  to { left: -100%; }
}
.paused .danmaku-float {
  animation-play-state: paused;
  opacity: 0.6;
}

/* 控制条 */
.controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  background: rgba(8, 14, 28, 0.92);
}
.ctl-btn {
  color: #dbe4f5;
  display: inline-flex;
  align-items: center;
  padding: 2px;
}
.ctl-btn.muted { color: #7c8aa5; cursor: default; }
.progress {
  flex: 1;
  height: 4px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.14);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, #60a5fa, #2f6bff);
}
.time {
  font-size: 11px;
  color: #9fb0cc;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>
