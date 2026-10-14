# 사이드 패널 설계 (US-003)

## 레이아웃
최상단 브랜드와 [새 대화] 버튼, 그 아래 대화 목록(최근순, 패널 안 스크롤), 하단 고정 설정 링크.

## 항목
- 제목 한 줄 말줄임(`text-overflow: ellipsis`), 전체 제목은 `title` 속성
- 둘째 줄 보조 텍스트: "제안 N · 채택 M" (기존 API 값 그대로), 날짜는 `title` 속성으로 이동
- 현재 대화: `--color-bg-user` 배경 + `aria-current="page"`

## 상태 (모든 항목·버튼 공통)
| 상태 | 표현 |
|------|------|
| hover | `--hover` 배경 |
| focus-visible | `--focus-ring` |
| active | `--color-bg-user` 배경 |
| disabled | 투명도 0.5, 커서 기본 |

## 접근성
링크 목록이라 Tab으로 이동·Enter로 선택. 방향키 이동은 넣지 않음(목록 링크 표준 동작으로 충분).
