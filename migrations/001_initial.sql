-- The reference backend applies the same idempotent schema from persistence.db.
-- This file is kept as an inspectable migration artifact for deployment tooling.
CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES ('001_initial', CURRENT_TIMESTAMP);
