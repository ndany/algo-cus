-- sql/migrations/002_telemetry.sql
-- Usage telemetry and access attempt tracking

CREATE TABLE IF NOT EXISTS usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    user_name TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_log_email ON usage_log(user_email);
CREATE INDEX IF NOT EXISTS idx_usage_log_action ON usage_log(action);

CREATE TABLE IF NOT EXISTS access_attempts (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    attempt_type TEXT NOT NULL,
    code_provided TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_attempts_email ON access_attempts(email);
