# Research: PM Agent 프로토타입

Technical Context에 NEEDS CLARIFICATION은 없다. 이 문서는 ADR 중 상태가 "가정"인 항목을 언제, 어떻게 검증하고, 틀렸을 때 무엇으로 갈아타는지 적는다. 확정 ADR의 근거는 `_workspace/01_cto_tech-decisions.md` 0절(형제 레포 조사)에 있다.

## R1. Amplitude MCP OAuth 동적 클라이언트 등록 (ADR-3)

- Decision: MCP Python SDK `OAuthClientProvider`로 동적 클라이언트 등록 → 승인 코드(PKCE) 흐름을 쓴다. 토큰은 `app_settings`에 둔다.
- Rationale: Amplitude 공식 문서는 원격 MCP가 OAuth만 받는다고 밝힌다(API 키 클라이언트는 연결 불가). 동적 등록 지원은 서드파티 Nango 문서로만 확인했다.
- Alternatives considered: Amplitude Dashboard REST API 직접 호출(`../kbap-amplitude/amp.py` 재사용).
- **검증 방법**: B7 첫 태스크로 확인한다. 로컬에서 `PUBLIC_BASE_URL=http://localhost:8000`으로 `POST /api/integrations/amplitude/connect`를 부른다. 받은 URL을 브라우저로 승인하고 콜백 뒤 MCP `list_tools`가 도구 목록을 돌려주면 통과다. 컨테이너를 재시작한 뒤 `list_tools`를 다시 성공시켜 토큰 영속화도 확인한다.
- **틀리면**: 동적 등록이 거부되면 Amplitude 앱 등록으로 받은 고정 client_id를 `AMPLITUDE_OAUTH_CLIENT_ID`로 넣는다. MCP 자체가 막히면 `amp.py`를 `source: "amplitude"` 도구로 감싼다. 둘 다 계약 변경은 없다.

## R2. 공개 도메인 (ADR-6)

- Decision: cloudflared 터널 호스트명은 환경변수 `PUBLIC_BASE_URL`(백엔드)과 `VITE_API_BASE_URL`(프론트)로만 쓴다. 예시는 `https://pm-agent-api.simhani1.dev`다.
- **검증 방법**: B8에서 실제 호스트명으로 `curl https://<호스트>/api/health`를 실행해 200을 확인한다. 같은 호스트로 OAuth 콜백을 승인해 본다(Amplitude가 redirect_uri로 받아들이는지).
- **틀리면**: 값만 바꾼다. 코드 변경은 없다.

## R3. 공유 접근 토큰 (ADR-7)

- Decision: `ACCESS_TOKEN`이 비어 있지 않을 때만 Bearer를 검사한다.
- **검증 방법**: B1 검사 스크립트에서 두 경우를 확인한다. 토큰을 설정하면 `/api/health`는 200, 정의되지 않은 경로(예: `/api/nope`)는 401 `UNAUTHORIZED`여야 한다(인증이 라우팅보다 먼저다). 토큰을 비우면 health는 200, 같은 경로는 404 `NOT_FOUND`여야 한다. B8에서는 사용자에게 운영에서 켤지 묻는다.
- **틀리면**: 필요 없다는 결정이면 운영 env에서 값을 비운다. 코드는 그대로 둔다.

## R4. 배포 전제 (ADR-11)

- Decision: 레포 이름 `kbap-pm-agent`, Docker Hub `simhani1/kbap-pm-agent`, 홈서버의 기존 MySQL·cloudflared(`monitor-net`)를 재사용하고 호스트 포트는 8001로 둔다.
- **검증 방법**: B8 착수 전에 홈서버에서 다음을 확인한다. 명령 결과는 사람이 실행해 붙인다.
```bash
docker network ls | grep monitor-net
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'mysql|8001'
```
  GitHub 레포 이름은 Pages `base` 경로를 결정하므로 F1에서 확인한다.
- **틀리면**: 레포 이름이 다르면 `vite.config.ts`의 `base` 한 줄을 바꾼다. 포트·네트워크는 `deploy/` compose만 바꾼다.

## R5. 택사노미 JSON 형식 (ADR-12)

- Decision: 계약서 `PUT /api/settings/taxonomy` 본문 형식 하나만 받는다.
- **검증 방법**: 팀의 실제 택사노미 문서(스프레드시트나 Amplitude export)를 한 번 이 형식으로 바꿔 업로드한다. 변환이 수작업 30분을 넘으면 변환 스크립트를 따로 둘지 CTO가 판단한다(B4 QA 시점).
- **틀리면**: 변환 스크립트를 레포 밖 도구로 둔다. 계약은 유지한다.

