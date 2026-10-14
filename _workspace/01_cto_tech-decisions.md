# 01 CTO — 기술 결정 (ADR)

작성일: 2026-10-15 · 입력: `docs/prd/PRD-kbap-pm-agent.md`, `_workspace/00_input.md`, 형제 레포(읽기 전용) 조사

## 0. 판단 근거로 쓴 사실 (형제 레포 조사)

| 레포 | 스택 | 이 결정에 주는 의미 |
|---|---|---|
| `../kbap` | Kotlin 2.3, Spring Boot 4.1, Spring AI 2.0, MySQL, Flyway, Gradle 멀티모듈 | 팀의 주력 스택. 단 LLM 사용은 비전·임베딩 단발 호출뿐이고, **에이전트형 LLM 로직은 KB-301/KB-320에서 Spring 밖으로 뺐다** |
| `../kbap-langchain` | Python 3.12, uv, LangGraph 1.x, LangChain 1.x, Langfuse | Spring의 LLM 파이프라인을 "이관해 없애는" 목적의 레포. 팀이 LLM 오케스트레이션은 Python으로 하기로 이미 결정한 흔적 |
| `../kbap-amplitude` | Python 3.12, FastAPI, LangGraph, pymysql, React+Vite(TS), Docker Hub 이미지, cloudflared 터널 | **이 제품의 전신 POC.** Amplitude 질의 에이전트 + MySQL 대화 저장 + 홈서버 배포까지 이미 해 봤다. 배포 스크립트·compose 컨벤션·MySQL 계정 패턴을 그대로 가져온다 |
| `../kbap-fe` | Expo 57 / React Native / TS | 분석 대상 FE 코드. 이벤트 호출이 `track(EVENTS.xxx, {...})` 단일 패턴이라 grep 선필터가 성립한다 (PRD 7.4 가정 확인됨) |
| `../kbap-admin/web` | React 19 + Vite + TS | 팀의 웹 프론트 기본형 |

---

### ADR-1: 백엔드는 Python 3.12 + FastAPI + LangChain 1.x (uv 관리)
- 결정: `backend/`는 Python 3.12, FastAPI(uvicorn 단일 워커), LangChain 1.x(`create_agent`), `langchain-mcp-adapters`, MySQL 드라이버는 구현자 위임. 패키지는 uv.
- 이유: (1) 에이전트 루프·MCP 클라이언트(OAuth 포함)·Claude↔GPT 교체 세 가지 모두 Python 생태계가 가장 성숙하다. (2) 팀은 이미 같은 스택으로 전신 POC(`kbap-amplitude`)와 운영 파이프라인(`kbap-langchain`)을 만들었고, Spring에서 LLM 로직을 빼낸 이력이 있다. (3) 홈서버 배포도 Python 컨테이너로 해 본 경로다.
- 버린 대안: Spring AI 2.0(Kotlin). 팀 숙련도는 가장 높지만, 이 앱은 kbap 백엔드와 코드·DB를 공유하지 않아 "운영 일관성" 이득이 작다. 멀티스텝 에이전트·MCP OAuth 클라이언트는 Spring AI 쪽 예제와 커뮤니티가 얇고, 프로토타입 기동·반복 속도도 느리다.
- 바꾸면 영향: 아래 "ADR-1 뒤집기" 참고. API 계약서와 프론트는 영향 없음.
- 상태: 확정 (2026-10-15 사용자 확인: Python 백엔드, TS 프론트)

#### ADR-1 뒤집기 — Spring AI(Kotlin)로 바꾸면 바뀌는 것
- **그대로인 것:** API 계약서 전체, 프론트 전부, MySQL 스키마(ADR-8), 배포 토폴로지(ADR-11), 비용 통제 전략(ADR-9). 계약을 언어 중립으로 썼기 때문이다.
- **다시 써야 하는 것:** `backend/` 전체. 에이전트 루프는 Spring AI `ChatClient` + `@Tool` 자동 도구 호출로, 구조화 제안은 `.entity(ProposalSet::class.java)`로, MCP는 `spring-ai-starter-mcp-client`(streamable HTTP)로 대체한다.
- **추가로 생기는 일:** Amplitude MCP OAuth를 서버가 대신 받는 흐름을 직접 붙여야 한다(Spring AI MCP 클라이언트의 OAuth 지원은 커뮤니티 모듈 수준). SSE는 `SseEmitter`/`Flux<ServerSentEvent>`. 스키마는 Flyway로.
- **얻는 것:** kbap과 같은 빌드·리뷰 규칙(ArchUnit, Kotest)과 같은 Docker 베이스. 두 사람이 한 언어만 쓴다.
- **뒤집기 신호:** 2주 차 끝에 MCP OAuth나 LangChain 버전 문제로 B7 모듈이 막히고, Spring 쪽에서 같은 기능을 하루 안에 검증할 수 있을 때.

