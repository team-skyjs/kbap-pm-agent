// F5 검사: 02 Settings 예시, 07 저장소·동기화·택사노미 응답 예시, 08 connect 예시가 파서를 통과한다.
// repository null, taxonomy null 변형도 통과한다. 택사노미 검증 실패 에러 본문의 위치 message가 그대로 읽힌다.
import assert from 'node:assert/strict'
import { errorText, parseAuthorizationUrl, parseErrorBody, parseRepository, parseSettings, parseTaxonomyStatus, type Settings } from '../src/api.ts'
import { jsonBlock } from './contract.ts'

const raw = jsonBlock('02-objects.md', 3)
const s: Settings = parseSettings(raw)
assert.equal(s.repository?.codeMapStatus, 'ready')
assert.equal(s.repository?.lastError, null)
assert.equal(s.amplitude.status, 'connected')
assert.equal(s.agentMode, 'real')
assert.equal(s.budget.limitUsd, 200)

// null 변형 (미등록·미업로드·끊김)
assert(typeof raw === 'object' && raw !== null)
const empty = parseSettings({ ...raw, repository: null, taxonomy: null, amplitude: { status: 'disconnected', serverUrl: 'https://mcp.amplitude.com/mcp', connectedAt: null } })
assert.equal(empty.repository, null)
assert.equal(empty.taxonomy, null)
assert.equal(empty.amplitude.connectedAt, null)

// 07: [1] PUT repository 응답, [2] sync 응답, [4] 택사노미 응답, [5] 택사노미 검증 실패
const put = parseRepository(jsonBlock('07-settings.md', 1))
assert.equal(put.codeMapCommit, null)
assert.equal(put.codeMapStatus, 'building')
assert.equal(parseRepository(jsonBlock('07-settings.md', 2)).headCommit, 'b71e04d')
assert.equal(parseTaxonomyStatus(jsonBlock('07-settings.md', 4)).eventCount, 2)
const v = parseErrorBody(jsonBlock('07-settings.md', 5))
assert.equal(v.error.code, 'VALIDATION_ERROR')
assert(errorText(v.error.code, v.error.message).includes('events[3].properties[0].type'))

// 08: connect
assert(parseAuthorizationUrl(jsonBlock('08-amplitude.md', 0)).authorizationUrl.startsWith('https://app.amplitude.com/oauth/authorize?'))

// lastError 키 누락(v1 shape)은 거부
const { lastError: _drop, ...noLastError } = put
assert.throws(() => parseRepository(noLastError))
