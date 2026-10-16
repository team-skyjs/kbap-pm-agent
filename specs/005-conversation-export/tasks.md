---
description: "대화 전체 내보내기 구현 태스크"
---

# Tasks: 대화 전체 내보내기

**Input**: `specs/005-conversation-export/`의 plan.md, spec.md, research.md, data-model.md, contracts/(계약 v1.4, export-markdown.md), quickstart.md

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 모듈마다 검사 하나와 QA 하나를 둔다. 모듈은 둘이다. E1 프론트 내보내기는 `check-f10.ts`와 `checks/ui/us13.spec.ts`, E2 백엔드 기록은 `check_b11.py`다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명 (모듈)`

- **역할**: `[FE]` frontend-dev(프론트 전부, 이번에 한해 `Chat.tsx`·`style.css`도), `[BE]` backend-dev(기록 엔드포인트), `[QA]` qa-integrator
- **스토리**: `[US1]` PDF, `[US2]` Markdown, `[US3]` 기록

## 공통 규칙

- 새 의존성, 서버 PDF, 헤드리스 브라우저, PDF 라이브러리 금지(FR-011).
- 내보낸 파일·인쇄 머리글에 API 주소·호스트명 금지(FR-009).
- 색·간격은 토큰만 쓴다. 인쇄용 밝은 값도 `--print-*` 토큰이다.
- 커밋은 경로 지정, `feat/conversation-export`에 한다.

---

## Phase 1: Foundational — 내보내기 버튼

- [ ] T001 [FE] 대화 상단 바(`Shell.tsx` `Topbar` 자식 또는 `Chat.tsx`)에 "내보내기" 버튼과 메뉴(PDF, Markdown)를 둔다. (E1)
  - 비활성: 메시지가 0개이거나 에이전트 실행 중이면 비활성이다.
  - 접근성: 버튼은 `aria-haspopup`·`aria-expanded`, 메뉴 항목은 Tab·Enter·ESC로 조작한다. 닫히면 버튼으로 포커스가 돌아간다.

---

## Phase 2: User Story 1 — PDF 인쇄 (P1) (E1)

- [ ] T002 [US1] [FE] `frontend/src/style.css` 끝에 `@media print` 블록과 `--print-*` 토큰을 둔다(research R2). (E1)
  - 흐름 풀기: `.app`·메인 열·`.scroll`의 `height: auto; max-height: none; overflow: visible; display: block`.
  - 숨김: 사이드바, Drawer, 입력창, 다듬기 카드, 상단 바 버튼·배지, 제안 카드 조작 버튼, `details.tools`, 코드 복사 버튼.
  - 페이지: 메시지·제안 카드 `break-inside: avoid`. `pre`·`code`·표 셀은 줄 바꿈으로 넘치지 않게 하고, `canvas`는 `max-width: 100%; height: auto`. `@page { margin: 16mm }`.
  - 밝게: 색 토큰을 `--print-*` 밝은 값으로 다시 정의하고 `color-scheme: light`. 다크 정의보다 뒤에 둔다.
- [ ] T003 [US1] [FE] 인쇄 머리글 요소(대화 제목, 생성일, 내보낸 날짜)를 대화 화면에 두고 화면에서는 숨긴다. 주소·호스트명은 넣지 않는다 (E1)
- [ ] T004 [US1] [FE] `frontend/src/print.ts`(신규): `startPrint()`가 기록(T011) 후 `window.print()`를 부른다. `beforeprint`에서 닫힌 `.proposal-card details`를 기록해 열고, `afterprint`에서 그것만 닫는다(research R2) (E1)
- [ ] T005 [US1] [FE] `frontend/src/ChartBlock.tsx`: `beforeprint`/`afterprint`와 `matchMedia('print')`를 듣는다(research R3). (E1)
  - 인쇄 전: 애니메이션을 끄고 `--print-chart-1`~`4`·`--print-text`·`--print-grid`에서 색을 읽어 인쇄 폭 상수로 `resize` + `update('none')`.
  - 인쇄 후: 화면 색·원래 애니메이션 설정으로 되돌리고 `resize()`.

---

## Phase 3: User Story 2 — Markdown 파일 (P1) (E1)

- [ ] T006 [US2] [FE] `frontend/src/exportMarkdown.ts`(신규): `toMarkdown(detail, now)`와 `exportFileName(title, id, now)`를 `contracts/export-markdown.md` 규격 그대로 구현한다. 입력은 대화 상세 응답과 시각뿐이고 `location`·API 기준 주소를 읽지 않는다 (E1)
- [ ] T007 [US2] [FE] Markdown 선택 시 화면이 가진 대화 상세 데이터로 파일을 만들어 내려받는다. Blob(`text/markdown;charset=utf-8`) → `<a download>` → `revokeObjectURL` 순서이고, 서버를 다시 부르지 않는다. 시작 시 기록(T011)한다 (E1)
- [ ] T008 [US2] [FE] `frontend/checks/check-f10.ts`(신규, `checks/run.ts`에 한 줄): assert 항목은 다음과 같다. (E1 검사)
  - 생성 결과: 계약 `04-conversations.md` 상세 예시와 Proposal 예시로 만든 결과에 머리글, 역할·시각 제목, 본문 원문, `### 제안 N. … — 미정|채택|보류`, 네 절, 퍼널 표가 있다.
  - chart 블록: 003 `chart-block.md` 선 예시를 본문에 넣으면 원문 그대로 남는다.
  - 실패 메시지: `> 실패: {errorCode}`가 붙는다.
  - 파일 이름: 금지 문자 치환, 60자 자르기, 제목 null이면 `대화-{id}`, 날짜 `YYYYMMDD`.
  - 운영 정보: 본문 원문 밖에 `http://`·`https://`가 없다.

