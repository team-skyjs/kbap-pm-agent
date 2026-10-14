---
description: "프론트 재설계 구현 태스크"
---

# Tasks: 프론트 재설계 — 대화에 집중하는 채팅 화면

**Input**: `specs/003-frontend-redesign/`의 plan.md, spec.md, research.md, data-model.md, contracts/chart-block.md, quickstart.md

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 스토리마다 검사 하나(Playwright 시나리오나 assert 스크립트)와 QA 태스크 하나를 둔다. Playwright는 PRD가 요청한 검사다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명`

- **역할**: `[DS]` frontend-designer(표현: 토큰·레이아웃·컴포넌트 마크업과 CSS), `[FE]` frontend-dev(렌더러·차트 파서·검사 스크립트·의존성), `[QA]` qa-integrator(ui-review + Playwright), `[BE]` backend-dev(시스템 프롬프트 한 줄), `[USER]` 사용자 결정
- **스토리**: `[US1]`~`[US12]` = PRD US-001~US-012

## 공통 규칙

- `frontend/src/api.ts`, `frontend/vite.config.ts`는 고치지 않는다(접근 제한 PR 소유). API 호출·SSE 처리·토큰 입력 흐름은 그대로 쓴다(FR-012).
- 파일 소유를 지킨다. `style.css`·`App.tsx`·`ConversationList.tsx`·`Chat.tsx`·`ProposalCard.tsx`·`SettingsPage.tsx`는 DS다. `Markdown.tsx`·`chartBlock.ts`·`ChartBlock.tsx`·`package.json`·`playwright.config.ts`·`checks/**`는 FE다. 남의 파일이 필요하면 담당자에게 요청한다.
- 컴포넌트 CSS에 원시 값 금지(0·1px·100% 예외). 값은 `:root` 토큰에서만 온다(FR-001).
- 표현 스토리의 완료 조건은 `npm run build` 통과, 해당 `checks/ui/usN.spec.ts` 통과, ui-review 스크린샷 확인이다.
- 커밋은 경로 지정, 스토리 단위, `feat/frontend-redesign`에 한다.

## 선행 조건

- [ ] 접근 제한 PR이 main에 머지된 뒤 `git merge origin/main`으로 이 브랜치에 합친다. 이 병합 전에는 `style.css`·`App.tsx`·`Chat.tsx`·`checks/run.ts`를 고치지 않는다. 두 PR이 같은 파일을 바꾼다(research R5).
  - 병합 전에 해도 되는 태스크: T001~T008(설치·검사 뼈대·설계 문서·토큰 제안서와 사용자 결정), T018·T033·T035(새 파일 렌더러·파서·차트), T032(사용자), T034(`run.ts` 한 줄 제외), T038·T039(백엔드).
  - 병합 뒤 세션 만료 배너 동작은 US8이 이어받는다.

---

## Phase 1: Setup

- [ ] T001 [FE] `frontend/package.json`과 `.gitignore`를 준비한다.
  - 의존성: `remark-gfm`, `chart.js`(^4)를 추가한다. 개발 의존성은 `@playwright/test`, `@axe-core/playwright`다.
  - 스크립트: `"check:ui": "playwright test -c playwright.config.ts"`를 추가한다. 기존 `check`·`build`는 그대로다.
  - `.gitignore`에 `_workspace/04_designer_screenshots/`, `frontend/test-results/`, `frontend/playwright-report/`를 넣는다.
  - quickstart의 `npx playwright install chromium`이 동작하는지 확인한다.

---

## Phase 2: Foundational — UI 검사 뼈대와 설계 문서

**Purpose**: 모든 표현 스토리의 완료 조건(Playwright)과 설계 입력을 먼저 세운다.

- [ ] T002 [FE] `frontend/playwright.config.ts`: `webServer`(`npm run dev`, 5173, reuseExistingServer)를 둔다.
  - 프로젝트 9개: 뷰포트 `1280x800`·`768x1024`·`375x812` × 모드 `light`·`dark`(`colorScheme`)·`reduced`(`reducedMotion: 'reduce'`, light), Chromium 하나.
  - 환경변수 `CHECK_UI_LIVE`가 없으면 고정 응답 모드다(ADR-26).
- [ ] T003 [FE] `frontend/checks/ui/fixtures.ts`: `page.route('**/api/**')` 고정 응답을 둔다.
  - 계약 예시: 대화 목록, 상세, 설정, 제안 PATCH 응답을 `frontend/checks/contract.ts`로 계약 분할본에서 읽는다.
  - SSE 스크립트 6종은 계약 05-messages 예시를 바탕으로 만든다.
    - 전송 직후: `message_created`만 보내고 2초간 유지한다.
    - 진행: `tool_call` 두 개 뒤 대기한다.
    - 완료: 제안 두 개가 든 `final`이다.
    - 부분 완료: `final`의 `content`가 "모델 호출 상한(10턴)에 도달해…"로 시작한다.
    - 오류: `error` `UPSTREAM_ERROR`다.
    - 세션 만료: 401 `text/html`이다.
  - 마크다운 표본 답변: 제목 4단계, 목록, 작업 목록, 표, 인용, 구분선, 코드, 링크, `<script>` 문자열과 `contracts/chart-block.md`의 세 예시를 그대로 넣는다.
- [ ] T004 [FE] `frontend/checks/ui/helpers.ts`: 공용 도구다.
  - 접근성: `expectNoSeriousA11y(page)`는 axe `critical`·`serious` 0을 확인한다.
  - 대비: `contrast(fg, bg)`는 WCAG 상대 휘도 공식으로 계산한다.
  - 레이아웃: `expectNoHorizontalScroll(page)`.
  - 스크린샷: `shot(page, story)`는 `_workspace/04_designer_screenshots/<story>-<project>.png`로 저장한다.
  - `frontend/checks/ui/smoke.spec.ts`: 고정 응답으로 앱이 뜨고 헬스 표시가 보인다.
- [ ] T005 [QA] 뼈대 검증: `npm run check:ui`로 smoke가 9프로젝트에서 통과하고 스크린샷 9장이 생기는지, 기존 `npm run check`가 영향 없이 통과하는지 확인한다
- [ ] T006 [DS] 설계 문서 `_workspace/04_designer_shell.md`·`_chat.md`·`_proposal.md`·`_settings.md`를 쓴다(`chat-ui-design` 스킬 형식, ChatGPT 데스크톱 레퍼런스). 각 문서에 레이아웃, 상태, 반응형, 접근성 항목과 쓰는 토큰 이름을 적는다(data-model.md 1절)

**Checkpoint**: 검사 명령이 돌고 설계 입력이 있다.

---

## Phase 3: User Story 1 — 디자인 토큰 (P1)

**Goal**: 모든 화면이 쓰는 토큰을 라이트·다크 쌍으로 정의하고 가독성 기준을 계산값으로 증명한다.

**Independent Test**: 토큰 제안서 계산값표를 확인하고, `us1.spec.ts`가 본문 크기·줄 간격·대비와 원시 값 부재를 검사한다.

- [ ] T007 [US1] [DS] `_workspace/04_designer_tokens.md`: 토큰 제안서를 쓴다(`design-system` 스킬).
  - 값: data-model.md 1절 토큰 전부의 라이트·다크 값을 적는다.
  - 대비 계산표: `--color-text`·`--color-text-muted` 대 `--color-bg`·`--color-surface`·`--color-user-bubble`은 4.5:1 이상, `--color-focus`·`--chart-1`~`4` 대 배경은 3:1 이상이다.
  - 강조색 후보 3개를 낸다.
- [ ] T008 [US1] [USER] 토큰 제안서를 보고 강조색 하나를 정한다(입력 문서의 첫 결정 지점). 결정을 제안서에 기록한다
- [ ] T009 [US1] [DS] `frontend/src/style.css`(선행 조건 이후)를 토큰 기반으로 바꾼다.
  - 토큰: `:root`에 토큰을 두고, `@media (prefers-color-scheme: dark)`에서 같은 이름의 값만 교체한다. `@media (prefers-reduced-motion: reduce)`에서 `--duration-*`는 0ms다.
  - 기본 요소: 본문 글꼴·크기·줄 간격·배경·글자색을 토큰으로 둔다.
  - 정리: 기존 원시 값을 모두 토큰으로 바꾼다.
- [ ] T010 [US1] [FE] `frontend/checks/ui/us1.spec.ts`: assert 항목은 다음과 같다. (US1 검사)
  - 가독성: `body`의 계산된 `font-size` ≥ 16px, `line-height`/`font-size` ≥ 1.6이다.
  - 대비: light·dark 프로젝트에서 본문·보조 텍스트 대 배경 대비가 4.5:1 이상이다(`contrast`).
  - 원시 값 부재: `frontend/src/*.css`의 `:root` 블록 밖과 `*.tsx`의 `style={{...}}`에 hex 색·`px` 원시 값이 없다(0·1px·100% 예외, Node `fs`로 검사).
- [ ] T011 [US1] [QA] us1 실행과 ui-review(토큰 일관성, 라이트·다크 스크린샷). 제안서 계산값과 화면 계산값 차이를 리포트한다 (US1 QA)

---

## Phase 4: User Story 2 — 앱 셸 레이아웃 (P1)

**Goal**: 사이드 패널(접기 유지) · 중앙 채팅(최대 폭) · 하단 입력창, 768px 이하 Drawer.

**Independent Test**: `us2.spec.ts`.

- [ ] T012 [US2] [DS] `frontend/src/App.tsx`·`style.css`: 셸을 만든다.
  - 사이드 패널: 고정 폭 토큰이다. 접기 버튼(`aria-label`, `aria-expanded`)이 있고 상태는 `localStorage` 키 하나에 저장한다(`try/catch`, 실패 무시).
  - 채팅·헤더: 중앙 채팅은 `--content-max` 가운데 정렬, 헤더는 대화 제목과 상태 배지뿐이다.
  - Drawer(768px 이하): 메뉴 버튼으로 열고 배경 클릭·ESC로 닫는다. `role="dialog"`·`aria-modal`, 포커스 가두기와 닫을 때 메뉴 버튼으로 포커스 복귀, 열린 동안 `body` 스크롤 잠금이다. 테두리·그림자는 Drawer에만 둔다.
  - 기존 해시 라우팅과 헬스 표시, 접근 제한이 넣은 세션 만료 처리는 유지한다.
- [ ] T013 [US2] [FE] `frontend/checks/ui/us2.spec.ts`: 1280에서 접기 → 새로고침 → 유지, 768·375에서 Drawer 열기·ESC·배경 클릭 닫기, 열린 동안 `document.body` 스크롤 잠김, Drawer 안 포커스 순환, 375 가로 스크롤 없음, 넓은 화면에서 채팅 본문 폭 ≤ `--content-max`를 assert하고 스크린샷을 찍는다 (US2 검사)
- [ ] T014 [US2] [QA] us2 실행과 ui-review(셸 9조합 스크린샷) (US2 QA)

---

## Phase 5: User Story 4 — 메시지 표현과 타이포그래피 (P1)

**Independent Test**: `us4.spec.ts`.

- [ ] T015 [US4] [DS] `frontend/src/Chat.tsx`·`style.css`: 메시지 표현을 바꾼다.
  - 구분: 사용자 메시지는 오른쪽 정렬·`--color-user-bubble` 배경, AI 메시지는 왼쪽·배경 없음·아바타 없음이다.
  - 글자: 글자 크기·줄 간격·단락 간격은 토큰이다.
  - 넘침: 긴 URL은 `overflow-wrap: anywhere`, 긴 코드는 블록 안 스크롤이다.
  - `api.ts` 호출과 SSE 처리 흐름은 바꾸지 않는다.
- [ ] T016 [US4] [FE] `frontend/checks/ui/us4.spec.ts`: 긴 URL·긴 코드가 든 고정 응답 대화에서 가로 넘침이 없고, 사용자 메시지만 배경이 있고, AI 메시지에 아바타 요소가 없는지 assert한다 (US4 검사)
- [ ] T017 [US4] [QA] us4 실행과 ui-review(메시지 타이포 스크린샷) (US4 QA)

---

## Phase 6: User Story 5 — 마크다운 렌더링 (P1)

**Independent Test**: `us5.spec.ts`.

- [ ] T018 [US5] [FE] `frontend/src/Markdown.tsx`: `react-markdown` + `remark-gfm` 컴포넌트를 만든다(ADR-25).
  - HTML: `rehype-raw`를 쓰지 않는다(HTML 미해석).
  - 링크: `target="_blank" rel="noopener noreferrer"`.
  - 표: 가로 스크롤 감싸개 `div`(`tabIndex=0`, `role="region"`, `aria-label`)로 감싼다.
  - 코드 블록: 언어 표시와 복사 버튼(`navigator.clipboard.writeText`, 성공 시 "복사됨" 1.5초, 실패 시 짧은 안내)을 둔다. 인라인 코드는 구분한다.
  - 언어 `chart`는 US6 전까지 일반 코드 블록으로 둔다.
- [ ] T019 [US5] [DS] `style.css`: 마크다운 요소 스타일을 토큰으로 둔다. 대상은 제목 4단계, 목록, 작업 목록, 인용, 구분선, 강조, 링크, 표(머리글 구분), 코드 블록(mono·스크롤·머리 영역), 인라인 코드다
- [ ] T020 [US5] [DS] `Chat.tsx`·`ProposalCard.tsx`: AI 본문, 제안 `proposal`, `steps` 항목을 `Markdown`으로 렌더한다
- [ ] T021 [US5] [FE] `frontend/checks/ui/us5.spec.ts`: 마크다운 표본 답변에서 다음을 assert하고 스크린샷을 찍는다. (US5 검사)
  - 요소: `h1`~`h4`, `table`과 `thead`, 작업 목록 체크박스(비활성), `blockquote`, `hr`가 있다.
  - 안전: 링크의 `target`·`rel`이 맞고, `<script>`는 문자로 보이며 DOM에 `script` 요소가 추가되지 않는다.
  - 상호작용: 코드 복사 클릭 후 클립보드 값이 원문이고(권한 부여), 표 감싸개가 가로 스크롤 가능하다.
- [ ] T022 [US5] [QA] us5 실행과 ui-review(마크다운 라이트·다크) (US5 QA)

---

## Phase 7: User Story 7 — 입력창과 전송 (P1)

**Independent Test**: `us7.spec.ts`.

- [ ] T023 [US7] [DS] `Chat.tsx`·`style.css`: 입력창을 하단에 고정한다. (US7)
  - 크기: 내용에 따라 자동 높이, 최대 `--composer-max-lines`(6줄)다.
  - 키: Enter 전송, Shift+Enter 줄바꿈이다. 한글 조합 중 Enter는 전송하지 않는다(`isComposing`).
  - 실행 중: 비활성과 안내 문구.
  - 접근성: `aria-label`과 포커스 윤곽선.
  - 보존: 오류·세션 만료 후 입력값을 보존한다.
- [ ] T024 [US7] [FE] `frontend/checks/ui/us7.spec.ts`: Shift+Enter 줄바꿈, Enter 전송, 6줄 초과 시 높이 고정과 내부 스크롤, 진행 고정 응답에서 비활성·안내 문구, 오류·세션 만료 고정 응답 후 입력값 유지, 한글 조합 중 Enter 미전송(`compositionstart` 이벤트로 흉내)을 assert한다 (US7 검사)
- [ ] T025 [US7] [QA] us7 실행과 ui-review (US7 QA)

---

## Phase 8: User Story 8 — 스트리밍·진행·오류 상태 (P1)

**Independent Test**: `us8.spec.ts`(SSE 고정 응답 6종).

- [ ] T026 [US8] [DS] `Chat.tsx`·`style.css`: 여섯 화면 상태를 표현한다(data-model.md 3절).
  - 판정: 상태 판정은 작은 순수 함수 `viewState()` 하나다.
  - 각 상태 표시:
    - 전송 직후: 대기 점 애니메이션.
    - 진행: 접힌 한 줄 진행 행과 완료 체크, 펼치면 `resultSummary`.
    - 완료: 본문과 제안 카드.
    - 부분 완료: 연한 안내 블록.
    - 오류: 문구와 다시 시도(입력 복원).
    - 세션 만료: 상단 배너(접근 제한의 동작 이어받기).
  - 레이아웃·동작: 높이 예약으로 점프를 막는다. 애니메이션은 `--duration-*`만 쓰고 동작 줄이기를 따른다.
  - 스크롤·낭독: 맨 아래에 있을 때만 자동 스크롤한다. 진행 행은 `aria-live="polite"`다.
- [ ] T027 [US8] [FE] `frontend/checks/ui/us8.spec.ts`: (US8 검사)
  - 상태: 6종 고정 응답마다 해당 표시 요소가 보이고 나머지는 없다.
  - 레이아웃: 진행 → 완료 전환에서 입력창의 `boundingBox().y` 변화가 2px 이하다.
  - 스크롤: 위로 스크롤한 상태에서 새 이벤트가 와도 `scrollTop`이 유지된다.
  - 동작 줄이기: reduced 프로젝트에서 대기 표시의 `animation-duration`이 0s다.
  - 실제 경로: `CHECK_UI_LIVE=1`이면 실제 fake 백엔드로 진행 → 완료 한 경로를 돈다.
- [ ] T028 [US8] [QA] us8 실행(고정 응답 + live 한 번)과 ui-review(상태 6종 스크린샷) (US8 QA)

---

## Phase 9: User Story 3 — 사이드 패널 대화 목록 (P2)

- [ ] T029 [US3] [DS] `ConversationList.tsx`·`style.css`: 다음을 반영한다.
  - 목록 상단 "새 대화" 버튼, 최근순, 제목 한 줄 말줄임, 현재 대화 강조(`aria-current="page"`).
  - 제안 수·채택 수 표시, 하단 고정 설정 링크.
  - hover·focus-visible·active 토큰 조합. 목록은 링크·버튼 요소라 Tab·Enter로 조작된다.
- [ ] T030 [US3] [FE] `frontend/checks/ui/us3.spec.ts`: 고정 응답 대화 3개에서 다음을 assert한다. (US3 검사)
  - 정렬·표시: 최근순, 긴 제목 말줄임(`text-overflow`), 현재 항목 `aria-current`, 제안 수·채택 수 텍스트.
  - 키보드: Tab·Enter만으로 다른 대화 선택.
  - 배치: 설정 링크가 패널 하단이다.
- [ ] T031 [US3] [QA] us3 실행과 ui-review(목록 상태 4종) (US3 QA)

---

## Phase 10: User Story 6 — 답변 안 데이터 블록을 차트로 (P2)

- [ ] T032 [US6] [USER] 차트 라이브러리를 확인한다. 기본안은 Chart.js v4다(research R1 실측 171KB min). 다르게 정하면 CTO에 알린다(ADR-24)
- [ ] T033 [US6] [FE] `frontend/src/chartBlock.ts`: `parseChartBlock(text)`를 둔다. 반환은 `{ok:true, spec} | {ok:false, reason}`이고, 검증 규칙은 data-model.md 2절을 그대로 따른다(추가 키 오류, 길이 일치, 전부 null 오류)
- [ ] T034 [US6] [FE] `frontend/checks/check-f7.ts`: `contracts/chart-block.md`의 세 예시(선·막대 통과, pie 실패)와 다섯 가지 실패 사례(길이 불일치, 추가 키, 전부 null, `series` 5개, JSON 깨짐)를 assert한다. 예시는 파일에서 직접 읽는다. 선행 조건 이후 `frontend/checks/run.ts` 목록에 f7 한 줄을 추가한다 (US6 검사 1)
- [ ] T035 [US6] [FE] `frontend/src/ChartBlock.tsx`: 차트를 그린다.
  - 로드·등록: `import('chart.js')`로 지연 로드하고 ADR-24의 컨트롤러만 등록한다.
  - 색: `getComputedStyle`로 `--chart-1`~`4`·`--chart-grid`·`--color-text`를 읽고, `matchMedia('(prefers-color-scheme: dark)')` change에서 다시 읽어 `update()`한다.
  - 생명주기·크기: 언마운트 시 `destroy()`, x 라벨 자동 생략, 반응형 크기다.
  - 접근성: 캔버스 컨테이너에 `role="img"`·`aria-label={title}`을 두고, 시각적으로 숨긴 `<table>`을 같은 데이터로 렌더한다.
- [ ] T036 [US6] [FE] `Markdown.tsx`: 언어 `chart` 코드 블록을 `parseChartBlock`으로 검사한다. 성공이면 `ChartBlock`, 실패면 원문 코드 블록이다
- [ ] T037 [US6] [DS] `style.css`: `--chart-1`~`4`·`--chart-grid` 토큰 라이트·다크 값(제안서 확정값), 차트 컨테이너(높이 예약·여백), 숨긴 표용 `.visually-hidden` 유틸리티
- [ ] T038 [US6] [BE] `backend/app/agent.py` `SYSTEM_PROMPT`에 한 줄을 추가한다: "시계열 지표(날짜별 수치)를 답할 때는 본문에 chart 코드 블록을 함께 쓴다. 형식:"과 `contracts/chart-block.md`의 선 예시 JSON 한 줄. 모델명은 넣지 않는다. 다른 프롬프트 문장은 바꾸지 않는다
- [ ] T039 [US6] [BE] `backend/checks/check_b9.py`: `SYSTEM_PROMPT`에 위 문장과 `specs/003-frontend-redesign/contracts/chart-block.md`의 선 예시 JSON이 글자 단위로 들어 있는지 assert한다 (US6 검사 2)
- [ ] T040 [US6] [FE] `frontend/checks/ui/us6.spec.ts`: (US6 검사 3)
  - 렌더링: 표본 답변에서 `canvas` 2개, 오류 예시는 `code.language-chart` 원문, 각 차트 컨테이너의 `aria-label`과 숨긴 표 행 수.
  - 다크: dark 프로젝트에서 차트가 그려진다(캔버스 비어 있지 않음, 픽셀 샘플).
  - 지연 로드: 차트 블록이 없는 대화를 열 때 `chart` 청크 요청이 없다(`page.on('request')`).
- [ ] T041 [US6] [QA] us6·f7·b9 실행, `npm run build`의 청크 크기 기록(차트 청크 ≤ 200KB, 전체 증가 ≤ 300KB, research R1 측정과 대조), ui-review(차트 라이트·다크) (US6 QA)

---

## Phase 11: User Story 9 — 제안 카드 재설계 (P2)

- [ ] T042 [US9] [DS] `ProposalCard.tsx`·`style.css`: 다음을 반영한다.
  - 배치: AI 메시지와 같은 폭이다.
  - 구역: 네 구역은 `<details>/<summary>` 또는 `aria-expanded` 버튼이다. 기본은 제안만 펼침이다.
  - 근거·퍼널: 근거 종류 라벨(지표·코드·택사노미), 코드 근거의 파일·함수·줄, 퍼널 단계 기존/신규 라벨.
  - 버튼·상태: 채택·보류·되돌리기는 카드 하단 오른쪽이고, 상태는 색과 라벨 텍스트를 같이 쓴다.
  - `updateProposal` 호출 흐름은 그대로다.
- [ ] T043 [US9] [FE] `frontend/checks/ui/us9.spec.ts`: (US9 검사)
  - 구역·근거: 계약 Proposal 예시 고정 응답에서 기본 펼침 상태, 근거 라벨 3종, 코드 근거의 `src/app/scan.tsx`·함수·줄 텍스트, 신규 단계 라벨.
  - 채택: 채택 클릭 → PATCH 고정 응답 → 상태 라벨 "채택", 새로고침 후 유지(상세 고정 응답 갱신).
- [ ] T044 [US9] [QA] us9 실행과 ui-review(카드 접힘·펼침·상태 3종) (US9 QA)

---

## Phase 12: User Story 11 — 접근성 (P2)

- [ ] T045 [US11] [DS] 전 화면 접근성을 손본다: 포커스 순서와 시각 순서 일치, `:focus-visible` 윤곽선(`--color-focus`), 아이콘 버튼 `aria-label`, 진행 live region(T026) 확인, Drawer 포커스 가두기(T012) 확인
- [ ] T046 [US11] [FE] `frontend/checks/ui/us11.spec.ts`: (US11 검사)
  - 키보드 흐름: 마우스 없이 새 대화 → 입력 → Enter → 완료 고정 응답 → 제안 "채택" 버튼까지 Tab으로 도달해 Enter로 채택한다.
  - axe: 채팅·설정·Drawer 열림·제안 카드 펼침 화면에서 `expectNoSeriousA11y`.
- [ ] T047 [US11] [QA] us11 실행, 9조합 axe 결과 리포트(심각·중대 0) (US11 QA)

---

## Phase 13: User Story 10 — 설정 화면 재스타일 (P3)

- [ ] T048 [US10] [DS] `SettingsPage.tsx`·`style.css`: 구역(저장소·택사노미·Amplitude·토큰·예산) 간격·타이포·폼 요소를 토큰으로 맞춘다. 상태는 라벨 텍스트와 색을 같이 쓴다(연결됨·미연결·마지막 동기화). 기능·API 호출은 바꾸지 않는다
- [ ] T049 [US10] [FE] `frontend/checks/ui/us10.spec.ts`: 설정 고정 응답에서 상태 라벨 텍스트("연결됨" 등), 폼 요소 포커스 윤곽선, 토큰 입력과 저장 동작이 기존과 같은지(`localStorage` 키), 375 가로 스크롤 없음을 assert한다 (US10 검사)
- [ ] T050 [US10] [QA] us10 실행과 ui-review(설정 라이트·다크) (US10 QA)

---

## Phase 14: User Story 12 — 자동 UI 검사 완성 (P1, 집계)

**Goal**: 스토리별 시나리오를 한 명령으로 9조합 전부 안정적으로 돌리고 ui-review 입력을 만든다. 뼈대는 Phase 2에서 세웠다.

- [ ] T051 [US12] [FE] `frontend/checks/ui/README.md`에 실행법, 프로젝트 목록, live 모드, 스크린샷 규칙을 적는다. 시나리오 전부를 3회 연속 돌려 불안정한 대기(`waitForTimeout`)를 상태 기반 대기로 바꾼다 (US12)
- [ ] T052 [US12] [QA] 전체 검증: (US12 QA)
  - 검사: `npm run check`(f1~f7)와 `npm run check:ui` 전체(9조합)가 통과한다.
  - 화면 리뷰: 스크린샷 전체로 ui-review를 하고, 차단·높음이 0건이어야 한다(SC-002). 결과는 `_workspace/05_ui_review.md`에 쓴다.

---

## Phase 15: Polish

- [ ] T053 [QA] 회귀 확인: 질문 → 제안 → 채택 → 새로고침 흐름(fake 백엔드, SC-004)을 돈다. 기존 계약 검사도 돌린다(`cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md` 출력 없음, 계약 미변경 확인)
- [ ] T054 [QA] 실제 키 확보 시 시계열 질문 5건으로 차트 블록 출현률을 잰다(SC-007, ADR-27 가정 검증). 결과는 CTO에 보낸다
- [ ] T055 [USER] 두 사용자가 주관 평가를 한다(SC-006). 코드 가독성 지적이 있으면 구문 강조 재검토(ADR-25)
- [ ] T056 [FE] 두 PR(접근 제한, 재설계) 머지 후: `check:ui`를 배포 워크플로우에 넣을지 team-lead와 정한다. 넣으면 Chromium 설치와 `check:ui` 단계를 추가하는 PR을 따로 연다(ADR-26)

---

## 요구사항 커버리지

| 요구 | 태스크 |
|---|---|
| FR-001 토큰만 | T007~T010, T037 |
| FR-002 16px·1.6·4.5:1 | T007, T009, T010 |
| FR-003 셸 | T012, T013 |
| FR-004 Drawer | T012, T013, T045 |
| FR-005 시스템 테마 | T009, T035 |
| FR-006 GFM·HTML 미해석·링크 | T018~T021 |
| FR-007 코드 블록 | T018, T019, T021 |
| FR-008 차트·대체·대체 표 | T033~T037, T040 |
| FR-009 여섯 상태·입력 보존 | T023, T026, T027 |
| FR-010 상호작용 4상태 | T009, T029, T045 |
| FR-011 키보드·접근성 | T045, T046 |
| FR-012 기능·API 불변 | 공통 규칙, T053 |
| FR-013 자동 검사 | T002~T005, T051, T052 |
| FR-014 에이전트 지시 | T038, T039 |
| FR-015 메시지 구분 | T015, T016 |
| FR-016 애니메이션·점프·스크롤 | T026, T027 |
| SC-001 | T007, T010, T011 |
| SC-002 | T052 |
| SC-003 | T047, T052 |
| SC-004 | T053 |
| SC-005 | T041 |
| SC-006 | T055 |
| SC-007 | T054 |

## Dependencies & Execution Order

- **선행 조건**(접근 제한 머지 → main 병합)은 DS의 `style.css`·`App.tsx`·`Chat.tsx` 태스크와 T034의 `run.ts` 한 줄을 막는다. 병합 전에 시작할 수 있는 태스크: T001~T008(설치·검사 뼈대·설계 문서·토큰 제안서와 사용자 결정), T018·T033·T035(새 파일 렌더러·파서·차트), T032(사용자), T034(`run.ts` 한 줄 제외), T038·T039(백엔드).
- **Phase 2**(T002~T006) → 모든 `usN.spec.ts`.
- **US1**: T007 → T008(사용자) → T009 순서다. T009가 끝나야 DS 표현 태스크가 시작된다.
- **P1 스토리 순서**: US2 → US4 → US5 → US7 → US8. US5의 T018(FE 새 파일)은 US1과 병렬이다.
- **P2**: US3, US6, US9, US11. US6은 T032(사용자) 후 T035, T036은 T018 이후, T038·T039(BE)는 언제든 된다. US11은 다른 표현 스토리 이후다.
- **P3**: US10. **US12**: 모든 스토리 이후. **Polish**: 마지막. T056은 두 PR 머지 후다.

## Parallel Opportunities

- FE의 T001~T004·T018·T033·T034·T035는 DS의 T006·T007과 동시에 진행한다(새 파일, 겹치지 않음).
- BE의 T038·T039는 다른 모든 태스크와 독립이다.
- 표현 스토리마다 DS 구현과 FE 시나리오 작성은 병렬이다(시나리오는 설계 문서 T006 기준으로 먼저 쓰고 구현이 따라온다).

## Implementation Strategy

1. Setup + 검사 뼈대 + 설계 문서 + 토큰 제안서(사용자 확인)까지 끝낸다. 렌더러·파서 새 파일은 이와 병렬로 만든다.
2. 접근 제한 머지를 기다렸다가 main을 병합하고, P1 표현 스토리(US2 → US4 → US5 → US7 → US8)를 진행한다.
3. P2(US3·US6·US9·US11), P3(US10)를 진행한 뒤 US12 집계와 ui-review를 한다.
4. 실제 키로 차트 블록 출현률, 사용자 주관 평가, CI 편입을 결정한다.
