// 계약 경계 (계약서 v1.1, _workspace/01_cto_api-contract.md). 타입·파서·fetch는 이 파일 하나에만 둔다.
// 응답은 unknown으로 받아 필드 단위로 검증하며 새 객체를 만든다. any·as 캐스팅·단독 제네릭 없음 (헌법 원칙 I).
// null 규칙: 계약상 값이 없으면 키는 있고 값이 null이다. 그래서 키 누락은 파싱 실패로 본다.

import { mockFetch } from './mock.ts'

// ---------- 공통: 에러 ----------

export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'BUDGET_EXCEEDED'
  | 'CONVERSATION_NOT_FOUND'
  | 'PROPOSAL_NOT_FOUND'
  | 'NOT_FOUND'
  | 'REPOSITORY_NOT_CONFIGURED'
  | 'RUN_IN_PROGRESS'
  | 'UPSTREAM_ERROR'
  | 'INTERNAL_ERROR'

const ERROR_CODES = [
  'VALIDATION_ERROR', 'UNAUTHORIZED', 'BUDGET_EXCEEDED', 'CONVERSATION_NOT_FOUND', 'PROPOSAL_NOT_FOUND',
  'NOT_FOUND', 'REPOSITORY_NOT_CONFIGURED', 'RUN_IN_PROGRESS', 'UPSTREAM_ERROR', 'INTERNAL_ERROR',
] as const

// 화면에서 쓰는 코드는 위 열 개 + 프론트 자체 사유 두 개.
// NETWORK_ERROR: fetch 자체 실패(백엔드 꺼짐·CORS). BAD_RESPONSE: 응답이 계약 shape와 다름.
export type ClientErrorCode = ErrorCode | 'NETWORK_ERROR' | 'BAD_RESPONSE'

export class ApiError extends Error {
  constructor(public code: ClientErrorCode, message: string, public status: number | null = null) {
    super(message)
  }
}

export type ErrorBody = { error: { code: ErrorCode; message: string } }

// ---------- 파싱 도우미 (계약 shape를 런타임에 확인) ----------

function bad(path: string, why: string): never {
  throw new ApiError('BAD_RESPONSE', `응답 형식이 계약과 다릅니다: ${path} ${why}`)
}
function obj(v: unknown, p: string): object {
  if (typeof v !== 'object' || v === null || Array.isArray(v)) bad(p, '객체가 아님')
  return v
}
function get(o: object, k: string, p: string): unknown {
  if (!(k in o)) bad(`${p}.${k}`, '키 없음')
  const v: unknown = Object.getOwnPropertyDescriptor(o, k)?.value
  return v
}
function str(o: object, k: string, p: string): string {
  const v = get(o, k, p)
  if (typeof v !== 'string') bad(`${p}.${k}`, '문자열 아님')
  return v
}
function num(o: object, k: string, p: string): number {
  const v = get(o, k, p)
  if (typeof v !== 'number') bad(`${p}.${k}`, '숫자 아님')
  return v
}
function strOrNull(o: object, k: string, p: string): string | null {
  return get(o, k, p) === null ? null : str(o, k, p)
}
function numOrNull(o: object, k: string, p: string): number | null {
  return get(o, k, p) === null ? null : num(o, k, p)
}
function oneOf<T extends string>(o: object, k: string, opts: readonly T[], p: string): T {
  const v = get(o, k, p)
  const hit = opts.find((x) => x === v)
  if (hit === undefined) bad(`${p}.${k}`, `허용값 아님: ${JSON.stringify(v)}`)
  return hit
}
function arr<T>(o: object, k: string, p: string, each: (v: unknown, p: string) => T): T[] {
  const v = get(o, k, p)
  if (!Array.isArray(v)) bad(`${p}.${k}`, '배열 아님')
  return v.map((x: unknown, i) => each(x, `${p}.${k}[${i}]`))
}
function objOrNull<T>(o: object, k: string, p: string, parse: (v: unknown, p: string) => T): T | null {
  const v = get(o, k, p)
  return v === null ? null : parse(v, `${p}.${k}`)
}

