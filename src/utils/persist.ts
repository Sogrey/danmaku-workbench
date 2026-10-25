/**
 * 工作台持久化：IndexedDB 快照存取
 *
 * 设计：
 *  - 单 key 快照（messages + records + liveElapsed），量级 KB 级，整存整取
 *  - todo 队列不入库——它是 records 的子集（target≠none 且未 done），
 *    恢复时由 records 重建，保证两侧永远一致
 *  - 带版本号，结构升级时不兼容的旧快照直接丢弃重建
 *  - IndexedDB 不可用（隐私模式等）时静默降级为「不持久化」，不阻断主流程
 */
import type { DanmakuMessage, WorkRecord } from '@/types'

const DB_NAME = 'danmaku-workbench'
const DB_VERSION = 1
const STORE_NAME = 'workbench'
const KEY = 'snapshot'

/** 快照结构版本：字段语义变更时 +1，旧数据自动失效 */
const SCHEMA_VERSION = 1

export interface PersistSnapshot {
  version: number
  savedAt: string
  messages: DanmakuMessage[]
  records: WorkRecord[]
  liveElapsed: number
}

let dbPromise: Promise<IDBDatabase | null> | null = null

function openDb(): Promise<IDBDatabase | null> {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve) => {
    if (typeof indexedDB === 'undefined') {
      resolve(null)
      return
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => resolve(null) // 打不开就降级：不持久化
  })
  return dbPromise
}

let warnedWriteFailed = false

/** 保存快照（覆盖写）。失败仅告警一次——持久化不阻断业务流程，但不可完全不可观测。 */
export async function saveSnapshot(snapshot: PersistSnapshot): Promise<void> {
  try {
    const db = await openDb()
    if (!db) return
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put(snapshot, KEY)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
      tx.onabort = () => reject(tx.error)
    })
  } catch (err) {
    if (!warnedWriteFailed) {
      warnedWriteFailed = true
      console.warn('[persist] 快照写入 IndexedDB 失败，本次会话不再持久化：', err)
    }
  }
}

/** 读取快照；无数据 / 版本不兼容 / 结构异常返回 null。 */
export async function loadSnapshot(): Promise<PersistSnapshot | null> {
  try {
    const db = await openDb()
    if (!db) return null
    const data = await new Promise<PersistSnapshot | null>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const req = tx.objectStore(STORE_NAME).get(KEY)
      req.onsuccess = () => resolve((req.result as PersistSnapshot | undefined) ?? null)
      req.onerror = () => reject(req.error)
    })
    if (!data) return null
    if (data.version !== SCHEMA_VERSION) return null
    if (!Array.isArray(data.messages) || !Array.isArray(data.records)) return null
    return data
  } catch {
    return null
  }
}

/** 清空快照（重置整场直播时调用）。 */
export async function clearSnapshot(): Promise<void> {
  try {
    const db = await openDb()
    if (!db) return
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).delete(KEY)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // 静默
  }
}
