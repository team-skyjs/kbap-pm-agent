# 01 CTO — 작업 분할

작성일: 2026-10-15 (갱신: 계약 v1.1, ADR-15·16 반영) · 기준 문서: `01_cto_tech-decisions.md`, `01_cto_api-contract.md`

규칙:
- 모듈 하나 = QA가 따로 검증할 수 있는 단위. 모듈을 끝내면 QA에 넘기고 다음 모듈로 간다.
- 계약과 다르게 구현해야 할 이유가 생기면 구현하지 말고 CTO에 변경 요청을 보낸다.
- 백엔드는 B3까지 `AGENT_MODE=fake`만으로 완료할 수 있어야 한다. LLM 비용은 B5부터 쓴다.

## 레포 구조

```
kbap-pm-agent/
  docker-compose.yml          # 로컬: backend + mysql (ADR-11)
  .github/workflows/pages.yml # frontend → GitHub Pages
  deploy/                     # 홈서버용 compose·env 예시·배포 스크립트 (kbap-amplitude/deploy 복사 후 이름 변경)
  backend/
    pyproject.toml, uv.lock, Dockerfile, schema.sql
    app/                      # FastAPI 앱. 내부 구조는 구현자 위임
  frontend/
    package.json, vite.config.ts (base: '/kbap-pm-agent/')
    src/api.ts                # 계약서 타입과 호출 함수는 이 파일 하나에
```

## backend

