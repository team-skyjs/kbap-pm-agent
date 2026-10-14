# 디자인 토큰 제안서 (US-001)

상태: **확정·적용됨** (2026-10-15, 강조색 B 파랑). 토큰 이름은 `specs/003-frontend-redesign/data-model.md` 1절을 따른다.
레퍼런스: ChatGPT 데스크톱 앱. 넓은 여백, 거의 없는 테두리, 중립 회색 축, 강조색 하나.
기존 시스템: 없음 (`style.css`에 원시 값만 있고 `:root` 변수 없음).

## 1. 색

중립 회색 축은 채도 0. 구조는 테두리 대신 배경 단차(본문 `bg` / 사이드 패널 `surface`)와 여백으로 만든다.
사용자·AI 구분은 배경 하나로만 한다(사용자만 `bg-user`, AI는 배경 없음).

| 토큰 | 라이트 | 다크 | 용도·근거 |
|------|--------|------|----------|
| `--color-bg` | `#ffffff` | `#212121` | 채팅 본문 배경. 다크는 순흑 대신 눈부심이 적은 짙은 회색 |
| `--color-surface` | `#f9f9f9` | `#171717` | 사이드 패널·코드 블록·카드. 본문과 한 단계 차이 |
| `--color-user-bubble` | `#f4f4f4` | `#303030` | 사용자 메시지 블록 |
| `--color-text` | `#0d0d0d` | `#ececec` | 본문 |
| `--color-text-muted` | `#5d5d5d` | `#b4b4b4` | 보조 텍스트(시각, 수치, 안내). 12~14px에서도 4.5:1 |
| `--color-border` | `#e5e5e5` | `#3a3a3a` | 표 칸, 입력창 윤곽. 장식용이라 정보 전달에 쓰지 않음 |
| `--color-accent` | 후보 중 선택 | 후보 중 선택 | 링크, 주 버튼, 포커스 윤곽선, 현재 대화 표시 |
| `--color-accent-contrast` | `#ffffff` | `#0d0d0d` | 강조색 배경 위 글자 |
| `--color-danger` | `#c62828` | `#ff8a80` | 오류 문구, 세션 만료 배너 |

상태(hover/active)는 별도 토큰 없이 `color-mix(in srgb, var(--color-text) 6%, transparent)` 같은 조합으로 만든다. 값이 하나 더 필요해지면 그때 `--color-hover`를 추가한다.

### 명도 대비 계산값 (WCAG 2.x 상대 휘도)

| 조합 | 라이트 | 다크 | 기준 |
|------|-------|------|------|
| 본문 / bg | 19.44 | 13.63 | 4.5 통과 |
| 본문 / surface | 18.46 | 15.18 | 4.5 통과 |
| 본문 / bg-user | 17.67 | 11.17 | 4.5 통과 |
| 보조 / bg | 6.58 | 7.77 | 4.5 통과 |
| 보조 / surface | 6.25 | 8.65 | 4.5 통과 |
| 보조 / bg-user | 5.99 | 6.37 | 4.5 통과 |
| 위험 / bg | 5.62 | 7.05 | 4.5 통과 |
| 위험 / bg-user | 5.11 | 5.78 | 4.5 통과 |
| 테두리 / bg | 1.26 | 1.42 | 장식용, 기준 대상 아님 |

테두리는 일부러 약하다. 입력창처럼 경계가 조작에 필요한 곳은 포커스 시 강조색 윤곽선(3:1 이상)으로 보강한다.

### 강조색 후보 (하나를 고른다)

| 후보 | 라이트 | 다크 | 강조/bg | 강조/surface | 강조 위 글자 | 인상 |
|------|-------|------|--------|-------------|-------------|------|
| A. 녹청 | `#0d7d5f` | `#10a37f` | 5.10 / 5.04 | 4.85 / 5.61 | 5.10 / 6.08 | ChatGPT 계열. 레퍼런스와 가장 가깝고 "채택"의 긍정 의미와 어울림. 대신 채택 상태색과 겹치지 않게 상태는 라벨로 구분 |
| B. 파랑 | `#2563eb` | `#6ea8fe` | 5.17 / 6.67 | 4.91 / 7.42 | 5.17 / 8.05 | 링크 관습과 일치해 학습 비용 0. 도구형 제품의 중립적 인상 |
| C. 보라 | `#6d28d9` | `#b69cff` | 7.10 / 7.05 | 6.75 / 7.84 | 7.10 / 8.50 | 대비 여유가 가장 크다. K-Bap 고유 색으로 구별되지만 분석 도구치고 개성이 강함 |

(값은 라이트 / 다크 순. 모두 4.5:1 통과.)
추천: **B. 파랑**. 링크·포커스·버튼이 한 색으로 자연스럽고, 녹색은 채택 상태, 빨강은 위험으로 의미가 이미 있어 충돌이 없다.

## 2. 글꼴

| 토큰 | 값 | 근거 |
|------|-----|------|
| `--font-sans` | `system-ui, -apple-system, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif` | 웹 폰트 없이 시스템 폰트. 한국어는 OS 기본 고딕 |
| `--font-mono` | `ui-monospace, "SF Mono", Menlo, Consolas, "D2Coding", monospace` | 코드 블록·인라인 코드 |
| `--text-sm` | `0.875rem` (14px) | 보조 텍스트, 표, 배지 |
| `--text-base` | `1rem` (16px) | 본문. FR-2 하한 |
| `--text-lg` | `1.25rem` (20px) | 제목·헤더 |
| `--leading-body` | `1.6` | 본문 줄 간격. FR-2 하한 |
| `--leading-tight` | `1.3` | 제목·한 줄 UI 요소 |
| `--tracking-body` | `-0.01em` | 한글 시스템 고딕은 기본 자간이 넓어 약간 좁힘. 보조 텍스트는 `0` |
| `--paragraph-gap` | `var(--space-4)` (16px) | 단락 사이 간격, 약 1줄 |

