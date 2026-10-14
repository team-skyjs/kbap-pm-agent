---
name: kbap-build-orchestrator
description: "K-Bap PM Agent(docs/prd/PRD-kbap-pm-agent.md) 구현 하네스의 오케스트레이터. CTO가 기술 결정과 API 계약을 내리고, frontend-dev·backend-dev가 frontend/·backend/를 병렬 구현하고, frontend-designer가 채팅 UI/UX(레이아웃·사이드바·메시지·반응형·접근성·디자인 시스템)를 설계·구현하며, qa-integrator가 모듈마다 경계면을 검증하는 팀을 조율한다. 트리거: 'PRD대로 구현', '프로토타입 만들어', '하네스 실행', '빌드 시작', '개발 시작', 'frontend/backend 구현', 'UI 개선', '화면 다듬기', '채팅 UI 설계', '디자인 시스템 적용', 'UI 리뷰'. 후속 작업: '다시 실행', '재실행', '백엔드만 다시', '프론트만 다시', 'QA만 다시', '계약 바꿔서 다시', '이어서 구현', '이전 결과 기반으로 개선', '업데이트', '수정', '보완' 요청 시에도 반드시 이 스킬을 사용. PRD 자체를 쓰거나 고치는 요청에는 쓰지 않는다 (그건 create-prd)."
---

# K-Bap Build Orchestrator

PRD를 동작하는 프로토타입으로 바꾸는 팀을 조율한다. 리더(이 세션)는 팀을 만들고, 진행을 보고, 막힌 곳을 뚫고, 결과를 종합한다. 코드는 쓰지 않는다.

## 실행 모드: 하이브리드

| Phase | 모드 | 이유 |
|-------|------|------|
| Phase 2 (기술 결정) | 서브 에이전트 (`cto` 단독) | 결정은 한 사람이 내려야 일관된다. 통신 상대가 아직 없다 |
| Phase 3 (구현 + 점진 QA) | 에이전트 팀 (`frontend-dev`, `backend-dev`, `qa-integrator`, 대기 중인 `cto`, UI 작업이 있으면 `frontend-designer`) | FE↔BE 계약 질의, QA→개발자 결함 보고, 개발자→CTO 계약 변경 요청이 실시간으로 오간다 |
| Phase 4 (최종 QA) | 팀 유지, `qa-integrator`만 작업 | 수정 요청이 개발자에게 바로 가야 한다 |

**도구 매핑:** 이 환경에 TeamCreate/TaskCreate가 있으면 그것을 쓴다. 없으면 `Agent`(name 지정, `run_in_background: true`, `model: "opus"`)로 팀원을 띄우고 `SendMessage({to: name})`로 통신한다. 작업 목록은 `specs/<feature>/tasks.md`(없으면 `_workspace/00_tasks.md`) 파일로 대신한다.

## 에이전트 구성

| 팀원 | 타입 | 역할 | 스킬 | 출력 |
|------|------|------|------|------|
| cto | 커스텀 `cto` | 스택·구조·계약·작업분할 결정, 계약 변경 심사 | tech-decision | `_workspace/01_cto_{tech-decisions,api-contract,task-split}.md` |
| backend-dev | 커스텀 `backend-dev` | `backend/` 구현 | implement-from-contract | `backend/`, `_workspace/02_backend_progress.md` |
| frontend-dev | 커스텀 `frontend-dev` | `frontend/` 구현 | implement-from-contract | `frontend/`, `_workspace/02_frontend_progress.md` |
| frontend-designer | 커스텀 `frontend-designer` | 채팅 UI/UX 설계·구현(레이아웃·사이드바·메시지·입력창·상태·반응형·접근성), 디자인 시스템, UI 자기 점검 | design-system, chat-ui-design, ui-review (+implement-from-contract 보고 형식) | `frontend/` 표현 계층, `_workspace/02_designer_progress.md`, `_workspace/04_designer_<화면>.md` |
| qa-integrator | 커스텀 `qa-integrator` | 모듈별 경계면 교차 검증, 최종 리포트 | integration-qa | `_workspace/03_qa_{findings,report}.md` | UI 검증 시 ui-review 병행 |

