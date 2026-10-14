import { useCallback, useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import {
  ApiError, describe, errorText, getConversation, sendMessage,
  type ConversationDetail, type Message, type StreamEvent, type ToolCall,
} from './api.ts'

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

function MessageView({ m, streamError }: { m: Message; streamError?: string }) {
  return (
    <div className={`msg ${m.role}`}>
      <div className="muted">{m.role === 'user' ? '나' : '에이전트'} · {new Date(m.createdAt).toLocaleString()}</div>
      {m.content && <Markdown>{m.content}</Markdown>}
      <ToolCalls calls={m.toolCalls} />
      {m.status === 'running' && <Progress calls={m.toolCalls} />}
      {m.proposals.length > 0 && <div className="muted">제안 {m.proposals.length}개</div>}
      {m.status === 'failed' && <div className="error">실행 실패: {streamError ?? errorText(m.errorCode ?? 'INTERNAL_ERROR')}</div>}
      {m.usage && (
        <div className="muted">
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

  // 다른 탭에서 시작했거나 끊긴 실행: 스트림이 없으니 3초마다 상세를 다시 읽는다.
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
        // 실행 중 메시지 규칙(계약서 Message): content "", proposals [], usage null
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

  async function submit() {
    const content = input.trim()
    if (!content || streaming) return
    setNotice('')
    setStreaming(true)
    try {
      const end = await sendMessage(id, content, onEvent)
      setInput('')
      if (end === 'disconnected') {
        setNotice('스트림이 끊겨 저장된 상태를 다시 불러왔습니다.')
        load()
      }
    } catch (e) {
      // 스트림 전 에러(409 RUN_IN_PROGRESS, 403 BUDGET_EXCEEDED, 400, 404, 401)는 입력창 아래에 안내
      setNotice(describe(e))
      if (e instanceof ApiError && e.code === 'RUN_IN_PROGRESS') load()
    } finally {
      setStreaming(false)
      onChanged()
    }
  }

  if (loadError) return <p className="error">{loadError}</p>
  if (!detail) return <p>불러오는 중…</p>
  const disabled = streaming || running
  return (
    <div className="chat">
      <h3>{detail.title ?? '새 대화'}</h3>
      {detail.messages.length === 0 && <p className="muted">질문을 입력하세요. 예: 스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘</p>}
      {detail.messages.map((m) => <MessageView key={m.id} m={m} streamError={streamErrors[m.id]} />)}
      <div className="composer">
        <textarea
          value={input} rows={3} maxLength={4000} disabled={disabled}
          placeholder={disabled ? '에이전트 실행 중에는 보낼 수 없습니다' : '질문 (Ctrl+Enter로 전송)'}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void submit() }}
        />
        <button onClick={() => void submit()} disabled={disabled || !input.trim()}>보내기</button>
      </div>
      {notice && <p className="error">{notice}</p>}
    </div>
  )
}