export function parseErrorBody(v: unknown): ErrorBody {
  const e = obj(get(obj(v, 'body'), 'error', 'body'), 'body.error')
  return { error: { code: oneOf(e, 'code', ERROR_CODES, 'error'), message: str(e, 'message', 'error') } }
}

// ---------- 공통: 요청 ----------

// ponytail: VITE_MOCK=1이면 fetch 대신 mock.ts(계약서 예시 값). 백엔드 모듈이 다 붙으면 mock.ts째 삭제.
const env = import.meta.env
export const API_BASE_URL: string = env?.VITE_API_BASE_URL ?? ''
export const MOCK: boolean = env?.VITE_MOCK === '1'

const TOKEN_KEY = 'kbap-pm-agent.accessToken'
export function getToken(): string {
  try { return localStorage.getItem(TOKEN_KEY) ?? '' } catch { return '' }
}
export function setToken(t: string): void {
  try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY) } catch { /* 저장 불가 브라우저 */ }
}

async function rawFetch(path: string, method: string, body?: string): Promise<Response> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const t = getToken()
  if (t) headers['Authorization'] = `Bearer ${t}`
  const init: RequestInit = { method, headers, body }
  try {
    return MOCK ? await mockFetch(path, init) : await fetch(API_BASE_URL + path, init)
  } catch {
    throw new ApiError('NETWORK_ERROR', `백엔드에 연결할 수 없습니다 (${API_BASE_URL || '주소 미설정'}).`)
  }
}

// 비 2xx는 계약 에러 형식으로 파싱해 ApiError로 던진다.
async function throwIfError(res: Response): Promise<void> {
  if (res.ok) return
  let parsed: ErrorBody
  try {
    parsed = parseErrorBody(await res.json())
  } catch {
    throw new ApiError('BAD_RESPONSE', `HTTP ${res.status}: 에러 응답이 계약 형식이 아닙니다.`, res.status)
  }
  throw new ApiError(parsed.error.code, parsed.error.message, res.status)
}

async function request<T>(method: string, path: string, parse: (v: unknown) => T, body?: unknown): Promise<T> {
  const res = await rawFetch(path, method, body === undefined ? undefined : JSON.stringify(body))
  await throwIfError(res)
  const json: unknown = await res.json()
  return parse(json)
}

// ---------- GET /api/health ----------

export type Health = { status: 'ok' | 'degraded'; db: 'ok' | 'error'; version: string }

export function parseHealth(v: unknown): Health {
  const o = obj(v, 'health')
  return {
    status: oneOf(o, 'status', ['ok', 'degraded'] as const, 'health'),
    db: oneOf(o, 'db', ['ok', 'error'] as const, 'health'),
    version: str(o, 'version', 'health'),
  }
}
export const getHealth = () => request('GET', '/api/health', parseHealth)

// ---------- 공통 객체: ConversationSummary ----------

export type ConversationSummary = {
  id: number
  title: string | null
  createdAt: string
  updatedAt: string
  messageCount: number
  proposalCount: number
  adoptedCount: number
}

export function parseConversationSummary(v: unknown, p = 'conversation'): ConversationSummary {
  const o = obj(v, p)
  return {
    id: num(o, 'id', p),
    title: strOrNull(o, 'title', p),
    createdAt: str(o, 'createdAt', p),
    updatedAt: str(o, 'updatedAt', p),
    messageCount: num(o, 'messageCount', p),
    proposalCount: num(o, 'proposalCount', p),
    adoptedCount: num(o, 'adoptedCount', p),
  }
}

// ---------- 공통 객체: ToolCall ----------

export type ToolCall = {
  id: number
  seq: number
  source: 'amplitude' | 'code' | 'taxonomy'
  name: string
  input: Record<string, unknown>
  status: 'running' | 'succeeded' | 'failed'
  resultSummary: string | null
  durationMs: number | null
  startedAt: string
}

