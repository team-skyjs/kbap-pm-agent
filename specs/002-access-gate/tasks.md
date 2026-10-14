---
description: "접근 제한 구현 태스크"
---

# Tasks: 접근 제한

**Input**: `specs/002-access-gate/`의 plan.md, spec.md, research.md, quickstart.md, contracts/README.md(정본 계약 v1.2)

**Tests**: 테스트 선작성 태스크는 없다(헌법 원칙 V). 모듈(G1~G5)마다 assert 검사 태스크 하나와 QA 교차 검증 태스크 하나를 둔다.

## 형식

`- [ ] T### [P?] [US?] [역할] 설명 (모듈)`

- **역할**: `[BE]` backend-dev, `[FE]` frontend-dev, `[QA]` qa-integrator, `[USER]` 사용자가 Cloudflare·GitHub 대시보드에서 직접 하는 일(코드 없음)
- **모듈**:
  - G1: 백엔드 정적 서빙과 같은 출처
  - G2: 세션 만료 구분
  - G3: CORS 제거와 예시 값
  - G4: 배포 통합
  - G5: 운영 검사

## 공통 규칙

- 운영 호스트명·도메인·IP·ssh 별칭·서버 경로를 파일·커밋·PR에 쓰지 않는다(CLAUDE.md). 예시는 `pm-agent.example.com`, 값은 `PUBLIC_BASE_URL` 같은 변수 이름이다.
- 응답 shape 기준은 계약 v1.2다(`_workspace/01_cto_api-contract.md`). 구현이 맞지 않으면 CTO에 요청한다.
- 커밋은 모듈 단위로 `feat/access-gate`에 한다. main 직접 커밋은 금지다.

## 선행 조건 (team-lead)

- [x] 헌법 "기술 제약"의 프론트·FE↔BE·비목표 줄을 ADR-22에 맞게 개정했다(v1.2.0, 79d45b9). G1 병합을 막던 조건이 해소됐다.
- [x] 2026-10-15 재개: main(v1.3.0, Pages+공유 토큰)에 보관 브랜치를 합치고 헌법을 v1.4.0으로 재개정했다. 전환 기간에는 토큰이 운영 필수로 남는다(Phase 8에서 끈다).

---

## Phase 1: Setup

없음. 기존 `frontend/`·`backend/`·`deploy/`를 그대로 쓴다.

---

## Phase 2: Foundational — 백엔드가 프론트를 정적 서빙 + 같은 출처 `/api` 헬스 왕복, 배포 통합 (G1, G4)

**Purpose**: 모든 스토리의 전제. 로컬에서 운영과 같은 같은 출처 구조(컨테이너 하나가 `/`와 `/api`를 함께 제공)를 띄우고, 같은 배포 흐름으로 그 이미지가 홈서버에 올라간다.

**⚠️ 순서 주의**: `pages.yml`(T013)을 G1과 같은 PR에서 지운다. 남겨 두면 G1 병합 순간 Pages가 상대 경로 빌드로 재배포되어 깨진다. 지우면 마지막 정상 Pages가 새 입구 검증(T022)까지 그대로 남는다.

### G1 — 백엔드 정적 서빙과 같은 출처

- [x] T001 [FE] `frontend/vite.config.ts`: `base: '/'`로 바꾼다. 개발 서버에 `server.proxy: { '/api': 'http://localhost:8000' }`를 둔다. 주석에서 Pages 언급을 지운다 (G1)
- [x] T002 [FE] `frontend/src/api.ts`: `API_BASE_URL`과 `VITE_API_BASE_URL` 참조를 지우고 상대 경로 `/api/...`로 호출한다(계약 v1.2 Base URL). `NETWORK_ERROR` 문구에서 주소 출력을 뺀다. 남은 `VITE_API_BASE_URL` 참조(`vite-env.d.ts` 등)도 지운다 (G1)
- [ ] T003 [BE] `backend/Dockerfile`: node 단계(`node:22-alpine`)에서 `frontend/`를 `npm ci && npm run build && npm run check -- f6`로 빌드하고, 산출물 `dist/`를 백엔드 이미지에 복사한다. 빌드 컨텍스트는 레포 루트(`-f backend/Dockerfile`)이며 `.dockerignore`로 `node_modules`·`.venv`를 뺀다. 삭제된 `pages.yml`의 f6 검사를 이어받는다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G1)
- [ ] T004 [BE] `backend/app/main.py`: 정적 파일과 토큰 범위를 다룬다. (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G1)
  - 정적 마운트: 모든 `/api` 라우터 뒤에 `StaticFiles(directory=<dist>, html=True)`를 `/`에 마운트한다. dist가 없으면(로컬 백엔드 단독 실행) 마운트를 건너뛴다.
  - 404 유지: 정의되지 않은 `/api/...`는 계약 404 `NOT_FOUND` JSON 그대로여야 하고 `index.html`로 떨어지지 않는다.
  - 토큰 범위: 공유 토큰 미들웨어 검사를 `/api/` 경로로 한정한다(계약 v1.2 인증 절). 정적 파일에 토큰을 요구하면 브라우저가 앱을 받지 못한다.
  - 캐시: `index.html`은 `Cache-Control: no-cache`, `/assets/`는 기본값이다.
