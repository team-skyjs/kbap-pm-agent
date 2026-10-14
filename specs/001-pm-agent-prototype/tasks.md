---
description: "PM Agent 프로토타입 구현 태스크"
---

# Tasks: PM Agent 프로토타입

**Input**: `specs/001-pm-agent-prototype/`의 plan.md, spec.md, data-model.md, contracts/(계약서 v1.1), research.md, quickstart.md

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 모듈마다 `assert` 검사 스크립트 태스크 하나와 QA 교차 검증 태스크 하나를 둔다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명 (모듈)`

- **[P]**: 다른 파일을 건드리고 미완료 태스크에 의존하지 않아 병렬 가능
- **[US1]~[US4]**: spec.md 사용자 스토리. Setup·Foundational·Polish 단계에는 붙이지 않는다
- **역할**: `[BE]` backend-dev, `[FE]` frontend-dev, `[QA]` qa-integrator
- **모듈**: `_workspace/01_cto_task-split.md`의 B1~B8, F1~F6. 모듈 하나는 한 단계 안에서 끝난다

## 공통 규칙 (모든 태스크)

- 응답·요청 shape는 `contracts/`가 유일한 기준이다. 맞지 않으면 구현을 바꾸지 말고 CTO에 계약 변경을 요청한다(헌법 원칙 I).
- 외부 호출은 `backend/app/repo.py`(GitHub), `backend/app/amplitude.py`(Amplitude MCP), `backend/app/agent.py`(모든 LLM 호출: 에이전트 실행과 코드 요약 `summarize()`) 세 파일에서만 한다. 각 파일은 `AGENT_MODE=fake` 분기를 가진다(원칙 III, ADR-15).
- 의도적 단순화에는 `ponytail:` 주석을 단다(원칙 II).
- 프론트 계약 타입은 `frontend/src/api.ts`에만 두고 `any`·타입 캐스팅을 쓰지 않는다(원칙 I).
- 모듈의 QA 태스크가 통과하면 모듈 단위로 커밋한다(`feat(backend): ...`, `feat(frontend): ...`).

---

## Phase 1: Setup

**Purpose**: 레포 뼈대. 두 역할이 동시에 시작한다.

- [x] T001 [BE] 레포 루트에 `.gitignore`(`.env`, `node_modules`, `dist`, `.venv`, `__pycache__`), `.env.example`(ADR 환경변수 표 전부, `AGENT_MODE=fake` 기본), `docker-compose.yml` 작성. 서비스는 `backend`(build `./backend`, `8000:8000`, `AGENT_MODE=${AGENT_MODE:-fake}`, `DATABASE_URL`, `CORS_ORIGINS=http://localhost:5173`, 볼륨 `/data`)와 `mysql`(`mysql:8.4`, `3307:3306`, 볼륨, DB `kbap_pm_agent`, healthcheck). backend는 mysql healthy 이후 기동 (B1)
- [x] T002 [P] [BE] `backend/pyproject.toml` + `backend/uv.lock`: Python 3.12, fastapi, uvicorn, langchain 1.x, langchain-anthropic, langchain-openai, langchain-mcp-adapters, mcp, MySQL 드라이버(위임) (B1)
- [x] T003 [P] [BE] `backend/Dockerfile`: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` 기반, `git`·`ripgrep` 설치, `uv sync --frozen`, `uvicorn app.main:app --host 0.0.0.0 --port 8000` 단일 워커(`ponytail:` 주석에 단일 워커 이유) (B1)
- [x] T004 [P] [FE] `frontend/`에 Vite + React + TS 프로젝트 생성. `frontend/vite.config.ts`의 `base: '/kbap-pm-agent/'`. `frontend/package.json` 스크립트 `dev`·`build`·`preview`·`check`(`frontend/checks/check-<모듈>.ts` 실행, 실행기는 research.md 메모대로 하나 고정) (F1)

---

## Phase 2: Foundational — 서버 뜬다 / 화면 뜬다 + 헬스체크 왕복 (B1, F1)

**Purpose**: QA가 처음 검증하는 최소 경계면. 모든 스토리의 전제다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 스토리 작업을 시작하지 않는다.

- [x] T005 [BE] `backend/schema.sql`: data-model.md의 6개 테이블을 `CREATE TABLE IF NOT EXISTS`로 작성. 제약을 그대로 옮긴다. 예: `role ENUM('user','assistant')`, `status ENUM('running','completed','failed')`, `decision_status ENUM('pending','adopted','on_hold') DEFAULT 'pending'`, `llm_usage.message_id ... ON DELETE SET NULL`, 나머지 FK `ON DELETE CASCADE`, `utf8mb4`, 시각 `DATETIME(3)` (B1)
- [x] T006 [BE] `backend/app/db.py`: `DATABASE_URL` 연결, 기동 시 `schema.sql` 실행, 쿼리 헬퍼. ORM 없이 시작(`ponytail:` 주석) (B1)
- [x] T007 [BE] `backend/app/main.py`: FastAPI 앱 생성. `CORS_ORIGINS`(쉼표 구분) CORS, `Authorization`·`Content-Type` 허용. `ACCESS_TOKEN`이 비어 있지 않으면 `/api/health`·`/api/integrations/amplitude/callback`을 뺀 모든 경로에 Bearer 검사(401 `UNAUTHORIZED`). 공통 에러 핸들러: 요청 검증 오류 → 400 `VALIDATION_ERROR`(FastAPI 422 금지), 없는 경로 → 404 `NOT_FOUND`, 처리되지 않은 예외 → 500 `INTERNAL_ERROR`. 형식은 `contracts/01-common.md` (B1)
- [x] T008 [BE] `backend/app/main.py`에 `GET /api/health`: DB 정상 `{"status":"ok","db":"ok","version":"0.1.0"}`, DB 실패도 200으로 `{"status":"degraded","db":"error","version":"0.1.0"}` (`contracts/03-health.md`) (B1)
- [x] T009 [BE] `backend/checks/check_b1.py`: assert 스크립트. health 응답이 계약 예시와 같은 키·값, 없는 경로가 공통 에러 형식 404, `Origin: http://localhost:5173` preflight 통과, `ACCESS_TOKEN` 설정 시 health 200·`/api/nope` 401 `UNAUTHORIZED`, 미설정 시 health 200·`/api/nope` 404 `NOT_FOUND`(research.md R3) (B1 검사)
- [x] T010 [P] [FE] `frontend/src/api.ts`: `VITE_API_BASE_URL` 기준 공통 `request()`. `localStorage`의 접근 토큰을 Bearer로 붙이고, 비 2xx 응답은 `{"error":{"code","message"}}`를 파싱해 `ApiError(code, message)`로 던진다. `Health` 타입과 `getHealth()` (F1)
- [x] T011 [FE] `frontend/src/main.tsx`, `frontend/src/App.tsx`: 해시 라우터, 상단에 헬스 배지("ok" / "degraded" / "연결 실패") (F1)
- [x] T012 [FE] `frontend/checks/check-f1.ts`: `contracts/03-health.md`의 두 예시 JSON과 `contracts/01-common.md`의 에러 예시가 `api.ts` 타입·파서를 통과하고 에러 `code`가 `"CONVERSATION_NOT_FOUND"`로 읽힌다 (F1 검사)
- [x] T013 [QA] F1↔B1 교차 검증: `docker compose up` 후 `localhost:5173` → `localhost:8000` health 왕복, CORS preflight, 401·404 형식, `npm run build && npm run preview`에서 `/kbap-pm-agent/` 하위 경로 동작, `check_b1.py`·`check-f1.ts` 실행 결과 (B1·F1 QA)

