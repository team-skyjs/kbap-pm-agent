# 03 QA — 결함 누적 기록

기준: `_workspace/01_cto_api-contract.md` v1.1. 형식: `integration-qa` 스킬 3절.

## 모듈 검증 로그

| 날짜 | 모듈 | 결과 | 비고 |
|---|---|---|---|
| 2026-10-15 | F1 (b27c4ce) | 단독 통과 | `npm run check -- f1` OK, build 자산 경로 `/kbap-pm-agent/`, preview `/kbap-pm-agent/` 200. 실제 B1 왕복·CORS는 T013에서 확인 |
| 2026-10-15 | B1 (1202053) + T013 F1↔B1 | 통과 | `check_b1.py` OK. 실서버 curl: health 키·값 일치, `/api/nope` 404 공통 형식, DB 중단 시 200 degraded, PATCH preflight 허용, 401 `UNAUTHORIZED`(Origin 있으면 CORS 헤더 포함), 토큰 일치 시 404, callback 비인증. headless Chrome: dev(5173)·빌드본 preview 모두 배지 "ok", 백엔드 중단 시 "연결 실패", 해시 `#/settings` 동작. 참고(결함 아님): preview 출처 4173은 기본 `CORS_ORIGINS`에 없어 `CORS_ORIGINS=http://localhost:5173,http://localhost:4173`로 띄워야 한다. 405는 404 `NOT_FOUND`로 응답(계약에 405 코드 없음, 수용) |
| 2026-10-15 | B2 (6b60fd1) T018 | 통과 | `check_b2.py` OK. 실서버 33항목: 계약서 원문 JSON과 키 단위 일치(Summary·상세·Proposal·PATCH 응답·목록 items), null 규칙, 201, 시각 `.mmmZ`, title 0/201자·숫자·깨진 JSON 400, 상세 메시지 순서·user usage null·usage는 purpose=agent만 합산, PATCH note 생략 유지·null 삭제·pending 시 decidedAt null, 400/404 코드, DB enum `adopted`. 참고: MySQL JSON 컬럼이 evidence·measurement 키 순서를 바꿔 내보낸다(값 동일, 계약은 키 순서를 규정하지 않음) |
| 2026-10-15 | F2 (68ffe70)·F4 (dbb9f7d) ↔ B2 | 부분 통과 | headless Chrome 실서버: 목록 수·"새 대화"·제안/채택 수, 카드 4영역 순서, evidence 3종, 퍼널 신규 위치 `src/app/scan.tsx · handleRetry · 398`, 채택 PATCH 본문 계약 일치, 새로고침 유지, 보류→미결정 decidedAt null, 없는 대화 에러 표시. `npm run check` f1~f5 OK. 남은 것: 제목 자동 채움(T045)·fake 제안 카드(T030)·SSE(T026)는 B3 후 |

## 결함

(없음)