- [ ] T005 [BE] 레포 루트 `docker-compose.yml`: `web` 서비스를 두지 않는다(있으면 삭제). `backend` 빌드 컨텍스트를 레포 루트 + `backend/Dockerfile`로 바꿔 `localhost:8000`이 `/`와 `/api`를 함께 제공하게 한다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G1)
- [x] T006 [FE] `frontend/checks/check-f6.ts`의 기대값을 바꾼다. `dist/index.html` 자산 경로가 `/assets/`로 시작하고 번들에 `http://`·`https://` API 주소가 박혀 있지 않아야 한다 (G1)
- [x] T007 [FE] `deploy/checks/check_g1.sh`: 로컬 compose가 뜬 상태에서 curl로 다음을 assert한다. 실패하면 0이 아닌 종료다. (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G1 검사)
  - `localhost:8000/`이 200 `text/html`이다.
  - `localhost:8000/api/health`가 `{"status":"ok","db":"ok","version":"0.1.0"}`다.
  - fake 모드 메시지 전송 SSE를 같은 출처(`localhost:8000`)로 받아 첫 `tool_call`이 5초 안에 오고 `final`로 끝난다.
- [x] T008 [QA] G1 교차 검증: `docker compose up -d --build` 후 `check_g1.sh`와 `npm run check -- f6`를 실행한다. 브라우저 `localhost:8000`에서 네트워크 요청이 전부 같은 출처 `/api/...`이고, `ACCESS_TOKEN`이 켜져 있어도 첫 화면(`/`, `/assets/`)이 토큰 없이 열리는지 본다. 정의되지 않은 `/api/nope`이 계약 404 JSON이어야 한다. 001 quickstart 시나리오 3~5(질문→제안→채택)가 동작해야 한다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G1 QA)
- [x] T040 [FE] `frontend/Dockerfile`·`frontend/nginx.conf`·`frontend/.dockerignore`를 삭제하고 `check_g1.sh` 대상을 `localhost:8000`으로 바꾼다(8a8e311) (G1)

### G4 — 배포 통합

- [ ] T009 [BE] `.github/workflows/deploy-backend.yml`을 `git mv`로 `deploy.yml`로 바꾼다. (G4)
  - 트리거: `paths`에 `frontend/**`를 추가한다.
  - 빌드: `build` job이 이미지 하나(`ghcr.io/<owner>/kbap-pm-agent`, 컨텍스트 레포 루트, `-f backend/Dockerfile`, 프론트 포함)를 커밋 태그로 빌드·푸시한다. 웹 이미지는 없다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업).
  - 정리: `CORS_ORIGINS` 관련 env 줄과 주석의 러너 이름·운영 식별자를 지운다.
