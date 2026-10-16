---
description: "Amplitude 서버 고정 인증 구현 태스크"
---

# Tasks: Amplitude 서버 고정 인증

**Input**: `specs/006-amplitude-rest/`의 plan.md, spec.md, research.md, data-model.md, contracts/(계약 v1.5, amplitude-tools.md), quickstart.md

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 모듈마다 검사 하나와 QA 하나를 둔다.
- A1 백엔드 REST·사전 점검·상태: `backend/checks/check_b12.py`(신규). `check_b7.py`는 폐기한다.
- A2 프론트 설정·거절 안내: frontend-dev의 `check-f*`와 Playwright 시나리오.
- 실제 키 확인은 사람이 하는 수동 태스크다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명 (모듈)`

- **역할**: `[BE]` backend-dev(주도), `[FE]` frontend-dev, `[QA]` qa-integrator
- **스토리**: `[US1]` 재승인 없이 지표, `[US2]` 실행 전 거절, `[US3]` 설정 화면, `[US4]` 상태 기록

## 공통 규칙

- 키 값은 env만 쓴다. 응답·로그·`tool_calls.input`·예외 메시지에 넣지 않는다(헌법 원칙 III).
- Amplitude 호출은 `backend/app/amplitude.py` 한 파일에서, 허용 경로의 GET만 한다(ADR-34).
- 새 의존성 금지, 모델명 코드 금지, 운영 정보 비노출, 코드 주석 규칙을 지킨다.
- 커밋은 경로 지정, `feat/amplitude-rest`에 한다.

---

## Phase 1: Setup

- [x] T001 [BE] 설정 파일 정리(ADR-34). (A1)
  - env 예시: `.env.example`·`deploy/kbap-pm-agent.env.example`에서 `AMPLITUDE_MCP_URL`·`AMPLITUDE_TOOLS`를 지우고 `AMPLITUDE_API_KEY=`·`AMPLITUDE_SECRET_KEY=`·`AMPLITUDE_REST_BASE=`(주석: 기본 `https://amplitude.com`, EU 주소)를 둔다.
  - 배포 워크플로우: `.github/workflows/deploy-backend.yml`의 env 생성 단계도 같게 한다(키 둘은 Secrets, 주소는 Variables).
  - 문서: `deploy/README.md`에 "운영 Secrets 두 개 등록 필요(team-lead)"를 적는다. 값은 쓰지 않는다.

---

## Phase 2: Foundational — REST 기반, OAuth 제거, 저장 구조 (A1)

- [x] T002 [BE] `backend/app/amplitude.py` 기반을 다시 쓴다. (A1)
  - 지우는 것: OAuth provider·DB 토큰 저장소·connect/callback 라우트·MCP 도구 목록·허용 목록 불일치 처리.
  - 키·주소: env 키 둘과 주소를 읽는다. 둘 중 하나라도 비면 키 없음이다.
  - 호출 함수 `_get(path, params)`: 허용 경로 6개(amplitude-tools.md 4절)의 GET만 허용하고 나머지는 호출 전에 예외다. `httpx.BasicAuth`, `(path, params)` 키의 15분 프로세스 캐시(`ponytail:` 단일 워커 전제)를 쓴다.
  - 오류 분류: 400·401/403·429·연결/5xx를 나눈다. 예외 메시지에 키를 넣지 않는다.
- [x] T003 [BE] `backend/app/main.py`에서 amplitude 라우터 등록과 `OPEN_PATHS`의 콜백을 지운다. `backend/app/settings.py`의 `amplitude_state()`는 `{"status": "configured" | "missing"}`(계약 v1.5)을 돌려준다 (A1)
- [x] T004 [BE] `backend/schema.sql`에 `messages.amplitude_status ENUM('used','unavailable','skipped') NULL`을 둔다. `backend/app/db.py` `init()`에는 두 가지를 넣는다(research R5, ADR-29 패턴). (A1)
  - 컬럼이 없을 때만 `ALTER TABLE messages ADD COLUMN …`.
  - `DELETE FROM app_settings WHERE k IN ('amplitude','amplitude_oauth')`(멱등).

---

## Phase 3: User Story 1 — 재승인 없이 지표가 붙은 답 (P1) (A1)

- [x] T005 [US1] [BE] `amplitude_query`(amplitude-tools.md 1절)를 만든다. (A1)
  - 인자: Pydantic 모델(`kind`, `events[{event_type, filters[]}]`, `start`·`end`, `metric`·`formula`, `interval`, `group_by`, `n`, `conversion_window_seconds`)이다. 종류별 이벤트 개수·90일 상한·세그멘테이션 `n` any|active·퍼널 `n` new|active를 검사하고, 맞지 않는 인자는 `인자 오류: …`다. `ce:` 접두어는 그대로 통과시킨다.
  - 호출: REST 세 경로 매핑(날짜는 `YYYYMMDD`로 변환)이다.
  - 결과: 압축표 세 종류다. `kbap-amplitude/amp.py`의 `series_table`·`funnel_table`·`retention_table`·`_summary`·`_labels`를 차트 dict 없이 옮겨 다듬는다. 31행 상한, 표본 30 미만 경고를 두고 끝에 `clip()`.
