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
  // 입력창에 넣은 개선안의 기록 ID: 실제 전송 때 refined, 비우거나 떠나면 cancelled로 확정
  const pending = useRef<number | null>(null)
  // 열린 카드. 호출자의 전송 함수는 이전 렌더의 상태를 볼 수 있어 상태 대신 ref로 판단(중복 기록 방지)
  const openCard = useRef<number | null>(null)

  // 선택 기록은 집계용이라 기다리지 않고 실패도 무시(전송을 막지 않음)
  const record = (id: number, choice: RefineChoice) => { void recordRefineChoice(id, choice).catch(() => {}) }
  const settle = (choice: RefineChoice) => {
    if (pending.current === null) return
    record(pending.current, choice)
    pending.current = null
  }

  // 대화를 떠나거나 화면이 닫히면 보내지 않은 개선안은 취소
  useEffect(() => () => { run.current++; settle('cancelled') }, [conversationId])
  useEffect(() => { if (input !== undefined && !input.trim()) settle('cancelled') }, [input])

  const start = useCallback(async (question: string) => {
    const q = question.trim()
    if (!q) return
    const mine = ++run.current
    // 넣어 둔 개선안이나 열린 카드를 두고 다시 다듬으면 이전 것은 취소
    settle('cancelled')
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

  // 카드 닫기. choice가 null이면 기록을 미룸(입력창에 넣기)
  const finish = (choice: RefineChoice | null) => {
    if (state.phase !== 'card' || openCard.current === null) return null
    openCard.current = null
    if (choice) record(state.result.refinementId, choice)
    else pending.current = state.result.refinementId
    setState({ phase: 'idle' })
    return state
  }

  return {
    state,
    start,
    sendRefined: () => { const s = finish('refined'); if (s) send(s.result.refined) },
    sendOriginal: () => { const s = finish('original'); if (s) send(s.original) },
    // 기록은 전송 때(sent)로 미룸, 편집 후 전송도 개선안 채택으로 셈
    insertRefined: () => { const s = finish(null); if (s) setInput(s.result.refined) },
    close: () => { finish('cancelled') },
    dismissError: () => setState({ phase: 'idle' }),
    // 호출자가 메시지를 보내는 순간 호출(입력창을 비우기 전). 넣어 둔 개선안이 있으면 refined,
    // 카드를 연 채 입력창으로 보내면 원문 전송이라 original로 기록하고 카드를 닫음
    sent: () => {
      settle('refined')
      if (openCard.current !== null) {
        record(openCard.current, 'original')
        openCard.current = null
        setState({ phase: 'idle' })
      }
    },
  }
}
