<script setup lang="ts">
import LivePanel from '@/components/live/LivePanel.vue'
import ProcessingPanel from '@/components/processing/ProcessingPanel.vue'
import TodoPanel from '@/components/todo/TodoPanel.vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()
</script>

<template>
  <div class="classroom">
    <!-- 标题区 -->
    <div class="titlebar">
      <h1>Jev 体验营 · 直播课堂</h1>
      <p>查看观众提问，跟进听课问题，安排讲师与助教处理。</p>
    </div>

    <!-- 三栏工作区 -->
    <div class="workspace">
      <LivePanel />
      <ProcessingPanel />
      <TodoPanel />
    </div>
  </div>
</template>

<style scoped>
.classroom {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.titlebar h1 {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.5px;
}
.titlebar p {
  margin-top: 3px;
  font-size: 13px;
  color: var(--text-3);
}
.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.04fr 1.16fr 0.92fr;
  gap: 14px;
}
@media (max-width: 1100px) {
  .workspace {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}
</style>
