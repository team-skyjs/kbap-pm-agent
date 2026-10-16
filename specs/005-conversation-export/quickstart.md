# Quickstart: 대화 전체 내보내기

```bash
docker compose up -d --build        # 레포 루트: backend(fake) + mysql. conversation_exports 테이블 자동 생성
cd frontend && npm run dev          # http://localhost:5173
```

## 시나리오

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | 새 대화(메시지 0) | "내보내기" 비활성 | FR-001 |
| 2 | fake 질문 3~4번으로 화면보다 긴 대화를 만들고 내보내기 → PDF | Chrome 인쇄 미리보기에 첫 메시지부터 끝까지, 제안 카드 네 절 펼침, 차트 그림, 사이드바·입력창 없음 | US1, SC-001 |
| 3 | 시스템 다크 테마로 2 반복 | 미리보기가 흰 배경·밝은 글자·밝은 차트 | US1-4 |
| 4 | 인쇄 대화상자 취소 | 화면 카드 접힘·차트 크기·색이 원래대로 | US1-2·3 |
| 5 | 내보내기 → Markdown | `{제목}-YYYYMMDD.md` 내려받기, contracts/export-markdown.md 규격과 일치 | US2 |
| 6 | `SELECT format, COUNT(*) FROM conversation_exports GROUP BY format` | 2·3에서 pdf 2, 5에서 markdown 1 | US3, SC-003 |

## 검사

```bash
cd frontend && npm run check && npx playwright test checks/ui/us13.spec.ts
cd backend && uv run python checks/check_b11.py      # 백엔드 검사는 순차 실행(공유 검사 DB)
```
