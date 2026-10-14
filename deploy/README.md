# 배포 (홈서버, ADR-11)

main에 병합되면 자동 배포된다.
- 백엔드: `.github/workflows/deploy-backend.yml` — GitHub 러너가 `backend/`를 이미지로 빌드해 `ghcr.io/team-skyjs/kbap-pm-agent:<커밋해시>`로 푸시 → 홈서버의 self-hosted 러너가 `deploy/docker-compose.kbap-pm-agent.yml`로 pull·up·헬스체크. `backend/**`, `deploy/**` 변경 시에만 돈다.
- 프론트: `.github/workflows/pages.yml` — `frontend/**` 변경 시 GitHub Pages로 배포.

운영 env 파일은 deploy job이 매번 GitHub Secrets/Variables에서 생성하고 끝나면 지운다. 서버에 키 파일을 두지 않는다.

## 최초 1회 설정 (사람이 한다)

1. **self-hosted 러너 등록** (홈서버): 레포 Settings → Actions → Runners → New self-hosted runner. 라벨은 기본 `self-hosted`면 된다. 러너 사용자가 docker 그룹에 있어야 한다. techmoa 러너가 같은 서버면 그 러너를 이 레포에도 등록하거나 org 러너로 공유한다.
2. **홈서버 MySQL에 DB·계정**: `docker exec -i mysql-prod mysql -uroot -p < deploy/mysql-init.sql` (암호를 바꿔서)
3. **GitHub Secrets / Variables** (레포 Settings → Secrets and variables → Actions):

   | Secrets (비밀) | 내용 |
   |---|---|
   | `DATABASE_URL` | `mysql://kbap_pm:<비밀번호>@mysql-prod:3306/kbap_pm_agent` (mysql-init.sql의 `kbap_pm` 계정, `<암호>` 자리에 넣은 값) |
   | `ANTHROPIC_API_KEY` | Claude 키 |
   | `OPENAI_API_KEY` | GPT 쓸 때만. 없으면 빈 값 |
   | `GH_PAT` | kbap-fe 클론용 PAT (Contents: Read). env 파일에는 `GITHUB_TOKEN`으로 들어간다 |
   | `ACCESS_TOKEN` | 공개 API 잠금. 비우면 꺼짐 |

   | Variables (비밀 아님) | 값 |
   |---|---|
   | `PUBLIC_BASE_URL` | `https://<운영 API 주소>` |
   | `CORS_ORIGINS` | `https://team-skyjs.github.io` |
   | `AMPLITUDE_MCP_URL` | `https://mcp.amplitude.com/mcp` |
   | `AGENT_MODEL`, `CODE_SUMMARY_MODEL`, `LLM_BUDGET_USD` | 생략 시 기본값(anthropic:claude-sonnet-5-5 / claude-haiku-5-5 / 200) |
   | `VITE_API_BASE_URL` | 프론트 빌드용. `PUBLIC_BASE_URL`과 같은 값 |
4. **cloudflared ingress**: `<운영 API 호스트명>` → `http://kbap-pm-agent:8000` (같은 `monitor-net`)
5. **GitHub Pages**: 레포 Settings → Pages → Source "GitHub Actions". Settings → Variables → `VITE_API_BASE_URL=https://<운영 API 주소>`
6. **ghcr 패키지**: 첫 배포 후 Packages에 `kbap-pm-agent`가 생긴다. 비공개여도 deploy job이 GITHUB_TOKEN으로 로그인해 pull하므로 공개로 바꿀 필요 없다.

## 배포 후 확인

개발 PC의 레포 안에서 (`backend/`):
```bash
PUBLIC_BASE_URL=https://<운영 API 주소> uv run python checks/check_b8.py
```
기대 출처를 git remote에서 계산하므로 레포 밖(컨테이너)에서는 `EXPECTED_ORIGIN=https://team-skyjs.github.io`를 직접 줘야 하고, 그 값이 틀리면 사본 오류를 못 잡는다.

## 수동 배포 (폴백)

CI가 막혔을 때만. `deploy/kbap-pm-agent.env.example`을 `.env.prod`로 복사해 값을 채우고, 개발 PC에서 `docker login ghcr.io` 후 `./deploy/push-and-deploy.sh [ssh-host]`.

## research.md R4 확인 결과

2026-10-15 기준 미확인. 홈서버 접근이 없어 아래를 실행하지 못했다. 러너 등록 전에 사람이 실행해 결과를 여기에 붙인다.

```bash
docker network ls | grep monitor-net
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'mysql|8001'
```

전제: 레포 `team-skyjs/kbap-pm-agent`, 이미지 `ghcr.io/team-skyjs/kbap-pm-agent`, MySQL 컨테이너명 `mysql-prod`(kbap-amplitude env 기준), 네트워크 `monitor-net`, 호스트 포트 8001 비어 있음.
