# contracts/ — 004 질문 마법사

계약은 제품 전체에 하나이므로 사본을 두지 않는다.

- 정본: `_workspace/01_cto_api-contract.md` v1.3
- 분할본: `specs/001-pm-agent-prototype/contracts/`. 이번에 추가된 절은 `08b-questions.md`이고, 동기화 확인 명령은 그 폴더 README에 있다.

v1.3에서 바뀐 곳:

| 분할 파일 | 변경 |
|---|---|
| `01-common.md` | 변경 이력 v1.3, 에러 코드 `REFINEMENT_NOT_FOUND`, 시연 모드 표에 다듬기 행 |
| `08b-questions.md` (신규) | `POST /api/questions/refine`, `POST /api/questions/refine/{refinementId}/choice` |
| `09-summary.md` | 요약표 두 행 |

기존 엔드포인트의 요청·응답 shape는 바뀌지 않는다.