### ADR-2: 에이전트 루프는 LangChain `create_agent` 기본 루프 + 구조화 최종 응답
- 결정: 직접 그래프를 짜지 않고 `langchain.agents.create_agent(model, tools, system_prompt, response_format=AgentAnswer)`를 쓴다. 최종 응답은 Pydantic 스키마 `AgentAnswer{content, proposals[]}`로 강제한다(계약서의 Proposal 구조 그대로). 스트리밍은 `astream(stream_mode="updates")` 결과를 SSE 이벤트로 변환한다.
- 이유: PRD가 요구하는 것은 "도구 여러 번 호출 + 중간 결과 보고 다음 조회 결정"이고, 기본 ReAct 루프가 정확히 그것이다. 제안 4필드를 본문 문자열이 아닌 구조로 받는 것도 `response_format` 한 줄로 끝난다.
- 버린 대안: kbap-amplitude식 9노드 StateGraph. 품질 튜닝 단계에서는 유효하나 v1에서 "채택할 만한가"를 검증하기 전에 짓기엔 과하다. 필요해지면 같은 LangGraph 위에서 노드를 추가한다.
- 바꾸면 영향: `backend/app/agent/` 내부만. SSE 이벤트 형식은 계약이므로 유지.
- 가드: 질문당 모델 호출 턴 상한 `AGENT_MAX_TURNS`(기본 10). 도구 호출은 세지 않는다(한 턴의 병렬 도구 호출은 1턴). 초과 시 추가 모델 호출 없이 그때까지의 결과로 부분 `final`을 보낸다.
- 변경 사유: 2026-10-15 사용자 결정. 상한의 목적은 LLM 비용 통제이고, 질문 경로의 도구(grep·캐시·DB·MCP 조회)는 비용이 0이라 비용은 모델 턴에서만 생긴다(도구 20 → 도구 5 → 모델 턴 10).
- 상태: 대체됨(→ADR-20) — LangChain `create_agent` 대신 공급자별 공식 SDK 런타임

### ADR-3: Amplitude는 `langchain-mcp-adapters` + MCP Python SDK OAuth, 서버가 토큰 보관
- 결정: `MultiServerMCPClient`로 `https://mcp.amplitude.com/mcp`(streamable HTTP)에 연결한다. 인증은 MCP SDK의 `OAuthClientProvider`(OAuth 2.1 + 동적 클라이언트 등록)를 `auth`로 넘기고, 토큰 저장소는 MySQL `app_settings`에 둔다. 최초 1회는 브라우저 승인이 필요하므로 계약서의 `POST /api/integrations/amplitude/connect` → 승인 URL → `GET /api/integrations/amplitude/callback` 흐름으로 처리한다.
- 이유: Amplitude 원격 MCP는 OAuth만 받는다(API 키 미지원). 사용자 2명·인증 없음이므로 연결은 "서버 단위 1개"로 충분하다.
- 버린 대안: Amplitude Dashboard REST API 직접 호출(kbap-amplitude 방식). 검증된 코드가 있지만 PRD가 공식 MCP를 명시했고 택사노미·차트 도구를 공짜로 얻는다. MCP 연결이 막히면 kbap-amplitude `amp.py`를 도구로 감싸는 것이 즉시 쓸 수 있는 대체 경로다.
- 바꾸면 영향: Amplitude 도구 공급 함수 하나와 settings의 `amplitude` 상태 필드.
- 상태: 가정 — 동적 클라이언트 등록 지원은 Amplitude 공식 문서가 아닌 서드파티(Nango) 문서로만 확인했다. B7 첫날 실연결로 검증한다. (2026-10-15 영향 범위 갱신: `langchain-mcp-adapters` 제거. OAuth는 MCP SDK `OAuthClientProvider` 그대로이고, 도구 공급은 ADR-20의 두 런타임이 이 provider 하나를 공유한다. Anthropic 런타임은 `anthropic.lib.tools.mcp.async_mcp_tool`, OpenAI 런타임은 `MCPServerStreamableHttp(params={"url", "auth"})`를 쓴다. Anthropic MCP 커넥터는 쓰지 않는다. 근거는 research.md R8)

### ADR-4: 추론 모델은 `init_chat_model` 문자열 하나로 교체
- 결정: 모델은 환경변수 `AGENT_MODEL`(예: `anthropic:claude-sonnet-5-5`, `openai:gpt-6-luna`)과 `CODE_SUMMARY_MODEL`로 지정하고 `langchain.chat_models.init_chat_model`로 생성한다. 코드에 공급자 분기를 두지 않는다.
- 이유: PRD 7.3 "설정으로 교체 가능, 하나로 시작". 두 공급자의 도구 호출·구조화 출력이 LangChain에서 같은 인터페이스다.
- 버린 대안: 공급자 SDK 직접 사용. 루프·도구 스키마 변환을 두 벌 써야 한다.
- 기본값: 구현자 위임. 단 코드 요약은 200달러 크레딧이 있는 Claude 저가 모델로 시작하길 권장.
- 상태: 대체됨(→ADR-20) — `init_chat_model` 대신 모델 문자열 접두사(`anthropic:`/`openai:`)로 런타임 선택

### ADR-5: 프론트는 React + Vite + TypeScript 정적 SPA, HashRouter
- 결정: `frontend/`는 React 19 + Vite + TS. 라우팅은 해시(`#/conversations/7`). `vite.config.ts`의 `base`는 `/kbap-pm-agent/`. API 주소는 빌드 시 `VITE_API_BASE_URL`.
- 이유: GitHub Pages 프로젝트 페이지는 하위 경로 + 서버 리라이트 없음이라 해시 라우팅이 404 우회 없이 동작한다. 팀이 kbap-admin/web, kbap-amplitude/web에서 같은 구성을 쓴다.
- 버린 대안: Expo Web(kbap-fe 재사용). 모바일 의존성이 무겁고 정적 웹 산출물이 목적에 맞지 않는다. Next.js 정적 export는 이 규모에 기능 과잉이다.
- 바꾸면 영향: 프론트 전체. 계약은 그대로.
- 상태: 확정

