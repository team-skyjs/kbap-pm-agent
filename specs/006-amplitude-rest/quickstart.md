# Quickstart: Amplitude 서버 고정 인증

```bash
docker compose up -d --build        # 레포 루트. 기동 시 messages.amplitude_status 추가, 이전 OAuth 설정 행 삭제
cd frontend && npm run dev
```

## 시나리오

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | 키 없이(real 모드, Amplitude 키 비움) 질문 | 503 `AMPLITUDE_UNAVAILABLE` "키가 설정되어 있지 않습니다" 안내, `llm_usage` 행 0, 메시지 저장 없음, 입력값 유지 | US2-1·5, SC-003 |
| 2 | 1의 안내에서 "Amplitude 없이 진행" | 답이 오고 본문에 Amplitude를 쓰지 않았다고 적힘, `amplitude_status='skipped'` | US2-4, US4-2 |
| 3 | 설정 화면(키 없음 / 있음) | "키 없음" / "서버 키로 연결됨", 연결 버튼 없음 | US3 |
| 4 | 실제 키로 퍼널·세그멘테이션·리텐션·이벤트 맥락 질문 각 1회 | 도구 성공, 수치 근거, `amplitude_status='used'` | US1, SC-004 (미검증·사람) |
| 5 | data-model.md 상태 조회 SQL | 2·4의 건수 | US4, SC-002 |

## 검사

```bash
cd backend && uv run python checks/check_b12.py      # 순차 실행(공유 검사 DB)
cd frontend && npm run check && npm run check:ui
```
