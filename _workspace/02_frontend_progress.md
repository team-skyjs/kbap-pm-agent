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

## 002 접근 제한 (feat/access-gate-resume)

실행: `docker compose up -d --build` → http://localhost:8000 (백엔드 컨테이너가 빌드된 프론트를 `/`에서 정적 서빙, 같은 출처 /api). 개발: `cd frontend && npm run dev` (5173, /api → localhost:8000 프록시)

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| G1 같은 출처 | 완료 | compose backend :8000 (정적 서빙) | 실제(fake 모드) | deploy/checks/check_g1.sh, npm run check -- f6 | 0b8ff91(pages.yml 삭제 포함), 8a8e311(nginx 웹 컨테이너 제거, 검사 대상 8000) |
| G2 세션 만료 구분 | 완료 | 동일 | 실제 + 가짜 접근 계층(401 HTML) 브라우저 확인 | npm run check -- g2 | c1b2f4e |