### ADR-6: FE↔BE는 Cloudflare Tunnel + CORS + POST 응답 SSE
- 결정: 백엔드는 홈서버의 기존 cloudflared(`monitor-net`)로 공개한다. CORS 허용 출처는 `CORS_ORIGINS`(쉼표 구분). 메시지 전송은 `POST` 응답 자체를 `text/event-stream`으로 보내고, 프론트는 `fetch` + `ReadableStream`으로 읽는다. 15초마다 `: ping` 주석을 보낸다.
- 이유: 에이전트 한 턴이 수십 초~수 분 걸려 Cloudflare의 100초 응답 대기 제한(524)에 걸린다. 스트리밍은 이를 피하고 도구 호출 진행 상황도 보여준다. POST 하나로 끝나 폴링·실행 ID 관리가 필요 없다.
- 버린 대안: 폴링(실행 상태 테이블·백그라운드 작업 필요), WebSocket(양방향 불필요), `EventSource`(GET만 가능).
- 바꾸면 영향: 계약서 메시지 전송 엔드포인트와 FE 채팅 모듈.
- 공개 도메인: 가정. 예시는 `https://pm-agent.example.com`(운영 값은 문서에 쓰지 않는다), 실제 값은 `VITE_API_BASE_URL`과 `PUBLIC_BASE_URL`로만 주입한다.
- 상태: 확정 (도메인만 가정)

### ADR-7: 공유 접근 토큰 하나로 공개 API를 잠근다
- 결정: 환경변수 `ACCESS_TOKEN`이 설정되면 `/api/health`와 OAuth 콜백을 제외한 모든 요청에 `Authorization: Bearer <ACCESS_TOKEN>`을 요구한다. 프론트는 설정 화면에서 토큰을 한 번 입력받아 `localStorage`에 둔다. 미설정이면 검사하지 않는다(로컬 개발).
- 이유: 백엔드는 인터넷에 공개되고 요청마다 LLM 비용이 든다. 사용자 인증(PRD 비목표)이 아니라 200달러 예산을 지키는 문지기다.
- 버린 대안: Cloudflare Access(GitHub Pages 출처에서 오는 교차 출처 요청과 궁합이 나쁨), 무방비 공개(예산 소진 위험).
- 바꾸면 영향: 미들웨어 하나와 FE 설정 입력칸 하나.
- 상태: 가정 — PRD에 없는 결정. 필요 없으면 `ACCESS_TOKEN`을 비워 두면 된다.
- 2026-10-15 갱신: 사용자 결정으로 운영에서 **필수**. 배포 워크플로우가 ACCESS_TOKEN이 비면 실패하고, 배포 스크립트가 토큰 없는 보호 경로 401을 확인한다(헌법 v1.3.0). "비워 두면 꺼진다"는 로컬·시연용에만 해당.

### ADR-8: MySQL 스키마 뼈대 — 6개 테이블, 기동 시 `schema.sql` 적용
- 결정: `backend/schema.sql`에 `CREATE TABLE IF NOT EXISTS`로 정의하고 앱 기동 시 실행한다. 이후 변경은 같은 파일에 `ALTER`를 추가하고 수동 적용한다. 시간은 UTC `DATETIME(3)`, 문자셋 `utf8mb4`.
  - `conversations(id BIGINT PK AI, title VARCHAR(200), created_at, updated_at)`
  - `messages(id, conversation_id FK→conversations ON DELETE CASCADE, role ENUM('user','assistant'), status ENUM('running','completed','failed'), content MEDIUMTEXT, error_code VARCHAR(50) NULL, created_at)`
  - `tool_calls(id, message_id FK CASCADE, seq INT, source ENUM('amplitude','code','taxonomy'), name VARCHAR(100), input_json JSON, status ENUM('running','succeeded','failed'), result_summary VARCHAR(1000), result_text MEDIUMTEXT, duration_ms INT NULL, started_at)`
  - `proposals(id, message_id FK CASCADE, conversation_id FK CASCADE, seq INT, type ENUM('improvement','funnel_design'), title VARCHAR(200), evidence_json JSON, proposal_text TEXT, steps_json JSON, measurement_json JSON, decision_status ENUM('pending','adopted','on_hold') DEFAULT 'pending', decision_note TEXT NULL, decided_at NULL, created_at)`
  - `llm_usage(id, message_id NULL FK SET NULL, purpose ENUM('agent','code_summary'), model VARCHAR(100), input_tokens INT, output_tokens INT, cost_usd DECIMAL(10,4), created_at)` — 예산 집계의 단일 출처
  - `app_settings(k VARCHAR(100) PK, v JSON, updated_at)` — 저장소 설정, 택사노미, Amplitude OAuth 토큰
- 이유: PRD 7.1-5와 핵심 결과 1(채택 건수)을 SQL 한 줄로 집계할 수 있는 최소 구조. 채택은 제안당 상태 하나라 별도 이력 테이블 없이 컬럼으로 둔다. 제안 내부 구조(근거·단계·측정)는 프론트 계약을 그대로 담는 JSON 컬럼이다.
- 버린 대안: Alembic 마이그레이션(v1 스키마 변동 대비로는 과함, 변동이 잦아지면 도입). 채택 이력 테이블(누가 바꿨는지 볼 필요가 없는 2인 팀).
- 바꾸면 영향: 계약서 응답 필드 일부, 집계 쿼리.
- 상태: 확정

### ADR-9: 코드 분석 비용 통제 — 무료 인덱스 → 좁힌 읽기 → 파일 단위 요약 캐시 → 예산 상한
- 결정:
  1. **무료 인덱스(LLM 0원):** 저장소 동기화 시 ripgrep으로 `TRACK_CALL_PATTERN`(기본 `track\(EVENTS\.(\w+)`)을 훑어 이벤트→`파일:줄` 목록을 만든다. 화면 목록은 `SCREEN_GLOB`(기본 `src/app/**/*.tsx`, expo-router).
  2. **에이전트 코드 도구는 좁혀서만 읽는다:** `find_event_calls(eventName)`(인덱스), `search_code(regex, glob)`(rg, 최대 30건), `get_screen_summary(path)`(캐시), `read_code(path, startLine, endLine)`(호출당 최대 200줄). 파일 통째 전송 도구는 없다.
  3. **화면 요약 캐시:** 화면 파일마다 저가 모델로 150단어 요약(역할·주요 컴포넌트·핸들러·발생 이벤트)을 만들고 **git blob SHA를 키로** 저장한다. 커밋이 바뀌면 blob이 바뀐 파일만 다시 요약한다. 저장 매체(DB/파일)는 위임.
  4. **예산 상한:** 모든 LLM 호출을 `llm_usage`에 기록하고, 누적이 `LLM_BUDGET_USD`(기본 200)를 넘으면 새 메시지를 `BUDGET_EXCEEDED`로 거절한다. 단가는 설정 표로 둔다.
