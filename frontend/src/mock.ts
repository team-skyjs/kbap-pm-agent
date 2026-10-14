// ponytail: 백엔드 없이 화면을 띄우는 가짜 fetch. 값은 계약서 v1.1 예시 그대로. VITE_MOCK=1일 때만 쓰인다.
// 메모리 상태라 새로고침하면 초기화된다. 실제 백엔드 연동이 끝나면 이 파일과 api.ts의 MOCK 분기를 지운다.

const now = () => new Date().toISOString()
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const err = (status: number, code: string, message: string) => json(status, { error: { code, message } })

// 계약서 02-objects Proposal 예시 (funnel_design)
const funnelProposal = () => ({
  id: 15, conversationId: 7, messageId: 42, seq: 2, type: 'funnel_design', title: '스캔 실패 후 재시도 퍼널 측정 설계',
  evidence: [
    { kind: 'metric', summary: '최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.', value: '41.3%', source: 'Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14' },
    { kind: 'code', summary: '실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.', file: 'src/app/scan.tsx', function: 'onScanFailed', line: 405, snippet: 'track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });' },
    { kind: 'taxonomy', summary: 'scan_complete는 성공·실패를 success 속성으로 구분한다.', eventName: 'scan_complete' },
  ],
  proposal: '실패 화면의 재시도 동작에 신규 이벤트 scan_retry_tap을 심어, 실패 후 재시도로 회복되는 비율을 측정한다.',
  steps: ['EVENTS 상수에 scan_retry_tap을 추가한다.', 'src/app/scan.tsx의 handleRetry 첫 줄에서 track(EVENTS.scan_retry_tap, { fail_reason })를 호출한다.', '택사노미 문서에 scan_retry_tap 정의와 fail_reason 속성을 추가한다.', '배포 후 7일간 아래 퍼널을 Amplitude에 저장해 확인한다.'],
  measurement: {
    primaryMetric: 'scan_complete(success=false) 이후 24시간 내 scan_complete(success=true) 도달 비율', baseline: null, target: '35%',
    funnel: [
      { order: 1, eventName: 'scan_complete', status: 'existing', condition: 'success=false', location: null, properties: [] },
      { order: 2, eventName: 'scan_retry_tap', status: 'new', condition: null, location: { file: 'src/app/scan.tsx', function: 'handleRetry', line: 398 }, properties: [{ name: 'fail_reason', type: 'string' }] },
      { order: 3, eventName: 'scan_complete', status: 'existing', condition: 'success=true', location: null, properties: [] },
    ],
  },
  decision: { status: 'pending', note: null, decidedAt: null }, createdAt: '2026-10-15T09:14:40.990Z',
})
// 계약서 04-conversations 상세 예시의 improvement 제안
const improvementProposal = () => ({
  id: 14, conversationId: 7, messageId: 42, seq: 1, type: 'improvement', title: 'OCR 실패 화면에 재시도·직접 입력 동선 추가',
  evidence: [{ kind: 'metric', summary: '실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.', value: '62%', source: 'Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14' }],
  proposal: "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.",
  steps: ['src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.', '직접 입력은 기존 search 화면으로 이동시킨다.'],
  measurement: { primaryMetric: 'scan_start 대비 scan_complete(success=true) 전환율', baseline: '41.3%', target: '48%', funnel: [] },
  decision: { status: 'pending', note: null, decidedAt: null }, createdAt: '2026-10-15T09:14:40.980Z',
})

type Obj = Record<string, unknown>
type Conv = { id: number; title: string | null; createdAt: string; updatedAt: string; messages: Obj[]; proposals: Obj[] }

let nextId = 1000
const convs: Conv[] = [
  { id: 6, title: null, createdAt: '2026-10-14T05:40:00.000Z', updatedAt: '2026-10-14T05:40:00.000Z', messages: [], proposals: [] },
]

function summary(c: Conv) {
  const adopted = c.proposals.filter((p) => (p.decision as Obj).status === 'adopted').length
  return { id: c.id, title: c.title, createdAt: c.createdAt, updatedAt: c.updatedAt, messageCount: c.messages.length, proposalCount: c.proposals.length, adoptedCount: adopted }
}
const msg = (o: Obj) => ({ errorCode: null, toolCalls: [], proposals: [], usage: null, status: 'completed', ...o })