## R6. 비공개 저장소 접근 (ADR-13)

- Decision: `GITHUB_TOKEN` fine-grained PAT(Contents read-only)로 HTTPS 클론한다.
- **검증 방법**: B4에서 `team-skyjs/kbap-fe`를 실제로 클론한다. 토큰을 빼고 동기화했을 때 응답이 `UPSTREAM_ERROR`이고, `repository.lastError`에 사유가 있으며, 응답·로그 어디에도 토큰 문자열이 없는지 확인한다(grep).
- **틀리면**: 조직 정책이 PAT를 막으면 GitHub App 설치 토큰으로 바꾼다. 클론 함수 하나만 바뀐다.

## R7. 반응형 모드만 (ADR-14)

- Decision: v1은 사용자 질문에만 반응한다.
- **검증 방법**: 출시 4주 차 회고에서 SC-001(채택 4건)을 본다. 채택이 적은 이유가 "질문을 안 해서"라면 다음 버전에 주간 실행을 추가한다.
- **틀리면**: 스케줄러가 `agent.py`의 실행 함수를 부르게 추가한다. 계약에는 영향이 없다.

## R8. LLM SDK 전환과 Amplitude MCP 연결 방식 (ADR-20)

- Decision: Amplitude MCP는 **(b) MCP Python SDK로 직접 연결**한다. OAuth는 기존 `OAuthClientProvider`(httpx.Auth)를 그대로 쓴다. Anthropic 런타임은 `anthropic.lib.tools.mcp.async_mcp_tool(t, session)`로 MCP 도구를 tool runner 도구로 바꾼다. OpenAI 런타임은 같은 provider를 `MCPServerStreamableHttp(params={"url": ..., "auth": provider})`에 넘긴다.
- Rationale:
  1. OpenAI 구현은 어차피 로컬 MCP 연결이 필요하다. (b)면 OAuth provider 하나를 두 런타임이 공유한다. (a)는 Anthropic 전용 연결 경로가 하나 더 생긴다.
  2. 토큰 갱신: MCP 커넥터의 `authorization_token`은 정적 Bearer 값이라 만료 전 갱신을 우리가 따로 해야 한다. `OAuthClientProvider`는 refresh를 스스로 처리한다.
  3. 진행 표시(FR-001, SC-004): (a)는 MCP 호출이 Anthropic 서버에서 일어나 응답 블록으로 사후에만 보인다. (b)는 도구가 로컬에서 실행돼 공통 래퍼가 `tool_call`/`tool_result`를 실시간으로 낸다.
  4. 실패 격리(FR-010, ADR-16): (b)는 MCP 예외를 로컬에서 잡아 `tool_result` `failed`로 보내고 실행을 계속한다. (a)의 서버 측 실패가 요청 전체 실패인지 블록 단위인지는 확인하지 않았다.
  5. (a)의 장점인 코드 감소는 SDK가 MCP 변환 헬퍼를 제공해 작다.
- Alternatives considered: (a) Anthropic MCP 커넥터(`mcp_servers=[{"type":"url","url","name","authorization_token"}]` + `tools=[{"type":"mcp_toolset","mcp_server_name"}]`, beta `mcp-client-2025-11-20`, Claude API에서 beta 제공). OpenAI 구현을 버리고 Anthropic만 남길 때 다시 검토한다.
- **확인한 사실** (2026-10-15)
  - **설치된 `anthropic` 1.13.0** (`backend/.venv`):
    - `beta.messages.tool_runner` 파라미터에 `output_format`, `output_config`, `thinking`, `cache_control`, `fallbacks`, `betas`, `max_iterations`, `mcp_servers`, `tool_choice`가 있다.
    - `anthropic/lib/tools/mcp.py`에 `mcp_tool`과 `mcp_content` 등이 있다. 비동기 `async_mcp_tool`은 claude-api 스킬 문서 기준이며, 설치본 이름은 구현 시 확인한다.
  - **claude-api 스킬**:
    - Tool Runner는 `@beta_tool`/`@beta_async_tool` + `client.beta.messages.tool_runner`다.
    - 구조화 출력은 `output_config.format`이고, Pydantic은 `messages.parse(output_format=...)`다.
    - 현행 모델(Sonnet 5.5, Opus 5.5, Fable 5.1)은 강제 `tool_choice` any/tool을 400으로 거부한다.
    - 사고는 `{"type": "adaptive"}`이고 Sonnet 5.5는 disabled가 400이다.
    - Sonnet 5.5는 서버 측 폴백 `fallbacks="default"`(beta `server-side-fallback-2026-07-01`)를 Claude API에서만 지원한다.
    - Python runner는 `pause_turn`을 자동 재개하지 않는다. 서버 도구를 쓰지 않으므로 해당 없다.
    - `stop_reason == "refusal"`은 본문을 읽기 전에 확인한다.
  - **OpenAI Agents SDK 문서**:
    - `MCPServerStreamableHttp(name, params={"url", "headers", "timeout", "auth", "httpx_client_factory"}, cache_tools_list, max_retry_attempts)`. `params["auth"]`는 설치된 `mcp` 메이저 버전에 맞는 `httpx.Auth`여야 한다(mcp 1.30 → httpx).
    - `failure_error_function`이 모델에 보이는 MCP 실패 메시지를 정하고, `None`이면 예외를 던진다.
    - `Agent(output_type=PydanticModel)`, `Runner.run_streamed`, `RunItemStreamEvent.name`(`tool_called`, `tool_output`), `result.cancel()`.
