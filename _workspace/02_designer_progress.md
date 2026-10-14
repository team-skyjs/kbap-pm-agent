# frontend-designer 진행 (003 프론트 재설계)

## 화면별 상태
| 스토리 | 상태 | 비고 |
|-------|------|------|
| US-001 디자인 토큰 | 적용 완료 | 강조색 B(파랑) 확정. `style.css` `:root` + 다크 + reduced-motion |
| US-002 앱 셸 | 구현 완료 | 사이드 패널 접기(localStorage), 768px 이하 Drawer(ESC·배경 탭·스크롤 잠금), 하단 고정 입력창. 설계 `04_designer_shell.md` |
| US-003 사이드 패널 | 구현 완료 | 새 대화 최상단, 제목 한 줄 말줄임, 제안·채택 수, 설정 하단 고정, aria-current. 설계 `04_designer_sidebar.md` |
| US-005 마크다운 표현 | 구현 완료 | 제목·목록·작업 목록·인용·구분선·표·코드 블록 스타일, Chat·ProposalCard 렌더러 연결 |
| US-007 입력창 | 구현 완료 | Enter 전송·Shift+Enter 줄바꿈·한글 조합 중 미전송, 최대 6줄 자동 높이, 안내 줄 높이 예약 |
| US-008 상태 | 구현 완료 | `viewState()`로 전송 직후·진행·완료·부분 완료·오류 판정, 세션 만료 배너는 `SESSION_EXPIRED` 코드에만(접근 제한 머지 후 동작). 401 토큰 오류는 입력창 아래 안내만 |
| US-009 제안 카드 | 구현 완료 | 접는 구역 넷(제안만 펼침), 근거·퍼널 라벨, 상태 라벨, 결정 버튼 오른쪽. 설계 `04_designer_proposal.md` |
| US-010 설정 | 구현 완료 | 구역 여백·상태 라벨·입력 라벨, 인라인 style 제거. 설계 `04_designer_settings.md` |
| US-011 접근성 | 자체 점검 통과 | axe 심각·중대 0(라이트·다크 × 1280·375 × 채팅·카드 펼침·Drawer·설정), Drawer 포커스 가두기·복귀 |
| US-004 메시지 | 구현 완료 | 사용자만 오른쪽 배경 블록, AI 배경 없음, 역할 라벨은 스크린리더 전용. 설계 `04_designer_messages.md` |

## 토큰 변경 (제안서 대비)
| 이름 | 값 (라이트 / 다크) | 이유 |
|------|-------------------|------|
| `--color-accent` | `#2563eb` / `#6ea8fe` | 사용자 선택 B |
| `--color-ok` | `#1b7f3b` / `#6fdc8c` | 상태 배지·채택 카드. 배경 대비 5.07 / 9.43 |
| `--color-warn` | `#8a5a00` / `#f0c050` | 저하 배지·보류 카드·신규 퍼널 행. 배경 대비 5.93 / 9.48 |
| `--tint` | `12%` | 상태 배경 = 의미 색 12% + 본문 배경. 그 위 본문 글자 대비 16.0 이상 / 10.4 이상 |
| `--hover` | 본문색 6% | hover 배경 공통 |
| `--focus-ring`, `--focus-offset` | `2px solid accent`, `2px` | 포커스 윤곽선 공통 |
| `--viewport-h` | `100dvh` | 앱 셸 전체 높이. 모바일 주소창 높이 변화 반영 |
| `--text-code` | `0.9em` | 인라인 코드 크기(주변 글자 기준) |
| `--input-grow-basis` | `240px` | 폼 입력 줄의 기본 폭, 좁으면 줄바꿈 |

## 토큰 이름 정렬 (data-model.md 1절)
`--color-bg-user`→`--color-user-bubble`, `--color-on-accent`→`--color-accent-contrast`, `--leading`→`--leading-body`, `--tracking`→`--tracking-body`, `--shadow-sm`→`--shadow-overlay`, `--sidebar-w`→`--sidebar-width`, `--content-max-w`→`--content-max`, `--dur-*`→`--duration-*`, `--input-max-h`→`--composer-max-lines`(6). 추가: `--color-focus`, `--chart-1`~`4`, `--chart-grid`, `--chart-h`(280px, 차트 높이 예약).

## 미결
- `SettingsPage.tsx`의 인라인 폭(`flex: 0 0 160px`)은 설정 화면 재스타일 때 클래스로 옮김(공동 파일이라 지금은 미수정)
- 세션 만료 배너를 api.ts 이벤트에 연결하는 일은 접근 제한 PR 몫
- 차트 폭: ChartBlock의 비율 고정 해제를 frontend-dev에 요청