function sse(c: Conv, content: string): Response {
  const userMessage = msg({ id: nextId++, conversationId: c.id, role: 'user', content, createdAt: now() })
  c.messages.push(userMessage)
  if (!c.title) c.title = content.slice(0, 40)
  const aid = nextId++
  const assistant: Obj = msg({ id: aid, conversationId: c.id, role: 'assistant', status: 'running', content: '', createdAt: now() })
  c.messages.push(assistant)
  const t1 = { id: nextId++, seq: 1, source: 'taxonomy', name: 'search_taxonomy', input: { query: 'scan' }, startedAt: now() }
  const t2 = { id: nextId++, seq: 2, source: 'code', name: 'find_event_calls', input: { eventName: 'scan_complete' }, startedAt: now() }
  const running = { status: 'running', resultSummary: null, durationMs: null }
  const done1 = { ...t1, status: 'succeeded', resultSummary: '일치 이벤트 2개: scan_start, scan_complete', durationMs: 8 }
  const done2 = { ...t2, status: 'succeeded', resultSummary: '2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)', durationMs: 14 }
  const proposals = [improvementProposal(), funnelProposal()].map((p) => ({ ...p, id: nextId++, conversationId: c.id, messageId: aid, createdAt: now() }))
  const enc = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    async start(ctl) {
      const send = (event: string, data: unknown) => ctl.enqueue(enc.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
      send('message_created', { userMessage, assistantMessageId: aid })
      await sleep(400); send('tool_call', { ...t1, ...running })
      await sleep(600); send('tool_result', done1); assistant.toolCalls = [done1]
      ctl.enqueue(enc.encode(': ping\n\n'))
      await sleep(400); send('tool_call', { ...t2, ...running })
      await sleep(800); send('tool_result', done2)
      Object.assign(assistant, {
        status: 'completed', toolCalls: [done1, done2], proposals,
        content: '지난 30일 스캔 퍼널에서 가장 큰 이탈은 **scan_start → scan_complete(성공)** 구간입니다. 실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.',
        usage: { model: 'anthropic:claude-sonnet-5-5', inputTokens: 18432, outputTokens: 2210, costUsd: 0 },
      })
      c.proposals.push(...proposals)
      c.updatedAt = now()
      send('final', assistant)
      ctl.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

// 계약서 02-objects Settings 예시. fake 모드처럼 agentMode "fake", 처음엔 저장소·택사노미 없음.
const settings: Obj = {
  repository: null,
  taxonomy: null,
  amplitude: { status: 'disconnected', serverUrl: 'https://mcp.amplitude.com/mcp', connectedAt: null },
  models: { agent: 'anthropic:claude-sonnet-5-5', codeSummary: 'anthropic:claude-haiku-5-5' },
  agentMode: 'fake',
  budget: { limitUsd: 200.0, spentUsd: 3.4172 },
}

function taxonomyError(body: Obj): string | null {
  if (!Array.isArray(body.events) || body.events.length === 0) return 'events: 1개 이상이어야 합니다.'
  for (const [i, e] of body.events.entries()) {
    if (typeof e?.name !== 'string') return `events[${i}].name: 필수입니다.`
    for (const [j, pr] of (Array.isArray(e.properties) ? e.properties : []).entries()) {
      if (!['string', 'number', 'boolean'].includes(pr?.type)) return `events[${i}].properties[${j}].type: "${pr?.type}"는 허용되지 않습니다. string, number, boolean 중 하나여야 합니다.`
    }
  }
  return null
}

export async function mockFetch(path: string, init: RequestInit): Promise<Response> {
  await sleep(100)
  const method = init.method ?? 'GET'
  let body: Obj = {}
  try { body = typeof init.body === 'string' && init.body ? JSON.parse(init.body) : {} } catch { return err(400, 'VALIDATION_ERROR', '본문 JSON이 깨졌습니다.') }
  let m: RegExpMatchArray | null
  if (method === 'GET' && path === '/api/health') return json(200, { status: 'ok', db: 'ok', version: '0.1.0' })
  if (path === '/api/conversations') {
    if (method === 'GET') return json(200, { items: [...convs].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).map(summary) })
    if (method === 'POST') {
      const c: Conv = { id: nextId++, title: typeof body.title === 'string' ? body.title : null, createdAt: now(), updatedAt: now(), messages: [], proposals: [] }
      convs.push(c)
      return json(201, summary(c))
    }
  }
  if ((m = path.match(/^\/api\/conversations\/(\d+)(\/messages)?$/))) {
    const c = convs.find((x) => x.id === Number(m![1]))
    if (!c) return err(404, 'CONVERSATION_NOT_FOUND', `대화 ${m[1]}을 찾을 수 없습니다.`)
    if (method === 'GET' && !m[2]) return json(200, { id: c.id, title: c.title, createdAt: c.createdAt, updatedAt: c.updatedAt, messages: c.messages })
    if (method === 'POST' && m[2]) {
      const content = typeof body.content === 'string' ? body.content : ''
      if (content.length < 1 || content.length > 4000) return err(400, 'VALIDATION_ERROR', 'content는 1~4000자여야 합니다.')
      if (c.messages.some((x) => x.status === 'running')) return err(409, 'RUN_IN_PROGRESS', '이 대화에서 이미 실행 중인 응답이 있습니다.')
      return sse(c, content)
    }
  }
  if (method === 'PATCH' && (m = path.match(/^\/api\/proposals\/(\d+)$/))) {
    const p = convs.flatMap((c) => c.proposals).find((x) => x.id === Number(m![1]))
    if (!p) return err(404, 'PROPOSAL_NOT_FOUND', `제안 ${m[1]}을 찾을 수 없습니다.`)
    const prev = p.decision as Obj
    const status = body.status
    if (status !== 'pending' && status !== 'adopted' && status !== 'on_hold') return err(400, 'VALIDATION_ERROR', 'status가 허용값이 아닙니다.')
    p.decision = {
      status,
      note: 'note' in body ? body.note : prev.note,
      decidedAt: status === 'pending' ? null : status !== prev.status ? now() : prev.decidedAt,
    }
    const c = convs.find((x) => x.id === p.conversationId)
    if (c) c.updatedAt = now()
    return json(200, p)
  }
  if (method === 'GET' && path === '/api/settings') return json(200, settings)
  if (method === 'PUT' && path === '/api/settings/repository') {
    if (typeof body.url !== 'string' || !/^(https:\/\/github\.com\/|file:\/\/)/.test(body.url)) return err(400, 'VALIDATION_ERROR', 'url은 https://github.com/으로 시작해야 합니다.')
    settings.repository = {
      url: body.url, branch: typeof body.branch === 'string' ? body.branch : 'develop', headCommit: '9f3c2a1', codeMapCommit: '9f3c2a1',
      codeMapStatus: 'ready', trackedEventCount: 87, screenCount: 41, syncedAt: now(), lastError: null,
    }
    return json(200, settings.repository)
  }
  if (method === 'POST' && path === '/api/settings/repository/sync') {
    if (!settings.repository) return err(409, 'REPOSITORY_NOT_CONFIGURED', '저장소를 먼저 등록하세요.')
    settings.repository = { ...(settings.repository as Obj), syncedAt: now() }
    return json(200, settings.repository)
  }
  if (method === 'PUT' && path === '/api/settings/taxonomy') {
    const why = taxonomyError(body)
    if (why) return err(400, 'VALIDATION_ERROR', why)
    settings.taxonomy = { eventCount: (body.events as unknown[]).length, uploadedAt: now() }
    return json(200, settings.taxonomy)
  }
  if (method === 'POST' && path === '/api/integrations/amplitude/connect') {
    settings.amplitude = { status: 'connected', serverUrl: 'https://mcp.amplitude.com/mcp', connectedAt: now() }
    return json(200, { authorizationUrl: 'https://app.amplitude.com/oauth/authorize?response_type=code&client_id=mcp-4f2a91&redirect_uri=https%3A%2F%2Fpm-agent-api.simhani1.dev%2Fapi%2Fintegrations%2Famplitude%2Fcallback&state=Zx81kQ&code_challenge=Q9v0aR3&code_challenge_method=S256' })
  }
  return err(404, 'NOT_FOUND', `mock: ${method} ${path} 없음`)
}
