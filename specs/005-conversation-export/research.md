# Research: 대화 전체 내보내기

NEEDS CLARIFICATION은 없다. 이 문서는 내보내기 기록(R1), 인쇄 레이아웃(R2), 차트 인쇄(R3), Markdown 형식(R4), UI 검사(R5)를 정한다.

## R1. 내보내기 기록 (ADR-31)

- Decision: (a) 최소 엔드포인트 `POST /api/conversations/{conversationId}/exports` `{format: "pdf" | "markdown"}` → 201과 테이블 `conversation_exports`. 질문 마법사 선택 기록과 같은 방식이다. 프론트는 시작할 때 한 번 부르고 기다리지 않는다.
- Rationale: 성공 기준이 "건수·형식 기록"뿐인데, PRD가 말한 "기존 로그 경로"는 조회할 수 있는 형태로 존재하지 않는다. 기록을 생략하면(b) 측정이 사라진다. 엔드포인트 하나·테이블 하나·검사 하나라 비용이 작다.
- PDF 기록 시점: 인쇄 대화상자를 연 순간이다(`window.print()` 호출 직전). 브라우저는 사용자가 "PDF로 저장"을 했는지 알려 주지 않으므로 "시작" 건수다.
- 조회 한 줄:
  ```sql
  SELECT format, COUNT(*) AS n FROM conversation_exports GROUP BY format;
  ```

## R2. 인쇄 레이아웃 (ADR-32)

- 원인(PRD 2절): `.app { height: var(--viewport-h); overflow: hidden }`(`--viewport-h: 100dvh`) 안의 `.scroll { overflow-y: auto }`가 문서 흐름 밖이라 한 화면 분량만 인쇄된다.
- Decision: `style.css` 끝에 `@media print` 블록 하나를 둔다.
  - **흐름 풀기**: `.app`, `.app` 안 메인 열, `.scroll`에 `height: auto; max-height: none; overflow: visible; display: block`.
  - **숨김**: 사이드바, Drawer, 입력창(composer), 다듬기 카드, 상단 바의 버튼·배지, 제안 카드의 채택·보류 버튼, 도구 진행 행(`details.tools`), 코드 복사 버튼, 세션·오류 배너의 조작 버튼.
  - **보이기**: 인쇄 머리글 요소(화면에서는 `display: none`). 내용은 대화 제목, 생성일, 내보낸 날짜다.
  - **끊김 방지**: 메시지 블록과 제안 카드에 `break-inside: avoid`. 한 페이지보다 크면 브라우저가 나눈다.
  - **넘침 방지**: `pre, code`에 `white-space: pre-wrap; overflow-wrap: anywhere`, 표 감싸개에 `overflow: visible`, 표에 `table-layout: fixed; width: 100%`, 셀 `overflow-wrap: anywhere`.
  - **밝게**: 같은 블록에서 `:root`의 색 토큰을 밝은 값으로 다시 정의하고 `color-scheme: light`. 다크 테마 정의(`prefers-color-scheme: dark`)보다 뒤에 둬 덮어쓴다. 값은 `--print-*` 토큰을 참조한다(원시 값 금지, FR-001).
  - **페이지**: `@page { margin: 16mm }`.
- 닫힌 `<details>` 문제: 제안 카드의 네 절은 `<details>`이고 기본으로 "제안"만 열려 있다. 닫힌 `<details>`의 내용은 인쇄되지 않는다. 그래서 `print.ts`가 `beforeprint`에서 `.proposal-card details:not([open])`을 기록해 두고 `open`을 켜며, `afterprint`에서 기록한 것만 다시 닫는다. 도구 진행 행 `details.tools`는 인쇄에서 숨기므로 건드리지 않는다.
- 이벤트: Chrome·Safari·Firefox 모두 `beforeprint`/`afterprint`를 지원한다. `window.print()`를 거치지 않은 Ctrl+P도 같은 이벤트가 오므로 같은 결과다.

## R3. 차트 인쇄 (ADR-32)