---

## Phase 4: User Story 3 — 내보내기 기록 (P2) (E2)

- [ ] T009 [US3] [BE] `backend/schema.sql`에 `conversation_exports`(data-model.md, `conversation_id` FK `ON DELETE CASCADE`, `format ENUM('pdf','markdown') NOT NULL`, `created_at DATETIME(3)`)를 추가한다. `backend/app/conversations.py`에 `POST /api/conversations/{conversation_id}/exports`를 만든다. `format`이 두 값 밖이면 400 `VALIDATION_ERROR`, 없는 대화는 404 `CONVERSATION_NOT_FOUND`, 성공은 201 `{exportId, conversationId, format, createdAt}`(계약 v1.4 `08c-exports.md`)다 (E2)
- [ ] T010 [US3] [BE] `backend/checks/check_b11.py`(신규): 201 응답 키가 계약 예시와 같고 행이 하나 생긴다. 잘못된 형식은 400, 없는 대화는 404다. pdf 1·markdown 2를 넣은 뒤 data-model.md의 형식별 건수 SQL 결과가 맞다 (E2 검사)
- [ ] T011 [P] [US3] [FE] `frontend/src/api.ts`에 `recordExport(conversationId, format)`(응답 타입 `ExportRecord`, 기존 파서 방식)를 둔다. `print.ts`·Markdown 내려받기가 기다리지 않고 부르며 실패는 무시한다 (E1)

---

## Phase 5: UI 검사와 검증

- [ ] T012 [FE] `frontend/checks/ui/fixtures.ts`에 내보내기 기록 고정 응답(201, 500)을 추가하고 `frontend/checks/ui/us13.spec.ts`(신규)를 쓴다(research R5). (E1 검사)
  - 인쇄 매체: `emulateMedia({media: 'print'})`에서 숨길 요소가 `display: none`이고, `.app`·`.scroll`이 스크롤 영역이 아니다(`overflow` visible, `scrollHeight <= clientHeight + 1`). 인쇄 머리글이 보이고, dark 컨텍스트에서도 `body` 배경이 흰색이다.
  - 인쇄 직전·직후: `beforeprint` 이벤트를 보내면 제안 카드 네 절이 열리고 차트 캔버스 폭이 인쇄 폭 이하다. `afterprint`면 원래대로 돌아온다.
  - Markdown: 다운로드 이벤트의 파일 이름 형식과 내용(상태 라벨, 네 절)을 확인한다.
  - 버튼·기록: 메시지 0개·실행 중이면 비활성이다. 기록 POST 본문의 `format`이 맞고, 기록 500이어도 내려받기와 `window.print` 호출(스텁)이 된다.
- [ ] T013 [QA] E1 검증: `check-f10`·`us13`을 실행한다. Chrome 인쇄 미리보기에서 quickstart 시나리오 2~4(긴 대화 전체, 카드 네 절, 차트 가독성, 다크→밝게, 취소 후 복원)를 수동으로 확인하고, ui-review(인쇄 결과)를 한다. 차트·끊김 결과를 CTO에 보낸다(ADR-32 가정 확인) (E1 QA)
- [ ] T014 [QA] E2 검증: `check_b11.py`를 실행하고, 계약 diff 0(`cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md`)을 확인한다. 프론트 기록 호출 본문을 계약과 대조한다 (E2 QA)
- [ ] T015 [QA] 회귀: `npm run check`(f1~f10), `npm run check:ui` 전체, 백엔드 `check_b1`~`check_b11` 순차 실행, 질문 → 제안 → 채택 흐름 유지를 본다(SC-005)

---

## 요구사항 커버리지

| 요구 | 태스크 |
|---|---|
| FR-001 버튼·비활성·키보드 | T001, T012 |
| FR-002 인쇄 흐름 풀기 | T002, T004, T012 |
| FR-003 숨김·머리글 | T002, T003, T012 |
| FR-004 카드 펼침·복원 | T004, T012 |
| FR-005 차트 재그리기·복원 | T005, T012, T013 |
| FR-006 밝은 인쇄 | T002, T005, T012 |
| FR-007 끊김·넘침 | T002, T013 |
| FR-008 Markdown 규격 | T006~T008 |
| FR-009 운영 정보 비노출 | T003, T006, T008 |
| FR-010 기록·실패 무시 | T009~T012 |
| FR-011 의존성·서버 PDF 금지 | 공통 규칙 |
| FR-012 기존 동작 불변 | T014, T015 |
| SC-001 | T013 |
| SC-002 | T008 |
| SC-003 | T010 |
| SC-004 | T012 |
| SC-005 | T015 |

## Dependencies & Execution Order

- T001 → US1·US2.
- US1: T002 → T003 → T004·T005(병렬 가능).
- US2: T006 → T007, T008은 T006 이후.
- US3: BE의 T009 → T010. FE의 T011은 계약 v1.4로 바로 시작하고 T004·T007이 쓴다.
- T012는 T001~T007·T011 이후, QA는 각 모듈 완료 후다.

## Implementation Strategy

1. frontend-dev가 T001 → US1(T002~T005) → US2(T006~T008) → T011 → T012 순서로 진행한다.
2. backend-dev는 동시에 T009·T010을 끝낸다.
3. QA는 E2(T014) → E1(T013) → 회귀(T015) 순서다.
