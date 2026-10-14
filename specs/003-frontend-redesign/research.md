# Research: 프론트 재설계

Technical Context에 NEEDS CLARIFICATION은 없다. 이 문서는 plan이 정할 세 가지(차트 라이브러리, 구문 강조, UI 검사 구성·CI)와 구현 위험 두 가지(테마 전환 시 차트 색, 접근 제한 PR과의 병합)를 다룬다.

## R1. 차트 라이브러리 (ADR-24)

조건(PRD US-006·7절): 선·막대, 범례·축 라벨·값 툴팁, 다크 모드, 접근성, 번들 증가 200KB 이하.

**측정** (2026-10-15, esbuild `--bundle --minify`, 선·막대에 필요한 부분만 import, 격리된 임시 디렉토리):

| 후보 | 버전 | min | gzip | 범례·툴팁 | 다크 모드 | 접근성 | React 의존 |
|---|---|---|---|---|---|---|---|
| **Chart.js** (컨트롤러 선택 등록) | 4.5.1 | 171KB | 59KB | 내장 | 색을 옵션으로 주입, 테마 변경 시 `update()` | canvas라 대체 텍스트 필요 | 없음 |
| uPlot | 1.6.32 | 50KB | 22KB | 범례 내장, 툴팁은 플러그인 직접 작성 | 색 주입 | canvas, 대체 텍스트 필요 | 없음 |
| Recharts | 2.15.4 | 393KB | 108KB | 내장 | props | SVG지만 기본 낭독 지원 약함 | 있음 |
| (참고) remark-gfm | 4.0.1 | 41KB | 12KB | — | — | — | — |

- Decision: **Chart.js v4**. `LineController`·`BarController`·`CategoryScale`·`LinearScale`·`PointElement`·`LineElement`·`BarElement`·`Legend`·`Tooltip`·`Title`만 등록하고, 차트 블록이 처음 나올 때 동적 `import()`로 별도 청크를 받는다.
- Rationale: 200KB(min) 안에 들고, PRD가 요구한 범례·축 라벨·툴팁이 내장이라 직접 짜는 코드가 없다. uPlot은 30% 크기지만 툴팁과 막대 정렬을 직접 구현해야 해 원칙 II(짧은 코드)에 불리하다. Recharts는 예산을 넘는다.
- 접근성: canvas 차트는 낭독되지 않는다. 그래서 모든 라이브러리에 공통으로 같은 JSON에서 만든 시각적으로 숨긴 `<table>`과 `role="img"`·`aria-label`(제목)을 둔다(data-model.md).
- 총량: remark-gfm 41 + Chart.js 171 = 약 212KB(min)로 SC-005의 300KB 안이다. Chart.js는 지연 청크라 첫 화면 비용에는 들지 않는다.
- **검증 방법**: T005(의존성 추가 직후)와 마지막 QA에서 `vite build` 결과의 청크 크기를 기록하고 위 측정과 대조한다. 200KB를 넘으면 uPlot으로 바꾼다(ChartBlock.tsx 내부만 바뀐다).
- 사용자 확인: 입력 문서의 "첫 사용자 결정 지점"이라 tasks.md `[USER]` 태스크로 둔다.

## R2. 코드 블록 구문 강조 (ADR-25)

- Decision: **넣지 않는다.** 코드 블록은 고정폭 글꼴, 가로 스크롤, 언어 표시, 복사 버튼만 갖는다.
- Rationale: PRD 5절이 "차트 라이브러리 하나만 예외"로 새 의존성을 묶었다. 구문 강조기(highlight.js 코어 + 언어 몇 개, Prism, Shiki)는 두 번째 예외가 된다. 답변의 코드는 짧은 이벤트 호출 예시가 대부분이라 강조 없이도 읽힌다.
- Alternatives considered: highlight.js core + 언어 4~5개(추정 수십 KB, 지연 로드 가능). Shiki는 WASM·문법 파일로 수백 KB라 제외했다.
- 다시 볼 조건: 사용자 평가(SC-006)에서 코드 가독성이 지적되면 다음 사이클에서 highlight.js core를 지연 로드로 검토한다.

## R3. UI 검사 구성과 CI (ADR-26)

