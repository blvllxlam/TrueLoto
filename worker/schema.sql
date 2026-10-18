-- Схема D1 для API Mini App. Основана на моделях существующего Python-бота.
-- Это отдельная облачная БД; локальная SQLite бота автоматически не синхронизируется.

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id INTEGER NOT NULL UNIQUE,
  username TEXT,
  first_name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_admin INTEGER NOT NULL DEFAULT 0,
  language_code TEXT,
  participation_status TEXT NOT NULL DEFAULT 'not_participating',
  participation_amount REAL NOT NULL DEFAULT 0,
  winning_chance REAL NOT NULL DEFAULT 0,
  wins_count INTEGER NOT NULL DEFAULT 0,
  losses_count INTEGER NOT NULL DEFAULT 0,
  payment_details TEXT,
  payment_status TEXT NOT NULL DEFAULT 'not_paid'
);

CREATE TABLE IF NOT EXISTS draw_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  draw_datetime TEXT,
  participant_limit INTEGER,
  status TEXT NOT NULL DEFAULT 'not_started'
);

INSERT OR IGNORE INTO draw_settings (id, draw_datetime, participant_limit, status)
VALUES (1, NULL, NULL, 'not_started');

CREATE TABLE IF NOT EXISTS draw_rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  winner_telegram_id INTEGER NOT NULL,
  participant_count INTEGER NOT NULL,
  total_weight INTEGER NOT NULL,
  completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
