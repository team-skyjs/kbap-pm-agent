-- 홈서버 기존 MySQL 컨테이너에서 root로 한 번 실행: docker exec -i <MySQL 컨테이너명> mysql -uroot -p < deploy/mysql-init.sql
-- 테이블은 앱 기동 시 backend/schema.sql로 만든다
CREATE DATABASE IF NOT EXISTS kbap_pm_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'kbap_pm'@'%' IDENTIFIED BY '<암호>';
GRANT ALL PRIVILEGES ON kbap_pm_agent.* TO 'kbap_pm'@'%';
FLUSH PRIVILEGES;
