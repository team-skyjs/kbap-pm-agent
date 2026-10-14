import { useEffect, useRef, useState } from 'react'
import {
  connectAmplitude, describe, getSettings, getToken, putRepository, putTaxonomy, setToken, syncRepository,
  type Settings,
} from './api.ts'

const time = (s: string | null) => (s ? new Date(s).toLocaleString() : '-')

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null)
  const [loadError, setLoadError] = useState('')
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [token, setTokenInput] = useState(getToken())
  const [busy, setBusy] = useState('')
  const [msg, setMsg] = useState<Record<string, string>>({})
  const poll = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = () => getSettings().then((x) => { setS(x); setLoadError('') }, (e) => setLoadError(describe(e)))
  useEffect(() => {
    void load()
    return () => { if (poll.current) clearInterval(poll.current) }
  }, [])
  useEffect(() => {
    if (s?.repository && !url) { setUrl(s.repository.url); setBranch(s.repository.branch) }
  }, [s])

  // 영역별 실행과 결과 문구, 실패 시 서버 message 그대로 표시
  async function run(area: string, f: () => Promise<string>) {
    setBusy(area)
    setMsg((m) => ({ ...m, [area]: '' }))
    try {
      const ok = await f()
      setMsg((m) => ({ ...m, [area]: ok }))
    } catch (e) {
      setMsg((m) => ({ ...m, [area]: `오류: ${describe(e)}` }))
    } finally {
      setBusy('')
    }
  }

  const saveRepo = () => run('repo', async () => {
    const repository = await putRepository(url.trim(), branch.trim())
    setS((x) => (x ? { ...x, repository } : x))
    return '등록했습니다.'
  })
  const sync = () => run('repo', async () => {
    const repository = await syncRepository()
    setS((x) => (x ? { ...x, repository } : x))
    return '동기화했습니다.'
  })
  const upload = (file: File | undefined) => file && run('taxonomy', async () => {
    const taxonomy = await putTaxonomy(await file.text())
    setS((x) => (x ? { ...x, taxonomy } : x))
    return `업로드했습니다: 이벤트 ${taxonomy.eventCount}개`
  })

  function connect() {
    // 팝업 차단 회피: 클릭 시점에 빈 탭부터 열기
    const tab = window.open('', '_blank')
    void run('amplitude', async () => {
      try {
        const { authorizationUrl } = await connectAmplitude()
        if (tab) tab.location.href = authorizationUrl
        else window.open(authorizationUrl, '_blank')
      } catch (e) {
        tab?.close()
        throw e
      }
      // 승인 완료는 응답으로 알 수 없어 settings 재조회로 확인 (3초 간격, 최대 2분)
      if (poll.current) clearInterval(poll.current)
      let tries = 0
      poll.current = setInterval(async () => {
        tries++
        const x = await getSettings().catch(() => null)
        if (x) setS(x)
        if (x?.amplitude.status === 'connected' || tries >= 40) {
          if (poll.current) clearInterval(poll.current)
          setMsg((m) => ({ ...m, amplitude: x?.amplitude.status === 'connected' ? '연결되었습니다.' : '2분 안에 승인이 확인되지 않았습니다. 다시 시도하세요.' }))
        }
      }, 3000)
      return '새 탭에서 Amplitude 승인을 마치세요. 상태를 확인하는 중…'
    })
  }

  function saveToken() {
    setToken(token.trim())
    setMsg((m) => ({ ...m, token: token.trim() ? '저장했습니다.' : '지웠습니다.' }))
    void load()
  }

  const r = s?.repository
  return (
    <div className="settings">
      <h3>설정</h3>

      <section>
        <h4>접근 토큰</h4>
        <p className="muted">백엔드에 ACCESS_TOKEN이 설정된 경우에만 필요합니다. 이 브라우저에만 저장됩니다.</p>
        <div className="composer">
          <input type="password" value={token} onChange={(e) => setTokenInput(e.target.value)} placeholder="토큰" />
          <button onClick={saveToken}>저장</button>
        </div>
        {msg.token && <div>{msg.token}</div>}
      </section>

      {loadError && <p className="error">{loadError}</p>}
      {!s && !loadError && <p>불러오는 중…</p>}
      {s && (
        <>
          <section>
            <h4>상태</h4>
            <div>실행 모드: <b>{s.agentMode === 'fake' ? 'fake (시연)' : 'real'}</b></div>
            <div>모델: 에이전트 <code>{s.models.agent}</code> · 코드 요약 <code>{s.models.codeSummary}</code></div>
            <div>예산: ${s.budget.spentUsd.toFixed(4)} / ${s.budget.limitUsd.toFixed(2)}</div>
          </section>

          <section>
            <h4>FE 저장소</h4>
            {r ? (
              <div>
                <div><code>{r.url}</code> ({r.branch}) · 커밋 <code>{r.headCommit}</code></div>
                <div>코드 맵: {r.codeMapStatus}{r.codeMapCommit && ` (${r.codeMapCommit})`} · 화면 {r.screenCount}개 · 추적 이벤트 {r.trackedEventCount}곳</div>
                <div>동기화: {time(r.syncedAt)}</div>
                {r.lastError && <div className="error">마지막 오류: {r.lastError}</div>}
              </div>
            ) : <div className="muted">등록된 저장소가 없습니다.</div>}
            <div className="composer">
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/team-skyjs/kbap-fe" />
              <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="브랜치 (비우면 기본)" style={{ flex: '0 0 160px' }} />
              <button disabled={busy !== '' || !url.trim()} onClick={() => void saveRepo()}>등록</button>
              <button disabled={busy !== '' || !r} onClick={() => void sync()}>동기화</button>
            </div>
            {busy === 'repo' && <div>클론·인덱싱 중…</div>}
            {msg.repo && <div className={msg.repo.startsWith('오류') ? 'error' : ''}>{msg.repo}</div>}
          </section>

          <section>
            <h4>택사노미</h4>
            {s.taxonomy ? <div>이벤트 {s.taxonomy.eventCount}개 · 갱신 {time(s.taxonomy.uploadedAt)}</div> : <div className="muted">업로드된 택사노미가 없습니다.</div>}
            <input
              type="file" accept=".json,application/json" disabled={busy !== ''}
              onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = '' }}
            />
            {msg.taxonomy && <div className={msg.taxonomy.startsWith('오류') ? 'error' : ''}>{msg.taxonomy}</div>}
          </section>

          <section>
            <h4>Amplitude</h4>
            <div>
              {s.amplitude.status === 'connected' ? `연결됨 (${time(s.amplitude.connectedAt)})` : '연결 안 됨'} · <code>{s.amplitude.serverUrl}</code>
            </div>
            <button disabled={busy !== ''} onClick={connect}>{s.amplitude.status === 'connected' ? '다시 연결' : '연결'}</button>
            {msg.amplitude && <div className={msg.amplitude.startsWith('오류') ? 'error' : ''}>{msg.amplitude}</div>}
          </section>
        </>
      )}
    </div>
  )
}
