import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import Markdown from './Markdown.tsx'
import {
  ApiError, describe, errorText, getConversation, sendMessage,
  type ConversationDetail, type Message, type Proposal, type StreamEvent, type ToolCall,
} from './api.ts'
import ProposalCard from './ProposalCard.tsx'
import { SessionBanner, Topbar } from './Shell.tsx'

const SOURCE_LABEL: Record<ToolCall['source'], string> = { amplitude: 'Amplitude', code: '코드', taxonomy: '택사노미' }

function upsertTool(list: ToolCall[], t: ToolCall): ToolCall[] {
  const rest = list.filter((x) => x.id !== t.id)
  return [...rest, t].sort((a, b) => a.seq - b.seq)
}

export type ViewState = 'sending' | 'progress' | 'done' | 'partial' | 'error'

// 상한 중단 시 서버가 본문 첫 문장에 넣는 사유 문구의 앞부분
const LIMIT_PREFIXES = ['모델 호출 상한(', '실행 시간 상한(']

export function viewState(m: Pick<Message, 'status' | 'content' | 'toolCalls'>): ViewState {
  if (m.status === 'failed') return 'error'
  if (m.status === 'running') return m.toolCalls.length ? 'progress' : 'sending'
  return LIMIT_PREFIXES.some((x) => m.content.startsWith(x)) ? 'partial' : 'done'
}

// 사유 첫 문장과 나머지 본문 분리
function splitReason(content: string): [string, string] {
  const i = content.search(/[.。]\s|\n/)
  return i < 0 ? [content, ''] : [content.slice(0, i + 1).trim(), content.slice(i + 1).trim()]
}

const TOOL_MARK: Record<ToolCall['status'], string> = { running: '…', succeeded: '✓', failed: '✕' }

function ToolRow({ calls, running }: { calls: ToolCall[]; running: boolean }) {
  const cur = [...calls].reverse().find((t) => t.status === 'running')
  const failed = calls.filter((t) => t.status === 'failed').length
  // 완료 요약은 호출 상태에서 유도, 실패가 하나라도 있으면 경고 표기
  const summary = cur ? `${SOURCE_LABEL[cur.source]} 조회 중… (${cur.name})`
    : running ? `조회 ${calls.length}건 완료, 답변 정리 중…`
    : failed ? `⚠ 조회 ${calls.length}건 중 ${failed}건 실패` : `✓ 조회 ${calls.length}건`
  return (
    <details className={failed && !cur && !running ? 'tools has-failed' : 'tools'}>
      <summary aria-live={running ? 'polite' : undefined}>{summary}</summary>
      <ol>
        {calls.map((t) => (
          <li key={t.id} className={t.status === 'failed' ? 'failed' : undefined}>
            <span aria-hidden="true">{TOOL_MARK[t.status]} </span>
            {t.status === 'failed' ? <span className="tool-failed">실패 </span>
              : <span className="sr-only">{t.status === 'running' ? '실행 중' : '완료'}: </span>}
            {SOURCE_LABEL[t.source]} <code>{t.name}</code>
            {t.durationMs !== null && ` · ${t.durationMs}ms`}
            {t.resultSummary && <div>{t.resultSummary}</div>}
          </li>
        ))}
      </ol>
    </details>
  )
}

function MessageView({ m, streamError, onProposal, onRetry }: {
  m: Message; streamError?: string; onProposal: (p: Proposal) => void; onRetry?: () => void
}) {
  if (m.role === 'user') {
    return (
      <div className="msg user" title={new Date(m.createdAt).toLocaleString()}>
        <span className="sr-only">나:</span>
        <p className="user-text">{m.content}</p>
      </div>
    )
  }
  const state = viewState(m)
  const [reason, rest] = state === 'partial' ? splitReason(m.content) : ['', m.content]
  return (
    <div className={`msg assistant ${state}`} title={new Date(m.createdAt).toLocaleString()}>
      <span className="sr-only">에이전트:</span>
      {state === 'sending' && <div className="typing" role="status" aria-label="에이전트 실행 중"><span /><span /><span /></div>}
      {m.toolCalls.length > 0 && <ToolRow calls={m.toolCalls} running={m.status === 'running'} />}
      {state === 'partial' && <div className="notice-block" role="note">{reason}</div>}
      {rest && <Markdown>{rest}</Markdown>}
      {state === 'error' && (
        <div className="error-row" role="alert">
          <span className="error">실행 실패: {streamError ?? errorText(m.errorCode ?? 'INTERNAL_ERROR')}</span>
          {onRetry && <button type="button" className="btn" onClick={onRetry}>다시 시도</button>}
        </div>
      )}
      {m.proposals.map((p) => <ProposalCard key={p.id} p={p} onUpdated={onProposal} />)}
      {m.usage && (
        <div className="muted usage">
          {m.usage.model} · 입력 {m.usage.inputTokens} / 출력 {m.usage.outputTokens} 토큰 · ${m.usage.costUsd.toFixed(4)}
        </div>
      )}
    </div>
  )
}

