# 01 CTO — API 계약서 v1.4

작성일: 2026-10-15 · 이 문서가 FE·BE·QA의 유일한 경계 기준이다. 변경은 CTO만 하고, 바뀌면 상단 변경 이력에 남긴다.

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-10-15 | v1 | 최초 작성 |
| 2026-10-15 | v1.1 | 명세(spec.md)·헌법 정합: 코드 근거에 `function` 추가(FR-003), 저장소 `lastError` 추가(엣지 케이스 비공개 저장소), 실행 시간 상한·소스 실패 시 동작 명시(FR-010, 엣지 케이스), 택사노미 검증 실패 메시지 규칙(US4-4), `AGENT_MODE=fake`가 저장소·Amplitude까지 대체(헌법 원칙 III, FR-011), 실행 중 메시지 필드 규칙 |
| 2026-10-15 | v1.1 (문구) | 메시지 전송 상한 비고: 도구 호출 수 → 모델 호출 턴 수 `AGENT_MAX_TURNS`(기본 10). shape 변경 없음 |
| 2026-10-15 | v1.1 (예시) | 예시 운영 호스트를 `pm-agent.example.com`으로 바꿨다(Base URL 예시, connect 예시 redirect_uri). 운영 정보 비노출. 값·shape 의미 변경 없음 |
| 2026-10-15 | v1.3 | 질문 마법사(specs/004-question-wizard): `POST /api/questions/refine`(질문 다듬기)와 `POST /api/questions/refine/{refinementId}/choice`(선택 기록)를 추가했다. 에러 코드 `REFINEMENT_NOT_FOUND`를 추가하고 시연 모드 동작도 정했다. 기존 엔드포인트 shape는 그대로다. v1.2는 접근 제한 PR(미머지)이 쓰는 번호라 건너뛴다 |
| 2026-10-15 | v1.3 (문구) | PRD 보강 반영: 택사노미 이름 4,000자 상한과 잘림 시 요약 표시 규칙. shape 변경 없음 |
| 2026-10-15 | v1.3 (문구 2) | PRD 3차 반영: "입력창에 넣기"의 기록 시점(전송 시 refined, 전송 없이 비우거나 대화 이탈 시 cancelled), `refined` 범위 밖이면 502, 택사노미 상한 시 질문과 겹치는 이름 우선. shape 변경 없음 |
| 2026-10-17 | v1.4 | 대화 내보내기(specs/005-conversation-export): `POST /api/conversations/{conversationId}/exports`(내보내기 기록)를 추가했다. 기존 shape는 그대로다 |

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
| `REFINEMENT_NOT_FOUND` | 404 | 질문 다듬기 기록 ID 없음 |
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
| `POST /api/questions/refine` | LLM을 호출하지 않는다. 이 문서의 다듬기 응답 예시 `refined`·`summary`를 그대로 돌려주고 기록 행을 만든다(`refinementId`는 실제 새 ID). 사용량은 0원으로 기록한다 |
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

## 공통 객체

### ConversationSummary
```json
{
  "id": 7,
  "title": "스캔 퍼널 이탈 지점 개선안",
  "createdAt": "2026-10-15T09:12:03.418Z",
  "updatedAt": "2026-10-15T09:14:41.022Z",
  "messageCount": 2,
  "proposalCount": 2,
  "adoptedCount": 1
}
```
- `title`: 생성 시 지정하지 않으면 `null`. 첫 사용자 메시지가 저장될 때 앞 40자로 채운다.

