# Quickstart: 프론트 재설계

```bash
cd frontend && npm ci && npx playwright install chromium   # 최초 1회
npm run dev                                                # http://localhost:5173 (백엔드는 레포 루트 docker compose up, fake 모드)
npm run check && npm run check:ui                          # 모듈 검사(f1~f7) + UI 검사(뷰포트 3 × 모드 3)
```

`check:ui`는 백엔드 없이 계약 예시 기반 고정 응답으로 돈다. 정상 스트리밍 한 개를 실제 fake 백엔드로 확인하려면 `CHECK_UI_LIVE=1 npm run check:ui`를 쓴다. 스크린샷은 `_workspace/04_designer_screenshots/`에 생긴다(gitignore). 차트 블록 형식은 [contracts/chart-block.md](./contracts/chart-block.md), 토큰 목록은 [data-model.md](./data-model.md)를 본다.

## 확인 시나리오

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | 시스템 테마를 라이트·다크로 바꿔 가며 채팅 화면을 연다 | 같은 배치, 색만 바뀜. 대비 계산값이 토큰 제안서와 일치 | US1, SC-001 |
| 2 | 1280px에서 사이드 패널 접기 → 새로고침 | 접힌 상태 유지 | US2 |
| 3 | 375px에서 메뉴 → Drawer → ESC | 닫힘, 가로 스크롤 없음, 열린 동안 본문 스크롤 잠김 | US2, FR-004 |
| 4 | 마크다운 표·코드·링크·`<script>`가 든 답변(고정 응답) | 표 가로 스크롤, 코드 복사, 링크 새 탭, 태그는 문자로 보임 | US5 |
| 5 | contracts/chart-block.md의 세 예시가 든 답변 | 선·막대 차트 2개 + 오류 예시는 원문 코드 블록, 다크에서도 읽힘 | US6 |
| 6 | 키보드만으로 새 대화 → 입력 → Enter → 제안 채택 | 전 과정 가능, 윤곽선 항상 보임 | US7, US11 |
| 7 | 여섯 상태 고정 응답(전송 직후·진행·완료·부분 완료·오류·세션 만료) | 각 상태 표시가 다르고 입력값 보존, 레이아웃 점프 없음 | US8 |
| 8 | `npm run build` 후 청크 크기 확인 | 증가 300KB 이하, 차트 청크는 분리되고 200KB 이하 | SC-005 |
| 9 | 실제 키로 시계열 질문 5건(가능할 때) | 4건 이상 답변에 올바른 차트 블록 | SC-007 |
