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
| B9 LLM SDK 전환 | 완료(실키 미검증) | 동일 | LLM: anthropic SDK tool runner / openai-agents, 가짜 HTTP 전송으로 두 런타임 검증. 실제 키 호출 미검증(T073) | `checks/check_b6.py`, `checks/check_b7.py` | LangChain 제거. anthropic SDK는 httpx2를 써서 검사 전송은 httpx2.MockTransport |

## 005 대화 전체 내보내기

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| E2 내보내기 기록 | 완료 | 동일 | 외부 호출 없음(fake·real 같음) | `checks/check_b11.py` | `POST /api/conversations/{id}/exports` → 201. 테이블 `conversation_exports` 신규(CREATE IF NOT EXISTS, 마이그레이션 없음). 대화 삭제 시 CASCADE. 회귀 check_b2·b3 통과 |

## 006 Amplitude 서버 고정 인증

| 모듈 | 상태 | 실행 | 연동 상태 | 검사 | 비고 |
|------|------|------|----------|------|------|
| A1 REST·사전 점검·상태 | 완료(실제 키 미검증) | 동일. 실제 모드는 env `AMPLITUDE_API_KEY`·`AMPLITUDE_SECRET_KEY` 필요 | Amplitude: REST 코드 완료, 검사는 httpx.MockTransport. 실제 키 호출 미검증(Taxonomy 응답 필드 이름 포함, 사람·키 필요). LLM: 가짜 전송으로 두 런타임 확인 | `checks/check_b12.py` (b7 삭제) | MCP·OAuth 코드와 connect/callback 제거, `mcp` 직접 의존성 제거(openai-agents 경유로 설치는 남음). `llm_mock.sse`는 기본 `skipAmplitude: true`. OpenAI 런타임은 도구 실패 문장을 모델에 그대로 전달하도록 `failure_error_function` 지정(SDK 기본은 고정 문장이라 인자 오류를 모델이 고칠 수 없었음) |
