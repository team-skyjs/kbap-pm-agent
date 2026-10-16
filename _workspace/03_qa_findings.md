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
| 2026-10-15 | 운영 배포 T057·T060 (fix/prod-hostname 75ddea5) | 조회 범위 통과, 일부 미검증 | T057: 레포 안 check_b8 재현 — health PASS, preflight team-skyjs.github.io(from git remote) PASS, SSE 100초 SKIP(real). 운영 health 200 0.35s, 없는 경로 404 공통 형식, 허용 안 된 출처 preflight 400. **ACCESS_TOKEN 꺼짐**: 토큰 없이 대화 목록·설정 200(설정 응답에 비밀값 없음). T060: headless Chrome으로 운영 Pages 200, 자산 `/kbap-pm-agent/`, 헬스 배지 ok, 대화 목록 1개 = API, 대화 상세 메시지 4 = API, 설정 화면 real·저장소·택사노미 45개 표시, 번들에 운영 API 주소·localhost 없음. 쓰기 요청은 브라우저 단 차단(0건 발생). 미검증: cloudflared 경유 SSE 장시간 ping(T057), Pages에서 SSE·채택 왕복(T060) — 메시지 전송·PATCH 금지 범위. 관찰(사용자 실행 1건, 조회만): Anthropic 실제 구조화 응답 completed, 소스 3종 사용, 첫 tool_call 약 11초(SC-004 5초 초과)·final 약 53초, 질문 1건 $1.601(입력 780,309 토큰) |
| 2026-10-15 | 운영 식별자 정리 (chore/scrub-ops-identifiers b18b17c..a59c1b8) | 통과 | 지정 grep 결과는 QA 리포트 예시 2줄뿐이었고 이 브랜치에서 `pm-agent.example.com`으로 교체해 0건. 계약: 예시 문구 2곳과 변경 이력 1줄만 바뀌고 원본·분할본 diff 0, fake 승인 URL과 examples.AUTH_URL이 계약 예시와 글자 단위 동일. 배포: compose ENV_FILE 필수(없으면 config 종료 1), deploy 스크립트 COMPOSE_FILE·ENV_FILE 없으면 docker 호출 전 종료 1, push 스크립트 REMOTE_DIR 없으면 원격 호출 전 종료 1, 원격 실행에 두 경로 명시. CI 경로: deploy-backend.yml 115·116줄이 COMPOSE_FILE·ENV_FILE을 넘기고, 같은 env로 가짜 docker·curl을 둔 deploy 스크립트가 pull·up·health·완료까지 종료 0. `git archive a59c1b8` 이미지(별도 DB)로 check_b1~b7 OK. 프론트 변경 0. 추가된 줄·커밋 메시지의 운영 식별자 0 |
| 2026-10-15 | 003 US-001 디자인 토큰 (94971e9) | 통과 | 커밋본 frontend·backend를 따로 빌드(공용 스택 무접촉, preview + 별도 fake 백엔드). npm run check f1~f5 OK, 빌드 후 f6 OK, 계약 diff 0. 번들 365.4KB(gzip 114.0KB), 재설계 전 기준선 362.5KB 대비 +2.9KB. 원시 값: style.css 토큰 정의 밖 0(동작 줄이기의 시간 토큰 재정의만), TSX 인라인 1건(설정 입력 폭, 설정 재스타일 때 이동 예정). Playwright 라이트·다크 × 1280/768/375 × 채팅·설정: 본문 16px·줄 간격 1.60, 보이는 글자 전부 명도 대비 4.5 이상(최소 라이트 5.99, 다크 4.51 = "새 대화" 버튼, 여유 0.01), 포커스 윤곽선 solid 2px, 동작 줄이기에서 전환 0s. 기준선(ea4a100)은 보조 텍스트 14px·대비 미달 23~47곳·axe color-contrast 7~11건 → 해소. 재설계 전부터 있던 것(이번 변경 무관, 해당 모듈에서 재확인): 375px 가로 스크롤(채팅 560px·설정 726px), axe critical label 1(설정 입력), serious scrollable-region-focusable 1(채팅). 흐름 회귀(질문→진행 0.7s→카드 2장→채택→새로고침 유지, 409 안내) 통과 |
| 2026-10-15 | 003 뼈대·렌더러·파서 (030e50c·91e5c19·2b89291) + 셸·사이드 패널·메시지 (01306ec) | 결함 1 | 커밋본(01306ec) 별도 빌드·별도 fake 백엔드. npm run check f1~f5·f7 OK, 빌드 후 f6 OK, 계약 diff 0. check:ui smoke 9프로젝트 9/9, 스크린샷 9장(T005). 원시 값: style.css 토큰 밖 0(동작 줄이기 시간 재정의·768px 분기점만), TSX 인라인 1(설정 입력 폭). Markdown: HTML 해석 플러그인 없음, 링크 target=_blank rel=noopener noreferrer, ChartBlock lazy. 번들 371.7KB(+9.2KB); 01306ec 시점에는 Markdown 미연결이라 차트 청크가 빌드에 없음 → 청크 분리·차트 미로드는 US6에서. Playwright 라이트·다크 × 1280/768/375: 본문 16px·lh 1.60, 대비 미달 0(최소 라이트 5.17, 다크 4.51), 375 가로 스크롤 해소(이전 560·726px), 동작 줄이기 0s. 셸: 1280 접기 새로고침 유지·접힌 패널 포커스 없음, 768·375 닫힌 Drawer에 Tab 안 들어감, 열림 role=dialog·body overflow hidden, ESC·배경 탭 닫힘. 키보드만으로 새 대화→입력→보내기→채택 가능. 메시지: 사용자만 배경, 1600px에서 본문 768px 가운데, 375 넘침 0. axe 남은 2건(재설계 전부터): serious scrollable-region-focusable = 제안 카드 코드 근거 `<pre>`(US9), critical label = 설정 택사노미 file input(US10). 결함 UI-1 |
| 2026-10-15 | 003 마크다운·차트 연결 (d113e08·4947e82·b872d66·3d9f2e9) | 커밋본 기준 통과, T019 대기 | 원격 HEAD 3d9f2e9 커밋본만 따로 빌드(공유 트리의 designer 미커밋 style.css 제외). check f1~f5·f7·f8 OK, f6 OK. 번들 592.2KB = 기준선 대비 +229.7KB(≤300), ChartBlock 별도 청크 164.8KB(≤200), index.html은 차트 청크를 선로딩하지 않고 차트 없는 대화·설정 화면에서 차트 청크 요청 0. check:ui 27 통과·9 실패: smoke 9·us6 18 통과, us5 9개 모두 마지막 단언 `.md-table-scroll` overflow-x=visible로 실패 → designer T019 미커밋(공유 트리 미커밋 상태에서는 36/36이라는 frontend-dev 보고와 일치). Markdown SSR: `javascript:`·`data:` 링크 href 비움, `<img onerror>`·`<a href=javascript:>`는 글자로 표시. 화면 회귀: 채팅 라이트·다크 3폭 대비 미달 0·가로 스크롤 0·동작 줄이기 0s. 흐름 회귀: 질문→카드→채택→새로고침 통과, 409 안내는 `p.error.notice`로 표시·입력 유지(기존 QA 스크립트의 `.chat .error` 선택자만 낡음). 제안: 409·오류 안내가 aria-live 영역 밖(US8·US11에서) |
| 2026-10-15 | 003 셸 보완·마크다운 표현·입력창·상태 + us2 (원격 HEAD 4a442e5 커밋본) | UI-1 확인됨, 결함 1 | 커밋본만 빌드(공유 트리 미커밋 제외). check f1~f8 OK, check:ui 45 통과·9 건너뜀(폭 전용), us2의 Drawer 포커스 단언·us5 표 스크롤 통과. 번들 602.2KB(+239.7KB), 차트 청크 164.8KB, 차트 없는 화면 차트 요청 0. 셸(QA 스크립트): 768·375 Drawer Tab 0/16 이탈, ESC 뒤 메뉴 버튼 복귀 → UI-1 확인됨. 화면: 라이트·다크 3폭 대비 미달 0(다크 최소 4.51 = 설정 "저장" 버튼), 가로 스크롤 0, 채팅 axe 심각·중대 0(제안 카드 재설계로 `<pre>` 해소), 설정 label critical 1 남음(US10). 키보드: 새 대화→입력(Tab 79, 새 대화 뒤 포커스가 버튼에 남아 목록 14개를 지남)→보내기→채택 가능. 입력창: Shift+Enter 줄바꿈, 조합 중 Enter 무시, Enter 전송, 12줄에 약 6줄 높이·내부 스크롤. 상태: 전송 직후 .typing, 진행 "조회 중"+입력 비활성+aria-live polite, 완료 .md만, 부분 완료 .notice-block 사유 첫 문장, 오류 .error-row+다시 시도로 질문 복원·포커스, 동작 줄이기 애니메이션 0s. 채택: PATCH 계약 본문, 머리 라벨 "채택"·새로고침 유지·목록 채택 1, 메모·되돌리기·결정 시각 유지. 흐름 회귀 통과(QA 스크립트 선택자만 재설계 마크업으로 갱신). 제안: 새 대화 뒤 입력창으로 포커스 이동. 결함 UI-2 |
| 2026-10-15 | 003 제안 카드(4a442e5)·설정·접근성(703981d)·코드 근거(a0cda6c)·chart 지시(315c2a2) — 원격 HEAD 315c2a2 커밋본 | 통과, UI-2 열림 | check f1~f8·f6 OK, check:ui 45 통과·9 건너뜀, TSX 인라인 style 0, 계약 diff 0. 번들 604.3KB(+241.8KB), 차트 청크 164.8KB. 백엔드: 프롬프트에 규칙 10(chart 지시+선 예시) 한 줄만 추가·모델명 0, check_b9 OK(예시 한 글자 바꾸면 종료 1), 커밋본 이미지 check_b1~b7 OK. 화면: 라이트·다크 3폭 × 채팅·설정 대비 미달 0, 가로 스크롤 0, axe 심각·중대 0(설정 file input label·코드 근거 pre 해소). 카드: 기본 펼침 [근거 닫힘, 제안 열림, 실행 닫힘, 측정 닫힘], 상태 라벨 미결정/채택, 근거·퍼널 라벨 글자, 메모 aria-label, 퍼널 표 스크롤 영역 tabIndex 0·aria-label·키보드로 도달, 채택 PATCH·새로고침 유지·메모·되돌리기·결정 시각 유지. 설정: 토큰 저장(localStorage), 저장소 등록 PUT 본문·라벨 등록됨·동기화 시각 갱신, 택사노미 업로드 2개·date 위치 오류·2개 유지·role=status, Amplitude 연결 라벨, 파일 입력 Tab 도달·라벨 윤곽선 2px, Tab 순서 = 화면 순서. 차트 스크린샷(us6 dark): 본문 폭, 다크 토큰, 대체 표 숨김. 키보드 흐름·흐름 회귀(QA 스크립트를 재설계 마크업으로 갱신) 통과. 제안(낮음): 409 안내가 다른 실행이 끝난 뒤에도 남음, 새 대화 뒤 포커스가 입력창으로 가지 않음 |
| 2026-10-15 | 003 최종 (원격 HEAD 88a30db 커밋본) | 통과, 열린 결함 0 | check 7/7·f6 OK, 계약 diff 0. check:ui 3회 연속 247 통과·50 건너뜀·실패 0(건너뜀: 세션 만료 fixme 18 — 접근 제한 병합 때 연결, live 9 — CHECK_UI_LIVE=1 전용, 정적 검사 1회만 8, reduced 전용 6, 넓은 화면 전용 6, 좁은 화면 전용 3). 검사 코드에 waitForTimeout 0. 백엔드 b1~b7·b9 OK, b8(fake 지연 21, 별도 컨테이너) health·preflight·SSE 105초 OK. 번들 604.7KB(gzip 193.9KB), 재설계 전 대비 +242.2KB(차트 청크 164.8KB, 차트 제외 +77.4KB), 차트 없는 화면 차트 요청 0. 라이트·다크 × 1280/768/375 × 채팅·설정: 본문 16px·lh 1.60, 대비 미달 0(최소 라이트 5.17, 다크 6.37), 가로 스크롤 0, axe 심각·중대 0, 카드 전부 펼침·375 Drawer 열림도 axe 0. UI-2 확인됨: 401 UNAUTHORIZED에 배너 없음, #chat-hint "접근 토큰이 없거나 맞지 않습니다. 설정에서 확인하세요"+#/settings 링크, 입력 유지. 새 대화 Enter 뒤 포커스가 입력창. 409 안내는 다른 실행이 끝나면 기본 안내로 돌아감(88a30db). 흐름 회귀(실제 fake 백엔드, 진행→완료 live 경로 포함) 통과. 다크 "저장" 대비: 4a442e5는 클래스 없는 기본 버튼 rgb(236,236,236)/rgb(107,107,107) = 4.511, 703981d 이후 btn primary rgb(13,13,13)/rgb(110,168,254) = 8.047 → 측정 기준 차이가 아니라 버튼 스타일 변경. 참고: us8 live 시나리오는 대화 생성을 localhost:8000으로 고정해 이 브랜치에선 실행 불가(접근 제한 병합 뒤 같은 출처 전제), QA가 시도하다 공용 개발 DB(8000)에 빈 대화를 프로젝트 수만큼 만들었다 |
| 2026-10-15 | 409 안내 보강 (134d5aa, Codex 반영) | 통과 | 커밋본: check 7·f6 OK, check:ui 247 통과·50 건너뜀·실패 0. 다른 실행 중 409 → 실행 중 표시·입력·보내기 비활성·안내 표시, 그 실행이 끝나면 안내가 기본 안내로 돌아가고 입력값 유지. 이전 재조회가 늦게 도착하는 순서는 us8 케이스 추가 예정(frontend-dev) |
| 2026-10-15 | PR #13 Codex 2건 (f1afd83) | 통과, 결함 1(검사 인프라) | 정적: fixtures가 항상 가로챔(LIVE 단락 제거), us8의 test.skip(LIVE) 제거·live 테스트만 skip(!LIVE), Markdown이 memo로 감싸짐, us6에 캔버스 MutationObserver 단언. 커밋본(고유 포트 UI_PORT=5193): check 7·f6 OK, check:ui 247 통과·50 건너뜀·실패 0. live 모드는 공용 개발 DB(8000)에 대화를 만들어 재실행하지 않음. 같은 커밋본을 기본 포트 5183으로 돌린 첫 실행은 78 실패 — 동시에 돈 다른 에이전트의 dev 서버를 reuseExistingServer로 재사용한 탓 → UI-3 |
| 2026-10-15 | 409 경합 수정 (67c0fec) — frontend-dev가 us8 순서 케이스 작성 중 발견한 결함 | 통과 | 결함: 134d5aa에서 늦게 도착한 이전 재조회(completed)가 409 뒤 재조회(running)를 덮어 폴링이 멈추고 409 안내가 남음. 수정: Chat.tsx load()가 재조회마다 순번을 매기고 이미 반영한 순번보다 오래된 응답을 버림(Chat.tsx:114~119). 확인: 커밋본(UI_PORT=5194) check 7·f6 OK, check:ui 247 통과·50 건너뜀·실패 0. 공유 트리의 미커밋 us8 409 순서 케이스를 커밋본 사본에 넣어 9/9 통과, 수정 전 134d5aa Chat.tsx로 바꾸면 9/9 실패(반대 확인). 해당 케이스는 아직 원격에 없음(frontend-dev 커밋 대기) |
| 2026-10-15 | us8 409 순서 케이스 커밋 (e69b9dd) | 통과 | 커밋본(UI_PORT=5195) check 7 OK, check:ui 256 통과·50 건너뜀·실패 0. 경합 회귀 검사가 원격에 남음 |
| 2026-10-15 | UI-3 재검증 (2e6012b) | 확인됨 | playwright.config.ts: listen(0)로 빈 포트를 골라 UI_PORT에 넣고 reuseExistingServer false. 커밋본 두 사본에서 UI_PORT 없이 check:ui를 동시에 돌려 각각 다른 포트(55737·55738)로 떴고 둘 다 256 통과·50 건너뜀·실패 0. UI_PORT=5199를 미리 점유하면 재사용하지 않고 'already used'로 종료 1 |
| 2026-10-15 | 도구 일부 실패 표시 (6db3a1c, 검사 07426fb) | 통과 | 커밋본 check 7·f6 OK, check:ui 265 통과·50 건너뜀·실패 0. QA 직접(상세 응답 가로채기, 도구 2건 중 1건 failed): 요약 "⚠ 조회 2건 중 1건 실패", details.has-failed, 펼치면 li.failed 1·"실패" 라벨, 대비 라이트 5.93·다크 9.48, axe 심각·중대 0. 실패를 글자로도 구분(색만 아님) |
| 2026-10-15 | 004 질문 마법사 데이터 흐름 (3b5f09d, frontend T014~T016) | 정적 통과, 백엔드 대기 | 계약 v1.3 08b 절과 api.ts 대조: 요청 {conversationId(null 허용), question}, 응답 {refinementId, refined, summary}, 선택 기록 {choice: refined/original/cancelled} → {refinementId, choice, chosenAt} 필드 단위 일치, 캐스팅 없는 파서, REFINEMENT_NOT_FOUND 추가. 커밋본 npm run check f1~f5·f7~f9 OK(f9 단언 11), 계약 diff 0. 실제 백엔드 왕복은 다듬기 엔드포인트 완료 후 |
| 2026-10-15 | 004 Q1 질문 다듬기 백엔드 (2d9f7ae) T008 | 통과, 결함 1(낮음) | 커밋본 이미지·별도 DB(fake): refine 응답 키 = 계약 08b, fake refined·summary = 예시 원문, conversationId null·생략 200, 빈·공백만·4001자·누락·깨진 JSON 400, 4000자 200, 없는 대화 404, choice 키 = 계약·chosenAt ISO·덮어쓰기와 갱신·허용값 밖·누락 400·없는 기록 404 REFINEMENT_NOT_FOUND, DB choice = 마지막 값, llm_usage refine 0원, 대화 messages에 안 나타남. check_b1~b7·b9·b10 OK, 계약 diff 0. 결함 QA-11 |
| 2026-10-15 | 004 T013 US2 수락 시나리오(실제 키, Haiku 5.5 기본값) | 실행 완료, 규칙 위반 리포트 | 별도 실제 모드 컨테이너·별도 DB, kbap-fe EVENTS 45개 택사노미. 4건 모두 200, 지연 2.4~3.4초, 건당 $0.0002~0.0003. (1) 일상어 "스캔 이탈 왜 많아?" 이벤트·기간·기본값 표시 통과(error_state_view 범위 추가는 경계선) (2) 택사노미에 없는 "결제 화면" → 없는 이름은 안 지었으나 order_card_open·order_done으로 대상을 바꿈(사용자 말 유지 규칙 부분 위반, 요약에는 대체 사실 표시) (3) 후속 "그걸 주 단위로" 직전 대상 반영 통과, 원문에 없는 목적 문장 추가 (4) 이미 구체적 질문: 의미 유지, 요약에 '거의 그대로' 표시 없음 + 원문에 없는 산출물 조건 추가(위반). 출력 원문은 QA 산출물 t013_out.json으로 보관, 05_refine_comparison에 반영 예정 |
| 2026-10-15 | 004 T025 모델 비교 (실제 키, 프롬프트 01050f7·c51a5ea) | 통과, 결론 Haiku | 샘플 10건 × Haiku·Sonnet 순차 2회 실행. 최종 프롬프트 Sonnet 76·Haiku 72(4점 차, 기준 8 미만), Haiku 의도 0점 0건. Haiku 지연 중앙값 3.22초(SC-001 통과), 평균 $0.0004(SC-004 통과). 새 문제: 규칙 7 이후 처리 메모가 다듬은 질문 본문에 들어감(backend-dev에 전달). 상세 `06_refine_model_comparison.md` |
| 2026-10-15 | QA-11 재검증·T008 (01050f7) | 확인됨 | 커밋본 이미지·별도 DB: qa_refine.py 실패 0, check_b1~b7·b9·b10 OK(b4·b5는 rg가 PATH에 있어야 함), 계약 diff 0 |
| 2026-10-15 | 004 US1·US3 실제 fake 왕복 (0b5c430) T020·T023 | 통과, 결함 2(중간 1, 낮음 1) | 커밋본 이미지·별도 DB(fake) + 커밋본 프론트 dev 서버. check f1~f5·f7~f9 OK, check:ui 364 통과·50 건너뜀·실패 0. 시연 1~8 Playwright: 빈 입력 비활성, 다듬는 동안 입력창 잠금·aria-busy, 카드 원문·개선안·요약, 첫 포커스 개선안으로 보내기, 개선안·원문 전송과 기록, 입력창에 넣기 직후 POST 없음·NULL, 편집 전송 refined, 비우면 cancelled, ESC cancelled·입력창 포커스, 채택 비율 SQL 40.0·shown 5, refine 사용량 5행 0원, 선택 POST 순서 refined,original,refined,cancelled,cancelled. ui-review 라이트·다크 × 1280·375: 1280 좌우·375 위아래, 가로 스크롤 없음, 카드 최소 대비 5.17, 버튼 비활성·호버·포커스 링 2px, 동작 줄이기 0s. 예산: real 컨테이너 settings spentUsd = llm_usage 합계(refine 0.1048). 결함 QA-12, UI-4 |
| 2026-10-15 | 프롬프트 재확인 Haiku (0b5c430, 347a825) | 통과 | 347a825에서 처리 메모 유입·세 문장·한자 0건, 지연 중앙값 4.12초(SC-001 안, 여유 감소). `06_refine_model_comparison.md` 재확인 절 |
| 2026-10-15 | 계약 08b 보강(b91fbd3) 넣기 뒤 새 다듬기 (프론트 0b5c430) | 통과 | 실제 fake 왕복: 입력창에 넣기 직후 이전 행 NULL, 새로 다듬기 시작 시 이전 행 cancelled, 새 행 NULL. 문구 2차(03d77df)의 4,000자 502·택사노미 겹침 우선은 check_b10(347a825 OK)으로 확인 |
| 2026-10-15 | QA-12·UI-4 재검증, T020·T023·T027 회귀 (7d84470, 테스트만 바뀐 34a0195) | 통과 | 커밋본 이미지·별도 DB(fake): 시연 1~8 실패 0, 넣기 뒤 새 다듬기 cancelled, ui-review 라이트·다크 × 1280·375 실패 0, 375×560 입력창 화면 안. check f1~f5·f7~f9 OK, check:ui 379 통과·71 건너뜀·실패 0(34a0195), check_b1~b7·b9·b10 OK(b8은 운영 검사), 계약 diff 0. SC-005 질문→진행 0.75초→카드 2장→채택→새로고침 유지, 409 안내 후 입력 비활성 약 80ms, 다른 클라이언트 실행을 폴링으로 반영. 열린 결함 0 |
| 2026-10-15 | Haiku thinking 끄기 (1ce6b6d) 10건 재실행 | 통과, 유지 권고 | 지연 중앙값 4.12→2.91초, 출력 토큰 128~274(600 이상 0건), 처리 메모 유입 0, 한자 0, 의도 0점 0건. 2번에 프롬프트 규칙 문구 "두 문장 이내로"가 질문 본문에 들어간 1건 |
| 2026-10-15 | 규칙 문구 유입 수정 (87641b4) Haiku 10건 재실행 | 확인됨 | 규칙 문구·처리 메모 유입 0, 세 문장 0, 한자 0. 2번은 "주문 흐름 단계별 이탈 수와 비율"로 규칙 문구 없음. 지연 중앙값 2.10초, 출력 토큰 133~239 |
| 2026-10-15 | REFINE_THINKING 환경변수화 (d349085) | 정적 통과 | 워크플로우 기본 disabled, env 예시 둘 다 disabled, 코드 기본 adaptive(미설정 시 thinking 미전송). 요청 형태는 1ce6b6d와 같아 재실행 생략. 위험: REFINE_MODEL을 Sonnet 등으로 바꾸고 REFINE_THINKING=disabled를 두면 다듬기가 모두 502. deploy/README에 명시됨 |
| 2026-10-15 | thinking disabled 거부 시 재시도 (56c5d82) | 통과 | disabled 요청이 400이면 경고 로그 후 thinking 없이 1회 재시도, 다시 실패하면 502. 워크플로우 기본 adaptive(운영은 Variable disabled). 커밋본 check_b6·b10 OK. 위 d349085의 Sonnet+disabled 502 위험 해소. 참고: 모든 400에 재시도하므로 다른 원인의 400도 1회 더 호출(400은 과금 없음) |
| 2026-10-15 | PR #16 Codex 2건 (943a915) | 통과, 결함 1(낮음) | Anthropic 거절 시 usage 기록(502·행 없음), 공백만 refined·summary 502·행 없음. 커밋본 check_b1~b7·b9·b10 OK. 같은 원칙으로 남은 경로 QA-13 |
| 2026-10-15 | 최종 회귀 (ab2137f = 943a915·1778aca 포함) | 통과 | 커밋본: check 8 OK, check:ui 388 통과·71 건너뜀·실패 0, check_b1~b7·b9·b10 OK(b8 운영), 계약 diff 0. 실제 fake 왕복: 시연 1~8 실패 0, 카드 연 채 Enter original, 넣기 뒤 새 다듬기 cancelled, 카드 연 채 다른 대화로 이동 cancelled·전송 없음. 열린 결함 QA-13(낮음)뿐 |
| 2026-10-15 | QA-13 재검증 (69fe1b1) | 확인됨 | parse → create 전환 후 실제 경로 정상(10/10), 실패 응답 usage 기록은 check_b10 두 런타임 × 세 형식 오류 + 거절. 열린 결함 0 |
| 2026-10-15 | QA-13 되돌림·재적용 (b23076b → 4b1828c) | 확인됨 | 69fe1b1을 b23076b로 되돌렸다가 team-lead 결정으로 4b1828c에서 다시 적용. b23076b는 ab2137f와 backend 동일·check_b10 OK, 4b1828c는 69fe1b1과 코드 동일·check_b10 OK. 69fe1b1 실제 키 검증이 현재 상태에 유효 |
| 2026-10-15 | PR #16 Codex 다듬기 시간 상한 (1feba63) | 통과 | REFINE_TIMEOUT_SECONDS(기본 20초) 초과 시 502 UPSTREAM_ERROR·행 없음, 계약 08b "모델 호출 실패 502"와 일치. 프론트에는 별도 요청 시간 상한이 없어 서버 상한과 충돌 없음. 커밋본 check_b1~b7·b9·b10 OK, 계약 diff 0. 실제 키 엔드포인트 2건 200(2.96·1.66초), 응답 키 refinementId·refined·summary, usage 행 2 |
| 2026-10-15 | PR #16 Codex 재리뷰 2건 (50f7871, 선택 기록을 message_created 뒤로) | 통과 | 커밋본: check 8 OK, check:ui 424 통과·71 건너뜀·실패 0. 실제 fake 왕복: 시연 1~8 실패 0(채택 비율 40.0·shown 5), 선택 POST 순서 동일, 카드 연 채 Enter는 서버 확인(약 200ms) 뒤 카드 닫힘·original, 넣기 뒤 새 다듬기·다른 대화 이동 cancelled, SC-005 흐름 유지. 실제 409: 카드 연 채 Enter가 409면 카드 유지·기록 NULL·안내 표시, 실행 끝난 뒤 원문으로 보내기 original |
| 2026-10-15 | 마지막 회귀 (b83894e = 62d36b2 포함) | 통과 | 커밋본: check 8 OK, check:ui 424 통과·71 건너뜀·실패 0. 실제 fake 왕복: 시연 1~8 실패 0, 넣기 뒤 새 다듬기·이동 cancelled, SC-005 흐름 유지. 전송 실패 실측(별도 DB에 예산 초과 행을 잠시 넣어 403 유도): 409 중 개선안으로 보내기 → 기록 없음·개선안이 입력창에 남음·다시 보내면 refined, 예산 초과 중 원문으로 보내기 → 기록 없음·이후 무관한 전송에도 기록 없음, 넣기 뒤 예산 실패 → 기록 없음·입력창 유지·다시 보내면 refined. 열린 결함 0 |
| 2026-10-15 | 최종 회귀 (3a75c5f = ac9181f 카드 재오픈·b551a53 compare_refine·3a75c5f busy 중 닫기 무시) | 통과, 결함 1(낮음, 다음 사이클) | 커밋본: check 8 OK, check:ui 433 통과·71 건너뜀·실패 0, check_b1~b7·b9·b10 OK, 계약 diff 0, compare_refine 구문 OK. 실제 fake 왕복: 시연 1~8 실패 0, 넣기 뒤 새 다듬기·이동 cancelled, SC-005 유지. 전송 실패: 409 중 개선안으로 보내기 → 같은 카드 재오픈·기록 없음·입력창 원문 → 재시도 refined 1건(선택 POST ["refined"]). 예산 실패 원문으로 보내기 → 카드 재오픈·기록 없음 → 재시도 original. 넣기 뒤 예산 실패 → 입력창 유지 → 재시도 refined. 응답 지연 중 Enter 직후 ESC → 닫기 비활성·카드 유지·기록 없음, 서버 확인 뒤 original 1건. 결함 UI-5 |
| 2026-10-17 | 005 E2 내보내기 기록 백엔드 (3c28f88) T014 | 통과(프론트 본문 대조는 커밋 대기) | 커밋본 이미지·별도 DB(fake): pdf·markdown 201, 응답 키 {exportId, conversationId, format, createdAt} = 계약 v1.4 예시, createdAt ISO 밀리초 Z, 행 생성·형식 일치. 형식 밖·대문자·누락·숫자·null·깨진 JSON·배열 본문 400 VALIDATION_ERROR(공통 에러 형식), 없는 대화 404 CONVERSATION_NOT_FOUND, 경로 abc 400, 오류 요청은 행 없음, FK ON DELETE CASCADE, 대화 상세 shape 불변. ACCESS_TOKEN 설정 시 토큰 없음 401·있음 201, CORS preflight 200. check_b1~b7·b9·b10·b11 OK, 계약 diff 0. 프론트 api.ts recordExport(작업 트리, 미커밋): 본문 {format}, 파서 네 키·enum이 계약과 일치 |
| 2026-10-17 | 005 E1 내보내기 프론트 (1b0dda9) T013·T014·T015 | 통과, 결함 2(낮음), 수동 인쇄 미리보기 미검증 | 커밋본: check f1~f5·f7~f10 OK, check:ui 514 통과·71 건너뜀·실패 0. 실제 fake 백엔드(3c28f88 이미지·별도 DB) 왕복: 메시지 0·실행 중 비활성, PDF로 인쇄 → window.print 1회·기록 본문 {"format":"pdf"}, Markdown → `{제목}-YYYYMMDD.md`·기록 본문 {"format":"markdown"}·주소 없음·메시지 수·chart 블록 보존, DB pdf·markdown. 인쇄 상태(beforeprint + print 미디어): 카드 절 32/32 펼침, 머리글 제목·생성·내보낸 날짜, 사이드바·입력창·다듬기·채택·도구 행·메뉴·상단바 숨김, 다크에서도 흰 배경·어두운 글자. 취소(afterprint) 뒤 카드 접힘·차트 크기 복원. Chrome 인쇄 렌더링(A4 폭) PDF 15쪽: 차트 밝은 색·글자 판독 가능, 카드 쪼개짐 없음, 표·코드 가로 넘침 없음. 화면 ui-review 라이트·다크 × 1280·375: 메뉴 키보드(Enter 열기·첫 항목 포커스·화살표·ESC 복귀), axe 0, 대비 4.5 이상, 화면 안. 회귀: check_b1~b7·b9~b11 OK, 계약 diff 0, 질문→제안→채택→새로고침 유지. 결함 QA-14, UI-6. 인쇄 대화상자 자체는 자동화가 막혀(모달이 페이지 스크립트를 멈춤, 헤드리스는 afterprint 미발생) 수동 확인 필요 |
| 2026-10-17 | 005 E1 후속: 인쇄에서 사용량 줄 숨김 (db71656) | 통과 | 커밋본 check 9 OK, check:ui 514 통과·71 건너뜀·실패 0. 실제 fake 왕복 인쇄 상태에서 보이는 사용량 줄 0개(전에는 4개). 나머지 인쇄·Markdown·기록 항목 그대로 통과, 차트 색 복원은 QA-14로 여전히 열림 |
| 2026-10-17 | QA-14·UI-6 재검증 (2003354) | 확인됨 | 커밋본 check 9 OK, check:ui 523 통과·71 건너뜀·실패 0. 다크 차트 복원: afterprint가 print 미디어 중에 오는 순서와 미디어가 먼저 풀리는 순서 모두 4초 뒤 색 분포가 인쇄 전과 같음. 같은 대화 A4 PDF: 15쪽 → 10쪽, 마지막 쪽 빼고 내용이 60% 위에서 끝나는 쪽 5 → 0, 질문이 답과 같은 쪽에서 시작. 한 쪽보다 큰 측정 설계 카드는 쪽 경계에서 나뉨(불가피), 퍼널 표 한 행이 쪽 경계에서 갈림(관찰, 결함 아님). 실제 fake 왕복 인쇄·Markdown·기록 항목 실패 0. 열린 결함 0 |
| 2026-10-17 | QA-14·UI-6 최종 (f9cb344, CTO 결정 반영: 인쇄 중 responsive:false·작은 단위만 avoid·tr avoid·복원은 afterprint와 미디어 해제 둘 다 뒤 다음 프레임) | 확인됨 | 커밋본 check 9 OK, check:ui 523 통과·71 건너뜀·실패 0. 차트 색 복원: afterprint가 print 미디어 중에 오는 순서, 미디어가 먼저 풀리는 순서, 미디어 변화 없이 이벤트만 오는 경우 모두 인쇄 전과 같음. 뷰포트 1280에서 print 미디어 에뮬레이션 시 캔버스 680x280(2003354는 1280x280로 재확대). A4 PDF 10쪽, 빈칸 쪽 0, 퍼널 표 행 갈림 쪽 3·5·7·9 → 없음. 실제 fake 왕복 인쇄·Markdown·기록 실패 0. 관찰(결함 아님): afterprint 없이 print 미디어만 오가면(DevTools 미디어 에뮬레이션) 차트가 인쇄 색으로 남음. 실제 인쇄는 afterprint를 보냄 |
| 2026-10-17 | 인쇄 다듬기 (74dbb33: 절 요약·답 제목 break-after avoid, p orphans·widows 3, 인쇄 질문 1px 테두리) | 통과 | 커밋본 check 9 OK, check:ui 523 통과·71 건너뜀·실패 0. 같은 대화 A4 PDF 10쪽(변화 없음), 빈칸 쪽 0, 표 행 갈림 없음, 질문 테두리 보임. 차트 색 복원 세 경우 모두 인쇄 전과 같음, 뷰포트 1280 인쇄 캔버스 680x280. fake 왕복 인쇄·Markdown·기록 실패 0. 열린 결함 0 |
| 2026-10-17 | PR #18 Codex 4건 (fc246e0) | 통과 | 커밋본 check 9 OK, check:ui 541 통과·71 건너뜀·실패 0. 실제 fake 왕복(print()가 beforeprint·afterprint를 보내는 실제 Chrome 흉내): 메뉴 PDF 기록 정확히 1건, beforeprint 직접(Ctrl+P) 1건 추가, Markdown 1건(대화당 pdf,pdf,markdown, 요청 3회·중복 없음). 화면에서 만든 새 대화 첫 답변 직후 내보내기: 인쇄 머리글·Markdown 제목이 실제 제목. 줄바꿈 제목은 Markdown 머리글 "# 스캔 퍼널 이탈 둘째 줄 질문" 한 줄, 인쇄 머리글 h1도 한 줄(white-space normal). 같은 검사가 74dbb33에서는 Ctrl+P 기록 없음·Markdown 제목 두 줄로 실패 |
| 2026-10-17 | 006 A2 프론트 (bb6a94c) | 통과(정적·검사), 백엔드 왕복은 A1 커밋 대기 | 커밋본 check 9 OK, check:ui 568 통과·71 건너뜀·실패 0. 계약 v1.5와 정적 대조: Settings.amplitude 파서가 {status: configured|missing}만 받음, sendMessage는 skipAmplitude가 참일 때만 필드를 보냄, AMPLITUDE_UNAVAILABLE 에러 코드·안내 추가, connectAmplitude 제거, 설정 라벨 '서버 키로 연결됨'·'키 없음'과 서버 변수 안내(키 값 표시 없음), 503이면 서버 메시지 그대로·입력 유지·'Amplitude 없이 진행' 재전송 |
| 2026-10-17 | 006 A1 백엔드 (cc9221e) T014 | 통과, 경계면 20항목 실패 0 | 커밋본 이미지·별도 DB, 가짜 Amplitude(AMPLITUDE_REST_BASE). 키 없음 settings {status: missing}·키 있음 configured(응답에 키 없음). 메시지 503 AMPLITUDE_UNAVAILABLE 네 이유(키 없음, 401·403 인증, 429 한도, 연결 실패) 문구가 계약과 글자 단위로 같고 거절 시 메시지 0·llm_usage 0. skipAmplitude 문자열·숫자·null 400. 삭제된 connect·callback 404 NOT_FOUND. 사전 점검은 /api/2/taxonomy/event 한 경로·Basic 인증. 로그에 키 없음. 기동 멱등: 열 삭제·OAuth 행 2개 넣고 두 번 기동 → 열 enum('used','unavailable','skipped') 복구·행 0·오류 없음. fake 모드 Amplitude 호출 0·상태 NULL, API에 amplitude_status 없음. check_b1~b6·b9~b12 OK(b7 삭제 확인), 계약 diff 0. MCP 흔적: 코드·설정·계약 분할본 0(문서 이력만), backend/app은 OAuth 행 삭제 문자열 1건. mcp 패키지는 openai-agents의 간접 의존으로 남음 |
| 2026-10-17 | 006 T015 실제 키 (cc9221e, 도구 직접 호출) | 일부 실패, 결함 2 | 로컬 .env 프로젝트 키, Amplitude 호출 8회 모두 200(틀린 키 1회는 401 → "인증에 실패했습니다" 거절). 이벤트 목록 50개, category·description 필드 이름 일치(값이 있는 이벤트에서 표시), 이벤트 속성 type·사용자 속성 목록 정상. 세그멘테이션(uniques 7일)·퍼널(scan_start→scan_complete, 7일 창, 표본 30 미만 경고)·리텐션 모두 성공하고 압축표 형식. 결함: 리텐션 D열이 하루씩 밀림(QA-15), 세그멘테이션 시리즈 이름이 "0"(QA-16). 에이전트 질문 경로(amplitude_status='used')는 LLM 비용 때문에 돌리지 않음 |
| 2026-10-17 | 006 A2 실제 왕복·ui-review·회귀 (HEAD 9a1e1c4 = bb6a94c·cc9221e) T016 | 통과 | 커밋본 프론트 + cc9221e 이미지(real·키 없음 / 가짜 키 / fake). 라이트·다크 × 1280·375: 설정 '키 없음'+변수 이름 안내 / '서버 키로 연결됨', 연결 버튼 없음, axe 0. 키 없이 질문 → 503 서버 문구 그대로·입력 유지·메시지 저장 0, 'Amplitude 없이 진행'을 키보드로 → 본문 [{content}, {content, skipAmplitude:true}], 다음 전송 뒤 버튼 사라짐, 답 행 amplitude_status='skipped'(LLM 키 없어 failed). 회귀: check 9 OK, check:ui 568 통과·71 건너뜀·실패 0, check_b1~b6·b9~b12 OK, 질문→제안→채택→새로고침·409 유지. data-model 상태 조회 SQL: completed+상태 행 0(실제 실행은 LLM 없이 failed, fake는 NULL)으로 규칙과 일치. 커밋 44개 diff·메시지에 키 값·운영 호스트 0 |
| 2026-10-17 | QA-15·QA-16 재검증 (43cdf08) | 확인됨 | 커밋본 check_b1~b6·b9~b12 OK, 계약 diff 0. 실제 키(Amplitude 3회): 같은 리텐션 조회가 모든 코호트 D0 100%, 합산 "D0 100.0% (52/52), D1 11.8% (4/34), D2 14.3% (4/28)"로 앞서 분석한 실제 값과 일치, 미완 칸은 빈칸. 단일 이벤트 세그멘테이션 머리 `| date | app_opened |`, group_by(platform)는 `| date | Android | iOS |`(형식 파일 규칙과 같음) |
| 2026-10-17 | T015 실제 질문 1회 (43cdf08, team-lead 승인, QA 로컬 DB) | 통과, 결함 1(낮음) | 질문 "최근 7일 스캔 성공률 알려줘", Sonnet 5.5, 35초. 도구 7회(amplitude_context 3, amplitude_query 4) 모두 succeeded, 인자 오류·재시도 0. 세그멘테이션 인자에 events·filters(success is/is not true)·metric totals·기간을 올바르게 씀. 답 본문에 실제 수치(성공률 57.1% = 8/14, 시작 대비 44.4% = 8/18, 일별 표·chart 블록), 표 합계·비율이 서로 맞음. 제안 카드는 없음(조회 질문). messages.amplitude_status='used'. llm_usage: agent 5행, 입력 42,782·출력 2,402 토큰, $0.1096. 로그에 키 없음. 결함 QA-17 |

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