export default function Chat({ id, onChanged }: { id: number; onChanged: () => void }) {
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [loadError, setLoadError] = useState('')
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [notice, setNotice] = useState('')
  const [streamErrors, setStreamErrors] = useState<Record<number, string>>({})
  const [sessionExpired, setSessionExpired] = useState(false)
  const [tokenError, setTokenError] = useState(false)
  // 409 안내를 지울 판단 기준: 409 이후에 보낸 재조회 결과만 사용
  const [busyFrom, setBusyFrom] = useState<number | null>(null)
  const loadSeq = useRef(0)
  const [loadedSeq, setLoadedSeq] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  // 사용자가 맨 아래를 보고 있을 때만 자동 스크롤
  const atBottom = useRef(true)

  const applied = useRef(0)
  const load = useCallback(() => {
    const seq = ++loadSeq.current
    getConversation(id).then((d) => {
      // 늦게 도착한 이전 응답이 새 상태를 덮지 않도록 버림
      if (seq < applied.current) return
      applied.current = seq
      setDetail(d); setLoadedSeq(seq); setLoadError('')
    }, (e) => setLoadError(describe(e)))
  }, [id])

  useEffect(() => { setDetail(null); setNotice(''); load() }, [load])

  const running = detail?.messages.some((m) => m.status === 'running') ?? false

  // 스트림 없는 실행 중 메시지(다른 탭·끊긴 실행)는 3초마다 상세 재조회
  useEffect(() => {
    if (!running || streaming) return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [running, streaming, load])

  const setMessages = (f: (ms: Message[]) => Message[]) => setDetail((d) => (d ? { ...d, messages: f(d.messages) } : d))
  const patchMessage = (mid: number, f: (m: Message) => Message) => setMessages((ms) => ms.map((m) => (m.id === mid ? f(m) : m)))

  function onEvent(e: StreamEvent) {
    switch (e.event) {
      case 'message_created': {
        const u = e.data.userMessage
        // 계약상 실행 중 메시지 형태: content "", proposals [], usage null
        const placeholder: Message = {
          id: e.data.assistantMessageId, conversationId: u.conversationId, role: 'assistant', status: 'running',
          content: '', errorCode: null, toolCalls: [], proposals: [], usage: null, createdAt: u.createdAt,
        }
        setMessages((ms) => [...ms, u, placeholder])
        onChanged()
        return
      }
      case 'tool_call':
      case 'tool_result': {
        const t = e.data
        setMessages((ms) => ms.map((m) => (m.status === 'running' ? { ...m, toolCalls: upsertTool(m.toolCalls, t) } : m)))
        return
      }
      case 'final':
        patchMessage(e.data.id, () => e.data)
        return
      case 'error': {
        const { assistantMessageId, error } = e.data
        setStreamErrors((s) => ({ ...s, [assistantMessageId]: errorText(error.code, error.message) }))
        patchMessage(assistantMessageId, (m) => ({ ...m, status: 'failed', errorCode: error.code }))
        return
      }
    }
  }

  function onProposal(p: Proposal) {
    patchMessage(p.messageId, (m) => ({ ...m, proposals: m.proposals.map((x) => (x.id === p.id ? p : x)) }))
    onChanged()
  }

  async function submit() {
    const content = input.trim()
    if (!content || streaming) return
    setNotice('')
    setTokenError(false)
    setBusyFrom(null)
    setStreaming(true)
    try {
      const end = await sendMessage(id, content, onEvent)
      setInput('')
      if (end === 'disconnected') setNotice('스트림이 끊겨 저장된 상태를 다시 불러왔습니다.')
      // 종료 후 항상 상세 재조회: 서버가 채운 제목과 저장 상태 반영
      load()
    } catch (e) {
      // 스트림 시작 전 에러(실행 중, 예산 초과, 입력 오류 등)는 입력창 아래에 안내
      setNotice(describe(e))
      setTokenError(e instanceof ApiError && e.code === 'UNAUTHORIZED')
      // 토큰 문제(UNAUTHORIZED)는 설정 안내로 충분, 배너는 세션 만료 코드에만. 이 코드는 접근 제한 머지 후 생김
      if (e instanceof ApiError) {
        const code: string = e.code
        if (code === 'SESSION_EXPIRED') setSessionExpired(true)
      }
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS') { setBusyFrom(loadSeq.current + 1); load() }
    } finally {
      setStreaming(false)
      onChanged()
    }
  }

  // 다른 실행 중 안내는 그 실행이 끝나 입력이 풀리면 지움
  useEffect(() => {
    if (busyFrom !== null && loadedSeq >= busyFrom && !running) { setNotice(''); setBusyFrom(null) }
  }, [running, loadedSeq])

  // 빈 대화를 열면 바로 입력하도록 입력창에 포커스
  const empty = detail?.messages.length === 0
  useEffect(() => { if (empty) inputRef.current?.focus() }, [empty])

  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el && atBottom.current) el.scrollTop = el.scrollHeight
  }, [detail])

  // field-sizing 미지원 브라우저용 자동 높이
  useLayoutEffect(() => {
    const ta = inputRef.current
    if (!ta || CSS.supports('field-sizing', 'content')) return
    ta.style.height = 'auto'
    ta.style.height = `${ta.scrollHeight}px`
  }, [input])

  function onScroll() {
    const el = scrollRef.current
    if (el) atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }

  // 실패한 답변 직전의 사용자 질문을 입력창에 되돌림
  function retry(index: number) {
    const prev = detail?.messages.slice(0, index).reverse().find((m) => m.role === 'user')
    if (prev) setInput(prev.content)
    inputRef.current?.focus()
  }

  if (loadError) return <><Topbar title="대화" /><div className="scroll"><div className="thread"><p className="error">{loadError}</p></div></div></>
  if (!detail) return <><Topbar title="대화" /><div className="scroll"><div className="thread"><p className="muted">불러오는 중…</p></div></div></>
  const disabled = streaming || running
  return (
    <>
      <Topbar title={detail.title ?? '새 대화'} />
      {sessionExpired && <SessionBanner />}
      <div className="scroll" ref={scrollRef} onScroll={onScroll}>
        <div className="thread chat">
          {detail.messages.length === 0 && <p className="muted empty">질문을 입력하세요. 예: 스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘</p>}
          {detail.messages.map((m, i) => (
            <MessageView
              key={m.id} m={m} streamError={streamErrors[m.id]} onProposal={onProposal}
              onRetry={disabled ? undefined : () => retry(i)}
            />
          ))}
        </div>
      </div>
      <div className="chat-input-wrap">
        <div className="chat-input">
          <textarea
            ref={inputRef} value={input} rows={1} maxLength={4000} disabled={disabled} aria-label="질문 입력"
            aria-describedby="chat-hint" placeholder="질문을 입력하세요"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              // 한글 조합 중 Enter는 글자 확정용이라 전송하지 않음
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void submit() }
            }}
          />
          <button type="button" className="btn primary" onClick={() => void submit()} disabled={disabled || !input.trim()}>보내기</button>
        </div>
        <p id="chat-hint" className={notice ? 'hint error' : 'hint muted'} aria-live="polite">
          {tokenError
            ? <>접근 토큰이 없거나 맞지 않습니다. <a href="#/settings">설정에서 확인하세요</a></>
            : notice || (disabled ? '에이전트 실행 중에는 보낼 수 없습니다' : 'Enter로 전송, Shift+Enter로 줄바꿈')}
        </p>
      </div>
    </>
  )
}
