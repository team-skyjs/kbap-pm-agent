// F2 검사: 04-conversations 목록 예시가 타입을 통과하고, title null 항목은 "새 대화"로 보인다.
import assert from 'node:assert/strict'
import { parseConversationList, type ConversationSummary } from '../src/api.ts'
import { displayTitle } from '../src/ConversationList.tsx'
import { jsonBlock } from './contract.ts'

const { items }: { items: ConversationSummary[] } = parseConversationList(jsonBlock('04-conversations.md', 0))
assert.deepEqual(items.map((c) => c.id), [7, 6])
assert.equal(displayTitle(items[0]), '스캔 퍼널 이탈 지점 개선안')
assert.equal(items[1].title, null)
assert.equal(displayTitle(items[1]), '새 대화')
assert.equal(items[0].adoptedCount, 1)

// items 감싸기 없는 맨 배열은 거부
assert.throws(() => parseConversationList([]))