### UI-1: Drawer가 포커스를 가두지 않고, 닫은 뒤 메뉴 버튼으로 포커스를 돌려주지 않는다
- 화면·폭·모드: 모든 화면 / 768px·375px / light·dark
- 항목: 접근성 — Drawer에 역할·포커스 가두기 (tasks T012 "포커스 가두기와 닫을 때 메뉴 버튼으로 포커스 복귀", FR-004)
- 현상: 01306ec 커밋본, Playwright. 메뉴 열기 → Drawer(role=dialog, body 잠금은 정상) 열린 상태에서 Tab 16번 중 3번이 Drawer 밖 요소로 나감(768·375 동일). ESC로 닫은 뒤 `document.activeElement`가 body(aria-label null)로, 메뉴 버튼으로 돌아오지 않음. 재현: QA 스크립트 e2e_shell.mjs 또는 수동으로 375px에서 ☰ → Tab 반복 → ESC
- 기준: tasks T012, FR-004 "열린 동안 본문 스크롤 잠금, 포커스 가두기", ui-review 접근성 "Drawer에 역할·포커스 가두기"
- 수정 방향: `frontend/src/Shell.tsx` Drawer 열릴 때 첫 포커스 요소로 이동, Tab/Shift+Tab을 Drawer 안에서 순환(또는 Drawer 밖 영역에 `inert`), 닫힐 때 메뉴 버튼 ref로 focus()
- 심각도: 차단(접근성 실패)
- 수신: frontend-designer
- 상태: 확인됨 (4485719: 열 때 첫 링크로 포커스, Tab·Shift+Tab 순환, ESC 뒤 메뉴 버튼 복귀. QA 스크립트와 us2.spec 모두 통과)