**Checkpoint**: 양쪽이 뜨고 헬스체크가 왕복한다.

---

## Phase 3: User Story 1 — 근거 있는 기획 제안 받기 (Priority: P1) 🎯 MVP (B2, B3, F3, F4)

**Goal**: fake 모드에서 질문 → 진행 표시 → 4부분 제안 카드 → 채택이 끝까지 동작한다.

**Independent Test**: `AGENT_MODE=fake`에서 새 대화에 질문을 보내면 5초 안에 도구 호출 진행이 보이고, 제안 2장이 근거→제안→실행단계→측정방법 순으로 표시되며, "채택" 후 새로고침해도 상태와 결정 시각이 유지된다(quickstart 시나리오 3·5).

### B2 — 대화·제안 저장

- [x] T014 [P] [US1] [BE] `backend/app/schemas.py`: `contracts/02-objects.md`의 ConversationSummary, Message, ToolCall, Proposal, Settings Pydantic 모델(camelCase 별칭, null 규칙). 규칙을 모델에 그대로 넣는다.
  - Evidence는 `kind` 판별 유니온(metric `{summary,value,source}` / code `{summary,file,function,line,snippet}` / taxonomy `{summary,eventName}`)이고, 다른 kind의 키는 직렬화하지 않는다.
  - FunnelStep은 `"status가 \"new\"면 location(file, function, line) 필수, \"existing\"이면 location: null"`, `order`가 1부터 연속, properties `type`이 `"string" | "number" | "boolean"`.
  - `funnel_design`이면 `funnel` 1개 이상, `evidence`·`steps`는 1개 이상.
  - 에이전트 최종 응답 모델 `AgentAnswer{content, proposals[]}`도 둔다. (B2)
- [x] T015 [US1] [BE] `backend/app/conversations.py`: 아래 세 엔드포인트, 응답은 `contracts/04-conversations.md`. (B2)
  - `GET /api/conversations`: `{"items":[...]}`, `updatedAt` 내림차순, `messageCount`·`proposalCount`·`adoptedCount` 조회 시 집계.
  - `POST /api/conversations`: 본문 `{}` 또는 `title` 1~200자, 201.
  - `GET /api/conversations/{conversationId}`: 메시지 `createdAt` 오름차순, toolCalls `seq` 오름차순, proposals 포함, `usage`는 `llm_usage` 합산, user 메시지 `usage: null`. 없으면 404 `CONVERSATION_NOT_FOUND`.
- [x] T016 [US1] [BE] `backend/app/conversations.py`에 `PATCH /api/proposals/{proposalId}`: `status` 필수(`pending|adopted|on_hold`), `note` 생략 시 유지·`null`이면 삭제·최대 1000자, status 변경마다 `decidedAt` 갱신·`pending`이면 `null`, 대화 `updated_at` 갱신, 없으면 404 `PROPOSAL_NOT_FOUND`. 응답은 Proposal 전체(`contracts/06-proposals.md`) (B2)
- [x] T017 [US1] [BE] `backend/checks/check_b2.py`: `contracts/02`·`04`·`06`의 예시 JSON이 `schemas.py` 모델을 통과하고 재직렬화 결과가 원문과 같은 키 구조. 시험 제안을 DB에 넣고 PATCH `adopted`→`pending`에서 `decidedAt`이 채워졌다가 `null`. 잘못된 status가 400 `VALIDATION_ERROR` (B2 검사)
- [x] T018 [US1] [QA] B2 교차 검증: 네 엔드포인트 응답을 계약 예시와 키 단위로 대조(null 규칙, `items` 감싸기, camelCase, 201), `check_b2.py` 실행 (B2 QA)

### B3 — 메시지 전송 SSE (fake)