### Message
```json
{
  "id": 42,
  "conversationId": 7,
  "role": "assistant",
  "status": "completed",
  "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다. 실패의 62%가 OCR 실패이고, 실패 화면에 재시도 동작이 없습니다. 아래 두 제안을 확인해 주세요.",
  "errorCode": null,
  "toolCalls": [
    {
      "id": 301,
      "seq": 1,
      "source": "amplitude",
      "name": "query_funnel",
      "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"},
      "status": "succeeded",
      "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%",
      "durationMs": 2310,
      "startedAt": "2026-10-15T09:12:05.101Z"
    },
    {
      "id": 302,
      "seq": 2,
      "source": "code",
      "name": "find_event_calls",
      "input": {"eventName": "scan_complete"},
      "status": "succeeded",
      "resultSummary": "2곳: src/app/scan.tsx:405 (실패), src/app/scan.tsx:427 (성공)",
      "durationMs": 14,
      "startedAt": "2026-10-15T09:12:08.550Z"
    }
  ],
  "proposals": [],
  "usage": {
    "model": "anthropic:claude-sonnet-5-5",
    "inputTokens": 18432,
    "outputTokens": 2210,
    "costUsd": 0.0884
  },
  "createdAt": "2026-10-15T09:12:04.002Z"
}
```
- `role`: `"user"` | `"assistant"`.
- `status`: `"running"` | `"completed"` | `"failed"`. user 메시지는 항상 `"completed"`.
- `errorCode`: `status`가 `"failed"`일 때 에러 코드 문자열, 아니면 `null`.
- user 메시지는 `toolCalls: []`, `proposals: []`, `usage: null`.
- `status`가 `"running"`인 assistant 메시지(실행 중 상세 조회)는 `content: ""`, `proposals: []`, `usage: null`이고 `toolCalls`에는 그때까지 저장된 호출이 들어간다.
- `content`: 마크다운 문자열. **제안 내용을 여기에 섞지 않는다.** 제안은 `proposals`에만 있다.
- `toolCalls`는 `seq` 오름차순. `source`: `"amplitude"` | `"code"` | `"taxonomy"`. `status`: `"running"` | `"succeeded"` | `"failed"`. `name`은 도구 이름 그대로(Amplitude MCP 도구명은 MCP 서버가 정한 이름). `resultSummary`는 최대 500자, `running`이면 `null`. `durationMs`는 `running`이면 `null`.
- 위 예시의 `proposals`는 지면상 비웠다. 실제 완료 메시지에는 아래 Proposal이 0개 이상 들어간다.

### Proposal
```json
{
  "id": 15,
  "conversationId": 7,
  "messageId": 42,
  "seq": 1,
  "type": "funnel_design",
  "title": "스캔 실패 후 재시도 퍼널 측정 설계",
  "evidence": [
    {
      "kind": "metric",
      "summary": "최근 30일 scan_start 대비 성공한 scan_complete 전환율이 41.3%다.",
      "value": "41.3%",
      "source": "Amplitude funnel: scan_start → scan_complete(success=true), 2026-09-15~2026-10-14"
    },
    {
      "kind": "code",
      "summary": "실패 시 scan_complete를 success=false로 보내고 끝나며, 재시도 버튼 핸들러에는 이벤트가 없다.",
      "file": "src/app/scan.tsx",
      "function": "onScanFailed",
      "line": 405,
      "snippet": "track(EVENTS.scan_complete, { success: false, fail_reason: reason, item_count: 0, degraded: false });"
    },
    {
      "kind": "taxonomy",
      "summary": "scan_complete는 성공·실패를 success 속성으로 구분한다.",
      "eventName": "scan_complete"
    }
  ],
  "proposal": "실패 화면의 재시도 동작에 신규 이벤트 scan_retry_tap을 심어, 실패 후 재시도로 회복되는 비율을 측정한다.",
  "steps": [
    "EVENTS 상수에 scan_retry_tap을 추가한다.",
    "src/app/scan.tsx의 handleRetry 첫 줄에서 track(EVENTS.scan_retry_tap, { fail_reason })를 호출한다.",
    "택사노미 문서에 scan_retry_tap 정의와 fail_reason 속성을 추가한다.",
    "배포 후 7일간 아래 퍼널을 Amplitude에 저장해 확인한다."
  ],
  "measurement": {
    "primaryMetric": "scan_complete(success=false) 이후 24시간 내 scan_complete(success=true) 도달 비율",
    "baseline": null,
    "target": "35%",
    "funnel": [
      {"order": 1, "eventName": "scan_complete", "status": "existing", "condition": "success=false", "location": null, "properties": []},
      {"order": 2, "eventName": "scan_retry_tap", "status": "new", "condition": null, "location": {"file": "src/app/scan.tsx", "function": "handleRetry", "line": 398}, "properties": [{"name": "fail_reason", "type": "string"}]},
      {"order": 3, "eventName": "scan_complete", "status": "existing", "condition": "success=true", "location": null, "properties": []}
    ]
  },
  "decision": {
    "status": "adopted",
    "note": "KB-812로 이번 스프린트에 진행",
    "decidedAt": "2026-10-15T09:20:11.730Z"
  },
  "createdAt": "2026-10-15T09:14:40.990Z"
}
```

