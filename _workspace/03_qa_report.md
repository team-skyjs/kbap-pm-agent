# QA 리포트 — 2026-10-15

기준: `_workspace/01_cto_api-contract.md` v1.1 (`specs/001-pm-agent-prototype/contracts/`와 diff 없음). 결함 상세: `_workspace/03_qa_findings.md`.

## 요약: 통과 14 / 실패 0 / 미검증 6

- 결함 4건(QA-1~QA-4) 모두 수정·재검증 완료. 열린 결함 0.
- fake 모드(`AGENT_MODE=fake`)에서 quickstart 시나리오 1~10이 실서버 + 브라우저(headless Chrome)로 처음부터 끝까지 동작한다.
- 미검증 6건은 모두 사람이 해야 하는 일(LLM 키·비용 승인, Amplitude 브라우저 승인, 운영 배포)에 막혀 있다. 통과로 적지 않았다.
- tasks.md: 61개 중 54개 체크. 미체크 7개는 T042·T046·T050·T054·T057·T060·T061(아래 미검증 항목).

## 모듈별 결과

| 모듈 | 경계면 | 결과 | 결함 ID | 비고 |
|---|---|---|---|---|
| B1·F1 | GET /api/health, CORS, 401·404 공통 에러, Pages 하위 경로 | 통과 | - | 토큰 켠 서버에서 401에도 CORS 헤더, DB 중단 시 200 degraded, 빌드본 preview `/kbap-pm-agent/` |
| B2 | 대화 목록·생성·상세, PATCH 제안 | 통과 | - | 계약 원문 JSON과 키 단위 일치 33항목, null 규칙, 201, `.mmmZ` 시각, DB enum |
| B3 | POST messages SSE (fake) | 통과 | - | 이벤트 줄 형식·순서·키, final = GET 상세, 400/404/409, 끊김 → failed, 15초 ping |
| F3 | 채팅 생성·상세·스트리밍 | 통과 | QA-1(확인됨) | 첫 진행 표시 0.74s(SC-004 5초 이내), 409 안내 + 재조회 + 3초 폴링 |
| F4 | 제안 카드·채택/보류 | 통과 | - | 4영역 순서, evidence 3종, 퍼널 기존/신규·위치, PATCH 본문, 새로고침 유지, pending 복귀 decidedAt null |
| F2 | 대화 목록·다시 열기 | 통과 | - | 제목 앞 40자 자동, "새 대화", 제안·채택 수, 최근순 |
| B4 | settings, 저장소 등록·sync, 택사노미 | 통과 | QA-2(확인됨) | real 공개 클론 kbap-fe trackedEventCount 117 = 소스 `rg -o`, 토큰 비노출, sync 실패 lastError + 기존 클론 유지, date 오류 메시지 계약 원문 일치 |
| B5 | 코드 도구·요약 캐시·예산 | 통과 (실제 요약 LLM 미검증) | - | 403 BUDGET_EXCEEDED 시 메시지 미저장·조회 200, read_code 200줄, search_code 30건 |
| B6 | 실제 에이전트 루프 | BE 통과, 실모드 미검증 | - | 가짜 채팅 모델로 실제 루프 5경로 통과, 키 없는 real에서 SSE error UPSTREAM_ERROR → 화면 표시 |
| B7 | Amplitude connect·callback | fake 통과, real 승인 미검증 | - | connect = 계약 예시 원문, 즉시 connected, callback text/html 3종, 도구 실패에도 final |
| F5 | 설정 화면 | fake·real(저장소·택사노미) 통과 | - | Amplitude 새 탭 + 3.2s 후 "연결됨", 폴링 중단. real lastError 표시 |
| F6 | GitHub Pages 빌드 | 통과 (운영 왕복 미검증) | - | 자산 `/kbap-pm-agent/`, 번들에 base URL, mock 데이터 미포함 |
| B8 | 배포 파일·운영 검사 | 로컬 통과, 운영 미검증 | QA-4(확인됨) | check_b8: health, team-skyjs.github.io preflight, SSE 105초·ping 5회 |
| 계약/ADR | 운영 CORS 출처 | 확인됨 | QA-3(확인됨) | ADR-18 `https://team-skyjs.github.io` |

