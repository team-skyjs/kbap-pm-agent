# K-Bap PM Agent

레포 구조: `frontend/` (GitHub Pages), `backend/` (홈서버 Docker), `docs/prd/` (PRD 문서), `specs/` (Spec Kit).

## Git 워크플로우

main에 직접 커밋하지 않는다. 작업은 브랜치(`feat/...`, `fix/...`, `docs/...`)에서 하고 PR로 main에 합친다. 하네스 에이전트도 같다: 리더가 빌드 시작 시 브랜치를 만들고, 팀원은 그 브랜치에 커밋하며, 완료 후 리더가 PR을 연다. PR 설명 끝에는 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`를 붙인다. PR 제목은 영어로 쓰고 `feat:`·`fix:`·`ci:`·`docs:` 같은 접두어를 붙인다. 본문은 한국어로 쓴다. 작업 중 만든 내부 식별자(ADR 번호, 태스크 번호, 모듈 코드, QA 번호 등)는 PR 제목·본문에 쓰지 않고, 무엇이 왜 바뀌었는지 말로 적는다.

## PRD 문서 위치

모든 PRD는 `docs/prd/`에 둔다. `create-prd`(pm-execution) 등 PRD 스킬로 문서를 생성·수정할 때 산출물 경로를 반드시 `docs/prd/PRD-<product-name>.md`로 지정한다. 루트에 PRD를 만들지 않는다. 현재 PRD: `docs/prd/PRD-kbap-pm-agent.md`.

## 하네스: K-Bap PM Agent 구현

**목표:** PRD를 동작하는 프로토타입으로 바꾼다. CTO가 결정하고, FE·BE 개발자가 병렬 구현하고, QA가 경계면을 모듈마다 검증한다.

**문서 흐름:** PRD → `.specify/memory/constitution.md` → `specs/<feature>/spec.md` → plan.md → tasks.md → 구현. Spec Kit 스킬(`speckit-*`)로 생성한다.

**트리거:** 구현·빌드·개발 시작, 프론트/백엔드 작업, 재실행·부분 재실행·이어서 구현 요청 시 `kbap-build-orchestrator` 스킬을 사용하라. PRD 작성·수정은 `create-prd`. 단순 질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-10-15 | 초기 구성 (cto, frontend-dev, backend-dev, qa-integrator / 4 스킬) | 전체 | - |
| 2026-10-15 | PRD를 `docs/prd/`로 이동, PRD 스킬 산출물 경로 규칙 추가 | CLAUDE.md, 참조 경로 전체 | 사용자 요청 |
| 2026-10-15 | PR 제목은 영어, 본문은 한국어, 내부 식별자 금지 | CLAUDE.md | 사용자 지시 (한국어 제목은 번역이 어색) |
| 2026-10-15 | Git 워크플로우 규칙 추가: main 직접 커밋 금지, 브랜치 + PR | CLAUDE.md, orchestrator, implement-from-contract, integration-qa | 사용자 지시 "pr을 연다. 바로 커밋하지 않는다" |
| 2026-10-15 | 첫 빌드 완료. 61 태스크 중 54 통과, 미검증 7(키·승인·배포 필요). 결함 4건 모두 경계면 아님(표시 1, 인덱스 범위 1, 운영 출처 2). ADR-17~19 추가 | 전체 | 하네스 첫 실행 결과 |
| 2026-10-15 | Spec Kit 도입. 헌법 v1.0.0, specs/001-pm-agent-prototype. 오케스트레이터·implement 스킬이 tasks.md를 작업 목록으로 사용 | CLAUDE.md, orchestrator, implement-from-contract | 사용자 요청 "speckit으로 기술 명세서 작성 후 구현" |
