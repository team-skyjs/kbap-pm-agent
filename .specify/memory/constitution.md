<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0   (개정 2026-10-15)
Bump rationale (MINOR): "기술 제약"의 프론트 배포·FE↔BE 연결 줄을 접근 제한 설계(ADR-22·23)에 맞게 실질 변경.
  사유: 프론트를 홈서버 nginx 컨테이너로 옮기고 같은 호스트명·같은 출처를 Cloudflare Access 뒤에 둔다.
Modified principles: 없음 (원칙 I에 계약 분할본 위치 한 줄 명확화).
Modified sections: 기술 제약 — 프론트 줄, FE↔BE 줄, 비목표 줄.
Templates reviewed: ✅ plan/spec/tasks 템플릿 — 변경 불필요.
Follow-up: specs/002-access-gate/plan.md Constitution Check의 "선행 조건" 해소.
-->

# K-Bap PM Agent Constitution

## Core Principles

### I. 계약이 경계다

프론트와 백엔드가 만나는 지점은 API 계약서 하나다(`_workspace/01_cto_api-contract.md`,
Spec Kit 단계에서는 `specs/<feature>/contracts/`로 복제·동기화한다. 분할본은 제품당 하나이며 현재는
`specs/001-pm-agent-prototype/contracts/`다. 다른 기능 디렉토리는 정본을 가리키는 안내만 둔다).

- 응답 JSON의 필드명·중첩·감싸기 구조·에러 형식은 계약서와 글자 단위로 일치해야 한다(MUST).
- 계약은 언어 중립이다. 백엔드 언어를 바꿔도 계약서·프론트·DB 스키마는 그대로여야 한다(MUST).
- 계약 변경은 구현자가 혼자 하지 않는다. CTO 역할이 심사해 계약서를 먼저 고치고, 양쪽 구현자와
  QA에게 통지한 뒤 코드가 따라간다(MUST).
- 타입 캐스팅·`any`·단독 제네릭으로 계약 불일치를 컴파일러에서 숨기는 것은 금지한다(MUST NOT).

근거: 두 사람이 따로 쓴 코드가 처음 만나는 곳에서 거의 모든 결함이 난다. 기준이 하나면 QA가
세 개(계약·생산자·소비자)를 동시에 읽어 대조할 수 있다.

### II. 작동하는 가장 짧은 코드

이 제품은 개발자 2명의 프로토타입이다. 없는 코드가 가장 좋은 코드다.

- 두 번째 사용처가 생기기 전에는 추상화·인터페이스·팩토리·설정 계층을 만들지 않는다(MUST NOT).
- "나중을 위한" 스캐폴딩, 미사용 옵션, 한 값만 갖는 설정은 만들지 않는다(MUST NOT).
- 의도적 단순화에는 `ponytail:` 주석으로 한계와 업그레이드 경로를 적는다(MUST).
  예: `# ponytail: 파일 캐시, 동시 요청 늘면 DB로`
- UI는 읽을 수 있고 눌리면 된다. 디자인 시스템·상태관리 라이브러리는 필요가 증명된 뒤에 넣는다.

근거: PRD가 "세련됨보다 동작"을 명시했다. 작은 팀에서 추상화는 속도가 아니라 디버깅 비용이다.

### III. 갈아끼울 수 있는 외부 연동

LLM, Amplitude MCP, GitHub 저장소 접근은 각각 한 지점(seam)을 통해서만 호출한다.

- 실행 모드 설정 하나(`AGENT_MODE=fake`)로 외부 연동 전부를 계약서 예시 값으로 대체할 수 있어야
  한다(MUST). 프론트 연동과 QA는 외부 키 없이 완료 가능해야 한다.
- 추론 모델과 코드 분석 모델은 환경변수 문자열 하나로 교체 가능해야 한다(MUST). 특정 모델명을
  코드에 박지 않는다.
- 외부 서비스 실패가 서버를 죽이면 안 된다(MUST NOT). 계약서의 공통 에러 형식으로 응답한다.

근거: 외부 서비스는 느리고, 유료이고, 자주 바뀐다. 가짜로 먼저 계약을 맞추면 QA가 빨라지고
비용이 보존된다.

### IV. 비용 상한

코드 분석에 쓸 Claude API 예산은 200달러다. 비용 통제는 문서가 아니라 코드로 한다.

- 모델을 부르기 전에 무료 수단(grep, 인덱스, 캐시)으로 후보를 좁힌다(MUST). 코드베이스 전체를
  한 요청에 보내는 코드는 금지한다(MUST NOT).
- 파일 단위 요약은 캐시하고, 저장소 커밋이 바뀐 파일만 다시 분석한다(MUST).
- 예산 상한을 코드에 두고, 넘으면 모델 호출을 거절하며 계약서 에러 형식으로 알린다(MUST).
- 모든 모델 호출은 토큰 사용량을 기록한다(MUST).

근거: 예산이 바닥나면 제품이 멈춘다. 비용은 사후 청구서가 아니라 설계 제약이다.