- 이유: PRD 5절·7.3. 인덱스와 grep은 비용이 0이고, 커밋 단위가 아닌 blob 단위 캐시라 작은 커밋은 거의 공짜로 갱신된다.
- 버린 대안: 벡터 임베딩 RAG(인프라·튜닝 비용 대비 이 규모의 FE 코드에선 grep으로 충분), 커밋 단위 전체 재요약(변경 한 줄에 전체 비용).
- 바꾸면 영향: `backend/app/code/` 내부. 계약에는 settings의 `repository` 상태 필드만 노출된다.
- 상태: 확정

### ADR-10: 외부 연동은 "에이전트 실행" 한 곳에서 가짜로 갈아 끼운다
- 결정: `AGENT_MODE=fake`이면 실제 LLM·Amplitude 대신 스크립트된 실행기가 계약서와 같은 SSE 이벤트(도구 호출 2개 + improvement 제안 1개 + funnel_design 제안 1개)를 내고 DB에 저장한다. GitHub는 가짜를 두지 않고 `file://` 로컬 경로 클론으로 시험한다. 그 외 추상화 계층은 만들지 않는다.
- 이유: QA와 FE 연동은 LLM 비용·OAuth 없이 돌아야 한다. 교체 지점이 하나면 가짜가 실제와 어긋날 곳도 하나다.
- 버린 대안: LLM·MCP·GitHub 각각의 인터페이스+가짜 구현(구현 하나짜리 추상화 세 개, 유지비만 늘어남).
- 바꾸면 영향: 없음(테스트 경로).
- 상태: 대체됨(→ADR-15) — 헌법 원칙 III이 fake 모드에서 GitHub·Amplitude까지 대체하도록 요구한다

### ADR-11: 로컬은 `docker compose up`, 운영은 kbap-amplitude 배포 컨벤션 그대로
- 결정:
  - 로컬: 레포 루트 `docker-compose.yml`에 `backend`(build `./backend`, 포트 8000)와 `mysql`(`mysql:8.4`, 포트 3307, 볼륨)을 둔다. `backend` 이미지에는 `git`, `ripgrep`이 들어가고 클론은 볼륨 `/data/repos`.
  - 운영 BE: 이미지 `simhani1/kbap-pm-agent:latest`(amd64·arm64). 홈서버에는 `deploy/docker-compose.kbap-pm-agent.yml`(이미지만, `monitor-net`, `127.0.0.1:8001:8000`)과 `kbap-pm-agent.env`. MySQL은 홈서버의 기존 MySQL 컨테이너에 전용 DB `kbap_pm_agent`와 계정을 만든다(kbap-amplitude 7절과 같은 방식). cloudflared ingress를 `http://kbap-pm-agent:8000`으로.
  - 운영 FE: GitHub Actions가 `frontend/`를 빌드해 GitHub Pages로 배포. `VITE_API_BASE_URL`은 레포 Variables.
  - FE 로컬: `npm run dev`(5173), `VITE_API_BASE_URL=http://localhost:8000`.
- 이유: 이미 돌아가는 홈서버 경로를 재사용하면 배포 결정이 0개다. 포트 8000은 kbap-amplitude가 쓰고 있어 8001.
- 버린 대안: 운영에도 전용 MySQL 컨테이너 추가(홈서버 자원 중복).
- 바꾸면 영향: compose 파일과 배포 스크립트만.
- 상태: 가정 — GitHub 레포 이름 `kbap-pm-agent`, Docker Hub 계정 `simhani1`, 홈서버에 기존 MySQL·cloudflared가 그대로 있다는 전제.

### ADR-12: 택사노미는 계약서에 정의한 JSON 하나로 받는다
- 결정: `PUT /api/settings/taxonomy`에 계약서의 JSON 형식(이벤트명·설명·카테고리·속성 목록)으로 전체 교체 업로드한다. 프론트는 사용자가 고른 `.json` 파일을 읽어 그대로 보낸다. 다른 형식(CSV, Amplitude export) 변환은 사람이 한 번 한다.
- 이유: PRD 열린 질문. 형식을 하나로 고정해야 FE·BE가 같은 파서를 가정한다.
- 버린 대안: Amplitude MCP 택사노미 도구만 사용(우리 쪽 정의 문서가 따로 있다는 PRD 전제와 다름. 단, 에이전트는 MCP 택사노미 도구도 함께 쓸 수 있다).
- 바꾸면 영향: 업로드 엔드포인트 요청 형식과 FE 파일 읽기.
- 상태: 가정

### ADR-13: 비공개 FE 저장소는 서버 환경변수 `GITHUB_TOKEN`으로 클론한다
- 결정: `GITHUB_TOKEN`(fine-grained PAT, 대상 저장소 Contents read-only)이 있으면 HTTPS 클론 URL에 넣어 쓴다. 토큰은 API 응답·로그에 내보내지 않는다. 저장소는 1개만 등록한다.
- 이유: PRD 열린 질문. 사용자 2명·저장소 1개에 GitHub App은 과하다.
- 버린 대안: GitHub App, SSH 배포 키(이미지에 ssh 설정 필요).
- 바꾸면 영향: 클론 함수 하나.
- 상태: 가정

