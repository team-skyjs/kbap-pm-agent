### PATCH /api/proposals/{proposalId}
- 용도: 제안 채택·보류·메모.
- 요청:
```json
{"status": "adopted", "note": "KB-812로 이번 스프린트에 진행"}
```
  - `status`: `"pending"` | `"adopted"` | `"on_hold"`, 필수.
  - `note`: 문자열(최대 1000자) 또는 `null`. 키를 생략하면 기존 메모를 유지하고, `null`이면 지운다.
- 응답 200: 갱신된 Proposal 전체(위 Proposal shape).
- 에러: `VALIDATION_ERROR`, `PROPOSAL_NOT_FOUND`.

