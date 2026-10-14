# 03 QA — 결함 누적 기록

기준: `_workspace/01_cto_api-contract.md` v1.1. 형식: `integration-qa` 스킬 3절.

## 모듈 검증 로그

| 날짜 | 모듈 | 결과 | 비고 |
|---|---|---|---|
| 2026-10-15 | F1 (b27c4ce) | 단독 통과 | `npm run check -- f1` OK, build 자산 경로 `/kbap-pm-agent/`, preview `/kbap-pm-agent/` 200. 실제 B1 왕복·CORS는 T013에서 확인 |
| 2026-10-15 | B1 (1202053) + T013 F1↔B1 | 통과 | `check_b1.py` OK. 실서버 curl: health 키·값 일치, `/api/nope` 404 공통 형식, DB 중단 시 200 degraded, PATCH preflight 허용, 401 `UNAUTHORIZED`(Origin 있으면 CORS 헤더 포함), 토큰 일치 시 404, callback 비인증. headless Chrome: dev(5173)·빌드본 preview 모두 배지 "ok", 백엔드 중단 시 "연결 실패", 해시 `#/settings` 동작. 참고(결함 아님): preview 출처 4173은 기본 `CORS_ORIGINS`에 없어 `CORS_ORIGINS=http://localhost:5173,http://localhost:4173`로 띄워야 한다. 405는 404 `NOT_FOUND`로 응답(계약에 405 코드 없음, 수용) |
| 2026-10-15 | B2 (6b60fd1) T018 | 통과 | `check_b2.py` OK. 실서버 33항목: 계약서 원문 JSON과 키 단위 일치(Summary·상세·Proposal·PATCH 응답·목록 items), null 규칙, 201, 시각 `.mmmZ`, title 0/201자·숫자·깨진 JSON 400, 상세 메시지 순서·user usage null·usage는 purpose=agent만 합산, PATCH note 생략 유지·null 삭제·pending 시 decidedAt null, 400/404 코드, DB enum `adopted`. 참고: MySQL JSON 컬럼이 evidence·measurement 키 순서를 바꿔 내보낸다(값 동일, 계약은 키 순서를 규정하지 않음) |
| 2026-10-15 | F2 (68ffe70)·F4 (dbb9f7d) ↔ B2 | 부분 통과 | headless Chrome 실서버: 목록 수·"새 대화"·제안/채택 수, 카드 4영역 순서, evidence 3종, 퍼널 신규 위치 `src/app/scan.tsx · handleRetry · 398`, 채택 PATCH 본문 계약 일치, 새로고침 유지, 보류→미결정 decidedAt null, 없는 대화 에러 표시. `npm run check` f1~f5 OK. 남은 것: 제목 자동 채움(T045)·fake 제안 카드(T030)·SSE(T026)는 B3 후 |
| 2026-10-15 | B3 (6b82ef0) T022 | 통과 | `check_b3.py` OK. 실서버 SSE 원문: 헤더 `text/event-stream`·`no-cache`·`X-Accel-Buffering: no`, 블록마다 event 1줄+data 1줄+빈 줄, 순서 message_created→(tool_call,tool_result)×2→final, 각 data 키 = 계약 예시(ToolCall·Message·Proposal, `input`은 도구별 자유 형식), final = GET 상세, 제목 앞 40자, usage.costUsd 0, 스트림 전 400(0자·4001자·누락)/404/409 JSON, running 상세 필드 규칙, 끊김 → failed/INTERNAL_ERROR 후 재전송 가능, 대기 15초마다 `: ping` |
| 2026-10-15 | F3·F4·F2 ↔ B3 (T026·T030·T045) | F4·F2 통과, F3 결함 1 | headless Chrome 실서버 fake: 첫 진행 표시 0.74s(SC-004), 진행 문구 택사노미→코드 전환, final 후 카드 2장 4영역 순서·퍼널 기존/신규·위치, 채택 후 새로고침 유지·목록 채택 1, 목록 제목 앞 40자, 409 안내 + 상세 재조회 + 3초 폴링으로 타 클라이언트 실행 반영. 결함 QA-1 |
| 2026-10-15 | QA-1 재검증 (cc53864) | 확인됨 | final 후 헤더 = 앞 40자, 새로고침 전후 동일. T024·T026 체크 |
| 2026-10-15 | B4 (6aa932d) T034 | 결함 1 | `check_b4.py` OK. fake: Settings·repository·taxonomy 응답 키 = 계약, PUT 값 = 시연 모드 표, sync는 syncedAt만, 잘못된 url·빈 branch 400, 택사노미 date 메시지가 계약 원문과 글자 단위 일치, 실패 시 기존 값 유지. real(별도 DB `kbap_pm_agent_qa`, 키 없음): team-skyjs/kbap-fe 공개 클론 1.3s, headCommit 7자, 잘못된 GITHUB_TOKEN으로 PUT·sync 502 `UPSTREAM_ERROR` + lastError 저장 + 기존 클론 유지, 응답·로그·/data·git config에 토큰 문자열 0건, 요약 실패 lastError 저장(LLM 키 없음, 비용 0). 결함 QA-2 |
| 2026-10-15 | F5 (f08981f) ↔ B4 | 저장소·택사노미 통과, Amplitude 미검증 | headless Chrome fake·real: 모드·모델·예산 표시, PUT 본문, fake 값 표시, 동기화 시각 갱신, 파일 원문 그대로 PUT, 업로드 2개, date 위치 오류 표시 + 2개 유지(새로고침 후도), 깨진 JSON·잘못된 URL VALIDATION_ERROR, real lastError 표시. Amplitude 연결은 B7 대기 |
| 2026-10-15 | F6 (70c56b4) | 정적 통과 | 운영 URL로 build + `check -- f6` OK, 자산 `/kbap-pm-agent/`, 번들에 mock 데이터 없음, 레포 이름과 base 일치. 운영 왕복(T060)은 B8 대기. QA-3(운영 CORS 출처) cto |
| 2026-10-15 | B5 (9a23420) T038 | 통과 (실제 요약 LLM 미검증) | `check_b5.py` OK(가짜 요약기: building→ready, 재동기화 요약 0회, 파일 1개 변경 1회, read_code 200줄, search_code 30건, 단가표). 실서버: `LLM_BUDGET_USD=0` → 메시지 403 `BUDGET_EXCEEDED` JSON, 메시지 저장 안 됨, 목록·상세 200, 프론트 입력창 아래 안내 + 입력 유지. real 키 없음: codeMapStatus building→failed + lastError, spentUsd 0. 실제 요약 비용 증가(SC-006)는 키 필요 |
| 2026-10-15 | B6 (8cb3321) | BE 통과, T042 미검증 | `check_b6.py` OK(가짜 채팅 모델로 실제 create_agent 루프: 도구→구조화 final, 도구 예외 failed 후 계속, 호출·시간 상한 부분 final, 모델 실패 error). 정적: 제안 직렬화 by_alias로 null 키 유지, 모델명 하드코딩 없음, 소스 상태 문장. 실서버 real 키 없음: SSE message_created→error `UPSTREAM_ERROR` + assistantMessageId, DB failed·content ""·usage null, 프론트가 저장된 실패와 스트림 error 모두 code별 문구로 표시, 비용 0. T042(실제 질문 4부분 제안·openai 교체·성능)는 LLM 키 없어 미검증 |
| 2026-10-15 | QA-3 (d32661a) | 확인됨 | ADR-18 운영 출처 `https://team-skyjs.github.io`, ADR 환경변수 표·T056 정정 확인 |
| 2026-10-15 | B7 (ef2cfce) | fake 통과, real 승인 미검증 | `check_b7.py` OK(도구 예외·도구 목록 실패에도 final). 실서버 fake: connect 응답 = 계약 예시 원문, 직후 settings.amplitude connected·connectedAt ISO·키 = 계약, callback 3종 200 `text/html` 한 줄 문구(성공 문구는 real 승인 필요). real 동적 등록·승인·토큰 교환·list_tools·재시작 유지·실제 metric 근거(T046 후반·T050)는 사람 승인과 Amplitude 계정이 필요해 미검증 — QA가 외부에 OAuth 클라이언트를 추가 등록하지 않으려고 real connect도 호출하지 않음 |
| 2026-10-15 | F5 ↔ B7 (T052·T054 fake) | fake 통과 | headless Chrome: 연결 안 됨 → 클릭 시 새 탭이 계약 예시 authorizationUrl로 이동(외부 요청은 가로채 막음), 3.2s 뒤 "연결됨 (시각)" + "연결되었습니다.", 이후 폴링 중단. T054 real 모드 Amplitude 항목은 미검증 |
| 2026-10-15 | B8 (f2890fe) | 결함 1, 운영 미배포 | 별도 컨테이너(fake, FAKE_DELAY_SECONDS=21)에서 `check_b8.py` OK: health, preflight, SSE 105초 유지·ping 5회·final. 배포 파일 정적: 이미지·monitor-net·127.0.0.1:8001·/data 볼륨·healthcheck·db ok 확인·.env.prod gitignore 확인. 결함 QA-4. 운영 배포는 홈서버 SSH·Docker Hub 권한이 필요해 미실행 → T057·T060 미검증 |
| 2026-10-15 | QA-2·QA-4 재검증 (5c5a6ad) | 확인됨 | kbap-fe f34c518 real 클론: trackedEventCount 117 = `rg -o -g '*.{ts,tsx,js,jsx}'` 117, index.json 비코드 파일 0, search_code `**/*.md` 0건, read_code가 md·저장소 밖 경로 거부. check_b4·b5 OK. deploy env 예시·check_b8 출처 team-skyjs.github.io, check_b8(FAKE_DELAY 21) health·preflight team-skyjs·SSE 105초 OK. 참고: 117곳 중 17곳은 `__tests__` 파일의 문자열 매치(ADR-19 범위 안, 남은 위험으로 기록) |
| 2026-10-15 | T061 최종 (fake) | 통과, real 미검증 | 계약 diff 없음, check_b1~b7·check-f1~f6 OK, check_b8 별도 컨테이너 OK, quickstart 시나리오 1~10 실서버 + headless Chrome 통과, 열린 결함 0. real 시나리오는 T042·T050·T057·T060에 막혀 T061 미체크. 리포트 `_workspace/03_qa_report.md` |
| 2026-10-15 | 출처 구조 대응 (67c6f3a + check_b8 작업 트리) · F1·F6 mock 삭제 (0b98411) | 통과 | check_b8이 git remote로 기대 출처 계산: 서버 출처 simhani1이면 preflight 400으로 실패, team-skyjs면 통과, git 없는 컨테이너는 EXPECTED_ORIGIN 요구로 실패. check_b8 변경은 미커밋. 프론트 mock 참조 0, check-f1~f6 OK, 운영 빌드 자산 경로, 헬스 ok, F3 SSE 화면 흐름 통과 |
| 2026-10-15 | check_b8 커밋 확인 (680ba9e·4a512df) | 확인됨 | 680ba9e = QA가 검증한 작업 트리와 동일. 4a512df: PASS 줄에 기대 출처 근거 표시("기대 출처: git remote"), EXPECTED_ORIGIN 폴백에 한계 주석. 레포 안 실행으로 team-skyjs 서버 preflight 통과 재확인 |
| 2026-10-15 | T072 헌법 정합 (d3302ae) | 결함 1(문서) | 헌법 v1.1.0 기술 제약 백엔드 줄 = ADR-20(공식 SDK, Claude tool runner, openai-agents, LangChain 미사용, 접두사 선택). 원칙 I~V 문구 무변경. plan.md Constitution Check·data-model.md에 개정 전 문구 잔존 → QA-5 |
| 2026-10-15 | QA-5 재검증 (155daef) | 확인됨 | T072 체크 |
| 2026-10-15 | B9 (9e1c2c6) T071 | 통과, 결함 1(문서) | 계약 diff 없음. backend/app·pyproject·uv.lock·설치 패키지에 langchain 0. check_b1~b7 OK(check_b6: 두 런타임 가짜 전송으로 SSE 순서·final=Message·llm_usage·도구 예외 failed 후 계속·location null·refusal UPSTREAM_ERROR·호출/시간 상한 부분 final·foo:bar 기동 실패, check_b7: 가짜 MCP 서버로 두 런타임 amplitude 성공/실패). fake SSE 원문의 이벤트 이름·data 키 구조가 전환 전 기준선과 diff 0. 정적: 내부 이벤트 형식·`conversations.py` 무변경, 공통 래퍼가 tool_call→tool_result 순서. real 무키 실서버: anthropic·openai 둘 다 message_created→error UPSTREAM_ERROR + DB failed, `foo:bar`면 기동 실패, 비용 0. 프론트 무변경으로 check-f1~f6 OK, 채팅·제안(첫 진행 0.76s)·목록·채택·Amplitude 화면 흐름 통과. 결함 QA-6 |
| 2026-10-15 | B9 cto 추가 확인 (b3c572d) + QA-6 재검증 (da85244) | 통과 | (1) anthropic 1.13.0이 httpx2 사용·설치 확인(T069 정정 문구와 일치). (2) openai-agents 트레이스: DefaultTraceProvider `_manual_disabled=True`, 가짜 전송 실행 + force_flush 뒤 트레이스 URL 송신 0. (3) MCP 오류 두 경로 × 두 런타임(QA 스크립트, 가짜 FastMCP + 클라이언트 `call_tool` 예외 주입): isError 결과·클라이언트 예외 모두 `tool_result failed` → `final`. 참고: check_b7의 "MCP 예외"는 FastMCP가 isError로 바꿔 보내는 경로라 클라이언트 예외 경로는 검사 스크립트에 없다. QA-6: 운영 env 예시에 OpenAI 예시·키 조건 주석 확인, T068 체크 |
| 2026-10-15 | check_b7 클라이언트 예외 경로 (a75addd) | 통과 | 재빌드 컨테이너(= 커밋본)에서 check_b7 OK: 두 런타임 × MCP 성공·isError·ConnectionError·연결 실패. 첫 실행은 backend-dev 수정 중 같은 검사용 DB를 동시에 써 저장 단계 IndexError로 실패했고, 단독 재실행은 통과(결함 아님). 리포트 남은 위험 항목 닫음 |
| 2026-10-15 | T075 턴 상한 (7dbeab6) | 통과 | 계약 diff 0(f11d5b9 비고 문구 반영 확인). `AGENT_MAX_TOOL_CALLS` 잔존: backend·deploy·.env.example·docker-compose.yml·.github·루트 .env 0건(범위 밖 `docs/architecture/agent-loop-langchain.*` 2건, LangChain 시절 구조도). 재빌드 컨테이너(= 커밋본) check_b1~b7 OK, check_b6 AGENT_MAX_TURNS=2 병렬 2개 = 1턴·모델 요청 2회·도구 3회 후 부분 final. QA 추가: 기본 10턴에서 도구만 돌려주는 가짜 모델 → 두 런타임 모두 모델 요청 10회·tool 쌍 10·부분 final 첫 줄 = 계약 문구 "모델 호출 상한(10턴)에 도달해 여기까지의 조회 결과로 답합니다."·status completed·proposals []. fake SSE 이벤트·키 구조 기준선과 diff 0. 참고: 모델이 없는 도구 이름을 부르면 openai는 ModelBehaviorError로 실행 전체 UPSTREAM_ERROR, anthropic은 오류 결과로 계속(남은 위험) |
| 2026-10-15 | 주석 정리 frontend (1430a07) | 통과 | 코드 변화 0: 바뀐 TS 15개 모두 esbuild 변환 결과 동일, style.css는 주석 1줄만. check-f1~f6 OK, 계약 diff 0. frontend 주석의 내부 식별자 8줄→0, 종결형 어미 32줄→0 |
| 2026-10-15 | 주석 정리 backend (d24edde) | 통과, 결함 1(기존) | 코드 변화 0: 바뀐 .py 24개 docstring 제외 AST 동일, schema.sql·Dockerfile은 주석 줄만. 재빌드 컨테이너(= 커밋본) check_b1~b7 OK, 계약 diff 0. backend 주석 내부 식별자 24줄→0, 종결형 82줄→1(`backend/checks/check_b6.py:41` "돈다"; 정규식이 잡은 나머지 3줄은 명사 "필요" 오탐). 저장소 전체(주석 감사 대상 41개 파일): 식별자 32→0, 종결형 114→1. 도구 docstring 문구는 모델에 가는 도구 설명이라 문체만 바뀐 것 확인(의미 동일). 정리와 별개로 QA-7 발견 |
| 2026-10-15 | QA-7 재검증 (dbf5428) | 확인됨 | 재빌드 컨테이너(= 커밋본)에서 두 런타임 도구 스키마의 매개변수 9개 모두 description, check_b1~b7 OK, backend/app docstring 외 코드 변화 0, 계약 diff 0. 저장소 주석 잔존: 식별자 0, 종결형 0(정규식 4줄은 명사 "필요" 오탐). T063 재체크. ADR-21은 c636aab로 되돌려져 T078 대상 아님 |
| 2026-10-15 | Amplitude MCP 도구 허용 목록 (41c6193) | 통과 | 워크트리 이미지를 별도 컨테이너·별도 DB로 실행(메인 스택 무접촉): check_b1~b7 OK, check_b7 허용 목록 시나리오 두 런타임 통과. QA 직접 덤프(가짜 MCP 서버가 도구 5개 제공, 저장소·택사노미 등록): 모델 요청 도구가 기본값에서 두 런타임 모두 8개 = 우리 6 + get_amplitude_context·query_amplitude_data(create_chart·save_chart_edits·query_dataset 제외), `AMPLITUDE_TOOLS` 빈 값이면 11개(전부). 거르기 지점은 `amplitude.keep()` 하나. 시스템 프롬프트 7번 "차트를 만들거나 수정·저장하지 않는다". 기본값이 코드·env 예시 2곳·배포 워크플로우에서 같음. 계약 diff 0. 이 커밋 diff·메시지에 운영 호스트·경로 0. 참고: 기반 main의 deploy 스크립트 3개에 서버 경로·ssh 별칭 기본값이 남아 있음(spec 002 T011 범위). 첫 실행 이미지는 작업 트리에서 빌드해 backend-dev 후속 미커밋 변경이 섞였을 수 있어, `git archive 41c6193`으로 다시 빌드해 검사·덤프를 재실행했고 결과 동일 |
| 2026-10-15 | 도구 결과 상한 + 프롬프트 8번 (136e3cf) | 통과 | `git archive 136e3cf` 이미지(별도 DB)로 check_b1~b7 OK(check_b6 두 런타임 5,002자 → 모델 3000자+생략·DB 원문, check_b7 두 런타임 MCP 모델 사본 잘림·DB·이벤트 원문). QA 직접: 기본값 3000에서 5,002자 MCP 결과 → 두 런타임 모두 모델 사본 = 원문 앞 3000자 + "…(5002자 중 3000자, 이하 생략)", SSE tool_result summary는 원문 첫 줄·succeeded, DB result_text 5002자(OpenAI MCP 경로 포함). 프롬프트 8번 문구 확인. `TOOL_RESULT_MAX_CHARS=3000`이 .env.example·deploy env 예시·deploy-backend.yml에 존재. 계약 diff 0, 커밋 diff·메시지 운영 정보 0 |
| 2026-10-15 | PR #7 리뷰 반영 (8eaca95) | 통과 | `git archive 8eaca95` 이미지(별도 DB)로 check_b1~b7 OK, check_b7 새 시나리오 4개(두 런타임 × 허용 목록 0건 일치·텍스트+이미지 결과) 통과. QA 덤프: `AMPLITUDE_TOOLS=no_such_tool`이면 두 런타임 모두 모델 요청 도구 6개(우리 도구만)·시스템 프롬프트에 "허용 목록 불일치", 기본값 8개·빈 값 11개 회귀 없음, 결과 상한 덤프 회귀 없음. 계약 diff 0, 운영 정보 0. 같은 이름·인자 반복 시 원문 보관 FIFO 건은 PR에서 기각(미수정) |

