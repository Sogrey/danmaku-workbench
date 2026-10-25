<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import CalibrationView from '@/components/pages/CalibrationView.vue'
import ClassroomView from '@/components/pages/ClassroomView.vue'
import RecordsView from '@/components/pages/RecordsView.vue'
import DecisionDrawer from '@/components/DecisionDrawer.vue'
import { useUiStore } from '@/stores/ui'
import { useWorkbenchStore } from '@/stores/workbench'

const ui = useUiStore()
const wb = useWorkbenchStore()
</script>

<template>
  <div class="app-shell">
    <AppHeader />

    <main class="app-main">
      <ClassroomView v-if="ui.activeView === 'classroom'" />
      <RecordsView v-else-if="ui.activeView === 'records'" />
      <CalibrationView v-else />
    </main>

    <footer class="app-footer">
      <span>© 2026 Jev 直播弹幕工作台 · 模型判断 / 程序分流 / 人员跟进</span>
      <span v-if="wb.totalCount > 0">
        已完成 {{ wb.judgedCount }} 条弹幕的判断与分流<template v-if="wb.failedCount > 0">，{{ wb.failedCount }} 条待重试</template>
      </span>
      <span v-else>决策引擎：{{ wb.providerDesc }}</span>
    </footer>

    <DecisionDrawer />
  </div>
</template>
