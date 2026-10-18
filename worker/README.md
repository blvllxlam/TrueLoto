# TrueLoto Mini App — initial scaffold

Ветка: `mini-app`. Существующий Python-бот не менялся.

## Что добавлено
- `web/index.html` — первый экран Telegram Mini App.
- `worker/src/index.js` — API с проверкой Telegram `initData`.
- `worker/schema.sql` — схема Cloudflare D1.
- `worker/wrangler.toml` — конфигурация Worker и привязка к созданной D1.

## Важно
D1 — отдельная облачная база. Она пока не синхронизирована с локальной SQLite бота. Реальные платежи и участие отключены.

## Дальнейшее развёртывание (PowerShell, из корня репозитория)

1. Установить секрет токена бота в Worker:
   `npx.cmd wrangler@latest secret put BOT_TOKEN --config worker/wrangler.toml`
   Вставь токен в интерактивный запрос Wrangler. Не сохраняй токен в Git.

2. Создать таблицы в удалённой D1:
   `npx.cmd wrangler@latest d1 execute trueloto-db --remote --file=worker/schema.sql --config worker/wrangler.toml`

3. Опубликовать API:
   `npx.cmd wrangler@latest deploy --config worker/wrangler.toml`
   Сохрани выданный URL Worker вида `https://trueloto-api.<subdomain>.workers.dev`.

4. В `web/index.html` замени `https://YOUR-WORKER-SUBDOMAIN.workers.dev` в `API_BASE` на фактический URL Worker и сохрани файл.

5. Создай Pages project и опубликуй frontend:
   `npx.cmd wrangler@latest pages project create trueloto-mini-app`
   `npx.cmd wrangler@latest pages deploy web --project-name trueloto-mini-app`

6. Открой выданный Pages URL внутри Telegram Web App. Для реального теста нужен настроенный URL кнопки Mini App в BotFather или в клавиатуре бота.

## API
- `GET /api/health` — проверка доступности Worker, без Telegram-авторизации.
- `GET /api/me` — создать/прочитать профиль пользователя из D1.
- `GET /api/draw` — настройки текущего розыгрыша и число участников.
- `GET /api/rules` — правила тестового режима.
- `POST /api/participation` — намеренно возвращает статус «недоступно», платежей нет.

## Безопасность
- API проверяет подпись Telegram `initData` и ограничивает её возраст 24 часами.
- `BOT_TOKEN` должен храниться только как Worker secret.
- Не подключай реальный сбор платежей до отдельного проектирования и проверки требований.
