/**
 * 工作台主 store：弹幕流、判断流程、记录
 *
 * 生命周期：消息进入 → judging → Provider 决策 → 路由分流 → 待办/记录
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { CategoryId, DanmakuMessage, DecisionResult, Disposition, WorkRecord } from '@/types'
import { getProvider, DecisionEngineError } from '@/decision'
import { routeDecision } from '@/decision/routing'
import { SCORE_LEVEL_NAMES } from '@/config/criteria'
import { formatClock } from '@/decision/keywords'
import { useTodoStore } from './todo'

let seq = 0
const nextId = () => `msg-${++seq}`

/** 模拟弹幕池（课程截图同款场景） */
const SEED_DANMAKU: string[] = [
  '你好',
  '老师，你的声音有点小',
  'Jev 会自己写出一段回复吗',
  '这个怎么弄',
  '这个例子终于看懂了',
  '分类结果怎么接业务？',
  'SDK 异步调用和同步调用有什么差别',
  '终端的字太小了，麻烦放大一点',
  '刚才你说的那里',
  '麦克风没声音，背景音乐能听见',
  '老师黑屏了，直播好像断了',
  '加我微信，免费领取 Jev 源码',
  '哈哈哈，讲得不错',
  'print(1) 这种代码是用什么语言写的',
  '安装 SDK 的时候一直报错，装不上',
  '666，这个阈值设计讲明白了',
]

function normalizeDecision(d: DecisionResult): DecisionResult {
  if (!d.score.level) d.score.level = SCORE_LEVEL_NAMES[d.score.levelIndex] ?? '正常答疑'
  return d
}

export const useWorkbenchStore = defineStore('workbench', () => {
  // ---------- state ----------
  const messages = ref<DanmakuMessage[]>([])
  /** 'all' | 'technical' */
  const filter = ref<'all' | 'technical'>('all')
  const following = ref(true)
  const liveRunning = ref(false)
  const liveElapsed = ref(0)
  const selectedId = ref<string | null>(null)
  /** 全量判断记录（分类与记录页数据源） */
  const records = ref<WorkRecord[]>([])
  /** 决策引擎说明 */
  const providerDesc = ref(getProvider().describe())

  let simulatorTimer: ReturnType<typeof setTimeout> | null = null
  let clockTimer: ReturnType<typeof setInterval> | null = null

  // ---------- getters ----------
  const visibleMessages = computed(() => {
    const list = messages.value
    if (filter.value === 'all') return list
    // 只看技术提问：技术类 + 判断中的（避免新消息被过滤后不可见）
    return list.filter((m) => m.status === 'judging' || m.label === 'technical')
  })

  const currentMessage = computed(
    () => messages.value.find((m) => m.id === selectedId.value) ?? null,
  )

  const totalCount = computed(() => messages.value.length)
  const judgedCount = computed(
    () => messages.value.filter((m) => m.status === 'done').length,
  )
  const failedCount = computed(
    () => messages.value.filter((m) => m.status === 'failed').length,
  )

  // ---------- actions ----------
  function pushMessage(text: string, manual = false) {
    const trimmed = text.trim()
    if (!trimmed) return null
    const msg: DanmakuMessage = {
      id: nextId(),
      author: '现场观众',
      time: formatClock(new Date()),
      text: trimmed,
      status: 'pending',
      manual,
    }
    messages.value.push(msg)
    if (following.value) selectedId.value = msg.id
    // 进入即自动判断（对齐原工作台：消息流入 → 判断 → 分流）
    judgeMessage(msg.id)
    return msg
  }

  async function judgeMessage(id: string) {
    const msg = messages.value.find((m) => m.id === id)
    if (!msg || msg.status === 'judging' || msg.status === 'done') return

    msg.status = 'judging'
    selectedId.value = msg.id
    const provider = getProvider()

    try {
      const decision = normalizeDecision(await provider.decide(msg))
      const disposition = routeDecision(decision)

      msg.decision = decision
      msg.disposition = disposition
      msg.label = decision.choice.category
      msg.status = 'done'

      // 全量记录
      const record: WorkRecord = {
        id: msg.id,
        time: msg.time,
        author: msg.author,
        text: msg.text,
        decision,
        disposition,
        done: false,
      }
      records.value.push(record)

      // 分流进待办（普通聊天 target='none' 保留在弹幕区）
      if (disposition.target !== 'none') {
        useTodoStore().pushRecord(record)
      }
    } catch (err) {
      msg.status = 'failed'
      if (!(err instanceof DecisionEngineError)) {
        console.error('[workbench] judge failed:', err)
      }
    }
  }

  function retryMessage(id: string) {
    const msg = messages.value.find((m) => m.id === id)
    if (!msg || msg.status !== 'failed') return
    msg.status = 'pending'
    judgeMessage(id)
  }

  /** 模拟一条失败（演示失败降级：保留原文、可稍后重试） */
  function simulateFailure(id: string) {
    const msg = messages.value.find((m) => m.id === id)
    if (msg) {
      Object.assign(msg, { forceError: true })
      msg.status = 'pending'
      judgeMessage(id)
    }
  }

  function selectMessage(id: string) {
    selectedId.value = id
  }

  // ---------- 直播模拟器 ----------
  function startLive() {
    if (liveRunning.value) return
    liveRunning.value = true
    scheduleNext()
    clockTimer = setInterval(() => {
      liveElapsed.value++
    }, 1000)
  }

  function stopLive() {
    liveRunning.value = false
    if (simulatorTimer) {
      clearTimeout(simulatorTimer)
      simulatorTimer = null
    }
    if (clockTimer) {
      clearInterval(clockTimer)
      clockTimer = null
    }
  }

  function scheduleNext() {
    if (!liveRunning.value) return
    const delay = 4000 + Math.random() * 6000 // 4~10s 一条
    simulatorTimer = setTimeout(() => {
      const pool = SEED_DANMAKU.filter(
        (t) => !messages.value.some((m) => m.text === t && m.status === 'done'),
      )
      const candidates = pool.length ? pool : SEED_DANMAKU
      const text = candidates[Math.floor(Math.random() * candidates.length)]
      pushMessage(text)
      scheduleNext()
    }, delay)
  }

  /** 重置整场直播 */
  function resetAll() {
    stopLive()
    messages.value = []
    records.value = []
    selectedId.value = null
    liveElapsed.value = 0
    useTodoStore().$reset()
  }

  return {
    // state
    messages,
    filter,
    following,
    liveRunning,
    liveElapsed,
    selectedId,
    records,
    providerDesc,
    // getters
    visibleMessages,
    currentMessage,
    totalCount,
    judgedCount,
    failedCount,
    // actions
    pushMessage,
    judgeMessage,
    retryMessage,
    simulateFailure,
    selectMessage,
    startLive,
    stopLive,
    resetAll,
  }
})