- [x] T019 [US1] [BE] `backend/app/agent.py`: 에이전트 실행 seam `run_agent(conversation_id, content)`가 내부 이벤트를 비동기로 낸다. fake 분기는 계약서 시연 모드 표대로 도구 호출 2개(`taxonomy`, `code`)와 제안 2개(`improvement` 1, `funnel_design` 1)를 계약 예시 값으로 내고, `usage.costUsd`는 `0`이다. real 분기는 B6에서 채운다 (B3)
- [x] T020 [US1] [BE] `backend/app/conversations.py`에 `POST /api/conversations/{conversationId}/messages`(`contracts/05-messages.md`). (B3)
  - 스트림 전 JSON 에러: `content` 1~4000자 위반 `VALIDATION_ERROR`, `CONVERSATION_NOT_FOUND`, running 메시지 존재 시 409 `RUN_IN_PROGRESS`. 예산 검사(403 `BUDGET_EXCEEDED`)는 B5의 T035에서 붙인다.
  - 처리 순서: user 메시지 저장 → 제목이 null이면 앞 40자로 채움 → assistant 메시지 `running` 생성 → `message_created`.
  - 도구 호출은 `tool_call`/`tool_result`마다 DB에 반영한다. 끝은 `final`(completed) 또는 `error`(failed, `errorCode`) 정확히 하나.
  - 15초마다 `: ping`. 헤더 `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
  - 클라이언트가 끊기면 `failed`/`INTERNAL_ERROR`로 마감한다.
- [x] T021 [US1] [BE] `backend/checks/check_b3.py`: fake 실행 SSE를 받아 이벤트 순서(`message_created` 1회 → 도구 쌍 → 종료 이벤트 1회), `final` 데이터가 Message 모델 통과, 같은 대화 `GET` 상세의 assistant 메시지가 `final`과 동일, 실행 중 재전송 409 (B3 검사)
- [x] T022 [US1] [QA] B3 교차 검증: curl로 SSE 원문을 계약 예시와 대조(이벤트 이름, data 한 줄 JSON, 빈 줄), ping 간격, 끊김 후 `failed` 마감, `check_b3.py` 실행 (B3 QA)

### F3 — 채팅 화면: 생성·상세·스트리밍

- [x] T023 [P] [US1] [FE] `frontend/src/api.ts`. (F3)
  - 타입: `contracts/02-objects.md`의 ConversationSummary, Message, ToolCall, Proposal. Evidence는 `kind` 판별 유니온, FunnelStep `status`는 `"existing" | "new"`.
  - 함수: `createConversation()`, `getConversation(id)`.
  - `sendMessage(id, content, handlers)`: `fetch` + `ReadableStream`으로 SSE를 파싱한다. `: ping`은 무시하고 `message_created`·`tool_call`·`tool_result`·`final`·`error`를 처리하며, 스트림 전 JSON 에러는 `ApiError`로 던진다.
- [x] T024 [US1] [FE] `frontend/src/Chat.tsx`: 경로 `#/conversations/:id`. (F3)
  - 대화 열기·전송: "새 대화" → POST 후 이동. 메시지는 마크다운으로 렌더하고, 도구 호출은 접힌 목록으로 둔다.
  - 진행 표시: 실행 중 `tool_call`→`tool_result`로 진행 줄(어느 소스 조회 중인지)을 갱신하고, `final`로 메시지를 교체한다.
  - 오류·복구: `error`는 메시지 하단에 code별 문구로 표시한다. 스트림이 끊기면 상세를 다시 조회한다. 409·403은 입력창 아래에 안내하고, 실행 중에는 입력을 비활성화한다.
- [x] T025 [US1] [FE] `frontend/checks/check-f3.ts`: `contracts/05-messages.md`의 SSE 예시 원문(ping 줄 추가)을 파서에 넣어 이벤트 순서와 타입이 맞고 `final`이 Message로 읽힌다. `contracts/04`의 상세 예시가 타입을 통과한다 (F3 검사)
- [x] T026 [US1] [QA] F3↔B3 교차 검증(fake): 질문 전송부터 첫 진행 표시까지 5초 이내(SC-004), 이벤트별 화면 상태, 새로고침 후 상세 일치, 409 표시, `check-f3.ts` 실행 (F3 QA)

### F4 — 제안 카드 + 채택/보류

- [x] T027 [US1] [FE] `frontend/src/ProposalCard.tsx`: 네 영역을 근거→제안→실행단계→측정방법 순서로 둔다. (F4)
  - 근거는 kind별로 그린다. metric은 값과 출처, code는 `파일:줄`·함수·snippet, taxonomy는 이벤트명.
  - 측정방법은 `primaryMetric`, `baseline`, `target`과 퍼널 표(순서·이벤트·기존/신규·조건·위치·속성)다. 신규 단계는 강조한다.
  - "채택"·"보류" 버튼과 메모 입력을 둔다. `Chat.tsx` 메시지 아래에 카드를 렌더한다.
- [x] T028 [US1] [FE] `frontend/src/api.ts`에 `updateProposal(id, {status, note})`. 응답 Proposal로 카드 상태를 갱신한다 (F4)
- [x] T029 [US1] [FE] `frontend/checks/check-f4.ts`: `contracts/02-objects.md`의 Proposal 예시와 `contracts/04`의 improvement 예시가 타입을 통과하고, 렌더 헬퍼가 네 영역 순서를 지키며, 신규 단계 위치 문자열이 `src/app/scan.tsx · handleRetry · 398`로 만들어진다 (F4 검사)
- [x] T030 [US1] [QA] F4↔B2·B3 교차 검증: fake 제안 2장의 카드 렌더를 계약 필드와 대조, 채택→새로고침 유지(US1-2), 보류·메모·`pending` 복귀 시 `decidedAt` 표시, `check-f4.ts` 실행 (F4 QA)

**Checkpoint**: fake 모드 MVP. US1 인수 시나리오 1~3을 시연 데이터로 통과한다. 시나리오 4와 실제 데이터는 Phase 4·6 뒤에 확인한다.

---

## Phase 4: User Story 2 — 측정 설계 제안 받기 (Priority: P2) (B4, B5, B6)

**Goal**: 실제 FE 저장소와 택사노미를 읽어, 퍼널 단계마다 기존/신규와 신규 이벤트의 파일·함수를 내는 실제 에이전트. 같은 엔진으로 US1의 실제 모드도 완성된다.

**Independent Test**: kbap-fe를 등록하고 택사노미를 올린 뒤 "장바구니 개선 효과를 측정하고 싶다"를 보낸다. `funnel_design` 제안의 퍼널이 2단계 이상이고, 신규 단계마다 클론에 실제로 있는 파일·함수가 들어가면 통과다.

**선행 메모**: 저장소·택사노미 백엔드(B4)는 US4 설정 화면에도 쓰이지만, 코드 위치를 내려면 클론이 먼저 있어야 해서 여기서 만든다. 설정 UI(F5)는 Phase 6에 있다. 그때까지 QA는 curl로 등록한다.

### B4 — 저장소·택사노미

- [x] T031 [US2] [BE] `backend/app/repo.py`: 외부 seam. `REPOS_DIR` 아래 얕은 클론·pull·HEAD 7자리 SHA를 다룬다. (B4)
  - 인증: `GITHUB_TOKEN`이 있으면 HTTPS URL에 넣되 로그·예외 메시지에서 제거한다.
  - 인덱스: rg로 `CODE_GLOB`(기본 `*.{ts,tsx,js,jsx}`) 파일만 대상으로 `TRACK_CALL_PATTERN` 인덱스(이벤트명 → `[{file,line,function}]`)를 만들고, `SCREEN_GLOB`로 화면 수를 센다. 문서 파일은 제외한다(ADR-19).
  - 실패 처리: 실패 사유를 `lastError` 문장으로 만든다.
  - fake 분기: 클론 없이 계약서 Settings 예시 값을 돌려준다.
