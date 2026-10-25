/**
 * 课堂待办 store：讲师待答 / 助教处理 / 待确认 三个队列
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { RouteTarget, WorkRecord } from '@/types'

export type TodoTab = RouteTarget extends infer T
  ? T extends 'instructor' | 'assistant' | 'confirm' ? T
  : never
  : never

export const useTodoStore = defineStore('todo', () => {
  const instructor = ref<WorkRecord[]>([])
  const assistant = ref<WorkRecord[]>([])
  const confirm = ref<WorkRecord[]>([])
  const activeTab = ref<'instructor' | 'assistant' | 'confirm'>('instructor')

  /** 队列内排序：Score 优先级从高到低，同分按进入顺序（时间） */
  function sortQueue(list: WorkRecord[]) {
    list.sort((a, b) => {
      if (b.decision.score.value !== a.decision.score.value) {
        return b.decision.score.value - a.decision.score.value
      }
      return a.time < b.time ? -1 : 1
    })
  }

  function pushRecord(record: WorkRecord) {
    const map = { instructor, assistant, confirm } as const
    const queue = map[record.disposition.target as 'instructor' | 'assistant' | 'confirm']
    if (queue) {
      queue.value.push(record)
      sortQueue(queue.value)
    }
  }

  function markDone(id: string) {
    for (const queue of [instructor, assistant, confirm]) {
      const idx = queue.value.findIndex((r) => r.id === id)
      if (idx >= 0) {
        const [record] = queue.value.splice(idx, 1)
        record.done = true
        return
      }
    }
  }

  /**
   * 从全量记录重建队列（持久化恢复时调用）：
   * 队列 = records 中 target≠none 且未标记完成的子集，排序规则与实时一致。
   */
  function rehydrate(records: WorkRecord[]) {
    $reset()
    for (const r of records) {
      if (r.disposition?.target && r.disposition.target !== 'none' && !r.done) {
        pushRecord(r)
      }
    }
  }

  const activeQueue = computed(() => {
    const map = { instructor, assistant, confirm } as const
    return map[activeTab.value].value
  })

  const counts = computed(() => ({
    instructor: instructor.value.length,
    assistant: assistant.value.length,
    confirm: confirm.value.length,
    total: instructor.value.length + assistant.value.length + confirm.value.length,
  }))

  function $reset() {
    instructor.value = []
    assistant.value = []
    confirm.value = []
    activeTab.value = 'instructor'
  }

  return {
    instructor,
    assistant,
    confirm,
    activeTab,
    activeQueue,
    counts,
    pushRecord,
    markDone,
    rehydrate,
    $reset,
  }
})
