/**
 * UI store：视图切换 + 判断详情抽屉
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WorkRecord } from '@/types'

export type ViewName = 'classroom' | 'records'

export const useUiStore = defineStore('ui', () => {
  const activeView = ref<ViewName>('classroom')
  /** 判断详情抽屉当前展示的记录（null = 关闭） */
  const drawerRecord = ref<WorkRecord | null>(null)

  function switchView(view: ViewName) {
    activeView.value = view
  }

  function openDrawer(record: WorkRecord) {
    drawerRecord.value = record
  }

  function closeDrawer() {
    drawerRecord.value = null
  }

  return { activeView, drawerRecord, switchView, openDrawer, closeDrawer }
})