## 결함

### QA-1: 첫 메시지 전송 후 채팅 헤더 제목이 새로고침 전까지 "새 대화"로 남는다
- 모듈: frontend / F3 (T024)
- 경계면: POST /api/conversations/{id}/messages 응답 이후 화면 상태
- 기대: 계약서 ConversationSummary "`title`: 생성 시 지정하지 않으면 `null`. 첫 사용자 메시지가 저장될 때 앞 40자로 채운다." 서버는 message_created 시점에 이미 제목을 채운다(GET 상세 `title` = 앞 40자 확인). 같은 화면의 왼쪽 목록은 재조회로 새 제목을 보여준다
- 실제: `frontend/src/Chat.tsx` `<h3>{detail.title ?? '새 대화'}</h3>`의 `detail.title`은 최초 GET 값(null) 그대로. onEvent는 messages만 갱신하고 final·스트림 종료 후 상세를 다시 읽지 않는다. 재현: 새 대화 → 질문 전송 → final 후 헤더 "새 대화", 새로고침하면 "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘 — 제목 자동"
- 수정 방향: 프론트. final(또는 스트림 종료) 뒤 `load()`로 상세를 다시 읽거나, title이 null이면 message_created 때 userMessage.content 앞 40자로 채운다(서버 규칙 복제보다 재조회 권장)
- 수신: frontend-dev
- 상태: 확인됨 (cc53864: 스트림 종료마다 load(). 재검증 통과)

