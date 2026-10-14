# 메시지 표현 설계 (US-004)

## 구분 방식 (하나만)
- 사용자: 오른쪽 정렬, `--color-bg-user` 배경, `--radius-lg`, 최대 폭 80%
- AI: 왼쪽 정렬, 배경 없음, 아바타 없음, 스레드 전체 폭
- "나/에이전트" 라벨은 화면에서 숨기고 스크린리더 전용으로 유지. 시각은 `title` 속성

## 타이포
본문 `--text-base`/`--leading`/`--tracking`, 단락 간격 `--paragraph-gap`, 메시지 사이 `--space-6`.
사용량 줄·도구 호출은 `--text-sm` 보조 텍스트.

## 넘침
- 긴 단어·URL: `overflow-wrap: anywhere`
- 코드·표: 블록 안 가로 스크롤(`overflow-x: auto`), 메시지 자체는 넘치지 않음(`min-width: 0`)