### V. 모듈마다 검사 하나, 테스트는 요청 기반

- 모듈(QA가 따로 검증하는 단위)마다 실행 가능한 검사 하나를 남긴다(MUST). 프레임워크 없이
  `assert` 스크립트면 충분하다. 최소 내용: "계약서 예시 JSON이 이 모듈의 타입·파서를 통과한다".
- 그 외 단위 테스트·테스트 선작성은 사용자가 요청하거나 스펙이 명시할 때만 작성한다(SHOULD NOT
  by default). kbap 본체 헌법 v8 원칙 I과 같은 입장이다.
- QA는 전체 완성 후가 아니라 모듈 완료 직후 경계면을 검증한다(MUST). 결함은 재현 가능하게
  (파일:라인, 계약서 인용, 실제값) 보고한다.

근거: 프로토타입에서 테스트 스위트는 속도를 잡아먹는다. 그러나 검사가 하나도 없는 모듈은 QA가
경계면을 확인할 수단이 없다.

## 기술 제약

PRD 5·7.3·8절과 CTO ADR(`_workspace/01_cto_tech-decisions.md`)에서 확정된 것.

- 레포 구조: 이 저장소 하나에 `frontend/`와 `backend/`를 둔다.
- 백엔드: Python 3.12, FastAPI, MySQL. 패키지는 uv. LLM 호출은 공급자 공식 SDK로 한다(Claude는 `anthropic` SDK의
  tool runner, GPT는 `openai-agents`). LangChain 계열은 쓰지 않는다. 공급자 선택은 모델 문자열 접두사(`anthropic:`/`openai:`)로 한다(ADR-20). 홈서버 Docker 컨테이너로 운영.
  로컬은 `docker compose up` 한 번으로 백엔드+MySQL이 떠야 한다.
- 프론트: TypeScript, React, Vite 정적 SPA. 홈서버 nginx 정적 컨테이너로 배포하고 백엔드와 같은 호스트명·같은
  출처에서 제공한다. 해시 라우팅을 쓰고 API는 상대 경로 `/api`로 호출한다. 빌드 시 백엔드 주소 환경변수는 없다.
- FE↔BE: 같은 호스트명 아래 Cloudflare Access 뒤의 터널. 웹 컨테이너 nginx가 `/api`를 백엔드로 프록시한다(CORS
  없음). 에이전트 응답은 POST 응답 자체를 SSE 스트림으로 보낸다.
- Amplitude: 공식 원격 MCP(조회 전용). 이벤트 전송·택사노미 자동 수정은 하지 않는다.
- 비목표(v1): 앱 안의 사용자 인증·권한·멀티테넌시(접근 제한은 인프라인 Cloudflare Access가 한다), 백엔드 코드 분석,
  코드 자동 수정·PR 생성,
  능동 모드(먼저 제안). 공유 접근 토큰(ADR-7)은 선택 장치이며 비워 두면 꺼진다.

## 개발 워크플로우

- 문서 흐름: PRD → 헌법 → `specs/<feature>/spec.md` → `plan.md` + `contracts/` + `data-model.md`
  → `tasks.md` → 구현. Spec Kit 스킬(`speckit-*`)로 생성하고, CTO ADR은 plan.md의 입력이다.
- 역할: `cto`(결정·계약 심사), `backend-dev`, `frontend-dev`(계약서대로 구현),
  `qa-integrator`(모듈마다 경계면 교차 검증). 조율은 `kbap-build-orchestrator` 스킬.
- 모듈 완료 → QA 알림 → 결함은 담당자에게 직접, 경계면 결함은 양쪽 모두에게.
- `_workspace/`의 중간 산출물은 삭제하지 않는다. 재실행·감사 추적에 쓴다.
- 커밋은 모듈 단위로 한다. 커밋 메시지는 `feat(backend): ...`, `feat(frontend): ...`,
  `fix(contract): ...` 형식을 따른다.

## Governance

- 이 헌법은 다른 관행·스킬·에이전트 정의보다 우선한다. 충돌하면 헌법을 따르거나 헌법을 개정한다.
- 개정은 이 파일을 수정하고 버전을 올린다. MAJOR: 원칙 삭제·비호환 재정의, MINOR: 원칙·절 추가
  또는 실질 확장, PATCH: 문구·오타. 개정 사유는 상단 Sync Impact Report에 적고, 커밋 전 제거한다.
- 기술 결정은 ADR로 남긴다(`_workspace/01_cto_tech-decisions.md`). ADR이 헌법 "기술 제약"과
  어긋나면 헌법을 먼저 개정한다.
- plan.md의 Constitution Check는 원칙 I~V 각각에 대해 준수 여부와, 위반 시 정당화를 적어야 한다.
- 복잡도(추상화, 새 의존성, 새 테이블)는 plan.md의 Complexity Tracking에 이유를 적어야 한다.

**Version**: 1.2.0 | **Ratified**: 2026-10-15 | **Last Amended**: 2026-10-15
