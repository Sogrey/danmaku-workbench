<script setup lang="ts">
import LivePlayer from './LivePlayer.vue'
import DanmakuList from './DanmakuList.vue'
import MessageInput from './MessageInput.vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div>
        <div class="panel-title"><span class="no">01</span> 直播画面与弹幕</div>
      </div>
      <span class="badge" :class="wb.liveRunning ? 'badge-live' : 'badge-plain'">
        <span v-if="wb.liveRunning" class="chip-dot"></span>
        {{ wb.liveRunning ? `直播中 · 本场 ${wb.totalCount} 条` : '已就绪 · 本场 ' + wb.totalCount + ' 条' }}
      </span>
    </header>

    <LivePlayer />
    <DanmakuList />
    <MessageInput />
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card);
  padding: 14px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
