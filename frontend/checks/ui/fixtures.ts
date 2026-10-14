// 고정 응답: 계약 분할본 예시 JSON과 05-messages SSE 예시로 만든 시나리오. 항상 가로채고,
// CHECK_UI_LIVE=1은 mockApi를 부르지 않는 live 전용 테스트만 실제 백엔드로 돌게 함
import type { Page, Route } from '@playwright/test'
import { blocks, jsonBlock } from '../contract.ts'

export const LIVE = process.env.CHECK_UI_LIVE === '1'

// hang: 응답을 보내지 않고 요청을 열어 둠(스트림 진행 중 화면)
// token: 백엔드 공유 토큰 401(계약 JSON UNAUTHORIZED), expired: 접근 계층 로그인 HTML 401
export type Scenario = 'sent' | 'progress' | 'done' | 'partial' | 'error' | 'token' | 'expired' | 'hang'

type Json = Record<string, unknown>
const clone = <T>(v: T): T => structuredClone(v)
const obj = (v: unknown): Json => (typeof v === 'object' && v !== null && !Array.isArray(v) ? Object.fromEntries(Object.entries(v)) : {})
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const isJson = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v)

// 계약 예시
export const HEALTH = jsonBlock('03-health.md', 0)
export const LIST = obj(jsonBlock('04-conversations.md', 0))
export const CREATED = obj(jsonBlock('04-conversations.md', 1))
export const DETAIL = obj(jsonBlock('04-conversations.md', 2))
export const PROPOSAL = obj(jsonBlock('02-objects.md', 2))
export const SETTINGS = jsonBlock('02-objects.md', 3)

const CHART_DIR = new URL('../../../specs/003-frontend-redesign/contracts/', import.meta.url)
const CHART_EXAMPLES = blocks('chart-block.md', CHART_DIR).flatMap((b) => b.split('\n').filter((l) => l.startsWith('{')))

// 마크다운 표본 답변: 요소 전부 + 차트 예시 세 개(선·막대·형식 오류)
export const MARKDOWN_SAMPLE = [
  '# 제목 1', '## 제목 2', '### 제목 3', '#### 제목 4', '',
  '본문 **강조**와 `인라인 코드`, [링크](https://example.com/docs), <script>window.__xss = 1</script>', '',
  '완료 비율이 **41%**로 낮다', '',
  '- 항목 A', '- 항목 B', '', '1. 첫째', '2. 둘째', '', '- [x] 끝난 일', '- [ ] 남은 일', '',
  '| 이벤트 | 7일 사용자 | 30일 사용자 | 전환율 | 비고 |', '|---|---|---|---|---|',
  '| scan_start | 2,418 | 9,870 | 41.3% | 아주 긴 비고 문장이 들어가 표가 화면보다 넓어지는 경우를 만든다 |', '',
  '> 인용 문단', '', '---', '',
  '```ts', 'track(EVENTS.scan_retry_tap, { fail_reason })', '```', '',
  ...CHART_EXAMPLES.flatMap((c) => ['```chart', c, '```', '']),
].join('\n')

const now = () => new Date().toISOString()
const sse = (events: [string, unknown][]) => events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join('')

// 05-messages SSE 예시의 이벤트를 원형으로 사용
const SSE_EXAMPLE = blocks('05-messages.md')[1].split('\n\n').filter(Boolean).map((b) => {
  const [ev, data] = b.split('\n')
  return [ev.slice('event: '.length), obj(JSON.parse(data.slice('data: '.length)))] as const
})
const exampleEvent = (name: string) => clone(SSE_EXAMPLE.find(([e]) => e === name)?.[1] ?? {})

export const PARTIAL_PREFIX = '모델 호출 상한(10턴)에 도달해 여기까지의 조회 결과로 답합니다.'

type Options = {
  scenario?: Scenario
  assistantContent?: string
  // 대화 목록 대체 (기본: 계약 예시 두 개)
  list?: Json[]
  // 진행 시나리오에서 첫 상세 재조회 뒤 완료로 전환
  completeAfterPoll?: boolean
}

