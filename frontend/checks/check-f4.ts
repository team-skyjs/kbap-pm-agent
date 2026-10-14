// F4 검사: 02-objects Proposal 예시와 04 상세의 improvement 예시가 파서를 통과하고,
// 카드가 근거→제안→실행 단계→측정 방법 순서로 렌더되며, 신규 단계 위치가 "src/app/scan.tsx · handleRetry · 398"이다.
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { parseConversationDetail, parseProposal, type Proposal } from '../src/api.ts'
import ProposalCard, { CARD_SECTIONS, locationText } from '../src/ProposalCard.tsx'
import { jsonBlock } from './contract.ts'

const funnel: Proposal = parseProposal(jsonBlock('02-objects.md', 2))
assert.equal(funnel.type, 'funnel_design')
assert.deepEqual(funnel.evidence.map((e) => e.kind), ['metric', 'code', 'taxonomy'])
const code = funnel.evidence[1]
assert(code.kind === 'code' && code.function === 'onScanFailed' && code.line === 405)
assert.equal(funnel.decision.status, 'adopted')

const improvement = parseConversationDetail(jsonBlock('04-conversations.md', 2)).messages[1].proposals[0]
assert.equal(improvement.type, 'improvement')
assert.deepEqual(improvement.measurement.funnel, [])
assert.equal(improvement.decision.decidedAt, null)

// 신규 단계 위치 문자열
const step = funnel.measurement.funnel.find((s) => s.status === 'new')
assert(step?.location)
assert.equal(locationText(step.location), 'src/app/scan.tsx · handleRetry · 398')
assert.equal(locationText({ file: 'a.tsx', function: 'f', line: null }), 'a.tsx · f')

// 네 영역 순서: 정의와 실제 렌더 HTML 둘 다
assert.deepEqual(CARD_SECTIONS.map((s) => s.key), ['evidence', 'proposal', 'steps', 'measurement'])
for (const p of [funnel, improvement]) {
  const html = renderToStaticMarkup(createElement(ProposalCard, { p, onUpdated: () => {} }))
  const at = CARD_SECTIONS.map((s) => html.indexOf(`<h5>${s.label}</h5>`))
  assert(at.every((x, i) => x >= 0 && (i === 0 || x > at[i - 1])), `영역 순서 틀림: ${at}`)
}

// 계약 위반 shape는 거부: new 단계 location 필수 아님(파서는 null 허용), kind 오타는 거부
assert.throws(() => parseProposal({ ...funnel, evidence: [{ kind: 'metrics', summary: 'x' }] }))