- [x] T032 [US2] [BE] `backend/app/settings.py`: `contracts/07-settings.md` 그대로. (B4)
  - `GET /api/settings`: `models`·`agentMode`·`budget.limitUsd`는 환경변수, `spentUsd`는 `llm_usage` 합계.
  - `PUT /api/settings/repository`: `url`은 `https://github.com/` 또는 `file://`로 시작해야 한다. 클론과 인덱스 후 응답하고 `codeMapStatus`를 시작한다.
  - `POST /api/settings/repository/sync`: 미등록이면 409 `REPOSITORY_NOT_CONFIGURED`. 실패하면 502 `UPSTREAM_ERROR`를 내되 `lastError`를 저장하고 기존 클론을 유지한다.
  - `PUT /api/settings/taxonomy`: 전부 통과해야 교체한다. 실패하면 기존 값을 유지하고 `message`에 `"events[3].properties[0].type: ..."` 식으로 첫 위반 위치를 적는다. `app_settings` 키 `repository`·`taxonomy`.
- [x] T033 [US2] [BE] `backend/checks/check_b4.py`: `file://` 시험 저장소(`track(EVENTS.a)` 3곳)를 등록해 `trackedEventCount == 3`, sync 시 HEAD 변경 반영, 택사노미 계약 예시 업로드 `eventCount == 2`, `"date"` 타입 업로드가 400이고 `eventCount` 2 유지, fake 모드 `PUT /api/settings/repository` 응답이 계약 예시 값 (B4 검사)
- [x] T034 [US2] [QA] B4 교차 검증: 실제 `team-skyjs/kbap-fe` 클론. `trackedEventCount`가 소스 파일 호출 수(`rg -o -g '*.{ts,tsx,js,jsx}' 'track\(EVENTS\.' | wc -l`, 한 줄에 여러 번 있으면 각각 센다)와 같은지 본다. kbap-fe develop f34c518 기준 117(문서 매치 3건 제외, ADR-19). 인덱스·`search_code` 결과에 `.md` 파일이 없는지도 확인한다(QA-2). 토큰을 빼고 동기화했을 때 `UPSTREAM_ERROR`이면서 `lastError` 사유가 남고, 응답·로그에 토큰 문자열이 없는지 확인한다(research.md R6). `check_b4.py` 실행 (B4 QA)

### B5 — 코드 도구 + 요약 캐시 + 예산

- [x] T035 [P] [US2] [BE] `backend/app/budget.py`: 모든 LLM 호출의 사용량을 기록하고 예산을 검사한다. (B5)
  - 기록: `record(purpose, model, input_tokens, output_tokens, message_id)`가 단가표(설정)로 `cost_usd`를 계산해 `llm_usage`에 넣는다. fake 모드도 토큰 0·`cost_usd` 0 행을 기록한다(fake `usage.costUsd` 0이 이 합산에서 나온다).
  - 검사: `check()`는 `SUM(cost_usd) >= LLM_BUDGET_USD`이면 `BUDGET_EXCEEDED`를 낸다. `backend/app/conversations.py`의 메시지 전송 라우트에서 스트림 시작 전에 `check()`를 호출하도록 붙인다(계약 05-messages의 스트림 전 에러).
- [x] T036 [US2] [BE] `backend/app/code_tools.py`: 에이전트 도구. (B5)
  - 코드 도구: `find_event_calls(eventName)`(인덱스), `search_code(regex, glob)`(rg, 최대 30건, `CODE_GLOB` 범위 안에서만 — ADR-19), `get_screen_summary(path)`(캐시), `read_code(path, startLine, endLine)`(호출당 최대 200줄, 저장소 밖 경로 거부).
  - 택사노미 도구: `search_taxonomy(query)`, `get_event_definition(name)`. source는 `taxonomy`.
  - 요약 캐시: 동기화 후 백그라운드로 화면 요약을 만든다. 키는 `(path, blob SHA)`이고 재시작 후에도 유지된다. 바뀐 blob만 다시 요약한다. 요약 LLM 호출은 `backend/app/agent.py`의 `summarize(text)`(`CODE_SUMMARY_MODEL`, fake 분기 포함)를 통해서만 하며, 호출 전 `budget.check()`를 부른다. `code_tools.py`는 모델을 직접 만들지 않는다(원칙 III). 상태는 `codeMapStatus` `building`→`ready`|`failed`, `codeMapCommit`으로 반영한다. 파일 통째 전송 도구는 만들지 않는다(원칙 IV).
- [x] T037 [US2] [BE] `backend/checks/check_b5.py`: `read_code` 201줄 요청이 200줄로 잘림, `search_code` 31건 이상 매치가 30건, 같은 커밋 재동기화 시 `llm_usage` 행 증가 0, 파일 1개 변경 후 1, `LLM_BUDGET_USD=0.01`에서 메시지 전송이 403 `BUDGET_EXCEEDED` (B5 검사)
- [x] T038 [US2] [QA] B5 교차 검증: settings의 `codeMapStatus`·`codeMapCommit`·`budget.spentUsd` 변화가 계약과 일치, 예산 초과 시 대화 조회는 계속 200(엣지 케이스), `check_b5.py` 실행 (B5 QA)

### B6 — 실제 에이전트 루프

> T039의 LangChain `create_agent` 구현은 Phase 8(B9, ADR-20)에서 공급자별 공식 SDK로 대체된다. SSE·상한·실패 처리 요구는 그대로 유지한다.


- [x] T039 [US2] [BE] `backend/app/agent.py` real 분기. (B6)
  - 구성: `init_chat_model(AGENT_MODEL)`과 `create_agent(model, tools=code_tools+taxonomy_tools, system_prompt, response_format=AgentAnswer)`를 쓴다.
  - 스트리밍: `astream(stream_mode="updates")`를 `tool_call`/`tool_result`/`final`로 변환한다.
  - 상한: `AGENT_MAX_TOOL_CALLS`(20) 또는 `AGENT_TIMEOUT_SECONDS`(170)에 닿으면 그때까지의 결과로 `final`을 보낸다. `status: "completed"`이고 `content` 첫 문장에 중단 사유를 적는다(ADR-16).
  - 실패 처리: 도구가 실패하면 `tool_result` `failed`로 보내고 실행은 계속한다. 모델 호출 자체가 실패하면 `error` `UPSTREAM_ERROR`다.
  - 사용량: 매 호출을 `budget.record`로 기록한다.