## 결함 이력

| ID | 내용 | 수신 | 상태 |
|---|---|---|---|
| QA-1 | 첫 메시지 후 채팅 헤더 제목이 새로고침 전까지 "새 대화" | frontend-dev | 확인됨 (cc53864) |
| QA-2 | 이벤트 인덱스·검색이 코드 밖 `specs/*.md`까지 포함(kbap-fe 120 vs 117) | backend-dev, cto(ADR-19) | 확인됨 (5c5a6ad) |
| QA-3 | 운영 CORS 출처 simhani1.github.io ≠ 레포 소유자 team-skyjs | cto | 확인됨 (d32661a, ADR-18) |
| QA-4 | B8 deploy env 예시·check_b8 출처가 ADR-18 이전 값 | backend-dev | 확인됨 (5c5a6ad) |

같은 출처 결함이 두 번(QA-3 → QA-4) 났다. 문서(ADR)와 배포 파일·검사 스크립트에 같은 값이 따로 적혀 있는 게 원인이다. 한 번 더 재발하면 cto에 구조 원인으로 올린다.

## 미검증 항목과 이유

| 태스크 | 항목 | 이유 | 필요한 것 |
|---|---|---|---|
| T042 | B6 실제 LLM: US2 퍼널 신규 단계 파일·함수 실존, US1 4부분 제안, `openai:` 모델 교체, 첫 tool_call 5초·final 3분 | `ANTHROPIC_API_KEY`·`OPENAI_API_KEY` 없음. 비용 발생 | 사용자가 `.env`에 키를 넣고 비용 사용 승인 |
| T046 후반 | MCP 동적 등록 → 브라우저 승인 → `list_tools` | 사람이 Amplitude에서 승인해야 함 | Amplitude 계정 승인 |
| T050 | B7 real: 승인 후 connected, 재시작 후 유지, metric 근거 수치 대조(SC-003), MCP 차단 시 빠진 근거 명시 | 위와 같음. QA는 외부에 OAuth 클라이언트를 추가 등록하지 않으려고 real connect를 호출하지 않았다 | 위와 같음 + LLM 키 |
| T054 일부 | quickstart 시나리오 10 real(Amplitude) | 위와 같음 | 위와 같음 |
| T057 | 운영 도메인 health, cloudflared 경유 SSE ping 유지, 운영 ACCESS_TOKEN 사용 여부 | 운영 미배포(홈서버 SSH·Docker Hub 권한) | `./deploy/push-and-deploy.sh` 실행, R4 확인 |
| T060 | GitHub Pages → 운영 백엔드 health·대화·SSE·채택 왕복 | 운영 미배포, Pages 미배포 | 레포 Pages Source "GitHub Actions", Variables `VITE_API_BASE_URL`, 운영 `CORS_ORIGINS=https://team-skyjs.github.io` |

T061(최종)은 fake 부분(계약 diff 없음, check 13개, quickstart 1~10)을 통과했지만 real 시나리오가 위 항목에 막혀 체크하지 않았다.

## 남은 위험