### QA-2: 이벤트 인덱스가 코드 밖 문서 파일(specs/*.md)의 track 호출까지 센다
- 모듈: backend / B4 (T031 `backend/app/repo.py`)
- 경계면: GET /api/settings, PUT·sync 응답 `repository.trackedEventCount` / 이후 `find_event_calls` 결과 → code 근거 `file`, 신규 이벤트 `location`
- 기대: ADR-9 "ripgrep으로 TRACK_CALL_PATTERN을 훑어 이벤트→파일:줄 목록". 계약서 Proposal code 근거 `file`은 코드 파일(저장소 루트 기준 상대 경로). T034 기준 "trackedEventCount가 `rg -c 'track\(EVENTS\.'` 합과 같은지"
- 실제: `backend/app/repo.py` `build_index`가 `rg ... -e PATTERN .`로 저장소 전체를 훑는다. team-skyjs/kbap-fe develop(f34c518): trackedEventCount 120 = ts/tsx 117 + `specs/004-inbox-server/tasks.md` 2 + `specs/001-notification-settings/tasks.md` 1. `rg -c` 줄 합은 119(tasks.md 한 줄에 2회). 문서 위치가 인덱스에 들어가 에이전트가 `specs/.../tasks.md:40`을 코드 근거로 인용할 수 있다
- 수정 방향: 백엔드. rg에 소스 글로브를 준다(예: `-g '*.{ts,tsx,js,jsx}'` 또는 `--type ts --type js`, 필요하면 환경변수 `TRACK_CALL_GLOB`). 수정 후 kbap-fe에서 117이어야 한다. 세는 단위(줄 vs 호출)는 호출 수(-o)가 맞다고 본다 — T034 문구의 `rg -c`는 줄 수라 1 차이가 날 수 있음
- 수신: backend-dev
- 상태: 확인됨 (5c5a6ad ADR-19 CODE_GLOB, kbap-fe 117). 이전 메모: d32661a로 T034 기준이 저장소 전체 `rg -o | wc -l`=120이 되어 문서 파일 매치를 그대로 통과시킨다. 기준을 소스 파일로 한정해야 한다고 cto에 전달)