export function parseToolCall(v: unknown, p = 'toolCall'): ToolCall {
  const o = obj(v, p)
  return {
    id: num(o, 'id', p),
    seq: num(o, 'seq', p),
    source: oneOf(o, 'source', ['amplitude', 'code', 'taxonomy'] as const, p),
    name: str(o, 'name', p),
    input: Object.fromEntries(Object.entries(obj(get(o, 'input', p), `${p}.input`))),
    status: oneOf(o, 'status', ['running', 'succeeded', 'failed'] as const, p),
    resultSummary: strOrNull(o, 'resultSummary', p),
    durationMs: numOrNull(o, 'durationMs', p),
    startedAt: str(o, 'startedAt', p),
  }
}

// ---------- 공통 객체: Proposal ----------

export type Evidence =
  | { kind: 'metric'; summary: string; value: string; source: string }
  | { kind: 'code'; summary: string; file: string; function: string | null; line: number; snippet: string }
  | { kind: 'taxonomy'; summary: string; eventName: string }

export type FunnelStep = {
  order: number
  eventName: string
  status: 'existing' | 'new'
  condition: string | null
  location: { file: string; function: string; line: number | null } | null
  properties: { name: string; type: 'string' | 'number' | 'boolean' }[]
}

export type Measurement = {
  primaryMetric: string
  baseline: string | null
  target: string | null
  funnel: FunnelStep[]
}

export type DecisionStatus = 'pending' | 'adopted' | 'on_hold'

export type Decision = { status: DecisionStatus; note: string | null; decidedAt: string | null }

export type Proposal = {
  id: number
  conversationId: number
  messageId: number
  seq: number
  type: 'improvement' | 'funnel_design'
  title: string
  evidence: Evidence[]
  proposal: string
  steps: string[]
  measurement: Measurement
  decision: Decision
  createdAt: string
}

const DECISION_STATUSES = ['pending', 'adopted', 'on_hold'] as const

function parseEvidence(v: unknown, p: string): Evidence {
  const o = obj(v, p)
  const kind = oneOf(o, 'kind', ['metric', 'code', 'taxonomy'] as const, p)
  const summary = str(o, 'summary', p)
  if (kind === 'metric') return { kind, summary, value: str(o, 'value', p), source: str(o, 'source', p) }
  if (kind === 'code') {
    return {
      kind, summary,
      file: str(o, 'file', p), function: strOrNull(o, 'function', p), line: num(o, 'line', p), snippet: str(o, 'snippet', p),
    }
  }
  return { kind, summary, eventName: str(o, 'eventName', p) }
}

function parseFunnelStep(v: unknown, p: string): FunnelStep {
  const o = obj(v, p)
  return {
    order: num(o, 'order', p),
    eventName: str(o, 'eventName', p),
    status: oneOf(o, 'status', ['existing', 'new'] as const, p),
    condition: strOrNull(o, 'condition', p),
    location: objOrNull(o, 'location', p, (lv, lp) => {
      const l = obj(lv, lp)
      return { file: str(l, 'file', lp), function: str(l, 'function', lp), line: numOrNull(l, 'line', lp) }
    }),
    properties: arr(o, 'properties', p, (pv, pp) => {
      const x = obj(pv, pp)
      return { name: str(x, 'name', pp), type: oneOf(x, 'type', ['string', 'number', 'boolean'] as const, pp) }
    }),
  }
}

function parseDecision(v: unknown, p: string): Decision {
  const o = obj(v, p)
  return { status: oneOf(o, 'status', DECISION_STATUSES, p), note: strOrNull(o, 'note', p), decidedAt: strOrNull(o, 'decidedAt', p) }
}

export function parseProposal(v: unknown, p = 'proposal'): Proposal {
  const o = obj(v, p)
  const m = obj(get(o, 'measurement', p), `${p}.measurement`)
  const mp = `${p}.measurement`
  return {
    id: num(o, 'id', p),
    conversationId: num(o, 'conversationId', p),
    messageId: num(o, 'messageId', p),
    seq: num(o, 'seq', p),
    type: oneOf(o, 'type', ['improvement', 'funnel_design'] as const, p),
    title: str(o, 'title', p),
    evidence: arr(o, 'evidence', p, parseEvidence),
    proposal: str(o, 'proposal', p),
    steps: arr(o, 'steps', p, (sv, sp) => (typeof sv === 'string' ? sv : bad(sp, '문자열 아님'))),
    measurement: {
      primaryMetric: str(m, 'primaryMetric', mp),
      baseline: strOrNull(m, 'baseline', mp),
      target: strOrNull(m, 'target', mp),
      funnel: arr(m, 'funnel', mp, parseFunnelStep),
    },
    decision: parseDecision(get(o, 'decision', p), `${p}.decision`),
    createdAt: str(o, 'createdAt', p),
  }
}

