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

CORS: 백엔드는 `CORS_ORIGINS`의 출처에 대해 위 메서드 전부와 `Authorization`, `Content-Type` 헤더의 preflight를 허용한다.
