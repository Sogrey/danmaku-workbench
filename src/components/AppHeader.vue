<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
import { useWorkbenchStore } from '@/stores/workbench'

const ui = useUiStore()
const wb = useWorkbenchStore()

function toggleLive() {
  wb.liveRunning ? wb.stopLive() : wb.startLive()
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <!-- logo -->
      <div class="logo">
        <span class="logo-mark">J</span>
        <span class="logo-text">Jev <em>直播弹幕工作台</em></span>
      </div>

      <!-- 导航 -->
      <nav class="nav">
        <button
          class="nav-item"
          :class="{ active: ui.activeView === 'classroom' }"
          @click="ui.switchView('classroom')"
        >
          课堂互动
        </button>
        <button
          class="nav-item"
          :class="{ active: ui.activeView === 'records' }"
          @click="ui.switchView('records')"
        >
          分类与记录
        </button>
        <button
          class="nav-item"
          :class="{ active: ui.activeView === 'calibration' }"
          @click="ui.switchView('calibration')"
        >
          校准与阈值
        </button>
      </nav>

      <!-- 状态 + 操作 -->
      <div class="status">
        <span class="badge badge-ok">
          <span class="chip-dot"></span>
          弹幕分类已配置
        </span>
        <button class="btn-live" :class="{ running: wb.liveRunning }" @click="toggleLive">
          {{ wb.liveRunning ? '暂停直播' : '开始' }}
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  flex: none;
  height: var(--header-h);
  background: #fff;
  border-bottom: 1px solid var(--border);
}
.header-inner {
  height: 100%;
  margin: 0 auto;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 22px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 9px;
}
.logo-mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(135deg, #60a5fa, var(--primary));
  color: #fff;
  font-weight: 800;
  font-size: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(47, 107, 255, 0.28);
}
.logo-text {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}
.logo-text em {
  font-style: normal;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-2);
  margin-left: 4px;
}
.nav {
  display: flex;
  gap: 4px;
  height: 100%;
}
.nav-item {
  position: relative;
  padding: 0 14px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-2);
  transition: color 0.2s;
}
.nav-item:hover {
  color: var(--text);
}
.nav-item.active {
  color: var(--primary-deep);
}
.nav-item.active::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 3px;
  border-radius: 3px 3px 0 0;
  background: var(--primary);
}
.status {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-live {
  padding: 7px 22px;
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #4f8bff, var(--primary));
  box-shadow: 0 4px 12px rgba(47, 107, 255, 0.32);
  transition: all 0.2s;
}
.btn-live:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(47, 107, 255, 0.4);
}
.btn-live.running {
  background: #f2f5fa;
  color: var(--text-2);
  box-shadow: none;
  border: 1px solid var(--border-strong);
}
</style>
