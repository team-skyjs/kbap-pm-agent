import { useEffect, useState } from 'react'
import {
  describe, getSettings, getToken, putRepository, putTaxonomy, setToken, syncRepository,
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

  const load = () => getSettings().then((x) => { setS(x); setLoadError('') }, (e) => setLoadError(describe(e)))
  useEffect(() => { void load() }, [])
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
              <span className={`status ${s.amplitude.status === 'configured' ? 'ok' : ''}`}>{s.amplitude.status === 'configured' ? '서버 키로 연결됨' : '키 없음'}</span>
            </h2>
            {/* 키는 서버 환경 변수로만 관리, 화면에서는 상태만 */}
            {s.amplitude.status === 'missing' && (
              <p className="muted">서버 환경 변수 <code>AMPLITUDE_API_KEY</code>와 <code>AMPLITUDE_SECRET_KEY</code>를 설정한 뒤 서버를 다시 시작하세요. 키가 없으면 Amplitude 없이 답합니다.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
