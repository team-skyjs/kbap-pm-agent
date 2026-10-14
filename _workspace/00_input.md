# 입력 — 2026-10-15

- PRD: `docs/prd/PRD-kbap-pm-agent.md`
- 레포 구조: `frontend/` (GitHub Pages 정적), `backend/` (홈서버 Docker + MySQL)
- 백엔드 스택: **Python 확정 (2026-10-15 사용자 확인).** 당초 CTO 판단에 위임, 후보: 사용자가 올린 후보 두 가지:
  1. Python + LangChain (에이전트 생태계 성숙)
  2. Spring AI (Java/Kotlin, 팀의 기존 K-Bap 백엔드와 같은 생태계일 가능성)
- 프론트 스택: **TypeScript 확정 (2026-10-15 사용자 확인).** React+Vite는 CTO 결정
- 참고용 형제 레포 (읽기만, 팀의 기존 숙련도 파악): `../kbap/`, `../kbap-fe/`, `../kbap-langchain/`, `../kbap-admin/`
- 사용자 지시: "우선 빠르게 동작하는 프로토타입. 디테일은 나중에."