- [ ] T010 [BE] `deploy/docker-compose.kbap-pm-agent.yml`: 서비스는 `kbap-pm-agent` 하나다(웹 서비스가 있으면 삭제). `env_file`은 `${ENV_FILE:?}` 필수다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업) (G4)
- [ ] T011 [BE] `deploy/deploy.kbap-pm-agent.sh`·`deploy/push-and-deploy.sh`: 서버 경로 기본값을 지우고 `COMPOSE_FILE`·`ENV_FILE`·원격 경로를 환경변수 필수로 바꾼다. `push-and-deploy.sh`의 ssh 별칭 기본값(`HOST="${1:-...}"`)도 지우고 첫 인자를 필수로 한다. 없으면 사용법을 출력하고 종료 코드 1이다(QA 지적). 헬스체크에 `127.0.0.1:8001/`(정적 `index.html`)과 기존 `127.0.0.1:8001/api/health`를 둔다한다 (G4)
- [ ] T012 [BE] `deploy/README.md`·`deploy/kbap-pm-agent.env.example`: 운영 도메인을 `pm-agent.example.com`이나 `<운영 호스트명>`으로 바꾼다. `CORS_ORIGINS`·`VITE_API_BASE_URL`·Pages 절차를 지운다. 다음을 적는다. (G4)
  - 터널 규칙: 운영 호스트명 → `http://kbap-pm-agent:8000`(기존 규칙 그대로, 변경 없음).
  - Access 설정 절차: T020·T021·T024 요약.
  - 서비스 토큰 교체 절차: 만료 1년, 새 토큰 발급 → Secrets 교체 → 옛 토큰 폐기.
- [x] T013 [FE] `.github/workflows/pages.yml` 삭제(위 순서 주의) (G4)
- [ ] T014 [BE] `deploy/checks/check_g4.sh`: assert 항목은 다음과 같다. (G4 검사)
  - 더미 env로 `docker compose -f deploy/docker-compose.kbap-pm-agent.yml config`가 성공하고 서비스가 `kbap-pm-agent` 하나뿐이다.
  - `ENV_FILE` 없이는 compose가 실패한다(필수화 확인).
  - `deploy/push-and-deploy.sh`를 인자 없이 실행하면 원격 접속 전에 종료 코드 1로 끝난다. 레포의 셸 스크립트에 `${1:-` 형태로 호스트·별칭 기본값을 두는 줄이 없다(ssh 별칭 검출).
  - `deploy/`·`.github/`·`backend/`·`frontend/`에 서버 사용자 경로(`/home/`)와 `deploy/README.md` 이전 버전에 있던 운영 도메인 문자열이 없다. 문자열은 스크립트에 쓰지 않는다. 비교 기준은 CI Variable `PUBLIC_BASE_URL`의 호스트이고, 로컬에서는 같은 이름의 환경변수다.
- [ ] T015 [QA] G4 교차 검증: 다음을 확인하고 `check_g4.sh`를 실행한다. (G4 QA)
  - 비고: 운영 항목(배포 실행·홈서버 healthy·터널 불변)은 머지 후 첫 자동 배포에서 검증한다. 미머지 브랜치로 운영을 바꾸지 않는다(team-lead 결정).
  - 비고: verify job 분기(fb881c0) 로컬 확인 — `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET` 중 하나라도 비면 경고 후 종료 0, 둘 다 있으면 check_b8 엄격 실행(실패 시 종료 1), 둘 다 있고 `PUBLIC_BASE_URL`이 비면 종료 1. 하나만 설정된 반쯤 설정 상태도 경고 후 통과하므로 T024 직후 첫 배포 로그에서 경고가 사라졌는지 확인한다. 실행 확인은 머지 후.
  - `workflow_dispatch`로 배포를 실행해 이미지 하나가 커밋 태그로 푸시된다.
  - 홈서버에서 컨테이너가 healthy이고 배포 스크립트 헬스(정적 `/`와 `/api/health`)가 통과한다.
  - 이 시점에는 터널이 아직 백엔드를 직접 가리키므로 운영 동작이 바뀌지 않아야 한다.
  - 운영 식별자 세 종류(서버 경로, 운영 도메인, ssh 별칭)가 `deploy/`·`.github/`에 남지 않았다.

**Checkpoint**: 로컬은 같은 출처로 동작하고, 정적 서빙을 포함한 이미지가 홈서버에 떠 있다. 아직 Access 전이며 공유 토큰이 API를 잠근다.

---

## Phase 3: User Story 1 — 허용된 팀원이 로그인 한 번으로 사용한다 (Priority: P1) (G2 + 사람 설정)

**Goal**: 허용 이메일로 PIN 로그인 후 질문·제안·설정·Amplitude 연결이 기존처럼 동작하고, 세션이 만료되면 다시 로그인을 안내한다.

**Independent Test**: 운영 호스트명에서 허용 이메일로 로그인하고 질문 하나 → 제안 → 설정 화면 → Amplitude 연결을 확인한다. `CF_Authorization` 쿠키를 지우고 질문을 보내면 "다시 로그인" 안내가 뜨고 입력값이 남는다.

