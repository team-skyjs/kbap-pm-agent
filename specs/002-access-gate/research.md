# Research: 접근 제한

Technical Context에 NEEDS CLARIFICATION은 없다. 이 문서는 ADR-22·23이 기대는 동작 가정(R1~R4)과 설계 선택 비교(R5·R6), 운영 정보 노출 정리(R7)를 다룬다. 운영 호스트명은 `<운영 호스트명>`으로만 쓴다(값은 GitHub Variables `PUBLIC_BASE_URL`).

## R1. 만료 세션에서 Access가 fetch에 무엇을 돌려주나

- Decision: 프론트는 모든 요청에 `X-Requested-With: XMLHttpRequest`를 보내고 `redirect: "manual"`을 쓴다. 다음 셋 중 하나면 세션 만료로 판정한다(계약 v1.2 공통 절).
  - 이 문서의 JSON 에러 형식이 아닌 401·403
  - `opaqueredirect`
  - 상태 5xx가 아닌 `text/html`. 5xx HTML(nginx·Cloudflare 오류 페이지)은 연결 실패로 다룬다. Access는 5xx로 거부하지 않는다
- Rationale: Cloudflare의 세션 관리 문서는 요청에 `X-Requested-With: XMLHttpRequest`가 있으면 만료 세션에 401을 준다고 설명한다. 헤더가 없으면 `<팀>.cloudflareaccess.com` 로그인으로 302 리다이렉트하는데, fetch가 이를 따라가면 교차 출처라 CORS 실패(TypeError)로 보인다. 여러 앱 포럼 사례가 이 증상이었다. `redirect: "manual"`은 헤더가 무시되는 경우의 대비다.
- 출처 신뢰도: 401 동작은 검색으로 찾은 Cloudflare 문서(비표준 포트 URL로 노출)에서만 확인했고 표준 문서 주소로 재확인하지 못했다. 그래서 가정이다.
- **검증 방법** (T022, Access 설정 후): 쿠키 없는 상태에서 다음 두 요청을 보낸다.
  ```bash
  curl -si -H 'X-Requested-With: XMLHttpRequest' "$PUBLIC_BASE_URL/api/health" | head -1   # 기대: 401
  curl -si "$PUBLIC_BASE_URL/api/health" | head -1                                         # 기대: 302 (Location: ...cloudflareaccess.com)
  ```
  브라우저에서 세션 쿠키 `CF_Authorization`을 지운 뒤 질문을 보내 "다시 로그인" 안내가 뜨는지도 본다.
- **틀리면**: 401이 오지 않아도 `opaqueredirect` 판정이 302를 잡는다. 둘 다 아니면 응답 `content-type`이 JSON·SSE가 아닌 모든 비 5xx 응답을 세션 만료로 넓힌다(5xx는 계속 연결 실패). `api.ts` 한 곳만 바뀐다.

## R2. Amplitude OAuth 콜백이 Access 뒤에서 이어지나

- Decision: 콜백도 Access 뒤에 둔다(우회 정책 없음).
- Rationale: 콜백은 Amplitude 승인 후 브라우저의 최상위 GET 이동이다. 같은 브라우저에 Access 세션 쿠키가 있으면 통과한다. 세션이 없으면 Access가 로그인 후 원래 URL(쿼리 포함)로 돌려보내는 것이 일반 동작이라 `code`·`state`가 유지될 것으로 본다.
- **검증 방법** (T022):
  1. 로그인 상태에서 설정 화면 → Amplitude 연결 → 승인을 진행한다. 콜백 페이지 "Amplitude 연결 완료"가 뜨고 상태가 "연결됨"이면 통과다.
  2. `CF_Authorization`을 지운 직후 승인을 진행한다. 로그인 뒤 콜백 페이지가 뜨는지 본다.
- **틀리면**: Access 애플리케이션에 경로 `/api/integrations/amplitude/callback`만 대상으로 하는 **Bypass** 정책(또는 별도 앱)을 둔다. 콜백은 앱 수준 인증이 원래 없고(계약), `state`가 위조 호출을 막는다. 대시보드 설정 하나라 코드 변경이 없다.

## R3. SSE(최대 170초)가 Access·터널·nginx를 끊김 없이 지나나

