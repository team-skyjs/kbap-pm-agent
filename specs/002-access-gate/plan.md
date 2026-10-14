# Implementation Plan: 접근 제한

**Branch**: `feat/access-gate` (기능 디렉토리 `002-access-gate`) | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/002-access-gate/spec.md`, `docs/prd/PRD-access-gate.md`

**결정 출처**: `_workspace/01_cto_tech-decisions.md` ADR-22(같은 출처 + Access), ADR-23(운영 검사), 계약 `_workspace/01_cto_api-contract.md` v1.2

## Summary

프론트를 GitHub Pages에서 홈서버로 옮긴다. 백엔드 이미지가 빌드된 프론트를 함께 담아 FastAPI가 `/`에서 정적 서빙하므로, 화면과 API가 한 컨테이너·한 호스트명·같은 출처에 놓인다. 터널 규칙은 그대로(호스트명 → 백엔드)이고, Cloudflare Access가 호스트 전체를 이메일 일회용 PIN과 허용 목록으로 막는다.

이로써 다음이 정리된다.
- CORS·`VITE_API_BASE_URL`·Pages 워크플로우를 없앤다.
- 프론트는 세션 만료(Access 응답)를 계약 에러와 구분해 다시 로그인을 안내한다.
- 배포 워크플로우 하나가 두 이미지를 같은 커밋 태그로 배포한다.
- 운영 검사는 서비스 토큰으로 Access를 통과해 바깥 경로 전체를 검증한다.

## Technical Context

**Language/Version**: 기존과 같다(백엔드 Python 3.12, 프론트 TypeScript·React·Vite). 새 언어는 없다.

**Primary Dependencies**: 추가 없음. FastAPI `StaticFiles`(이미 의존성에 포함된 Starlette)와 백엔드 Dockerfile의 node 빌드 단계만 쓴다.

**Storage**: 변경 없음.

**Testing**: 헌법 원칙 V. 모듈마다 assert 검사 스크립트 하나와 QA 교차 검증 하나다. 프론트는 `frontend/checks/check-g*.ts`, 운영은 `backend/checks/check_b8.py` 갱신, 로컬 같은 출처는 `deploy/checks/check_g1.sh`(curl), 배포 구성은 `deploy/checks/check_g4.sh`(compose config·운영 식별자 검사)다.

**Target Platform**: 홈서버 Docker(`monitor-net`), 대시보드 관리형 cloudflared 터널, Cloudflare Zero Trust 무료 플랜.

**Project Type**: 웹 애플리케이션(`frontend/` + `backend/`) + 인프라 설정(사람이 대시보드에서).

**Performance Goals**: SC-004. 첫 진행 표시 5초, 완성 제안 3분이 접근 제한 전후로 유지돼야 한다. 프록시 계층이 추가되지 않아 SSE 경로는 그대로다.

**Constraints**:
- 운영 호스트명·IP·서버 경로를 레포에 쓰지 않는다(CLAUDE.md "운영 정보 비노출"). 문서 예시는 `pm-agent.example.com`과 변수 이름이다.
- 앱 코드에 인증을 넣지 않는다(PRD 8절).
- Cloudflare 무료 플랜 안에서 해결한다.

**Scale/Scope**: 사용자 2명. 컨테이너 수 그대로(백엔드 이미지에 프론트 포함), 계약 공통 절 문구 변경, 사람 손 설정 3종(Access 앱·이메일 정책, 서비스 토큰, Pages 내리기).

NEEDS CLARIFICATION: 없음. 동작 가정 4개는 [research.md](./research.md) R1~R4에서 검증 방법과 대체 경로를 정했다.

## Constitution Check

*GATE: Phase 0 전 1차, Phase 1 설계 후 2차 확인.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. 계약이 경계다 | 준수 | 계약 v1.2는 공통 절 문구만 바꾼다(Base URL, 요청 헤더, 접근 계층 응답, CORS, 콜백 비고, 예시 호스트). 응답 shape는 그대로다. 원본과 `specs/001-pm-agent-prototype/contracts/` 분할본 diff 0을 확인했다. 헌법 v1.2.0(재개 시 v1.4.0으로 같은 내용 재개정) 원칙 I이 분할본 위치를 제품당 하나로 정했다. 그래서 002에 사본을 만들지 않고 [contracts/README.md](./contracts/README.md)가 정본 위치와 바뀐 절을 가리킨다(사본을 늘리면 동기화 대상이 늘어난다). |
| II. 작동하는 가장 짧은 코드 | 준수 | 정적 서빙은 `StaticFiles` 마운트 한 줄이고, 프록시 컨테이너·터널 경로 규칙을 만들지 않는다. CORS 미들웨어와 `VITE_API_BASE_URL`은 지워서 코드가 준다. 세션 만료 판정은 `api.ts`의 `rawFetch` 한 곳이다. |
| III. 갈아끼울 수 있는 외부 연동 | 준수 | LLM·Amplitude·GitHub seam과 `AGENT_MODE=fake`는 그대로다. Access는 앱 바깥 계층이라 seam 대상이 아니다. 로컬과 fake 모드는 Access 없이 같은 출처 구조로 돈다. |
| IV. 비용 상한 | 준수 (강화) | 예산 상한 코드는 그대로이고, 허용 목록 밖 호출이 백엔드에 닿지 않아 예산 소진 경로가 닫힌다(SC-001). |
| V. 모듈마다 검사 하나 | 준수 | G1~G5 모듈마다 검사 태스크와 QA 태스크를 둔다(tasks.md). 테스트 선작성 태스크는 없다. |

기술 제약 절과의 대조:
- **일치(헌법 v1.2.0 → 재개 시 v1.4.0, 내용 동일)**: 기술 제약의 프론트 줄(백엔드 컨테이너가 정적 파일을 함께 제공, 같은 출처, 상대 경로 `/api`), FE↔BE 줄(Cloudflare Access 뒤 터널, 한 컨테이너가 `/api`와 정적 프론트 제공), 비목표 줄(앱 내 인증 없음, 접근 제한은 인프라)이 ADR-22와 맞는다. 선행 조건은 해소됐다.
- 비목표 "사용자 인증·권한"과 충돌하지 않는다. 앱 안의 인증은 계속 없고, 접근 제한은 인프라(Cloudflare Access)가 한다.

## Project Structure

### Documentation (this feature)

```text
specs/002-access-gate/
├── spec.md
├── plan.md              # 이 파일
├── research.md          # R1~R5: 가정 검증과 운영 검사 방식 비교
├── quickstart.md        # 로컬 같은 출처 실행·운영 확인 절차
├── contracts/README.md  # 정본 계약 위치와 v1.2 변경 절 (사본 없음)
├── checklists/requirements.md
└── tasks.md
```

data-model.md는 만들지 않는다. 저장 구조 변경이 없다.

### Source Code (repository root)

```text
frontend/
├── vite.config.ts       # base '/', server.proxy '/api' → localhost:8000
├── src/api.ts           # 상대 경로, X-Requested-With, redirect manual, SESSION_EXPIRED 판정
├── src/Chat.tsx·SettingsPage.tsx  # 세션 만료 안내(입력 보존, 새로고침 버튼)
└── checks/check-g2.ts   # 신규 (기존 check-f6.ts는 base 기대값 갱신)
backend/
├── Dockerfile           # node 단계에서 frontend/ 빌드 → dist/를 이미지에 포함 (빌드 컨텍스트: 레포 루트)
├── app/main.py          # StaticFiles를 / 에 마운트(/api 라우터 뒤), 공유 토큰 검사를 /api/로 한정, CORS 미들웨어 제거
└── checks/check_b1.py·check_b8.py   # preflight 기대 반전, 서비스 토큰·Access 거부 검사
deploy/
├── docker-compose.kbap-pm-agent.yml # 서비스 하나 그대로, 서버 경로 기본값 제거
├── deploy.kbap-pm-agent.sh          # 정적 / 헬스 추가, 서버 경로 기본값 제거
├── checks/check_g1.sh·check_g4.sh   # 로컬 같은 출처 왕복 / 배포 구성·운영 식별자 검사
├── kbap-pm-agent.env.example·README.md   # CORS_ORIGINS 제거, 운영 값 자리표시자화, 서비스 토큰 교체 절차
docker-compose.yml                   # 로컬: backend 빌드 컨텍스트를 레포 루트로 (web 서비스 없음)
.github/workflows/deploy.yml         # deploy-backend.yml 개명, 트리거에 frontend/**, 이미지 하나, check_b8 단계
.github/workflows/pages.yml          # 삭제
```

**Structure Decision**: 기존 두 디렉토리를 그대로 쓴다. 프론트 빌드는 백엔드 이미지 빌드의 한 단계라 배포 단위가 하나다. 프론트만 바뀌어도 이미지를 다시 빌드한다. 로컬 개발은 Vite dev 서버 프록시(`localhost:5173`), 컨테이너 확인은 `localhost:8000`이다.

## Complexity Tracking

| 항목 | 왜 필요한가 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 프론트 빌드를 백엔드 이미지에 포함 | Pages에는 Access를 걸 수 없고 github.io가 우회로로 남는다(PRD 3절). 홈서버의 다른 앱과 같이 컨테이너 하나가 직접 서빙한다(사용자 결정) | nginx 웹 컨테이너(첫 판)는 컨테이너·이미지·SSE 버퍼링 설정이 하나씩 늘고 서버 운영 방식과 다르다. 대가로 프론트만 바뀌어도 백엔드 이미지를 다시 빌드한다 |
| 사람 손 설정(Access 앱·정책 2개, 서비스 토큰) | 접근 제한이 인프라 계층에 있다(FR-010: 허용 목록 변경에 코드 없음) | Terraform 등 IaC는 사용자 2명·설정 몇 개에 과하다 |
