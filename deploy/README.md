# 배포 (홈서버, ADR-11)

1. 홈서버 MySQL에 DB·계정: `docker exec -i mysql-prod mysql -uroot -p < deploy/mysql-init.sql` (암호를 바꿔서)
2. `cp deploy/kbap-pm-agent.env.example .env.prod` 후 값 입력
3. 개발 PC에서 `./deploy/push-and-deploy.sh` (buildx 멀티아키 빌드·푸시 → 서버 전송 → pull·up·health)
4. cloudflared ingress: `pm-agent-api.simhani1.dev` → `http://kbap-pm-agent:8000`
5. 확인: `PUBLIC_BASE_URL=https://pm-agent-api.simhani1.dev uv run python checks/check_b8.py` (backend/에서)

## research.md R4 확인 결과

2026-10-15 기준 미확인. 홈서버 접근이 없어 아래를 실행하지 못했다. 배포 전에 사람이 실행해 결과를 여기에 붙인다.

```bash
docker network ls | grep monitor-net
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'mysql|8001'
```

전제: 레포 `kbap-pm-agent`, Docker Hub `simhani1/kbap-pm-agent`, MySQL 컨테이너명 `mysql-prod`(kbap-amplitude env 기준), 네트워크 `monitor-net`, 호스트 포트 8001 비어 있음.