- Decision:
  - **도구**: `@playwright/test` + `@axe-core/playwright`, Chromium만 쓴다. `frontend/playwright.config.ts`의 `webServer`가 `vite dev`(5173)를 띄운다.
  - **매트릭스**: 프로젝트 = 뷰포트 3종(1280×800, 768×1024, 375×812) × 모드 3종(light, dark, reduced-motion). 모드는 `colorScheme`, `reducedMotion` 컨텍스트 옵션이다.
  - **API**: 기본은 `page.route('**/api/**')`로 고정 응답을 준다. 고정 응답은 계약 분할본의 예시 JSON(`frontend/checks/contract.ts`로 읽음)과 SSE 스크립트 6종으로 만든다. SSE는 전송 직후, 진행, 완료, 부분 완료, 오류, 세션 만료이고 세션 만료는 401 HTML이다. 백엔드 없이 결정적으로 돈다.
  - **실제 경로 한 개**: `CHECK_UI_LIVE=1`이면 정상 스트리밍 시나리오 하나만 고정 응답 없이 로컬 백엔드 fake 모드(`docker compose up`)로 돈다. PRD US-012의 "백엔드 fake 모드"를 이것으로 만족한다.
  - **스크린샷**: 시나리오 끝마다 `_workspace/04_designer_screenshots/<story>-<viewport>-<mode>.png`로 저장한다. 이 폴더는 gitignore한다(이미지가 레포를 키우고, ui-review 입력은 로컬이면 충분하다).
  - **CI**: 이번 사이클은 로컬 실행만 한다. 배포 워크플로우가 접근 제한 PR에서 바뀌고 있어 같은 파일을 동시에 고치지 않는다. 두 PR이 모두 머지된 뒤 `check:ui`를 CI 단계로 넣을지 별도 태스크로 정한다(tasks.md Polish).
- Rationale: 오류·부분 완료·세션 만료는 fake 백엔드가 재현하지 못한다. 그래서 기본은 고정 응답이 맞고, 진짜 SSE 타이밍은 live 한 개로 확인한다. 고정 응답을 계약 예시에서 만들면 계약과 화면 검사가 같은 기준을 본다(원칙 I).
- Alternatives considered: 백엔드 fake 모드 전용(오류 상태 재현 불가), MSW(의존성 추가, Playwright route로 충분).
- 접근성 기준: axe 결과 중 `impact`가 `critical`·`serious`인 위반이 0이면 통과다(SC-003).

## R4. 테마 전환 시 차트 색

- Decision: ChartBlock은 그릴 때 `getComputedStyle(document.documentElement)`로 토큰 값(`--color-text`, `--color-border`, `--chart-1`~`--chart-4`)을 읽는다. `matchMedia('(prefers-color-scheme: dark)')`의 change 이벤트에서 색을 다시 읽어 `chart.update()`한다.
- Rationale: 차트 색을 토큰에서만 가져와 FR-001을 지킨다. 테마가 화면을 연 채 바뀌는 엣지 케이스도 처리한다.
- 토큰 요구: 디자인 토큰에 차트 시리즈 색 4개(`--chart-1`~`--chart-4`)를 라이트·다크 쌍으로 둔다. 표면 대비 3:1 이상(그래픽 요소 기준)으로 한다(data-model.md).

## R5. 접근 제한 PR과의 병합 순서

- 사실(2026-10-15, `origin/main...origin/feat/access-gate-resume` 비교): 접근 제한 PR이 고친 프론트 파일은 `api.ts`, `App.tsx`, `Chat.tsx`(세션 만료 안내), `style.css`(1줄), `vite.config.ts`, `checks/check-f6.ts`·`check-g2.ts`·`run.ts`다. `api.ts`뿐 아니라 재설계가 다시 짜는 `App.tsx`·`Chat.tsx`·`style.css`와 겹친다.
- Decision (2026-10-15 사용자 결정으로 변경): 재설계를 먼저 머지하고, 접근 제한 PR은 맨 나중에 이 변경 위로 병합한다.
  - 재설계는 main의 현재 화면 파일을 기준으로 바로 작업한다. `api.ts`·`vite.config.ts`는 고치지 않아 충돌 범위를 화면 파일과 검사 목록으로 줄인다.
  - 접근 제한 쪽이 병합할 때 세션 만료 배너와 `SESSION_EXPIRED` 판정을 재설계된 `Chat.tsx`에 다시 얹는다. 재설계는 배너 자리만 마련한다. 지금의 `UNAUTHORIZED`(공유 토큰 401)는 세션 만료가 아니라 오류 상태(토큰·설정 안내)로 표시한다(QA UI-2).
- ADR 파일: 이 브랜치의 ADR-24~27은 접근 제한 브랜치의 ADR-21~23과 같은 위치(“위임” 절 앞)에 붙는다. 머지 때 글자 충돌이 나지만 두 블록을 순서대로 남기면 된다.