### QA-3: 운영 CORS 출처(simhani1.github.io)가 레포 소유자(team-skyjs)와 다르다
- 모듈: 계약/ADR (B8·F6 배포 전)
- 경계면: 운영 GitHub Pages → 백엔드 CORS preflight
- 기대: ADR 환경변수 표 `CORS_ORIGINS` = `https://simhani1.github.io,http://localhost:5173`, T056 `Origin: https://simhani1.github.io` preflight
- 실제: `git remote` origin = `https://github.com/team-skyjs/kbap-pm-agent.git`, `.github/workflows/pages.yml`은 이 레포에서 배포 → Pages 출처는 `https://team-skyjs.github.io`. 그대로면 운영에서 모든 요청이 CORS로 막혀 프론트가 "연결 실패"
- 수정 방향: CTO가 운영 출처를 확정해 ADR·T056·운영 `.env`의 CORS_ORIGINS를 맞춘다(배포 레포가 simhani1 포크면 그대로 두고 그 사실을 ADR에 명시)
- 수신: cto
- 상태: 확인됨 (d32661a ADR-18: 운영 출처 team-skyjs.github.io, T056 정정)

### QA-4: B8 운영 env 예시와 check_b8의 출처가 ADR-18 이전 값(simhani1.github.io)이다
- 모듈: backend / B8 (T055·T056)
- 경계면: 운영 GitHub Pages → 백엔드 CORS preflight
- 기대: ADR-18 "운영 `CORS_ORIGINS`에는 `https://team-skyjs.github.io`", ADR 환경변수 표 `CORS_ORIGINS` = `https://team-skyjs.github.io,http://localhost:5173`, T056 "`Origin: https://team-skyjs.github.io` preflight 통과"
- 실제: `deploy/kbap-pm-agent.env.example` `CORS_ORIGINS=https://simhani1.github.io`, `backend/checks/check_b8.py:12` `origin = "https://simhani1.github.io"`. 이 예시로 .env.prod를 만들면 운영 Pages의 모든 요청이 CORS로 거부되고, check_b8은 틀린 출처로 통과해 그 사실을 숨긴다
- 수정 방향: 백엔드. 두 곳을 `https://team-skyjs.github.io`로. check_b8은 출처를 환경변수로 받지 말고 ADR 값 고정(검사가 운영 설정을 따라가면 검사가 아니다)
- 수신: backend-dev
- 상태: 확인됨 (5c5a6ad. 같은 출처 결함 2회째(QA-3→QA-4)라 재발 시 cto에 구조 원인 보고)

