import { useEffect, useState } from 'react'
import { getHealth, MOCK } from './api.ts'

// ponytail: 경로가 두세 개라 라우터 라이브러리 대신 location.hash를 직접 읽는다. 경로가 늘면 react-router HashRouter로.
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

export default function App() {
  const hash = useHash()
  return (
    <>
      <header>
        <a href="#/"><b>K-Bap PM Agent</b></a>
        <a href="#/settings">설정</a>
        <HealthBadge />
        {MOCK && <span className="badge degraded">mock 데이터</span>}
      </header>
      <main style={{ padding: 16 }}>
        {hash === '#/settings' ? <p>설정 화면 (F5)</p> : <p>대화를 선택하거나 새로 시작하세요.</p>}
      </main>
    </>
  )
}