### ADR-14: v1은 질문에 반응하는 모드만 만든다
- 결정: 능동 제안(스케줄 실행)은 만들지 않는다.
- 이유: PRD 8절 첫 버전 범위에 없고, 다음 버전의 "능동 리포트"와 겹친다.
- 버린 대안: 주 1회 크론 실행. 다음 버전에서 같은 에이전트 실행 함수를 스케줄러가 부르면 된다.
- 바꾸면 영향: 없음(추가만).
- 상태: 가정

### ADR-15: `AGENT_MODE=fake`는 LLM·Amplitude·GitHub 세 연동을 모두 대체한다 (ADR-10 대체)
- 결정: 외부 호출은 세 지점(seam)으로만 한다. 에이전트 실행(LLM+MCP 도구), 저장소 클론·pull, Amplitude OAuth 연결이다. `AGENT_MODE=fake`이면 세 지점 모두 계약서 예시 값을 돌려준다(계약서 "시연 모드" 표). 분기는 각 지점 함수 안의 `if` 하나이며 인터페이스·가짜 클래스는 만들지 않는다.
- 이유: 헌법 원칙 III("외부 연동 전부를 계약서 예시 값으로 대체")과 FR-011, SC-005. ADR-10은 GitHub를 `file://`로 시험하게 해 외부 키 없는 시연과 어긋났다.
- 버린 대안: ADR-10 유지(헌법 위반), 연동별 인터페이스+가짜 구현(원칙 II 위반).
- 바꾸면 영향: 저장소·Amplitude 함수 각각에 분기 하나. `file://` 클론은 real 모드 시험 수단으로 남는다.
- 상태: 확정 (2026-10-15 영향 범위 갱신: fake 분기는 `agent.py`에서 런타임 선택 전에 탄다. 두 런타임은 fake 모드에서 호출되지 않는다. 키 없는 런타임 검증은 각 SDK 클라이언트에 `httpx.MockTransport`를 주입하는 검사 스크립트로 한다(ADR-20). 운영 코드에 가짜 런타임은 두지 않는다)

### ADR-16: 에이전트 실행 시간 상한 `AGENT_TIMEOUT_SECONDS`(기본 170초)
- 결정: 모델 호출 턴 상한(ADR-2)에 더해 실행 시간 상한을 둔다. 둘 중 하나에 닿으면 그때까지의 조회 결과로 `final`을 보내고 `content` 첫 문장에 중단 사유를 적는다. 개별 도구 실패는 실행을 멈추지 않는다.
- 이유: 명세 SC-004(완성 제안 3분 이내)와 엣지 케이스(상한 시간 초과 시 부분 답변). 170초면 저장·전송 여유를 두고 3분 안에 끝난다.
- 버린 대안: 상한 없음(SC-004 위반), 상한 초과 시 `error`(이미 모은 근거를 버림).
- 바꾸면 영향: 에이전트 실행 함수 한 곳.
- 상태: 확정

### ADR-17: 구조화 최종 응답은 `ProviderStrategy(AgentAnswer)`로 명시한다 (ADR-2 보정)
- 결정: `create_agent(..., response_format=ProviderStrategy(AgentAnswer))`로 공급자 네이티브 구조화 출력을 쓴다(Anthropic `output_config.format` json_schema, OpenAI `response_format`). Evidence는 JSON 스키마가 `anyOf`가 되도록 일반 Union으로 정의한다. 판별 유니온과 검증 결과는 같다. JSON 스키마로 표현되지 않는 교차 규칙(신규 단계 `location` 필수, `order` 연속)은 응답 수신 후 Pydantic 검증으로 강제한다.
- 이유: LangChain 1.4의 `ToolStrategy` 경로는 `tool_choice="any"`를 강제하는데, claude-sonnet-5-5·claude-opus-5-5·claude-fable-5-1이 강제 tool_choice를 400으로 거부한다(backend-dev 보고, 2026-10-15).
- 버린 대안: `ToolStrategy`(위 모델에서 실패), 최종 응답을 텍스트로 받아 JSON 파싱(FR-002 구조 보장이 약해짐).
- 바꾸면 영향: `backend/app/agent.py`와 `schemas.py`의 Evidence 정의만. 계약·FE 영향 없음.
- 미검증: 실제 키 호출 전이다. T042에서 스키마 제약(`minItems` 등) 거부가 나오면 해당 제약을 Pydantic 사후 검증으로 옮긴다.
- 상태: 대체됨(→ADR-20) — 구조화 응답은 Anthropic `output_format`, OpenAI Agents `output_type`

### ADR-18: 운영 프론트 출처는 `https://team-skyjs.github.io` (ADR-11 가정 확인)
- 결정: GitHub Pages는 `team-skyjs/kbap-pm-agent` 레포에서 배포한다. 운영 `CORS_ORIGINS`에는 `https://team-skyjs.github.io`(경로 없이 출처만)를 넣는다. 프론트 URL은 `https://team-skyjs.github.io/kbap-pm-agent/`다. Docker Hub 이미지(`simhani1/kbap-pm-agent`)와 홈서버 계정은 ADR-11 그대로다.
- 이유: 실제 git remote가 `team-skyjs`다. ADR-11의 예시 출처 `simhani1.github.io`는 틀린 가정이었고, 그대로 배포하면 운영 요청이 전부 CORS로 거부된다(QA-3, 2026-10-15).
- 버린 대안: simhani1 개인 포크에서 Pages 배포(레포가 둘이 되고 배포 경로가 갈라진다).
- 바꾸면 영향: 운영 env의 `CORS_ORIGINS` 값. `backend/checks/check_b8.py`는 기대 출처를 git remote에서 계산하므로 손댈 필요가 없다.
- 단일 출처: 출처 값의 기준은 git remote다. ADR·env 예시·운영 env의 값은 사본이고, check_b8이 운영 서버의 preflight 응답을 remote에서 계산한 출처와 대조해 사본 오류를 잡는다(QA-3·QA-4 2회 재발 후 추가).
- 상태: 확정

