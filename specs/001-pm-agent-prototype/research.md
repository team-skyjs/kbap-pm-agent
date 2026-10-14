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

## 기술 선택 메모 (확정 ADR, 구현 시 주의)

- **LangChain 구조화 응답**: `ProviderStrategy(AgentAnswer)`로 공급자 네이티브 구조화 출력을 쓴다(ADR-17). `ToolStrategy`는 강제 tool_choice를 쓰는데 현행 Claude 모델이 이를 거부한다. JSON 스키마로 못 쓰는 교차 규칙(`funnel_design` 신규 단계 `location` 필수, `order` 연속)은 응답 후 Pydantic으로 검증한다. B6에서 Claude와 GPT로 각각 한 번씩 실행해 스키마가 거부되지 않는지 확인한다.
- **SSE + Cloudflare**: 응답 헤더에 `Cache-Control: no-cache`, `X-Accel-Buffering: no`를 둔다. 15초 ping으로 터널 유휴 종료를 막는다.
- **프론트 검사 스크립트 실행**: `.ts` 검사는 Node 22.6 이상의 `--experimental-strip-types` 또는 `tsx`로 실행한다. 고르는 것은 구현자 몫이며 `package.json` 스크립트 `check`에 고정한다.
- **ripgrep 패턴**: kbap-fe는 `track(EVENTS.xxx, ...)` 단일 패턴이다(형제 레포에서 확인). 패턴은 `TRACK_CALL_PATTERN` 환경변수로 둔다.
