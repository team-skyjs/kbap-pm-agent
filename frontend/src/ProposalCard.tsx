import { useState } from 'react'
import { describe, updateProposal, type DecisionStatus, type Evidence, type FunnelStep, type Proposal } from './api.ts'

// 카드 네 영역은 정확히 이 순서다 (계약서 Proposal 필드 규칙). 렌더는 이 배열을 그대로 따른다.
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

function EvidenceItem({ e }: { e: Evidence }) {
  switch (e.kind) {
    case 'metric':
      return <li><b>[지표] {e.value}</b> {e.summary}<div className="muted">출처: {e.source}</div></li>
    case 'code':
      return (
        <li>
          <b>[코드] <code>{e.file}:{e.line}</code></b>{e.function && <> · <code>{e.function}</code></>} {e.summary}
          <pre>{e.snippet}</pre>
        </li>
      )
    case 'taxonomy':
      return <li><b>[택사노미] <code>{e.eventName}</code></b> {e.summary}</li>
  }
}

function Measurement({ m }: { m: Proposal['measurement'] }) {
  return (
    <>
      <div>핵심 지표: {m.primaryMetric}</div>
      <div>기준값: {m.baseline ?? '없음'} · 목표: {m.target ?? '없음'}</div>
      {m.funnel.length > 0 && (
        <table>
          <thead><tr><th>순서</th><th>이벤트</th><th>구분</th><th>조건</th><th>위치</th><th>속성</th></tr></thead>
          <tbody>
            {m.funnel.map((s) => (
              <tr key={s.order} className={s.status === 'new' ? 'new' : ''}>
                <td>{s.order}</td>
                <td><code>{s.eventName}</code></td>
                <td>{s.status === 'new' ? '신규' : '기존'}</td>
                <td>{s.condition ?? '-'}</td>
                <td>{s.location ? <code>{locationText(s.location)}</code> : '-'}</td>
                <td>{s.properties.length ? s.properties.map((p) => `${p.name}: ${p.type}`).join(', ') : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
    evidence: <ul>{p.evidence.map((e, i) => <EvidenceItem key={i} e={e} />)}</ul>,
    proposal: <p>{p.proposal}</p>,
    steps: <ol>{p.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>,
    measurement: <Measurement m={p.measurement} />,
  }
  const d = p.decision
  return (
    <div className={`card ${d.status}`}>
      <div className="muted">제안 {p.seq} · {TYPE_LABEL[p.type]}</div>
      <h4>{p.title}</h4>
      {CARD_SECTIONS.map((s) => (
        <section key={s.key}>
          <h5>{s.label}</h5>
          {body[s.key]}
        </section>
      ))}
      <div className="decision">
        <b>상태: {DECISION_LABEL[d.status]}</b>
        {d.decidedAt && <span className="muted"> · {new Date(d.decidedAt).toLocaleString()}</span>}
        <div className="composer">
          <input value={note} maxLength={1000} placeholder="메모 (예: KB-812로 이번 스프린트에 진행)" onChange={(e) => setNote(e.target.value)} />
          <button disabled={saving} onClick={() => void decide('adopted')}>채택</button>
          <button disabled={saving} onClick={() => void decide('on_hold')}>보류</button>
          {d.status !== 'pending' && <button disabled={saving} onClick={() => void decide('pending')}>미결정으로</button>}
        </div>
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  )
}
