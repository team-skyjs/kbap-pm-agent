import { useEffect, useState } from 'react'
import { createConversation, describe, getHealth } from './api.ts'
import Chat from './Chat.tsx'
import ConversationList from './ConversationList.tsx'
import SettingsPage from './SettingsPage.tsx'

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

function HealthBadge() {
  const [label, setLabel] = useState<'확인 중' | 'ok' | 'degraded' | '연결 실패'>('확인 중')
  useEffect(() => {
    getHealth().then((h) => setLabel(h.status), () => setLabel('연결 실패'))
  }, [])
  const cls = label === 'ok' ? 'ok' : label === 'degraded' ? 'degraded' : label === '연결 실패' ? 'down' : ''
  return <span className={`badge ${cls}`} title="GET /api/health">서버: {label}</span>
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
  return <>{' '}<button onClick={() => void create()}>새 대화</button>{error && <span className="error"> {error}</span>}</>
}

export default function App() {
  const hash = useHash()
  const [listVersion, setListVersion] = useState(0)
  const refreshList = () => setListVersion((v) => v + 1)
  const conv = hash.match(/^#\/conversations\/(\d+)$/)
  return (
    <>
      <header>
        <a href="#/"><b>K-Bap PM Agent</b></a>
        <a href="#/settings">설정</a>
        <HealthBadge />
        <NewConversationButton onCreated={refreshList} />
      </header>
      <div className="layout">
      <ConversationList version={listVersion} currentId={conv ? Number(conv[1]) : null} />
      <main>
        {hash === '#/settings' ? <SettingsPage />
          : conv ? <Chat key={conv[1]} id={Number(conv[1])} onChanged={refreshList} />
          : <p>대화를 선택하거나 새로 시작하세요.</p>}
      </main>
      </div>
    </>
  )
}
