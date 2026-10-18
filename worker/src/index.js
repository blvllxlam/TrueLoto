const TEST_RULES =
  "Правила TrueLoto будут опубликованы перед запуском первого раунда. Сейчас Mini App находится в тестовом режиме. Платежи не принимаются.";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "Content-Type, X-Telegram-Init-Data",
    },
  });
}

function hex(buffer) {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function hmac(keyBytes, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message)));
}

async function validateTelegramInitData(initData, botToken) {
  if (!initData || !botToken) return null;

  const params = new URLSearchParams(initData);
  const receivedHash = params.get("hash");
  const authDate = Number(params.get("auth_date"));
  if (!receivedHash || !Number.isFinite(authDate)) return null;

  // Не принимаем initData старше 24 часов.
  const now = Math.floor(Date.now() / 1000);
  if (authDate > now + 60 || now - authDate > 86400) return null;

  params.delete("hash");
  params.delete("signature");
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");

  const secretKey = await hmac(new TextEncoder().encode(botToken), "WebAppData");
  const calculatedHash = hex(await hmac(secretKey, dataCheckString));

  if (calculatedHash.length !== receivedHash.length) return null;
  const a = new TextEncoder().encode(calculatedHash);
  const b = new TextEncoder().encode(receivedHash);
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  if (diff !== 0) return null;

  try {
    const user = JSON.parse(params.get("user") || "null");
    if (!user || !Number.isSafeInteger(user.id)) return null;
    return user;
  } catch {
    return null;
  }
}

async function requireTelegramUser(request, env) {
  const initData = request.headers.get("X-Telegram-Init-Data");
  const user = await validateTelegramInitData(initData, env.BOT_TOKEN);
  return user;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204 });
    const url = new URL(request.url);

    if (url.pathname === "/api/health" && request.method === "GET") {
      return json({ ok: true, service: "trueloto-api" });
    }

    if (!url.pathname.startsWith("/api/")) return json({ error: "Not found" }, 404);

    const tgUser = await requireTelegramUser(request, env);
    if (!tgUser) return json({ error: "Telegram authentication failed. Open this app inside Telegram." }, 401);

    if (url.pathname === "/api/me" && request.method === "GET") {
      const telegramId = String(tgUser.id);
      await env.DB.prepare(
        `INSERT INTO users (telegram_id, username, first_name, language_code)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(telegram_id) DO UPDATE SET
           username = excluded.username,
           first_name = excluded.first_name,
           language_code = COALESCE(users.language_code, excluded.language_code)`
      ).bind(telegramId, tgUser.username || null, tgUser.first_name || "Telegram user",
        (tgUser.language_code || "ru").slice(0, 2)).run();

      const user = await env.DB.prepare(
        `SELECT first_name, created_at, language_code, participation_status,
                winning_chance, wins_count, losses_count
         FROM users WHERE telegram_id = ?`
      ).bind(telegramId).first();

      return json({
        user: {
          ...user,
          winning_chance_percent: (Number(user.winning_chance || 0) * 100).toFixed(2) + "%",
        },
      });
    }

    if (url.pathname === "/api/draw" && request.method === "GET") {
      const draw = await env.DB.prepare(
        "SELECT draw_datetime, participant_limit, status FROM draw_settings WHERE id = 1"
      ).first();
      const count = await env.DB.prepare(
        "SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'"
      ).first();
      return json({ draw: draw || { draw_datetime: null, participant_limit: null, status: "not_started" }, participant_count: count.count });
    }

    if (url.pathname === "/api/rules" && request.method === "GET") {
      return json({ rules: TEST_RULES, test_mode: true });
    }

    if (url.pathname === "/api/participation" && request.method === "POST") {
      // Участие намеренно выключено: платежей в тестовой версии нет.
      return json({ error: "Участие пока недоступно. Это тестовая версия без платежей." }, 409);
    }

    return json({ error: "Not found" }, 404);
  },
};