- **실제 LLM 경로 전체가 실호출 미검증.** 구조화 응답은 ADR-17로 ProviderStrategy(Anthropic `output_config.format`)를 쓴다. 가짜 모델 검사는 통과했지만 실제 공급자가 AgentAnswer 스키마를 받아들이는지, 모델이 계약 규칙(new 단계 location 필수 등)을 어기면 재시도 없이 `UPSTREAM_ERROR`로 끝나는 빈도는 모른다.
- **Amplitude 실제 연동 미검증.** 토큰 갱신·재시작 유지·MCP 도구 이름과 결과 크기는 실제 계정으로만 확인된다. 진행 중 OAuth는 프로세스 메모리에 하나만 있다(단일 워커 가정).
- **이벤트 인덱스의 테스트 파일 매치.** kbap-fe 117곳 중 17곳이 `src/lib/__tests__/*` 안의 문자열(`'track(EVENTS.app_opened)'`) 매치다. ADR-19 범위 안이지만 에이전트가 테스트 파일을 코드 근거로 인용할 수 있다.
- **함수명 추정은 정규식.** `enclosing_function`은 중괄호 균형 추정이라 일부 JSX 핸들러는 prop 이름(`onWrite` 등)으로 나온다.
- **운영 출처 값 중복 → 검사로 통제됨.** 출처의 단일 기준은 git remote(67c6f3a)다. ADR·env 예시·운영 `.env.prod`는 사본이고, `check_b8.py`가 remote 소유자로 `https://<owner>.github.io`를 계산해 운영 preflight와 대조한다. 확인: 서버 `CORS_ORIGINS=https://simhani1.github.io`이면 check_b8 실패(preflight 400), `https://team-skyjs.github.io`이면 통과. git 저장소가 없는 곳(컨테이너)에서는 `EXPECTED_ORIGIN` 없이 명시적으로 실패한다. 남은 틈: `EXPECTED_ORIGIN`을 손으로 틀리게 주면 사본 오류를 다시 숨길 수 있으니 개발 PC(레포 안)에서 돌린다. 주의: 이 check_b8 변경은 QA 확인 시점에 backend-dev 작업 트리에만 있고 아직 커밋 전이다
- **MySQL JSON 컬럼의 키 재정렬.** tool_call `input`은 키 순서가 바뀌어 나간다(값 동일, 계약은 순서를 규정하지 않음). 제안 evidence·measurement는 백엔드가 계약 순서로 되돌린다.
- **타입 캐스팅 우회 없음.** 프론트는 `any`·`as` 없이 런타임 파서로 필드 단위 검증한다(키 누락도 BAD_RESPONSE). 백엔드 라우트는 dict를 직접 만들고 Pydantic 모델은 검사 스크립트·AgentAnswer에만 쓴다. 응답 shape 보증은 검사 스크립트와 이 QA 대조에 기대고 있다.

## 갱신 이력

- 2026-10-15: 프론트 mock 삭제(345f633·0b98411) 후 F1·F6 재검증 통과(check-f1~f6 OK, 운영 빌드 자산 `/kbap-pm-agent/`, 헬스 배지 ok, F3 SSE 화면 흐름 그대로). 출처 결함 구조 대응(67c6f3a) 확인, 남은 위험 갱신.

## Phase 8: LLM SDK 전환 (B9, ADR-20) — 2026-10-15

| 태스크 | 결과 | 비고 |
|---|---|---|
| T071 B9 교차 검증 (fake + 가짜 전송) | 통과 | 계약 diff 0, langchain 0(코드·lock·설치본), check_b1~b7 OK, fake SSE 이벤트 이름·data 키 구조가 전환 전 기준선과 diff 0, 두 런타임 무키 실서버 error 경로 계약대로, 프론트 무변경 화면 흐름 통과 |
| T072 헌법 정합 | 통과 | 헌법 v1.1.0 = ADR-20. QA-5(plan·data-model 개정 전 문구) 확인됨 |
| T075 턴 상한 재검증 (AGENT_MAX_TURNS=10) | 통과 | 계약 diff 0, 옛 변수명 0(지정 범위), check_b6 OK, 두 런타임 10턴 = 모델 요청 10회, 부분 final 문구 = 계약, SSE 구조 불변 |
| T073 실제 키 검증 | 미검증 | `ANTHROPIC_API_KEY`·`OPENAI_API_KEY` 없음. 비용 0 원칙 |
| T068 env 예시 | 통과 | QA-6(운영 env 예시 안내 누락) 확인됨 |
| cto 추가 확인 | 통과 | anthropic SDK는 httpx2(가짜 전송도 httpx2), openai-agents 트레이스 꺼짐·송신 0, MCP 오류 isError 결과·클라이언트 예외 두 경로 모두 두 런타임에서 `tool_result failed` → `final` |