모든 Agent 호출에 `model: "opus"`를 명시한다.

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `_workspace/` 존재 여부 확인
2. 모드 결정:
   - **없음** → 초기 실행. Phase 1로
   - **있음 + 부분 요청** ("백엔드만", "QA만", "계약 바꿔서") → 부분 재실행. 아래 표의 해당 Phase만 실행. 에이전트 프롬프트에 기존 산출물 경로를 넣어 이어서 하게 한다
   - **있음 + 새 입력** (PRD 대폭 변경, "처음부터") → `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 초기 실행. `frontend/`, `backend/`는 사용자에게 유지/삭제를 확인한다

| 부분 요청 | 실행 범위 |
|----------|----------|
| "spec/plan/tasks 다시" | Spec Kit 스킬(speckit-specify/plan/tasks)을 cto에게 위임 → 영향 모듈만 Phase 3 |
| "스택/계약 다시" | Phase 2 → 계약 변경 영향 모듈만 Phase 3 → Phase 4 |
| "백엔드만 / 프론트만 다시" | Phase 3에서 해당 개발자 + QA만 |
| "QA만 다시" | Phase 4만 |
| "UI만 다시 / 화면 다듬기 / 디자인 적용" | Phase 3에서 frontend-designer + qa-integrator만. 계약·데이터 변경 없음 |
| "이어서 구현" | Phase 3부터, progress 파일의 "진행중/대기" 모듈부터 |

### Phase 1: 준비

1. `docs/prd/PRD-kbap-pm-agent.md`를 읽는다. 없으면 중단하고 PRD를 먼저 요청한다. `.specify/memory/constitution.md`가 있으면 함께 읽고 팀원 프롬프트에 "헌법 준수"를 명시한다
2. 사용자 메시지에서 스택 선호(Python/TypeScript, 프레임워크)를 찾는다. 없으면 **묻지 않고** CTO에게 "선호 없음, 기본값 선택 후 가정으로 표시"를 전달한다. 프로토타입이 목적이므로 결정 지연보다 뒤집기 쉬운 기록이 낫다
3. 작업 브랜치 생성: `git checkout -b feat/<feature-slug>` (main 직접 커밋 금지, CLAUDE.md Git 워크플로우). 팀원 프롬프트에 브랜치 이름을 명시한다
4. `_workspace/` 생성, `_workspace/00_input.md`에 PRD 경로·스택 선호·사용자 지시 요약 기록

### Phase 2: 기술 결정
**실행 모드:** 서브 에이전트

```
Agent(
  name: "cto", subagent_type: "cto", model: "opus",
  prompt: "docs/prd/PRD-kbap-pm-agent.md와 _workspace/00_input.md를 읽고 tech-decision 스킬에 따라
           _workspace/01_cto_tech-decisions.md, 01_cto_api-contract.md, 01_cto_task-split.md를 작성하라.
           완료 시 '가정' 상태 ADR 목록을 보고하라."
)
```

완료 후 리더가 확인하는 것:
- 세 파일 존재
- 계약서 JSON 예시에 자리표시자(`{...}`, `string`) 없음
- 작업 분할의 첫 모듈이 양쪽 모두 "뜬다 + 헬스체크"
- 가정 ADR 목록을 사용자에게 한 줄씩 보고 (진행은 멈추지 않는다)

실패 시 1회 재호출. 재실패면 사용자에게 보고하고 중단. 계약 없이 구현을 시작하지 않는다.

### Phase 3: 병렬 구현 + 점진 QA
**실행 모드:** 에이전트 팀

1. 팀 띄우기 — 한 메시지에서 핵심 4명을 동시에, 작업에 UI/UX 항목이 있으면 frontend-designer까지 5명:
   - `cto` (대기 모드: "계약 변경 요청과 질의에만 응답하라. 변경 시 계약서 수정 후 세 명에게 SendMessage")
   - `backend-dev`, `frontend-dev` ("implement-from-contract 스킬로 task-split 순서대로 구현. 모듈 완료마다 qa-integrator에게 보고")
   - `qa-integrator` ("integration-qa 스킬로 모듈 완료 알림마다 즉시 검증. 결함은 담당자에게 직접")
   - `frontend-designer` — 작업에 UI/UX 항목(레이아웃·사이드바·메시지 표현·반응형·접근성·디자인 시스템)이 있을 때만 띄운다 ("chat-ui-design·design-system 스킬로 설계 후 구현, ui-review로 자기 점검 후 qa-integrator에 보고. api.ts와 데이터 흐름은 frontend-dev 소유, 공동 파일은 사전 통지"). 디자인 시스템이 없으면 designer의 토큰 제안을 리더가 사용자에게 확인받은 뒤 적용한다
   모두 `run_in_background: true`, `model: "opus"`.

2. 작업 목록: `.specify/feature.json`이 가리키는 `specs/<feature>/tasks.md`가 있으면 그것이 작업 목록이다 (Spec Kit 흐름). 팀원들은 완료한 태스크를 `- [x]`로 체크한다. tasks.md가 없으면 `_workspace/00_tasks.md`에 task-split을 체크리스트로 복사해 대신 쓴다

3. 팀원 간 통신 규칙 (에이전트 정의에 있지만 프롬프트에도 요약해 넣는다):
   - 개발자 → QA: `[모듈 완료]` 형식
   - QA → 개발자: `QA-N` 결함 형식, 경계면 결함은 양쪽에
   - 개발자 → CTO: `[계약 변경 요청]` 형식. CTO → 전원: 변경 통지
   - 개발자 ↔ 개발자: 계약서 읽고도 모호할 때만 직접 질의
   - frontend-designer ↔ frontend-dev: 공동 파일(App/Chat/ConversationList/ProposalCard/SettingsPage) 수정 전 범위 통지. 표현은 designer, 데이터 흐름은 dev
   - frontend-designer → qa-integrator: `[모듈 완료]`에 반응형·접근성 자체 점검 결과(ui-review) 첨부

4. 리더 모니터링:
   - 팀원 완료/유휴 알림 수신 시 progress·findings 파일을 읽어 상태 파악
   - 한 개발자가 "막힘"으로 10분 이상이면 SendMessage로 원인 확인. 상대 파트 대기면 mock으로 진행하게 지시
   - 같은 결함이 두 번 열리면 CTO에게 구조 검토 지시
   - 계약 변경이 3회를 넘으면 사용자에게 보고 (계약 초안이 부실했다는 신호)

5. 종료 조건: 작업 분할의 모든 모듈이 progress에 "완료", findings에 "열림" 결함 0

### Phase 4: 최종 QA
**실행 모드:** 팀 유지, `qa-integrator` 주도

1. QA에게 "전체 모듈 실행 검증 + 최종 리포트" 지시. mock→실제 전환된 모듈은 다시 본다
2. 새 결함이 나오면 Phase 3의 수정 루프로 돌아간다. 최대 2회
3. `_workspace/03_qa_report.md` 생성 확인

### Phase 5: 정리

1. 팀원 전원에게 종료 요청
2. `_workspace/` 보존 (삭제하지 않는다. 감사 추적과 재실행에 쓴다)
3. PR 생성: 브랜치를 푸시하고 `gh pr create`로 main 대상 PR을 연다. 본문에 QA 리포트 요약(통과/실패/미검증)과 미검증 항목에 필요한 것을 적는다. 머지는 사용자가 한다
4. 사용자 보고: 실행 방법(FE·BE 각 한 줄), 가정 ADR 목록, QA 통과/실패/미검증 수, 남은 위험, 미검증 외부 연동에 필요한 키 목록
5. 피드백 요청: "결과·팀 구성·워크플로우에서 바꿀 점이 있나요?" 피드백은 CLAUDE.md 변경 이력에 기록하고 해당 에이전트/스킬을 수정한다

## 데이터 흐름

```
PRD ──→ [cto] ──→ 01_cto_tech-decisions.md
                  01_cto_api-contract.md ←──── 계약 변경 요청 ────┐
                  01_cto_task-split.md                            │
                        │                                         │
          ┌─────────────┴──────────────┐                          │
          ↓                            ↓                          │
   [backend-dev]  ←─ shape 질의 ─→  [frontend-dev] ───────────────┤
                                   [frontend-designer] ─ 표현 계층 ─┘(공동 파일 사전 통지)
     backend/                        frontend/                    │
   02_backend_progress.md         02_frontend_progress.md         │
          │    [모듈 완료]                 │    [모듈 완료]          │
          └──────────→ [qa-integrator] ←───┘                      │
                        │  QA-N 결함 (양쪽에)                      │
                        │  계약 결함 ─────────────────────────────┘
                   03_qa_findings.md
                   03_qa_report.md
                        ↓
                   [리더: 종합 보고]
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| CTO 산출물 불완전 (자리표시자, 파일 누락) | 1회 재호출 with 구체적 누락 지점. 재실패면 중단 보고 |
| 개발자 1명 중지 | SendMessage로 상태 확인 → 재시작. 재실패면 같은 정의로 새 에이전트 띄우고 progress 파일부터 이어가게 |
| 개발자 2명 모두 중지 | 사용자에게 보고, 진행 여부 확인 |
| QA 중지 | 재시작. 재실패면 리더가 findings 파일 기준으로 최소 검증(헬스체크 왕복)만 직접 수행하고 리포트에 "QA 미완" 명시 |
| 외부 키 없음 (Amplitude, LLM) | 가짜 연동으로 진행. 리포트에 미검증 명시. 통과로 위장하지 않는다 |
| 계약 변경 충돌 (FE·BE가 동시에 상반된 요청) | CTO가 결정. 리더는 개입하지 않는다 |
| 계약 변경 3회 초과 | 사용자에게 보고. 계약 초안 재검토 제안 |
| 같은 결함 2회 재발 | CTO에게 구조적 원인 분석 지시 (공용 파서, 계약 모호) |