### QA-5: 헌법 v1.1.0 개정 뒤 plan.md·data-model.md에 개정 전 문구가 남았다
- 모듈: 문서 / Phase 8 (T072)
- 경계면: 헌법 ↔ plan.md Constitution Check, data-model.md
- 기대: 헌법 v1.1.0 Sync Report "Follow-up: plan.md Constitution Check의 \"불일치(개정 대기)\" 표시를 T072에서 해소". 기술 제약 "LLM 호출은 공급자 공식 SDK로 한다 … LangChain 계열은 쓰지 않는다"
- 실제: `specs/001-pm-agent-prototype/plan.md:63` "**불일치(개정 대기)**: 헌법 기술 제약의 \"백엔드: Python 3.12, FastAPI, LangChain 1.x\"가 ADR-20과 어긋난다" 그대로. `specs/001-pm-agent-prototype/data-model.md:85` llm_usage.model 설명 "`init_chat_model` 문자열 그대로"(ADR-4 대체됨, ADR-20은 `provider:model` 접두사 문자열)
- 수정 방향: CTO. plan.md:63을 "일치(헌법 v1.1.0, d3302ae)"로, data-model.md:85를 "`AGENT_MODEL`·`CODE_SUMMARY_MODEL` 문자열 그대로(`provider:model`, ADR-20)"로. 백엔드 코드·`.env.example:13`의 LangChain 잔존은 B9(T062~T068) 범위라 B9 완료 시 QA가 확인
- 수신: cto
- 상태: 확인됨 (155daef: plan.md:63 "일치(헌법 v1.1.0, d3302ae)", data-model.md:85 provider:model. specs·.specify의 남은 LangChain 언급은 미사용을 밝히는 문장뿐)

