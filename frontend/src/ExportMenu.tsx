import { useEffect, useId, useRef, useState } from 'react'
import { recordExport, type ConversationDetail } from './api.ts'
import { exportFileName, toMarkdown } from './exportMarkdown.ts'
import { startPrint } from './print.ts'

// 화면이 가진 대화 상세로 파일을 만들어 내려받음(서버 재호출 없음)
function downloadMarkdown(detail: ConversationDetail) {
  void recordExport(detail.id, 'markdown').catch(() => {})
  const now = new Date()
  const url = URL.createObjectURL(new Blob([toMarkdown(detail, now)], { type: 'text/markdown;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = exportFileName(detail.title, detail.id, now)
  document.body.append(a)
  a.click()
  a.remove()
  // 클릭 처리 뒤 해제
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

export default function ExportMenu({ detail, disabled }: { detail: ConversationDetail; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const menuId = useId()

  const close = (returnFocus: boolean) => {
    setOpen(false)
    if (returnFocus) button.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close(true) }
    // 메뉴 밖 클릭이나 포커스 이동이면 닫음
    const onOutside = (e: Event) => {
      const t = e.target
      if (t instanceof Node && !menu.current?.contains(t) && !button.current?.contains(t)) close(false)
    }
    addEventListener('keydown', onKey)
    addEventListener('pointerdown', onOutside)
    addEventListener('focusin', onOutside)
    return () => {
      removeEventListener('keydown', onKey)
      removeEventListener('pointerdown', onOutside)
      removeEventListener('focusin', onOutside)
    }
  }, [open])

  return (
    <div className="export-menu">
      <button
        ref={button} type="button" className="btn export-btn" disabled={disabled}
        aria-haspopup="menu" aria-expanded={open} aria-controls={menuId} onClick={() => setOpen((o) => !o)}
      >
        내보내기
      </button>
      {open && (
        <div ref={menu} id={menuId} role="menu" aria-label="내보내기 형식" className="export-list">
          <button type="button" role="menuitem" onClick={() => { close(true); startPrint(detail.id) }}>PDF로 인쇄</button>
          <button type="button" role="menuitem" onClick={() => { close(true); downloadMarkdown(detail) }}>Markdown 파일</button>
        </div>
      )}
    </div>
  )
}
