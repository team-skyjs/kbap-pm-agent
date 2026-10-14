# Quickstart: PM Agent 프로토타입

```bash
docker compose up -d --build                                          # 레포 루트: backend(8000) + mysql(3307)
cd frontend && npm ci && VITE_API_BASE_URL=http://localhost:8000 npm run dev   # → http://localhost:5173/kbap-pm-agent/
```

기본값은 `AGENT_MODE=fake`(루트 `docker-compose.yml`)다. 외부 키 없이 아래 시나리오를 끝까지 돌릴 수 있어야 한다(SC-005). 응답 shape는 [contracts/](./contracts/README.md), 저장 구조는 [data-model.md](./data-model.md)를 본다.

## 전제

- Docker(Compose v2), Node 22 이상.
- 실제 모드(`AGENT_MODE=real`)에서만 다음이 필요하다: `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY`, 비공개 저장소면 `GITHUB_TOKEN`, Amplitude 계정 승인. 키는 루트 `.env`에만 두고 커밋하지 않는다.

## 시나리오 (fake 모드)

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | `curl localhost:8000/api/health` | `{"status":"ok","db":"ok","version":"0.1.0"}` | B1 |
| 2 | 화면 상단 헬스 표시 확인 | "ok" | F1 |
| 3 | 새 대화 → "스캔 퍼널에서 가장 큰 이탈 지점 찾아서 개선안 제안해줘" 전송 | 5초 안에 도구 호출 진행 표시가 뜨고, 이어서 제안 카드 2장(개선 1, 측정 설계 1)이 근거→제안→실행단계→측정방법 순서로 표시된다 | US1, US2, SC-004 |
| 4 | 측정 설계 카드의 퍼널 표 확인 | 단계마다 기존/신규 표시가 있고, 신규 단계에 파일·함수가 있다 | US2, FR-004 |
| 5 | 개선 카드에서 "채택" 클릭 후 새로고침 | 채택 상태와 결정 시각이 유지된다. 대화 목록의 채택 수가 1이다 | US1-2, US3 |
| 6 | 대화를 하나 더 만들고 목록 확인 | 최근 순, 제목·시각·제안 수 표시 | US3 |
| 7 | 설정 화면: 저장소 `https://github.com/team-skyjs/kbap-fe` 등록 | 동기화 시각·화면 수 표시(fake 값) | US4-2 |
| 8 | 설정 화면: 택사노미 JSON 업로드(계약서 예시 본문) | 이벤트 2개, 갱신 시각 표시 | US4-1 |
| 9 | 속성 `type`을 `"date"`로 바꿔 다시 업로드 | 위반 위치가 담긴 오류가 뜨고, 이벤트 수는 2개 그대로 | US4-4 |
| 10 | 설정 화면: Amplitude 연결 | 상태가 "연결됨"으로 바뀐다. fake 모드에서 열린 탭은 계약서 예시 URL이라 Amplitude 오류 페이지가 떠도 정상이다 | US4-3 |

## 실제 모드 확인

1. `.env`에 `AGENT_MODE=real`과 키를 넣고 `docker compose up -d`.
2. 설정 화면에서 저장소 등록 → `codeMapStatus`가 `ready`가 될 때까지 대기.
3. Amplitude 연결 승인.
4. 시나리오 3을 실제 질문으로 다시 실행하고, 제안의 수치를 Amplitude에서 직접 대조한다(SC-003).
5. 설정 화면 예산에서 `spentUsd`가 늘었는지 확인한다(SC-006).

## 검사 스크립트

모듈 검사는 각자 한 줄로 돈다(헌법 원칙 V).

```bash
docker compose exec backend uv run python checks/check_b1.py
cd frontend && npm run check -- f1
cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md   # 계약 동기화
```