// 대화 7(계약 상세 예시, 제안 두 개) + 전송 시나리오. 다른 대화는 빈 상태로 시작
// 전송·제안 결정은 상세에 저장되어 새로고침 뒤에도 유지
export async function mockApi(page: Page, opts: Options = {}): Promise<void> {
  const scenario = opts.scenario ?? 'done'
  const detail = clone(DETAIL)
  const seeded = arr(detail.messages).map(obj)
  const seededAssistant = seeded.find((m) => m.role === 'assistant')
  if (seededAssistant) {
    if (opts.assistantContent !== undefined) seededAssistant.content = opts.assistantContent
    // 계약 상세 예시의 개선 제안에 Proposal 예시(측정 설계, 근거 3종)를 더하고 결정은 미결정으로 시작
    const funnel = { ...clone(PROPOSAL), id: 15, seq: 2, messageId: seededAssistant.id, decision: { status: 'pending', note: null, decidedAt: null } }
    seededAssistant.proposals = [...arr(seededAssistant.proposals), funnel]
  }
  const threads = new Map<number, Json[]>([[7, seeded]])
  const thread = (id: number) => threads.get(id) ?? threads.set(id, []).get(id) ?? []
  // 저장 상태를 바꿔야 해서 복사 없이 원본 객체를 찾음
  const allProposals = () => [...threads.values()].flat().flatMap((m) => arr(m.proposals).filter(isJson))
  let readsAfterSend = -1
  let nextId = 900

  await page.route('**/api/**', async (route: Route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname.slice(url.pathname.indexOf('/api/'))
    const method = req.method()
    const json = (status: number, body: unknown) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

    if (method === 'GET' && path === '/api/health') return json(200, HEALTH)
    if (method === 'GET' && path === '/api/settings') return json(200, SETTINGS)
    if (method === 'GET' && path === '/api/conversations') return json(200, opts.list ? { items: opts.list } : LIST)
    if (method === 'POST' && path === '/api/conversations') return json(201, CREATED)
    if (method === 'GET' && /^\/api\/conversations\/\d+$/.test(path)) {
      const id = Number(path.split('/').pop())
      const msgs = thread(id)
      // 전송 직후 재조회(스트림 종료 시)는 진행 상태로, 그 다음 주기 재조회부터 완료
      if (opts.completeAfterPoll && readsAfterSend >= 0 && ++readsAfterSend > 1) {
        for (const m of msgs) if (m.status === 'running') Object.assign(m, { status: 'completed', content: String(exampleEvent('final').content), toolCalls: arr(m.toolCalls).map((t) => ({ ...obj(t), status: 'succeeded', durationMs: 8, resultSummary: '완료' })) })
      }
      return json(200, { ...detail, id, title: id === 7 ? detail.title : null, messages: msgs })
    }
    if (method === 'PATCH' && /^\/api\/proposals\/\d+$/.test(path)) {
      const body = obj(req.postDataJSON())
      const status = body.status
      const id = Number(path.split('/').pop())
      const target = allProposals().find((p) => p.id === id)
      if (!target) return json(404, { error: { code: 'PROPOSAL_NOT_FOUND', message: `제안 ${id}을 찾을 수 없습니다.` } })
      const prev = obj(target.decision)
      target.decision = { status, note: 'note' in body ? body.note : prev.note, decidedAt: status === 'pending' ? null : now() }
      return json(200, target)
    }
    if (method === 'POST' && /^\/api\/conversations\/\d+\/messages$/.test(path)) {
      if (scenario === 'hang') return new Promise<void>(() => {})
      readsAfterSend = 0
      if (scenario === 'token') return json(401, { error: { code: 'UNAUTHORIZED', message: '접근 토큰이 없거나 틀렸습니다.' } })
      if (scenario === 'expired') return route.fulfill({ status: 401, contentType: 'text/html', body: '<html><body>로그인</body></html>' })
      const convId = Number(path.split('/')[3])
      const content = String(obj(req.postDataJSON()).content ?? '')
      const user = { ...obj(exampleEvent('message_created').userMessage), id: nextId++, conversationId: convId, content, createdAt: now() }
      const aid = nextId++
      const base = { id: aid, conversationId: convId, role: 'assistant', errorCode: null, proposals: [], usage: null, createdAt: now() }
      const call = (seq: number, status: 'running' | 'succeeded') => ({
        ...exampleEvent(status === 'running' ? 'tool_call' : 'tool_result'), id: 500 + seq, seq,
      })
      const events: [string, unknown][] = [['message_created', { userMessage: user, assistantMessageId: aid }]]
      let saved: Json
      if (scenario === 'sent') {
        saved = { ...base, status: 'running', content: '', toolCalls: [] }
      } else if (scenario === 'progress') {
        events.push(['tool_call', call(1, 'running')], ['tool_result', call(1, 'succeeded')], ['tool_call', call(2, 'running')])
        saved = { ...base, status: 'running', content: '', toolCalls: [call(1, 'succeeded'), call(2, 'running')] }
      } else if (scenario === 'error') {
        events.push(['tool_call', call(1, 'running')], ['tool_result', call(1, 'succeeded')])
        events.push(['error', { error: { code: 'UPSTREAM_ERROR', message: 'LLM 공급자 응답 오류로 실행을 중단했습니다.' }, assistantMessageId: aid }])
        saved = { ...base, status: 'failed', errorCode: 'UPSTREAM_ERROR', content: '', toolCalls: [call(1, 'succeeded')] }
      } else {
        events.push(['tool_call', call(1, 'running')], ['tool_result', call(1, 'succeeded')])
        const final = exampleEvent('final')
        const proposals = scenario === 'done'
          ? [obj(arr(seededAssistant?.proposals)[0]), PROPOSAL].map((p, i) => ({ ...clone(p), id: 700 + i, seq: i + 1, conversationId: convId, messageId: aid }))
          : []
        saved = {
          ...final, ...base, status: 'completed', toolCalls: [call(1, 'succeeded')], proposals, usage: final.usage,
          content: scenario === 'partial' ? `${PARTIAL_PREFIX} 지금까지 확인한 범위에서는 스캔 실패가 가장 큰 이탈입니다.` : String(final.content),
        }
        events.push(['final', saved])
      }
      thread(convId).push(user, saved)
      return route.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(events) })
    }
    return json(404, { error: { code: 'NOT_FOUND', message: `고정 응답 없음: ${method} ${path}` } })
  })
}
