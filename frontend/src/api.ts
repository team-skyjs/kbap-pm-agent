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
