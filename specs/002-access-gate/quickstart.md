# Quickstart: 접근 제한

```bash
docker compose up -d --build        # 레포 루트: backend(8000, /api와 빌드된 프론트를 함께 제공) + mysql(3307)
cd frontend && npm ci && npm run dev  # 개발용: http://localhost:5173 (Vite가 /api → localhost:8000 프록시)
```

같은 출처 확인은 `http://localhost:8000/`이다. 브라우저 개발자 도구의 네트워크 탭에서 모든 요청이 `localhost:8000/api/...`로 나가야 한다. 계약은 [contracts/README.md](./contracts/README.md)의 정본을 본다. 운영 호스트명은 문서에 쓰지 않으며, 아래 `$PUBLIC_BASE_URL`은 GitHub Variables의 값이다.

## 로컬 시나리오 (Access 없음, `AGENT_MODE=fake`)

| # | 하는 일 | 기대 결과 | 관련 |
|---|---|---|---|
| 1 | `bash deploy/checks/check_g1.sh` | `/`가 index.html, `/api/health`가 `{"status":"ok","db":"ok","version":"0.1.0"}`, 정적 자산 경로가 `/assets/`로 시작, SSE 첫 이벤트 5초 이내 | G1, FR-001 |
| 2 | `http://localhost:8000` 열고 질문 전송 | 진행 표시 → 제안 카드. 001 quickstart 시나리오 3~5와 같다 | FR-005 |
| 3 | `curl -si -X OPTIONS -H 'Origin: https://evil.example.com' -H 'Access-Control-Request-Method: POST' localhost:8000/api/conversations` | `access-control-allow-origin` 헤더 없음 | G3, US3-2 |
| 4 | `cd frontend && npm run check -- g2` | 세션 만료 판정 3종(401 비 JSON, opaqueredirect, 비 5xx text/html), 백엔드 401 JSON, 5xx HTML(연결 실패) 구분 | G2, FR-006 |

## 운영 확인 (사람 설정 T021·T024 이후, 터널 규칙은 변경 없음 T020)

1. 쿠키 없는 브라우저로 `$PUBLIC_BASE_URL`을 연다. Access 로그인 화면이 뜬다(US2-1).
2. 허용 이메일로 PIN 로그인을 하고, 질문·제안·설정·Amplitude 연결을 확인한다(US1, research R2).
3. 다음 명령을 실행한다(ADR-23).
   ```bash
   CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... PUBLIC_BASE_URL=... uv run python backend/checks/check_b8.py
   ```
   토큰이 있으면 `/`, `/api/health`, SSE 100초가 통과하고, 토큰이 없으면 거부되며, 다른 출처 preflight는 거부된다.
4. 옛 Pages 주소를 열면 404다(US3-1).
5. 허용되지 않은 호출 시각에 백엔드 로그(`docker logs kbap-pm-agent`)에 해당 요청이 없다(US2-2, SC-001).