- 사실: 인쇄 미리보기는 페이지 폭으로 다시 배치하지만 캔버스 비트맵은 다시 그려지지 않는다. `beforeprint` 시점의 `getComputedStyle`은 여전히 화면 매체 값이다(다크면 다크 색).
- Decision: `ChartBlock`이 `window`의 `beforeprint`/`afterprint`와 `matchMedia('print')` change를 듣는다.
  - 인쇄 전: `animation: false`로 두고, 색을 `--print-chart-1`~`4`·`--print-text`·`--print-grid` 토큰(항상 밝은 값)에서 읽는다. `chart.resize(PRINT_WIDTH, 높이)` 후 `update('none')`. `PRINT_WIDTH`는 A4 세로에서 여백 16mm를 뺀 본문 폭에 맞춘 상수 하나(약 680px)다.
  - 인쇄 후: 화면 토큰 색과 원래 애니메이션 설정으로 되돌리고 `resize()`(컨테이너 크기)한다.
  - 인쇄 CSS: `canvas { max-width: 100% !important; height: auto !important }`로 비트맵이 폭을 넘지 않게 한다.
- Alternatives considered: 인쇄 전에 캔버스를 이미지로 바꿔 끼우기(DOM 교체·복원이 더 복잡), 인쇄용 별도 차트 렌더(코드 중복).
- 가정: 위 상수 폭과 CSS 축소로 A4·Letter 모두 읽을 수 있다. Chrome 미리보기로 확인한다(SC-001, 수동).

## R4. Markdown 형식 (ADR-33)

- Decision: [contracts/export-markdown.md](./contracts/export-markdown.md) 하나가 기준이다. 요지는 다음과 같다.
  - 머리글: 제목·생성 시각·내보낸 날짜·메시지 수.
  - 메시지: 역할·로컬 시각(UTC 오프셋 표기)과 본문 원문.
  - 제안 카드: 제목·상태(채택/보류/미정)·유형과 근거·제안·실행 단계·측정 방법 네 절(퍼널은 표).
  - 그 밖: 결정 메모, chart 블록은 본문 원문이라 그대로 남는다.
  - 파일 이름: `{다듬은 제목}-{YYYYMMDD}.md`, 제목이 없으면 `대화-{id}`.
- Rationale: 본문을 원문 그대로 두면 표·코드·chart 블록이 손실 없이 남는다. 제안 카드는 화면 구조(네 절)를 그대로 옮겨 문서로 잘라 쓰기 좋다. 시각을 로컬 + 오프셋으로 적으면 읽기 쉽고 모호하지 않다.
- 내려받기: `new Blob([text], {type: 'text/markdown;charset=utf-8'})` → `URL.createObjectURL` → 임시 `<a download>` 클릭 → `revokeObjectURL`. 화면이 이미 가진 대화 상세 응답을 쓰며, 다시 부르지 않는다.
- 운영 정보: 생성 함수는 대화 데이터만 입력으로 받고 `location`·API 기준 주소를 읽지 않는다. 검사(f10)가 결과에 `http://`·`https://`가 본문 원문 밖에서 생기지 않는지 본다.

## R5. UI 검사 (us13)

- `page.emulateMedia({ media: 'print' })`로 다음을 확인한다.
  - 숨김: 사이드바·입력창·다듬기 카드·버튼의 `display: none`.
  - 흐름: `.app`의 `overflow`가 visible이고 높이가 뷰포트 고정이 아니다. `.scroll`의 `overflow-y`가 visible이고 `scrollHeight <= clientHeight + 1`이다.
  - 표시: 인쇄 머리글이 보인다. 다크 컨텍스트에서도 `body` 배경이 흰색이다.
- `emulateMedia`는 `beforeprint`를 일으키지 않는다. 그래서 `window.dispatchEvent(new Event('beforeprint'))`로 details 열림과 차트 재그리기(캔버스 폭 ≤ 인쇄 폭, 애니메이션 꺼짐)를 확인하고, `afterprint`로 복원을 확인한다.
- Markdown: `page.waitForEvent('download')`로 파일 이름 형식과 내용(제안 상태 라벨, 네 절, chart 블록 원문)을 확인한다.
- 기록: 고정 응답으로 `POST .../exports` 본문의 `format`을 확인하고, 기록 500이어도 내려받기가 되는지 본다. `window.print`는 스텁으로 바꿔 대화상자를 열지 않는다.