남은 위험(Phase 8):
- **두 실제 공급자 모두 실호출 미검증.** Anthropic `output_format=AgentAnswer`가 스키마 제약(`min_length`, `ge`, 판별 유니온)을 받아들이는지, OpenAI strict 스키마가 판별 유니온을 받아들이는지는 실제 API로만 확인된다(research.md R8). 가짜 전송 검사는 요청 파라미터와 응답 처리만 본다.
- **Anthropic 최종 응답은 `parsed_output`이 아니라 마지막 text 블록 JSON을 `AgentAnswer`로 다시 검증한다.** T065 문구와 다르지만 검증 결과는 같다. text 블록이 없으면 `UPSTREAM_ERROR`로 끝난다.
- **잘못된 모델 접두사는 서버 기동 실패다(ADR-20 의도).** 운영 env를 고칠 때 헬스체크가 아예 안 뜨는 형태로 드러난다. 배포 스크립트 3단계 헬스체크가 이를 잡는다.
- **MCP 클라이언트 예외 경로 → 검사로 통제됨.** a75addd로 check_b7이 isError 결과와 `call_tool` ConnectionError 두 경로를 두 런타임에서 모두 검사한다(T070, 9718928). QA 재실행 OK.
- **없는 도구 이름 호출 시 런타임 동작이 다르다 — 알려진 차이, ADR-20 기록(bdbeb6c).** OpenAI 런타임은 `ModelBehaviorError`로 실행 전체가 `UPSTREAM_ERROR`(추론 모델 자체 실패), Anthropic 런타임은 도구 실패로 보고 계속한다. 둘 다 계약 안이다. T073 실제 실행에서 OpenAI 쪽에 반복되면 부분 final로 돌리고 계약 비고에 사유를 추가한다(CTO 결정).
- **`docs/architecture/agent-loop-langchain.*`는 ADR-20 전환 전 기준선으로 보관한다(CTO 결정).** 옛 변수 `AGENT_MAX_TOOL_CALLS(5)`가 남아 있지만 상한 변수명 주석이 달려 있다(fc9b033). 현행 구조로 읽지 않는다.
- **OpenAI 사용량은 실행 1회 합계 1행.** 요청별 비용 추적은 안 된다.
- 위 Phase 1~7 남은 위험의 "실제 LLM 경로 실호출 미검증"은 런타임이 바뀌었을 뿐 그대로다(ProviderStrategy 문구는 ADR-20으로 대체됨).

## 운영 배포 검증 — 2026-10-15 (fix/prod-hostname)

운영: 백엔드 `https://<운영 API 주소>`(cloudflared, real), 프론트 `https://team-skyjs.github.io/kbap-pm-agent/`. 메시지 전송·대화 생성·채택 PATCH는 운영 DB와 LLM 비용 때문에 하지 않았다.

| 항목 | 결과 | 비고 |
|---|---|---|
| T057 health·preflight | 통과 | check_b8 재현(레포 안): health, team-skyjs.github.io preflight(from git remote). 허용 안 된 출처 400 |
| T057 cloudflared 경유 SSE 장시간 ping | 미검증 | 운영이 real이라 check_b8 SSE 검사 SKIP. 메시지 전송은 비용 |
| T057 운영 ACCESS_TOKEN 사용 여부 | **사용자 결정 필요** | 지금 꺼져 있다. 토큰 없이 대화 목록·설정이 읽히고, 누구나 메시지를 보내 LLM 예산을 쓸 수 있다 |
| T060 Pages ↔ 운영 조회 왕복 | 통과 | 헬스 배지 ok, 대화 목록·상세·설정 화면이 API와 일치, 자산 경로, 번들 API 주소 |
| T060 Pages에서 SSE·채택 왕복 | 미검증 | 메시지 전송·PATCH 금지 범위 |

T057·T060은 미검증 부분이 남아 체크하지 않았다.

운영 실사용 관찰(사용자 실행 1건, QA는 조회만):
- Anthropic 실제 호출로 `AgentAnswer` 구조화 응답이 `completed`. 택사노미·코드·Amplitude 세 소스 모두 사용(도구 14회). 위 "실제 공급자 실호출 미검증" 위험의 Anthropic 쪽 일부가 실증됐다. OpenAI 쪽은 그대로 미검증
- 시간: 첫 tool_call 약 11초(SC-004 "5초 안에 진행 표시" 초과), final 약 53초(3분 이내 충족). 표본 1건
- 비용: 질문 1건 $1.601, 입력 780,309 토큰·출력 4,031 토큰. 이 단가면 200달러로 약 125질문. 입력 대부분이 캐시 읽기면 실제 청구는 더 낮다(코드는 캐시 토큰을 입력 단가로 보수 계산). 실제 청구액은 Anthropic 콘솔로 대조 필요


