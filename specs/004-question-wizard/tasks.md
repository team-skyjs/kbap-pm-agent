---
description: "질문 마법사 구현 태스크"
---

# Tasks: 질문 마법사

**Input**: `specs/004-question-wizard/`의 plan.md, spec.md, research.md, data-model.md, quickstart.md, contracts/README.md(정본 계약 v1.3)

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 모듈마다 검사 하나와 QA 하나다. 모듈은 셋이다. Q1 백엔드 다듬기는 `check_b10.py`, Q2 프론트 계약·상태는 `check-f9.ts`, Q3 프론트 화면은 `checks/ui/us12.spec.ts`다. 모델 비교(US4)는 측정이다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명 (모듈)`

- **역할**: `[BE]` backend-dev(엔드포인트·프롬프트·기록 테이블·마이그레이션·검사 b10·비교 스크립트), `[FE]` frontend-dev(`api.ts` 호출·상태 훅·선택 기록 전송·검사 f9·Playwright us12), `[DS]` frontend-designer(버튼·비교 카드 표현·접근성), `[QA]` qa-integrator(경계면·ui-review·모델 비교표 채점)

## 공통 규칙

- 응답 shape는 계약 v1.3(`_workspace/01_cto_api-contract.md`, 분할본 `08b-questions.md`)이 기준이다. 맞지 않으면 CTO에 요청한다.
- LLM 호출은 `backend/app/agent.py`의 `refine()`으로만 한다(원칙 III). 모델명을 코드에 박지 않는다.
- 프론트 파일 소유(003 규칙)를 지킨다. `Chat.tsx`·`style.css`·`RefineCard.tsx`는 DS, `api.ts`·`refine.ts`·`checks/**`는 FE다.
- 사용자 중간 확인 없이 끝까지 간다(사용자 지시). 커밋은 경로 지정, `feat/question-wizard`에 한다.

---

## Phase 1: Setup

- [ ] T001 [BE] `.env.example`·`deploy/kbap-pm-agent.env.example`에 `REFINE_MODEL=`(비우면 `CODE_SUMMARY_MODEL`)을 주석과 함께 추가한다. 배포 워크플로우의 env 생성 단계에도 `REFINE_MODEL=${REFINE_MODEL:-}`(Variables)를 추가한다 (Q1)

---

## Phase 2: Foundational — 다듬기 엔드포인트 뼈대(시연 모드), 저장 구조 (Q1)

**Purpose**: 프론트가 실제 백엔드(fake)로 붙을 수 있는 최소 경계면이다.

- [ ] T002 [BE] `backend/schema.sql`: `question_refinements` 테이블을 data-model.md 그대로 추가한다. 제약은 다음과 같다. (Q1)
  - `conversation_id BIGINT NULL` FK `ON DELETE SET NULL`.
  - `choice ENUM('refined','original','cancelled') NULL`.
  - `summary VARCHAR(300)`, `chosen_at DATETIME(3) NULL`.
  - `llm_usage.purpose`는 `ENUM('agent','code_summary','refine') NOT NULL`로 바꾼다.
- [ ] T003 [BE] `backend/app/db.py` `init()`: `schema.sql` 실행 뒤 마이그레이션을 실행한다(ADR-29). `information_schema.COLUMNS`에서 `llm_usage.purpose`의 `COLUMN_TYPE`에 `'refine'`이 없을 때만 `ALTER TABLE llm_usage MODIFY purpose ENUM('agent','code_summary','refine') NOT NULL`이다. 주석에 이유(기존 테이블 ENUM은 CREATE IF NOT EXISTS로 안 바뀜)를 적는다 (Q1)
- [ ] T004 [BE] `backend/app/schemas.py`에 두 모델을 추가한다. (Q1)
  - `RefineResult`: `refined` 1~4000자, `summary` 1~300자. 모델 출력이 벗어나면 엔드포인트가 502 `UPSTREAM_ERROR`(자르지 않음, 행 없음)다.
  - 요청 모델: `question` 1~4000자이고 공백만이면 거절, `conversationId`는 int 또는 null.
- [ ] T005 [BE] `backend/app/agent.py` `refine(prompt) -> (RefineResult, model_str)`: 다듬기 seam이다. 실제 런타임은 T010에서 채운다. (Q1)
  - 모델: `env("REFINE_MODEL") or env("CODE_SUMMARY_MODEL")`.
  - fake 분기: 계약 v1.3 다듬기 응답 예시의 `refined`·`summary`를 반환하고 `budget.record("refine", "fake", 0, 0, None)`.
  - 기동 검사: `check_models()`에 `REFINE_MODEL`(설정된 경우) 접두사 검사를 추가한다.
  - 예시: `backend/checks/examples.py`에 계약 08b 예시를 추가한다.
- [ ] T006 [BE] `backend/app/refine.py`(신규)에 `POST /api/questions/refine`를 만들고 `main.py`에 라우터를 등록한다. (Q1)
  - 처리 순서: 요청 검증(400 `VALIDATION_ERROR`), `conversationId`가 있으면 존재 확인(404 `CONVERSATION_NOT_FOUND`), `budget.check()`(403 `BUDGET_EXCEEDED`), 입력 조립(T011이 채운다. 그 전에는 질문만 넘긴다), `agent.refine()`, `question_refinements` 행 삽입, 응답 `{refinementId, refined, summary}`.
  - 잘림 표시: 조립 결과가 `truncated`면 요약 끝에 " (택사노미 이름이 많아 앞부분만 참고)"를 붙인다. 합계가 300자를 넘으면 모델 요약 쪽을 줄인다(계약 v1.3).
  - 실패 처리: 모델 실패·구조화 검증 실패(`refined` 4,000자 초과 포함)는 502 `UPSTREAM_ERROR`이고 행을 만들지 않는다.
- [ ] T007 [BE] `backend/checks/check_b10.py`(신규, fake 모드): assert 항목은 다음과 같다. (Q1 검사)
  - 응답·기록: 다듬기 응답 키가 계약 예시와 같고(`refinementId`는 새 정수, `refined`·`summary`는 예시와 글자 단위로 같음), 행 1개, `llm_usage`에 `purpose='refine'` 0원 행 1개가 생긴다.
  - 검증: 빈 문자열·공백만·4001자는 400이다. 없는 `conversationId`는 404, `conversationId: null`은 200이다.
  - 예산: `LLM_BUDGET_USD=0`이면 403이다.
  - 마이그레이션: 검사 DB에 옛 ENUM(`'agent','code_summary'`)으로 `llm_usage`를 만들고 `init()`을 두 번 호출하면 `COLUMN_TYPE`에 `refine`이 있고 두 번째 호출이 에러 없이 끝난다.
- [ ] T008 [QA] Q1 교차 검증: curl 응답을 계약 08b 예시와 키 단위로 대조하고 `check_b10.py`를 순차 실행한다. 계약 diff 0(`cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md`)을 확인한다 (Q1 QA)

**Checkpoint**: fake 백엔드로 다듬기가 왕복하고 기록이 남는다.

---

## Phase 3: User Story 2 — 다듬은 질문이 답하기 좋은 모양 (P1) (Q1)

**Goal**: 실제 모델 경로와 다듬기 규칙·입력 조립.

**Independent Test**: `check_b10.py`의 규칙·조립·가짜 전송 항목과, 실제 키가 있으면 spec US2 수락 시나리오 네 질문.

- [ ] T009 [P] [US2] [BE] 런타임 두 파일에 `refine(model, prompt) -> (RefineResult, input_tokens, output_tokens)`를 둔다(research R2). (Q1)
  - `agent_anthropic.py`: `messages.parse(model, max_tokens=2000, output_format=RefineResult, output_config={"effort": "low"}, messages=[...])`. `tools`·`tool_choice`·`thinking`은 주지 않는다. `stop_reason == "refusal"`이면 예외다. usage를 반환한다.
  - `agent_openai.py`: `Agent(model, output_type=RefineResult, tools=[])` 단발 실행, usage를 반환한다.
  - `agent.refine()` real 분기가 이를 부르고 `budget.record("refine", model_str, ...)`한다.
- [ ] T010 [US2] [BE] `backend/app/refine.py` `REFINE_PROMPT` 상수: ADR-30의 규칙 여덟 개(7·8은 실제 키 QA 관찰로 추가. 아래는 1~6의 요지:의도 유지, 기간·실제 이벤트 이름·지표·산출물 드러내기, 지어내지 않기·목록에 없는 대상은 사용자 말 유지, 기본값은 요약에 "(원문에 없음)", 이미 구체적이면 그대로, 한국어 두 문장 이내·요약 한 줄)를 문장으로 둔다 (Q1)
- [ ] T011 [US2] [BE] `refine.py` 입력 조립 함수 `build_prompt(question, conversation_id)`(research R5): (Q1)
  - 택사노미: `app_settings.taxonomy`의 `events[].name`만 쉼표로 잇고, 없으면 "택사노미 없음"이다. 4,000자를 넘을 때만 고르는 순서를 바꾼다. 질문과 겹치는 이름(이름 전체가 질문에 들어 있거나, 이름을 `_`로 나눈 조각 하나가 질문의 영숫자 낱말(소문자)과 같음)을 원래 순서대로 먼저 넣는다. 남은 자리는 나머지 이름을 원래 순서대로 4,000자 안에서 채운다. 잘렸으면 `truncated=True`를 함께 반환한다.
  - 이력: 대화의 `status='completed'`이고 비어 있지 않은 메시지 중 최근 사용자 2개·에이전트 2개, 각 앞 500자, 오래된 순이다. null 대화면 이력 없음이다.
  - 마지막에 질문을 붙인다.
- [ ] T012 [US2] [BE] `check_b10.py`에 항목을 추가한다. (Q1 검사)
  - 프롬프트: `REFINE_PROMPT`에 규칙 키 문장 여덟 개가 들어 있다.
  - 조립: `build_prompt`에 택사노미 정의·속성 문자열이 없고 이름만 있다. 이력이 4개 이하이고 각 500자 이하이며 순서가 맞다. 택사노미가 없으면 "택사노미 없음"이다. 이름 합계가 4,000자를 넘는 택사노미면 넣은 이름 문자열이 4,000자 이하이고 `truncated`이며, fake 응답 요약 끝에 고정 문구가 붙고 300자 이하다. 질문 "scan_complete 왜 줄었어?"와 4,000자를 넘는 택사노미(뒤쪽에 `scan_complete`)면, 넣은 목록에 `scan_complete`가 포함된다(겹치는 이름 우선). 겹치지 않는 이름은 원래 순서다.
  - 가짜 전송: 두 런타임이 `RefineResult`를 돌려주고 사용량 행이 생긴다(기존 `checks/llm_mock.py` 재사용). refusal과 잘못된 JSON은 502이고 행이 없다.
- [x] T013 [US2] [QA] US2 검증: `check_b10.py`를 실행한다. 실제 키가 있으면 spec US2 수락 시나리오 질문 네 개(일상어, 택사노미에 없는 대상, 후속 질문, 이미 구체적)를 다듬어 규칙 위반을 리포트한다. 키가 없으면 "미검증"으로 둔다 (Q1 QA)

---

## Phase 4: User Story 1 — 질문을 다듬어 고르고 보낸다 (P1) (Q2, Q3)

**Goal**: 버튼, 진행, 비교 카드, 네 가지 선택, 실패 안내, 키보드 조작.

**Independent Test**: `us12.spec.ts`(고정 응답)와 quickstart 시연 모드 시나리오 1~6.

- [x] T014 [P] [US1] [FE] `frontend/src/api.ts`에 다듬기 호출을 추가한다. (Q2)
  - 타입: `RefineResponse{refinementId, refined, summary}`, `RefineChoice = 'refined' | 'original' | 'cancelled'`, `RefineChoiceResponse{refinementId, choice, chosenAt}`.
  - 함수: `refineQuestion(conversationId: number | null, question)`, `recordRefineChoice(id, choice)`.
  - 파서는 기존 방식(`any`·캐스팅 없음)이고, 에러는 기존 `ApiError`다.
- [x] T015 [US1] [FE] `frontend/src/refine.ts`(신규) 다듬기 상태 훅이다. (Q2)
  - 상태: `idle | refining | card | error`.
  - 시작: `start(question, conversationId)`. 진행 중 대화가 바뀌면 결과를 버린다.
  - 선택 동작: 네 개이고, 각각 `recordRefineChoice`를 기다리지 않고 부르며 실패를 무시한다.
    - `sendRefined()`: 기록 `refined`, 개선안을 전송 함수로 넘김.
    - `sendOriginal()`: 기록 `original`, 원문 전송.
    - `insertRefined()`: 입력창 값만 교체하고 아직 기록하지 않는다. 같은 `refinementId`를 들고 있다가 그 입력으로 실제 전송하면 `refined`, 전송 없이 입력을 비우거나 대화를 떠나면 `cancelled`를 기록한다(PRD 3차).
    - `close()`: 기록 `cancelled`, 원문 유지.
  - 오류: 다듬기 오류면 `error` 상태와 안내 문구이고 원문을 유지한다. `UNAUTHORIZED` 문구는 기존 규칙(003 UI-2)을 따른다.
- [x] T016 [US1] [FE] `frontend/checks/check-f9.ts`: 계약 `08b-questions.md`의 다듬기·선택 응답 예시가 `api.ts` 파서를 통과하고, `choice`가 세 값 밖이면 파서가 거부하는지 확인한다. `checks/run.ts`에 f9를 추가한다 (Q2 검사)
- [ ] T017 [US1] [DS] `frontend/src/RefineCard.tsx`(신규)·`style.css`: 비교 카드 표현이다. (Q3)
  - 배치: 입력창 위에 둔다. 넓은 화면은 좌 원문·우 개선안 두 열, 375px은 위아래로 쌓는다. 개선안 아래에 변경 요약 한 줄이 있다.
  - 동작: 버튼 네 개(개선안으로 보내기·원문으로 보내기·입력창에 넣기·닫기)다.
  - 접근성: `role="region"`과 `aria-labelledby`(제목)다. 열릴 때 첫 동작 버튼으로 포커스가 가고 ESC로 닫는다.
  - 오류: 오류 상태는 짧은 안내 한 줄이다.
  - 스타일: 토큰만 쓰고, 003 상호작용 네 상태와 라이트·다크를 지원한다.
- [ ] T018 [US1] [DS] `frontend/src/Chat.tsx`·`style.css`: 보내기 왼쪽에 "질문 다듬기" 버튼(아이콘 + 라벨, `aria-label`)을 둔다. (Q3)
  - 비활성: 입력이 비었거나, 에이전트 실행 중이거나, 다듬는 중이면 비활성이다. 다듬는 동안 버튼은 진행 표시이고 입력창은 잠긴다.
  - 연결: `refine.ts` 훅을 연결하고, 카드가 닫히면 포커스를 입력창으로 돌린다.
  - 기존 전송 흐름은 그대로다.
- [ ] T019 [US1] [FE] `frontend/checks/ui/fixtures.ts`에 다듬기·선택 고정 응답(계약 08b 예시, 오류 502, 선택 500)을 추가하고 `frontend/checks/ui/us12.spec.ts`를 쓴다. (Q3 검사)
  - 수락 시나리오: spec US1의 1~9를 다룬다.
    - 버튼 상태: 빈 입력 비활성, 실행 중 비활성.
    - 진행·선택: 진행 중 입력창 잠금, 네 선택의 결과(전송 본문, 입력창 값), 선택 POST 본문의 `choice` 값. "입력창에 넣기"는 클릭 시 POST가 없고, 전송 시 `refined`, 입력을 비우면 `cancelled`다.
    - 실패·키보드: 다듬기 502이면 안내와 원문 유지, 키보드만으로 버튼 → 카드 → 선택, 포커스 이동.
  - 기록 실패: 선택 기록 500이어도 전송된다.
  - 공통: axe critical·serious 0, 9조합 스크린샷이다.
- [ ] T020 [US1] [QA] US1 검증: `check-f9`, `us12.spec.ts`를 실행한다. quickstart 시연 시나리오 1~6을 실제 fake 백엔드로 돌리고, ui-review(카드 라이트·다크·375, 버튼 네 상태)를 한다 (Q2·Q3 QA)

---

## Phase 5: User Story 3 — 선택 결과가 남아 채택 비율을 본다 (P2) (Q1)

**Independent Test**: quickstart 시나리오 3~8 후 data-model.md의 채택 비율 SQL.

- [ ] T021 [US3] [BE] `refine.py`에 `POST /api/questions/refine/{refinementId}/choice`를 만든다. (Q1)
  - 검증: `choice` 세 값 밖이면 400이고, 없는 ID는 404 `REFINEMENT_NOT_FOUND`다.
  - 기록: `choice`·`chosen_at`을 갱신한다(덮어쓰기 허용).
  - 응답: `{refinementId, choice, chosenAt}`.
- [ ] T022 [US3] [BE] `check_b10.py`에 항목을 추가한다. (Q1 검사)
  - 응답·덮어쓰기: 선택 200 응답 키가 계약 예시와 같고, 두 번 부르면 마지막 값으로 바뀌며 `chosenAt`이 갱신된다.
  - 에러: 404와 400이다.
  - 집계: 네 행(`refined` 2, `original` 1, `cancelled` 1)에 data-model.md의 채택 비율 SQL을 돌리면 `50.0`이고 `shown`은 4다.
- [ ] T023 [US3] [QA] US3 경계면 검증: (Q1 QA)
  - 매핑: 프론트 선택 POST 본문과 계약 enum이 일치한다. "입력창에 넣기"는 넣는 순간 기록이 없고, 전송하면 `refined`, 비우거나 대화를 떠나면 `cancelled`다.
  - 기록: quickstart 시나리오 3~8 후 DB 행이 맞다.
  - 예산: `settings.budget.spentUsd`에 다듬기 비용이 합산된다(real 모드면 0 초과).

---

## Phase 6: User Story 4 — 다듬기 모델을 비교로 정한다 (P2)

- [ ] T024 [US4] [BE] `backend/checks/compare_refine.py`(신규)를 만든다(research R1).
  - 샘플: 10건을 고정한다. 유형은 일상어 이탈 2, 기간 없는 지표 2, 측정 설계 2, 후속(직전 대화 포함) 2, 이미 구체적 1, 택사노미에 없는 대상 1이다.
  - 입력: 택사노미 이름은 DB 값이 있으면 그것을, 없으면 고정 목록을 쓴다.
  - 실행: 같은 `build_prompt` 결과를 `anthropic:claude-haiku-5-5`와 `anthropic:claude-sonnet-5-5`로 `agent` 런타임을 통해 다듬는다.
  - 출력: `_workspace/06_refine_model_comparison.md`에 샘플별 원문, 두 모델의 개선안·요약·지연(초)·비용, 빈 채점 칸(항목 4 × 0~2)을 표로 쓴다. 비용은 `llm_usage`에 `refine`으로 남는다.
- [x] T025 [US4] [QA] 실제 키(로컬 `.env`)로 `compare_refine.py`를 실행한다. (US4 QA)
  - 채점: 네 항목을 채점하고 합계를 낸다.
  - 결정: ADR-28 규칙(Sonnet이 8점 이상 높거나, Haiku 의도 보존 0점이 2건 이상이면 Sonnet)을 적용해 결정과 근거를 비교표 끝에 쓴다.
  - 보고: CTO에 결과를 보낸다(CTO가 ADR-28 상태를 갱신).
- [ ] T026 [US4] [BE] 결정 반영: `.env.example`·`deploy/kbap-pm-agent.env.example`의 `REFINE_MODEL` 예시와 주석을 결정 모델로 바꾸고, 운영 Variables 값이 필요하다는 것을 `deploy/README.md`에 한 줄 적는다(값 설정은 team-lead)

---

## Phase 7: Polish

- [ ] T027 [QA] 회귀: 아래를 모두 통과하는지 본다.
  - 모듈·UI 검사: `npm run check`(f1~f9), `npm run check:ui` 전체.
  - 백엔드 검사: `check_b1`~`check_b10`을 순차 실행한다.
  - 계약: diff 0.
  - 흐름: 질문 → 제안 → 채택 → 새로고침(fake)이 유지된다(SC-005).
- [ ] T028 [QA] SC-001(비교 실행의 지연 중앙값 ≤ 5초, 결정 모델 기준)과 SC-004(`llm_usage`의 refine 평균 비용 ÷ agent 질문 평균 비용 ≤ 1%)를 기록한다. 키가 없으면 "미검증"이다

---

## 요구사항 커버리지

| 요구 | 태스크 |
|---|---|
| FR-001 버튼·비활성 | T018, T019 |
| FR-002 1회 호출·검증 | T004~T007, T009 |
| FR-003 택사노미·이력 참고 | T011, T012 |
| FR-004 다듬기 규칙 | T010, T012, T013 |
| FR-005 비교 카드·네 동작·키보드 | T015, T017, T018, T019 |
| FR-006 실패 안내 | T006, T015, T019 |
| FR-007 기록·편집 후 전송=채택 | T002, T006, T015, T021~T023 |
| FR-008 사용량·예산 | T002, T003, T005, T009, T023 |
| FR-009 기록 실패가 전송을 막지 않음 | T015, T019 |
| FR-010 모델 설정 | T001, T005, T026 |
| FR-011 시연 모드 | T005, T007 |
| FR-012 기존 계약 불변 | 공통 규칙, T008, T027 |
| SC-001 | T028 |
| SC-002 | T022, T023 |
| SC-003 | T024~T026 |
| SC-004 | T028 |
| SC-005 | T027 |

## Dependencies & Execution Order

- **Phase 2**(T002~T008)는 모든 스토리의 전제다. T005 → T006, T002·T003 → T007.
- **US2**(T009~T013)는 Phase 2 이후이고, T009는 T010·T011과 병렬이다.
- **US1**: FE의 T014~T016은 Phase 2와 병렬이다(계약 예시로 시작). DS의 T017·T018은 T015 훅 인터페이스 확정 후, T019는 T017·T018 이후다.
- **US3**: T021은 T006 이후이고, 프론트 선택 호출은 T015에 이미 있다.
- **US4**: T024는 T009·T011 이후, T025는 T024 이후, T026은 T025 이후다.
- **Polish**: 마지막이다.

## Parallel Opportunities

- backend-dev(T001~T012, T021~T024)와 frontend-dev(T014~T016, T019)는 계약 v1.3을 기준으로 동시에 진행한다.
- designer의 T017(카드)은 T015 훅의 반환 형태만 정해지면 시작한다.

## Implementation Strategy

1. Phase 2로 fake 왕복을 연다. 프론트는 같은 시간에 계약 예시로 API·훅·검사를 만든다.
2. US2 실제 경로와 US1 화면을 병행하고, US3 선택 엔드포인트를 붙인다.
3. US4 비교로 모델을 확정하고, Polish 회귀 후 team-lead가 PR을 연다.