### G2 — 세션 만료 구분

- [x] T016 [US1] [FE] `frontend/src/api.ts` `rawFetch`·`sendMessage`: 모든 요청에 `X-Requested-With: XMLHttpRequest`를 붙이고 `redirect: 'manual'`을 쓴다. 다음 셋 중 하나면 `ApiError('SESSION_EXPIRED', ...)`를 던진다(계약 v1.2 접근 계층 응답, research R1). (G2)
  - `res.type === 'opaqueredirect'`
  - 401·403 중 본문이 계약 에러 JSON이 아닌 것
  - 상태 5xx가 아니면서 `content-type`이 `application/json`·`text/event-stream`이 아닌 응답
  - 상태 5xx이면서 계약 JSON이 아닌 응답(터널·Cloudflare 오류 페이지)은 `NETWORK_ERROR`다(계약 v1.2 문구 개정, frontend-dev 요청).
  - 백엔드의 401 `UNAUTHORIZED` JSON은 기존대로 처리한다.
- [x] T017 [US1] [FE] `frontend/src/Chat.tsx`·`SettingsPage.tsx`: `SESSION_EXPIRED`면 화면 상단에 "로그인이 만료되었습니다" 안내와 "다시 로그인" 버튼(`location.reload()`)을 둔다. 채팅 입력값은 지우지 않는다(spec 엣지 케이스). 스트림 도중 끊김은 기존 상세 재조회를 유지한다 (G2)
- [x] T018 [US1] [FE] `frontend/checks/check-g2.ts`: 가짜 `Response` 여섯 종을 판정 함수에 넣는다. `opaqueredirect`, 401 `text/html`, 200 `text/html`은 `SESSION_EXPIRED`여야 한다. 401 계약 JSON `UNAUTHORIZED`는 `UNAUTHORIZED`, 502·504 `text/html`은 `NETWORK_ERROR`여야 한다 (G2 검사)
- [x] T019 [US1] [QA] G2 교차 검증: `check-g2.ts`를 실행한다. 브라우저 요청 가로채기(또는 로컬 프록시)로 세 응답을 흉내 내, 안내 표시와 입력 보존을 확인한다 (G2 QA)

### 사람 설정 (Cloudflare 대시보드)

- [ ] T020 [US1] [USER] Zero Trust → Networks → Tunnels: 운영 호스트명의 공개 호스트 규칙이 `http://kbap-pm-agent:8000` 그대로인지 확인만 한다. 정적 서빙은 같은 컨테이너라 규칙 변경이 없다 (2026-10-15 백엔드 정적 서빙으로 변경, 재작업)
- [ ] T021 [US1] [USER] Zero Trust → Access → Applications: 다음과 같이 설정한다.
  - 운영 호스트명 전체(경로 비움)로 Self-hosted 애플리케이션을 만든다. Login method는 One-time PIN, 세션 길이는 24시간(PRD 열린 질문, 필요하면 조정)이다.
  - 정책 "Allow: Emails"에 허용 이메일 2개를 넣는다. 이메일은 레포·대화 어디에도 적지 않는다.
- [ ] T022 [US1] [QA] US1 운영 검증. 결과는 `_workspace/03_qa_report.md`에 기록하되 운영 호스트명은 쓰지 않는다. (US1 QA)
  - 로그인·화면: 허용 이메일로 로그인하면 헬스 표시가 정상이다(US1-1).
  - 질문: 진행 표시와 제안이 기존 형태로 오고 첫 진행 5초·제안 3분 이내다(US1-2, SC-004).
  - Amplitude: 설정 → Amplitude 연결 → 승인 후 "연결됨"이다(US1-3, research R2 두 경우).
  - 세션 유지: 브라우저를 닫았다 열어도 재로그인이 없다(US1-4).
  - 세션 만료: research R1 curl 두 줄 결과를 확인하고, 쿠키 삭제 후 질문해 안내를 확인한다.
  - R2가 실패하면 CTO에 보고한다(대체: 콜백 경로 Bypass 정책).

**Checkpoint**: 새 입구가 동작한다. 이 검증 전에는 Phase 5(옛 경로 폐쇄)를 하지 않는다.

---

## Phase 4: User Story 2 — 허용되지 않은 요청은 서버에 닿지 않는다 (Priority: P1) (G5)