### ADR-19: 코드 인덱스·검색 범위는 소스 파일로 한정 `CODE_GLOB` (ADR-9 보정)
- 결정: rg 인덱스(`TRACK_CALL_PATTERN`), `search_code`, `read_code`, `trackedEventCount`는 `CODE_GLOB`(기본 `*.{ts,tsx,js,jsx}`) 파일만 대상으로 한다. 마크다운·문서·`specs/`는 제외한다. 에이전트의 `code` 근거는 이 범위 안의 파일만 인용할 수 있다.
- 이유: kbap-fe는 `specs/*/tasks.md`에도 `track(EVENTS.` 문자열이 있다. 범위가 없으면 에이전트가 문서를 코드 근거로 인용하고 이벤트 수가 부풀려진다(QA-2, 2026-10-15. develop f34c518 기준 전체 120 vs 소스 117).
- 버린 대안: `.gitignore`·확장자 무관 전체 검색(문서 오인용), 디렉토리 화이트리스트(`src/`만, 저장소 구조가 바뀌면 깨짐).
- 바꾸면 영향: `backend/app/repo.py`·`code_tools.py`의 rg 인자. 계약 영향 없음.
- 상태: 확정

### ADR-20: LLM 호출은 공급자별 공식 SDK로, LangChain 제거 (ADR-2·4·17 대체)
- 결정: `langchain`, `langchain-anthropic`, `langchain-openai`, `langchain-mcp-adapters`를 의존성에서 뺀다. 외부 LLM seam은 `backend/app/agent.py`의 `run_agent()`·`summarize()` 그대로다. `AGENT_MODEL`·`CODE_SUMMARY_MODEL`의 접두사가 런타임을 고른다(`anthropic:<모델 ID>`, `openai:<모델명>`, 그 외는 기동 실패). 런타임은 파일 두 개이고 공통 인터페이스 클래스는 두지 않는다. 접두사 → 함수 dict 하나로 분기한다.
  - **anthropic** (`backend/app/agent_anthropic.py`, 공식 `anthropic` SDK)
    - 루프: `AsyncAnthropic().beta.messages.tool_runner(...)`에 `@beta_async_tool` 도구를 넘긴다.
    - 구조화 응답: `output_format=AgentAnswer`(구조화 출력)를 쓴다.
    - 사고: `thinking={"type": "adaptive"}`.
    - 캐싱: 최상위 `cache_control={"type": "ephemeral"}`로 시스템 프롬프트·도구 목록을 캐시한다.
    - 거절 대비: `betas=["server-side-fallback-2026-07-01"]` + `fallbacks="default"`로 서버 측 폴백을 켠다.
    - `tool_choice`는 지정하지 않는다(auto. 현행 모델이 any/tool 강제를 400으로 거부한다).
    - 매 반복의 `BetaMessage.usage`를 기록한다. `stop_reason == "refusal"`이면 `error` `UPSTREAM_ERROR`로 끝낸다.
  - **openai** (`backend/app/agent_openai.py`, `openai-agents`)
    - 구성: `Agent(instructions, model=<접두사 뗀 이름>, tools=[function_tool...], mcp_servers=[MCPServerStreamableHttp(...)], output_type=AgentAnswer)`.
    - 스트리밍: `Runner.run_streamed(...)`의 `RunItemStreamEvent`(`tool_called`, `tool_output`)를 받는다. 모델명(GPT-6-luna 등)은 환경변수로만 받는다.
  - **공통**
    - 도구: 코드·택사노미 도구는 `code_tools.py`의 같은 Python 함수이고, 각 런타임은 데코레이터로 얇게 감싸기만 한다.
    - 이벤트·실패: `tool_call`/`tool_result` 이벤트와 도구 예외 처리(실패 결과를 모델에 돌려주고 실행 계속, ADR-16)는 `agent.py`의 공통 래퍼 하나가 맡는다.
    - 상한·사용량: 170초 상한(`asyncio.timeout`), 모델 호출 턴 상한(`AGENT_MAX_TURNS`), 부분 `final`, 사용량 기록, 예산 검사는 `agent.py`에 남는다.
    - 사후 검증: JSON 스키마로 못 쓰는 교차 규칙(신규 단계 `location` 필수, `order` 연속)은 응답 후 `AgentAnswer` Pydantic 검증으로 강제한다. ADR-17의 재시도 없음 규칙을 이어받는다.
- 이유:
  - 사용자 지시(2026-10-15): 공식 SDK를 쓰고, 공급자 교체는 OpenAI SDK로 갈아끼울 수 있으면 된다.
  - LangChain 추상화가 Claude 네이티브 기능(적응형 사고, 구조화 출력, 프롬프트 캐싱, 서버 측 폴백)을 가리고, 이미 ToolStrategy 강제 tool_choice로 400을 낸 적이 있다(ADR-17).
  - 설치된 `anthropic` 1.13.0의 `tool_runner`는 `output_format`·`thinking`·`cache_control`·`fallbacks`·`betas`·`max_iterations`를 받는다(설치본 시그니처 확인).
- 버린 대안:
  - LangChain 유지: 위 이유.
  - OpenAI Agents SDK 하나를 공통 런타임으로 쓰고 Claude를 LiteLLM·커스텀 모델 공급자로 돌리기: 사용자가 SDK로 바꾸는 이유인 Claude 네이티브 기능을 그 경로가 다시 잃는다.
  - 공통 `LLMRuntime` 인터페이스 클래스: 구현 두 개에 dict 분기로 충분하다(원칙 II).
  - Anthropic MCP 커넥터(서버 측 MCP 연결): research.md R8.
