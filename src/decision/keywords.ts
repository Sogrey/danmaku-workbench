/**
 * Mock 决策引擎的关键词规则
 *
 * 说明：这只是「模型未接入前」的占位实现，用于跑通端到端流程与 UI。
 * 真实接入后此文件将被 Jev/Laya 等 Provider 替代，规则不进入生产。
 */
import type { CategoryId } from '@/types'

export const KEYWORDS: Record<CategoryId, string[]> = {
  technical: [
    '怎么', '如何', '为什么', '？', '?', '报错', 'error', 'Error', 'ERROR',
    '安装', '配置', '代码', 'sdk', 'SDK', 'api', 'API', '调用', '区别', '差别',
    '是什么', '能不能', '支持', '语法', '异常', 'failed', 'install', 'print',
    'module', 'import', '能写', '会写', '输出', '异步', '同步', '解码', '延迟',
    'token', '概率', '分类', '阈值', '接口', '请求', '回复', '写出', '生成',
  ],
  feedback: [
    '声音', '音量', '画面', '黑屏', '卡', '字幕', '字号', '太小', '放大',
    '断', '麦克风', '听不清', '太小了', '闪退', '看不到', '调高', '调大',
    '没声音', '听不到', '断流', '延迟高', '糊了', '花屏',
  ],
  spam: [
    '微信', 'vx', 'VX', '加群', '领取', '链接', '优惠', '兼职', '赚钱',
    '免费领', '私聊', '推广', '点击', '下单',
  ],
  chat: [
    '你好', '哈哈', '嘿嘿', '666', '不错', '赞', '厉害', '辛苦', '谢谢',
    '看懂了', '明白了', '学到', '支持老师', '牛',
  ],
  insufficient: ['这个', '那个', '刚才', '它', '他', '这', '那', '刚才你说的'],
}

/** 高影响关键词（Score 提分项） */
export const HIGH_IMPACT = [
  '黑屏', '断流', '没声音', '听不到', '无法', '装不上', '报错', '失败',
  'failed', '不能运行', '卡死',
]

/** 统计文本对某关键词列表的命中数 */
export function countHits(text: string, words: string[]): number {
  let n = 0
  for (const w of words) {
    if (text.includes(w)) n++
  }
  return n
}

export function formatClock(date: Date): string {
  const p = (x: number) => String(x).padStart(2, '0')
  return `${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
}