### UI-2: 토큰 없음·불일치 401(UNAUTHORIZED)을 "로그인이 만료되었습니다 / 다시 로그인" 세션 만료 배너로 안내한다
- 화면·폭·모드: 채팅 / 전 폭 / light·dark
- 항목: 상태 — 세션 만료 상태 구분, 오류 안내의 정확성(계약 경계)
- 현상: 4a442e5 커밋본. 메시지 전송에 401 `{"error":{"code":"UNAUTHORIZED","message":"접근 토큰이 없거나 일치하지 않습니다."}}`가 오면 상단에 "로그인이 만료되었습니다. 입력한 내용은 그대로 남아 있습니다. [다시 로그인]" 배너가 뜨고, 아래에 "접근 토큰이 없거나 틀렸습니다. 설정 화면에서 입력하세요. (UNAUTHORIZED)"가 함께 뜬다. [다시 로그인]은 새로고침이라 토큰 문제를 고치지 못한다. 원인 `frontend/src/Chat.tsx:175` `if (e instanceof ApiError && e.code === 'UNAUTHORIZED') setSessionExpired(true)`
- 기준: 계약 v1.1 공통 "인증: … 없거나 틀리면 401 `UNAUTHORIZED`"(토큰 문제, 로그인 세션 없음). 접근 제한 계약 v1.2 "백엔드의 401 `UNAUTHORIZED`(`ACCESS_TOKEN`)는 JSON 에러 형식이라 구분된다 … 백엔드 에러 코드와 섞지 않는다". 반면 `specs/003-frontend-redesign/data-model.md` 3절 표가 세션 만료를 "`SESSION_EXPIRED`(접근 제한 머지 후) 또는 `UNAUTHORIZED`"로 정의해 두 의미를 섞었다 → 스펙 결함, 구현은 스펙을 따름
- 수정 방향: CTO가 data-model 3절에서 `UNAUTHORIZED`를 세션 만료에서 빼고(토큰 안내 = 기존 notice), 세션 만료는 `SESSION_EXPIRED`만으로 정의. 그다음 designer가 Chat.tsx:175 조건을 `SESSION_EXPIRED`로(이 브랜치엔 아직 없으니 배너는 접근 제한 머지 때 연결)
- 심각도: 높음(잘못된 해결 방법 안내, 계약 경계 혼동)
- 수신: cto(스펙), frontend-designer(구현)
- 상태: 확인됨 (8087635·b9a873b 스펙: 세션 만료는 SESSION_EXPIRED만. 9000fa7·bc01b76·26b6f35·4b16661: 401은 #chat-hint 토큰 안내+설정 링크, 배너 없음, 입력 유지)

### UI-3: check:ui가 고정 포트 dev 서버를 재사용해, 동시 실행 시 다른 트리의 코드로 검사한다
- 화면·폭·모드: 전체 / 전 프로젝트 / 검사 인프라
- 항목: 자동 UI 검사 신뢰성 (FR-013 "명령 하나로 다시 실행되는 자동 검사")
- 현상: `frontend/playwright.config.ts` webServer가 `UI_PORT`(기본 5183) + `reuseExistingServer: true`. f1afd83 커밋본 깨끗한 사본을 기본 포트로 돌렸을 때 그 순간 다른 에이전트의 check:ui가 5183에 dev 서버를 띄워 둔 상태여서 그 서버를 재사용 → 78 실패. 같은 사본을 UI_PORT=5193으로 다시 돌리면 247 통과·실패 0. 재사용된 서버가 미커밋 수정이 든 트리라면 반대로 결함이 가려진 가짜 통과도 난다
- 기준: 검사는 실행한 트리의 코드를 검사해야 한다(QA는 커밋본으로 판정)
- 수정 방향: `reuseExistingServer: false`(또는 `!process.env.CI`가 아니라 항상 false)로 바꾸거나, 실행마다 빈 포트를 잡는다. 최소한 README에 "동시 실행 시 UI_PORT를 다르게" 경고
- 심각도: 높음(검사 결과 오판)
- 수신: frontend-dev
- 상태: 확인됨 (2e6012b: 실행마다 빈 포트, 재사용 끔. 동시 실행 두 사본 모두 256 통과, 점유 포트 지정 시 즉시 실패)

### QA-11: refine 요청의 conversationId에 문자열 "7"을 넣어도 정수로 받아들인다
- 모듈: backend / 004 Q1 (POST /api/questions/refine)
- 경계면: 요청 검증
- 기대: 계약 공통 "ID: 양의 정수(JSON number)", `VALIDATION_ERROR` = "필수 필드 누락·타입 오류·허용값 밖"
- 실제: `{"conversationId": "7", "question": "x"}` → 400이 아니라 404 `CONVERSATION_NOT_FOUND`(그 DB에 대화 7이 없어서). Pydantic 기본(lax) 모드가 "7"을 7로 강제 변환. 대화 7이 있으면 200으로 통과한다
- 수정 방향: 백엔드. 요청 모델 `conversationId: int | None`을 strict(`StrictInt` 또는 `model_config strict`)로. check_b10 타입 400 케이스에 문자열 ID 추가
- 수신: backend-dev
- 상태: 확인됨 (4918a52: RefineIn.conversation_id를 StrictInt로, check_b10에 문자열·불리언 케이스 추가. 01050f7 커밋본 재검증: "7"·7.0·true 모두 400 VALIDATION_ERROR, null 200)

### QA-12: 카드가 열린 채 원문을 보낸 뒤 실행 중에 "개선안으로 보내기"를 누르면 전송 없이 refined로 기록된다
- 모듈: frontend / 004 Q2·Q3 (Chat.tsx submit, refine.ts finish, RefineCard)
- 경계면: 선택 기록 ↔ 실제 전송
- 기대: data-model "개선안을 보낸 경우 refined", FR-007 채택 = 실제 전송. 기록은 화면에서 일어난 일과 같아야 한다
- 실제: 재현 순서는 다음과 같다. (1) 입력 → 질문 다듬기 → 카드가 열린다. (2) 입력창에서 Enter → 원문이 전송되고 에이전트가 실행된다. 카드는 남고 기록은 NULL이다. (3) 실행 중 카드의 "개선안으로 보내기" → `finish('refined')`가 기록 POST를 보낸다. 그러나 `submit`은 `streaming`이라 바로 return한다. 사용자 메시지는 4개에서 4개로 그대로, 카드는 닫히고, 기록 = refined다. 개선안 문장은 어디에도 남지 않는다. "원문으로 보내기"도 같은 경로로 original이 잘못 남는다. 채택 비율(SC-002)이 부풀고 사용자는 눌렀는데 아무 일도 없다
- 수정 방향: 프론트. 카드가 열린 상태에서 메시지가 전송되면 카드를 닫고 `original`로 기록한다(사용자가 원문을 보낸 것). `submit`의 `refine.sent()` 옆에서 처리하면 된다. 실행 중에는 카드의 두 전송 버튼도 비활성으로 둔다. us12에 "카드 연 채 Enter" 케이스를 추가한다
- 수신: frontend-dev, frontend-designer
- 상태: 확인됨 (f56d363: 열린 카드를 ref로 추적, 카드 연 채 전송하면 original로 기록하고 닫음, 카드 동작은 열린 카드가 있을 때만. 34001a6의 실행 중 비활성과 함께 7d84470 커밋본 재검증: 카드 연 채 Enter → 카드 닫힘·original 기록·원문 전송(DB 메시지 확인), 시연 1~8 실패 0)

### UI-4: 375px에서 카드가 열리면 메시지 영역이 키보드로 스크롤되지 않는다 (axe scrollable-region-focusable, serious)
- 모듈: frontend / 004 Q3 (Chat.tsx `.scroll`, RefineCard)
- 경계면: 화면 접근성
- 기대: check:ui 공통 기준 axe critical·serious 0
- 실제: 375×800 빈 대화에서 카드(높이 472px)를 열면 `.scroll`이 152px로 줄어 내용이 넘친다. 안에 포커스 가능한 요소가 없어 axe serious `scrollable-region-focusable`이 난다(라이트·다크 둘 다, 카드 닫힌 상태는 0). 375×667에서는 메시지 영역이 19px, 375×560에서는 0px이 되고 문서 전체가 스크롤되며 입력창 아래쪽이 화면 밖으로 나간다. us12는 대화에 제안 카드(포커스 가능)가 있는 고정 응답이라 잡지 못한다
- 수정 방향: 디자이너. `.scroll`에 `tabIndex={0}`과 접근 이름("대화 내용")을 준다. 또는 좁은 화면에서 카드 높이에 상한을 두고 카드 안을 스크롤한다. us12에 빈 대화 375 axe 케이스를 추가한다
- 수신: frontend-designer
- 상태: 확인됨 (34001a6: `.scroll`에 tabIndex·region·"대화 내용", 카드 높이를 화면 절반으로 제한하고 카드 안 스크롤. 커밋본 재검증: 라이트·다크 × 1280·375 axe critical·serious 0, 375×667 메시지 영역 127px, 375×560 입력창 화면 안·문서 스크롤 없음)

### QA-13: 형식이 틀린 다듬기 응답과 OpenAI 거절은 과금되지만 사용량에 기록되지 않는다
- 모듈: backend / 004 (agent.refine, agent_anthropic.refine, agent_openai.refine)
- 경계면: LLM 응답 ↔ 예산 기록
- 기대: 943a915가 세운 원칙 "거절도 과금되므로 예산에 기록", FR-008 사용량·예산
- 실제: Anthropic `messages.parse`가 구조화 출력 검증(잘못된 JSON, 4,001자 이상 refined, 공백만 refined·summary)에서 예외를 내면 응답 usage를 읽기 전에 빠져나가 llm_usage 행이 없다. 모델은 출력 토큰을 이미 썼다. OpenAI 런타임 `Runner.run`의 거절·검증 실패도 기록 경로가 없다(현재 OpenAI 키 없음). 모두 502·다듬기 행 없음은 맞다
- 수정 방향: 백엔드. 원응답을 받은 뒤 검증하는 경로(예: `messages.create` 후 `RefineResult.model_validate_json`)로 바꾸거나, 검증 예외에 usage를 실어 Refused와 같은 방식으로 기록한다. 빈도·금액이 작아(Haiku 1회 약 $0.0004) 다음 사이클로 미뤄도 된다
- 수신: backend-dev
- 상태: 확인됨 (69fe1b1: Anthropic은 messages.create + RefineResult 직접 검증, OpenAI는 RunHooks.on_llm_end로 usage 누적, 거절·형식 오류는 usage를 실은 예외로 기록 후 502. 커밋본 check_b1~b7·b9·b10 OK, 계약 diff 0. 실제 키 Haiku 10건: 오류 0, usage 행 +10, 지연 중앙값 1.94초, 규칙 문구·처리 메모 유입 0)

### UI-5: 409로 카드가 다시 열리면 키보드 포커스가 페이지 본문으로 떨어진다
- 모듈: frontend / 004 (refine.ts 카드 재오픈, RefineCard 첫 포커스)
- 경계면: 화면 접근성 (전송 실패 후 상태)
- 기대: ac9181f 설명대로 재오픈 시 포커스가 "개선안으로 보내기"에 간다. 예산 403에서는 그렇게 된다
- 실제: 다른 클라이언트 실행 중 카드에서 "개선안으로 보내기"나 "원문으로 보내기" → 409 → 카드는 다시 열리지만 document.activeElement가 body다(두 버튼 모두 재현, 403은 정상). 409 뒤 상세 재조회로 실행 중 상태가 되어 카드 버튼·입력창이 모두 비활성이라 포커스를 둘 곳이 없는 것으로 보인다. 스크린 리더 사용자는 카드가 다시 열린 것과 위치를 알기 어렵다
- 수정 방향: 프론트. 실행 중에도 포커스 가능한 요소(카드 닫기는 busy라 비활성이므로 카드 제목에 tabIndex=-1을 주고 포커스, 또는 #chat-hint 안내로 포커스)를 정하고, 실행이 끝나 버튼이 살아나면 개선안으로 보내기로 옮긴다. us12에 409 재오픈 포커스 케이스를 추가한다
- 수신: frontend-dev, frontend-designer
- 상태: 열림 (낮음, 다음 사이클. 프론트 동결)

### QA-14: 인쇄 후 차트 색 복원이 afterprint와 print 미디어 해제 순서에 달려 있다
- 모듈: frontend / 005 E1 (ChartBlock.tsx onAfterPrint)
- 경계면: 화면 상태 복원 (FR-005 "끝나면 화면 상태로 돌아온다")
- 기대: 인쇄 대화상자를 닫으면 차트가 화면 테마 색으로 돌아온다
- 실제: onAfterPrint가 `paint(chart, false)`로 화면 토큰(--color-text·--chart-*)을 읽는데, 그 순간 print 미디어가 아직 적용돼 있으면 @media print가 덮어쓴 밝은 인쇄 값이 읽힌다. 이어서 미디어가 screen으로 바뀌어도 `printing`이 이미 false라 onPrintMedia가 아무것도 하지 않는다. 재현(다크): beforeprint → print 미디어 → afterprint → screen 미디어 순서면 차트 제목·범례·눈금이 어두운 글자로 남아 다크 배경에서 안 보인다(4초 뒤에도 유지). 미디어를 먼저 screen으로 돌린 뒤 afterprint면 정상. 실제 Chrome 인쇄 미리보기 순서는 자동화로 확인하지 못했다(대화상자가 스크립트를 멈추고, 헤드리스는 afterprint를 보내지 않음)
- 수정 방향: 프론트. 복원 그리기를 순서와 무관하게 만든다. 예: onAfterPrint에서 `requestAnimationFrame`(또는 print 미디어가 false가 될 때)까지 미뤄 화면 값을 읽거나, onPrintMedia(false)는 printing 여부와 상관없이 화면 색으로 다시 칠한다. us13에 "afterprint가 print 미디어 중에 와도 복원" 케이스를 추가한다
- 수신: frontend-dev
- 상태: 확인됨 (f9cb344 최종: afterprint와 print 미디어 해제가 모두 온 뒤 다음 프레임에 화면 토큰으로 한 번 복원, 미디어가 안 바뀌면 afterprint만으로 복원. 세 경우 모두 복원 확인)

### UI-6: 인쇄에서 긴 에이전트 메시지가 통째로 다음 쪽으로 밀려 쪽마다 큰 빈칸이 생긴다
- 모듈: frontend / 005 E1 (style.css @media print `.msg { break-inside: avoid }`)
- 경계면: 인쇄 결과 (FR-007, SC-001)
- 기대: 메시지·카드는 가능한 한 잘리지 않되 쪽을 낭비하지 않는다
- 실제: 한 쪽보다 긴 에이전트 메시지(카드 2장 포함 약 1,500px)에 break-inside: avoid가 걸려 Chrome이 메시지를 다음 쪽 처음으로 민다. A4 PDF에서 1쪽은 머리글과 첫 질문만 있고 나머지가 비었고, 질문 다음 쪽마다 같은 현상이라 메시지 10개가 15쪽이 됐다. 긴 메시지는 어차피 쪽 경계에서 나뉘므로 avoid가 이득 없이 빈칸만 만든다
- 수정 방향: 프론트·디자이너. avoid를 `.card`·`.msg.user`와 작은 블록(표 행, 근거 항목)에만 두고 `.msg.assistant`에서는 뺀다. 사용자 질문이 쪽 끝에 홀로 남지 않게 하려면 `.msg.user { break-after: avoid }`를 고려한다
- 수신: frontend-dev, frontend-designer
- 상태: 확인됨 (f9cb344 최종: .card-head·.card-section·.md-chart·pre·tr만 avoid, .msg.user·.card-head·.card h4는 break-after: avoid. A4 15쪽 → 10쪽, 빈칸 쪽 5 → 0, 표 행 갈림 4쪽 → 0)

### QA-15: 리텐션 표의 D열이 하루씩 밀려 D1이 늘 100%로 보고된다
- 모듈: backend / 006 A1 (amplitude.retention_table)
- 경계면: Amplitude REST 응답 ↔ 모델에게 주는 결과 표(contracts/amplitude-tools.md 리텐션)
- 기대: `| cohort (n) | D0 … D14 |`와 `합산(combined):`의 Dn이 실제 n일째 복귀율이다
- 실제: 실제 `/api/2/retention` 응답의 코호트 배열은 첫 칸이 코호트 크기, 둘째 칸부터 Day 0이다. 마지막 날 코호트(Oct 16)가 [61/61, 61/61(미완), 0/61(미완)], Oct 14 코호트가 [10/10, 10/10, 3/10, 2/10(미완), 0/10(미완)]이라 둘째 칸이 Day 0, 셋째 칸이 Day 1이어야 날짜가 맞는다. 구현은 첫 칸을 D0으로 세서, 모든 코호트의 D1이 100%이고 미래 날짜 칸에 수가 있다. 합산 줄도 "D1 100.0% (52/52), D2 11.8% (4/34)"로 나오는데 실제는 D0 100%, D1 11.8%다. 모델이 이 표로 리텐션을 답하면 잘못된 수치가 근거로 들어간다. check_b12의 가짜 응답이 첫 칸을 D0으로 만들어 잡지 못했다
- 수정 방향: 백엔드. values·combined 배열의 첫 칸을 코호트 크기로 보고 둘째 칸부터 D0으로 쓴다(코호트 n은 첫 칸 outof). check_b12의 RET 가짜 응답을 실제 모양(첫 칸 = 크기)으로 바꾼다. 실제 키 재확인은 내가 1회 한다
- 수신: backend-dev (cto 참조)
- 상태: 확인됨 (43cdf08: 첫 칸은 코호트 크기 n, 둘째 칸부터 D0. 실제 키로 D0 100%·D1 11.8% 확인, check_b12 가짜 응답을 실제 모양으로)

### QA-16: 이벤트 하나짜리 세그멘테이션 표의 시리즈 이름이 "0"이다
- 모듈: backend / 006 A1 (amplitude._labels, series_table)
- 경계면: Amplitude REST 응답 ↔ 결과 표
- 기대: `| date | 시리즈... |`의 시리즈 이름으로 모델이 어떤 이벤트(또는 group_by 값)인지 알 수 있다
- 실제: group_by 없이 이벤트 하나(app_opened)를 조회하면 실제 응답 seriesLabels가 [0]이라 표 머리가 `| date | 0 |`, 요약이 `0: 합 103 …`이다. 이벤트 두 개면 0·1로 나올 것이라 어느 쪽이 어느 이벤트인지 모델이 추측해야 한다
- 수정 방향: 백엔드. group_by가 없으면 시리즈 이름을 events 순서의 event_type으로 쓴다(seriesLabels가 정수일 때). check_b12 SEG 가짜 응답에 정수 라벨 경우를 추가한다
- 수신: backend-dev
- 상태: 확인됨 (43cdf08: 정수 라벨은 이벤트 이름, group_by는 그룹 값. 실제 키로 확인)

### QA-17: Amplitude 도구 호출의 resultSummary가 표 제목 줄뿐이라 화면 도구 목록에 수치가 없다
- 모듈: backend / 006 A1 (Amplitude 도구 결과 → tool_calls.result_summary)
- 경계면: GET /api/conversations/{id}의 `toolCalls[].resultSummary` ↔ 화면 도구 호출 목록
- 기대: 계약 예시처럼 요약에 핵심 수치가 들어간다(예: "scan_start 2,418명 → scan_complete(success=true) 999명, 전환율 41.3%", 최대 500자)
- 실제: 실제 질문 1회의 amplitude_query 4건이 모두 `**segmentation scan_complete 2026-10-10~2026-10-16 (7 rows × 1 series)**` 같은 제목 한 줄이다. 표와 `요약:` 줄은 저장되지 않아 화면에서 도구를 펼쳐도 수치를 볼 수 없고, 답의 수치를 도구 결과와 대조할 수도 없다. amplitude_context도 "이벤트 50개 (…)"·"**scan_complete** 이벤트 속성" 한 줄이다
- 수정 방향: 백엔드. 요약을 제목 줄 대신 결과 문자열 앞 500자(또는 `요약:` 줄 우선)로 만든다. 다음 사이클로 미뤄도 답 자체에는 영향이 없다
- 수신: backend-dev
- 상태: 열림 (낮음)