- 바꾸면 영향:
  - 바뀌는 것: `backend/app/agent.py`, `agent_anthropic.py`, `agent_openai.py`, `amplitude.py`의 도구 공급 함수, `pyproject.toml`, `backend/checks/check_b6.py`·`check_b7.py`.
  - 그대로인 것: API 계약 v1.1, 프론트, DB 스키마, SSE 이벤트 형식.
- 구현 확인(9e1c2c6): `openai-agents` 0.23.1의 `function_tool`, `max_turns`/`MaxTurnsExceeded`, `result.context_wrapper.usage`를 확인했다. 트레이싱은 끈다. 실행 내용(코드 발췌, 지표)이 OpenAI 트레이스로 나가지 않게 하기 위해서다. MCP 도구는 두 런타임 모두 공통 래퍼로 감싼다(Anthropic `async_mcp_tool` 미사용). Anthropic SDK의 전송 계층은 `httpx2`다.
- 알려진 런타임 차이(QA eb7f906): 모델이 없는 도구 이름을 부르면 Anthropic tool runner는 오류 결과를 돌려주고 계속한다. openai-agents는 `ModelBehaviorError`로 실행 전체가 `error` `UPSTREAM_ERROR`다. 둘 다 계약 안이다. 앞은 도구 실패, 뒤는 "추론 모델 자체 실패"로 분류된다. 지금은 맞추지 않는다. T073 실제 실행에서 OpenAI 쪽에 반복되면 `ModelBehaviorError`를 잡아 부분 `final`(`partial_content()`)로 보내도록 바꾼다. 이때 계약 05 비고에 중단 사유 하나를 추가해야 한다.
- 미검증: 실제 키 호출(T073). 구조화 출력이 `AgentAnswer` 스키마 제약을 받는지가 남았다.
- 상태: 확정 (헌법 "기술 제약"의 "LangChain 1.x" 문구 개정이 선행돼야 한다. 거버넌스 규칙. team-lead에 개정안 전달)

### ADR-24: 답변 차트는 Chart.js v4(필요한 컨트롤러만, 지연 로드) (003 프론트 재설계)
- 결정: `chart.js` v4에서 선·막대에 필요한 컨트롤러·스케일·요소·범례·툴팁·제목만 등록한다. 차트 블록이 처음 나올 때 동적 `import()`로 별도 청크를 받는다. 색은 CSS 토큰(`--chart-1`~`--chart-4`, `--chart-grid`, 글자색)에서 읽고, 시스템 테마가 바뀌면 다시 읽어 갱신한다. 캔버스 옆에 같은 데이터의 숨긴 표를 둔다(낭독기용).
- 이유: 2026-10-15 esbuild 실측에서 선·막대만 쓰면 171KB(min)/59KB(gzip)로 예산 200KB 안이다. 범례·축 라벨·툴팁이 내장이라 직접 짤 코드가 없다. 지연 로드라 차트 없는 화면은 비용이 0이다.
- 버린 대안: uPlot(50KB, 툴팁·막대 정렬을 직접 구현해야 함), Recharts(393KB, 예산 초과).
- 바꾸면 영향: `frontend/src/ChartBlock.tsx` 내부만. 차트 블록 형식(specs/003 contracts/chart-block.md)과 파서는 그대로다.
- 상태: 가정 — 실제 앱 빌드에서의 청크 크기와 사용자 확인(입력 문서의 첫 결정 지점)이 남았다. 200KB를 넘거나 사용자가 다른 것을 고르면 uPlot으로 바꾼다.

### ADR-25: 마크다운은 react-markdown + remark-gfm, 원시 HTML 미해석, 구문 강조 없음 (003)
- 결정: 답변 본문과 제안 텍스트를 같은 `Markdown` 컴포넌트로 그린다. `remark-gfm`으로 표·취소선·작업 목록을 켠다. `remark-cjk-friendly`(2.3.2)로 한국어 강조 닫힘 규칙을 고친다. CommonMark에서는 구두점 뒤·글자 앞의 닫는 `**`가 닫히지 않아 `**41%**로`가 문자로 보인다(2026-10-15 추가, team-lead 승인, 메인 청크 +13KB min/+5KB gzip, frontend-dev 4947e82). `rehype-raw`는 쓰지 않아 모델 출력의 HTML은 문자로 보인다. 링크는 `target="_blank" rel="noopener noreferrer"`다. 코드 블록은 고정폭·가로 스크롤·언어 표시·복사 버튼만 갖고 구문 강조는 하지 않는다. 언어 `chart` 블록은 ADR-27 파서로 넘긴다.
- 이유: PRD 5절이 새 의존성을 "차트 하나 예외"로 묶었고, 구문 강조기는 기능 추가라 두 번째 예외가 된다. `remark-cjk-friendly`는 기능이 아니라 한국어 마크다운의 정확성 결함 수정이라 예외로 승인했다(자체 `**` 치환보다 단일 `*`와 강조 안 인라인 요소까지 다룬다). 답변 코드는 짧은 이벤트 호출 예시라 강조 없이도 읽힌다. HTML 미해석은 모델 출력을 신뢰하지 않는 기본값이다.
- 버린 대안: highlight.js core 지연 로드(다음 사이클 후보), Shiki(수백 KB), `rehype-raw`+sanitize(필요 없음).
- 바꾸면 영향: `Markdown.tsx` 한 곳.
- 상태: 확정 (사용자 평가에서 코드 가독성이 지적되면 다시 본다)

