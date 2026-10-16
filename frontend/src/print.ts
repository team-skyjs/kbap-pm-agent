// 브라우저 인쇄(PDF 저장)의 앞뒤 처리. Ctrl+P로 바로 인쇄해도 같은 이벤트가 와서 결과가 같음
import { recordExport } from './api.ts'

const pad = (n: number) => String(n).padStart(2, '0')
export const today = (d = new Date()) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

// 닫힌 제안 카드 절은 인쇄되지 않으므로 인쇄 동안만 열고, 직접 연 것만 다시 닫음
const openedForPrint = new Set<HTMLDetailsElement>()

function beforePrint() {
  for (const d of document.querySelectorAll<HTMLDetailsElement>('details.card-section:not([open])')) {
    d.open = true
    openedForPrint.add(d)
  }
  for (const el of document.querySelectorAll<HTMLElement>('[data-print-date]')) el.textContent = today()
}

function afterPrint() {
  for (const d of openedForPrint) d.open = false
  openedForPrint.clear()
}

export function installPrintSupport(): () => void {
  addEventListener('beforeprint', beforePrint)
  addEventListener('afterprint', afterPrint)
  return () => {
    removeEventListener('beforeprint', beforePrint)
    removeEventListener('afterprint', afterPrint)
  }
}

// 기록은 기다리지 않고 실패도 무시(내보내기를 막지 않음)
export function startPrint(conversationId: number): void {
  void recordExport(conversationId, 'pdf').catch(() => {})
  window.print()
}
