// 브라우저 인쇄(PDF 저장)의 앞뒤 처리. Ctrl+P로 바로 인쇄해도 같은 이벤트가 와서 결과가 같음
import { recordExport, type ConversationDetail } from './api.ts'

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
  // 기록은 메뉴·Ctrl+P 어느 경로든 여기 한 곳에서 한 번. 인쇄 머리글이 없는 화면(설정 등)은 기록하지 않음
  const id = Number(document.querySelector<HTMLElement>('.print-header[data-conversation-id]')?.dataset.conversationId)
  // 기다리지 않고 실패도 무시(내보내기를 막지 않음)
  if (id > 0) void recordExport(id, 'pdf').catch(() => {})
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

// 차트는 지연 청크라 인쇄 전에 받아 두고 한 프레임 그린 뒤 인쇄
// ponytail: Ctrl+P로 바로 인쇄하면 이 대기를 거치지 않아, 차트 청크가 아직 없으면 차트가 빠질 수 있음
export async function startPrint(detail: ConversationDetail): Promise<void> {
  if (detail.messages.some((m) => /^```chart\s*$/m.test(m.content))) {
    await import('./ChartBlock.tsx')
    await new Promise((r) => requestAnimationFrame(r))
  }
  window.print()
}