## 003 프론트 재설계 — 2026-10-15 (feat/frontend-redesign, 최종 88a30db)

### 요약: 통과 12 / 실패 0 / 미검증 2

사용자 스토리 12개(토큰·셸·목록·메시지·마크다운·차트·입력창·상태·제안 카드·설정·접근성·자동 UI 검사)가 모두 통과했다. 결함 3건(UI-1 Drawer 포커스, UI-2 401을 세션 만료로 안내)은 모두 확인됨이다. 미검증 2건은 실제 키가 필요한 차트 블록 출현률(SC-007)과 사용자 주관 평가(SC-006)다.

| 기준 | 결과 | 값 |
|---|---|---|
| SC-001 가독성 | 통과 | 본문 16px·줄 간격 1.60, 보이는 글자 대비 최소 라이트 5.17·다크 6.37(라이트·다크 × 1280/768/375 × 채팅·설정) |
| SC-002 화면 리뷰 차단·높음 0 | 통과 | UI-1(차단)·UI-2(높음) 확인됨, 열린 결함 0 |
| SC-003 자동 UI 검사·axe | 통과 | check:ui 3회 연속 247 통과·50 건너뜀·실패 0. axe 심각·중대 0(채팅·설정·카드 전부 펼침·375 Drawer, 라이트·다크) |
| SC-004 기능 회귀 0 | 통과 | f1~f8·f6, b1~b9 OK, 계약 diff 0. 질문→진행(0.74s)→카드→채택→새로고침 유지, 409·토큰 오류 안내, 설정 등록·업로드·Amplitude 연결 그대로 |
| SC-005 번들 | 통과 | 증가 +242.2KB(≤300), 차트 청크 164.8KB(≤200) 별도·차트 없는 화면 요청 0 |
| SC-006 주관 평가 | 미검증 | 사용자 몫(T055) |
| SC-007 차트 블록 출현률 | 미검증 | 실제 키 필요(T054). 프롬프트 지시는 check_b9로 글자 단위 확인 |

check:ui 건너뜀 50의 내역: 세션 만료 18(접근 제한 병합 때 SESSION_EXPIRED 연결, fixme), live 9(CHECK_UI_LIVE=1 전용), 정적 검사 8(한 프로젝트에서만), 동작 줄이기 전용 6, 넓은 화면 전용 6, 좁은 화면 전용 3.

### 미검증 항목과 이유
- **차트 블록 출현률(T054, SC-007):** 실제 LLM 키가 필요하다.
- **주관 평가(T055, SC-006), 차트 라이브러리 확정(T032):** 사용자 몫이다.
- **check:ui의 CI 반영(T056):** 두 PR 머지 뒤 team-lead와 결정한다.
- **us8 live 시나리오:** 대화 생성을 `localhost:8000`으로 고정해 이 브랜치에서는 돌지 않는다(접근 제한 병합 뒤 같은 출처 전제). live 경로 자체는 QA가 실제 fake 백엔드로 진행→완료를 확인했다.

### 남은 위험
- **세션 만료 배너가 아직 연결되지 않았다.** 이 브랜치 api.ts는 SESSION_EXPIRED를 만들지 않는다. 접근 제한 PR 병합 때 연결하고 us7·us8 fixme를 켜야 한다.
- **실제 모델이 chart 블록을 얼마나 쓰는지 모른다.** 형식이 틀리면 원문 코드 블록으로 대체되므로 화면이 깨지지는 않는다.
- **번들이 재설계 전보다 +77KB(차트 제외) 커졌다.** 마크다운·GFM·한국어 강조 플러그인 몫이다. 차트 165KB는 차트가 있을 때만 내려받는다.
- **check:ui가 CI에 없다.** 지금은 개발자가 직접 돌려야 회귀를 잡는다.

### 실행 방법
```bash
cd frontend && npm ci && npx playwright install chromium
npm run check                      # f1~f5·f7·f8
VITE_API_BASE_URL=http://localhost:8000 npm run build && VITE_API_BASE_URL=http://localhost:8000 npm run check -- f6
npm run check:ui                   # 9 프로젝트(1280/768/375 × light/dark/reduced), 고정 응답
cd ../backend && uv run python checks/check_b9.py   # 레포 안에서
```

