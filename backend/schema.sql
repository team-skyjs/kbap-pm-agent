-- 기동 시 app/db.py가 실행. 변경은 이 파일 끝에 ALTER 추가 후 수동 적용.
-- 시각은 UTC (연결마다 time_zone='+00:00').

CREATE TABLE IF NOT EXISTS conversations (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id BIGINT NOT NULL,
  role ENUM('user','assistant') NOT NULL,
  status ENUM('running','completed','failed') NOT NULL,
  content MEDIUMTEXT NOT NULL,
  error_code VARCHAR(50) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_conv (conversation_id, created_at),
  CONSTRAINT fk_msg_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tool_calls (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  message_id BIGINT NOT NULL,
  seq INT NOT NULL,
  source ENUM('amplitude','code','taxonomy') NOT NULL,
  name VARCHAR(100) NOT NULL,
  input_json JSON NOT NULL,
  status ENUM('running','succeeded','failed') NOT NULL,
  result_summary VARCHAR(1000) NULL,
  result_text MEDIUMTEXT NULL,
  duration_ms INT NULL,
  started_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_msg (message_id, seq),
  CONSTRAINT fk_tc_msg FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS proposals (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  message_id BIGINT NOT NULL,
  conversation_id BIGINT NOT NULL,
  seq INT NOT NULL,
  type ENUM('improvement','funnel_design') NOT NULL,
  title VARCHAR(200) NOT NULL,
  evidence_json JSON NOT NULL,
  proposal_text TEXT NOT NULL,
  steps_json JSON NOT NULL,
  measurement_json JSON NOT NULL,
  decision_status ENUM('pending','adopted','on_hold') NOT NULL DEFAULT 'pending',
  decision_note TEXT NULL,
  decided_at DATETIME(3) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_msg (message_id, seq),
  INDEX idx_conv (conversation_id),
  CONSTRAINT fk_p_msg FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
  CONSTRAINT fk_p_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS llm_usage (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  message_id BIGINT NULL,
  purpose ENUM('agent','code_summary','refine') NOT NULL,
  model VARCHAR(100) NOT NULL,
  input_tokens INT NOT NULL,
  output_tokens INT NOT NULL,
  cost_usd DECIMAL(10,4) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_msg (message_id),
  CONSTRAINT fk_u_msg FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS app_settings (
  k VARCHAR(100) PRIMARY KEY,
  v JSON NOT NULL,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 질문 다듬기 1회 = 1행. 모델 호출이 실패하면 행을 만들지 않음. choice는 사용자가 카드를 닫을 때 기록(덮어쓰기 허용)
CREATE TABLE IF NOT EXISTS question_refinements (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id BIGINT NULL,
  original_question TEXT NOT NULL,
  refined_question TEXT NOT NULL,
  summary VARCHAR(300) NOT NULL,
  model VARCHAR(100) NOT NULL,
  choice ENUM('refined','original','cancelled') NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  chosen_at DATETIME(3) NULL,
  INDEX idx_choice (choice),
  CONSTRAINT fk_qr_conv FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
