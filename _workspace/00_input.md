# 입력 — 2026-10-15

- PRD: `docs/prd/PRD-kbap-pm-agent.md`
- 레포 구조: `frontend/` (GitHub Pages 정적), `backend/` (홈서버 Docker + MySQL)
- 백엔드 스택: **Python 확정 (2026-10-15 사용자 확인).** 당초 CTO 판단에 위임, 후보: 사용자가 올린 후보 두 가지:
  1. Python + LangChain (에이전트 생태계 성숙)
  2. Spring AI (Java/Kotlin, 팀의 기존 K-Bap 백엔드와 같은 생태계일 가능성)
- 프론트 스택: **TypeScript 확정 (2026-10-15 사용자 확인).** React+Vite는 CTO 결정
- 참고용 형제 레포 (읽기만, 팀의 기존 숙련도 파악): `../kbap/`, `../kbap-fe/`, `../kbap-langchain/`, `../kbap-admin/`
- 사용자 지시: "우선 빠르게 동작하는 프로토타입. 디테일은 나중에."

## 005 대화 전체 내보내기 (2026-10-17)
- PRD: docs/prd/PRD-conversation-export.md (PR #17 머지)
- 브랜치: feat/conversation-export (main 작업 트리)
- 사용자 지시: Spec Kit(specify→plan→tasks) → 구현 → PR까지 중간 확인 없이 진행
- 범위: 프론트 중심. 인쇄용 스타일 + 내보내기 버튼(PDF/Markdown). 백엔드는 내보내기 기록용 최소 변경만 허용(없어도 됨, CTO 결정)

## 006 Amplitude 서버 고정 인증 (2026-10-17)
- PRD: docs/prd/PRD-amplitude-server-auth.md (PR #19 머지)
- 브랜치: feat/amplitude-rest (main 작업 트리)
- 사용자 지시: Spec Kit → 구현 → PR까지 중간 확인 없이 진행
- 범위: 백엔드 중심. MCP OAuth 경로 제거 → Dashboard REST(세그멘테이션·퍼널·리텐션)+Taxonomy API 프로젝트 키. 실행 전 사전 점검·거절. 프론트는 설정 화면 정리 + 거절 안내.
- 운영 확인 사실: MCP 토큰 만료 24h·갱신 토큰 없음·scope all:read all:write. 3일 호출 102건 = query_amplitude_data 86(실패 17 정의 오류) + get_amplitude_context 16. 커스텀 이벤트 0개, REST는 ce: 접두어. 세그멘테이션 n=any|active, 퍼널 n=new|active. 형제 레포 ../kbap-amplitude/amp.py(302줄) 참고 가능.