## 004 질문 마법사 — 2026-10-15 (feat/question-wizard, 최종 3a75c5f)

### 요약: 통과 7 / 실패 0 / 미검증 2

QA 태스크 7개(T008·T013·T020·T023·T025·T027·T028)가 모두 통과했다. 결함 4건(QA-11 문자열 ID 수용, QA-12 카드 연 채 전송 시 잘못된 선택 기록, UI-4 375 스크롤 영역 접근성, 처리 메모 유입)은 확인됨이다. PR 리뷰 반영(거절 사용량 기록, 공백 개선안 502, 카드 연 채 이탈 cancelled, 다듬기 20초 상한, 선택 기록을 서버 확인 뒤로, 카드에서 보낸 전송이 실패하면 기록 없이 같은 카드를 다시 열고 재시도하면 1건만 기록, 응답 대기 중 닫기·ESC 무시)도 확인했다. 열린 결함은 UI-5(낮음, 409로 카드가 다시 열릴 때 포커스가 본문으로 떨어짐, 다음 사이클) 하나다. 409·예산 초과 전송 실패는 실제 fake 백엔드로 재현했다. QA-13(형식이 틀린 응답의 사용량 미기록)도 69fe1b1에서 확인됨이다. 다듬기 모델은 비교로 Haiku 5.5로 정했다.

| 기준 | 결과 | 값 |
|---|---|---|
| 계약 08b 왕복 | 통과 | refine·choice 응답 키 = 계약 예시, 요청 검증 400(문자열·실수·불리언 ID 포함), 없는 ID 404, 4,000자 넘는 개선안 502·행 없음, 계약 diff 0 |
| 화면 흐름 (US1) | 통과 | 시연 1~8 실제 fake 왕복 실패 0. 빈 입력 비활성, 다듬는 동안 잠금, 첫 포커스, 네 선택, ESC, 카드 연 채 전송은 original로 닫힘 |
| 선택 기록 (US3, SC-002) | 통과 | 선택 POST 순서 refined·original·refined·cancelled·cancelled, 넣기는 전송 때 refined·비우면 cancelled·새 다듬기면 cancelled, 채택 비율 SQL 40.0·shown 5 |
| 사용량·예산 | 통과 | fake 0원 행, real 컨테이너 settings spentUsd = llm_usage 합계 |
| 다듬기 품질 (US2) | 통과 | 실제 키 10건, 목록 밖 이벤트 이름 0, 처리 메모 유입 0, 의도 0점 0건 |
| SC-001 지연 | 통과 | Haiku 중앙값 2.91초(thinking 끔, 1ce6b6d). 비교 기준 프롬프트에서 3.22초 |
| SC-004 비용 | 통과 | Haiku 1회 평균 약 $0.0004, 질문 1회 목표 $0.3의 0.13% |
| 화면 리뷰·접근성 | 통과 | 라이트·다크 × 1280·375 카드 대비 최소 5.17, axe critical·serious 0, 버튼 네 상태, 동작 줄이기 0s, 375×560까지 입력창 화면 안 |
| 기능 회귀 (SC-005) | 통과 | check f1~f5·f7~f9, check:ui 433 통과·71 건너뜀·실패 0, check_b1~b7·b9·b10 OK. 질문→카드→채택→새로고침 유지, 409 안내 후 입력 비활성 |

### 미검증 항목과 이유
- **SC-004의 분모:** 로컬에는 fake 기록만 있어 실제 agent 질문 비용이 없다. 운영 첫 질문 기록값($1.60)과 비용 PRD 목표($0.3)로 계산했다. 운영에서 refine·agent 평균을 llm_usage로 다시 보면 된다.
- **실제 키로 화면 끝까지:** 실제 모델은 엔드포인트(T013)와 비교 스크립트(T025)로만 돌렸다. 화면은 fake 고정 응답으로 검증했다. 응답 형식은 같아 경계면 위험은 낮다.
- check_b8은 운영 대상 검사라 로컬 회귀에서 뺐다.

