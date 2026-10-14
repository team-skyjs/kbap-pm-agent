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
  const feedback = (area: string) => msg[area] && (
    <p className={msg[area].startsWith('오류') ? 'feedback error' : 'feedback muted'} role="status">{msg[area]}</p>
  )
  return (
    <div className="settings">
      <section>
        <h2>접근 토큰</h2>
        <p className="muted">백엔드에 ACCESS_TOKEN이 설정된 경우에만 필요합니다. 이 브라우저에만 저장됩니다.</p>
        <div className="field-row">
          <input type="password" value={token} onChange={(e) => setTokenInput(e.target.value)} placeholder="토큰" aria-label="접근 토큰" />
          <button type="button" className="btn primary" onClick={saveToken}>저장</button>
        </div>
        {feedback('token')}
      </section>

      {loadError && <p className="error">{loadError}</p>}
      {!s && !loadError && <p className="muted">불러오는 중…</p>}
      {s && (
        <>
          <section>
            <h2>상태</h2>
            <dl className="metric">
              <dt>실행 모드</dt><dd>{s.agentMode === 'fake' ? 'fake (시연)' : 'real'}</dd>
              <dt>모델</dt><dd>에이전트 <code>{s.models.agent}</code> · 코드 요약 <code>{s.models.codeSummary}</code></dd>
              <dt>예산</dt><dd>${s.budget.spentUsd.toFixed(4)} / ${s.budget.limitUsd.toFixed(2)}</dd>
            </dl>
          </section>

          <section>
            <h2>FE 저장소 <span className={`status ${r ? (r.lastError ? 'down' : 'ok') : ''}`}>{r ? (r.lastError ? '오류' : '등록됨') : '미등록'}</span></h2>
            {r ? (
              <dl className="metric">
                <dt>저장소</dt><dd><code>{r.url}</code> ({r.branch})</dd>
                <dt>커밋</dt><dd><code>{r.headCommit}</code></dd>
                <dt>코드 맵</dt><dd>{r.codeMapStatus}{r.codeMapCommit && ` (${r.codeMapCommit})`} · 화면 {r.screenCount}개 · 추적 이벤트 {r.trackedEventCount}곳</dd>
                <dt>마지막 동기화</dt><dd>{time(r.syncedAt)}</dd>
              </dl>
            ) : <p className="muted">등록된 저장소가 없습니다.</p>}
            {r?.lastError && <p className="error">마지막 오류: {r.lastError}</p>}
            <div className="field-row">
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/team-skyjs/kbap-fe" aria-label="저장소 주소" />
              <input className="branch-input" value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="브랜치 (비우면 기본)" aria-label="브랜치" />
              <button type="button" className="btn primary" disabled={busy !== '' || !url.trim()} onClick={() => void saveRepo()}>등록</button>
              <button type="button" className="btn" disabled={busy !== '' || !r} onClick={() => void sync()}>동기화</button>
            </div>
            {busy === 'repo' && <p className="feedback muted" role="status">클론·인덱싱 중…</p>}
            {feedback('repo')}
          </section>

          <section>
            <h2>택사노미 <span className={`status ${s.taxonomy ? 'ok' : ''}`}>{s.taxonomy ? '업로드됨' : '없음'}</span></h2>
            {s.taxonomy ? <p>이벤트 {s.taxonomy.eventCount}개 · 갱신 {time(s.taxonomy.uploadedAt)}</p> : <p className="muted">업로드된 택사노미가 없습니다.</p>}
            <label className="btn file-btn">
              JSON 파일 선택
              <input
                type="file" accept=".json,application/json" disabled={busy !== ''} className="visually-hidden"
                onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = '' }}
              />
            </label>
            {feedback('taxonomy')}
          </section>

          <section>
            <h2>
              Amplitude{' '}
              <span className={`status ${s.amplitude.status === 'connected' ? 'ok' : ''}`}>{s.amplitude.status === 'connected' ? '연결됨' : '미연결'}</span>
            </h2>
            <dl className="metric">
              <dt>서버</dt><dd><code>{s.amplitude.serverUrl}</code></dd>
              {s.amplitude.status === 'connected' && <><dt>연결 시각</dt><dd>{time(s.amplitude.connectedAt)}</dd></>}
            </dl>
            <button type="button" className="btn primary" disabled={busy !== ''} onClick={connect}>{s.amplitude.status === 'connected' ? '다시 연결' : '연결'}</button>
            {feedback('amplitude')}
          </section>
        </>
      )}
    </div>
  )
}
