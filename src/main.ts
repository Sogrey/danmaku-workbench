import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import type { DanmakuMessage, WorkRecord } from '@/types'
import { loadSnapshot, saveSnapshot, type PersistSnapshot } from './utils/persist'
import { useTodoStore } from './stores/todo'
import { useWorkbenchStore } from './stores/workbench'
import './assets/styles/variables.css'
import './assets/styles/base.css'

/**
 * 启动流程：先恢复 IndexedDB 快照（如有），再挂载应用——
 * 避免页面先渲染空态再闪现历史数据。
 *
 * 持久化写入：订阅 workbench/todo 两个 store 的任意 state 变更，
 * debounce 400ms 后整存快照；todo 队列不入库（由 records 重建）。
 */
async function bootstrap() {
  const pinia = createPinia()
  const app = createApp(App)
  app.use(pinia)

  const wb = useWorkbenchStore(pinia)
  const todo = useTodoStore(pinia)

  const snap = await loadSnapshot()
  if (snap) wb.$hydrate(snap)

  let saveTimer: ReturnType<typeof setTimeout> | undefined
  const scheduleSave = () => {
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      // store state 是 Vue reactive proxy，IndexedDB 结构化克隆无法处理 Proxy：
      // 先 JSON round-trip 转纯对象再入库（undefined 可选字段序列化后缺失，语义不变）
      const snapshot: PersistSnapshot = {
        version: 1,
        savedAt: new Date().toISOString(),
        messages: JSON.parse(JSON.stringify(wb.messages)) as DanmakuMessage[],
        records: JSON.parse(JSON.stringify(wb.records)) as WorkRecord[],
        liveElapsed: wb.liveElapsed,
      }
      void saveSnapshot(snapshot)
    }, 400)
  }
  // todo.markDone 会修改共享 record.done，deep watch 同样会触发 workbench 订阅；两边都挂，双保险
  wb.$subscribe(scheduleSave)
  todo.$subscribe(scheduleSave)

  app.mount('#app')
}

void bootstrap()