- [x] T040 [US2] [BE] `backend/app/agent.py` 시스템 프롬프트(코드에 모델명 금지). 담을 지시는 다음과 같다. (B6)
  - 제안은 반드시 근거→제안→실행단계→측정방법이다.
  - 근거는 metric·code·taxonomy로 구분하고, code 근거에는 파일·함수를 쓴다.
  - 신규 이벤트는 파일·함수 위치가 필수다.
  - 택사노미에 있으나 코드에 없으면 근거에 "정의는 있으나 코드에서 발견되지 않음"(US2-3)으로 쓰고, 코드에만 있으면 "코드에만 존재, 정의 없음"(엣지 케이스)으로 쓴다.
  - 쓸 수 없는 소스가 있으면 `content`에 빠진 근거를 명시한다(FR-010).
- [x] T041 [US2] [BE] `backend/checks/check_b6.py`: `AgentAnswer`가 계약 예시 제안 2개를 통과하고, 신규 단계 `location: null`·`order` 불연속·`funnel_design` 빈 funnel을 거부한다. 상한 도달 시 만드는 부분 `final`이 Message 모델을 통과하고 `content`가 사유 문장으로 시작한다 (B6 검사)
- [ ] T042 [US2] [QA] B6 실제 모드 교차 검증(`AGENT_MODE=real`): (B6 QA)
  - US2 질문: 측정 설계 질문의 `funnel_design` 신규 단계 파일·함수가 클론에 실제로 있는지 grep으로 확인한다.
  - US1 질문: 개선 질문 하나로 4부분 제안이 나오는지 본다.
  - 모델 교체: `AGENT_MODEL`을 `openai:` 모델로 바꿔 한 번 실행한다(FR-014, research.md 메모).
  - SSE·상한: SSE 순서가 fake와 같은지, `AGENT_TIMEOUT_SECONDS=5`로 부분 `final`이 오는지 확인한다. FE 변경 없이 동작해야 한다.
  - 성능: 실제 질문 3개의 첫 `tool_call` 도착 시간(5초 이내)과 `final` 도착 시간(3분 이내)을 기록한다(SC-004).

**Checkpoint**: 실제 저장소·택사노미 기반으로 US1·US2가 동작한다(지표 근거는 Phase 6 뒤).

---

## Phase 5: User Story 3 — 대화 기록 보존과 재열기 (Priority: P3) (F2)

**Goal**: 과거 대화 목록에서 하나를 열어 당시 제안과 채택 상태를 다시 본다.

**Independent Test**: 대화 2개를 만들고 목록에서 최근 순·제목·시각·제안 수를 확인한다. 채택이 있는 대화를 다시 열어 메시지 순서와 채택 상태가 그대로인지 본다(quickstart 시나리오 6). 백엔드 목록 엔드포인트는 B2(T015)에서 이미 만들었다.

- [x] T043 [US3] [FE] `frontend/src/ConversationList.tsx`: 왼쪽 목록이다. `GET /api/conversations`를 쓰고 `updatedAt` 내림차순으로 보여준다. 제목이 `null`이면 "새 대화"로, 시각·`proposalCount`·`adoptedCount`를 함께 표시한다. 선택하면 `#/conversations/:id`로 간다. 메시지 `final`·제안 PATCH 후 목록을 다시 읽는다. `api.ts`에 `listConversations()` (F2)
- [x] T044 [US3] [FE] `frontend/checks/check-f2.ts`: `contracts/04-conversations.md`의 목록 예시가 타입을 통과하고, `title: null` 항목 표시 문자열이 "새 대화" (F2 검사)
- [x] T045 [US3] [QA] F2↔B2 교차 검증: 대화 2개 생성·정렬, 첫 메시지 후 제목 자동 채움(40자), 채택 1건 후 `adoptedCount` 1, 다시 열기 시 메시지 순서·채택 상태 보존(US3-1·2), `check-f2.ts` 실행 (F2 QA)

**Checkpoint**: US1~US3이 fake 모드로 처음부터 끝까지 동작한다(SC-005).

---

## Phase 6: User Story 4 — 소스 연결 설정 (Priority: P4) (B7, F5)

**Goal**: 택사노미 업로드, 저장소 등록·동기화, Amplitude 승인 연결을 한 화면에서 하고 상태를 본다.

**Independent Test**: quickstart 시나리오 7~10. 택사노미 업로드 후 이벤트 수가, 저장소 동기화 후 시각과 화면 수가 보여야 한다. 연결 승인 후 상태는 "연결됨"이어야 하고, 잘못된 택사노미는 위치가 담긴 오류와 함께 기존 값을 유지해야 한다.

### B7 — Amplitude MCP 연결

- [ ] T046 [US4] [BE] research.md R1 검증 스파이크(B7 첫 태스크): 로컬에서 MCP SDK `OAuthClientProvider`로 `AMPLITUDE_MCP_URL`에 동적 클라이언트 등록 → 승인 → `list_tools` 성공 여부를 확인한다. 막히면 즉시 CTO에 보고(대체 경로: 고정 client_id 또는 `../kbap-amplitude/amp.py`) (B7)
- [x] T047 [US4] [BE] `backend/app/amplitude.py`: 외부 seam. (B7)
  - OAuth 저장: `OAuthClientProvider`와 `app_settings` 키 `amplitude_oauth` 기반 토큰 저장소를 쓴다. 토큰은 API로 노출하지 않는다.
  - 승인 URL: redirect handler가 승인 URL을 잡아 `POST /api/integrations/amplitude/connect`가 `{"authorizationUrl": ...}`로 응답한다.
  - 콜백: `GET /api/integrations/amplitude/callback`이 code·state를 받아 토큰을 교환하고 한 줄 HTML("Amplitude 연결 완료. 이 탭을 닫아도 됩니다." / "Amplitude 연결 실패: {사유}")을 낸다. redirect_uri는 `PUBLIC_BASE_URL`로 만든다.
  - fake 분기: 예시 URL을 응답하고 즉시 connected (`contracts/08-amplitude.md`).