- **B9 구현에서 확인됨** (설치본, backend-dev 9e1c2c6)
  - **openai-agents 0.23.1**:
    - 이름: 함수 도구 데코레이터는 `function_tool`, 실행은 `Runner.run_streamed(..., max_turns=)`, 상한 초과는 `MaxTurnsExceeded`, 사용량은 `result.context_wrapper.usage`다.
    - MCP 실패: MCP `isError` 결과는 예외가 아니라 일반 출력으로 온다. 그래서 `MCPServerStreamableHttp`의 `custom_data_extractor`로 `isError`를 실어 `tool_result` `failed`를 판정한다. 예외는 `failure_error_function` 머리말로 판정한다.
    - 트레이싱: 기본값이 실행 내용(코드 발췌, 지표 수치)을 OpenAI 트레이스로 내보내므로 끈다.
  - **anthropic 1.13.0**: `async_mcp_tool`이 있다. 하지만 공통 래퍼가 `tool_call`/`tool_result`를 내야 해서, MCP 도구도 `@beta_async_tool` + MCP `inputSchema`로 직접 감싼다.
  - **설정**: real 모드는 `CODE_SUMMARY_MODEL`에도 접두사가 있어야 기동한다(ADR-20 "그 외는 기동 실패").
- **미확인 (T073, 실제 키 필요)**: Anthropic 구조화 출력이 `AgentAnswer` 스키마의 제약(`minItems`, `anyOf`, `minimum`, `maxLength`)을 받는지 확인해야 한다. SDK가 스키마를 변환 없이 보낸다. 거부되면 ADR-17 규칙대로 해당 제약을 Pydantic 사후 검증으로 옮긴다.
- **키 없는 검증 방법**: 두 SDK 모두 HTTP 클라이언트를 주입할 수 있다. 검사 스크립트가 스크립트된 API 응답(도구 호출 → 도구 결과 → 최종 JSON)을 넣어 실제 SDK 파싱 경로를 태운다(T069). 전송 계층은 SDK마다 다르다. **anthropic 1.x는 `httpx2`**를 쓰므로 `httpx2.MockTransport`로 넣는다(`httpx.AsyncClient`는 TypeError). openai·MCP SDK는 `httpx.MockTransport`다.

## 기술 선택 메모 (확정 ADR, 구현 시 주의)

- **구조화 응답 (ADR-20, 구 ADR-17)**: Anthropic은 tool runner의 `output_format=AgentAnswer`, OpenAI는 `Agent(output_type=AgentAnswer)`다. 교차 규칙은 Pydantic 사후 검증이다. B9에서 두 구현을 각각 확인한다(가짜 전송으로 T069, 실제 키로 T073).
- **SSE + Cloudflare**: 응답 헤더에 `Cache-Control: no-cache`, `X-Accel-Buffering: no`를 둔다. 15초 ping으로 터널 유휴 종료를 막는다.
- **프론트 검사 스크립트 실행**: `.ts` 검사는 Node 22.6 이상의 `--experimental-strip-types` 또는 `tsx`로 실행한다. 고르는 것은 구현자 몫이며 `package.json` 스크립트 `check`에 고정한다.
- **ripgrep 패턴**: kbap-fe는 `track(EVENTS.xxx, ...)` 단일 패턴이다(형제 레포에서 확인). 패턴은 `TRACK_CALL_PATTERN` 환경변수로 둔다.
