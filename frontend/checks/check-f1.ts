// F1 검사: contracts/03-health.md 두 예시와 01-common.md 에러 예시가 api.ts 파서를 통과한다.
import assert from 'node:assert/strict'
import { parseHealth, parseErrorBody, type Health } from '../src/api.ts'

const ok: Health = parseHealth(JSON.parse('{"status": "ok", "db": "ok", "version": "0.1.0"}'))
assert.deepEqual(ok, { status: 'ok', db: 'ok', version: '0.1.0' })

const degraded = parseHealth(JSON.parse('{"status": "degraded", "db": "error", "version": "0.1.0"}'))
assert.equal(degraded.status, 'degraded')
assert.equal(degraded.db, 'error')

const err = parseErrorBody(JSON.parse(`{
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "대화 7을 찾을 수 없습니다."
  }
}`))
assert.equal(err.error.code, 'CONVERSATION_NOT_FOUND')
assert.equal(err.error.message, '대화 7을 찾을 수 없습니다.')

// 계약 밖 shape는 거부한다: FastAPI 기본 422, 키 누락
assert.throws(() => parseErrorBody({ detail: [] }))
assert.throws(() => parseHealth({ status: 'ok', version: '0.1.0' }))