- [x] T048 [US4] [BE] `backend/app/agent.py`·`backend/app/settings.py` 연결: 연결된 경우에만 `MultiServerMCPClient` 도구를 `source: "amplitude"`로 에이전트 도구에 더한다. MCP 호출 실패는 `tool_result` `failed`로 보내고 실행은 계속한다(US1-4, FR-010). settings `amplitude.status`·`connectedAt`·`serverUrl`을 반영한다 (B7)
- [x] T049 [US4] [BE] `backend/checks/check_b7.py`: fake 모드 connect 응답이 계약 예시와 같고 직후 settings `amplitude.status == "connected"`. 콜백이 `text/html`. Amplitude 도구가 예외를 던지도록 바꿔도 메시지 실행이 `final`로 끝난다 (B7 검사)
- [ ] T050 [US4] [QA] B7 교차 검증(real): 브라우저 승인 후 connected, 컨테이너 재시작 후 유지, US1 개선 질문에서 metric 근거가 실제 수치로 나오고 Amplitude에서 직접 확인한 값과 같음(SC-003 표본), MCP 차단 시 나머지 소스로 답하고 빠진 근거 명시(US1-4), `check_b7.py` 실행 (B7 QA)

### F5 — 설정 화면

- [x] T051 [P] [US4] [FE] `frontend/src/api.ts`: Settings 타입, `getSettings()`, `putRepository()`, `syncRepository()`, `putTaxonomy()`, `connectAmplitude()` (F5)
- [x] T052 [US4] [FE] `frontend/src/SettingsPage.tsx`(`#/settings`): (F5)
  - 저장소: URL·브랜치 등록과 동기화 버튼을 둔다. `headCommit`·`codeMapStatus`·`screenCount`·`syncedAt`·`lastError`를 표시한다.
  - 택사노미: `.json` 파일을 고르면 내용을 그대로 PUT한다. 성공하면 `eventCount`·`uploadedAt`를, 실패하면 `message`를 그대로 보여준다.
  - Amplitude: 연결 버튼은 `window.open(authorizationUrl)` 뒤 settings를 3초 간격, 최대 2분 다시 읽는다.
  - 상태 표시: 모델·`agentMode`·예산(`spentUsd`/`limitUsd`)을 보여준다.
  - 접근 토큰: 입력값을 `localStorage`에 저장한다.
- [x] T053 [US4] [FE] `frontend/checks/check-f5.ts`: `contracts/02-objects.md` Settings 예시와 `contracts/07` 저장소·택사노미 응답 예시, `contracts/08` connect 예시가 타입을 통과하고, `repository: null`·`taxonomy: null` 변형도 통과 (F5 검사)
- [ ] T054 [US4] [QA] F5↔B4·B7 교차 검증: quickstart 시나리오 7~10을 fake와 real 각각, 잘못된 택사노미의 위치 메시지 표시와 기존 값 유지(US4-4), 토큰 미설정 저장소의 `lastError` 표시(엣지 케이스), `check-f5.ts` 실행 (F5 QA)

**Checkpoint**: 네 스토리 모두 독립 동작.

---

## Phase 7: Polish & 배포 (B8, F6)

- [x] T055 [BE] `deploy/`: `../kbap-amplitude/deploy/`의 compose·배포 스크립트·env 예시를 복사해 이름을 바꾼다(`docker-compose.kbap-pm-agent.yml`: 이미지 `simhani1/kbap-pm-agent:latest`, `monitor-net`, `127.0.0.1:8001:8000`. `deploy.kbap-pm-agent.sh`: pull → up → `/api/health` 확인). 멀티아키 빌드·푸시 명령. 홈서버 MySQL 전용 DB·계정 SQL. research.md R4 확인 결과 기록 (B8)
- [x] T056 [BE] `backend/checks/check_b8.py`: `PUBLIC_BASE_URL`의 `/api/health`가 200, 운영 출처 preflight 통과(ADR-18). 기대 출처는 상수로 박지 않고 `git remote get-url origin`의 소유자로 `https://<owner>.github.io`를 만든다(QA-3·QA-4 재발 대응: 출처의 단일 출처는 git remote이고 env·ADR 값은 이 검사로 검증되는 사본이다), SSE 응답이 100초 이상 끊기지 않음(fake 실행에 지연을 넣어 확인) (B8 검사)
- [ ] T057 [QA] B8 교차 검증: 운영 도메인 health, cloudflared 경유 SSE ping 유지, 운영 `ACCESS_TOKEN` 사용 여부를 사용자에게 확인(R3) (B8 QA)
- [x] T058 [P] [FE] `.github/workflows/pages.yml`: `frontend/` 빌드(`VITE_API_BASE_URL`은 레포 Variables) 후 GitHub Pages 배포 (F6)
- [x] T059 [FE] `frontend/checks/check-f6.ts`: `frontend/dist/index.html`의 자산 경로가 `/kbap-pm-agent/`로 시작하고, 번들에 `VITE_API_BASE_URL` 값이 들어 있다 (F6 검사)
- [ ] T060 [QA] F6↔B8 교차 검증: GitHub Pages URL에서 운영 백엔드로 health·대화·SSE·채택 왕복, `check-f6.ts` 실행 (F6 QA)
- [ ] T061 [QA] 최종: quickstart.md 전 시나리오(fake·real), 계약 동기화 `cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md` 출력 없음, 모든 `check_*`·`check-*` 일괄 실행

---

## Phase 8: LLM SDK 전환 (B9, ADR-20)

**Purpose**: LangChain을 걷어내고 공급자별 공식 SDK 런타임 두 개(Anthropic tool runner, OpenAI Agents SDK)로 바꾼다. API 계약 v1.1·SSE 이벤트·DB·프론트는 바뀌지 않는다. 모델 문자열 접두사(`anthropic:`/`openai:`)가 런타임을 고른다.

**완료 기준**: fake 모드 동작이 전환 전과 같다. 두 런타임이 가짜 HTTP 전송으로 계약 SSE 순서를 만든다. `backend/` 어디에도 `langchain` import가 없다. 계약 동기화 diff가 비어 있다.

