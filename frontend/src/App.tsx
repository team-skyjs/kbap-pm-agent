import { useEffect, useRef, useState } from 'react'
import { createConversation, describe, getHealth } from './api.ts'
import Chat from './Chat.tsx'
import ConversationList from './ConversationList.tsx'
import SettingsPage from './SettingsPage.tsx'
import { ShellContext, Topbar, type Health } from './Shell.tsx'

// ponytail: 경로가 두세 개라 라우터 라이브러리 없이 location.hash 직접 사용, 경로가 늘면 react-router HashRouter로
function useHash(): string {
  const [hash, setHash] = useState(location.hash)
  useEffect(() => {
    const on = () => setHash(location.hash)
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return hash
}

// 분기점은 CSS 미디어 쿼리와 같은 값
const MOBILE = '(max-width: 768px)'
function useMobile(): boolean {
  const [m, setM] = useState(() => matchMedia(MOBILE).matches)
  useEffect(() => {
    const q = matchMedia(MOBILE)
    const on = () => setM(q.matches)
    q.addEventListener('change', on)
    return () => q.removeEventListener('change', on)
  }, [])
  return m
}

const COLLAPSED_KEY = 'kbap.sidebarCollapsed'
function readCollapsed(): boolean {
  try { return localStorage.getItem(COLLAPSED_KEY) === '1' } catch { return false }
}

function NewConversationButton({ onCreated }: { onCreated: () => void }) {
  const [error, setError] = useState('')
  async function create() {
    setError('')
    try {
      const c = await createConversation()
      onCreated()
      location.hash = `#/conversations/${c.id}`
    } catch (e) {
      setError(describe(e))
    }
  }
  return <>
    <button type="button" className="btn new-chat" onClick={() => void create()}>새 대화</button>
    {error && <p className="error sidebar-error">{error}</p>}
  </>
}

export default function App() {
  const hash = useHash()
  const mobile = useMobile()
  const [listVersion, setListVersion] = useState(0)
  const refreshList = () => setListVersion((v) => v + 1)
  const [health, setHealth] = useState<Health>('확인 중')
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [drawer, setDrawer] = useState(false)
  const sidebarRef = useRef<HTMLElement>(null)

  useEffect(() => {
    getHealth().then((h) => setHealth(h.status), () => setHealth('연결 실패'))
  }, [])
  useEffect(() => {
    try { localStorage.setItem(COLLAPSED_KEY, collapsed ? '1' : '0') } catch { /* 저장 불가 환경은 기본값 유지 */ }
  }, [collapsed])
  // 화면 이동·데스크톱 전환 시 Drawer 닫기
  useEffect(() => setDrawer(false), [hash, mobile])

  const drawerOpen = mobile && drawer
  useEffect(() => {
    if (!drawerOpen) return
    document.body.style.overflow = 'hidden'
    sidebarRef.current?.querySelector<HTMLElement>('button, a')?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawer(false) }
    addEventListener('keydown', onKey)
    return () => { document.body.style.overflow = ''; removeEventListener('keydown', onKey) }
  }, [drawerOpen])

  const sidebarOpen = mobile ? drawer : !collapsed
  const toggle = () => (mobile ? setDrawer((d) => !d) : setCollapsed((c) => !c))
  const conv = hash.match(/^#\/conversations\/(\d+)$/)

  return (
    <ShellContext.Provider value={{ sidebarOpen, mobile, toggle, health }}>
      <div className={`app${sidebarOpen ? '' : ' sidebar-closed'}`}>
        {drawerOpen && <div className="backdrop" onClick={() => setDrawer(false)} />}
        <aside
          ref={sidebarRef} className="sidebar" id="sidebar"
          {...(drawerOpen ? { role: 'dialog', 'aria-modal': true, 'aria-label': '사이드 패널' } : {})}
        >
          <div className="sidebar-top">
            <a href="#/" className="brand">K-Bap PM Agent</a>
            {!mobile && (
              <button type="button" className="icon-btn" aria-label="사이드 패널 접기" aria-expanded={true} onClick={toggle}>
                <span aria-hidden="true">☰</span>
              </button>
            )}
          </div>
          <NewConversationButton onCreated={refreshList} />
          <ConversationList version={listVersion} currentId={conv ? Number(conv[1]) : null} />
          <a href="#/settings" className="sidebar-link" aria-current={hash === '#/settings' ? 'page' : undefined}>설정</a>
        </aside>
        <div className="main">
          {hash === '#/settings' ? <>
            <Topbar title="설정" />
            <div className="scroll"><div className="thread"><SettingsPage /></div></div>
          </>
            : conv ? <Chat key={conv[1]} id={Number(conv[1])} onChanged={refreshList} />
            : <>
              <Topbar title="K-Bap PM Agent" />
              <div className="scroll"><div className="thread empty"><p className="muted">대화를 선택하거나 새로 시작하세요.</p></div></div>
            </>}
        </div>
      </div>
    </ShellContext.Provider>
  )
}