- [x] T006 [US1] [BE] `amplitude_context`(amplitude-tools.md 2절)를 만든다. (A1)
  - 목록: `event_type`이 없으면 Taxonomy 이벤트 목록과 `app_settings.taxonomy`를 이름으로 병합한다. 설명은 택사노미 우선이고 출처를 표시하며, 커스텀은 `ce:`를 붙인다.
  - 속성: `event_type`이 있으면 이벤트 속성과 사용자 속성 이름이다.
  - 캐시는 15분이고 `clip()`을 적용한다.
- [x] T007 [US1] [BE] 에이전트를 연결한다. (A1)
  - 도구 목록(`backend/app/agent.py`): 키가 있고 건너뛰지 않을 때 두 도구를 기존 `wrap(…, source="amplitude")`로 넣는다.
  - 런타임: `agent_anthropic.py`의 MCP 세션·`_mcp_call`·불일치 분기와, `agent_openai.py`의 `MCPServerStreamableHttp`·MCP 이벤트 처리를 지운다.
  - `SYSTEM_PROMPT` 규칙 7: 도구 이름만 바꾼다.
  - `SYSTEM_PROMPT` 규칙 8: research R6 문장으로 교체한다.
  - 상태 문구: `Amplitude 있음` | `없음(사용자가 건너뜀)` | `없음(키 없음)`.
- [x] T008 [US1] [BE] 의존성 정리: `rg -n "from mcp|import mcp|MCPServer|mcp_tool" backend/app`가 비면 `backend/pyproject.toml`의 `anthropic[mcp]` extra와 `mcp`를 정리하고 `uv.lock`을 갱신한다. openai-agents는 유지한다. 새 의존성은 넣지 않는다 (A1)

---

## Phase 4: User Story 2 — 조회가 안 되면 실행 전에 안다 (P1) (A1, A2)

- [x] T009 [US2] [BE] 사전 점검과 상태 기록을 붙인다(ADR-36). (A1)
  - 점검 함수: `amplitude.preflight()`는 키를 확인한 뒤 `GET /api/2/taxonomy/event` 1회(캐시 공유)이고, 실패 이유 넷을 구분한다.
  - 요청 필드: `backend/app/conversations.py` 메시지 POST에 `skipAmplitude`(bool, 기본 false, 타입 엄격)를 받는다.
  - 거절: `budget.check()` 다음, 실제 모드이고 건너뛰지 않을 때 점검한다. 실패하면 사용자 메시지 저장 없이 503 `AMPLITUDE_UNAVAILABLE`(계약 v1.5 문구)이다.
  - 상태 기록: `skipped`/`used`를 run에 넘겨 assistant 메시지에 기록한다. 실행 중 Amplitude 401·403이면 `unavailable`이고, 시연 모드는 NULL이다.
- [x] T010 [US2] [BE] `backend/checks/check_b12.py`(신규)를 만들고 `backend/checks/check_b7.py`를 삭제한다. `httpx.MockTransport`로 Amplitude를 흉내 낸다. assert 항목은 다음과 같다. (A1 검사)
  - 도구:
    - 세 종류 결과 표의 머리 행과 요약 줄이 맞다.
    - 인자 오류는 Amplitude 요청 0회다. 대상은 91일, 세그멘테이션 `n: "new"`, 퍼널 이벤트 1개, 퍼널에 `metric`이다.
    - `ce:` 이벤트는 요청 JSON에 그대로 들어간다.
  - 호출 경계: 허용 밖 경로·POST가 예외이고, 같은 조회 두 번째는 요청 0회(캐시)다.
  - 맥락: 출처 세 종류와 택사노미 설명이 우선이다.
  - 사전 점검: 키 없음·401·429·연결 실패가 각각 계약 문구의 503이고, `llm_usage`·메시지 행 0이다.
  - 실행 상태:
    - `skipAmplitude`이면 `skipped`이고 시스템 프롬프트에 `없음(사용자가 건너뜀)`이 들어간다.
    - 정상은 `used`다.
    - 실행 중 401은 `unavailable`이고, 실행은 `final`로 끝난다(b7의 "Amplitude 실패에도 final" 이전).
  - 설정: `configured`/`missing`이다. 삭제된 두 경로는 404다.
  - 마이그레이션: `init()` 두 번이 멱등이고 OAuth 설정 행이 삭제된다.
  - 비밀: 로그 캡처와 응답 본문에 키 문자열이 없다.
- [x] T011 [US2] [FE] `frontend/src/Chat.tsx`: 메시지 전송이 `ApiError` 코드 `AMPLITUDE_UNAVAILABLE`이면 응답 `message`를 안내로 보이고 "Amplitude 없이 진행" 버튼을 둔다. 버튼은 같은 내용을 `skipAmplitude: true`로 다시 보낸다. 입력값은 보존하고 키보드로 조작할 수 있게 한다 (A2)

---

