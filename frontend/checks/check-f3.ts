// F3 검사: 05-messages SSE 예시 원문(+ping)이 파서를 통과해 순서·타입이 맞고 final이 Message로 읽힌다.
// 04-conversations 상세·생성 예시가 타입을 통과한다.
import assert from 'node:assert/strict'
import {
  createSseParser, parseConversationDetail, parseConversationSummary, parseSseBlock,
  type ConversationDetail, type Message, type StreamEvent,
} from '../src/api.ts'
import { blocks, jsonBlock } from './contract.ts'

const [, stream, errorStream] = blocks('05-messages.md')
const withPing = stream.replace('event: tool_call', ': ping\n\nevent: tool_call')

// 일부러 7바이트씩 잘라 넣어 청크 경계를 흉내낸다
const feed = createSseParser()
const events: StreamEvent[] = []
for (let i = 0; i < withPing.length; i += 7) events.push(...feed(withPing.slice(i, i + 7)))
events.push(...feed('\n\n'))

assert.deepEqual(events.map((e) => e.event), ['message_created', 'tool_call', 'tool_result', 'final'])
const [created, call, result, final] = events
assert(created.event === 'message_created' && created.data.assistantMessageId === 44 && created.data.userMessage.role === 'user')
assert(call.event === 'tool_call' && call.data.status === 'running' && call.data.resultSummary === null && call.data.durationMs === null)
assert(result.event === 'tool_result' && result.data.id === call.data.id && result.data.status === 'succeeded')
assert(final.event === 'final')
const m: Message = final.data
assert.equal(m.id, 44)
assert.equal(m.status, 'completed')
assert.equal(m.toolCalls.length, 1)
assert.equal(m.usage?.costUsd, 0.0484)

const err = parseSseBlock(errorStream)
assert(err?.event === 'error' && err.data.error.code === 'UPSTREAM_ERROR' && err.data.assistantMessageId === 44)
assert.equal(parseSseBlock(': ping\n'), null)

// 01-common의 SSE 형식 예시(tool_call 하나)
const common = blocks('01-common.md').find((b) => b.startsWith('event: tool_call'))
assert(common)
assert.equal(parseSseBlock(common)?.event, 'tool_call')

// 04-conversations: [0] 목록, [1] 생성 응답, [2] 상세
const createdConv = parseConversationSummary(jsonBlock('04-conversations.md', 1))
assert.equal(createdConv.title, '장바구니 개선 측정 설계')
const detail: ConversationDetail = parseConversationDetail(jsonBlock('04-conversations.md', 2))
assert.deepEqual(detail.messages.map((x) => x.role), ['user', 'assistant'])
assert.equal(detail.messages[1].proposals[0].type, 'improvement')

// 실행 중 메시지 규칙: content "", proposals [], usage null 이 통과한다
const running = parseConversationDetail({ ...detail, messages: [{ ...detail.messages[1], status: 'running', content: '', proposals: [], usage: null }] })
assert.equal(running.messages[0].status, 'running')
