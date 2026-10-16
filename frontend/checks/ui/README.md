# UI 검사 (Playwright + axe)

```bash
cd frontend
npm ci && npx playwright install chromium     # 최초 1회
npm run check:ui                              # 전체: 스펙 × 9 프로젝트
npx playwright test -c playwright.config.ts us6 --project 1280-dark   # 일부만
```

- dev 서버는 실행마다 빈 포트로 새로 띄우고 기존 서버를 재사용하지 않는다(`reuseExistingServer: false`). 그래서 여러 트리에서 동시에 돌려도 각자 자기 코드를 검사한다. 포트를 정하려면 `UI_PORT`를 주되, 이미 쓰는 포트면 실패한다. 경로는 `vite.config.ts`의 `base`를 따른다.
- 기존 모듈 검사(`npm run check`, f1~f8)와 분리된 명령이다.

## 프로젝트 (9)

뷰포트 `1280`(1280×800) · `768`(768×1024) · `375`(375×812) × 모드 `light` · `dark`(`colorScheme`) · `reduced`(`reducedMotion: reduce`, 라이트). 이름은 `<뷰포트>-<모드>`다. 768 이하는 Drawer 레이아웃이라 스펙이 `1280` 여부로 분기한다.

## 고정 응답과 live 모드

- 기본: `fixtures.ts`의 `mockApi(page, options)`가 `**/api/**`를 가로챈다. 값은 계약 분할본(`specs/001-pm-agent-prototype/contracts/`) 예시 JSON과 05-messages SSE 예시에서 만든다.
  - 대화 7은 계약 상세 예시에 측정 설계 제안을 더한 상태, 다른 대화는 빈 상태로 시작한다. 전송한 메시지와 제안 결정은 저장되어 새로고침 뒤에도 남는다.
  - 전송 시나리오(`scenario`): `sent`(전송 직후) · `progress`(진행) · `done`(완료, 제안 2) · `partial`(상한 사유 문장) · `error`(UPSTREAM_ERROR) · `token`(백엔드 토큰 401 계약 JSON) · `expired`(로그인 HTML 401) · `hang`(응답 없이 요청 유지).
  - 고정 응답은 한 번에 끝나는 응답이라 `sent`·`progress`는 스트림 종료 뒤 저장된 실행 중 상세로 상태를 재현한다. 스트림이 열린 동안의 화면은 `hang`으로 본다.
  - 옵션: `assistantContent`(대화 7 답변 본문 교체, 예: `MARKDOWN_SAMPLE`), `list`(대화 목록 교체), `completeAfterPoll`(진행 → 다음 주기 재조회에서 완료), `conflictRace`(409 안내 경합 재현).
  - 질문 다듬기: `refine`(`ok` = 계약 08b 예시, `fail` = 502 UPSTREAM_ERROR), `refineDelayMs`(다듬기 응답 지연, 기본 300ms, 진행 중 잠금 확인용), `choiceFail`(선택 기록 500, 전송은 계속되어야 함).
  - 내보내기: `exportFail`(내보내기 기록 500, 내려받기·인쇄는 계속되어야 함), `sendDelayMs`(메시지 전송 응답 지연).
  - Amplitude: `amplitudeUnavailable`(메시지 전송 503 AMPLITUDE_UNAVAILABLE, `skipAmplitude: true`로 다시 보내면 통과), `amplitudeStatus`(설정의 `configured`·`missing`).
  - 기타: `title`(대화 7 제목 교체).
- live: `CHECK_UI_LIVE=1 npm run check:ui`면 고정 응답 스펙은 그대로 돌고, `mockApi`를 부르지 않는 live 전용 테스트(us8의 진행 → 완료 한 경로)가 추가로 로컬 백엔드(`docker compose up`, fake 모드)를 쓴다. 백엔드와 같은 출처(dev 프록시)가 되는 접근 제한 병합 뒤부터 동작한다. 그 전에는 백엔드 CORS가 5173만 허용한다.
- 토큰 401(`UNAUTHORIZED`)은 오류 상태(토큰·설정 안내)이고 세션 만료가 아니다. 세션 만료(`expired`, 로그인 HTML 401 → `SESSION_EXPIRED`) 스펙은 `test.fixme`이고 접근 제한 PR 병합 때 켠다.

## 스크린샷

각 스펙이 `helpers.ts`의 `shot(page, '<스토리>[-<상태>]', info)`로 `_workspace/04_designer_screenshots/<스토리>[-<상태>]-<프로젝트>.png`를 남긴다(gitignore, ui-review 입력). 채팅은 내부 스크롤 영역이라, 보여 줄 요소가 아래에 있으면 `scrollIntoViewIfNeeded()` 뒤에 찍는다.

## 대기 규칙

`waitForTimeout`을 쓰지 않는다. 상태가 바뀌기를 `expect(...)`·`expect.poll`로 기다린다. 차트는 연속 두 프레임의 캔버스가 같아질 때까지, Drawer는 포커스가 패널 안으로 들어올 때까지 기다린다.

## 스펙

| 파일 | 스토리 |
|---|---|
| smoke | 앱 기동·헬스 |
| us1 | 토큰: 본문 16px·1.6, 대비 4.5:1, 토큰 밖 원시 값 부재 |
| us2 | 셸: 접기 유지, Drawer(포커스 가두기·ESC·배경·스크롤 잠금), 본문 최대 폭 |
| us3 | 대화 목록: 최근순·말줄임·aria-current·키보드 선택·설정 링크 하단 |
| us4 | 메시지: 넘침 없음, 사용자만 배경, 아바타 없음 |
| us5 | 마크다운: 요소·링크 안전 속성·HTML 비해석·코드 복사·표 스크롤·한글 조사 굵게 |
| us6 | 차트: 선·막대, 형식 오류 원문, 대체 표, 다크, 차트 청크 지연 로드 |
| us7 | 입력창: Enter·Shift+Enter, 6줄 고정, 실행 중 비활성, 오류·만료 뒤 입력 보존, 한글 조합 |
| us8 | 상태 6종, 입력창 위치 고정, 스크롤 유지, 동작 줄이기, live |
| us9 | 제안 카드: 기본 펼침, 근거 라벨, 코드 위치, 신규 단계, 채택 유지 |
| us10 | 설정: 상태 라벨, 포커스 윤곽선, 토큰 저장, 375 넘침 |
| us11 | 키보드만으로 질문→채택, axe 심각·중대 0(채팅·카드 펼침·Drawer·설정) |
| us12 | 질문 다듬기: 버튼 활성 조건, 진행 중 잠금, 비교 카드, 네 선택(전송 본문·입력창·선택 기록 값), 실패 안내와 원문 유지, 선택 기록 실패에도 전송, 키보드·포커스, axe |
| us13 | 대화 내보내기: 버튼 활성 조건·메뉴 키보드, Markdown 내려받기(이름·내용·기록), PDF 인쇄 호출·기록, 인쇄 매체(흐름 풀기·숨김·머리글·흰 배경), 인쇄 직전·직후(카드 절 열기·차트 인쇄 폭·복원) |
| us14 | Amplitude 서버 키: 설정 상태 라벨 두 가지(연결 버튼 없음), 전송 사전 점검 거절 안내·입력 보존·"Amplitude 없이 진행" 재전송(skipAmplitude) |
