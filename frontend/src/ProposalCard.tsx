import { useState } from 'react'
import { describe, updateProposal, type DecisionStatus, type Evidence, type FunnelStep, type Proposal } from './api.ts'
import Markdown from './Markdown.tsx'

// 계약이 정한 카드 네 영역 순서, 렌더는 이 배열 순서를 따름
export const CARD_SECTIONS = [
  { key: 'evidence', label: '근거' },
  { key: 'proposal', label: '제안' },
  { key: 'steps', label: '실행 단계' },
  { key: 'measurement', label: '측정 방법' },
] as const

export function locationText(loc: NonNullable<FunnelStep['location']>): string {
  return [loc.file, loc.function, loc.line].filter((x) => x !== null).join(' · ')
}

const DECISION_LABEL: Record<DecisionStatus, string> = { pending: '미결정', adopted: '채택', on_hold: '보류' }
const TYPE_LABEL: Record<Proposal['type'], string> = { improvement: '기획 개선', funnel_design: '측정 설계' }

const KIND_LABEL: Record<Evidence['kind'], string> = { metric: '지표', code: '코드', taxonomy: '택사노미' }

function EvidenceItem({ e }: { e: Evidence }) {
  const tag = <span className={`tag ${e.kind}`}>{KIND_LABEL[e.kind]}</span>
  switch (e.kind) {
    case 'metric':
      return <li>{tag} <b>{e.value}</b> {e.summary}<div className="muted">출처: {e.source}</div></li>
    case 'code':
      return (
        <li>
          {tag} {e.summary}
          <div className="muted"><code>{e.file}:{e.line}</code>{e.function && <> · <code>{e.function}</code></>}</div>
          <pre>{e.snippet}</pre>
        </li>
      )
    case 'taxonomy':
      return <li>{tag} <code>{e.eventName}</code> {e.summary}</li>
  }
}

function Measurement({ m }: { m: Proposal['measurement'] }) {
  return (
    <>
      <dl className="metric">
        <dt>핵심 지표</dt><dd>{m.primaryMetric}</dd>
        <dt>기준값</dt><dd>{m.baseline ?? '없음'}</dd>
        <dt>목표</dt><dd>{m.target ?? '없음'}</dd>
      </dl>
      {m.funnel.length > 0 && (
        <div className="md-table-scroll" tabIndex={0} role="region" aria-label="퍼널 단계">
          <table>
            <thead><tr><th>순서</th><th>이벤트</th><th>구분</th><th>조건</th><th>위치</th><th>속성</th></tr></thead>
            <tbody>
              {m.funnel.map((s) => (
                <tr key={s.order} className={s.status === 'new' ? 'new' : ''}>
                  <td>{s.order}</td>
                  <td><code>{s.eventName}</code></td>
                  <td><span className={`tag ${s.status}`}>{s.status === 'new' ? '신규' : '기존'}</span></td>
                  <td>{s.condition ?? '-'}</td>
                  <td>{s.location ? <code>{locationText(s.location)}</code> : '-'}</td>
                  <td>{s.properties.length ? s.properties.map((p) => `${p.name}: ${p.type}`).join(', ') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export default function ProposalCard({ p, onUpdated }: { p: Proposal; onUpdated: (p: Proposal) => void }) {
  const [note, setNote] = useState(p.decision.note ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function decide(status: DecisionStatus) {
    setSaving(true)
    setError('')
    try {
      const updated = await updateProposal(p.id, { status, note: note.trim() ? note.trim() : null })
      setNote(updated.decision.note ?? '')
      onUpdated(updated)
    } catch (e) {
      setError(describe(e))
    } finally {
      setSaving(false)
    }
  }

  const body = {
    evidence: <ul className="evidence">{p.evidence.map((e, i) => <EvidenceItem key={i} e={e} />)}</ul>,
    proposal: <Markdown>{p.proposal}</Markdown>,
    steps: <ol>{p.steps.map((s, i) => <li key={i}><Markdown>{s}</Markdown></li>)}</ol>,
    measurement: <Measurement m={p.measurement} />,
  }
  const d = p.decision
  return (
    <article className={`card ${d.status}`} aria-label={`제안 ${p.seq}: ${p.title}`}>
      <div className="card-head">
        <div className="muted">제안 {p.seq} · {TYPE_LABEL[p.type]}</div>
        <span className={`status ${d.status}`}>{DECISION_LABEL[d.status]}</span>
      </div>
      <h4>{p.title}</h4>
      {CARD_SECTIONS.map((s) => (
        // 제안 본문만 펼친 채 시작
        <details key={s.key} className="card-section" open={s.key === 'proposal'}>
          <summary><h5>{s.label}</h5></summary>
          <div className="card-body">{body[s.key]}</div>
        </details>
      ))}
      <div className="decision">
        <input
          value={note} maxLength={1000} aria-label="결정 메모" placeholder="메모 (예: KB-812로 이번 스프린트에 진행)"
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="decision-actions">
          {d.decidedAt && <span className="muted">{new Date(d.decidedAt).toLocaleString()}</span>}
          {d.status !== 'pending' && <button type="button" className="btn" disabled={saving} onClick={() => void decide('pending')}>되돌리기</button>}
          <button type="button" className="btn" disabled={saving} onClick={() => void decide('on_hold')}>보류</button>
          <button type="button" className="btn primary" disabled={saving} onClick={() => void decide('adopted')}>채택</button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>
    </article>
  )
}
