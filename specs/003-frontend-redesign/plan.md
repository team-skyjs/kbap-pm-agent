# Implementation Plan: 프론트 재설계 — 대화에 집중하는 채팅 화면

**Branch**: `feat/frontend-redesign` (기능 디렉토리 `003-frontend-redesign`) | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/003-frontend-redesign/spec.md`, `docs/prd/PRD-frontend-redesign.md`, `_workspace/00_input_003.md`

**결정 출처**: `_workspace/01_cto_tech-decisions.md` ADR-24(차트 라이브러리), ADR-25(마크다운 파이프라인), ADR-26(UI 검사 구성), ADR-27(차트 블록 형식). API 계약 `_workspace/01_cto_api-contract.md`는 바꾸지 않는다.

## Summary

기존 기능과 API 연동을 그대로 두고 화면 표현 계층만 다시 짠다.
- **토큰과 레이아웃**: CSS 변수 토큰(라이트·다크) 위에 ChatGPT 데스크톱형 셸을 만든다. 접히는 사이드 패널, 768px 이하 Drawer, 중앙 최대 폭 채팅, 하단 고정 입력창이다.
- **마크다운**: 답변과 제안 텍스트는 react-markdown + remark-gfm로 그리고, HTML은 해석하지 않는다.
- **차트**: 언어 표시가 `chart`인 코드 블록은 프론트 파서가 검증한다. 검증을 통과하면 지연 로드한 Chart.js 선·막대 차트와 대체 텍스트 표로, 실패하면 원문 코드 블록으로 보인다.
- **에이전트 지시**: 차트 블록을 쓰라는 시스템 프롬프트 한 줄을 백엔드 문자열 상수에 더한다(응답 형식 변경 없음).
- **검사**: Playwright + axe-core가 뷰포트 3종 × 라이트·다크·동작 줄이기에서 스토리별 시나리오를 돌리고 스크린샷을 남긴다. API는 계약 예시로 만든 고정 응답으로 대체한다.

## Technical Context

**Language/Version**: TypeScript, React 19, Vite 6(기존). 백엔드는 Python 3.12(문자열 한 줄).

**Primary Dependencies**:
- 런타임 추가: `remark-gfm`(약 41KB min), `remark-cjk-friendly`(한국어 강조 닫힘 수정, 메인 청크 +13KB min, 2026-10-15 추가), `chart.js` v4(필요한 컨트롤러만 등록, 약 171KB min/59KB gz, 지연 로드). 앱 빌드 실측(frontend-dev 4947e82)은 메인 약 +60KB와 차트 청크 169KB로 합계 약 229KB다.
- 개발 의존성 추가: `@playwright/test`, `@axe-core/playwright`. 브라우저는 Chromium만 쓴다.
- 크기는 2026-10-15 esbuild 실측값이다(research R1). 상태관리·UI 컴포넌트·CSS 프레임워크는 추가하지 않는다.

**Storage**: 브라우저 `localStorage`의 사이드 패널 접기 상태 한 키만. 저장 실패는 무시한다.

**Testing**: 헌법 원칙 V를 따른다. 스토리마다 검사 하나다.
- UI 스토리는 `frontend/checks/ui/usN.spec.ts`(Playwright)다.
- 차트 파서는 `frontend/checks/check-f7.ts`(assert, 기존 `npm run check`에 합류)다.
- 시스템 프롬프트 줄은 `backend/checks/check_b9.py`다.
- `npm run check:ui`는 기존 f1~f6과 분리된 명령이다.

**Target Platform**: 데스크톱 최신 Chromium·Safari·Firefox 우선, 모바일 브라우저는 깨지지 않음까지. 배포는 현행 방식 그대로.

**Project Type**: 웹 애플리케이션의 프론트 표현 계층 + 백엔드 문자열 상수 한 줄.

**Performance Goals**: SC-005. 운영 번들 증가 300KB 이하(min 기준), 차트 의존성 200KB 이하이며 차트 블록이 없는 화면은 차트 청크를 내려받지 않는다.

**Constraints**:
- `frontend/src/api.ts`를 고치지 않는다. 접근 제한 PR과 겹치지 않게 하기 위해서다.
- 병합 순서는 재설계 먼저, 접근 제한 PR은 맨 나중이다(2026-10-15 사용자 결정). 화면 파일은 main 현재본 기준으로 고치고, 접근 제한 쪽이 나중에 세션 만료 표시를 다시 얹는다(tasks.md "병합 순서").
- 컴포넌트 CSS에 원시 값을 쓰지 않는다(FR-001).

**Scale/Scope**: 화면 5개(App 셸, 대화 목록, 채팅, 제안 카드, 설정), 새 렌더러 컴포넌트 2개(마크다운, 차트), 스토리 12개.

NEEDS CLARIFICATION: 없음. 사용자 결정 두 가지(강조색, 차트 라이브러리 확인)는 tasks.md의 `[USER]` 태스크다.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인. 헌법 v1.3.0 기준(접근 제한 머지 후 v1.4.0이 되어도 프론트 표현 계층 조항은 같다).*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | API 계약을 바꾸지 않는다. 차트 블록은 API 필드가 아니라 답변 `content` 안의 마크다운 관례다. 그 형식은 [contracts/chart-block.md](./contracts/chart-block.md)에 따로 고정하고, 프론트 파서와 시스템 프롬프트가 같은 예시를 쓴다. UI 검사의 고정 응답은 계약 예시 JSON에서 만든다(`frontend/checks/contract.ts` 재사용). 타입 캐스팅·`any`는 쓰지 않는다. |
| II. 작동하는 가장 짧은 코드 | 준수 (정당화 1) | 새 런타임 의존성은 PRD가 허용한 둘(GFM 확장, 차트 하나)과, 정확성 결함 수정으로 team-lead가 승인한 한국어 강조 플러그인 하나다. 구문 강조는 넣지 않는다(ADR-25). 원칙 II의 "UI는 읽을 수 있고 눌리면 된다, 디자인 시스템은 필요가 증명된 뒤"는 이번 PRD(사용자 결정)가 필요를 증명했다. 그래도 토큰은 CSS 변수로만 두고 디자인 시스템 라이브러리는 쓰지 않는다. |
| III. 갈아끼울 수 있는 외부 연동 | 해당 없음 | 외부 연동 seam을 건드리지 않는다. 시스템 프롬프트 문자열만 바뀐다. 모델명은 코드에 박지 않는다. |
| IV. 비용 상한 | 준수 | 시스템 프롬프트에 한 줄(약 80토큰)을 더한다. 프롬프트 캐싱 대상 고정 앞부분이라 질문당 비용 영향은 무시할 수준이다. 차트 블록 출력 토큰은 시계열 답변에만 든다. |
| V. 모듈마다 검사 하나 | 준수 | 스토리마다 검사 하나(Playwright 시나리오, 또는 assert 스크립트)와 QA 태스크 하나다. Playwright는 사용자가 PRD에서 요청한 검사라 "요청 기반" 조항과 맞는다. 테스트 선작성 태스크는 없다. |

기술 제약 절과의 대조: React·Vite·TS 정적 SPA, 해시 라우팅, 상대 경로/환경변수 API 주소는 손대지 않는다(api.ts·vite.config.ts 미변경). 비목표(인증·권한 등)와 무관하다.

## Project Structure

### Documentation (this feature)

```text
specs/003-frontend-redesign/
├── spec.md
├── plan.md              # 이 파일
├── research.md          # R1 차트 라이브러리, R2 구문 강조, R3 UI 검사 구성·CI, R4 테마 전환 시 차트 색, R5 접근 제한 PR과의 병합 순서
├── data-model.md        # 디자인 토큰 목록, 차트 블록 스키마와 검증 규칙, 메시지 화면 상태
├── quickstart.md
├── contracts/chart-block.md   # 모델 출력 ↔ 프론트 파서 형식 (API 계약 아님)
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
frontend/
├── package.json                 # remark-gfm, chart.js / devDeps @playwright/test, @axe-core/playwright / script check:ui
├── playwright.config.ts         # 신규: webServer(vite dev), 프로젝트 3뷰포트 × 3모드
├── src/
│   ├── style.css                # [DS] 토큰(:root, 다크), 기본 요소, 셸·컴포넌트 스타일 (원시 값 금지)
│   ├── App.tsx                  # [DS] 셸: 사이드 패널/Drawer, 헤더, 라우팅 유지
│   ├── ConversationList.tsx     # [DS] 목록 표현
│   ├── Chat.tsx                 # [DS] 메시지·입력창·상태 표현 (api.ts 호출 흐름 유지)
│   ├── ProposalCard.tsx         # [DS] 접는 구역·라벨·버튼
│   ├── SettingsPage.tsx         # [DS] 재스타일
│   ├── Markdown.tsx             # 신규 [FE]: react-markdown + remark-gfm, 링크·코드·표 렌더, chart 분기
│   ├── chartBlock.ts            # 신규 [FE]: 차트 블록 JSON 파서·검증(순수 함수)
│   └── ChartBlock.tsx           # 신규 [FE]: chart.js 지연 로드, 토큰 색, 테마 변경 대응, 대체 표
├── checks/
│   ├── check-f7.ts              # 신규 [FE]: chartBlock 파서 assert (기존 npm run check에 합류)
│   └── ui/                      # 신규 [FE]: fixtures(계약 예시 기반), helpers(axe·스크린샷), usN.spec.ts
backend/
├── app/agent.py                 # [BE]: SYSTEM_PROMPT에 차트 블록 규칙 한 줄
└── checks/check_b9.py           # 신규 [BE]: 프롬프트 줄과 contracts/chart-block.md 예시 일치
.gitignore                       # _workspace/04_designer_screenshots/ 추가
_workspace/04_designer_*.md      # [DS] 화면별 설계 문서, 토큰 제안서
```

**Structure Decision**: 기존 컴포넌트 파일을 그대로 쓴다. 렌더러 두 개와 파서 하나만 새 파일이다. 파일 소유는 표현(frontend-designer)과 데이터·렌더러·검사(frontend-dev)로 나눠 같은 파일을 두 사람이 동시에 고치지 않게 한다. `Chat.tsx`·`ProposalCard.tsx`는 designer 소유이며, 마크다운이 필요한 자리에서 `Markdown` 컴포넌트를 가져다 쓴다.

## Complexity Tracking

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 런타임 의존성 3개(`remark-gfm`, `remark-cjk-friendly`, `chart.js`) | PRD US-005(GFM 표, 한국어 강조가 문자로 보이는 결함)·US-006(차트) | 표 파서·차트를 직접 구현하면 코드가 더 많고 접근성·툴팁을 다시 만들어야 한다. 차트는 지연 로드로 첫 화면 비용을 0으로 한다 |
| 개발 의존성 2개(Playwright, axe) | PRD US-011·US-012, 사용자가 요청한 검사 | 수동 확인만으로는 뷰포트 3 × 모드 3 = 9조합 회귀를 잡을 수 없다 |
