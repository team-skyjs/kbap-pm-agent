// 검사: 접근 계층 응답 세 종은 SESSION_EXPIRED, 백엔드 401 계약 JSON은 UNAUTHORIZED, 계약 JSON 없는 5xx는 NETWORK_ERROR
import assert from 'node:assert/strict'
import { ApiError, checkResponse, type ResponseLike } from '../src/api.ts'

async function codeOf(res: ResponseLike): Promise<string> {
  try {
    await checkResponse(res)
    return 'OK'
  } catch (e) {
    assert(e instanceof ApiError)
    return e.code
  }
}

// Node의 Response 생성자로는 opaqueredirect를 만들 수 없어 같은 모양의 객체 사용
const opaqueRedirect: ResponseLike = {
  type: 'opaqueredirect', status: 0, ok: false, headers: new Headers(),
  json: () => Promise.reject(new Error('본문 없음')),
}
const html = (status: number) => new Response('<html>login</html>', { status, headers: { 'Content-Type': 'text/html; charset=utf-8' } })
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

assert.equal(await codeOf(opaqueRedirect), 'SESSION_EXPIRED')
assert.equal(await codeOf(html(401)), 'SESSION_EXPIRED')
assert.equal(await codeOf(html(200)), 'SESSION_EXPIRED')
assert.equal(await codeOf(json(401, { error: { code: 'UNAUTHORIZED', message: '접근 토큰이 없거나 틀렸습니다.' } })), 'UNAUTHORIZED')
assert.equal(await codeOf(html(502)), 'NETWORK_ERROR')
assert.equal(await codeOf(html(504)), 'NETWORK_ERROR')

// 경계: 비계약 JSON은 403이면 SESSION_EXPIRED, 5xx면 NETWORK_ERROR, 그 외 4xx면 BAD_RESPONSE. 계약 JSON 5xx는 그 코드 유지
assert.equal(await codeOf(json(403, { message: 'forbidden' })), 'SESSION_EXPIRED')
assert.equal(await codeOf(json(500, { detail: [] })), 'NETWORK_ERROR')
assert.equal(await codeOf(json(422, { detail: [] })), 'BAD_RESPONSE')
assert.equal(await codeOf(json(502, { error: { code: 'UPSTREAM_ERROR', message: 'LLM 공급자 오류' } })), 'UPSTREAM_ERROR')
assert.equal(await codeOf(json(200, { status: 'ok' })), 'OK')
assert.equal(await codeOf(new Response('', { headers: { 'Content-Type': 'text/event-stream' } })), 'OK')
// 계약 에러 JSON인 403(예산 초과)은 세션 만료와 섞이지 않음
assert.equal(await codeOf(json(403, { error: { code: 'BUDGET_EXCEEDED', message: 'LLM 예산 상한에 도달했습니다.' } })), 'BUDGET_EXCEEDED')
