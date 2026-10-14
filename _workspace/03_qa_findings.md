# 03 QA — 결함 누적 기록

기준: `_workspace/01_cto_api-contract.md` v1.1. 형식: `integration-qa` 스킬 3절.

## 모듈 검증 로그

| 날짜 | 모듈 | 결과 | 비고 |
|---|---|---|---|
| 2026-10-15 | F1 (b27c4ce) | 단독 통과 | `npm run check -- f1` OK, build 자산 경로 `/kbap-pm-agent/`, preview `/kbap-pm-agent/` 200. 실제 B1 왕복·CORS는 T013에서 확인 |
| 2026-10-15 | B1 (1202053) + T013 F1↔B1 | 통과 | `check_b1.py` OK. 실서버 curl: health 키·값 일치, `/api/nope` 404 공통 형식, DB 중단 시 200 degraded, PATCH preflight 허용, 401 `UNAUTHORIZED`(Origin 있으면 CORS 헤더 포함), 토큰 일치 시 404, callback 비인증. headless Chrome: dev(5173)·빌드본 preview 모두 배지 "ok", 백엔드 중단 시 "연결 실패", 해시 `#/settings` 동작. 참고(결함 아님): preview 출처 4173은 기본 `CORS_ORIGINS`에 없어 `CORS_ORIGINS=http://localhost:5173,http://localhost:4173`로 띄워야 한다. 405는 404 `NOT_FOUND`로 응답(계약에 405 코드 없음, 수용) |
| 2026-10-15 | B2 (6b60fd1) T018 | 통과 | `check_b2.py` OK. 실서버 33항목: 계약서 원문 JSON과 키 단위 일치(Summary·상세·Proposal·PATCH 응답·목록 items), null 규칙, 201, 시각 `.mmmZ`, title 0/201자·숫자·깨진 JSON 400, 상세 메시지 순서·user usage null·usage는 purpose=agent만 합산, PATCH note 생략 유지·null 삭제·pending 시 decidedAt null, 400/404 코드, DB enum `adopted`. 참고: MySQL JSON 컬럼이 evidence·measurement 키 순서를 바꿔 내보낸다(값 동일, 계약은 키 순서를 규정하지 않음) |
| 2026-10-15 | F2 (68ffe70)·F4 (dbb9f7d) ↔ B2 | 부분 통과 | headless Chrome 실서버: 목록 수·"새 대화"·제안/채택 수, 카드 4영역 순서, evidence 3종, 퍼널 신규 위치 `src/app/scan.tsx · handleRetry · 398`, 채택 PATCH 본문 계약 일치, 새로고침 유지, 보류→미결정 decidedAt null, 없는 대화 에러 표시. `npm run check` f1~f5 OK. 남은 것: 제목 자동 채움(T045)·fake 제안 카드(T030)·SSE(T026)는 B3 후 |
| 2026-10-15 | B3 (6b82ef0) T022 | 통과 | `check_b3.py` OK. 실서버 SSE 원문: 헤더 `text/event-stream`·`no-cache`·`X-Accel-Buffering: no`, 블록마다 event 1줄+data 1줄+빈 줄, 순서 message_created→(tool_call,tool_result)×2→final, 각 data 키 = 계약 예시(ToolCall·Message·Proposal, `input`은 도구별 자유 형식), final = GET 상세, 제목 앞 40자, usage.costUsd 0, 스트림 전 400(0자·4001자·누락)/404/409 JSON, running 상세 필드 규칙, 끊김 → failed/INTERNAL_ERROR 후 재전송 가능, 대기 15초마다 `: ping` |
| 2026-10-15 | F3·F4·F2 ↔ B3 (T026·T030·T045) | F4·F2 통과, F3 결함 1 | headless Chrome 실서버 fake: 첫 진행 표시 0.74s(SC-004), 진행 문구 택사노미→코드 전환, final 후 카드 2장 4영역 순서·퍼널 기존/신규·위치, 채택 후 새로고침 유지·목록 채택 1, 목록 제목 앞 40자, 409 안내 + 상세 재조회 + 3초 폴링으로 타 클라이언트 실행 반영. 결함 QA-1 |

## 결함

### QA-1: 첫 메시지 전송 후 채팅 헤더 제목이 새로고침 전까지 "새 대화"로 남는다
- 모듈: frontend / F3 (T024)
- 경계면: POST /api/conversations/{id}/messages 응답 이후 화면 상태
- 기대: 계약서 ConversationSummary "`title`: 생성 시 지정하지 않으면 `null`. 첫 사용자 메시지가 저장될 때 앞 40자로 채운다." 서버는 message_created 시점에 이미 제목을 채운다(GET 상세 `title` = 앞 40자 확인). 같은 화면의 왼쪽 목록은 재조회로 새 제목을 보여준다
- 실제: `frontend/src/Chat.tsx` `<h3>{detail.title ?? '새 대화'}</h3>`의 `detail.title`은 최초 GET 값(null) 그대로. onEvent는 messages만 갱신하고 final·스트림 종료 후 상세를 다시 읽지 않는다. 재현: 새 대화 → 질문 전송 → final 후 헤더 "새 대화", 새로고침하면 "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘 — 제목 자동"
- 수정 방향: 프론트. final(또는 스트림 종료) 뒤 `load()`로 상세를 다시 읽거나, title이 null이면 message_created 때 userMessage.content 앞 40자로 채운다(서버 규칙 복제보다 재조회 권장)
- 수신: frontend-dev
- 상태: 열림