// ---------- 공통 객체: Message ----------

export type Usage = { model: string; inputTokens: number; outputTokens: number; costUsd: number }

export type Message = {
  id: number
  conversationId: number
  role: 'user' | 'assistant'
  status: 'running' | 'completed' | 'failed'
  content: string
  errorCode: string | null
  toolCalls: ToolCall[]
  proposals: Proposal[]
  usage: Usage | null
  createdAt: string
}

export function parseMessage(v: unknown, p = 'message'): Message {
  const o = obj(v, p)
  return {
    id: num(o, 'id', p),
    conversationId: num(o, 'conversationId', p),
    role: oneOf(o, 'role', ['user', 'assistant'] as const, p),
    status: oneOf(o, 'status', ['running', 'completed', 'failed'] as const, p),
    content: str(o, 'content', p),
    errorCode: strOrNull(o, 'errorCode', p),
    toolCalls: arr(o, 'toolCalls', p, parseToolCall),
    proposals: arr(o, 'proposals', p, parseProposal),
    usage: objOrNull(o, 'usage', p, (uv, up) => {
      const u = obj(uv, up)
      return { model: str(u, 'model', up), inputTokens: num(u, 'inputTokens', up), outputTokens: num(u, 'outputTokens', up), costUsd: num(u, 'costUsd', up) }
    }),
    createdAt: str(o, 'createdAt', p),
  }
}

// ---------- 대화 엔드포인트 ----------

export type ConversationDetail = { id: number; title: string | null; createdAt: string; updatedAt: string; messages: Message[] }

export function parseConversationDetail(v: unknown, p = 'conversation'): ConversationDetail {
  const o = obj(v, p)
  return {
    id: num(o, 'id', p),
    title: strOrNull(o, 'title', p),
    createdAt: str(o, 'createdAt', p),
    updatedAt: str(o, 'updatedAt', p),
    messages: arr(o, 'messages', p, parseMessage),
  }
}

export function parseConversationList(v: unknown): { items: ConversationSummary[] } {
  return { items: arr(obj(v, 'list'), 'items', 'list', parseConversationSummary) }
}

export const listConversations = () => request('GET', '/api/conversations', parseConversationList)
export const createConversation = (title?: string) =>
  request('POST', '/api/conversations', (v) => parseConversationSummary(v), title === undefined ? {} : { title })
export const getConversation = (id: number) =>
  request('GET', `/api/conversations/${id}`, (v) => parseConversationDetail(v))

// ---------- POST /api/conversations/{id}/messages (SSE) ----------

export type MessageCreated = { userMessage: Message; assistantMessageId: number }
export type StreamError = { error: { code: ErrorCode; message: string }; assistantMessageId: number }

export type StreamEvent =
  | { event: 'message_created'; data: MessageCreated }
  | { event: 'tool_call'; data: ToolCall }
  | { event: 'tool_result'; data: ToolCall }
  | { event: 'final'; data: Message }
  | { event: 'error'; data: StreamError }

// SSE 원문 블록 하나(빈 줄로 구분) → 이벤트. `: ping` 같은 주석만 있는 블록은 null.
export function parseSseBlock(block: string): StreamEvent | null {
  let event = ''
  const data: string[] = []
  for (const line of block.split(/\r?\n/)) {
    if (line === '' || line.startsWith(':')) continue
    const i = line.indexOf(':')
    const field = i < 0 ? line : line.slice(0, i)
    const value = i < 0 ? '' : line.slice(i + 1).replace(/^ /, '')
    if (field === 'event') event = value
    else if (field === 'data') data.push(value)
  }
  if (!event && data.length === 0) return null
  const d: unknown = JSON.parse(data.join('\n'))
  switch (event) {
    case 'message_created': {
      const o = obj(d, 'message_created')
      return { event, data: { userMessage: parseMessage(get(o, 'userMessage', 'message_created'), 'userMessage'), assistantMessageId: num(o, 'assistantMessageId', 'message_created') } }
    }
    case 'tool_call':
    case 'tool_result':
      return { event, data: parseToolCall(d, event) }
    case 'final':
      return { event, data: parseMessage(d, 'final') }
    case 'error': {
      const o = obj(d, 'error')
      return { event, data: { error: parseErrorBody(d).error, assistantMessageId: num(o, 'assistantMessageId', 'error') } }
    }
    default:
      return bad('sse', `알 수 없는 이벤트 ${JSON.stringify(event)}`)
  }
}

