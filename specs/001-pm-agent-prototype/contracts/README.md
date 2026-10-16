# contracts/ — API 계약서 분할본

원본은 `_workspace/01_cto_api-contract.md`(v1.4)다. 이 폴더의 `01`~`09` 파일(`08b`·`08c` 포함)은 원본을 장 경계에서 자른 것이며, 내용을 한 글자도 바꾸지 않았다(헌법 원칙 I).

| 파일 | 범위 |
|---|---|
| `01-common.md` | 변경 이력, 공통 규칙, 에러 형식, 시연 모드, SSE 형식 |
| `02-objects.md` | ConversationSummary, Message, Proposal, Settings |
| `03-health.md` | `GET /api/health` |
| `04-conversations.md` | `GET /api/conversations`, `POST /api/conversations`, `GET /api/conversations/{conversationId}` |
| `05-messages.md` | `POST /api/conversations/{conversationId}/messages` (SSE) |
| `06-proposals.md` | `PATCH /api/proposals/{proposalId}` |
| `07-settings.md` | `GET /api/settings`, `PUT /api/settings/repository`, `POST /api/settings/repository/sync`, `PUT /api/settings/taxonomy` |
| `08-amplitude.md` | `POST /api/integrations/amplitude/connect`, `GET /api/integrations/amplitude/callback` |
| `08b-questions.md` | `POST /api/questions/refine`, `POST /api/questions/refine/{refinementId}/choice` (v1.3, 질문 마법사) |
| `08c-exports.md` | `POST /api/conversations/{conversationId}/exports` (v1.4, 대화 내보내기 기록) |
| `09-summary.md` | 엔드포인트 요약표, CORS |

동기화 확인(레포 루트에서, 출력이 없어야 한다):

```bash
cat specs/001-pm-agent-prototype/contracts/0*.md | diff - _workspace/01_cto_api-contract.md
```

계약 변경 절차: CTO가 원본을 먼저 고치고, 이 폴더를 다시 자른 뒤 위 명령으로 확인한다. 이 폴더만 고치는 것은 금지한다.
