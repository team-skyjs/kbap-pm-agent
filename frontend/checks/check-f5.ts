// 검사: Settings·저장소·동기화·택사노미 응답 예시 파싱
// repository·taxonomy null 변형, Amplitude 서버 키 상태 두 값, 택사노미 검증 실패 message의 위치 정보 확인
import assert from 'node:assert/strict'
import { errorText, parseErrorBody, parseRepository, parseSettings, parseTaxonomyStatus, type Settings } from '../src/api.ts'
import { jsonBlock } from './contract.ts'

const raw = jsonBlock('02-objects.md', 3)
const s: Settings = parseSettings(raw)
assert.equal(s.repository?.codeMapStatus, 'ready')
assert.equal(s.repository?.lastError, null)
assert.deepEqual(s.amplitude, { status: 'configured' })
assert.equal(s.agentMode, 'real')
assert.equal(s.budget.limitUsd, 200)

// null 변형 (미등록·미업로드·서버 키 없음)
assert(typeof raw === 'object' && raw !== null)
const empty = parseSettings({ ...raw, repository: null, taxonomy: null, amplitude: { status: 'missing' } })
assert.equal(empty.repository, null)
assert.equal(empty.taxonomy, null)
assert.equal(empty.amplitude.status, 'missing')
// 이전 OAuth 상태값은 계약 밖
assert.throws(() => parseSettings({ ...raw, amplitude: { status: 'connected', serverUrl: 'x', connectedAt: null } }))

// 07-settings.md 블록 순서: [1] PUT repository, [2] sync, [4] 택사노미 응답, [5] 택사노미 검증 실패
const put = parseRepository(jsonBlock('07-settings.md', 1))
assert.equal(put.codeMapCommit, null)
assert.equal(put.codeMapStatus, 'building')
assert.equal(parseRepository(jsonBlock('07-settings.md', 2)).headCommit, 'b71e04d')
assert.equal(parseTaxonomyStatus(jsonBlock('07-settings.md', 4)).eventCount, 2)
const v = parseErrorBody(jsonBlock('07-settings.md', 5))
assert.equal(v.error.code, 'VALIDATION_ERROR')
assert(errorText(v.error.code, v.error.message).includes('events[3].properties[0].type'))

// lastError 키 누락(이전 계약 형태) 거부
const { lastError: _drop, ...noLastError } = put
assert.throws(() => parseRepository(noLastError))
