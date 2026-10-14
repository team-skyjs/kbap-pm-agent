# 02 Backend Progress

실행: 레포 루트 `docker compose up -d --build` → backend :8000, mysql :3307 (기본 `AGENT_MODE=fake`).
검사: `docker compose exec backend uv run python checks/check_bN.py` (검사는 `<DB>_check` 별도 DB를 쓴다. 개발 DB를 건드리지 않음)

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| B1 뼈대+헬스 | 완료 | `docker compose up -d --build` | - | `checks/check_b1.py` | QA 대기 |
| B2 대화·제안 | 완료 | 동일 | - | `checks/check_b2.py` | QA 대기. 계약 예시 원문은 `checks/examples.py` |
| B3 메시지 SSE (fake) | 완료 | 동일 | LLM·Amplitude·GitHub: fake | `checks/check_b3.py` | QA 대기. fake도 llm_usage에 0원 행을 남김(usage 객체·호출 횟수 검사용) |
| B4 저장소·택사노미 | 완료(QA-2 수정) | 동일 | GitHub: real 모드 실제 클론(file:// 검증), fake는 예시 값 | `checks/check_b4.py` (컨테이너) | QA 대기. 실제 kbap-fe 클론은 GITHUB_TOKEN 필요(미검증). codeMapStatus는 B5에서 building→ready |
| B5 코드 도구·요약 캐시·예산 | 완료 | 동일 | 요약 LLM: real 모드에서 CODE_SUMMARY_MODEL (미검증, 키 없음). fake는 0원 기록 | `checks/check_b5.py` (컨테이너) | QA 대기. 요약 캐시는 REPOS_DIR/summaries.json (path@blob) |
| B6 실제 에이전트 | 완료(실제 LLM 미검증) | AGENT_MODE=real + ANTHROPIC_API_KEY | LLM: real 코드 완료, 키 없어 실호출 미검증. 루프는 가짜 채팅 모델로 검증 | `checks/check_b6.py` | create_agent + ProviderStrategy(AgentAnswer). ToolStrategy는 tool_choice any 강제라 최신 Claude에서 400 |
| B7 Amplitude MCP | 완료(승인 흐름 미검증) | 동일 | Amplitude real: 동적 등록·승인 URL 생성까지 실서버 확인. 브라우저 승인→토큰 교환→list_tools는 사람 필요(미검증). fake: 예시 URL·즉시 connected | `checks/check_b7.py` | 토큰은 app_settings amplitude_oauth |
| B8 배포 | 완료(운영 미배포) | `./deploy/push-and-deploy.sh` | 홈서버 접근·Docker Hub 푸시는 사람 필요 | `checks/check_b8.py` (PUBLIC_BASE_URL 대상) | 로컬 uvicorn으로 health·github.io preflight·SSE 105초 유지 확인. R4 홈서버 확인은 미실행(deploy/README.md) |
