// 검사: SSE 예시 원문(+ping)의 이벤트 순서·타입, final의 Message 파싱
// 대화 상세·생성 예시의 파서 통과
import assert from 'node:assert/strict'
import {
  errorText, parseErrorBody, createSseParser, parseConversationDetail, parseConversationSummary, parseSseBlock,
  type ConversationDetail, type Message, type StreamEvent,
} from '../src/api.ts'
import { blocks, jsonBlock } from './contract.ts'

// 블록 순서가 계약 추가로 바뀌어도 맞도록 내용으로 찾음
const all = blocks('05-messages.md')
const stream = all.find((b) => b.startsWith('event: message_created'))
const errorStream = all.find((b) => b.startsWith('event: error'))
assert(stream && errorStream)
const withPing = stream.replace('event: tool_call', ': ping\n\nevent: tool_call')

// 7바이트씩 잘라 넣어 청크 경계 재현
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

// 공통 SSE 형식 예시(tool_call 하나)
const common = blocks('01-common.md').find((b) => b.startsWith('event: tool_call'))
assert(common)
assert.equal(parseSseBlock(common)?.event, 'tool_call')

// 04-conversations.md 블록 순서: [0] 목록, [1] 생성 응답, [2] 상세
const createdConv = parseConversationSummary(jsonBlock('04-conversations.md', 1))
assert.equal(createdConv.title, '장바구니 개선 측정 설계')
const detail: ConversationDetail = parseConversationDetail(jsonBlock('04-conversations.md', 2))
assert.deepEqual(detail.messages.map((x) => x.role), ['user', 'assistant'])
assert.equal(detail.messages[1].proposals[0].type, 'improvement')

// 실행 중 메시지 형태(content "", proposals [], usage null) 통과
const running = parseConversationDetail({ ...detail, messages: [{ ...detail.messages[1], status: 'running', content: '', proposals: [], usage: null }] })
assert.equal(running.messages[0].status, 'running')

// 사전 점검 거절(503 AMPLITUDE_UNAVAILABLE): 계약 예시가 에러 파서를 통과하고 이유 문구가 그대로 남음
const amp = all.map((b) => b.trim()).find((b) => b.includes('"AMPLITUDE_UNAVAILABLE"'))
assert(amp)
const ampErr = parseErrorBody(JSON.parse(amp))
assert.equal(ampErr.error.code, 'AMPLITUDE_UNAVAILABLE')
assert(ampErr.error.message.startsWith('Amplitude 조회 불가: '))
assert(errorText(ampErr.error.code).startsWith('Amplitude를 조회할 수 없습니다.'))
