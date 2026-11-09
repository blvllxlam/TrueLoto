-- Upgrade an existing TrueLoto D1 database to the virtual-wallet model.
-- Run once with: npx wrangler d1 migrations apply trueloto-db
-- Existing user and draw rows are retained. No real-money/payment data is used.

ALTER TABLE users ADD COLUMN updated_at TEXT;
ALTER TABLE users ADD COLUMN participation_amount_minor INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN winning_chance_basis_points INTEGER NOT NULL DEFAULT 0;

UPDATE users
SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP),
    participation_amount_minor = CAST(ROUND(COALESCE(participation_amount, 0) * 100) AS INTEGER),
    winning_chance_basis_points = CAST(ROUND(COALESCE(winning_chance, 0) * 10000) AS INTEGER);

CREATE TABLE IF NOT EXISTS wallets (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
  balance_minor INTEGER NOT NULL DEFAULT 0 CHECK (balance_minor >= 0),
  currency_code TEXT NOT NULL DEFAULT 'TST',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO wallets (user_id, balance_minor)
SELECT id, 0 FROM users;

CREATE TABLE IF NOT EXISTS wallet_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  amount_minor INTEGER NOT NULL CHECK (amount_minor <> 0),
  balance_after_minor INTEGER NOT NULL CHECK (balance_after_minor >= 0),
  transaction_type TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  reference_type TEXT,
  reference_id TEXT,
  description TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE draw_rounds ADD COLUMN status TEXT NOT NULL DEFAULT 'completed';
ALTER TABLE draw_rounds ADD COLUMN draw_datetime TEXT;
ALTER TABLE draw_rounds ADD COLUMN participant_limit INTEGER;
ALTER TABLE draw_rounds ADD COLUMN winner_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE draw_rounds ADD COLUMN created_at TEXT;
ALTER TABLE draw_rounds ADD COLUMN started_at TEXT;
ALTER TABLE draw_rounds ADD COLUMN finalized_at TEXT;
ALTER TABLE draw_rounds ADD COLUMN result_metadata_json TEXT;

UPDATE draw_rounds
SET created_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
    finalized_at = COALESCE(completed_at, CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS draw_participants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draw_round_id INTEGER NOT NULL REFERENCES draw_rounds(id) ON DELETE RESTRICT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  weight INTEGER NOT NULL DEFAULT 1 CHECK (weight > 0),
  entry_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (entry_amount_minor >= 0),
  status TEXT NOT NULL DEFAULT 'active',
  joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (draw_round_id, user_id)
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_created
  ON wallet_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_draw_rounds_status_created
  ON draw_rounds(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_draw_participants_round_status
  ON draw_participants(draw_round_id, status);
CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_created
  ON admin_audit_logs(created_at DESC);
