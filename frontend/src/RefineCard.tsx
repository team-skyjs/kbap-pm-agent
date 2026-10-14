import { useEffect, useId, useRef } from 'react'

type Props = {
  original: string
  refined: string
  summary: string
  onSendRefined: () => void
  onSendOriginal: () => void
  onInsert: () => void
  onClose: () => void
  // 에이전트 실행 중에는 보내기·넣기를 막아 잘못된 선택 기록 방지
  busy?: boolean
}

// 다듬기 결과 비교 카드. 기록·전송은 호출한 쪽이 담당
export default function RefineCard({ original, refined, summary, onSendRefined, onSendOriginal, onInsert, onClose, busy = false }: Props) {
  const titleId = useId()
  const primary = useRef<HTMLButtonElement>(null)
  useEffect(() => { primary.current?.focus() }, [])
  // 포커스가 입력창으로 옮겨가도 ESC로 닫힘, Drawer가 열려 있으면 Drawer가 먼저
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !document.querySelector('[role="dialog"]')) onClose()
    }
    addEventListener('keydown', onKey)
    return () => removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <section className="refine-card" role="region" aria-labelledby={titleId}>
      <div className="refine-head">
        <h2 id={titleId}>질문 다듬기 결과</h2>
        <button type="button" className="icon-btn" aria-label="닫기" onClick={onClose}><span aria-hidden="true">✕</span></button>
      </div>
      <div className="refine-compare">
        <div className="refine-pane original">
          <h3>원문</h3>
          <p>{original}</p>
        </div>
        <div className="refine-pane refined">
          <h3>개선안</h3>
          <p>{refined}</p>
          <p className="refine-summary"><span className="sr-only">바뀐 점: </span>{summary}</p>
        </div>
      </div>
      <div className="refine-actions">
        <button type="button" className="btn" disabled={busy} onClick={onInsert}>입력창에 넣기</button>
        <span className="refine-send">
          <button type="button" className="btn" disabled={busy} onClick={onSendOriginal}>원문으로 보내기</button>
          <button type="button" className="btn primary" ref={primary} disabled={busy} onClick={onSendRefined}>개선안으로 보내기</button>
        </span>
      </div>
    </section>
  )
}