**Goal**: 허용되지 않은 화면·API 요청이 모두 Access에서 멈추고, 운영 검사는 서비스 토큰으로 바깥 경로 전체를 검증한다.

**Independent Test**: 쿠키·토큰 없이 `/`, `/api/health`, `/api/conversations`, 메시지 전송을 호출하면 모두 백엔드 응답이 아니고 백엔드 로그에 남지 않는다. `check_b8.py`가 토큰 유무 두 경우를 모두 통과한다.

- [x] T023 [US2] [BE] `backend/checks/check_b8.py` 재작성(ADR-23). (G5 검사)
  - 정리: git remote 기반 Pages 출처 로직을 지운다.
  - 토큰 있음: `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`를 `CF-Access-Client-Id`·`CF-Access-Client-Secret` 헤더로 보낸다. `/`가 200 `text/html`, `/api/health`가 계약 JSON, SSE 장시간 시나리오(fake 모드일 때만, 기존 로직)가 100초 이상 유지되면 통과다.
  - 토큰 없음: `/api/health`·`/api/conversations`·메시지 전송 POST가 계약 JSON이 아니어야 한다. `X-Requested-With`를 붙이면 401이어야 한다(research R1, 아니면 경고만 내고 R1 대체 판정으로 넘긴다).
  - 다른 출처 preflight: 토큰과 함께 `Origin: https://evil.example.com`을 보내면 `access-control-allow-origin`이 없어야 한다.
  - 출력: 각 줄에 PASS/FAIL을 찍고, 운영 호스트명은 출력하지 않는다.
- [ ] T024 [US2] [USER] 서비스 토큰 연결. (G5)
  - Access → Service credentials에서 서비스 토큰 `kbap-pm-agent-check`(만료 1년)를 만든다.
  - T021 애플리케이션에 정책 "Service Auth: 이 토큰"을 추가한다.
  - GitHub Secrets `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`에 넣는다.
- [ ] T025 [US2] [QA] G5·US2 교차 검증: (G5 QA)
  - `check_b8.py`를 개발 PC에서 실행한다(서비스 토큰은 Secrets 값을 사람이 환경변수로 준다). SSE 장시간 항목은 운영을 잠시 fake 모드로 띄울 수 있을 때만 한다(research R3).
  - 허용 목록 밖 이메일로 PIN 로그인을 시도하면 거부된다(US2-3).
  - 토큰 없는 호출을 보낸 시각에 `docker logs kbap-pm-agent`에 해당 요청이 없다(US2-2).
  - 서비스 토큰 정책 공존(research R4)이 동작한다.

---

## Phase 5: User Story 3 — 옛 공개 경로가 닫힌다 (Priority: P2) (G3)

**Goal**: 옛 Pages 주소와 옛 출처 호출을 닫고, 백엔드에서 CORS를 걷어낸다. T022 통과 후에 병합·배포한다.

**Independent Test**: 옛 Pages 주소가 404이고, 어느 출처의 preflight도 허용되지 않는다.

- [ ] T026 [US3] [BE] `backend/app/main.py`: `CORSMiddleware`와 `CORS_ORIGINS` 읽기를 지운다. 미들웨어 순서 주석(CORS 바깥 감싸기)을 정리한다. 레포 루트 `docker-compose.yml`, `.env.example`, `deploy/kbap-pm-agent.env.example`에서 `CORS_ORIGINS`를 지운다 (G3)
- [ ] T027 [US3] [BE] 계약 v1.2 예시 값을 맞춘다. `backend/app/amplitude.py`의 fake connect 응답과 `backend/checks/examples.py`의 `authorizationUrl`을 계약 `08-amplitude.md` 예시와 글자 단위로 같게 한다(redirect_uri 호스트 `pm-agent.example.com`). fake 모드는 "예시를 그대로 응답"이다 (G3)
- [ ] T028 [US3] [BE] `backend/checks/check_b1.py`: CORS preflight 기대를 반전해 `Origin: http://localhost:5173`과 임의 출처 모두 `access-control-allow-origin` 헤더가 없어야 한다. `check_b7.py`의 connect 예시 비교가 새 URL로 통과해야 한다 (G3 검사)
- [ ] T029 [US3] [QA] G3 교차 검증: `check_b1.py`·`check_b7.py`를 순차 실행하고 계약 diff 0을 확인한다. 로컬 `localhost:8000`(정적 서빙) 동작이 그대로여야 한다(같은 출처는 CORS가 필요 없다). quickstart 로컬 시나리오 3을 본다 (G3 QA)
- [ ] T030 [US3] [USER] GitHub 레포 Settings → Pages에서 사이트를 내린다(Source를 None으로 또는 Unpublish). Settings → Variables에서 `VITE_API_BASE_URL`·`CORS_ORIGINS`를 삭제한다. T029 배포 후에 한다
- [ ] T031 [US3] [QA] US3 운영 검증: 옛 Pages 주소가 404다(US3-1). 옛 Pages 출처로 운영 preflight를 보내면 허용되지 않는다(US3-2, `check_b8.py` preflight 항목) (US3 QA)

