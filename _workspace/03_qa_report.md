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
| T073 실제 키 검증 | 미검증 | `ANTHROPIC_API_KEY`·`OPENAI_API_KEY` 없음. 비용 0 원칙 |
| T068 env 예시 | 통과 | QA-6(운영 env 예시 안내 누락) 확인됨 |
| cto 추가 확인 | 통과 | anthropic SDK는 httpx2(가짜 전송도 httpx2), openai-agents 트레이스 꺼짐·송신 0, MCP 오류 isError 결과·클라이언트 예외 두 경로 모두 두 런타임에서 `tool_result failed` → `final` |

남은 위험(Phase 8):
- **두 실제 공급자 모두 실호출 미검증.** Anthropic `output_format=AgentAnswer`가 스키마 제약(`min_length`, `ge`, 판별 유니온)을 받아들이는지, OpenAI strict 스키마가 판별 유니온을 받아들이는지는 실제 API로만 확인된다(research.md R8). 가짜 전송 검사는 요청 파라미터와 응답 처리만 본다.
- **Anthropic 최종 응답은 `parsed_output`이 아니라 마지막 text 블록 JSON을 `AgentAnswer`로 다시 검증한다.** T065 문구와 다르지만 검증 결과는 같다. text 블록이 없으면 `UPSTREAM_ERROR`로 끝난다.
- **잘못된 모델 접두사는 서버 기동 실패다(ADR-20 의도).** 운영 env를 고칠 때 헬스체크가 아예 안 뜨는 형태로 드러난다. 배포 스크립트 3단계 헬스체크가 이를 잡는다.
- **MCP 클라이언트 예외 경로 → 검사로 통제됨.** a75addd로 check_b7이 isError 결과와 `call_tool` ConnectionError 두 경로를 두 런타임에서 모두 검사한다(T070, 9718928). QA 재실행 OK.
- **OpenAI 사용량은 실행 1회 합계 1행.** 요청별 비용 추적은 안 된다.
- 위 Phase 1~7 남은 위험의 "실제 LLM 경로 실호출 미검증"은 런타임이 바뀌었을 뿐 그대로다(ProviderStrategy 문구는 ADR-20으로 대체됨).

## 실행 방법 (사용자가 직접 재현)

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
VITE_API_BASE_URL=https://pm-agent-api.simhani1.dev npm run build && VITE_API_BASE_URL=https://pm-agent-api.simhani1.dev npm run check -- f6

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
