# Implementation Plan: PM Agent 프로토타입

**Branch**: `main` (기능 디렉토리 `001-pm-agent-prototype`) | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-pm-agent-prototype/spec.md`

**결정 출처**: `_workspace/01_cto_tech-decisions.md`(ADR-1~21), `_workspace/01_cto_api-contract.md`(v1.1), `_workspace/01_cto_task-split.md`

## Summary

개발자 2명이 쓰는 채팅형 PM 에이전트다. 질문 하나에 에이전트가 택사노미·FE 코드·Amplitude를 여러 번 조회하고, 근거·제안·실행 단계·측정 방법 네 부분으로 구조화된 제안을 낸다. 사용자는 제안마다 채택·보류를 표시한다.

기술 접근:
- 백엔드는 FastAPI다. 에이전트는 두 단계다(ADR-21). 조사 단계는 공급자별 공식 SDK 도구 루프로 돌린다(Anthropic tool runner / OpenAI Agents SDK, 기본 Sonnet 5.5). 종합 단계는 도구 없이 1회 호출해 `AgentAnswer` 구조화 출력으로 제안을 쓴다(기본 Fable 5.1, ADR-1·20·21).
- 진행 상황은 POST 응답 SSE로 흘린다(ADR-6). 대화·도구 호출·제안·채택은 MySQL 6개 테이블에 저장한다(ADR-8).
- 코드 분석은 ripgrep 인덱스로 후보를 좁히고, 파일 단위 요약을 blob SHA로 캐시하며, 예산 상한을 코드로 강제한다(ADR-9).
- 프론트는 GitHub Pages의 React + Vite 정적 SPA다(ADR-5).
- `AGENT_MODE=fake` 하나로 외부 연동 세 가지를 모두 계약서 예시 값으로 대체한다(ADR-15).

## Technical Context

**Language/Version**: 백엔드 Python 3.12(uv), 프론트 TypeScript(React 19, Vite). 정확한 패치 버전은 구현자 위임.

**Primary Dependencies**:
- 백엔드: FastAPI, uvicorn(단일 워커), 공식 `anthropic` SDK(`[mcp]` extra, tool runner·구조화 출력·적응형 사고·프롬프트 캐싱·서버 측 폴백), `openai-agents`(OpenAI 런타임), MCP Python SDK(`OAuthClientProvider`). LangChain 계열은 쓰지 않는다(ADR-20). MySQL 드라이버는 위임. 컨테이너에 `git`, `ripgrep`.
- 프론트: React, Vite, 해시 라우터. 마크다운 렌더러 하나. UI 라이브러리는 위임.

**Storage**: MySQL 8.4. 스키마는 `backend/schema.sql`(`CREATE TABLE IF NOT EXISTS`)을 기동 시 적용한다(ADR-8). 클론한 저장소는 볼륨 `/data/repos`. 요약 캐시 매체(DB/파일)는 위임.

**Testing**: 헌법 원칙 V를 따른다. 모듈마다 `assert` 검사 스크립트 하나만 둔다. 백엔드는 `backend/checks/check_<module>.py`, 프론트는 `frontend/checks/check-<module>.ts`(Node 실행). 최소 내용은 "계약서 예시 JSON이 이 모듈의 타입·파서를 통과한다"다. 테스트 프레임워크·선작성 테스트는 없다.

**Target Platform**:
- 백엔드: 홈서버 Linux Docker(amd64·arm64), cloudflared 터널 뒤.
- 프론트: GitHub Pages `/kbap-pm-agent/`, 최신 데스크톱 브라우저.

**Project Type**: 웹 애플리케이션(`frontend/` + `backend/`).

**Performance Goals**: 첫 진행 표시(`tool_call` 이벤트)까지 5초 이내, 완성 제안까지 3분 이내(SC-004). 실행 상한은 `AGENT_TIMEOUT_SECONDS=170`, 모델 호출 턴 상한은 `AGENT_MAX_TURNS=10`(도구 호출은 세지 않음, ADR-2, ADR-16). 170초 중 종합 몫 `SYNTHESIS_TIMEOUT_SECONDS=50`, 조사 마감 120초(ADR-21).

**Constraints**:
- LLM 누적 비용 200달러 상한(`LLM_BUDGET_USD`, SC-006).
- Cloudflare 100초 응답 대기 제한 때문에 15초 ping SSE를 쓴다.
- 인증은 없고 선택적 공유 토큰만 둔다(ADR-7).
- Amplitude는 조회 전용이다.

**Scale/Scope**: 사용자 2명, 동시 실행 1~2개, FE 저장소 1개(kbap-fe 기준 화면 약 40개, 이벤트 호출 약 90곳), 엔드포인트 12개.

NEEDS CLARIFICATION: 없음. 열린 항목은 모두 ADR "가정"으로 확정했고, 검증 방법은 [research.md](./research.md)에 있다.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인. 두 번 모두 통과.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | `contracts/`는 `_workspace/01_cto_api-contract.md` v1.1의 무수정 분할본이고, `cat`+`diff`로 동일성을 확인한다(contracts/README.md). 계약은 언어 중립(JSON·SSE)이라 ADR-1을 뒤집어도 그대로다. 계약 변경은 CTO가 원본부터 고친다(tasks.md의 계약 변경 규칙). 프론트는 계약 타입을 `frontend/src/api.ts` 한 곳에 두고 `any`·캐스팅을 쓰지 않는다. Evidence는 판별 유니온으로 정의한다. |
| II. 작동하는 가장 짧은 코드 | 준수 | 외부 교체 지점은 함수 세 개 안의 `if` 분기이고, 인터페이스·가짜 클래스는 만들지 않는다(ADR-15). 직접 그래프 대신 기본 에이전트 루프를 쓴다(ADR-2). Alembic 없이 `schema.sql` 하나로 간다. 상태관리·UI 라이브러리는 넣지 않는다. 의도적 단순화(단일 워커, 페이지네이션 없음, 요약 캐시 매체)에는 `ponytail:` 주석을 단다. |
| III. 갈아끼울 수 있는 외부 연동 | 준수 (설계 중 보정, ADR-20 반영) | 1차 확인에서 위반을 찾았다. ADR-10은 fake 모드가 에이전트 실행만 대체해 GitHub·Amplitude가 실제로 호출됐다. ADR-15로 대체하고, 계약서 v1.1에 "시연 모드" 표를 추가했다. 2차 확인(analyze)에서 코드 요약 LLM 호출이 `code_tools.py`에 있던 것을 `agent.py`의 `summarize()`로 옮겨 LLM seam을 하나로 맞췄다. 모델은 `AGENT_MODEL`, `CODE_SUMMARY_MODEL` 문자열로 바꾸고, 접두사(`anthropic:`/`openai:`)가 런타임을 고른다(ADR-20). LLM 호출 지점은 여전히 `agent.py` 하나이며 두 런타임 파일은 그 안에서만 불린다. 외부 실패는 공통 에러 형식 `UPSTREAM_ERROR`나 실패한 `tool_result`로 응답하고 서버는 죽지 않는다(계약서 05-messages 비고). |
| IV. 비용 상한 | 준수 | ripgrep 인덱스·`search_code`(30건)·`read_code`(200줄)로 좁힌 뒤에만 모델에 보낸다. 파일 통째 전송 도구는 없다. 화면 요약은 blob SHA 키 캐시다. `llm_usage` 테이블에 모든 호출을 기록한다. 누적이 `LLM_BUDGET_USD` 이상이면 `BUDGET_EXCEEDED`로 거절한다(ADR-9). |
| V. 모듈마다 검사 하나 | 준수 | B1~B8, F1~F6 모듈마다 검사 스크립트 태스크 하나와 QA 교차 검증 태스크 하나를 둔다(tasks.md). 테스트 선작성 태스크는 없다. |

기술 제약 절과의 대조:
- **일치(헌법 v1.1.0, d3302ae)**: 기술 제약의 백엔드 스택이 ADR-20(공급자 공식 SDK, LangChain 미사용)과 맞는다.
- 레포 구조, 스택, SSE, 해시 라우팅, 조회 전용 Amplitude, 비목표 제외가 모두 ADR과 일치한다.
- 공유 접근 토큰은 헌법이 "선택 장치"로 명시한 그대로다.

## Project Structure

### Documentation (this feature)

```text
specs/001-pm-agent-prototype/
├── spec.md
├── plan.md              # 이 파일
├── research.md          # 가정 ADR 검증 방법
├── data-model.md        # ADR-8 스키마 + 계약 객체 매핑
├── quickstart.md        # 실행·시연 안내
├── contracts/           # 계약서 v1.1 무수정 분할본 (README.md에 동기화 확인 명령)
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks 산출물
```

### Source Code (repository root)

```text
docker-compose.yml               # 로컬: backend + mysql:8.4 (ADR-11)
.github/workflows/pages.yml      # frontend → GitHub Pages
deploy/
├── docker-compose.kbap-pm-agent.yml   # 홈서버: 이미지만, monitor-net, 127.0.0.1:8001:8000
├── deploy.kbap-pm-agent.sh            # pull → up → /api/health 확인
└── kbap-pm-agent.env.example
backend/
├── pyproject.toml, uv.lock, Dockerfile, schema.sql
├── app/
│   ├── main.py          # FastAPI 앱, CORS, 토큰 검사, 공통 에러 핸들러, 기동 시 schema.sql
│   ├── db.py            # 연결과 쿼리 함수
│   ├── conversations.py # 대화·메시지·제안 라우트
│   ├── settings.py      # 설정·저장소·택사노미 라우트
│   ├── repo.py          # seam: 클론·pull·rg 인덱스 (fake 분기)
│   ├── code_tools.py    # find_event_calls, search_code, get_screen_summary, read_code + 요약 캐시
│   ├── amplitude.py     # seam: MCP OAuth·도구 공급 (fake 분기)
│   ├── agent.py         # seam: 모든 LLM 호출 — run_agent()(조사 → 종합 오케스트레이션)/summarize(), 접두사로 런타임 선택, 공통 도구 래퍼·상한·사용량 (fake 분기)
│   ├── agent_anthropic.py  # anthropic tool runner 런타임 (agent.py에서만 import)
│   ├── agent_openai.py     # openai-agents 런타임 (agent.py에서만 import)
│   ├── budget.py        # llm_usage 기록·상한 검사
│   └── schemas.py       # 계약 객체 Pydantic 모델 (AgentAnswer 포함)
└── checks/              # 모듈별 assert 스크립트 check_b1.py … check_b8.py
frontend/
├── package.json, vite.config.ts (base: '/kbap-pm-agent/'), index.html
├── src/
│   ├── api.ts           # 계약 타입 + fetch + SSE 파서 (계약 경계는 이 파일 하나)
│   ├── App.tsx          # 해시 라우팅, 헬스 표시
│   ├── ConversationList.tsx
│   ├── Chat.tsx
│   ├── ProposalCard.tsx
│   └── SettingsPage.tsx
└── checks/              # 모듈별 assert 스크립트 check-f1.ts … check-f6.ts
```

**Structure Decision**: 웹 애플리케이션 2분할(ADR-11, 헌법 기술 제약). `backend/app/` 파일 구성은 출발점이고, 파일 추가·병합은 구현자 판단이다. 다만 아래 두 가지는 고정이다.
- 세 seam(`repo.py`=GitHub, `amplitude.py`=Amplitude MCP, `agent.py`=모든 LLM 호출)만 외부를 호출한다. 코드 요약도 `agent.py`의 `summarize()`를 거친다(원칙 III).
- 프론트 계약 타입은 `api.ts` 한 곳에 둔다(원칙 I).

## Complexity Tracking

위반은 없다. 거버넌스가 기록을 요구하는 복잡도 항목만 적는다.

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 테이블 6개 (`conversations`, `messages`, `tool_calls`, `proposals`, `llm_usage`, `app_settings`) | FR-006 저장 대상 4종, 원칙 IV 사용량 기록, 설정·OAuth 토큰 영속화 | 메시지 JSON 한 컬럼에 몰면 채택 건수(SC-001)와 비용 합계(SC-006)를 SQL로 못 센다 |
| MCP SDK OAuth (`OAuthClientProvider`) | Amplitude 공식 MCP가 OAuth만 받는다 | 직접 OAuth 2.1 + 동적 클라이언트 등록 구현은 수백 줄이다 |
| 조사·종합 2단계(모델 호출 +1회/질문) | 사용자 결정(ADR-21): 판단·작성은 가장 강한 모델이 한 번, 도구 루프는 저렴한 모델 | 단일 루프를 Fable로 돌리면 턴마다 2.5배 단가, 3단계 이상은 근거 없이 호출·맥락 손실 |
| 런타임 2개(`agent_anthropic.py`, `agent_openai.py`)와 새 의존성 `openai-agents` | 사용자 지시: 공식 SDK 사용, OpenAI로 갈아끼울 수 있어야 함(ADR-20, FR-014) | 한 런타임으로 두 공급자를 돌리면 Claude 네이티브 기능을 잃는다. 공통 인터페이스 클래스 대신 dict 분기 |
| 컨테이너에 `ripgrep` | 원칙 IV의 무료 선필터 | Python 정규식 순회는 느리고 `.gitignore`를 존중하지 않는다 |