---

## Phase 6: User Story 4 — 배포 한 번에 프론트와 백엔드가 함께 나간다 (Priority: P2)

**Goal**: main 병합이 이미지 하나(백엔드+프론트)를 배포하고, 배포 직후 운영 검사가 Access를 통과해 돈다. 배포 통합 자체는 G4(Phase 2)에서 했고, 여기서는 배포 후 검사를 붙인다.

**Independent Test**: 프론트만 바꾼 PR을 병합하면 배포 작업 하나가 이미지를 새로 빌드해 올리고 `check_b8` 단계가 통과한다.

- [x] T032 [US4] [BE] `.github/workflows/deploy.yml`에 `deploy` 이후 job `verify`를 추가한다. `ubuntu-latest`에서 `check_b8.py`를 실행하고, 환경변수 `PUBLIC_BASE_URL`(Variables)·`CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`(Secrets)를 쓴다. SSE 장시간 항목은 real 모드라 건너뛰는 기존 분기를 쓴다. 로그에 운영 호스트명을 찍지 않는다(GitHub가 Variables를 마스킹하지 않으므로 스크립트가 출력하지 않는다) (G5)
- [ ] T033 [US4] [QA] US4 검증: 프론트만 바꾼 작은 PR을 병합해 배포 작업이 프론트 변경을 포함한 이미지를 새 태그로 교체하고(US4-1, `frontend/**` 경로 트리거) `verify` job이 통과하는지(US4-2) 확인한다 (US4 QA)

---

## Phase 7: Polish

- [x] T034 [QA] `_workspace/03_qa_report.md`·`03_qa_findings.md`에서 운영 도메인 문자열을 `<운영 호스트명>`으로 바꾼다(QA 소유 파일, research R7)
- [ ] T035 [USER] git 히스토리에 남은 운영 도메인·서버 경로를 어떻게 할지 정한다. 히스토리 재작성(force push)은 열린 PR·브랜치를 깨므로 사용자 결정이다(research R7). 결정을 team-lead에 알린다
- [ ] T036 [QA] 최종 검증: (최종 QA)
  - quickstart 로컬·운영 시나리오 전부를 돈다.
  - 계약 동기화 `cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md`의 출력이 없어야 한다.
  - 모든 검사(`check_g1.sh`, `check_g4.sh`, `check-g2`, `check-f6`, `check_b1`, `check_b7`, `check_b8`)를 순차 실행한다.
  - SC-001(1주 후 Access 로그와 백엔드 로그 대조) 확인 날짜를 리포트에 적는다.

---

## Phase 8: 전환 마감 — 공유 토큰 끄기 (2026-10-15 재개 시 추가)

**목적**: US2 운영 검증(T025)이 끝나면 Access만 남기고 전환 장치인 공유 토큰을 끈다. 이 순서를 지켜야 한 순간도 API가 공개되지 않는다.

- [ ] T037 [BE] T025 통과 뒤: `.github/workflows/deploy.yml`에서 `ACCESS_TOKEN` 필수 검사(`:?`)와 verify job의 `ACCESS_TOKEN` env를 지운다. `deploy/deploy.kbap-pm-agent.sh`의 토큰 env 검증 단계와 보호 경로 401 확인 단계를 지운다. `deploy/kbap-pm-agent.env.example`·`deploy/README.md`의 토큰 문구를 "비움(Access가 막는다)"으로 되돌린다. 백엔드 코드는 그대로(비우면 꺼진다).
- [ ] T038 [USER] GitHub Secrets에서 `ACCESS_TOKEN`을 빈 값으로 바꾸고(또는 삭제) main 배포를 한 번 돌린다. 설정 화면의 토큰 입력은 비워도 된다.
- [ ] T039 [QA] 토큰 없이 Access 경유 보호 경로가 200, 게이트 밖 직접 요청은 서버에 닿지 않음(US2-1·2 재확인), `check_b8.py`가 `ACCESS_TOKEN` 없이 통과. 결과를 `_workspace/03_qa_report.md`에 기록(운영 호스트명 비기재).

