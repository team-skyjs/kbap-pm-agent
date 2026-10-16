# Implementation Plan: Amplitude 서버 고정 인증

**Branch**: `feat/amplitude-rest` (기능 디렉토리 `006-amplitude-rest`) | **Date**: 2026-10-17 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/006-amplitude-rest/spec.md`, `docs/prd/PRD-amplitude-server-auth.md`, `_workspace/00_input.md` 006 절

**결정 출처**: `_workspace/01_cto_tech-decisions.md` ADR-34(REST 프로젝트 키, ADR-3 대체), ADR-35(도구 두 개의 인자·결과), ADR-36(사전 점검·건너뛰기·상태 기록). 계약 v1.5, 내부 도구 형식 [contracts/amplitude-tools.md](./contracts/amplitude-tools.md).

## Summary

Amplitude MCP(OAuth, 갱신 토큰 없음)를 걷어내고 Dashboard REST·Taxonomy API를 프로젝트 키 Basic 인증으로 부른다.
- **도구**: `amplitude.py`가 `amplitude_query`(세그멘테이션·퍼널·리텐션)와 `amplitude_context`(이벤트·속성 + 업로드 택사노미)를 평범한 Python 함수로 제공한다. 두 런타임은 코드 도구처럼 같은 공통 래퍼로 감싸서 쓴다. MCP 세션 코드는 런타임에서 사라진다.
- **사전 점검**: 메시지 전송은 예산 검사 다음에 `amplitude.preflight()`로 이벤트 목록을 1회 조회한다(15분 캐시). 실패하면 503 `AMPLITUDE_UNAVAILABLE`로 거절하고, `skipAmplitude: true`면 Amplitude 없이 실행한다.
- **상태 기록**: 실행 상태는 `messages.amplitude_status`에 남는다.
- **설정 화면**: 설정의 Amplitude는 키 존재 여부만 알리고, OAuth 라우트·저장 토큰은 지운다.

## Technical Context

**Language/Version**: 백엔드 Python 3.12·FastAPI, 프론트 TypeScript·React(003 재설계 위).

**Primary Dependencies**: 추가 없음. 이미 쓰는 `httpx`만 쓴다. `mcp`, `anthropic[mcp]` extra, openai-agents의 MCP 사용은 코드에서 사라진다. 의존성 목록에서 빼는 것은 사용처가 0이 되는 것을 확인한 뒤 한다(T008).

**Storage**: `messages.amplitude_status ENUM('used','unavailable','skipped') NULL` 컬럼 추가(기동 시 조건부 `ALTER`, ADR-29 패턴). `app_settings`의 `amplitude`·`amplitude_oauth` 행 삭제(멱등).

**Testing**: 헌법 원칙 V. 모듈마다 검사 하나다.
- A1 백엔드 REST 도구·사전 점검·상태는 `backend/checks/check_b12.py`가 맡는다(신규). `httpx.MockTransport`로 Amplitude 응답을 주입한다.
- 기존 `check_b7.py`(MCP 전용)는 폐기한다. 그 안의 "Amplitude 실패에도 final로 끝남" 항목은 b12로 옮긴다.
- A2 프론트 설정·거절 안내는 frontend-dev의 `check-f*`와 Playwright가 맡는다.
- 실제 키 확인은 사람이 1회 한다(미검증으로 표시).

**Target Platform**: 기존과 같다.

**Project Type**: 웹 애플리케이션(백엔드 중심, 프론트는 설정 화면과 거절 안내).

**Performance Goals**: 사전 점검은 캐시 적중 시 0회 호출, 미스 시 1회다. Dashboard REST 한도(동시 5, 5분 1,000, 시간 108,000)는 사용자 2명 규모에서 여유가 크다(PRD 6.3).

**Constraints**:
- 키 값은 env만(헌법 원칙 III). 응답·로그·`tool_calls.input`에 키를 쓰지 않는다.
- 조회 전용 허용 경로 목록(FR-003)을 지킨다.
- 모델명을 코드에 박지 않는다.
- 운영 정보 비노출과 코드 주석 규칙을 지킨다.

**Scale/Scope**: 백엔드 파일 약 8개, 프론트 파일 3~4개, 엔드포인트 2개 삭제, 테이블 컬럼 1개.

NEEDS CLARIFICATION: 없음.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인. 헌법 v1.3.0.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | 계약 v1.5는 엔드포인트 2개를 삭제하고, 설정 `amplitude` shape를 축소하고, 메시지 요청에 선택 필드와 에러 코드를 하나씩 추가했다. 원본과 분할본 diff 0이다(분할본 `08-amplitude.md` 삭제). 프론트가 맞춰야 하는 shape 변경은 설정 `amplitude`와 `connectAmplitude` 제거이며 frontend-dev 태스크로 둔다. 모델용 도구 형식은 API가 아니므로 `contracts/amplitude-tools.md`에 따로 둔다(003·005 선례). |
| II. 작동하는 가장 짧은 코드 | 준수 | MCP와 REST를 공존시키지 않는다(PRD 6.2). 도구는 평범한 함수 두 개이고 기존 공통 래퍼를 그대로 쓴다. 압축표는 형제 레포의 검증된 구조를 옮겨 다듬는다(새로 설계하지 않음). 캐시는 프로세스 메모리 dict이고 `ponytail:` 주석으로 한계를 적는다. |
| III. 갈아끼울 수 있는 외부 연동 | 준수 | Amplitude 호출은 `amplitude.py` 한 파일에서만 한다. 키·주소는 env 세 개다. 시연 모드는 Amplitude를 부르지 않고 사전 점검을 통과시킨다. 검사는 `httpx.MockTransport`로 가짜 응답을 준다. 외부 실패는 계약 에러(`AMPLITUDE_UNAVAILABLE`)나 도구 실패로 답하고 서버를 죽이지 않는다. |
| IV. 비용 상한 | 준수 (강화) | 사전 점검이 모델 호출 전에 막아 Amplitude 없는 헛실행 비용이 사라진다. 사전 점검 자체는 LLM을 부르지 않는다. 결과 크기 상한(`clip`, 31행)으로 입력 토큰을 묶는다. |
| V. 모듈마다 검사 하나 | 준수 | A1(b12), A2(프론트 검사) 모듈마다 검사와 QA가 있다. 실제 키 확인은 수동 태스크로 분리했다. |

기술 제약 절과의 대조: 헌법 v1.3.0 기술 제약은 "Amplitude: 공식 원격 MCP(조회 전용)"이다. 이번 결정(REST 조회 전용)과 문구가 어긋난다. "조회 전용"은 유지되고 경로만 바뀐다. 거버넌스상 기술 제약 문구 개정이 필요하며 team-lead에 개정안을 전달한다(PATCH: "공식 원격 MCP" → "Dashboard REST·Taxonomy API 프로젝트 키").

## Project Structure

### Documentation (this feature)

```text
specs/006-amplitude-rest/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
├── contracts/README.md, contracts/amplitude-tools.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/
├── app/amplitude.py        # 전면 교체: env 키·Basic 인증 GET(허용 경로·15분 캐시), amplitude_query·amplitude_context, preflight(), 압축표, 오류 분류
├── app/agent.py            # 도구 목록에 Amplitude 두 도구(키 있고 건너뛰지 않을 때), 시스템 프롬프트 규칙 8 교체·Amplitude 상태 문구, 실행 상태 기록
├── app/agent_anthropic.py  # MCP 세션·_mcp_call·허용 목록 불일치 분기 삭제
├── app/agent_openai.py     # MCPServerStreamableHttp·mcp 이벤트 처리 삭제
├── app/conversations.py    # 메시지 POST: skipAmplitude, budget.check() 다음 preflight(), 503
├── app/settings.py         # amplitude_state() → {"status": "configured"|"missing"}
├── app/main.py             # amplitude 라우터·OPEN_PATHS의 콜백 삭제
├── app/db.py·schema.sql    # messages.amplitude_status, app_settings OAuth 행 삭제(멱등)
├── checks/check_b12.py     # 신규, checks/check_b7.py 삭제
└── pyproject.toml·uv.lock  # MCP 관련 의존성 정리(사용처 0 확인 후)
frontend/
├── src/api.ts              # Settings.amplitude 타입, connectAmplitude 삭제, sendMessage에 skipAmplitude
├── src/SettingsPage.tsx    # 연결 버튼·폴링 삭제, 상태 라벨 두 개
├── src/Chat.tsx            # AMPLITUDE_UNAVAILABLE 안내 + "Amplitude 없이 진행"(입력값 보존)
└── checks/…                # 설정·거절 안내 검사(번호는 frontend-dev)
.env.example, deploy/kbap-pm-agent.env.example, .github/workflows/deploy-backend.yml, deploy/README.md
                            # AMPLITUDE_API_KEY·AMPLITUDE_SECRET_KEY(Secrets)·AMPLITUDE_REST_BASE(Variables), MCP 변수 삭제
```

**Structure Decision**: Amplitude는 지금처럼 `amplitude.py` 한 파일이 외부 seam이다. 런타임은 Amplitude를 따로 알 필요가 없어진다(코드 도구와 같은 경로). 그래서 두 런타임 파일은 줄어들기만 한다.

## Complexity Tracking

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| `messages`에 컬럼 1개(마이그레이션) | PRD 핵심 결과 2의 측정 | 새 테이블은 실행과 1:1이라 과하다. `tool_calls`에서 추론하면 "건너뜀"을 알 수 없다 |
| 새 에러 코드 1개 | 사전 점검 거절을 프론트가 구분해 "없이 진행"을 보여야 한다 | `UPSTREAM_ERROR` 재사용은 다른 실패와 섞여 버튼을 띄울 근거가 없다 |
