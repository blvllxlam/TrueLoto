# TrueLoto

Telegram bot and Mini App test project. The bot and Mini App use the same Cloudflare D1 database through the Worker API.

## Architecture

- Telegram Mini App -> public Worker API -> D1
- Python Telegram bot -> private Worker API (shared secret) -> D1
- The bot must not use a local SQLite database as its application data store.
- This project is a test environment. No real payments or money transfers are supported.

## Configure the Worker

From the `worker` directory:

```powershell
npm install
npx wrangler secret put BOT_TOKEN
npx wrangler secret put BOT_API_SECRET
npx wrangler deploy
```

When prompted, enter the same Telegram bot token used by the bot and a long random value for `BOT_API_SECRET`. Keep the API secret private. Never put it in frontend code or commit it.

Apply the D1 migration only after checking the target database and taking a backup:

```powershell
npx wrangler d1 export trueloto-db --remote --output=./trueloto-before-migration.sql
npx wrangler d1 migrations apply trueloto-db --remote
```

The migration is intended to preserve existing D1 user and draw-history rows. It does not import the local SQLite test database.

The migration sequence includes an idempotent baseline (0001) and the D1 upgrade (0002). It can initialize a new database or upgrade the original schema. Keep `schema.sql` as the reference for the resulting current schema; do not execute it separately before applying migrations.

## Configure the Python bot

Copy `TrueLoto_bot/.env.example` to `TrueLoto_bot/.env` and fill in the values:

- `BOT_TOKEN`: Telegram bot token; must match the Worker secret.
- `ADMIN_TELEGRAM_ID`: Telegram numeric ID of the administrator.
- `WORKER_API_URL`: deployed Worker base URL, without a trailing slash.
- `BOT_API_SECRET`: same secret configured in the Worker.
- `DRAW_DATETIME`: optional display fallback used by the bot.

Install and start:

```powershell
cd TrueLoto_bot
py -m pip install -r requirements.txt
py main.py
```

The bot's user, language, participation, settings and draw operations are now routed through the Worker API. Keep the old local `trueloto.db` as a backup until the end-to-end test is complete.