- [x] T062 [BE] `backend/pyproject.toml`·`backend/uv.lock`: `langchain`, `langchain-anthropic`, `langchain-openai`, `langchain-mcp-adapters`를 제거하고 `anthropic[mcp]`, `openai-agents`를 추가한다. `mcp`는 1.x를 유지한다(`OAuthClientProvider`가 httpx.Auth여야 OpenAI Agents `params["auth"]`와 맞는다, research.md R8). `uv lock`·`uv sync` 후 Docker 이미지 빌드 확인 (B9)
- [x] T063 [BE] `backend/app/code_tools.py`: 코드·택사노미 도구(`find_event_calls`, `search_code`, `get_screen_summary`, `read_code`, `search_taxonomy`, `get_event_definition`)를 프레임워크 없는 Python 함수로 정리한다. 타입 힌트와 docstring(Args 절)이 도구 스키마의 원천이다. LangChain 데코레이터를 제거하고, 상한(30건·200줄·`CODE_GLOB`)은 함수 안에 둔다 (B9)
- [x] T064 [BE] `backend/app/agent.py`: seam 재구성. (B9)
  - 런타임 선택: `AGENT_MODEL`·`CODE_SUMMARY_MODEL`을 `provider:model`로 파싱한다. `{"anthropic": agent_anthropic, "openai": agent_openai}` dict로 고르고, 다른 접두사는 기동 시 실패시킨다.
  - 공통 도구 래퍼: `tool_call` 이벤트 → 실행 → `tool_result` 이벤트 순서다. 예외가 나면 `failed`와 오류 문장을 모델에 돌려주고 실행을 계속한다(ADR-16, FR-010). `source`는 `code`/`taxonomy`/`amplitude`.
  - 상한: `asyncio.timeout(AGENT_TIMEOUT_SECONDS)`와 도구 호출 수 상한이다. 도달하면 기존 `partial_content()`로 부분 `final`을 낸다.
  - 사용량·검증: 반복마다 사용량을 `budget.record`에 넘기고, `AgentAnswer` 사후 검증 실패는 `error` `UPSTREAM_ERROR`다(재시도 없음 `ponytail:` 주석 유지).
  - fake 분기: 런타임 선택보다 먼저 타며 변경하지 않는다.
  - `summarize()`: 같은 접두사 규칙으로 런타임별 단발 호출을 한다.
- [x] T065 [BE] `backend/app/agent_anthropic.py`: 공식 `anthropic` SDK 런타임. (B9)
  - 루프: `AsyncAnthropic().beta.messages.tool_runner(model, max_tokens, system, messages, tools=[@beta_async_tool로 감싼 T063 함수 + Amplitude MCP 도구], output_format=AgentAnswer, thinking={"type": "adaptive"}, cache_control={"type": "ephemeral"}, betas=["server-side-fallback-2026-07-01"], fallbacks="default", max_iterations=...)`. `tool_choice`는 넘기지 않는다.
  - 반복 처리: 각 `BetaMessage`에서 `stop_reason == "refusal"`이면 `error` `UPSTREAM_ERROR`로 끝낸다. usage(`input_tokens`, `output_tokens`, 캐시 토큰)를 기록하는데, 캐시 토큰은 입력 단가로 보수적으로 계산하고 `ponytail:` 주석을 단다.
  - 최종 응답은 `parsed_output`이다. 클라이언트 생성은 `_client()` 함수 하나로 두어 검사 스크립트가 교체할 수 있게 한다.
  - `summarize()`는 `client.messages.create(model=CODE_SUMMARY_MODEL 이름, ...)`다.
- [x] T066 [P] [BE] `backend/app/agent_openai.py`: `openai-agents` 런타임. (B9)
  - 구성: `Agent(name, instructions, model=<접두사 뗀 이름>, tools=[함수 도구로 감싼 T063 함수], mcp_servers=[amplitude 서버 객체], output_type=AgentAnswer)`.
  - 스트리밍: `Runner.run_streamed(..., max_turns=...)`의 `RunItemStreamEvent` `tool_called`/`tool_output`을 공통 래퍼 이벤트로 연결한다. 데코레이터 이름, `max_turns`, 사용량 접근 경로는 설치본에서 확인한다(research.md R8 미확인 항목).
  - 클라이언트: OpenAI 클라이언트 생성은 `_client()` 하나로 두어 검사 스크립트가 교체할 수 있게 한다.
  - `summarize()`는 도구 없는 단발 실행이다. 이 파일이 T065와 독립이라 병렬 가능하다.
- [x] T067 [BE] `backend/app/amplitude.py`: `MultiServerMCPClient`를 제거한다. (B9)
  - 공용 provider: `oauth_provider()`(기존 `OAuthClientProvider` + `app_settings` 토큰 저장소)를 두 런타임이 공유한다.
  - Anthropic용 `anthropic_tools()`: `streamablehttp_client(url, auth=provider)` 세션과 `async_mcp_tool`로 도구 목록을 만든다. 세션 수명은 실행 1회이고, 설치본 헬퍼 이름은 확인한다.
  - OpenAI용 `openai_server()`: `MCPServerStreamableHttp(name="amplitude", params={"url": AMPLITUDE_MCP_URL, "auth": provider}, cache_tools_list=True)`.
  - 미연결이면 둘 다 빈 값이고, fake 분기는 그대로 둔다. MCP 호출 예외는 공통 래퍼에서 `tool_result` `failed`가 되게 한다(OpenAI 쪽은 `failure_error_function` 기본값으로 모델에 실패를 보이되, 래퍼 이벤트도 `failed`로 낸다).
- [ ] T068 [P] [BE] `.env.example`, `deploy/kbap-pm-agent.env.example`: `AGENT_MODEL=anthropic:claude-sonnet-5-5`, `CODE_SUMMARY_MODEL=anthropic:claude-haiku-5-5`를 둔다. OpenAI로 바꾸는 예시(`openai:gpt-6-luna`)는 주석으로, `OPENAI_API_KEY`는 openai 접두사일 때만 필요하다고 적는다. LangChain 전용 변수가 있으면 제거한다 (B9)
- [x] T069 [BE] `backend/checks/check_b6.py` 갱신: 두 런타임 각각에 `_client()`를 교체해 스크립트 응답을 주입한다(Anthropic은 `httpx2.MockTransport`, OpenAI는 `httpx.MockTransport`, research.md R8). 스크립트는 1차 도구 호출(`find_event_calls`), 2차 최종 `AgentAnswer` JSON이다. assert 항목은 다음과 같다. (B9 검사)
  - 이벤트·사용량: SSE 이벤트 순서(`tool_call` → `tool_result` → `final`)가 계약 05와 같고, `final`이 Message 모델을 통과하며, `llm_usage` 행이 생긴다.
  - 실패 경로: 도구가 예외를 던져도 `final`로 끝나고 해당 `tool_result`가 `failed`다. 신규 단계 `location: null` 응답은 `error` `UPSTREAM_ERROR`, (Anthropic) `stop_reason: "refusal"` 응답도 `error` `UPSTREAM_ERROR`다.
  - 상한·접두사: `AGENT_TIMEOUT_SECONDS=1` + 지연 전송이면 부분 `final`이다. 알 수 없는 접두사(`foo:bar`)는 기동 실패다.
  - 마지막으로 `rg -n "langchain" backend/app backend/pyproject.toml`이 비어 있다.
