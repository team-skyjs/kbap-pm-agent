import { useCallback, useEffect, useState } from 'react'
import Markdown from './Markdown.tsx'
import {
  ApiError, describe, errorText, getConversation, sendMessage,
  type ConversationDetail, type Message, type Proposal, type StreamEvent, type ToolCall,
} from './api.ts'
import ProposalCard from './ProposalCard.tsx'
import { Topbar } from './Shell.tsx'

const SOURCE_LABEL: Record<ToolCall['source'], string> = { amplitude: 'Amplitude', code: '코드', taxonomy: '택사노미' }

function upsertTool(list: ToolCall[], t: ToolCall): ToolCall[] {
  const rest = list.filter((x) => x.id !== t.id)
  return [...rest, t].sort((a, b) => a.seq - b.seq)
}

function ToolCalls({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null
  return (
    <details className="tools">
      <summary>도구 호출 {calls.length}개</summary>
      <ol>
        {calls.map((t) => (
          <li key={t.id}>
            [{SOURCE_LABEL[t.source]}] <code>{t.name}</code> {t.status === 'running' ? '실행 중' : t.status === 'failed' ? '실패' : '완료'}
            {t.durationMs !== null && ` · ${t.durationMs}ms`}
            {t.resultSummary && <div>{t.resultSummary}</div>}
            <div className="muted"><code>{JSON.stringify(t.input)}</code></div>
          </li>
        ))}
      </ol>
    </details>
  )
}

function Progress({ calls }: { calls: ToolCall[] }) {
  const cur = [...calls].reverse().find((t) => t.status === 'running')
  return (
    <div className="progress">
      {cur ? `${SOURCE_LABEL[cur.source]} 조회 중… (${cur.name})` : calls.length ? `조회 ${calls.length}건 완료, 답변 정리 중…` : '에이전트 실행 중…'}
    </div>
  )
}

function MessageView({ m, streamError, onProposal }: { m: Message; streamError?: string; onProposal: (p: Proposal) => void }) {
  return (
    <div className={`msg ${m.role}`} title={new Date(m.createdAt).toLocaleString()}>
      <span className="sr-only">{m.role === 'user' ? '나' : '에이전트'}:</span>
      {m.content && <Markdown>{m.content}</Markdown>}
      <ToolCalls calls={m.toolCalls} />
      {m.status === 'running' && <Progress calls={m.toolCalls} />}
      {m.status === 'failed' && <div className="error">실행 실패: {streamError ?? errorText(m.errorCode ?? 'INTERNAL_ERROR')}</div>}
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

  const load = useCallback(() => {
    getConversation(id).then((d) => { setDetail(d); setLoadError('') }, (e) => setLoadError(describe(e)))
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
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS') load()
    } finally {
      setStreaming(false)
      onChanged()
    }
  }

  if (loadError) return <><Topbar title="대화" /><div className="scroll"><div className="thread"><p className="error">{loadError}</p></div></div></>
  if (!detail) return <><Topbar title="대화" /><div className="scroll"><div className="thread"><p className="muted">불러오는 중…</p></div></div></>
  const disabled = streaming || running
  return (
    <>
      <Topbar title={detail.title ?? '새 대화'} />
      <div className="scroll">
        <div className="thread chat">
          {detail.messages.length === 0 && <p className="muted empty">질문을 입력하세요. 예: 스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘</p>}
          {detail.messages.map((m) => <MessageView key={m.id} m={m} streamError={streamErrors[m.id]} onProposal={onProposal} />)}
        </div>
      </div>
      <div className="chat-input-wrap">
        <div className="chat-input">
          <textarea
            value={input} rows={1} maxLength={4000} disabled={disabled} aria-label="질문 입력"
            placeholder={disabled ? '에이전트 실행 중에는 보낼 수 없습니다' : '질문 (Ctrl+Enter로 전송)'}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void submit() }}
          />
          <button type="button" className="btn primary" onClick={() => void submit()} disabled={disabled || !input.trim()}>보내기</button>
        </div>
        {notice && <p className="error notice">{notice}</p>}
      </div>
    </>
  )
}