// 청크를 받아 완성된 블록만 이벤트로 돌려준다. 남은 조각은 다음 청크와 합친다.
export function createSseParser(): (chunk: string) => StreamEvent[] {
  let buf = ''
  return (chunk) => {
    buf += chunk.replace(/\r\n/g, '\n')
    const blocks = buf.split('\n\n')
    buf = blocks.pop() ?? ''
    return blocks.map(parseSseBlock).filter((e): e is StreamEvent => e !== null)
  }
}

// 스트림 시작 전 에러(400/404/409/403)는 ApiError로 던진다.
// 반환값: 'final' | 'error'면 정상 종료, 'disconnected'면 끝 이벤트 없이 끊김 → 호출자가 상세를 다시 읽는다.
export async function sendMessage(
  conversationId: number,
  content: string,
  onEvent: (e: StreamEvent) => void,
): Promise<'final' | 'error' | 'disconnected'> {
  const res = await rawFetch(`/api/conversations/${conversationId}/messages`, 'POST', JSON.stringify({ content }))
  await throwIfError(res)
  if (!res.body) return 'disconnected'
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  const feed = createSseParser()
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) return 'disconnected'
      for (const e of feed(value)) {
        onEvent(e)
        if (e.event === 'final' || e.event === 'error') {
          void reader.cancel()
          return e.event
        }
      }
    }
  } catch (e) {
    if (e instanceof ApiError) throw e
    return 'disconnected'
  }
}

// ---------- 화면 문구 (code로만 분기, 계약서 공통 규칙) ----------

const ERROR_TEXT: Record<ClientErrorCode, string> = {
  VALIDATION_ERROR: '입력값이 올바르지 않습니다.',
  UNAUTHORIZED: '접근 토큰이 없거나 틀렸습니다. 설정 화면에서 입력하세요.',
  BUDGET_EXCEEDED: 'LLM 예산 상한에 도달해 실행할 수 없습니다.',
  CONVERSATION_NOT_FOUND: '대화를 찾을 수 없습니다.',
  PROPOSAL_NOT_FOUND: '제안을 찾을 수 없습니다.',
  NOT_FOUND: '요청한 경로가 없습니다.',
  REPOSITORY_NOT_CONFIGURED: '저장소를 먼저 등록하세요.',
  RUN_IN_PROGRESS: '이 대화에서 이미 응답을 만드는 중입니다. 끝난 뒤 다시 보내세요.',
  UPSTREAM_ERROR: '외부 서비스(LLM·GitHub·Amplitude) 오류로 중단했습니다.',
  INTERNAL_ERROR: '서버 내부 오류로 중단했습니다.',
  NETWORK_ERROR: '백엔드에 연결할 수 없습니다.',
  BAD_RESPONSE: '서버 응답 형식이 계약과 다릅니다.',
}

// 서버 message가 있으면 함께 보여준다(사유·위치가 담긴다. 예: 택사노미 검증 실패).
export function errorText(code: string, message?: string): string {
  const base = ERROR_TEXT[ERROR_CODES.find((c) => c === code) ?? (code === 'NETWORK_ERROR' || code === 'BAD_RESPONSE' ? code : 'INTERNAL_ERROR')]
  return message && message !== base ? `${base} (${code}: ${message})` : `${base} (${code})`
}
export function describe(e: unknown): string {
  return e instanceof ApiError ? errorText(e.code, e.message) : String(e)
}
