// 검사: 질문 다듬기·선택 기록 응답 예시(08b-questions.md)가 api.ts 파서를 통과, 계약 밖 선택 값과 키 누락은 거부
import assert from 'node:assert/strict'
import { errorText, parseErrorBody, parseRefineChoiceResponse, parseRefineResponse, type RefineChoiceResponse, type RefineResponse } from '../src/api.ts'
import { jsonBlock } from './contract.ts'

// 08b 블록 순서: [0] 다듬기 요청, [1] 다듬기 응답, [2] 선택 요청, [3] 선택 응답
const refine: RefineResponse = parseRefineResponse(jsonBlock('08b-questions.md', 1))
assert.equal(refine.refinementId, 31)
assert(refine.refined.startsWith('최근 7일 scan_start'))
assert(refine.summary.length > 0)

const choice: RefineChoiceResponse = parseRefineChoiceResponse(jsonBlock('08b-questions.md', 3))
assert.equal(choice.choice, 'refined')
assert.equal(choice.chosenAt, '2026-10-15T10:02:11.204Z')

for (const c of ['refined', 'original', 'cancelled']) assert.equal(parseRefineChoiceResponse({ ...choice, choice: c }).choice, c)
assert.throws(() => parseRefineChoiceResponse({ ...choice, choice: 'edited' }), '세 값 밖 선택은 거부')
assert.throws(() => parseRefineResponse({ refinementId: 31, refined: 'x' }), 'summary 키 누락 거부')

// 새 에러 코드
const nf = parseErrorBody({ error: { code: 'REFINEMENT_NOT_FOUND', message: '다듬기 기록 31을 찾을 수 없습니다.' } })
assert.equal(nf.error.code, 'REFINEMENT_NOT_FOUND')
assert(errorText(nf.error.code).startsWith('질문 다듬기 기록을 찾을 수 없습니다.'))
