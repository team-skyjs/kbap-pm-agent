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
}

// 질문 다듬기 상태와 네 가지 선택. 원문은 입력창에 그대로 두고, 전송·교체만 호출자에게 맡김
export function useRefine({ conversationId, setInput, send }: Deps) {
  const [state, setState] = useState<RefineState>({ phase: 'idle' })
  // 다듬는 사이 대화가 바뀌거나 화면이 닫히면 늦게 온 결과를 버리기 위한 순번
  const run = useRef(0)
  useEffect(() => () => { run.current++ }, [conversationId])

  const start = useCallback(async (question: string) => {
    const q = question.trim()
    if (!q) return
    const mine = ++run.current
    setState({ phase: 'refining' })
    try {
      const result = await refineQuestion(conversationId, q)
      if (mine === run.current) setState({ phase: 'card', original: question, result })
    } catch (e) {
      if (mine === run.current) setState({ phase: 'error', code: e instanceof ApiError ? e.code : null, message: describe(e) })
    }
  }, [conversationId])

  // 선택 기록은 집계용이라 기다리지 않고 실패도 무시(전송을 막지 않음)
  const finish = (choice: RefineChoice) => {
    if (state.phase !== 'card') return null
    void recordRefineChoice(state.result.refinementId, choice).catch(() => {})
    setState({ phase: 'idle' })
    return state
  }

  return {
    state,
    start,
    sendRefined: () => { const s = finish('refined'); if (s) send(s.result.refined) },
    sendOriginal: () => { const s = finish('original'); if (s) send(s.original) },
    // 편집 후 전송도 개선안 채택으로 셈
    insertRefined: () => { const s = finish('refined'); if (s) setInput(s.result.refined) },
    close: () => { finish('cancelled') },
    dismissError: () => setState({ phase: 'idle' }),
  }
}
