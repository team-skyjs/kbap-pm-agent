# 배포 (홈서버, ADR-11)

main에 병합되면 자동 배포된다.
- 백엔드: `.github/workflows/deploy-backend.yml` — GitHub 러너가 `backend/`를 이미지로 빌드해 `ghcr.io/team-skyjs/kbap-pm-agent:<커밋해시>`로 푸시 → 홈서버의 self-hosted 러너가 `deploy/docker-compose.kbap-pm-agent.yml`로 pull·up·헬스체크. `backend/**`, `deploy/**` 변경 시에만 돈다.
- 프론트: `.github/workflows/pages.yml` — `frontend/**` 변경 시 GitHub Pages로 배포.

비밀값은 GitHub에 두지 않는다. 백엔드 키는 홈서버의 env 파일 하나에만 있다.

## 최초 1회 설정 (사람이 한다)

1. **self-hosted 러너 등록** (홈서버): 레포 Settings → Actions → Runners → New self-hosted runner. 라벨은 기본 `self-hosted`면 된다. 러너 사용자가 docker 그룹에 있어야 한다. techmoa 러너가 같은 서버면 그 러너를 이 레포에도 등록하거나 org 러너로 공유한다.
2. **홈서버 MySQL에 DB·계정**: `docker exec -i mysql-prod mysql -uroot -p < deploy/mysql-init.sql` (암호를 바꿔서)
3. **서버 env 파일**: `deploy/kbap-pm-agent.env.example`을 홈서버 `/home/simhani1/files/kbap-pm-agent.env`로 복사해 값 입력, `chmod 600`. CI는 이 파일을 읽기만 한다.
4. **cloudflared ingress**: `pm-agent-api.simhani1.dev` → `http://kbap-pm-agent:8000` (같은 `monitor-net`)
5. **GitHub Pages**: 레포 Settings → Pages → Source "GitHub Actions". Settings → Variables → `VITE_API_BASE_URL=https://pm-agent-api.simhani1.dev`
6. **ghcr 패키지**: 첫 배포 후 Packages에 `kbap-pm-agent`가 생긴다. 비공개여도 deploy job이 GITHUB_TOKEN으로 로그인해 pull하므로 공개로 바꿀 필요 없다.

## 배포 후 확인

개발 PC의 레포 안에서 (`backend/`):
```bash
PUBLIC_BASE_URL=https://pm-agent-api.simhani1.dev uv run python checks/check_b8.py
```
기대 출처를 git remote에서 계산하므로 레포 밖(컨테이너)에서는 `EXPECTED_ORIGIN=https://team-skyjs.github.io`를 직접 줘야 하고, 그 값이 틀리면 사본 오류를 못 잡는다.

## 수동 배포 (폴백)

CI가 막혔을 때만. 개발 PC에서 `docker login ghcr.io` 후 `./deploy/push-and-deploy.sh [ssh-host]`.

## research.md R4 확인 결과

2026-10-15 기준 미확인. 홈서버 접근이 없어 아래를 실행하지 못했다. 러너 등록 전에 사람이 실행해 결과를 여기에 붙인다.

```bash
docker network ls | grep monitor-net
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'mysql|8001'
```

전제: 레포 `team-skyjs/kbap-pm-agent`, 이미지 `ghcr.io/team-skyjs/kbap-pm-agent`, MySQL 컨테이너명 `mysql-prod`(kbap-amplitude env 기준), 네트워크 `monitor-net`, 호스트 포트 8001 비어 있음.
