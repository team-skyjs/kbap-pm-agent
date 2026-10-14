## 엔드포인트

### GET /api/health
- 용도: 서버·DB 생존 확인. 인증 불필요.
- 응답 200:
```json
{"status": "ok", "db": "ok", "version": "0.1.0"}
```
- DB 연결 실패 시에도 200으로 `{"status": "degraded", "db": "error", "version": "0.1.0"}`. 서버가 떠 있는지와 DB 상태를 분리해 보여주기 위함이다.