필드 규칙:
- `type`: `"improvement"`(세그먼트 A, 기획 개선) | `"funnel_design"`(세그먼트 B, 측정 설계).
- 카드 네 영역은 정확히 이 순서다: `evidence` → `proposal` → `steps` → `measurement`.
- `evidence`: 1개 이상. `kind`별 필드가 다르고, 다른 kind의 필드는 **보내지 않는다**(TS 판별 유니온).
  - `"metric"`: `summary`, `value`(문자열, 단위 포함), `source`
  - `"code"`: `summary`, `file`(저장소 루트 기준 상대 경로), `function`(감싸는 함수·컴포넌트 이름, 최상위 코드면 `null`), `line`(1부터), `snippet`(최대 10줄)
  - `"taxonomy"`: `summary`, `eventName`
- `proposal`: 문자열. `steps`: 문자열 배열, 1개 이상, 실행 순서대로.
- `measurement`:
  - `primaryMetric`: 문자열, 필수.
  - `baseline`, `target`: 문자열 또는 `null`.
  - `funnel`: 배열. `funnel_design`이면 1개 이상 필수. `improvement`면 빈 배열 가능.
  - funnel 단계: `order`(1부터 연속), `eventName`, `status`(`"existing"` | `"new"`), `condition`(문자열 또는 `null`), `location`, `properties`.
  - `status`가 `"new"`면 `location`(`file`, `function`, `line`) 필수, `"existing"`이면 `location: null`. `location.line`은 `null` 가능(함수만 특정될 때).
  - `properties`: 신규 이벤트에 붙일 속성 `[{name, type}]`. `type`은 `"string"` | `"number"` | `"boolean"`. 기존 이벤트는 빈 배열.
- `decision.status`: `"pending"` | `"adopted"` | `"on_hold"`. 생성 시 `"pending"`, `note: null`, `decidedAt: null`. `decidedAt`은 status가 바뀔 때마다 갱신되고 `"pending"`으로 돌리면 `null`.

### Settings
```json
{
  "repository": {
    "url": "https://github.com/team-skyjs/kbap-fe",
    "branch": "develop",
    "headCommit": "9f3c2a1",
    "codeMapCommit": "9f3c2a1",
    "codeMapStatus": "ready",
    "trackedEventCount": 87,
    "screenCount": 41,
    "syncedAt": "2026-10-15T08:55:02.117Z",
    "lastError": null
  },
  "taxonomy": {
    "eventCount": 64,
    "uploadedAt": "2026-10-14T12:01:44.500Z"
  },
  "amplitude": {
    "status": "connected",
    "serverUrl": "https://mcp.amplitude.com/mcp",
    "connectedAt": "2026-10-14T12:10:09.031Z"
  },
  "models": {
    "agent": "anthropic:claude-sonnet-5-5",
    "codeSummary": "anthropic:claude-haiku-5-5"
  },
  "agentMode": "real",
  "budget": {
    "limitUsd": 200.0,
    "spentUsd": 3.4172
  }
}
```
- `repository`: 미등록이면 `null`. `headCommit`, `codeMapCommit`은 7자리 짧은 SHA. `codeMapStatus`: `"none"` | `"building"` | `"ready"` | `"failed"`. 요약 생성 전 `codeMapCommit`은 `null`. `lastError`: 마지막 동기화·요약이 실패했으면 사유 문장(예: `"GitHub 인증 실패: GITHUB_TOKEN이 없거나 만료되었습니다."`), 성공하면 `null`. 토큰 값은 넣지 않는다.
- `taxonomy`: 미업로드면 `null`.
- `amplitude.status`: `"connected"` | `"disconnected"`. 끊겼으면 `connectedAt: null`.
- `agentMode`: `"real"` | `"fake"`.
- 저장소·택사노미·Amplitude가 비어 있어도 대화는 가능하다. 에이전트는 쓸 수 있는 도구만으로 답한다.

## 엔드포인트

### GET /api/health
- 용도: 서버·DB 생존 확인. 인증 불필요.
- 응답 200:
```json
{"status": "ok", "db": "ok", "version": "0.1.0"}
```
- DB 연결 실패 시에도 200으로 `{"status": "degraded", "db": "error", "version": "0.1.0"}`. 서버가 떠 있는지와 DB 상태를 분리해 보여주기 위함이다.

