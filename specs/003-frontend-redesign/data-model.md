# Data Model: 프론트 재설계

저장 구조(DB)와 API는 바뀌지 않는다. 이 문서는 화면 쪽 데이터 세 가지를 정의한다.

## 1. 디자인 토큰 (`frontend/src/style.css` `:root`)

이름은 고정하고 값은 토큰 제안서(US1, 사용자 확인)에서 정한다. 다크는 `@media (prefers-color-scheme: dark) { :root { ... } }`에서 같은 이름의 값만 바꾼다.

| 그룹 | 토큰 | 규칙 |
|---|---|---|
| 색 | `--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-border`, `--color-accent`, `--color-accent-contrast`, `--color-danger`, `--color-user-bubble`, `--color-focus` | `--color-text`·`--color-text-muted` 대 `--color-bg`·`--color-surface`·`--color-user-bubble` 대비 4.5:1 이상. `--color-focus` 대 배경 3:1 이상 |
| 차트 | `--chart-1`~`--chart-4`, `--chart-grid` | 시리즈 색 대 `--color-bg` 3:1 이상 |
| 글꼴 | `--font-sans`, `--font-mono` | 시스템 글꼴 스택(웹폰트 내려받기 없음) |
| 크기 | `--text-sm`, `--text-base`, `--text-lg` | `--text-base` ≥ 16px |
| 줄 간격·자간 | `--leading-body`, `--leading-tight`, `--tracking-body` | `--leading-body` ≥ 1.6 |
| 간격 | `--space-1`~`--space-8` | 4px 배수 |
| 반경 | `--radius-sm`, `--radius-md`, `--radius-lg` | |
| 그림자 | `--shadow-overlay` | Drawer·팝오버에만 |
| 레이아웃 | `--sidebar-width`, `--content-max`, `--composer-max-lines` | `--content-max` 720~800px |
| 전환 | `--duration-fast`(150ms), `--duration-base`(250ms) | `prefers-reduced-motion: reduce`에서 0ms |

토큰 제안서(`_workspace/04_designer_tokens.md`)는 라이트·다크 대비 계산값표를 포함한다(SC-001 근거).

## 2. 차트 블록 (`frontend/src/chartBlock.ts`)

형식 기준은 [contracts/chart-block.md](./contracts/chart-block.md)이다.

```ts
type ChartSpec = {
  type: 'line' | 'bar'
  title: string
  x: string[]
  series: { name: string; values: (number | null)[] }[]
}
// parseChartBlock(text: string): { ok: true; spec: ChartSpec } | { ok: false; reason: string }
```

검증 규칙(하나라도 어기면 `ok: false`, 화면은 원문 코드 블록):
- JSON 파싱이 실패하면 오류다.
- 최상위가 객체이고 키는 정확히 `type`·`title`·`x`·`series`다(추가 키는 오류).
- `type`은 `line`·`bar` 중 하나다. `title`은 1~80자 문자열이다.
- `x`는 1~366개 문자열이고 `series`는 1~4개다.
- 각 시리즈는 키가 `name`·`values`이고 `name`은 1~40자다. `values` 길이는 `x`와 같고, 원소는 유한한 숫자나 `null`이며, 전부 `null`이면 오류다.

대체 텍스트: `ChartBlock`은 같은 `spec`으로 시각적으로 숨긴 `<table>`(행 = x, 열 = 시리즈)을 렌더하고, 캔버스 컨테이너에 `role="img"`와 `aria-label={title}`을 둔다.

## 3. 메시지 화면 상태 (`Chat.tsx` 표현용, API 타입 아님)

API의 `Message.status`(`running`·`completed`·`failed`)와 SSE 이벤트에서 화면 상태 여섯 개를 파생한다. API 타입은 그대로다.

| 화면 상태 | 판정 | 표시 |
|---|---|---|
| 전송 직후 | `message_created` 후 첫 `tool_call` 전 | AI 자리 대기 점 애니메이션(동작 줄이기 시 정적 표시) |
| 진행 | `running`이고 도구 호출 있음 | 접힌 한 줄 진행 행(조회 중 → 완료 체크), 펼치면 `resultSummary` |
| 완료 | `final`, `status: "completed"`, 상한 사유 없음 | 본문 + 제안 카드 |
| 부분 완료 | `final`이고 `content`가 계약의 상한 사유 문장으로 시작 | 본문 위 연한 안내 블록 |
| 오류 | `error` 이벤트, `status: "failed"`, 또는 `ApiError`(아래 `SESSION_EXPIRED` 제외). `UNAUTHORIZED`도 여기다 | 짧은 문구 + 다시 시도(입력값 복원). `UNAUTHORIZED`면 "접근 토큰이 없거나 틀렸습니다" + 설정 화면 링크이고 다시 로그인 안내는 없다 |
| 세션 만료 | `ApiError` 코드 `SESSION_EXPIRED`만. 접근 제한 PR(#12)이 프론트 판정을 추가한 뒤에만 생긴다 | 상단 배너 + 다시 로그인(새로고침), 입력값 보존. #12 병합 때 연결한다 |

- 부분 완료 판정 문구는 계약 05-messages 비고의 두 예시 앞부분이다("모델 호출 상한(", "실행 시간 상한(").
- 판정 함수는 `Chat.tsx` 안의 작은 순수 함수 하나로 두고 Playwright 고정 응답으로 검사한다.
- `UNAUTHORIZED`(백엔드 공유 토큰 401, 계약 JSON)와 세션 만료(접근 계층 응답)는 섞지 않는다(계약 v1.1 공통 인증, v1.2 접근 계층 응답). 해결 방법이 다르다. 앞은 설정에서 토큰을 넣고, 뒤는 다시 로그인한다(QA UI-2).
