# 02 Frontend progress

실행: `cd frontend && npm ci && VITE_API_BASE_URL=http://localhost:8000 npm run dev` → http://localhost:5173/kbap-pm-agent/
백엔드 없이 띄우려면 백엔드를 `AGENT_MODE=fake`(기본)로 띄운다. 프론트 mock은 모든 B 모듈 연동 후 삭제했다.
검사: `npm run check -- f<N>` (tsc --noEmit 후 tsx로 checks/check-f<N>.ts). 인자 없으면 f1~f5 전부. f6은 `VITE_API_BASE_URL=... npm run build && VITE_API_BASE_URL=... npm run check -- f6`.
검사는 specs/001-pm-agent-prototype/contracts/*.md 코드 블록을 원문 그대로 읽어 파서에 넣는다(checks/contract.ts).

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| F1 뼈대+헬스 | 완료 | npm run dev | health: 실제(B1) | check-f1 | b27c4ce, QA 통과 |
| F3 채팅 | 완료 | 동일 | 대화 생성·상세·SSE: 실제(B2·B3 fake 모드)로 확인 | check-f3 | 6fc9ddf |
| F4 제안 카드 | 완료 | 동일 | PATCH: 실제(B2) 확인 | check-f4 | dbb9f7d |
| F2 대화 목록 | 완료 | 동일 | 목록: 실제(B2) 확인 | check-f2 | 68ffe70 |
| F5 설정 | 완료 | 동일 | settings·저장소·sync·택사노미: 실제(B4 fake) 확인, Amplitude connect: 실제(B7 fake) 확인 | check-f5 | f08981f |
| F6 Pages 배포 | 완료(로컬) | .github/workflows/pages.yml | 운영 URL 왕복은 B8 대기 | check-f6 | 70c56b4. 레포 Variables에 VITE_API_BASE_URL 필요, Pages source = GitHub Actions |

## 005 대화 내보내기 (feat/conversation-export)

실행: `cd frontend && npm run dev`, 대화 상단 바 "내보내기" → PDF로 인쇄 / Markdown 파일. 검사: `npm run check -- f10`, `npm run check:ui`(us13 포함).

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| E1 내보내기(버튼·인쇄·Markdown·기록 호출) | 완료 | 대화 상단 바 | 기록 호출: 고정 응답(백엔드 기록 엔드포인트 완료 전) | check-f10, us13 | 인쇄 머리글은 제목·날짜만. Markdown은 화면 대화 상세로만 생성 |

## 006 Amplitude 서버 고정 인증 (feat/amplitude-rest)

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| A2 설정 상태·전송 거절 안내 | 완료 | 설정 화면, 대화 전송 | 고정 응답(백엔드 A1 완료 뒤 fake 왕복 확인 예정) | check-f3(503 예시), check-f5(설정 v1.5), us14 | OAuth 연결 버튼·폴링 삭제, "Amplitude 없이 진행" 재전송 |
