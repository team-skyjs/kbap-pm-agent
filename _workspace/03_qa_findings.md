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
- 상태: 열림

### QA-3: 운영 CORS 출처(simhani1.github.io)가 레포 소유자(team-skyjs)와 다르다
- 모듈: 계약/ADR (B8·F6 배포 전)
- 경계면: 운영 GitHub Pages → 백엔드 CORS preflight
- 기대: ADR 환경변수 표 `CORS_ORIGINS` = `https://simhani1.github.io,http://localhost:5173`, T056 `Origin: https://simhani1.github.io` preflight
- 실제: `git remote` origin = `https://github.com/team-skyjs/kbap-pm-agent.git`, `.github/workflows/pages.yml`은 이 레포에서 배포 → Pages 출처는 `https://team-skyjs.github.io`. 그대로면 운영에서 모든 요청이 CORS로 막혀 프론트가 "연결 실패"
- 수정 방향: CTO가 운영 출처를 확정해 ADR·T056·운영 `.env`의 CORS_ORIGINS를 맞춘다(배포 레포가 simhani1 포크면 그대로 두고 그 사실을 ADR에 명시)
- 수신: cto
- 상태: 열림