마크다운 제목 4단계는 `--text-lg`/`--text-base` + 굵기(600)로 구분해 크기 단계를 늘리지 않는다.

## 3. 간격 (4px 배수 8단계)

| 토큰 | 값 | 주 용도 |
|------|-----|--------|
| `--space-1` | `4px` | 아이콘과 글자 사이 |
| `--space-2` | `8px` | 버튼 안쪽 세로, 목록 항목 간 |
| `--space-3` | `12px` | 버튼 안쪽 가로, 메시지 블록 안쪽 |
| `--space-4` | `16px` | 단락 간격, 모바일 좌우 여백 |
| `--space-5` | `20px` | 카드 안쪽 |
| `--space-6` | `24px` | 메시지 사이 |
| `--space-7` | `32px` | 구역 사이 |
| `--space-8` | `48px` | 화면 상하 여백, 빈 화면 안내 |

## 4. 반경·그림자

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--radius-sm` | `6px` | 인라인 코드, 배지, 작은 버튼 |
| `--radius-md` | `12px` | 코드 블록, 카드, 목록 항목 |
| `--radius-lg` | `24px` | 사용자 메시지 블록, 입력창 |
| `--shadow-overlay` | 라이트 `0 4px 16px rgb(0 0 0 / 0.08)`, 다크 `0 4px 16px rgb(0 0 0 / 0.4)` | Drawer·메뉴처럼 떠 있는 요소에만 |

## 5. 레이아웃

| 토큰 | 값 | 근거 |
|------|-----|------|
| `--sidebar-width` | `260px` | 기존 목록 폭 유지, 제목 한 줄 약 16자 |
| `--content-max` | `768px` | 720~800 범위 중앙. 16px 본문 기준 한 줄 약 45~50자(한글) |
| `--input-min-h` | `52px` | 한 줄 + 안쪽 여백 |
| `--composer-max-lines` | `6` | 입력창 최대 줄 수, 높이는 `줄 수 × 1lh + 여백` |
| `--header-h` | `56px` | 대화 제목·상태 배지 한 줄 |

Drawer 분기점은 `768px`(미디어 쿼리 값이라 토큰 아님).

## 6. 전환

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--duration-fast` | `150ms` | hover, 포커스, 버튼 상태 |
| `--duration-base` | `250ms` | 사이드 패널 접기, Drawer 열기, 구역 펼치기 |
| `--ease` | `cubic-bezier(0.2, 0, 0, 1)` | 감속 곡선 하나만 |

`prefers-reduced-motion: reduce`에서는 두 시간 토큰을 `0ms`로 바꾼다. 컴포넌트는 그대로.

## 7. 적용 형태 (확인 후 `style.css` 맨 위)

```css
:root {
  color-scheme: light dark;
  --color-bg: #ffffff; --color-surface: #f9f9f9; --color-user-bubble: #f4f4f4;
  --color-text: #0d0d0d; --color-text-muted: #5d5d5d; --color-border: #e5e5e5;
  --color-accent: <선택값>; --color-accent-contrast: #ffffff; --color-danger: #c62828;
  --shadow-overlay: 0 4px 16px rgb(0 0 0 / 0.08);
  /* 글꼴·간격·반경·레이아웃·전환은 모드 공통 */
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #212121; --color-surface: #171717; --color-user-bubble: #303030;
    --color-text: #ececec; --color-text-muted: #b4b4b4; --color-border: #3a3a3a;
    --color-accent: <선택값>; --color-accent-contrast: #0d0d0d; --color-danger: #ff8a80;
    --shadow-overlay: 0 4px 16px rgb(0 0 0 / 0.4);
  }
}
@media (prefers-reduced-motion: reduce) {
  :root { --duration-fast: 0ms; --duration-base: 0ms; }
}
```

## 8. 사용자 확인 필요

1. 강조색 A·B·C 중 하나 (추천 B)
2. 그 밖의 값은 바꿀 것이 있으면 알려주면 그대로 반영

## 9. 확정 후 추가 토큰

| 토큰 | 라이트 | 다크 | 대비(배경 / surface) | 용도 |
|------|-------|------|---------------------|------|
| `--color-focus` | `#2563eb` | `#6ea8fe` | 5.17 / 6.67 (3:1 기준) | 포커스 윤곽선 |
| `--color-ok` | `#1b7f3b` | `#6fdc8c` | 5.07 / 9.43 | 연결됨·채택 상태 |
| `--color-warn` | `#8a5a00` | `#f0c050` | 5.93 / 9.48 | 저하·보류·신규 퍼널 단계 |
| `--chart-1` | `#2563eb` | `#6ea8fe` | 5.17·4.91 / 6.67·7.42 | 차트 시리즈 1 |
| `--chart-2` | `#c2410c` | `#fb923c` | 5.18·4.92 / 7.11·7.92 | 차트 시리즈 2 |
| `--chart-3` | `#0f766e` | `#2dd4bf` | 5.47·5.20 / 8.65·9.63 | 차트 시리즈 3 |
| `--chart-4` | `#7c3aed` | `#c4b5fd` | 5.70·5.41 / 8.72·9.71 | 차트 시리즈 4 |
| `--chart-grid` | `--color-border` | `--color-border` | 장식 | 격자선 |

차트 시리즈는 모두 3:1 기준을 4.5:1 이상으로 넘는다. 시리즈 색은 색상환에서 떨어진 파랑·주황·청록·보라로 골라 색각 이상에서도 명도 차이로 구분된다.
