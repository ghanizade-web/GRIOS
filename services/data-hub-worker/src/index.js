const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const MAX_BODY_BYTES = 1_000_000;
const MAX_ROWS = 500;
const SCHEMA_VERSION = "1.0";

function response(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || !a || !b || a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

function authorized(request, env) {
  const expected = env.GRIOS_INGEST_TOKEN;
  const actual = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  return safeEqual(actual, expected);
}

function validObservation(row) {
  if (!row || typeof row !== "object" || Array.isArray(row)) return false;
  const required = ["asset_key", "symbol", "name", "asset_class", "instrument", "provider", "feed_class", "currency", "observed_at", "data_as_of"];
  if (!required.every((key) => typeof row[key] === "string" && row[key].trim().length > 0)) return false;
  if (row.asset_key.length > 240 || row.symbol.length > 40 || row.name.length > 200 || row.provider.length > 120) return false;
  if (!Number.isFinite(Date.parse(row.observed_at)) || !/^\d{4}-\d{2}-\d{2}$/.test(row.data_as_of)) return false;
  if (row.observations !== undefined && (!Array.isArray(row.observations) || row.observations.length > 1000)) return false;
  if (row.extra !== undefined && (row.extra === null || typeof row.extra !== "object" || Array.isArray(row.extra))) return false;
  return true;
}

function requiredEnv(env) {
  return Boolean(env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY && env.GRIOS_INGEST_TOKEN);
}

async function supabaseRequest(env, path, init = {}) {
  const base = String(env.SUPABASE_URL).replace(/\/$/, "");
  const upstream = await fetch(\`\${base}/rest/v1/\${path}\`, {
    ...init,
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      authorization: \`Bearer \${env.SUPABASE_SERVICE_ROLE_KEY}\`,
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!upstream.ok) throw new Error(\`SUPABASE_HTTP_\${upstream.status}\`);
  return upstream;
}

export async function handleRequest(request, env) {
  const url = new URL(request.url);
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { "cache-control": "no-store" } });
  if (!["GET", "POST"].includes(request.method)) return response({ error: "METHOD_NOT_ALLOWED" }, 405);
  if (!authorized(request, env)) return response({ error: "UNAUTHORIZED" }, 401);
  if (!requiredEnv(env)) return response({ error: "DATA_HUB_NOT_CONFIGURED" }, 503);

  try {
    if (url.pathname === "/v1/status" && request.method === "GET") {
      await supabaseRequest(env, "grios_market_observations?select=id&limit=1");
      return response({ status: "ok", service: "grios-data-hub", schema_version: SCHEMA_VERSION, database: "reachable", checked_at: new Date().toISOString() });
    }

    if (url.pathname === "/v1/ingest" && request.method === "POST") {
      const declaredLength = Number(request.headers.get("content-length") || 0);
      if (declaredLength > MAX_BODY_BYTES) return response({ error: "PAYLOAD_TOO_LARGE" }, 413);
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) return response({ error: "PAYLOAD_TOO_LARGE" }, 413);
      let payload;
      try { payload = JSON.parse(raw); } catch { return response({ error: "INVALID_JSON" }, 400); }
      if (payload?.schema_version !== SCHEMA_VERSION || !Array.isArray(payload.observations) || payload.observations.length < 1 || payload.observations.length > MAX_ROWS) {
        return response({ error: "INVALID_INGEST_ENVELOPE" }, 400);
      }
      if (!payload.observations.every(validObservation)) return response({ error: "INVALID_OBSERVATION" }, 422);
      const runId = crypto.randomUUID();
      const rows = payload.observations.map((row) => ({
        run_id: runId,
        asset_key: row.asset_key,
        symbol: row.symbol,
        name: row.name,
        asset_class: row.asset_class,
        instrument: row.instrument,
        provider: row.provider,
        feed_class: row.feed_class,
        currency: row.currency,
        observed_at: row.observed_at,
        data_as_of: row.data_as_of,
        caveat: row.caveat ?? null,
        observations: row.observations ?? [],
        extra: row.extra ?? {},
        source_revision: payload.source_revision ?? null,
        generated_at: payload.generated_at ?? new Date().toISOString(),
      }));
      await supabaseRequest(env, "grios_market_observations?on_conflict=run_id,asset_key,provider", {
        method: "POST",
        headers: { prefer: "resolution=ignore-duplicates,return=minimal" },
        body: JSON.stringify(rows),
      });
      return response({ status: "accepted", run_id: runId, accepted: rows.length, schema_version: SCHEMA_VERSION }, 202);
    }

    if (url.pathname === "/v1/markets/latest" && request.method === "GET") {
      const params = new URLSearchParams();
      params.set("select", "asset_key,symbol,name,asset_class,instrument,provider,feed_class,currency,observed_at,data_as_of,caveat,observations,extra,source_revision");
      if (url.searchParams.has("asset_class")) params.set("asset_class", \`eq.\${url.searchParams.get("asset_class")}\`);
      if (url.searchParams.has("symbol")) params.set("symbol", \`eq.\${url.searchParams.get("symbol").toUpperCase()}\`);
      params.set("order", "observed_at.desc");
      const limit = Math.max(1, Math.min(500, Number.parseInt(url.searchParams.get("limit") || "100", 10) || 100));
      params.set("limit", String(limit));
      const result = await supabaseRequest(env, \`grios_latest_market_observations?\${params.toString()}\`);
      const rows = await result.json();
      return response({ schema_version: SCHEMA_VERSION, count: rows.length, observations: rows });
    }

    return response({ error: "NOT_FOUND" }, 404);
  } catch (error) {
    const code = typeof error?.message === "string" && /^SUPABASE_HTTP_\d+$/.test(error.message) ? error.message : "UPSTREAM_UNAVAILABLE";
    return response({ error: code }, 502);
  }
}

export default { fetch: handleRequest };