| 순서 | 모듈 | 포함 엔드포인트 | 완료 기준 | 의존 |
|---|---|---|---|---|
| B1 | 뼈대: 서버 뜬다 + 헬스체크 | `GET /api/health` | `docker compose up`으로 backend+mysql이 뜨고, `curl localhost:8000/api/health`가 `{"status":"ok","db":"ok","version":"0.1.0"}`. 기동 시 `schema.sql` 6개 테이블 생성. 없는 경로는 공통 에러 형식 404 `NOT_FOUND`. `CORS_ORIGINS`의 `http://localhost:5173`에서 preflight 통과. `ACCESS_TOKEN` 설정 시 health는 통과, 다른 경로는 401 `UNAUTHORIZED` | 없음 |
| B2 | 대화·제안 저장 | `GET /api/conversations`, `POST /api/conversations`, `GET /api/conversations/{id}`, `PATCH /api/proposals/{id}` | 계약서 예시와 같은 shape(camelCase, null 규칙, `items` 감싸기). 시험용 제안을 DB에 넣고 PATCH로 `adopted`→`pending` 전환 시 `decidedAt`이 채워졌다가 `null`이 됨. FastAPI 기본 422 대신 `VALIDATION_ERROR` 400 | B1 |
| B3 | 메시지 전송 SSE (fake) | `POST /api/conversations/{id}/messages` | `AGENT_MODE=fake`에서 `message_created` → `tool_call`/`tool_result` 2쌍 → `final` 순서로 스트림. 제안 2개(improvement·funnel_design)가 계약 규칙(new 단계 `location` 필수 등)을 지켜 저장되고 `GET` 상세에 그대로 나옴. 15초 ping. 실행 중 재전송 시 409 `RUN_IN_PROGRESS`. 첫 메시지로 제목 채움. 클라이언트 연결 끊기면 메시지 `failed` 마감 | B2 |
| B4 | 설정: 저장소·택사노미 | `GET /api/settings`, `PUT /api/settings/repository`, `POST /api/settings/repository/sync`, `PUT /api/settings/taxonomy` | `file://` 로컬 저장소와 실제 `kbap-fe`(GITHUB_TOKEN)로 클론 성공. `trackedEventCount`가 `track\(EVENTS\.` 호출 수와 일치. 택사노미 업로드 후 `eventCount` 반영. 클론 실패 응답·로그에 토큰 없음. `codeMapStatus`는 이 모듈에서 `"none"` 유지 가능. 실패 시 `repository.lastError` 기록. `AGENT_MODE=fake`면 클론 없이 계약서 예시 값으로 응답(ADR-15) | B1 |
| B5 | 코드 도구 + 요약 캐시 + 예산 | (계약 변경 없음. settings의 `codeMapStatus`, `budget` 실값) | 에이전트용 도구 4개(`find_event_calls`, `search_code`, `get_screen_summary`, `read_code`)가 단독 호출로 동작(`read_code` 200줄 상한, `search_code` 30건 상한). 화면 요약이 blob SHA 키로 캐시되어 같은 커밋 재동기화 시 LLM 호출 0회, 파일 1개 변경 시 1회. 모든 LLM 호출이 `llm_usage`에 기록되고 `budget.spentUsd`에 반영. `LLM_BUDGET_USD`를 0.01로 두면 메시지 전송이 403 `BUDGET_EXCEEDED` | B4 |
| B6 | 실제 에이전트 루프 | `POST .../messages` (`AGENT_MODE=real`) | `create_agent` + 코드·택사노미 도구 + `response_format`. 계약서 SSE 순서 동일. 세그먼트 B 질문("장바구니 개선 효과 측정 설계해줘")에 `funnel_design` 제안이 나오고 신규 이벤트마다 실제 존재하는 파일·함수가 들어감. 도구 호출 `AGENT_MAX_TOOL_CALLS`·실행 시간 `AGENT_TIMEOUT_SECONDS` 상한에서 부분 `final`(ADR-16). 도구 하나가 실패해도 실행 계속. `AGENT_MODEL`만 바꿔 `openai:` 모델로도 한 번 실행 확인 | B3, B5 |
| B7 | Amplitude MCP 연결 | `POST /api/integrations/amplitude/connect`, `GET /api/integrations/amplitude/callback` | 브라우저 승인 후 `amplitude.status: "connected"`, 컨테이너 재시작 후에도 유지(토큰 DB 저장). 에이전트 도구 목록에 Amplitude MCP 도구가 `source: "amplitude"`로 붙음. 세그먼트 A 질문에 metric 근거가 실제 수치로 나옴. `AGENT_MODE=fake`면 connect가 예시 URL을 돌려주고 즉시 connected(ADR-15). **첫날 실연결부터 확인**하고 막히면 즉시 CTO 보고(ADR-3 대체 경로) | B6 |
| B8 | 운영 배포 | 전체 | 멀티아키 이미지 푸시, 홈서버 `deploy/` compose로 기동, cloudflared 경유 `https://<운영 도메인>/api/health` 200. 홈서버 MySQL에 전용 DB·계정 | B7 |
| B9 | LLM SDK 전환 (ADR-20) | (계약 변경 없음) `POST .../messages` 실제 모드 내부 | LangChain 제거, `anthropic` tool runner·`openai-agents` 두 런타임을 모델 접두사로 선택, Amplitude MCP는 MCP SDK 직접 연결(OAuth provider 공유). fake 동작 불변, 가짜 HTTP 전송으로 두 런타임 SSE 순서·실패·상한 검증(check_b6·check_b7), `rg langchain` 0, 계약 diff 0. 태스크 T062~T073 | B7 |

## frontend