### QA-6: 운영 env 예시에 OpenAI 전환 주석과 OPENAI_API_KEY 조건 안내가 없다
- 모듈: backend / B9 (T068)
- 경계면: 운영 설정(배포 env) — 런타임 선택 접두사
- 기대: T068 "`.env.example`, `deploy/kbap-pm-agent.env.example`: … OpenAI로 바꾸는 예시(`openai:gpt-6-luna`)는 주석으로, `OPENAI_API_KEY`는 openai 접두사일 때만 필요하다고 적는다"
- 실제: `.env.example:14·18`에는 있다. `deploy/kbap-pm-agent.env.example:9~12`는 `AGENT_MODEL`·`CODE_SUMMARY_MODEL`·`ANTHROPIC_API_KEY=`·`OPENAI_API_KEY=` 값만 있고 두 안내가 없다. 운영자가 openai로 바꿀 때 두 변수를 같은 접두사로 맞춰야 한다는 사실(다르거나 틀리면 기동 실패)을 알 길이 없다
- 수정 방향: 백엔드. `.env.example`의 두 주석을 운영 예시에도 옮긴다
- 수신: backend-dev
- 상태: 확인됨 (20355dd·da85244: 접두사 규칙, openai 예시, ANTHROPIC/OPENAI 키 조건 주석)