### ADR-26: UI 검사는 Playwright + axe, 기본은 계약 예시 기반 고정 응답, CI는 다음 단계 (003)
- 결정:
  - **도구·매트릭스**: `@playwright/test` + `@axe-core/playwright`(devDependency), Chromium 하나, `npm run check:ui`(기존 `npm run check`와 분리)다. 뷰포트 1280·768·375 × 모드 light·dark·reduced-motion 9조합이다.
  - **API**: `page.route('**/api/**')`로 계약 분할본 예시 JSON과 SSE 스크립트 6종(여섯 화면 상태)을 준다. `CHECK_UI_LIVE=1`이면 정상 스트리밍 시나리오 하나만 로컬 fake 백엔드로 돈다.
  - **통과 기준**: axe `critical`·`serious` 0이다. 스크린샷은 `_workspace/04_designer_screenshots/`에 두고 gitignore한다.
  - **CI**: 이번에는 넣지 않는다.
- 이유: 오류·부분 완료·세션 만료는 fake 백엔드로 재현할 수 없어 고정 응답이 필요하다. 고정 응답을 계약 예시에서 만들면 계약·화면 검사가 같은 기준을 본다(헌법 원칙 I). 배포 워크플로우는 접근 제한 PR이 바꾸는 중이라 같은 파일을 동시에 고치지 않는다.
- 버린 대안: fake 백엔드만 사용(오류 상태 불가), MSW(의존성 추가), 브라우저 3종(시간 대비 이득 작음).
- 바꾸면 영향: `frontend/playwright.config.ts`, `frontend/checks/ui/`.
- 상태: 확정 (CI 편입은 두 PR 머지 후 별도 결정, specs/003 tasks Polish)

### ADR-27: 차트 데이터는 답변 본문의 `chart` 코드 블록으로만, 형식은 엄격 검증 (003)
- 결정: 형식 기준 파일은 `specs/003-frontend-redesign/contracts/chart-block.md`다.
  - 형식: 키 `type`(line|bar)·`title`·`x`·`series[name, values]`만 허용하고, 길이가 일치해야 하며, 추가 키는 오류다.
  - 파서: 프론트 `chartBlock.ts` 순수 함수가 검증하고, 실패하면 원문 코드 블록으로 보인다.
  - 에이전트 지시: `SYSTEM_PROMPT`에 "시계열 지표를 답할 때 chart 블록을 함께 쓴다"는 한 줄과 형식 예시를 넣는다. 예시는 기준 파일과 글자 단위로 같다(`backend/checks/check_b9.py`가 확인).
  - API 계약과 응답 shape는 바뀌지 않는다.
- 이유: PRD 사용자 결정(차트는 답변 안 블록만, 계약 변경 없음). 엄격 검증이라야 모델 오타가 엉뚱한 차트가 되지 않고, 실패는 원문으로 남아 정보가 사라지지 않는다.
- 버린 대안: 근거(Evidence)에 시계열 필드 추가(계약 변경, PRD 비목표), 느슨한 파싱(추가 키 무시. 모델 실수를 숨김).
- 바꾸면 영향: 형식 파일, 파서, 프롬프트 한 줄.
- 상태: 가정 — 모델이 블록을 안정적으로 내는지(spec SC-007: 실제 시계열 질문 5건 중 4건)는 실제 키로 확인해야 한다.

## 위임 (구현자가 정하되 "설정으로 바꿀 수 있게"만 지킨다)

- UI 라이브러리·스타일링 (PRD: 세련된 UI 비목표)
- 캐시 저장 매체(DB 테이블 vs 볼륨 파일), MySQL 접근 라이브러리(SQLAlchemy Core / pymysql / aiomysql)
- 추론 모델 기본값 (`AGENT_MODEL`, `CODE_SUMMARY_MODEL`)
- 로깅 방식, Langfuse 연결 여부 (kbap-amplitude처럼 키 있으면 켜기 권장)
- 시스템 프롬프트, 숫자 검증 같은 품질 장치 (kbap-amplitude `graph.py`의 이벤트명 검증·숫자 검증을 참고 권장. 핵심 결과 3 대응)
- 라이브러리 정확한 버전 (Vite는 Node 버전과 맞출 것. kbap-amplitude는 Node 20.15에서 Vite 7+ 설치 문제로 6.x 고정한 이력이 있다)

## 환경변수 목록 (backend)

| 이름 | 예시 | 비고 |
|---|---|---|
| `DATABASE_URL` | `mysql://pm:pm@mysql:3306/kbap_pm_agent` | |
| `CORS_ORIGINS` | `https://team-skyjs.github.io,http://localhost:5173` | ADR-6, ADR-18 |
| `ACCESS_TOKEN` | (비우면 비활성) | ADR-7 |
| `PUBLIC_BASE_URL` | `https://pm-agent.example.com` (운영 값은 GitHub Variables에만) | OAuth 콜백 URL 생성 |
| `AGENT_MODE` | `real` / `fake` | ADR-15 |
| `AGENT_MODEL`, `CODE_SUMMARY_MODEL` | `anthropic:claude-sonnet-5-5`, `anthropic:claude-haiku-5-5` (OpenAI로 바꾸면 `openai:gpt-6-luna`) | ADR-20 |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | | 쓰는 쪽만 |
| `AGENT_MAX_TURNS` | `10` | ADR-2 (2026-10-15 사용자 결정: 도구 20→도구 5→모델 턴 10. 비용은 모델 턴에서만 생긴다) |
| `AGENT_TIMEOUT_SECONDS` | `170` | ADR-16 |
| `LLM_BUDGET_USD` | `200` | ADR-9 |
| `AMPLITUDE_MCP_URL` | `https://mcp.amplitude.com/mcp` | EU면 `https://mcp.eu.amplitude.com/mcp` |
| `GITHUB_TOKEN` | | ADR-13 |
| `REPOS_DIR` | `/data/repos` | |
| `TRACK_CALL_PATTERN`, `SCREEN_GLOB` | `track\(EVENTS\.(\w+)`, `src/app/**/*.tsx` | ADR-9 |
| `CODE_GLOB` | `*.{ts,tsx,js,jsx}` | ADR-19 |
