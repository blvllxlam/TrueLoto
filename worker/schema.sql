-- TrueLoto D1 schema (fresh database).
-- All balances and monetary amounts are integer minor units; no real payments.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id TEXT NOT NULL UNIQUE,
  username TEXT,
  first_name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
  language_code TEXT,
  payment_status TEXT NOT NULL DEFAULT 'not_paid',
  participation_status TEXT NOT NULL DEFAULT 'not_participating',
  participation_amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (participation_amount_minor >= 0),
  winning_chance_basis_points INTEGER NOT NULL DEFAULT 0 CHECK (winning_chance_basis_points >= 0),
  wins_count INTEGER NOT NULL DEFAULT 0 CHECK (wins_count >= 0),
  losses_count INTEGER NOT NULL DEFAULT 0 CHECK (losses_count >= 0)
);

CREATE TABLE IF NOT EXISTS wallets (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
  balance_minor INTEGER NOT NULL DEFAULT 0 CHECK (balance_minor >= 0),
  currency_code TEXT NOT NULL DEFAULT 'TST',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS draw_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  draw_datetime TEXT,
  participant_limit INTEGER CHECK (participant_limit IS NULL OR participant_limit > 0),
  status TEXT NOT NULL DEFAULT 'not_started'
);

INSERT OR IGNORE INTO draw_settings (id, draw_datetime, participant_limit, status)
VALUES (1, NULL, NULL, 'not_started');

CREATE TABLE IF NOT EXISTS draw_rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status TEXT NOT NULL DEFAULT 'created',
  draw_datetime TEXT,
  participant_limit INTEGER,
  participant_count INTEGER NOT NULL DEFAULT 0 CHECK (participant_count >= 0),
  total_weight INTEGER NOT NULL DEFAULT 0 CHECK (total_weight >= 0),
  winner_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
  winner_telegram_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  completed_at TEXT,
  finalized_at TEXT,
  result_metadata_json TEXT
);

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
