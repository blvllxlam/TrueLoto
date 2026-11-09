# TrueLoto Telegram bot

Python Telegram bot for the TrueLoto test environment. The bot and Telegram Mini App use the same Cloudflare D1 database through the Worker API. The bot does not use a local SQLite database.

## Configuration

Create `.env` from `.env.example` and set:

- `BOT_TOKEN` — Telegram bot token; must match the Worker secret.
- `ADMIN_TELEGRAM_ID` — numeric Telegram ID of the administrator.
- `WORKER_API_URL` — deployed Worker base URL, without a trailing slash.
- `BOT_API_SECRET` — same private secret configured in the Worker as `BOT_API_SECRET`.
- `DRAW_DATETIME` — optional fallback display date.

Never commit `.env` or share `BOT_API_SECRET`. The bot sends private requests to the Worker using the `X-Bot-Api-Key` header.

## Install and run

From this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py main.py
```

## Test-mode behavior

- User profiles, language, participation status, draw settings and draw history are stored in Cloudflare D1 through the Worker.
- The admin panel is available with `/admin`; use `/myid` to get the Telegram ID for administrator configuration.
- The test draw uses participant weight `losses_count + 1`.
- No real payments or money transfers are supported. Payment-related buttons only simulate the test flow.