### 남은 위험
- **운영 REFINE_MODEL 값은 team-lead가 Variables에 넣어야 한다.** 비우면 CODE_SUMMARY_MODEL로 대체된다.
- **모델이 프롬프트 규칙 문구를 질문에 옮길 수 있다.** thinking을 끈 뒤 1건("두 문장 이내로")이 나왔다. 에이전트 답변을 해치지는 않지만, 운영에서 다듬은 질문을 가끔 표본으로 본다.
- **1인 채점·1회 실행이다.** 같은 질문도 실행마다 다르게 다듬는다(결제 화면 질문이 T013에서는 대상을 바꿨고 이후에는 유지).
- **다듬기 호출이 SDK 내부 함수(transform_schema)에 기댄다.** 실패한 응답의 사용량을 기록하려고 parse 대신 create로 바꾼 결과다. SDK를 올릴 때 check_b10과 실제 키 1회 호출로 확인한다.
- **409로 카드가 다시 열리면 키보드 포커스를 잃는다(UI-5).** 마우스 사용에는 영향이 없고 실행이 끝나면 버튼이 살아난다.
- **llm_usage.cost_usd가 소수 넷째 자리다.** Haiku 1회 비용은 반올림 오차가 크다. 합계 판단에는 문제없다.

### 실행 방법
```bash
cd backend && uv run python checks/check_b10.py                       # 다듬기 계약·검증·기록·프롬프트 규칙 (fake)
cd backend && uv run python checks/compare_refine.py                   # 모델 비교, 실제 키·비용 발생, 결과 _workspace/06_refine_model_comparison.*
cd frontend && npm run check && npm run check:ui                       # f9·us12 포함
```
채택 비율은 `specs/004-question-wizard/data-model.md`의 SQL 한 줄로 본다.

## 005 대화 내보내기 — 2026-10-17 (feat/conversation-export, 백엔드 3c28f88·프론트 fc246e0)

### 요약: 통과 3 / 실패 0 / 미검증(사람) 1

통과는 기록 엔드포인트(T014), 회귀(T015), 인쇄·Markdown 자동 항목(T013 자동 부분)이다. 미검증(사람)은 Chrome 인쇄 대화상자 수동 확인(T013 수동 부분)이다. 결함 2건(QA-14 인쇄 후 차트 색 복원의 순서 의존, UI-6 긴 메시지가 다음 쪽으로 밀리는 빈칸)은 f9cb344에서 확인됨이고, 74dbb33(제목과 내용 붙이기, 질문 테두리)에서도 그대로다. 열린 결함은 0이다. 같은 대화의 A4 PDF가 15쪽에서 10쪽으로 줄고 빈칸 쪽과 표 행 갈림이 없어졌다. 인쇄 중 차트는 화면 폭과 무관하게 680px로 고정된다.

| 기준 | 결과 | 값 |
|---|---|---|
| 기록 엔드포인트 경계면 | 통과 | 201 응답 키 = 계약 v1.4 예시, 400·404 공통 에러 형식, 오류 요청은 행 없음, 대화 삭제 시 함께 삭제, 인증·CORS, 프론트 실제 요청 본문 {format} |
| 인쇄 흐름 (US1) | 통과(자동), 미검증(사람) | 인쇄 상태에서 카드 전부 펼침·머리글·조작 요소와 사용량 줄 숨김·다크에서도 밝은 인쇄, 취소 뒤 카드·차트 크기 복원. A4 PDF에서 차트 판독 가능·카드 쪼개짐 없음·가로 넘침 없음. 실제 인쇄 대화상자는 미확인 |
| Markdown (US2) | 통과 | 파일 이름 규칙, 메시지 수·원문·chart 블록 보존, 주소 없음, 파일 끝 줄바꿈 하나 |
| 기록 집계 (SC-003) | 통과 | 메뉴 PDF·Ctrl+P·Markdown 각각 정확히 한 행(중복 없음) |
| 화면 리뷰 | 통과 | 내보내기 메뉴 라이트·다크 × 1280·375: 비활성 조건, 키보드, axe 0, 대비 4.5 이상 |
| 기능 회귀 (SC-005) | 통과 | check f1~f10, check:ui 541 통과·71 건너뜀·실패 0, check_b1~b7·b9~b11, 계약 diff 0, 질문→제안→채택→새로고침 유지 |

