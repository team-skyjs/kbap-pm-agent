# 01 CTO — API 계약서 v1.1

작성일: 2026-10-15 · 이 문서가 FE·BE·QA의 유일한 경계 기준이다. 변경은 CTO만 하고, 바뀌면 상단 변경 이력에 남긴다.

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-10-15 | v1 | 최초 작성 |
| 2026-10-15 | v1.1 | 명세(spec.md)·헌법 정합: 코드 근거에 `function` 추가(FR-003), 저장소 `lastError` 추가(엣지 케이스 비공개 저장소), 실행 시간 상한·소스 실패 시 동작 명시(FR-010, 엣지 케이스), 택사노미 검증 실패 메시지 규칙(US4-4), `AGENT_MODE=fake`가 저장소·Amplitude까지 대체(헌법 원칙 III, FR-011), 실행 중 메시지 필드 규칙 |
| 2026-10-15 | v1.1 (문구) | 메시지 전송 상한 비고: 도구 호출 수 → 모델 호출 턴 수 `AGENT_MAX_TURNS`(기본 10). shape 변경 없음 |
| 2026-10-15 | v1.1 (예시) | 예시 운영 호스트를 `pm-agent.example.com`으로 바꿨다(Base URL 예시, connect 예시 redirect_uri). 운영 정보 비노출. 값·shape 의미 변경 없음 |

## 공통

- **Base URL:** 프론트 빌드 환경변수 `VITE_API_BASE_URL` (예: 로컬 `http://localhost:8000`, 운영 `https://pm-agent.example.com`). 모든 경로는 `/api`로 시작한다.
- **인증:** 백엔드에 `ACCESS_TOKEN`이 설정되어 있으면 `GET /api/health`와 `GET /api/integrations/amplitude/callback`을 제외한 모든 요청에 `Authorization: Bearer <토큰>` 헤더가 필요하다. 없거나 틀리면 401 `UNAUTHORIZED`.
- **형식:** 요청·응답 본문은 `application/json; charset=utf-8`. 메시지 전송 응답만 `text/event-stream`.
- **필드 이름:** camelCase 고정. DB의 snake_case를 그대로 노출하지 않는다.
- **ID:** 양의 정수(JSON number).
- **시각:** UTC ISO 8601, 밀리초 포함, `Z` 접미사. 예: `"2026-10-15T09:12:03.418Z"`.
- **null 규칙:** 값이 없는 필드는 키를 빼지 않고 `null`로 보낸다. 예외는 Evidence의 kind별 필드(아래 Proposal 참고).
- **목록:** 페이지네이션 없음(사용자 2명). 목록 응답은 `{"items": [...]}`로 감싼다.

### 에러 응답 (모든 엔드포인트 공통)

```json
{
  "error": {
    "code": "CONVERSATION_NOT_FOUND",
    "message": "대화 7을 찾을 수 없습니다."
  }
}
```

`message`는 사람이 읽는 한국어 문장이다. 프론트는 `code`로만 분기한다. FastAPI 기본 422 형식(`{"detail": [...]}`)은 쓰지 않는다. 백엔드가 예외 핸들러로 이 형식으로 바꾼다.

| code | HTTP | 언제 |
|---|---|---|
| `VALIDATION_ERROR` | 400 | 본문 JSON이 깨졌거나 필수 필드 누락·타입 오류·허용값 밖 |
| `UNAUTHORIZED` | 401 | 접근 토큰 누락·불일치 |
| `BUDGET_EXCEEDED` | 403 | LLM 누적 비용이 `LLM_BUDGET_USD` 이상 |
| `CONVERSATION_NOT_FOUND` | 404 | 대화 ID 없음 |
| `PROPOSAL_NOT_FOUND` | 404 | 제안 ID 없음 |
| `NOT_FOUND` | 404 | 정의되지 않은 경로 |
| `REPOSITORY_NOT_CONFIGURED` | 409 | 저장소 등록 전에 동기화 요청 |
| `RUN_IN_PROGRESS` | 409 | 같은 대화에 `status: "running"`인 assistant 메시지가 있는데 새 메시지 전송 |
| `UPSTREAM_ERROR` | 502 | GitHub 클론 실패, Amplitude OAuth 시작 실패, LLM 공급자 오류 |
| `INTERNAL_ERROR` | 500 | 그 외 |

### 시연 모드 (`AGENT_MODE=fake`)

백엔드가 `AGENT_MODE=fake`로 뜨면 외부 연동 세 가지(LLM, Amplitude MCP, GitHub)를 전부 호출하지 않는다. 응답 shape는 실제 모드와 같다.

| 엔드포인트 | fake 동작 |
|---|---|
| `POST /api/conversations/{conversationId}/messages` | 스크립트된 실행: 도구 호출 2개(`taxonomy`, `code`)와 제안 2개(`improvement` 1, `funnel_design` 1)를 계약 순서대로 스트림하고 DB에 저장. `usage.costUsd`는 `0` |
| `PUT /api/settings/repository` | 클론하지 않는다. 요청의 `url`·`branch`에 이 문서 Settings 예시의 나머지 값(`headCommit: "9f3c2a1"`, `codeMapStatus: "ready"` 등)을 채워 저장·응답 |
| `POST /api/settings/repository/sync` | 저장된 값을 `syncedAt`만 현재 시각으로 바꿔 응답 |
| `POST /api/integrations/amplitude/connect` | 이 문서의 예시 `authorizationUrl`을 그대로 응답하고 즉시 `amplitude.status`를 `"connected"`로 저장 |
| `GET /api/settings` | `agentMode: "fake"`. 나머지는 저장된 값 |

택사노미 업로드, 대화·제안 저장, 헬스체크는 두 모드가 같다.

### 스트리밍 (SSE)

메시지 전송 엔드포인트에서만 쓴다. 형식은 표준 SSE다.

```
event: tool_call
data: {"id":301,"seq":1,"source":"amplitude","name":"query_funnel","input":{"events":["scan_start","scan_complete"],"start":"2026-09-15","end":"2026-10-14"},"status":"running","resultSummary":null,"durationMs":null,"startedAt":"2026-10-15T09:12:05.101Z"}

```

- 각 이벤트는 `event:` 한 줄 + `data:` 한 줄(JSON 한 줄) + 빈 줄.
- 서버는 15초마다 `: ping` 주석 줄을 보낸다. 프론트는 무시한다.
- 스트림은 `final` 또는 `error` 이벤트 직후 서버가 닫는다. 둘 중 정확히 하나가 마지막 이벤트다.
- 스트림 도중 연결이 끊기면 프론트는 `GET /api/conversations/{id}`로 저장된 상태를 다시 읽는다. 끊긴 실행은 서버가 `status: "failed"`, `errorCode: "INTERNAL_ERROR"`로 마감한다.

