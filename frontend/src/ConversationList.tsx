import { useEffect, useState } from 'react'
import { describe, listConversations, type ConversationSummary } from './api.ts'

export const displayTitle = (c: Pick<ConversationSummary, 'title'>) => c.title ?? '새 대화'

// version 변경 시 재조회 (메시지 완료·제안 변경 후 App이 증가)
export default function ConversationList({ version, currentId }: { version: number; currentId: number | null }) {
  const [items, setItems] = useState<ConversationSummary[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    listConversations().then(
      (r) => { setItems([...r.items].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))); setError('') },
      (e) => setError(describe(e)),
    )
  }, [version])
  return (
    <nav className="list">
      {error && <p className="error">{error}</p>}
      {!error && items.length === 0 && <p className="muted">대화가 없습니다.</p>}
      {items.map((c) => (
        <a key={c.id} href={`#/conversations/${c.id}`} className={c.id === currentId ? 'current' : ''}>
          <div>{displayTitle(c)}</div>
          <div className="muted">
            {new Date(c.updatedAt).toLocaleString()} · 제안 {c.proposalCount} · 채택 {c.adoptedCount}
          </div>
        </a>
      ))}
    </nav>
  )
}