---

## 요구사항 커버리지

| 요구 | 태스크 |
|---|---|
| FR-001 같은 호스트명·상대 경로 | T001~T005, T007, T020 |
| FR-002 허용 목록·PIN | T021, T025 |
| FR-003 미허용 요청 차단(헬스 포함) | T020, T021, T023, T025 |
| FR-004 세션 유지 | T021(24시간), T022 |
| FR-005 기존 기능 유지 | T004(SSE), T008, T022 |
| FR-006 세션 만료 안내 | T016~T019 |
| FR-007 옛 주소 폐쇄·허용 출처 제거 | T013, T026, T030, T031 |
| FR-008 배포 하나로 둘 다 | T009~T011, T015, T033 |
| FR-009 운영 검사가 Access 통과 | T023, T024, T032 |
| FR-010 허용 목록 변경에 코드 없음 | T021(대시보드 관리, 설계로 충족) |
| SC-001 미허용 도달 0건(1주) | T025, T036 |
| SC-002 로그인 한 번으로 완료 | T022 |
| SC-003 옛 경로 닫힘 | T031 |
| SC-004 5초·3분 유지 | T007, T022 |

## Dependencies & Execution Order

- Phase 8(T037→T038→T039)은 T025 통과가 선행 조건이다. T030(Pages 내리기)·T031은 Phase 8과 독립이며 T022 뒤 언제든 가능.

- **선행 조건**(헌법 개정): 해소(79d45b9).
- **Phase 2**: G1(T001~T008)과 G4(T009~T015)는 병렬이다. 다만 T013(pages.yml 삭제)은 G1과 같은 PR이다.
- **Phase 3**: T020(터널 규칙 확인)은 T015 이후다. T021(Access)은 T020과 같이 하거나 바로 뒤에 한다. G2(T016~T019)는 Phase 2 G1 이후 병렬이다. T022는 T019·T021 이후다.
- **Phase 4**: T024는 T021 이후, T025는 T023·T024 이후다.
- **Phase 5**: **T022 통과 후에만** 병합·배포한다(CORS를 먼저 지우면 아직 쓰는 옛 Pages가 깨진다). T030은 T029 배포 후, T031은 T030 이후다.
- **Phase 6**: T032는 T023·T024 이후다.
- **Phase 7**: T034는 언제든, T035는 사용자, T036은 마지막이다.

모듈 의존: `G1 → G2`, `G1 ∥ G4`, `G4 → (사람 설정) → G5`, `G5·T022 → G3`.

## Parallel Opportunities

- T003(Dockerfile 프론트 빌드 단계)과 T004(정적 마운트·토큰 범위)는 같은 사람(backend-dev)이 이어서 한다. frontend-dev는 G2를 병렬로 진행한다.
- frontend-dev는 G1 → G2, backend-dev는 G4 → G5(T023) → G3 순서로 병렬 진행한다.
- 사람 설정 T020·T021·T024는 한 번에 대시보드에서 끝낼 수 있다(T015 이후).

## Implementation Strategy

1. G1·G4를 한 PR로 낸다(pages.yml 삭제 포함). 병합 후 홈서버 컨테이너가 정적 프론트를 함께 제공한다. Access 전까지는 공유 토큰이 API를 잠근다.
2. 사용자가 터널·Access를 설정하고(T020·T021), QA가 새 입구를 검증한다(T022). 같은 시기 G2를 병합한다.
3. 서비스 토큰(T024)과 운영 검사(T023·T032)를 붙인다.
4. 옛 경로를 닫는다(G3 병합 → T030 → T031).
5. 최종 검증(T036)과 1주 후 SC-001을 확인한다.

## Notes

- `[USER]` 태스크는 대시보드 작업이라 커밋이 없다. 끝나면 QA나 team-lead에 알린다.
- 공유 토큰 `ACCESS_TOKEN`은 전환 기간 운영 필수(main의 배포 검사), US2 검증 후 Phase 8에서 끈다(코드 제거는 별도 결정).