- Decision: nginx `location /api/`에 `proxy_buffering off`, `proxy_read_timeout 200s`, `proxy_http_version 1.1`을 둔다. 백엔드의 기존 15초 ping과 `X-Accel-Buffering: no`를 유지한다.
- Rationale: Cloudflare 프록시의 100초 응답 대기 제한은 바이트가 흐르면 문제가 아니며, 15초 ping이 이를 보장한다(ADR-6). Access는 인증 후 요청을 그대로 프록시하는 계층이라 스트림 시간 상한을 따로 두지 않는 것으로 본다. nginx 기본 버퍼링은 SSE를 묶어 보내므로 끈다.
- **검증 방법**: `check_b8.py`의 SSE 장시간 시나리오(서비스 토큰 + `AGENT_MODE=fake`, `FAKE_DELAY_SECONDS=21`, 약 105초)를 운영 경로로 돌린다(T023·T025). 로컬은 `deploy/checks/check_g1.sh`가 웹 컨테이너 경유 SSE의 첫 이벤트 도착 시간을 잰다.
- **틀리면**: Access가 끊으면 PRD 엣지 케이스대로 부분 결과와 재시도 안내(기존 끊김 처리: 상세 재조회)가 동작하는지 확인하고, Cloudflare 지원 범위를 다시 조사한다.

## R4. 서비스 토큰 정책과 이메일 정책이 한 애플리케이션에 공존하나

- Decision: 같은 Access 애플리케이션에 정책 두 개를 둔다. "Allow: 이메일 허용 목록"과 "Service Auth: 서비스 토큰 `kbap-pm-agent-check`"다.
- Rationale: Access 애플리케이션은 정책 여러 개를 순서대로 평가하고, 서비스 토큰은 Service Auth 동작으로 허용하는 것이 표준 구성이다.
- **검증 방법** (T025): 토큰 헤더로 `/api/health`가 200 JSON, 토큰 없이 비 JSON(R1)이면 통과다.
- **틀리면**: 서비스 토큰 전용 앱을 같은 호스트명의 경로 `/api/health`로 따로 만든다. SSE 검사 경로도 그 앱에 포함한다.

## R5. 운영 검사 방식: 서비스 토큰 vs 서버 내부 실행 (ADR-23)

| 기준 | 서비스 토큰으로 바깥에서 | 홈서버 내부에서 `127.0.0.1` |
|---|---|---|
| 이번에 바뀐 경로(터널·Access·nginx 분기) 검증 | 전부 지난다 | 하나도 안 지난다 |
| "막혀야 할 것이 막히나"(US2) 검증 | 토큰 없는 호출로 같은 스크립트가 잰다 | 불가 |
| SSE 100초 이상 유지(R3) | 실제 경로로 잰다 | nginx만 |
| 비밀 관리 | 서비스 토큰 1쌍(Secrets, 만료 1년) | 없음 |
| 사람 손 설정 | 토큰 발급 + 정책 1개 | 없음 |

- Decision: 서비스 토큰 방식. 비밀 하나가 늘지만, 이 기능이 바꾸는 것을 검증하는 유일한 방법이다. 내부 헬스체크는 이미 `deploy.kbap-pm-agent.sh`에 있다.

## R6. 경로 분기 위치: nginx 프록시 vs 터널 경로 규칙 (ADR-22)

| 기준 | nginx `location /api/` | 터널 ingress `^/api` 규칙 |
|---|---|---|
| 로컬에서 같은 출처 재현(첫 모듈 조건) | `docker compose up` 그대로 | 로컬용 프록시가 따로 필요 |
| 리뷰·검사 가능 | 레포 안 설정 | 대시보드에만 있음 |
| 대시보드 손 설정 | 규칙 1개(호스트 → 웹) | 규칙 2개(순서 중요) |
| SSE 설정 | nginx 버퍼링 끔 필요 | 없음 |
| 홉 | 하나 더 | 없음 |

- Decision: nginx 프록시. 되돌리려면 `location /api/` 블록을 지우고 대시보드 규칙 두 개를 만든다.

## R7. 레포에 남은 운영 식별자 (CLAUDE.md "운영 정보 비노출")

- 발견(2026-10-15, 작업 트리 기준). 운영 호스트명으로 보이는 도메인과 홈서버 사용자 경로가 레포 파일에 있다.
  - 운영 도메인: `deploy/README.md`, `deploy/kbap-pm-agent.env.example`.
  - 홈서버 사용자 경로: `deploy/docker-compose.kbap-pm-agent.yml`·`deploy.kbap-pm-agent.sh`·`push-and-deploy.sh`의 기본값.
  - 예시 도메인: `backend/app/amplitude.py`·`backend/checks/examples.py`의 계약 예시 URL.
  - CTO 문서(계약, ADR)의 예시 도메인은 이번 변경에서 `pm-agent.example.com`으로 바꿨다.
- Decision: 작업 트리 파일은 이번 기능에서 정리한다(T010~T012, T014 검사, T027, T034). 서버 경로 기본값은 없애고 `COMPOSE_FILE`·`ENV_FILE` 환경변수 필수로 바꾼다. 예시는 `pm-agent.example.com`을 쓴다.
- **남는 위험**: 레포가 공개이고 git 히스토리에 값이 남아 있다. 히스토리 재작성(force push)은 협업 브랜치·PR을 깨므로 사용자가 정한다. 운영 도메인을 바꾸지 않는다면 Access가 막아 주는 것이 이번 기능의 통제다.