### QA-7: 에이전트 도구 6개의 docstring에 매개변수 설명(Args 절)이 없다
- 모듈: backend / B9 (T063, 주석 정리 전부터 있던 공백)
- 경계면: 백엔드 → LLM 공급자 도구 스키마(두 런타임 모두 docstring을 도구 설명 원천으로 쓴다)
- 기대: T063 "타입 힌트와 docstring(Args 절)이 도구 스키마의 원천이다"
- 실제: `backend/app/code_tools.py`의 `find_event_calls(eventName)`, `search_code(regex, glob)`, `get_screen_summary(path)`, `read_code(path, startLine, endLine)`, `search_taxonomy(query)`, `get_event_definition(name)` 모두 한 줄 요약만 있고 Args 절이 없다(d24edde~1과 d24edde 동일). 모델은 매개변수 이름과 타입만 보고 `glob` 형식, `startLine`이 1부터인지, `path`가 저장소 루트 기준인지 등을 docstring 첫 줄에서 추측해야 한다. QA가 B9(T071)에서 T063을 통과시킬 때 놓쳤다
- 수정 방향: 백엔드. 각 함수에 `Args:` 절로 매개변수마다 한 줄(형식·범위). 두 런타임이 Args를 매개변수 description으로 옮기는지 check_b6의 요청 파라미터 assert에 하나 추가
- 수신: backend-dev
- 상태: 확인됨 (dbf5428: 도구 6개 Args 절. anthropic beta_async_tool·openai function_tool 스키마 모두 매개변수 9개 description 확인, check_b6 요청 파라미터 assert 추가)
