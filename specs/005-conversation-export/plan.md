# Implementation Plan: 대화 전체 내보내기

**Branch**: `feat/conversation-export` (기능 디렉토리 `005-conversation-export`) | **Date**: 2026-10-17 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/005-conversation-export/spec.md`, `docs/prd/PRD-conversation-export.md`

**결정 출처**: `_workspace/01_cto_tech-decisions.md` ADR-31(내보내기 기록), ADR-32(인쇄 방식과 차트), ADR-33(Markdown 형식). 계약 v1.4(엔드포인트 1개 추가), 파일 형식 [contracts/export-markdown.md](./contracts/export-markdown.md).

## Summary

대화 상단 바의 "내보내기" 버튼이 두 경로를 연다.
- **PDF**: `window.print()`를 쓴다. 인쇄 매체 스타일(`@media print`)이 `.app`의 화면 높이 고정·`overflow: hidden`과 `.scroll`의 스크롤을 풀어 대화 전체를 문서 흐름에 놓는다. 사이드바·입력창·조작 요소를 숨기고 밝은 토큰으로 바꾼다.
- **인쇄 직전·직후 처리**: `beforeprint`에서 제안 카드의 닫힌 `<details>`를 모두 열고 차트를 애니메이션 없이 인쇄 폭·밝은 색으로 다시 그린다. `afterprint`에서 되돌린다.
- **Markdown**: 이미 받은 대화 상세 데이터로 순수 함수가 파일 문자열을 만들어 Blob으로 내려받는다. 서버 호출은 없다.
- **기록**: 두 경우 모두 시작 시 `POST /api/conversations/{id}/exports`로 형식을 남긴다. 기다리지 않고, 실패는 무시한다.

## Technical Context

**Language/Version**: 프론트 TypeScript·React 19·Vite(003 재설계 위), 백엔드 Python 3.12·FastAPI.

**Primary Dependencies**: 추가 없음. 브라우저 `window.print`·`beforeprint`/`afterprint`·`matchMedia('print')`, `Blob`·`URL.createObjectURL`, 기존 Chart.js 인스턴스 API(`resize`, `options.animation`, `update('none')`)만 쓴다.

**Storage**: 새 테이블 `conversation_exports`(`CREATE TABLE IF NOT EXISTS`로 충분, ENUM 마이그레이션 없음).

**Testing**: 헌법 원칙 V. 모듈마다 검사 하나다.
- E1 프론트 내보내기: `frontend/checks/check-f10.ts`(Markdown 생성 규격)와 `frontend/checks/ui/us13.spec.ts`(인쇄 매체 에뮬레이션, 내려받기, 기록 호출).
- E2 백엔드 기록: `backend/checks/check_b11.py`.

**Target Platform**: Chrome 데스크톱이 기준이다(사용자 환경). Safari·Firefox 인쇄는 깨지지 않음까지만 보고 수동 확인 대상은 아니다.

**Project Type**: 웹 애플리케이션(프론트 대부분 + 백엔드 엔드포인트 1개).

**Performance Goals**: 없음(PRD 가정: 수십 메시지).

**Constraints**:
- 서버 PDF·헤드리스·PDF 라이브러리·새 의존성 금지(FR-011).
- 내보낸 파일과 인쇄 머리글에 API 주소·호스트명 금지(FR-009). 생성 함수는 `location`·API 기준 주소를 읽지 않는다.
- 토큰 규칙(FR-001) 유지. 인쇄용 밝은 값도 토큰으로 둔다.

**Scale/Scope**: 사용자 2명. 프론트 파일 약 6개, 백엔드 파일 3개.

NEEDS CLARIFICATION: 없음.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인. 헌법 v1.3.0.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | 계약 v1.4에 엔드포인트 하나(응답 201)를 더했다. 기존 shape는 그대로이고 원본과 분할본(새 파일 `08c-exports.md`) diff 0이다. 분할본은 제품당 하나이고 005에는 안내 파일을 둔다(002~004 선례). Markdown 파일 형식은 API가 아니므로 `contracts/export-markdown.md`에 따로 두고 생성 함수·검사가 같은 기준을 본다(003의 chart-block 선례). |
| II. 작동하는 가장 짧은 코드 | 준수 | 브라우저 인쇄 + CSS로 해결하고 PDF 라이브러리를 쓰지 않는다. Markdown은 순수 함수 하나다. 기록은 엔드포인트 하나와 테이블 하나다. 인쇄 직전 처리는 `beforeprint`/`afterprint` 한 곳에 모은다. |
| III. 갈아끼울 수 있는 외부 연동 | 해당 없음 | 외부 연동·LLM 호출이 없다. 시연 모드에서도 같은 동작(기록은 실제로 남김)이다. |
| IV. 비용 상한 | 해당 없음 | 모델 호출이 없다. |
| V. 모듈마다 검사 하나 | 준수 | E1(f10 + us13), E2(b11) 모듈마다 검사와 QA가 있다. 테스트 선작성은 없다. |

PRD와의 차이 한 가지: PRD 6.3은 "백엔드 변경 없음, 기존 로그 경로로 기록"이다. 그런데 조회할 수 있는 기존 로그 경로가 없어 최소 엔드포인트를 둔다(ADR-31). 앱 기능 PRD의 "측정은 DB 한 줄 조회" 규칙과 맞추기 위해서다.

## Project Structure

### Documentation (this feature)

```text
specs/005-conversation-export/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
├── contracts/README.md, contracts/export-markdown.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
frontend/
├── src/Chat.tsx (또는 Shell.tsx Topbar)  # "내보내기" 버튼·메뉴(PDF/Markdown), 비활성 조건, 인쇄 머리글 요소
├── src/print.ts               # 신규: beforeprint/afterprint 처리(details 열기·복원), window.print 호출
├── src/exportMarkdown.ts      # 신규: 순수 함수 toMarkdown(detail, now), exportFileName(title, id, now)
├── src/ChartBlock.tsx         # 인쇄 시 애니메이션 끔·인쇄 폭 재그리기·밝은 토큰, 복원
├── src/api.ts                 # recordExport(conversationId, format)
├── src/style.css              # @media print 블록(숨김·높이·스크롤 해제·끊김 방지·줄바꿈·밝은 토큰), --print-* 토큰
├── checks/check-f10.ts        # 신규: Markdown 규격 검사 (+ run.ts 한 줄)
└── checks/ui/us13.spec.ts     # 신규: 인쇄 매체 에뮬레이션·내려받기·기록 호출 (+ fixtures.ts 내보내기 고정 응답)
backend/
├── schema.sql                 # conversation_exports
├── app/conversations.py       # POST /api/conversations/{conversation_id}/exports
└── checks/check_b11.py        # 신규
```

**Structure Decision**: 이번 사이클은 frontend-dev 한 사람이 프론트 전부를 맡는다(team-lead 지시). 003 파일 소유 규칙(designer 소유의 `Chat.tsx`·`style.css`)은 이번에 한해 frontend-dev가 고친다. 백엔드 기록은 backend-dev 태스크로 분리한다.

## Complexity Tracking

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 백엔드 엔드포인트 1개 + 테이블 1개 | PRD 유일한 측정(건수·형식)을 조회 한 줄로 보려면 저장소가 필요하다 | 기록 생략은 측정 자체가 없어진다. 브라우저 콘솔 로그는 조회할 수 없다 |