### GET /api/conversations
- 용도: 대화 목록. `updatedAt` 내림차순.
- 응답 200:
```json
{
  "items": [
    {"id": 7, "title": "스캔 퍼널 이탈 지점 개선안", "createdAt": "2026-10-15T09:12:03.418Z", "updatedAt": "2026-10-15T09:14:41.022Z", "messageCount": 2, "proposalCount": 2, "adoptedCount": 1},
    {"id": 6, "title": null, "createdAt": "2026-10-14T05:40:00.000Z", "updatedAt": "2026-10-14T05:40:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}
  ]
}
```

### POST /api/conversations
- 용도: 빈 대화 생성.
- 요청: 본문 `{}` 또는 `{"title": "장바구니 개선 측정 설계"}`. `title`은 1~200자.
- 응답 201: ConversationSummary
```json
{"id": 8, "title": "장바구니 개선 측정 설계", "createdAt": "2026-10-15T10:00:00.000Z", "updatedAt": "2026-10-15T10:00:00.000Z", "messageCount": 0, "proposalCount": 0, "adoptedCount": 0}
```
- 에러: `VALIDATION_ERROR`.

### GET /api/conversations/{conversationId}
- 용도: 대화 상세. 메시지는 `createdAt` 오름차순, 각 메시지에 toolCalls·proposals·usage 포함.
- 응답 200:
```json
{
  "id": 7,
  "title": "스캔 퍼널 이탈 지점 개선안",
  "createdAt": "2026-10-15T09:12:03.418Z",
  "updatedAt": "2026-10-15T09:14:41.022Z",
  "messages": [
    {"id": 41, "conversationId": 7, "role": "user", "status": "completed", "content": "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘", "errorCode": null, "toolCalls": [], "proposals": [], "usage": null, "createdAt": "2026-10-15T09:12:03.990Z"},
    {"id": 42, "conversationId": 7, "role": "assistant", "status": "completed", "content": "지난 30일 스캔 퍼널에서 가장 큰 이탈은 scan_start → scan_complete(성공) 구간입니다.", "errorCode": null, "toolCalls": [{"id": 301, "seq": 1, "source": "amplitude", "name": "query_funnel", "input": {"events": ["scan_start", "scan_complete"], "start": "2026-09-15", "end": "2026-10-14"}, "status": "succeeded", "resultSummary": "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", "durationMs": 2310, "startedAt": "2026-10-15T09:12:05.101Z"}], "proposals": [{"id": 14, "conversationId": 7, "messageId": 42, "seq": 1, "type": "improvement", "title": "OCR 실패 화면에 재시도·직접 입력 동선 추가", "evidence": [{"kind": "metric", "summary": "실패한 scan_complete 중 fail_reason=ocr_empty가 62%다.", "value": "62%", "source": "Amplitude segmentation: scan_complete(success=false) by fail_reason, 2026-09-15~2026-10-14"}], "proposal": "OCR 실패 화면에 '다시 찍기'와 '메뉴 이름 직접 입력' 버튼을 둔다.", "steps": ["src/app/scan.tsx 실패 상태 UI에 버튼 2개를 추가한다.", "직접 입력은 기존 search 화면으로 이동시킨다."], "measurement": {"primaryMetric": "scan_start 대비 scan_complete(success=true) 전환율", "baseline": "41.3%", "target": "48%", "funnel": []}, "decision": {"status": "pending", "note": null, "decidedAt": null}, "createdAt": "2026-10-15T09:14:40.980Z"}], "usage": {"model": "anthropic:claude-sonnet-5-5", "inputTokens": 18432, "outputTokens": 2210, "costUsd": 0.0884}, "createdAt": "2026-10-15T09:12:04.002Z"}
  ]
}
```
- 에러: `CONVERSATION_NOT_FOUND`.

### POST /api/conversations/{conversationId}/messages
- 용도: 사용자 메시지를 저장하고 에이전트를 실행해 결과를 SSE로 흘린다.
- 요청:
```json
{"content": "장바구니 개선 효과를 보려면 퍼널을 어떻게 짜고, 어떤 이벤트를 어디에 추가해야 해?"}
```
  `content`는 1~4000자.
- 스트림 시작 **전** 에러는 일반 JSON 에러 응답이다: `VALIDATION_ERROR`, `CONVERSATION_NOT_FOUND`, `RUN_IN_PROGRESS`, `BUDGET_EXCEEDED`.
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

