# K-Bap PM Agent

레포 구조: `frontend/` (GitHub Pages), `backend/` (홈서버 Docker), `docs/prd/` (PRD 문서), `specs/` (Spec Kit).

## Git 워크플로우

main에 직접 커밋하지 않는다. 작업은 브랜치(`feat/...`, `fix/...`, `docs/...`)에서 하고 PR로 main에 합친다. 하네스 에이전트도 같다: 리더가 빌드 시작 시 브랜치를 만들고, 팀원은 그 브랜치에 커밋하며, 완료 후 리더가 PR을 연다. PR 설명 끝에는 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`를 붙인다. 작업 트리를 여러 에이전트가 공유하므로 커밋은 항상 경로를 지정해(`git commit -- <경로>` 또는 `git commit -o <파일>`) 자기 파일만 담고, 커밋 전 `git diff --cached --name-only`로 인덱스에 남의 스테이징이 없는지 확인한다. `git add -A`·`git add -u` 금지. PR 제목은 영어로 쓰고 항상 `접두어(범위)` 형식으로 시작한다. 접두어는 feat·fix·ci·docs·chore, 범위는 backend·frontend·deploy·harness·docs 중 하나이며 여러 영역에 걸치면 가장 큰 변경의 영역을 쓴다. 예: `feat(backend): ...`, `ci(deploy): ...`. PR 머지는 머지 커밋(`gh pr merge --merge`)으로 한다. squash·rebase 머지는 쓰지 않는다(브랜치 커밋 이력 보존). 쌓인(stacked) PR은 아래 PR을 머지한 뒤 **위 PR의 base가 main으로 바뀐 것을 확인하고** 머지한다. base가 머지된 브랜치를 가리킨 채 머지하면 변경이 main에 닿지 않는다(2026-10-15 PR #2 사례). 본문은 한국어로 쓴다. 작업 중 만든 내부 식별자(ADR 번호, 태스크 번호, 모듈 코드, QA 번호 등)는 PR 제목·본문에 쓰지 않고, 무엇이 왜 바뀌었는지 말로 적는다.

## 코드 주석 규칙

1. 주석 최소화: 핵심 메서드와 복잡한 로직에만. 코드만으로 이해되는 내용은 생략
2. 문체: 종결형 어미(~다, ~합니다) 금지. 명사형 또는 간결한 구문
3. 기획 정보 배제: 기획서의 코드값·정책값·내부 식별자(ADR 번호, 태스크 번호, 모듈 코드 등)를 주석에 기재하지 않음. 근거가 필요하면 "왜"를 말로 적음
4. 간결성: 핵심 의도와 이유만. 배경 설명·장황한 서술 금지
5. 일관성: 기존 주석 스타일을 존중하고 같은 규칙 적용
6. `ponytail:` 표시는 유지하되 위 문체 규칙을 따름 (예: `# ponytail: 파일 캐시, 동시 요청 늘면 DB로`)

## 운영 정보 비노출

운영 호스트명·도메인·IP·ssh 별칭·서버 경로를 저장소 파일(코드, 문서, 예시 env, PR 제목·본문, 커밋 메시지)에 쓰지 않는다. 실제 값은 GitHub Variables/Secrets와 서버에만 둔다. 문서에는 `<운영 API 주소>` 같은 자리표시자나 변수 이름(PUBLIC_BASE_URL)으로 가리킨다. 레포가 공개이고 홈서버라 노출되면 공격 표면이 된다.

## PRD 문서 위치

모든 PRD는 `docs/prd/`에 둔다. `create-prd`(pm-execution) 등 PRD 스킬로 문서를 생성·수정할 때 산출물 경로를 반드시 `docs/prd/PRD-<product-name>.md`로 지정한다. 루트에 PRD를 만들지 않는다. 현재 PRD: `docs/prd/PRD-kbap-pm-agent.md`.

## 하네스: K-Bap PM Agent 구현

**목표:** PRD를 동작하는 프로토타입으로 바꾼다. CTO가 결정하고, FE·BE 개발자가 병렬 구현하고, QA가 경계면을 모듈마다 검증한다.

**문서 흐름:** PRD → `.specify/memory/constitution.md` → `specs/<feature>/spec.md` → plan.md → tasks.md → 구현. Spec Kit 스킬(`speckit-*`)로 생성한다.

**트리거:** 구현·빌드·개발 시작, 프론트/백엔드 작업, UI/UX 개선·화면 다듬기·디자인 시스템 적용·UI 리뷰, 재실행·부분 재실행·이어서 구현 요청 시 `kbap-build-orchestrator` 스킬을 사용하라. PRD 작성·수정은 `create-prd`. 단순 질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-10-15 | 프론트 재설계 003 완료(토큰·레이아웃·마크다운·차트·Playwright UI 검사), 접근 제한 PR #12 보류·브랜치 유지 | frontend/, specs/003-frontend-redesign, ADR-24~27 | PR #13 머지 |
| 2026-10-15 | 운영 정보 비노출 규칙, 경로 지정 커밋 규칙 추가 | CLAUDE.md | 사용자 지시(홈서버 주소 노출 금지), 공유 인덱스 커밋 사고 2건 |
| 2026-10-15 | 프론트 GitHub Pages 유지·API 공유 토큰 잠금 결정. 헌법 v1.3.0, 접근 제한 PRD 보류, feat/access-gate 미머지 보관 | constitution, PRD-access-gate, CLAUDE.md | 사용자 결정 |
| 2026-10-15 | frontend-designer 에이전트 + design-system·chat-ui-design·ui-review 스킬 추가, 오케스트레이터·QA 연결 | agents/frontend-designer, skills 3개, orchestrator, qa-integrator | 사용자 요청: ChatGPT 레퍼런스 채팅 UI/UX 전문 에이전트 |
| 2026-10-15 | 초기 구성 (cto, frontend-dev, backend-dev, qa-integrator / 4 스킬) | 전체 | - |
| 2026-10-15 | PRD를 `docs/prd/`로 이동, PRD 스킬 산출물 경로 규칙 추가 | CLAUDE.md, 참조 경로 전체 | 사용자 요청 |
| 2026-10-15 | 코드 주석 규칙 6개 추가 | CLAUDE.md, implement-from-contract | 사용자 지시 |
| 2026-10-15 | PR 제목은 영어, 본문은 한국어, 내부 식별자 금지 | CLAUDE.md | 사용자 지시 (한국어 제목은 번역이 어색) |
| 2026-10-15 | Git 워크플로우 규칙 추가: main 직접 커밋 금지, 브랜치 + PR | CLAUDE.md, orchestrator, implement-from-contract, integration-qa | 사용자 지시 "pr을 연다. 바로 커밋하지 않는다" |
| 2026-10-15 | 첫 빌드 완료. 61 태스크 중 54 통과, 미검증 7(키·승인·배포 필요). 결함 4건 모두 경계면 아님(표시 1, 인덱스 범위 1, 운영 출처 2). ADR-17~19 추가 | 전체 | 하네스 첫 실행 결과 |
| 2026-10-15 | Spec Kit 도입. 헌법 v1.0.0, specs/001-pm-agent-prototype. 오케스트레이터·implement 스킬이 tasks.md를 작업 목록으로 사용 | CLAUDE.md, orchestrator, implement-from-contract | 사용자 요청 "speckit으로 기술 명세서 작성 후 구현" |