| 순서 | 모듈 | 호출 엔드포인트 | 완료 기준 | 의존 |
|---|---|---|---|---|
| F1 | 뼈대: 화면 뜬다 + 헬스체크 | `GET /api/health` | `npm run dev`로 화면이 뜨고 상단에 health 결과(ok / degraded / 연결 실패)가 보임. `src/api.ts`에 공통 fetch(Base URL, Bearer 토큰, 공통 에러 파싱→`code`). `npm run build` 산출물이 `/kbap-pm-agent/` 하위 경로에서 열림(`vite preview --base`로 확인). HashRouter | 없음 |
| F2 | 대화 목록·다시 열기 (US3) | `GET /api/conversations` | 왼쪽 목록(`updatedAt` 내림차순, 제목 null이면 "새 대화", 시각·제안 수·채택 수). 선택 시 `#/conversations/:id`로 이동. 메시지 final·제안 PATCH 후 목록 재조회. 순서상 F4 다음(2026-10-15 범위 조정: 생성·상세는 F3로 이동) | F3 |
| F3 | 채팅: 생성·상세·스트리밍 (US1) | `POST /api/conversations`, `GET /api/conversations/{id}`, `POST /api/conversations/{id}/messages` | 새 대화 버튼→생성 후 이동, 메시지 렌더(마크다운), 도구 호출 접힌 목록. `fetch` + `ReadableStream`으로 SSE 파싱(`: ping` 무시). `tool_call`→`tool_result`로 진행 표시 갱신, `final`로 메시지 교체, `error`는 메시지 하단에 code별 문구. 스트림이 끊기면 상세 재조회. 409·403은 입력창 아래 안내. 실행 중 입력 비활성. 계약서 예시 JSON mock으로 먼저 구현 | F1 |
| F4 | 제안 카드 + 채택/보류 | `PATCH /api/proposals/{id}` | 카드 네 영역이 근거→제안→실행단계→측정방법 순서. 근거는 kind별 렌더(code는 `파일:줄`·함수 + snippet). funnel은 표(순서·이벤트·기존/신규·위치·속성), 신규 단계 강조. 채택/보류 버튼과 메모 입력, 응답 Proposal로 카드 갱신, 근거 code는 함수명도 표시 | F3 |
| F5 | 설정 화면 | `GET /api/settings`, `PUT /api/settings/repository`, `POST /api/settings/repository/sync`, `PUT /api/settings/taxonomy`, `POST /api/integrations/amplitude/connect` | 저장소 URL·브랜치 등록과 동기화 버튼, `codeMapStatus` 표시. 택사노미 `.json` 파일 선택→본문 그대로 PUT. Amplitude 연결 버튼→새 탭 열고 3초 간격 최대 2분 settings 재조회. 모델·`agentMode`·예산(사용/한도) 표시. 접근 토큰 입력→`localStorage` | F1 |
| F6 | GitHub Pages 배포 | 전체 | `.github/workflows/pages.yml`이 `frontend/` 빌드·배포, `VITE_API_BASE_URL`은 레포 Variables. 운영 URL에서 health 왕복 성공 | F5, B8 |

프론트 진행 순서: F1 → F3 → F4 → F2 → F5 → F6 (스토리 우선순위 US1 → US3. `specs/001-pm-agent-prototype/tasks.md`가 실행 기준)

## 통합 지점

- **F1 ↔ B1:** 첫 경계면. 로컬 `localhost:5173` → `localhost:8000` health 왕복, CORS preflight, 401 처리. QA가 가장 먼저 검증한다.
- **F2 ↔ B2:** F2 완료 시 목록 실제 연동. shape 대조(null 규칙, `items` 감싸기, camelCase, `adoptedCount`).
- **F3·F4 ↔ B3:** B3(fake) 완료 즉시 실제 전환. 이후 FE는 LLM 비용 없이 fake 모드로 개발을 계속한다. SSE 이벤트 순서·종료 조건, 제안 4필드·funnel 규칙 검증.
- **F5 ↔ B4:** 저장소·택사노미 실제 전환. Amplitude 연결 버튼은 B7 완료 시 실제 전환(그전엔 `status: "disconnected"` 표시만).
- **전체 ↔ B6·B7:** `AGENT_MODE=real`로 바꿔 핵심 흐름 두 가지(세그먼트 A 개선 제안, 세그먼트 B 측정 설계)를 끝까지 한 번씩 돌린다. FE 변경이 없어야 정상이다.
- **F6 ↔ B8:** 운영 도메인에서 GitHub Pages → 홈서버 왕복.

## 계약 커버리지 확인

계약서 12개 엔드포인트가 모두 위 모듈에 있다: health(B1/F1), 대화 3개(B2/F3·F2), 메시지(B3·B6/F3), 제안 PATCH(B2/F4), 설정 4개(B4/F5), Amplitude 2개(B7/F5, 콜백은 FE 호출 없음).