### 미검증 항목과 이유
- **미검증(사람) — Chrome 인쇄 미리보기 수동 확인(quickstart 2~4):** 인쇄 대화상자가 열리면 페이지 스크립트가 멈춰 자동화로 조작할 수 없고, 헤드리스 Chrome은 afterprint를 보내지 않는다. 같은 인쇄 렌더링 엔진(page.pdf)에 인쇄 이벤트를 순서대로 보내 확인했다. 사용자가 다크 테마에서 내보내기 → PDF → 미리보기 확인 → 취소 후 차트 글자가 보이는지 한 번 보면 닫힌다.
- **fake 응답에는 차트가 없다.** 차트 인쇄는 QA 전용 DB에 차트 블록이 든 메시지를 넣어 확인했다.

### 남은 위험
- **카드는 절 단위로 나뉜다.** 카드 제목과 첫 절, 각 절, 차트, 코드, 표 행은 한 쪽에 둔다. 카드 전체가 한 쪽에 들어가지는 않는다.
- **DevTools에서 print 미디어만 켰다 끄면 차트가 인쇄 색으로 남는다.** 실제 인쇄는 afterprint를 보내 해당이 없다. 새로 고치면 돌아온다.
- **확인 범위 밖(ADR-32):** Safari·Firefox 인쇄, 수백 메시지 대화.

### 실행 방법
```bash
cd backend && uv run python checks/check_b11.py
cd frontend && npm run check && npx playwright test checks/ui/us13.spec.ts
```
형식별 건수는 `specs/005-conversation-export/data-model.md`의 SQL 한 줄로 본다.

## 실행 방법 (사용자가 직접 재현)

아래의 `pm-agent.example.com`은 예시 도메인이다. 실제 운영 주소는 GitHub Variables `PUBLIC_BASE_URL`에만 둔다.

```bash
# 1) 백엔드 + MySQL (fake 기본)
docker compose up -d --build
curl localhost:8000/api/health          # {"status":"ok","db":"ok","version":"0.1.0"}

# 2) 프론트 (Node 22 이상)
cd frontend && npm ci && VITE_API_BASE_URL=http://localhost:8000 npm run dev
# → http://localhost:5173/kbap-pm-agent/  에서 quickstart 시나리오 1~10

# 3) 검사 스크립트 전부
for c in b1 b2 b3 b4 b5 b6 b7; do docker compose exec backend uv run python checks/check_$c.py; done
cd frontend && npm run check
VITE_API_BASE_URL=https://pm-agent.example.com npm run build && VITE_API_BASE_URL=https://pm-agent.example.com npm run check -- f6

# 4) B8 검사 (레포 안에서 실행: 기대 출처를 git remote로 계산. SSE 105초 검사는 서버가 fake+FAKE_DELAY_SECONDS=21일 때만)
docker compose run -d --rm --name b8 -e FAKE_DELAY_SECONDS=21 -e CORS_ORIGINS=https://team-skyjs.github.io -p 8006:8000 backend
(cd backend && PUBLIC_BASE_URL=http://localhost:8006 uv run python checks/check_b8.py); docker rm -f b8

# 5) 계약 동기화
cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md   # 출력 없음
```

빌드본 preview(`npm run preview`, 출처 4173)로 확인하려면 `CORS_ORIGINS=http://localhost:5173,http://localhost:4173 docker compose up -d backend`로 띄운다.

실제 모드 확인은 `specs/001-pm-agent-prototype/quickstart.md` "실제 모드 확인" 절을 따른다. 실제 저장소 검증은 공용 DB를 건드리지 않게 별도 DB로 띄울 수 있다:

```bash
docker compose exec mysql mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS kbap_pm_agent_qa CHARACTER SET utf8mb4"
docker compose run -d --rm --name real -e AGENT_MODE=real -e DATABASE_URL=mysql://root:root@mysql:3306/kbap_pm_agent_qa -v qa-real-data:/data -p 8004:8000 backend
```
