import { createContext, useContext, type ReactNode } from 'react'

export type Health = '확인 중' | 'ok' | 'degraded' | '연결 실패'

type Shell = { sidebarOpen: boolean; mobile: boolean; toggle: () => void; health: Health }
export const ShellContext = createContext<Shell>({ sidebarOpen: true, mobile: false, toggle: () => {}, health: '확인 중' })

function HealthBadge({ label }: { label: Health }) {
  const cls = label === 'ok' ? 'ok' : label === 'degraded' ? 'degraded' : label === '연결 실패' ? 'down' : ''
  return <span className={`badge ${cls}`} title="GET /api/health">서버: {label}</span>
}

// 화면마다 제목이 달라 각 화면이 직접 렌더링
export function Topbar({ title, children }: { title: string; children?: ReactNode }) {
  const { sidebarOpen, mobile, toggle, health } = useContext(ShellContext)
  const label = mobile ? '메뉴 열기' : sidebarOpen ? '사이드 패널 접기' : '사이드 패널 펼치기'
  return (
    <header className="topbar">
      {(mobile || !sidebarOpen) && (
        <button type="button" className="icon-btn" data-menu-button aria-label={label} aria-expanded={sidebarOpen} aria-controls="sidebar" onClick={toggle}>
          <span aria-hidden="true">☰</span>
        </button>
      )}
      <h1 className="topbar-title" title={title}>{title}</h1>
      {children}
      <HealthBadge label={health} />
    </header>
  )
}

// 표시만 담당, 보이기 조건은 호출하는 화면이 판단
export function SessionBanner() {
  return (
    <div className="session-banner" role="alert">
      <span>로그인이 만료되었습니다. 다시 로그인한 뒤 보내 주세요.</span>
      <button type="button" className="btn" onClick={() => location.reload()}>다시 로그인</button>
    </div>
  )
}
