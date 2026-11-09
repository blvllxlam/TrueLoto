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
  return validateTelegramInitData(
    request.headers.get("X-Telegram-Init-Data"),
    env.BOT_TOKEN,
  );
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET, POST, OPTIONS",
          "access-control-allow-headers": "Content-Type, X-Telegram-Init-Data",
          "access-control-max-age": "86400",
        },
      });
    }

    const url = new URL(request.url);

    if (url.pathname === "/api/health" && request.method === "GET") {
      return json({ ok: true, service: "trueloto-api", test_mode: true });
    }

    if (!url.pathname.startsWith("/api/") && !url.pathname.startsWith("/internal/")) return json({ error: "Not found" }, 404);

    // Private bot-to-Worker API. Never expose BOT_API_SECRET to Mini App clients.
    if (url.pathname.startsWith("/internal/")) {
      const supplied = request.headers.get("X-Bot-Api-Key") || "";
      const expected = env.BOT_API_SECRET || "";
      if (!expected || supplied.length !== expected.length) {
        return json({ error: "Unauthorized" }, 401);
      }
      let keyDiff = 0;
      for (let i = 0; i < supplied.length; i++) keyDiff |= supplied.charCodeAt(i) ^ expected.charCodeAt(i);
      if (keyDiff !== 0) return json({ error: "Unauthorized" }, 401);

      const readBody = async () => {
        try { return await request.json(); } catch { return null; }
      };
      const userByTelegramId = async (id) => env.DB.prepare(
        "SELECT * FROM users WHERE telegram_id = ?"
      ).bind(String(id)).first();
      const serializeUser = (u) => u ? ({
        id: u.id, telegram_id: String(u.telegram_id), username: u.username,
        first_name: u.first_name, created_at: u.created_at, is_admin: Boolean(u.is_admin),
        language_code: u.language_code, participation_status: u.participation_status,
        participation_amount: Number(u.participation_amount_minor || 0) / 100,
        winning_chance: Number(u.winning_chance_basis_points || 0) / 10000,
        wins_count: u.wins_count, losses_count: u.losses_count,
        payment_status: u.payment_status || "not_paid",
      }) : null;

      if (url.pathname === "/internal/users/upsert" && request.method === "POST") {
        const body = await readBody();
        if (!body || !/^\d{1,20}$/.test(String(body.telegram_id || "")) || !body.first_name) {
          return json({ error: "Invalid user profile" }, 400);
        }
        const id = String(body.telegram_id);
        await env.DB.prepare(
          `INSERT INTO users (telegram_id, username, first_name, language_code, is_admin)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(telegram_id) DO UPDATE SET
             username = excluded.username, first_name = excluded.first_name,
             is_admin = excluded.is_admin, updated_at = CURRENT_TIMESTAMP`,
        ).bind(id, body.username || null, String(body.first_name).slice(0, 255),
          body.language_code || null, body.is_admin === true ? 1 : 0).run();
        await env.DB.prepare(
          "INSERT OR IGNORE INTO wallets (user_id, balance_minor) SELECT id, 0 FROM users WHERE telegram_id = ?"
        ).bind(id).run();
        return json({ user: serializeUser(await userByTelegramId(id)), created: true });
      }

      if (url.pathname === "/internal/users/get" && request.method === "POST") {
        const body = await readBody();
        if (!body?.telegram_id) return json({ error: "telegram_id required" }, 400);
        return json({ user: serializeUser(await userByTelegramId(body.telegram_id)) });
      }

      if (url.pathname === "/internal/users/list" && request.method === "GET") {
        const rows = await env.DB.prepare("SELECT * FROM users ORDER BY created_at DESC").all();
        return json({ users: (rows.results || []).map(serializeUser) });
      }

      if (url.pathname === "/internal/users/update" && request.method === "POST") {
        const body = await readBody();
        const allowed = new Set(["language_code", "participation_status", "payment_status"]);
        if (!body?.telegram_id || !allowed.has(body.field)) return json({ error: "Invalid update" }, 400);
        const value = String(body.value ?? "");
        if (value.length > 100) return json({ error: "Value too long" }, 400);
        const result = await env.DB.prepare(
          `UPDATE users SET ${body.field} = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?`
        ).bind(value, String(body.telegram_id)).run();
        return json({ ok: result.meta.changes > 0 });
      }

      if (url.pathname === "/internal/draw/settings" && request.method === "GET") {
        const settings = await env.DB.prepare("SELECT * FROM draw_settings WHERE id = 1").first();
        return json({ settings: settings || { id: 1, draw_datetime: null, participant_limit: null, status: "not_started" } });
      }

      if (url.pathname === "/internal/draw/settings" && request.method === "POST") {
        const body = await readBody();
        if (!body || !["draw_datetime", "participant_limit"].includes(body.field)) {
          return json({ error: "Invalid setting" }, 400);
        }
        if (body.field === "participant_limit" && (!Number.isInteger(body.value) || body.value < 1)) {
          return json({ error: "participant_limit must be a positive integer" }, 400);
        }
        const result = await env.DB.prepare(
          `UPDATE draw_settings
           SET ${body.field} = ?, status = 'not_started'
           WHERE id = 1
             AND status NOT IN ('started', 'finalizing')
             AND (? <> 'participant_limit' OR ? >= (
               SELECT COUNT(*) FROM users WHERE participation_status = 'waiting_draw'
             ))`
        ).bind(body.value ?? null, body.field, body.value ?? null).run();
        if (result.meta.changes !== 1) {
          return json({
            error: "Настройки нельзя изменить: розыгрыш уже запущен или лимит меньше числа записанных участников."
          }, 409);
        }
        return json({ ok: true });
      }

      if (url.pathname === "/internal/draw/waiting-count" && request.method === "GET") {
        const row = await env.DB.prepare(
          "SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'"
        ).first();
        return json({ count: row.count });
      }

      if (url.pathname === "/internal/draw/start" && request.method === "POST") {
        const result = await env.DB.prepare(
          "UPDATE draw_settings SET status = 'started' WHERE id = 1 AND status = 'not_started'"
        ).run();
        if (!result.meta.changes) return json({ error: "Draw is already started, finalizing, completed, or settings are missing" }, 409);
        return json({ ok: true });
      }

      if (url.pathname === "/internal/draw/run" && request.method === "POST") {
        const settings = await env.DB.prepare("SELECT * FROM draw_settings WHERE id = 1").first();
        const rows = await env.DB.prepare(
          "SELECT * FROM users WHERE participation_status = 'waiting_draw' ORDER BY id"
        ).all();
        const participants = rows.results || [];
        if (!settings || settings.status !== "started") return json({ error: "Draw is not started" }, 409);
        if (!settings.participant_limit || participants.length !== settings.participant_limit) {
          return json({ error: "Participant count does not match the configured limit" }, 409);
        }

        const weights = participants.map((u) => Number(u.losses_count || 0) + 1);
        const totalWeight = weights.reduce((sum, n) => sum + n, 0);
        let ticket = crypto.getRandomValues(new Uint32Array(1))[0] / 0x100000000 * totalWeight;
        let winnerIndex = 0;
        for (let i = 0; i < weights.length; i++) {
          ticket -= weights[i];
          if (ticket < 0) { winnerIndex = i; break; }
        }
        const winner = participants[winnerIndex];
        const now = new Date().toISOString();
        const roundId = Date.now() * 1000 + (crypto.getRandomValues(new Uint32Array(1))[0] % 1000);
        // Claim the draw in a standalone conditional update. Only one concurrent
        // request can move the state from started to finalizing.
        const claim = await env.DB.prepare(
          "UPDATE draw_settings SET status = 'finalizing' WHERE id = 1 AND status = 'started'"
        ).run();
        if (claim.meta.changes !== 1) {
          return json({ error: "Draw is already being finalized or is no longer started" }, 409);
        }
        // Read decliners only after claiming the round: new declines are now
        // blocked by the started state, so this list cannot miss a late opt-out.
        const declinedRows = await env.DB.prepare(
          "SELECT telegram_id, first_name, language_code FROM users WHERE participation_status = 'declined_for_karma' ORDER BY id"
        ).all();
        const declinedUsers = declinedRows.results || [];

        const statements = [
          env.DB.prepare(
            `INSERT INTO draw_rounds
             (id, status, draw_datetime, participant_limit, participant_count, total_weight,
              winner_user_id, winner_telegram_id, created_at, started_at, completed_at, finalized_at)
             SELECT ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
             WHERE EXISTS (SELECT 1 FROM draw_settings WHERE id = 1 AND status = 'finalizing')`
          ).bind(roundId, settings.draw_datetime, settings.participant_limit, participants.length,
            totalWeight, winner.id, String(winner.telegram_id), now, now, now, now),
        ];

        for (let i = 0; i < participants.length; i++) {
          const u = participants[i];
          statements.push(env.DB.prepare(
            `INSERT INTO draw_participants (draw_round_id, user_id, weight, status, joined_at)
             SELECT ?, ?, ?, 'completed', ?
             WHERE EXISTS (SELECT 1 FROM draw_rounds WHERE id = ?)`
          ).bind(roundId, u.id, weights[i], now, roundId));
          statements.push(env.DB.prepare(
            `UPDATE users SET
              winning_chance_basis_points = ?, participation_status = 'not_participating',
              payment_status = 'not_paid',
              wins_count = CASE WHEN id = ? THEN wins_count + 1 ELSE wins_count END,
              losses_count = CASE WHEN id = ? THEN 0 ELSE losses_count + 1 END,
              updated_at = CURRENT_TIMESTAMP
             WHERE id = ? AND participation_status = 'waiting_draw'
               AND EXISTS (SELECT 1 FROM draw_rounds WHERE id = ?)`
          ).bind(Math.round(weights[i] / totalWeight * 10000), winner.id, winner.id, u.id, roundId));
        }
        // A declined prize applies only to the current round. Re-enable those
        // users after this draw so they can choose again in the next round.
        statements.push(env.DB.prepare(
          "UPDATE users SET participation_status = 'not_participating', updated_at = CURRENT_TIMESTAMP WHERE participation_status = 'declined_for_karma'"
        ));
        statements.push(env.DB.prepare(
          "UPDATE draw_settings SET status = 'completed' WHERE id = 1 AND status = 'finalizing'"
        ));

        try {
          await env.DB.batch(statements);
        } catch (error) {
          await env.DB.prepare(
            "UPDATE draw_settings SET status = 'started' WHERE id = 1 AND status = 'finalizing'"
          ).run();
          return json({ error: "Draw finalization failed", detail: String(error) }, 409);
        }
        const finalized = await env.DB.prepare(
          "SELECT id FROM draw_rounds WHERE id = ?"
        ).bind(roundId).first();
        if (!finalized) return json({ error: "Draw was already finalized by another request" }, 409);

        return json({
          winner_telegram_id: String(winner.telegram_id),
          participants: participants.map((u, i) => ({
            telegram_id: String(u.telegram_id), first_name: u.first_name,
            username: u.username, language_code: u.language_code,
            weight: weights[i], is_winner: i === winnerIndex,
          })),
          declined_users: declinedUsers.map((u) => ({
            telegram_id: String(u.telegram_id), first_name: u.first_name,
            language_code: u.language_code,
          })),
          total_weight: totalWeight,
        });
      }

      if (url.pathname === "/internal/participation" && request.method === "POST") {
        const body = await readBody();
        const id = String(body?.telegram_id || "");
        const action = body?.action || "join";
        if (!/^\d{1,20}$/.test(id) || !["join", "decline"].includes(action)) {
          return json({ error: "Invalid participation request" }, 400);
        }
        if (action === "join") {
          const result = await env.DB.prepare(
            "UPDATE users SET participation_status = 'waiting_draw', payment_status = 'not_paid', participation_amount_minor = 0, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ? AND participation_status = 'not_participating' AND EXISTS (SELECT 1 FROM draw_settings WHERE id = 1 AND status = 'not_started' AND participant_limit IS NOT NULL AND participant_limit > (SELECT COUNT(*) FROM users WHERE participation_status = 'waiting_draw'))"
          ).bind(id).run();
          if (result.meta.changes === 1) {
            const settings = await env.DB.prepare("SELECT draw_datetime, participant_limit FROM draw_settings WHERE id = 1").first();
            const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'").first();
            return json({ ok: true, action, status: "waiting_draw", draw_datetime: settings.draw_datetime, participant_count: count.count, participant_limit: settings.participant_limit });
          }
        } else {
          const result = await env.DB.prepare(
            "UPDATE users SET participation_status = 'declined_for_karma', payment_status = 'not_paid', participation_amount_minor = 0, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ? AND participation_status = 'not_participating' AND EXISTS (SELECT 1 FROM draw_settings WHERE id = 1 AND status = 'not_started' AND participant_limit IS NOT NULL)"
          ).bind(id).run();
          if (result.meta.changes === 1) return json({ ok: true, action, status: "declined_for_karma" });
        }
        const user = await userByTelegramId(id);
        if (!user) return json({ error: "User not found" }, 404);
        if (user.participation_status === "waiting_draw") return json({ error: "Вы уже участвуете в текущем розыгрыше." }, 409);
        if (user.participation_status === "declined_for_karma") return json({ error: "Вы уже отказались от участия в этом раунде." }, 409);
        const settings = await env.DB.prepare("SELECT participant_limit, status FROM draw_settings WHERE id = 1").first();
        if (!settings || !settings.participant_limit) return json({ error: "Администратор ещё не настроил розыгрыш." }, 409);
        if (settings.status !== "not_started") return json({ error: "Регистрация участников на этот розыгрыш закрыта." }, 409);
        const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'").first();
        return json({ error: `Свободных мест нет (${count.count}/${settings.participant_limit}).` }, 409);
      }

      return json({ error: "Not found" }, 404);
    }

    const tgUser = await requireTelegramUser(request, env);
    if (!tgUser) {
      return json({ error: "Telegram authentication failed. Open this app inside Telegram." }, 401);
    }

    const telegramId = String(tgUser.id);

    if (url.pathname === "/api/me" && request.method === "GET") {
      // Register/update the Telegram profile and create its virtual wallet.
      await env.DB.batch([
        env.DB.prepare(
          `INSERT INTO users (telegram_id, username, first_name, language_code)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(telegram_id) DO UPDATE SET
             username = excluded.username,
             first_name = excluded.first_name,
             language_code = excluded.language_code,
             updated_at = CURRENT_TIMESTAMP`,
        ).bind(
          telegramId,
          tgUser.username || null,
          tgUser.first_name || "Telegram user",
          (tgUser.language_code || "ru").slice(0, 2),
        ),
        env.DB.prepare(
          `INSERT OR IGNORE INTO wallets (user_id, balance_minor)
           SELECT id, 0 FROM users WHERE telegram_id = ?`,
        ).bind(telegramId),
      ]);

      const user = await env.DB.prepare(
        `SELECT id, telegram_id, username, first_name, created_at, language_code,
                participation_status, winning_chance_basis_points,
                wins_count, losses_count
         FROM users WHERE telegram_id = ?`,
      ).bind(telegramId).first();

      const wallet = await env.DB.prepare(
        "SELECT balance_minor, currency_code FROM wallets WHERE user_id = ?",
      ).bind(user.id).first();

      return json({
        user: {
          id: user.id,
          telegram_id: user.telegram_id,
          username: user.username,
          first_name: user.first_name,
          created_at: user.created_at,
          language_code: user.language_code,
          participation_status: user.participation_status,
          winning_chance_percent: (Number(user.winning_chance_basis_points || 0) / 100).toFixed(2) + "%",
          wins_count: user.wins_count,
          losses_count: user.losses_count,
        },
        wallet: wallet || { balance_minor: 0, currency_code: "TST" },
        test_mode: true,
      });
    }

    if (url.pathname === "/api/draw" && request.method === "GET") {
      const draw = await env.DB.prepare(
        "SELECT draw_datetime, participant_limit, status FROM draw_settings WHERE id = 1",
      ).first();
      const count = await env.DB.prepare(
        "SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'",
      ).first();
      return json({
        draw: draw || { draw_datetime: null, participant_limit: null, status: "not_started" },
        participant_count: count.count,
        test_mode: true,
      });
    }

    if (url.pathname === "/api/history" && request.method === "GET") {
      const limit = Math.min(50, Math.max(1, Number(url.searchParams.get("limit")) || 20));
      const rows = await env.DB.prepare(
        `SELECT r.id, r.status, r.draw_datetime, r.participant_count,
                r.total_weight, r.created_at, r.completed_at,
                CASE WHEN r.winner_telegram_id = ? THEN 1 ELSE 0 END AS is_winner,
                p.weight AS my_weight, p.status AS my_status
         FROM draw_rounds r
         INNER JOIN draw_participants p ON p.draw_round_id = r.id
         INNER JOIN users u ON u.id = p.user_id
         WHERE u.telegram_id = ?
         ORDER BY r.created_at DESC
         LIMIT ?`
      ).bind(telegramId, telegramId, limit).all();
      return json({
        rounds: (rows.results || []).map((row) => ({
          id: row.id,
          status: row.status,
          draw_datetime: row.draw_datetime,
          participant_count: row.participant_count,
          total_weight: row.total_weight,
          created_at: row.created_at,
          completed_at: row.completed_at,
          is_winner: Boolean(row.is_winner),
          weight: row.my_weight,
          participant_status: row.my_status,
        })),
        test_mode: true,
      });
    }

    if (url.pathname === "/api/rules" && request.method === "GET") {
      return json({ rules: TEST_RULES, test_mode: true });
    }

    if (url.pathname === "/api/participation" && request.method === "POST") {
      let body;
      try { body = await request.json(); } catch { return json({ error: "Invalid JSON body" }, 400); }
      const action = body?.action || "join";
      if (!["join", "decline"].includes(action)) return json({ error: "Invalid participation action" }, 400);
      if (action === "join") {
        const result = await env.DB.prepare(
          "UPDATE users SET participation_status = 'waiting_draw', payment_status = 'not_paid', participation_amount_minor = 0, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ? AND participation_status = 'not_participating' AND EXISTS (SELECT 1 FROM draw_settings WHERE id = 1 AND status = 'not_started' AND participant_limit IS NOT NULL AND participant_limit > (SELECT COUNT(*) FROM users WHERE participation_status = 'waiting_draw'))"
        ).bind(telegramId).run();
        if (result.meta.changes === 1) {
          const [settings, count] = await Promise.all([
            env.DB.prepare("SELECT draw_datetime, participant_limit FROM draw_settings WHERE id = 1").first(),
            env.DB.prepare("SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'").first(),
          ]);
          return json({ ok: true, status: "waiting_draw", draw_datetime: settings.draw_datetime, participant_count: count.count, participant_limit: settings.participant_limit, test_mode: true });
        }
      } else {
        const result = await env.DB.prepare(
          "UPDATE users SET participation_status = 'declined_for_karma', payment_status = 'not_paid', participation_amount_minor = 0, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ? AND participation_status = 'not_participating' AND EXISTS (SELECT 1 FROM draw_settings WHERE id = 1 AND status = 'not_started' AND participant_limit IS NOT NULL)"
        ).bind(telegramId).run();
        if (result.meta.changes === 1) return json({ ok: true, status: "declined_for_karma", test_mode: true });
      }
      const user = await env.DB.prepare("SELECT participation_status FROM users WHERE telegram_id = ?").bind(telegramId).first();
      if (user?.participation_status === "waiting_draw") return json({ error: "Вы уже участвуете в текущем розыгрыше." }, 409);
      if (user?.participation_status === "declined_for_karma") return json({ error: "Вы уже отказались от участия в этом раунде." }, 409);
      const settings = await env.DB.prepare("SELECT participant_limit, status FROM draw_settings WHERE id = 1").first();
      if (!settings || !settings.participant_limit) return json({ error: "Администратор ещё не настроил розыгрыш." }, 409);
      if (settings.status !== "not_started") return json({ error: "Регистрация участников на этот розыгрыш закрыта." }, 409);
      const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM users WHERE participation_status = 'waiting_draw'").first();
      return json({ error: `Свободных мест нет (${count.count}/${settings.participant_limit}).` }, 409);
    }

    return json({ error: "Not found" }, 404);
  },
};