### PATCH /api/proposals/{proposalId}
- 용도: 제안 채택·보류·메모.
- 요청:
```json
{"status": "adopted", "note": "KB-812로 이번 스프린트에 진행"}
```
  - `status`: `"pending"` | `"adopted"` | `"on_hold"`, 필수.
  - `note`: 문자열(최대 1000자) 또는 `null`. 키를 생략하면 기존 메모를 유지하고, `null`이면 지운다.
- 응답 200: 갱신된 Proposal 전체(위 Proposal shape).
- 에러: `VALIDATION_ERROR`, `PROPOSAL_NOT_FOUND`.

### GET /api/settings
- 용도: 연결된 저장소·택사노미·Amplitude·모델·예산 상태 조회.
- 응답 200: Settings 객체(위 예시 그대로).

### PUT /api/settings/repository
- 용도: 분석할 FE 저장소 등록(교체). 얕은 클론을 마치고 응답한다. 무료 인덱스(이벤트 호출 목록)는 응답 전에 만들고, 화면 요약은 백그라운드로 시작한다.
- 요청:
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop"}
```
  `url`은 `https://github.com/`로 시작해야 한다(시험용으로 `file://` 허용). `branch` 생략 시 저장소 기본 브랜치.
- 응답 200: Settings의 `repository` 객체.
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop", "headCommit": "9f3c2a1", "codeMapCommit": null, "codeMapStatus": "building", "trackedEventCount": 87, "screenCount": 41, "syncedAt": "2026-10-15T08:55:02.117Z", "lastError": null}
```
- 에러: `VALIDATION_ERROR`, `UPSTREAM_ERROR`(클론 실패. 메시지에 토큰을 노출하지 않는다).

### POST /api/settings/repository/sync
- 용도: 등록된 저장소를 pull하고 커밋이 바뀌었으면 인덱스를 다시 만들고 바뀐 파일만 요약을 갱신한다.
- 요청: 본문 없음.
- 응답 200: `repository` 객체. 커밋이 바뀌었으면 `codeMapStatus: "building"`, 같으면 기존 상태 그대로.
```json
{"url": "https://github.com/team-skyjs/kbap-fe", "branch": "develop", "headCommit": "b71e04d", "codeMapCommit": "9f3c2a1", "codeMapStatus": "building", "trackedEventCount": 89, "screenCount": 41, "syncedAt": "2026-10-15T11:30:12.660Z", "lastError": null}
```
- 에러: `REPOSITORY_NOT_CONFIGURED`, `UPSTREAM_ERROR`. `UPSTREAM_ERROR`일 때도 같은 사유를 `repository.lastError`에 저장하고 기존 클론·인덱스는 유지한다.

### PUT /api/settings/taxonomy
- 용도: 택사노미 전체 교체 업로드. 프론트는 사용자가 고른 `.json` 파일 내용을 그대로 본문으로 보낸다.
- 요청:
```json
{
  "events": [
    {
      "name": "scan_complete",
      "description": "메뉴판 스캔이 끝나 결과 화면에 도달했거나 실패했을 때",
      "category": "scan",
      "properties": [
        {"name": "success", "type": "boolean", "description": "스캔 성공 여부"},
        {"name": "fail_reason", "type": "string", "description": "실패 사유 코드. 성공이면 없음"},
        {"name": "item_count", "type": "number", "description": "인식된 메뉴 수"}
      ]
    },
    {
      "name": "scan_start",
      "description": "카메라 촬영 또는 갤러리 선택으로 스캔을 시작했을 때",
      "category": "scan",
      "properties": [
        {"name": "source", "type": "string", "description": "camera 또는 gallery"}
      ]
    }
  ]
}
```
  - `events` 1개 이상. `name` 필수·중복 불가. `description`, `category`는 문자열 또는 `null`. `properties`는 빈 배열 가능, 속성 `type`은 `"string"` | `"number"` | `"boolean"`.
- 응답 200:
```json
{"eventCount": 2, "uploadedAt": "2026-10-15T11:40:00.000Z"}
```
- 에러: `VALIDATION_ERROR`. 검증은 전부 통과해야 반영하며, 실패하면 기존 택사노미를 그대로 둔다. `message`는 첫 번째 잘못된 항목의 위치와 사유를 담는다.
```json
{"error": {"code": "VALIDATION_ERROR", "message": "events[3].properties[0].type: \"date\"는 허용되지 않습니다. string, number, boolean 중 하나여야 합니다."}}
```

### POST /api/integrations/amplitude/connect
- 용도: Amplitude MCP OAuth 시작. 프론트는 받은 URL을 새 탭으로 연다.
- 요청: 본문 없음.
- 응답 200:
```json
{"authorizationUrl": "https://app.amplitude.com/oauth/authorize?response_type=code&client_id=mcp-4f2a91&redirect_uri=https%3A%2F%2Fpm-agent.example.com%2Fapi%2Fintegrations%2Famplitude%2Fcallback&state=Zx81kQ&code_challenge=Q9v0aR3&code_challenge_method=S256"}
```
  (URL의 호스트·쿼리는 Amplitude가 정한다. 프론트는 문자열을 그대로 연다.)
- 에러: `UPSTREAM_ERROR`.
- 비고: 승인 완료는 이 응답으로 알 수 없다. 프론트는 새 탭을 연 뒤 `GET /api/settings`를 3초 간격으로 최대 2분 다시 읽어 `amplitude.status`가 `"connected"`가 되면 멈춘다.

### GET /api/integrations/amplitude/callback
- 용도: Amplitude가 브라우저를 돌려보내는 OAuth 콜백. 인증 불필요. 프론트가 직접 부르지 않는다.
- 요청: 쿼리 `code`, `state` (Amplitude가 붙인다).
- 응답 200: `text/html` 한 줄 페이지. 성공 시 "Amplitude 연결 완료. 이 탭을 닫아도 됩니다.", 실패 시 "Amplitude 연결 실패: {사유}". JSON 아님.

### POST /api/questions/refine
- 용도: 사용자가 보내기 전에 질문을 다듬는다. 서버가 택사노미 이벤트 이름과 그 대화의 최근 메시지를 붙여 모델을 한 번 호출하고(도구 없음), 개선된 질문 하나와 변경 요약을 돌려준다. 호출마다 기록 행을 만든다.
- 요청:
```json
{"conversationId": 7, "question": "스캔 이탈 왜 많아?"}
```
  - `question`: 1~4000자(메시지 전송과 같은 규칙). 앞뒤 공백만 있으면 `VALIDATION_ERROR`.
  - `conversationId`: 대화 ID 또는 `null`. `null`이면 대화 이력 없이 다듬는다. 없는 ID면 404 `CONVERSATION_NOT_FOUND`.
- 응답 200:
```json
{"refinementId": 31, "refined": "최근 7일 scan_start → scan_complete(success=true) 퍼널에서 이탈이 가장 큰 단계를 찾고, 그 원인이 되는 화면 동작과 개선안을 제안해줘.", "summary": "기간을 최근 7일로 정하고(원문에 없음), 이벤트 이름과 원하는 산출물(개선안)을 명시했다."}
```
  - `refinementId`: 기록 행 ID. 선택 기록(아래)에 쓴다.
  - `refined`: 개선된 질문. 한국어 두 문장 이내, 1~4000자. 모델 출력이 이 범위를 벗어나면 서버는 502 `UPSTREAM_ERROR`로 응답하고 기록 행을 만들지 않는다(잘라서 돌려주지 않는다).
  - `summary`: 무엇이 달라졌는지 한 줄, 1~300자. 원문에 없던 기본값(기간 등)을 넣었으면 그 사실을 적는다. 택사노미 이름 목록이 4,000자를 넘어 서버가 일부만 넘겼으면 서버가 요약 끝에 `(택사노미 이름이 많아 앞부분만 참고)`을 붙인다(합쳐서 300자 이내로 앞을 줄인다). 일부를 고르는 규칙은 다음과 같다. 4,000자를 넘을 때만 고르는 순서를 바꾼다. 질문과 겹치는 이름(이름 전체가 질문에 들어 있거나, 이름을 `_`로 나눈 조각 하나가 질문의 영숫자 낱말(소문자)과 같음)을 원래 순서대로 먼저 넣는다. 남은 자리는 나머지 이름을 원래 순서대로 4,000자 안에서 채운다.
- 에러: `VALIDATION_ERROR`, `CONVERSATION_NOT_FOUND`, 403 `BUDGET_EXCEEDED`(호출 전 예산 검사), 502 `UPSTREAM_ERROR`(모델 호출 실패나 구조화 출력 검증 실패, 기록 행은 만들지 않는다). 공통 인증 규칙(`ACCESS_TOKEN`)은 다른 `/api` 요청과 같다.
- 비고: 사용량은 `llm_usage`에 용도 `refine`으로 남고 예산에 합산된다. 대화 메시지가 아니라 `messages`·`usage` 응답에는 나타나지 않는다. 모델은 `REFINE_MODEL`, 비어 있으면 `CODE_SUMMARY_MODEL`이다.

### POST /api/questions/refine/{refinementId}/choice
- 용도: 다듬기 결과를 사용자가 어떻게 골랐는지 기록한다. 채택 비율 집계용이며 화면에는 보이지 않는다.
- 요청:
```json
{"choice": "refined"}
```
  - `choice`: `"refined"`(개선안으로 보내기, 또는 "입력창에 넣기" 뒤 실제로 전송했을 때. 편집 후 전송도 채택으로 센다) | `"original"`(원문으로 보내기) | `"cancelled"`(ESC·닫기, 또는 "입력창에 넣기" 뒤 전송 없이 입력을 비우거나, 대화를 떠나거나, 새로 다듬기를 시작했을 때).
- 응답 200:
```json
{"refinementId": 31, "choice": "refined", "chosenAt": "2026-10-15T10:02:11.204Z"}
```
- 에러: `VALIDATION_ERROR`, `REFINEMENT_NOT_FOUND`.
- 비고: 다시 부르면 마지막 값으로 덮어쓰고 `chosenAt`을 갱신한다. 프론트는 선택이 확정될 때 한 번만 부른다. 보내기 두 개와 닫기는 클릭 시점, "입력창에 넣기"는 클릭이 아니라 그 뒤 전송·비우기·대화 이탈·새 다듬기 시작 시점이다. 기록 실패는 전송을 막지 않는다. 프론트는 실패를 무시하고 메시지 전송을 이어 간다.

### POST /api/conversations/{conversationId}/exports
- 용도: 사용자가 대화를 내보냈다는 사실(형식)을 기록한다. 내보내기 건수·형식 집계용이며 화면에는 보이지 않는다. 내보내기 자체(PDF 인쇄, Markdown 파일 생성)는 프론트가 하고 서버는 파일을 만들지 않는다.
- 요청:
```json
{"format": "markdown"}
```
  - `format`: `"pdf"`(인쇄 대화상자를 열었을 때. 실제 저장 여부는 알 수 없다) | `"markdown"`(파일 내려받기를 시작했을 때).
- 응답 201:
```json
{"exportId": 12, "conversationId": 7, "format": "markdown", "createdAt": "2026-10-17T03:20:45.118Z"}
```
- 에러: `VALIDATION_ERROR`(형식 밖 값, 본문 오류), `CONVERSATION_NOT_FOUND`. 공통 인증 규칙(`ACCESS_TOKEN`)은 다른 `/api` 요청과 같다.
- 비고: 프론트는 내보내기를 시작하면서 한 번 부르고 결과를 기다리지 않는다. 기록 실패는 내보내기를 막지 않는다. 시연 모드도 실제로 기록한다(외부 호출이 없다).

## 엔드포인트 요약

| 메서드 | 경로 | 인증 | 응답 |
|---|---|---|---|
| GET | `/api/health` | 불필요 | JSON |
| GET | `/api/conversations` | 필요 | JSON |
| POST | `/api/conversations` | 필요 | JSON 201 |
| GET | `/api/conversations/{conversationId}` | 필요 | JSON |
| POST | `/api/conversations/{conversationId}/messages` | 필요 | SSE |
| PATCH | `/api/proposals/{proposalId}` | 필요 | JSON |
| POST | `/api/questions/refine` | 필요 | JSON |
| POST | `/api/questions/refine/{refinementId}/choice` | 필요 | JSON |
| POST | `/api/conversations/{conversationId}/exports` | 필요 | JSON 201 |
| GET | `/api/settings` | 필요 | JSON |
| PUT | `/api/settings/repository` | 필요 | JSON |
| POST | `/api/settings/repository/sync` | 필요 | JSON |
| PUT | `/api/settings/taxonomy` | 필요 | JSON |
| POST | `/api/integrations/amplitude/connect` | 필요 | JSON |
| GET | `/api/integrations/amplitude/callback` | 불필요 | HTML |

CORS: 백엔드는 `CORS_ORIGINS`의 출처에 대해 위 메서드 전부와 `Authorization`, `Content-Type` 헤더의 preflight를 허용한다.