## Phase 5: User Story 3 — 설정 화면은 서버 키 상태만 (P2) (A2)

- [x] T012 [US3] [FE] API·설정 화면을 바꾼다. (A2)
  - `frontend/src/api.ts`: `Settings.amplitude`를 `{status: 'configured' | 'missing'}`로 바꾸고, `connectAmplitude`와 관련 타입·폴링을 지우며, `sendMessage`에 `skipAmplitude` 옵션을 둔다.
  - `frontend/src/SettingsPage.tsx`: 연결·다시 연결 버튼과 폴링을 지우고, "서버 키로 연결됨" / "키 없음 + 서버 환경 변수 설정 안내" 라벨만 둔다. 키 값은 보이지 않는다.
- [x] T013 [US3] [FE] 프론트 검사를 갱신한다. 번호는 frontend-dev가 정한다. (A2 검사)
  - 계약 파싱: 계약 v1.5 Settings·에러 예시 파싱 검사(기존 설정 검사 갱신).
  - Playwright: 고정 응답의 `amplitude` shape를 바꾸고 설정 시나리오를 갱신한다(두 상태 라벨, 연결 버튼 없음). 거절 안내 시나리오를 추가한다(503 → 안내 → "없이 진행" → 다시 보낸 요청 본문에 `skipAmplitude: true`, 입력값 보존).

---

## Phase 6: User Story 4 — 실행별 상태 기록 (P2)

T004·T009·T010이 구현과 검사를 맡는다. 조회 한 줄은 data-model.md에 있고, 확인은 T016이다.

---

## Phase 7: 검증

- [x] T014 [QA] A1 교차 검증: (A1 QA)
  - 실행·대조: `check_b12.py`를 순차 실행하고, curl 응답을 계약 v1.5(설정 `amplitude`, 503 에러 형식, 삭제된 두 경로 404)와 대조한다.
  - 계약: diff 0.
  - 잔재: `rg -n "mcp|oauth|AMPLITUDE_MCP" backend/app`에 결과가 없다(주석의 이력 언급 제외).
  - 비밀: 로그·`tool_calls.input`에 키가 없다.
- [x] T015 [US1] [QA] 실제 키 1회 수동 확인. 로컬 `.env`에 실제 키를 둔다. (미검증·사람·키)
  - 질문: 세그멘테이션·퍼널·리텐션·이벤트 맥락 질문 각 1회에서 도구가 성공하고, 수치 근거가 있으며, `amplitude_status='used'`다(SC-004, ADR-35 가정).
  - 응답 필드: Taxonomy API 응답 필드 이름이 구현과 맞다.
  - 설정·거절: 설정이 `configured`이고, 틀린 키면 "인증에 실패했습니다" 거절이다.
  - 키가 없으면 "미검증"으로 리포트한다.
- [x] T016 [QA] A2 + 회귀:
  - 검사: `npm run check`, `npm run check:ui` 전체, 백엔드 `check_b1`~`check_b12` 순차(b7 제외)를 실행한다.
  - 상태 조회: data-model.md 조회 SQL로 상태별 건수가 맞다.
  - 흐름: 질문 → 제안 → 채택 흐름이 유지된다(SC-005). ui-review(설정 화면, 거절 안내).

---

## 요구사항 커버리지

| 요구 | 태스크 |
|---|---|
| FR-001 env 키, 비노출 | T001, T002, T010, T014 |
| FR-002 도구 두 개 | T005, T006, T007 |
| FR-003 조회 전용 경로 | T002, T010 |
| FR-004 인자 규칙 | T005, T010 |
| FR-005 압축표 | T005, T010 |
| FR-006 15분 캐시 | T002, T006, T010 |
| FR-007 사전 점검·거절 | T009, T010 |
| FR-008 없이 진행 | T009, T011, T013 |
| FR-009 설정 화면 | T003, T012, T013 |
| FR-010 상태 기록 | T004, T009, T010, T016 |
| FR-011 MCP 제거 | T002, T003, T004, T007, T008, T014 |
| FR-012 시연 모드 | T009, T010 |
| FR-013 의존성 없음 | 공통 규칙, T008 |
| SC-001 | T012, T013 |
| SC-002 | T010, T016 |
| SC-003 | T010 |
| SC-004 | T015 |
| SC-005 | T016 |

## Dependencies & Execution Order

- T001 → T002 → T003·T004(병렬) → US1(T005·T006 병렬 → T007 → T008) → US2(T009 → T010).
- 프론트: T012는 계약 v1.5로 바로 시작한다. T011은 T012의 `sendMessage` 옵션 이후, T013은 T011·T012 이후다.
- QA: T014는 T010 이후, T016은 T013 이후, T015는 키가 준비되면 언제든 한다.

## 선행 조건 (team-lead)

- [x] 헌법 기술 제약 Amplitude 줄 개정: v1.3.1(f488739)에서 해소했다.
- 운영 Secrets `AMPLITUDE_API_KEY`·`AMPLITUDE_SECRET_KEY` 등록은 배포 전에 한다(값은 레포 밖).