- [x] T070 [BE] `backend/checks/check_b7.py` 갱신: 연결 상태에서 `anthropic_tools()`가 `source: "amplitude"`로 묶이는 도구를 내고, `openai_server()`가 `params["auth"]`에 같은 provider를 넣는지 확인한다(MCP 서버는 가짜 전송). MCP 호출 예외가 두 런타임 모두에서 `tool_result` `failed` 후 `final`로 이어진다. fake 모드 connect·settings 검사는 기존대로 둔다 (B9 검사)
- [x] T071 [QA] B9 교차 검증(fake + 가짜 전송): (B9 QA)
  - 기존 검사: `check_b5.py`·`check_b6.py`·`check_b7.py`를 실행한다.
  - SSE 비교: fake 모드 메시지 전송 SSE 원문을 전환 전 기록(T022·T042 로그)과 비교해 이벤트 이름·data 키 구조가 같은지 본다.
  - 계약·LangChain 잔존: `cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md` 출력이 없어야 하고, `rg -n langchain backend`에 결과가 없어야 한다.
  - 프론트: 변경 없이 F3·F4 화면이 동작해야 한다.
- [x] T072 [QA] 헌법 정합 확인: 헌법 "기술 제약"의 백엔드 스택 문구가 ADR-20과 일치하는지 본다(team-lead 개정 후). 일치하지 않으면 CTO에 보고한다 (B9 QA)
- [ ] T073 [QA] 실제 키 확보 시: `AGENT_MODEL`을 `anthropic:`과 `openai:`로 각각 두고 T042 시나리오(US1·US2 질문, SC-004 시간 측정)를 다시 실행한다. Anthropic 구조화 출력이 `AgentAnswer` 스키마 제약을 거부하는지 확인한다(research.md R8). 키가 없으면 "미검증"으로 리포트한다 (B9 QA)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)**: 2는 1 완료 후. 2가 끝나야 모든 스토리 시작.
- **US1 (3)**: 2 이후. 외부 키 없이 완료된다.
- **US2 (4)**: 3의 B3(T019~T022) 이후. real 분기가 fake와 같은 SSE 경로를 쓴다.
- **US3 (5)**: 3의 F3(T023~T026) 이후. US2와 병렬 가능하다(FE만 바뀜).
- **US4 (6)**: B7은 4의 B6(T039) 이후(도구 결합 지점). F5는 4의 B4(T032) 이후에 실제 연결을 하고, 그 전에는 계약 예시로 mock 개발한다.
- **Polish (7)**: 6 이후.
- **LLM SDK 전환 (8)**: B6·B7 이후. Phase 7과 독립(배포 이미지는 T062 이후 다시 빌드한다). 역할 순서는 T062 → T063 → (T064 → T065) ∥ T066 → T067 → T068 → T069·T070 → T071~T073.

### 모듈 의존 (task-split과 동일)

`B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8`, `B7 → B9`, `F1 → F3 → F4 → F2 → F5 → F6`

### 통합 지점 (mock → 실제 전환)

- F1 ↔ B1: T013
- F3·F4 ↔ B2·B3: T026, T030. 이후 FE는 fake 모드로 계속 개발한다.
- F2 ↔ B2: T045
- F5 ↔ B4·B7: T054
- 실제 모드 전체: T042, T050
- 운영: T060

## Parallel Opportunities

- Setup: T002·T003·T004 동시.
- Foundational: BE(T005~T009)와 FE(T010~T012)를 두 사람이 동시에 진행한다. T013만 합류점이다.
- US1: T014(BE 스키마)와 T023(FE 타입)을 동시에 시작한다. 이후 BE는 T015~T022, FE는 계약 예시 mock으로 T024~T029를 진행한다.
- US2 진행 중 FE는 US3(T043~T045)와 F5 mock(T051~T053)을 진행한다.
- US2 안에서 T035(budget.py)는 T031~T034와 병렬이다.

### Parallel Example: User Story 1

```bash
# backend-dev
Task: "T014 [US1] [BE] backend/app/schemas.py 계약 객체 Pydantic 모델"
# frontend-dev (동시에)
Task: "T023 [US1] [FE] frontend/src/api.ts 계약 타입 + SSE 파서"
```

## Implementation Strategy

### MVP First (User Story 1, fake 모드)

1. Phase 1~2 완료 → T013 헬스체크 왕복.
2. Phase 3 완료 → T030까지 통과하면 외부 키 없이 질문→진행→제안→채택이 시연된다.
3. **STOP and VALIDATE**: quickstart 시나리오 1~5.

### Incremental Delivery

1. US1(fake) → US2(실제 코드·택사노미, US1 실제 모드 포함) → US3(목록) → US4(설정 UI·Amplitude) → 배포.
2. 각 모듈은 검사 스크립트 + QA 통과 후 커밋한다.

### 역할별 흐름

- backend-dev: B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8
- frontend-dev: F1 → F3 → F4 → F2 → F5 → F6. B3 이후 fake 모드 백엔드로 실제 연동.
- qa-integrator: 모듈 QA 태스크가 열리는 즉시 검증한다. 결함은 `파일:라인`, 계약 인용, 실제값으로 담당자에게 보낸다. 경계면 결함은 양쪽에, 계약 자체 결함은 CTO에게 보낸다.

## Notes

- 계약 변경이 필요하면 태스크를 멈추고 CTO에 요청한다. CTO는 원본을 고친 뒤 `contracts/`를 다시 자르고 T061의 diff 명령으로 확인한다.
- 위임 항목(UI 라이브러리, 캐시 매체, DB 드라이버, 모델 기본값, 로깅)은 태스크 안에서 구현자가 정하고 `ponytail:` 주석이나 커밋 메시지에 남긴다.
