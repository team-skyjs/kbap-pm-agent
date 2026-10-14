## 엔드포인트 요약

| 메서드 | 경로 | 인증 | 응답 |
|---|---|---|---|
| GET | `/api/health` | 불필요 | JSON |
| GET | `/api/conversations` | 필요 | JSON |
| POST | `/api/conversations` | 필요 | JSON 201 |
| GET | `/api/conversations/{conversationId}` | 필요 | JSON |
| POST | `/api/conversations/{conversationId}/messages` | 필요 | SSE |
| PATCH | `/api/proposals/{proposalId}` | 필요 | JSON |
| GET | `/api/settings` | 필요 | JSON |
| PUT | `/api/settings/repository` | 필요 | JSON |
| POST | `/api/settings/repository/sync` | 필요 | JSON |
| PUT | `/api/settings/taxonomy` | 필요 | JSON |
| POST | `/api/integrations/amplitude/connect` | 필요 | JSON |
| GET | `/api/integrations/amplitude/callback` | 불필요 | HTML |

CORS: 없음. 프론트와 같은 출처에서만 호출한다. 백엔드는 CORS 헤더를 보내지 않으며, 다른 출처의 preflight는 허용되지 않는다.
