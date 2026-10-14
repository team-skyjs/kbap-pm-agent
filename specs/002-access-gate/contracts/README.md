# contracts/ — 002 접근 제한

이 기능은 계약의 **공통 절 문구만** 바꾼다. 응답 shape는 바뀌지 않는다. 계약은 제품 전체에 하나이므로 사본을 두지 않는다.

- 정본: `_workspace/01_cto_api-contract.md` v1.2
- 분할본: `specs/001-pm-agent-prototype/contracts/` (동기화 확인 명령은 그 폴더의 README)

v1.2에서 바뀐 절:

| 분할 파일 | 절 | 변경 |
|---|---|---|
| `01-common.md` | 변경 이력, 공통 | Base URL이 없어지고 같은 출처 상대 경로가 됐다. `X-Requested-With: XMLHttpRequest` 요청 헤더와 접근 계층 응답 규칙(세션 만료 판정)을 추가했고, 예시 호스트는 `pm-agent.example.com`이다 |
| `08-amplitude.md` | connect 예시, callback | 예시 `authorizationUrl`의 redirect_uri 호스트가 `pm-agent.example.com`이다. callback에 접근 계층 비고를 넣었다 |
| `09-summary.md` | CORS | CORS가 없다. 다른 출처 preflight는 허용하지 않는다 |

영향:
- **backend**: fake 모드 connect 응답과 `backend/checks/examples.py`의 예시 URL을 새 예시 값으로 맞춘다(계약 시연 모드 표: "예시 `authorizationUrl`을 그대로 응답"). CORS 미들웨어를 제거한다.
- **frontend**: `api.ts`의 Base URL 제거와 헤더·세션 만료 판정.
- **QA**: `check_b1`의 CORS 기대 반전, `check_b8` 갱신.