## 테스트 시나리오

### 정상 흐름
1. 사용자: "PRD대로 프로토타입 만들어줘. 백엔드는 Python으로"
2. Phase 0: `_workspace/` 없음 → 초기 실행
3. Phase 1: PRD 읽기, 스택 선호 "Python" 기록
4. Phase 2: cto가 ADR 8개, 계약서(6개 이상 엔드포인트), 작업 분할 작성. 가정 ADR 2개 사용자에 보고
5. Phase 3: 핵심 4명 띄움(UI 항목이 있으면 designer 포함 5명). 양쪽 헬스체크 모듈 완료 → QA 왕복 확인 통과. 채팅 모듈에서 QA-1(응답 감싸기 불일치) → 백엔드 수정 → 확인됨. 제안 카드 모듈에서 프론트가 CTO에 필드 추가 요청 → 계약 갱신 → 전원 통지
6. Phase 4: 최종 리포트. Amplitude·LLM은 키 없어 미검증
7. Phase 5: 실행 방법, 가정 2개, 통과 N/실패 0/미검증 2, 필요한 키 목록 보고

### 에러 흐름
1. Phase 3에서 backend-dev가 Docker 빌드 실패로 중지
2. 리더가 유휴 알림 수신, SendMessage로 원인 확인 → 재시작 지시
3. 재시작 실패 → 같은 정의로 새 backend-dev 띄움, "progress 파일의 진행중 모듈부터 이어가라"
4. 그동안 frontend-dev는 mock으로 진행, QA는 프론트 측 정적 대조만 수행
5. 복구 후 통합 지점에서 mock→실제 전환, QA 재검증
6. 리포트에 "백엔드 1회 재시작" 기록

### 부분 재실행
1. 사용자: "제안 응답에 confidence 필드 추가해서 다시"
2. Phase 0: `_workspace/` 있음 + 계약 변경 → "스택/계약 다시" 경로
3. cto만 호출해 계약서 갱신 (ADR 추가 없음, 계약 §만 변경)
4. 영향 모듈(백엔드 채팅, 프론트 제안 카드)만 개발자 호출 → QA 해당 모듈 재검증
5. 리포트 갱신
