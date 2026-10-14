# 배포 (홈서버)

운영 호스트명·서버 경로·ssh 별칭의 실제 값은 서버와 GitHub Secrets/Variables에서만 쓴다. 이 문서와 스크립트에는 `<운영 API 주소>`, `<서버 경로>` 같은 자리표시자와 환경변수 이름만 둔다.

main에 병합되면 `.github/workflows/deploy.yml`이 자동 배포한다.
- GitHub 러너가 레포 루트를 컨텍스트로 `backend/Dockerfile`을 빌드한다. 1단계가 `frontend/`를 빌드하고, 2단계 백엔드 이미지(`ghcr.io/<owner>/kbap-pm-agent`)가 그 정적 파일을 함께 담는다. 커밋 태그로 푸시한다.
- 홈서버의 self-hosted 러너가 `deploy/docker-compose.kbap-pm-agent.yml`로 pull·up 하고 `deploy/deploy.kbap-pm-agent.sh`가 헬스를 확인한다(`127.0.0.1:8001/api/health`, `127.0.0.1:8001/` 화면 HTML, 토큰 없는 `/api/conversations` 401).
- `backend/**`, `frontend/**`, `deploy/**` 변경 시에만 돈다.

화면과 API는 운영 호스트명 하나, 같은 출처다. 컨테이너 하나(FastAPI)가 `/api/*`를 처리하고 나머지 경로는 빌드된 프론트 정적 파일로 응답한다. 터널은 이 컨테이너로 연결하고, Cloudflare Access가 호스트 전체를 허용 목록으로 막는다. 공유 토큰(`ACCESS_TOKEN`)은 `/api/*`에만 걸린다(화면 파일은 브라우저가 토큰을 붙일 수 없어 제외).

운영 env 파일은 deploy job이 매번 GitHub Secrets/Variables에서 생성하고 끝나면 지운다. 서버에 키 파일을 두지 않는다. 운영 호스트명·서버 경로·접속 별칭은 이 레포에 쓰지 않는다(Variables·Secrets와 서버에만).

## 최초 1회 설정 (사람이 한다)

1. **self-hosted 러너 등록** (홈서버): 레포 Settings → Actions → Runners → New self-hosted runner. 러너 사용자가 docker 그룹에 있어야 한다.
2. **홈서버 MySQL에 DB·계정**: `docker exec -i <MySQL 컨테이너명> mysql -uroot -p < deploy/mysql-init.sql` (암호를 바꿔서)
3. **GitHub Secrets / Variables** (레포 Settings → Secrets and variables → Actions):

   | Secrets (비밀) | 내용 |
   |---|---|
   | `DATABASE_URL` | `mysql://kbap_pm:<비밀번호>@<MySQL 컨테이너명>:3306/kbap_pm_agent` (mysql-init.sql의 `kbap_pm` 계정) |
   | `ANTHROPIC_API_KEY` | Claude 키 |
   | `OPENAI_API_KEY` | GPT 쓸 때만. 없으면 빈 값 |
   | `GH_PAT` | 분석 대상 저장소 클론용 PAT (Contents: Read). env 파일에는 `GITHUB_TOKEN`으로 들어간다 |
   | `ACCESS_TOKEN` | API 공유 토큰. 전환 기간에는 운영 필수(비어 있으면 워크플로우와 배포 스크립트가 컨테이너 기동 전에 중단). Access 운영 검증이 끝난 뒤 끈다(토큰 끄기 단계: 워크플로우 필수 검사, 배포 스크립트 env 검증·토큰 잠금 확인, verify job의 `ACCESS_TOKEN` env를 함께 제거) |
   | `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET` | 배포 후 운영 검사(`check_b8.py`)용 Access 서비스 토큰 |

   | Variables (비밀 아님) | 값 |
   |---|---|
   | `PUBLIC_BASE_URL` | `https://<운영 호스트명>` (예: `https://pm-agent.example.com`). Amplitude OAuth 콜백 주소와 운영 검사 대상 |
   | `AMPLITUDE_MCP_URL` | `https://mcp.amplitude.com/mcp` |
   | `AGENT_MODEL`, `CODE_SUMMARY_MODEL`, `LLM_BUDGET_USD` | 생략 시 기본값(anthropic:claude-sonnet-5-5 / claude-haiku-5-5 / 200) |
4. **터널 규칙** (Zero Trust → Networks → Tunnels): 변경 없음. 운영 호스트명 → `http://kbap-pm-agent:8000`.
5. **Cloudflare Access** (Zero Trust → Access → Applications):
   - 운영 호스트명 전체(경로 비움)로 Self-hosted 애플리케이션. 로그인은 One-time PIN, 세션 24시간.
   - 정책 "Allow: Emails"에 허용 이메일. 이메일은 레포·대화 어디에도 적지 않는다.
   - 서비스 토큰(Access → Service credentials, 이름 `kbap-pm-agent-check`, 만료 1년)을 만들고 같은 애플리케이션에 정책 "Service Auth: 이 토큰"을 추가한다. 값은 Secrets `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`에.
6. **ghcr 패키지**: 첫 배포 후 Packages에 `kbap-pm-agent`가 생긴다. 비공개여도 deploy job이 GITHUB_TOKEN으로 로그인해 pull하므로 공개로 바꿀 필요 없다.

## 서비스 토큰 교체 (만료 1년)

1. Access → Service credentials에서 새 토큰 발급.
2. Access 애플리케이션의 "Service Auth" 정책에 새 토큰 추가.
3. GitHub Secrets `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`를 새 값으로 교체하고 `deploy` 워크플로우를 한 번 돌려 운영 검사 통과 확인.
4. 정책에서 옛 토큰을 빼고 옛 토큰 폐기.

## 배포 후 확인

배포 워크플로우의 `verify` job이 매 배포 뒤 `check_b8.py`를 바깥 경로로 실행한다. Secrets `CF_ACCESS_CLIENT_ID`·`CF_ACCESS_CLIENT_SECRET`가 비어 있으면 경고만 남기고 통과하고, 둘 다 들어가면 그때부터 검사 실패가 배포 실패가 된다.

수동 실행은 개발 PC에서 (`backend/`):
```bash
PUBLIC_BASE_URL=https://<운영 호스트명> CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... uv run python checks/check_b8.py
```

## 수동 배포 (폴백)

CI가 막혔을 때만. `deploy/kbap-pm-agent.env.example`을 레포 루트 `.env.prod`로 복사해 값을 채우고, 개발 PC에서 `docker login ghcr.io` 후:
```bash
IMAGE=ghcr.io/<owner>/kbap-pm-agent REMOTE_DIR=<서버 디렉토리> ./deploy/push-and-deploy.sh <ssh-host>
```

## 전제 확인 (홈서버, 사람이 실행)

```bash
docker network ls | grep monitor-net
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'mysql|8001'
```

전제: 네트워크 `monitor-net`, 호스트 포트 8001 비어 있음.
