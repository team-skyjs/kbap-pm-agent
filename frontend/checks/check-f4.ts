// 검사: Proposal 예시·improvement 예시 파싱, 카드 네 영역 렌더 순서, 신규 단계 위치 문자열
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

const step = funnel.measurement.funnel.find((s) => s.status === 'new')
assert(step?.location)
assert.equal(locationText(step.location), 'src/app/scan.tsx · handleRetry · 398')
assert.equal(locationText({ file: 'a.tsx', function: 'f', line: null }), 'a.tsx · f')

// 네 영역 순서: 정의와 실제 렌더 HTML 모두 확인
assert.deepEqual(CARD_SECTIONS.map((s) => s.key), ['evidence', 'proposal', 'steps', 'measurement'])
for (const p of [funnel, improvement]) {
  const html = renderToStaticMarkup(createElement(ProposalCard, { p, onUpdated: () => {} }))
  const at = CARD_SECTIONS.map((s) => html.indexOf(`<h5>${s.label}</h5>`))
  assert(at.every((x, i) => x >= 0 && (i === 0 || x > at[i - 1])), `영역 순서 틀림: ${at}`)
}

// 계약 위반 형태 거부: evidence kind 오타
assert.throws(() => parseProposal({ ...funnel, evidence: [{ kind: 'metrics', summary: 'x' }] }))
