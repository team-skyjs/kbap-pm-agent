import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, describe, recordRefineChoice, refineQuestion, type ClientErrorCode, type RefineChoice, type RefineResponse } from './api.ts'

export type RefineState =
  | { phase: 'idle' }
  | { phase: 'refining' }
  | { phase: 'card'; original: string; result: RefineResponse }
  // code는 화면이 토큰 오류(UNAUTHORIZED)를 설정 안내로 따로 그리기 위함
  | { phase: 'error'; code: ClientErrorCode | null; message: string }

type Deps = {
  conversationId: number | null
  // 입력창 값 교체(입력창에 넣기)
  setInput: (value: string) => void
  // 기존 메시지 전송 흐름으로 넘김
  send: (content: string) => void
  // 현재 입력창 값. 입력창에 넣은 개선안을 보내지 않고 비우면 취소로 기록하기 위함
  input?: string
}

// 질문 다듬기 상태와 네 가지 선택. 원문은 입력창에 그대로 두고, 전송·교체만 호출자에게 맡김
export function useRefine({ conversationId, setInput, send, input }: Deps) {
  const [state, setState] = useState<RefineState>({ phase: 'idle' })
  // 다듬는 사이 대화가 바뀌거나 화면이 닫히면 늦게 온 결과를 버리기 위한 순번
  const run = useRef(0)
  // 서버가 메시지를 받은(message_created) 뒤에 기록할 선택. 입력창에 넣기는 전송 실패에도 유지,
  // 카드의 두 보내기 버튼은 실패하면 그 카드를 다시 열기 위해 카드 내용을 함께 보관
  type Card = Extract<RefineState, { phase: 'card' }>
  const pending = useRef<{ id: number; choice: RefineChoice; reopen: Card | null } | null>(null)
  // 열린 카드. 호출자의 전송 함수는 이전 렌더의 상태를 볼 수 있어 상태 대신 ref로 판단(중복 기록 방지)
  const openCard = useRef<number | null>(null)

  // 선택 기록은 집계용이라 기다리지 않고 실패도 무시(전송을 막지 않음)
  const record = (id: number, choice: RefineChoice) => { void recordRefineChoice(id, choice).catch(() => {}) }
  // 넣어 둔 개선안을 보내지 않고 비우거나 떠나거나 다시 다듬으면 취소
  const cancelInsert = () => {
    const p = pending.current
    if (!p || p.reopen) return
    record(p.id, 'cancelled')
    pending.current = null
  }

  // 대화를 떠나거나 화면이 닫히면 보내지 않은 개선안과 열린 카드는 취소(다듬는 중이면 기록 없음)
  useEffect(() => () => {
    run.current++
    cancelInsert()
    pending.current = null
    if (openCard.current !== null) record(openCard.current, 'cancelled')
    openCard.current = null
  }, [conversationId])
  useEffect(() => { if (input !== undefined && !input.trim()) cancelInsert() }, [input])

  const start = useCallback(async (question: string) => {
    const q = question.trim()
    if (!q) return
    const mine = ++run.current
    // 넣어 둔 개선안이나 열린 카드를 두고 다시 다듬으면 이전 것은 취소
    cancelInsert()
    if (openCard.current !== null) record(openCard.current, 'cancelled')
    openCard.current = null
    setState({ phase: 'refining' })
    try {
      const result = await refineQuestion(conversationId, q)
      if (mine === run.current) {
        openCard.current = result.refinementId
        setState({ phase: 'card', original: question, result })
      }
    } catch (e) {
      if (mine === run.current) setState({ phase: 'error', code: e instanceof ApiError ? e.code : null, message: describe(e) })
    }
  }, [conversationId])

  // 카드 닫기. 닫기는 바로 기록, 나머지는 전송 확인 뒤 기록하도록 보류
  // defer: null이면 바로 기록(닫기), 아니면 전송 확인까지 보류. reopen이면 전송 실패 시 카드를 다시 염
  const finish = (choice: RefineChoice, defer: { reopen: boolean } | null) => {
    if (state.phase !== 'card' || openCard.current === null) return null
    openCard.current = null
    if (defer) pending.current = { id: state.result.refinementId, choice, reopen: defer.reopen ? state : null }
    else record(state.result.refinementId, choice)
    setState({ phase: 'idle' })
    return state
  }

  return {
    state,
    start,
    sendRefined: () => { const s = finish('refined', { reopen: true }); if (s) send(s.result.refined) },
    sendOriginal: () => { const s = finish('original', { reopen: true }); if (s) send(s.original) },
    // 편집 후 전송도 개선안 채택으로 셈
    insertRefined: () => { const s = finish('refined', { reopen: false }); if (s) setInput(s.result.refined) },
    close: () => { finish('cancelled', null) },
    // 오류 상태일 때만 닫음(열린 카드를 기록 없이 닫지 않도록)
    dismissError: () => setState((s) => (s.phase === 'error' ? { phase: 'idle' } : s)),
    // 서버가 메시지를 받았을 때(message_created) 호출. 보류한 선택을 기록,
    // 카드를 연 채 입력창으로 보냈으면 원문 전송이라 original로 기록하고 카드를 닫음
    sent: () => {
      const p = pending.current
      if (p) {
        record(p.id, p.choice)
        pending.current = null
      } else if (openCard.current !== null) {
        record(openCard.current, 'original')
        openCard.current = null
        setState({ phase: 'idle' })
      }
    },
    // 전송이 서버에 닿지 못함(예산 초과·409·인증·네트워크·이미 실행 중). 넣기는 유지,
    // 카드의 보내기 버튼이면 기록 없이 같은 카드를 다시 열어 한 번에 재시도하게 함(열리면 개선안 보내기에 포커스)
    sendFailed: () => {
      const p = pending.current
      if (!p?.reopen) return
      pending.current = null
      openCard.current = p.id
      setState(p.reopen)
    },
  }
}
