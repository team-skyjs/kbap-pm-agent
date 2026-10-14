# Implementation Plan: 질문 마법사

**Branch**: `feat/question-wizard` (기능 디렉토리 `004-question-wizard`) | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/004-question-wizard/spec.md`, `docs/prd/PRD-question-wizard.md`, `_workspace/00_input_004.md`

**결정 출처**: `_workspace/01_cto_tech-decisions.md` ADR-28(다듬기 모델 선택), ADR-29(사용량 용도 ENUM 마이그레이션), ADR-30(다듬기 프롬프트 규칙과 입력). 계약 `_workspace/01_cto_api-contract.md` v1.3(엔드포인트 2개 추가).

## Summary

입력창 옆 "질문 다듬기" 버튼이 `POST /api/questions/refine`를 부른다.
- **다듬기 호출**: 서버는 택사노미 이벤트 이름과 대화의 최근 메시지(사용자·에이전트 각 2개, 앞 500자)를 붙여 다듬기 모델을 한 번, 도구 없이 구조화 출력으로 호출한다. `{refinementId, refined, summary}`를 돌려주고 `question_refinements`에 행을 만든다.
- **비교 카드**: 원문과 개선안을 나란히 보이고 네 동작을 둔다. 카드가 닫힐 때 프론트가 `POST /api/questions/refine/{id}/choice`로 선택을 한 번 기록한다. 기록 실패는 전송을 막지 않는다.
- **사용량**: 비용은 `llm_usage`에 용도 `refine`으로 남는다. ENUM 값 추가는 기동 시 멱등 마이그레이션이다.
- **모델**: `REFINE_MODEL`(없으면 `CODE_SUMMARY_MODEL`)이고, 샘플 10건 Haiku 5.5 대 Sonnet 5.5 비교로 확정한다.

## Technical Context

**Language/Version**: 백엔드 Python 3.12(FastAPI, 공식 SDK 런타임 ADR-20), 프론트 TypeScript·React 19·Vite(003 재설계 위).

**Primary Dependencies**: 추가 없음. Anthropic `messages.parse`(구조화 출력)와 openai-agents `Agent(output_type=...)` 단발 실행은 기존 런타임 안에서 쓴다.

**Storage**: MySQL에 새 테이블 `question_refinements`, `llm_usage.purpose` ENUM에 `refine` 추가(data-model.md, ADR-29).

**Testing**: 헌법 원칙 V. 모듈마다 검사 하나다.
- 백엔드: `backend/checks/check_b10.py`.
- 프론트 계약 파싱: `frontend/checks/check-f9.ts`(`npm run check`에 합류).
- 프론트 화면: `frontend/checks/ui/us12.spec.ts`(Playwright, 003 검사 체계).
- 모델 비교는 검사가 아니라 측정이다. `backend/checks/compare_refine.py`가 비교표를 만들고 QA가 채점한다.

**Target Platform**: 기존과 같다.

**Project Type**: 웹 애플리케이션(백엔드 엔드포인트 2개 + 프론트 버튼·카드).

**Performance Goals**: SC-001 버튼 → 카드 보통 5초 이내(effort `low`, 출력 짧음). SC-004 다듬기 1회 비용 ≤ 질문 1회의 1%다(research R2 추정 Haiku 약 $0.0004, Sonnet 약 $0.008).

**Constraints**:
- LLM 호출은 `agent.py` seam으로만 한다(헌법 원칙 III). `refine()`을 추가하고 런타임 두 파일에 같은 이름의 구조화 단발 함수를 둔다.
- 예산 검사는 호출 전에 한다(원칙 IV).
- 시연 모드는 모델을 부르지 않는다(원칙 III, 계약 시연 모드 표).
- 기존 엔드포인트 shape는 그대로다(FR-012).
- 프론트 파일 소유(003 규칙)를 따른다. `Chat.tsx`·`style.css` 표현은 designer, `api.ts`·상태 훅·검사는 dev다.

**Scale/Scope**: 사용자 2명, 다듬기 하루 수십 회 이하.

NEEDS CLARIFICATION: 없음. 모델 확정(US4)은 측정 태스크이고, 그 전에는 기본값(`CODE_SUMMARY_MODEL`)으로 동작한다.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인. 헌법 v1.3.0.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | 계약 v1.3에 엔드포인트 두 개와 에러 코드 하나를 추가했다. 기존 shape는 그대로다. 원본과 분할본(`specs/001-pm-agent-prototype/contracts/`, 새 파일 `08b-questions.md`) diff 0이다. 분할본은 제품당 하나를 유지하고 004에는 사본 대신 안내 파일을 둔다(002·003 선례, 사본이 늘면 동기화 대상이 는다). 프론트 타입은 `api.ts` 한 곳, `any`·캐스팅은 쓰지 않는다. |
| II. 작동하는 가장 짧은 코드 | 준수 | 새 의존성은 없다. 선택 기록은 별도 엔드포인트 하나(메시지 전송 확장보다 짧고 취소도 기록, research R3)다. 마이그레이션 프레임워크 없이 기동 시 조건부 `ALTER` 한 문장(ADR-29)이다. |
| III. 갈아끼울 수 있는 외부 연동 | 준수 | 다듬기 LLM 호출은 `agent.py`의 `refine()` 하나를 거친다. 모델은 `REFINE_MODEL` 문자열(접두사로 런타임 선택)이고 비면 `CODE_SUMMARY_MODEL`이다. 시연 모드는 계약 예시를 돌려준다. 모델 실패는 계약 에러 `UPSTREAM_ERROR`로 응답한다. |
| IV. 비용 상한 | 준수 | 호출 전 `budget.check()`, 호출 뒤 `budget.record("refine", ...)`, 예산 합계에 포함된다. 입력은 이벤트 이름만(정의 제외)과 메시지 4개 × 500자로 묶어 짧다. |
| V. 모듈마다 검사 하나 | 준수 | 모듈 셋(백엔드 다듬기, 프론트 계약·상태, 프론트 화면)마다 검사 하나와 QA 하나다. 모델 비교는 PRD가 요구한 측정이며 테스트 선작성이 아니다. |

## Project Structure

### Documentation (this feature)

```text
specs/004-question-wizard/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
├── contracts/README.md   # 계약 정본 위치와 v1.3 추가 절 안내 (사본 없음)
└── checklists/requirements.md
```

### Source Code (repository root)

```text
backend/
├── schema.sql                 # question_refinements 테이블, llm_usage.purpose에 'refine' (새 DB용)
├── app/db.py                  # init(): schema.sql 뒤 멱등 마이그레이션(purpose ENUM에 refine 없으면 ALTER)
├── app/refine.py              # 신규: 라우터 2개, 입력 조립(택사노미 이름·최근 메시지), 기록, REFINE_PROMPT
├── app/agent.py               # refine(prompt) seam: 모델 선택·fake 분기·budget.record("refine")
├── app/agent_anthropic.py     # refine(): messages.parse(output_format=RefineResult), effort low
├── app/agent_openai.py        # refine(): Agent(output_type=RefineResult) 단발
├── app/schemas.py             # RefineResult(refined 1~4000·두 문장 이내, summary 1~300)
├── app/main.py                # 라우터 등록, 기동 모델 검사에 REFINE_MODEL 포함
├── checks/check_b10.py        # 신규
└── checks/compare_refine.py   # 신규: 샘플 10건 × 두 모델 비교표 생성(실제 키)
frontend/
├── src/api.ts                 # refineQuestion(), recordRefineChoice() + 타입
├── src/refine.ts              # 신규: 다듬기 상태(대기·진행·카드·오류)와 선택 처리 훅
├── src/RefineCard.tsx         # 신규 [designer]: 비교 카드 표현
├── src/Chat.tsx·style.css     # [designer]: 버튼 배치·상태 표현, 훅 연결
├── checks/check-f9.ts         # 신규
└── checks/ui/us12.spec.ts, fixtures.ts   # 다듬기 고정 응답·시나리오
.env.example, deploy/kbap-pm-agent.env.example   # REFINE_MODEL (비우면 CODE_SUMMARY_MODEL)
_workspace/06_refine_model_comparison.md         # 비교표와 결정
```

**Structure Decision**: 다듬기 백엔드는 기존 라우터 모듈처럼 파일 하나(`refine.py`)에 모은다. LLM 호출만 `agent.py` seam으로 넘긴다. 프론트는 상태·API를 dev가 `refine.ts` 훅으로, 표현을 designer가 `RefineCard.tsx`와 `Chat.tsx`로 나눠 같은 파일을 둘이 동시에 고치지 않게 한다.

## Complexity Tracking

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 새 테이블 `question_refinements` | PRD의 유일한 측정(채택 비율)과 다듬기 규칙 개선 근거 | `llm_usage`에 원문·개선안을 넣으면 사용량 테이블의 의미가 섞이고 선택 결과를 담을 자리가 없다 |
| 엔드포인트 2개 | 다듬기와 선택 기록 시점이 다르다(카드가 뜬 뒤 사용자가 고름) | 메시지 전송에 선택을 실으면 취소(전송 없음)를 기록할 수 없다 |
