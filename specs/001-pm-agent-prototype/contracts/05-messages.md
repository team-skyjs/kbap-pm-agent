### POST /api/conversations/{conversationId}/messages
- 용도: 사용자 메시지를 저장하고 에이전트를 실행해 결과를 SSE로 흘린다.
- 요청:
```json
{"content": "장바구니 개선 효과를 보려면 퍼널을 어떻게 짜고, 어떤 이벤트를 어디에 추가해야 해?"}
```
  `content`는 1~4000자. 선택 필드 `skipAmplitude`(boolean, 기본 `false`)도 받는다. `true`면 Amplitude 사전 점검을 건너뛰고 Amplitude 도구 없이 실행하며, 답의 `content`에 그 사실을 적는다.
- 스트림 시작 **전** 에러는 일반 JSON 에러 응답이다: `VALIDATION_ERROR`, `CONVERSATION_NOT_FOUND`, `RUN_IN_PROGRESS`, `BUDGET_EXCEEDED`, `AMPLITUDE_UNAVAILABLE`.
- 사전 점검(실제 모드, `skipAmplitude`가 `false`일 때): 예산 검사 다음에 Amplitude 이벤트 목록을 1회 조회한다(15분 캐시). 실패하면 모델을 호출하지 않고, 사용자 메시지도 저장하지 않고 503 `AMPLITUDE_UNAVAILABLE`로 거절한다. 예시는 아래와 같다.
```json
{"error": {"code": "AMPLITUDE_UNAVAILABLE", "message": "Amplitude 조회 불가: 서버에 Amplitude 키가 설정되어 있지 않습니다. 그래도 진행하면 Amplitude 없이 답합니다."}}
```
  이유별 `message` 앞부분은 다음 넷이다. "Amplitude 조회 불가: 서버에 Amplitude 키가 설정되어 있지 않습니다", "Amplitude 조회 불가: 인증에 실패했습니다(키 확인 필요)", "Amplitude 조회 불가: 요청 한도를 넘었습니다(잠시 후 다시)", "Amplitude 조회 불가: 연결에 실패했습니다". 키 값은 넣지 않는다.
- 정상이면 200, `Content-Type: text/event-stream`. 이벤트 순서:
  1. `message_created` 정확히 1회
  2. `tool_call` / `tool_result` 0회 이상 (같은 도구 호출 id로 `tool_call` 다음에 `tool_result`)
  3. `final` 또는 `error` 정확히 1회, 그 뒤 스트림 종료

```
event: message_created
data: {"userMessage":{"id":43,"conversationId":7,"role":"user","status":"completed","content":"장바구니 개선 효과를 보려면 퍼널을 어떻게 짜고, 어떤 이벤트를 어디에 추가해야 해?","errorCode":null,"toolCalls":[],"proposals":[],"usage":null,"createdAt":"2026-10-15T10:01:00.120Z"},"assistantMessageId":44}

event: tool_call
data: {"id":310,"seq":1,"source":"taxonomy","name":"search_taxonomy","input":{"query":"cart"},"status":"running","resultSummary":null,"durationMs":null,"startedAt":"2026-10-15T10:01:02.004Z"}

event: tool_result
data: {"id":310,"seq":1,"source":"taxonomy","name":"search_taxonomy","input":{"query":"cart"},"status":"succeeded","resultSummary":"일치 이벤트 2개: cart_add, cart_view","durationMs":8,"startedAt":"2026-10-15T10:01:02.004Z"}

event: final
data: {"id":44,"conversationId":7,"role":"assistant","status":"completed","content":"장바구니 퍼널은 cart_view → cart_add → order_card_open 3단계로 설계했습니다.","errorCode":null,"toolCalls":[{"id":310,"seq":1,"source":"taxonomy","name":"search_taxonomy","input":{"query":"cart"},"status":"succeeded","resultSummary":"일치 이벤트 2개: cart_add, cart_view","durationMs":8,"startedAt":"2026-10-15T10:01:02.004Z"}],"proposals":[],"usage":{"model":"anthropic:claude-sonnet-5-5","inputTokens":9120,"outputTokens":1404,"costUsd":0.0484},"createdAt":"2026-10-15T10:01:00.130Z"}

```
  - `tool_call`, `tool_result`의 `data`는 ToolCall 객체.
  - `final`의 `data`는 완성된 assistant Message 객체(위 Message와 같은 shape, proposals 포함). 예시는 지면상 `proposals`를 비웠다.
  - `error`의 `data`: 공통 에러 객체에 실패 처리된 메시지 ID를 더한다.
```
event: error
data: {"error":{"code":"UPSTREAM_ERROR","message":"LLM 공급자 응답 오류로 실행을 중단했습니다."},"assistantMessageId":44}

```
  - `error` 이후 해당 assistant 메시지는 DB에 `status: "failed"`, `errorCode`가 채워진 채 남는다. 그때까지의 toolCalls도 남는다.
- 비고: `AGENT_MODE=fake`이면 LLM·Amplitude 없이 위 순서대로 도구 호출 2개(`taxonomy`, `code`)와 제안 2개(`improvement` 1, `funnel_design` 1)를 내고 저장한다. QA·FE 연동은 이 모드로 한다.
- 비고(상한): 모델 호출 턴이 `AGENT_MAX_TURNS`(기본 10)에 닿거나 실행 시간이 `AGENT_TIMEOUT_SECONDS`(기본 170)를 넘으면, 서버는 그때까지의 조회 결과로 `final`을 보낸다. 도구 호출 횟수는 세지 않는다. 이때 `status`는 `"completed"`이고 `content` 첫 문장에 중단 사유를 적는다(예: "모델 호출 상한(10턴)에 도달해 여기까지의 조회 결과로 답합니다." / "실행 시간 상한(170초)에 도달해 여기까지의 조회 결과로 답합니다."). `proposals`는 빈 배열일 수 있다.
- 비고(소스 실패): 개별 도구 호출이 실패하면 해당 `tool_result`가 `status: "failed"`로 오고 실행은 계속된다. `final`의 `content`에 빠진 근거 소스를 명시한다. 스트림 전체를 `error`로 끝내는 것은 추론 모델 호출 자체가 실패했을 때뿐이다.

