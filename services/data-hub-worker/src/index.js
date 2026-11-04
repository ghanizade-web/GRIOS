const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const MAX_BODY_BYTES = 1_000_000;
const MAX_ROWS = 500;
const MAX_13F_BODY_BYTES = 10_000_000;
const MAX_13F_FILINGS = 100;
const MAX_13F_HOLDINGS = 25_000;
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


function validIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(value + "T00:00:00Z");
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function validIsoTimestamp(value) {
  return typeof value === "string"
    && /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
    && Number.isFinite(Date.parse(value));
}

function validSecUrl(value) {
  if (typeof value !== "string") return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && ["sec.gov", "www.sec.gov"].includes(parsed.hostname);
  } catch {
    return false;
  }
}

function valid13fSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) return false;
  if (!/^[0-9a-f]{64}$/.test(snapshot.snapshot_id || "")) return false;
  if (!/^\d{10}$/.test(snapshot.filer_cik || "")) return false;
  if (!validIsoDate(snapshot.report_period) || !validIsoTimestamp(snapshot.latest_filed_at)) return false;
  if (!Number.isSafeInteger(snapshot.holdings_count) || snapshot.holdings_count < 0 || snapshot.holdings_count > MAX_13F_HOLDINGS) return false;
  if (!Array.isArray(snapshot.applied_filings) || snapshot.applied_filings.length < 1 || snapshot.applied_filings.length > MAX_13F_FILINGS) return false;
  if (!Array.isArray(snapshot.holdings) || snapshot.holdings.length !== snapshot.holdings_count) return false;
  if (snapshot.source_revision !== undefined && snapshot.source_revision !== null && (typeof snapshot.source_revision !== "string" || snapshot.source_revision.length > 160)) return false;

  const accessions = new Set();
  const amendmentNumbers = new Set();
  let originals = 0;
  let originalPosition = -1;
  let previousFiledAt = null;
  let previousAmendmentNumber = 0;
  for (let filingIndex = 0; filingIndex < snapshot.applied_filings.length; filingIndex += 1) {
    const filing = snapshot.applied_filings[filingIndex];
    if (!filing || typeof filing !== "object" || Array.isArray(filing)) return false;
    if (!/^\d{10}-\d{2}-\d{6}$/.test(filing.accession_number || "") || accessions.has(filing.accession_number)) return false;
    accessions.add(filing.accession_number);
    if (!validIsoTimestamp(filing.filed_at) || (previousFiledAt && Date.parse(filing.filed_at) < Date.parse(previousFiledAt))) return false;
    previousFiledAt = filing.filed_at;
    if (!validSecUrl(filing.source_url) || (filing.cover_page_source_url != null && !validSecUrl(filing.cover_page_source_url))) return false;
    if (!["BASE_SNAPSHOT", "REPLACED_PRIOR_SNAPSHOT", "SUPPLEMENTED_PRIOR_SNAPSHOT"].includes(filing.effect)) return false;
    if (filing.form_type === "13F-HR") {
      originals += 1;
      originalPosition = filingIndex;
      if (filing.amendment_number != null || filing.amendment_type !== "ORIGINAL" || filing.effect !== "BASE_SNAPSHOT") return false;
    } else if (filing.form_type === "13F-HR/A") {
      if (!Number.isInteger(filing.amendment_number) || filing.amendment_number < 1 || filing.amendment_number > 99) return false;
      if (!["RESTATEMENT", "NEW HOLDINGS"].includes(filing.amendment_type)) return false;
      if (amendmentNumbers.has(filing.amendment_number) || filing.amendment_number <= previousAmendmentNumber) return false;
      amendmentNumbers.add(filing.amendment_number);
      previousAmendmentNumber = filing.amendment_number;
    } else {
      return false;
    }
  }
  if (originals !== 1 || originalPosition !== 0 || !previousFiledAt || Date.parse(snapshot.latest_filed_at) !== Date.parse(previousFiledAt)) return false;

  const rowIds = new Set();
  for (const holding of snapshot.holdings) {
    if (!holding || typeof holding !== "object" || Array.isArray(holding)) return false;
    if (typeof holding.row_id !== "string" || !holding.row_id || holding.row_id.length > 256 || rowIds.has(holding.row_id)) return false;
    rowIds.add(holding.row_id);
    if (typeof holding.issuer !== "string" || !holding.issuer.trim() || typeof holding.title_of_class !== "string" || !holding.title_of_class.trim()) return false;
    if (!/^[A-Z0-9*@#]{9}$/.test(holding.cusip || "")) return false;
    if (holding.figi != null && !/^[A-Z0-9]{12}$/.test(holding.figi)) return false;
    if (holding.put_call != null && !["Put", "Call"].includes(holding.put_call)) return false;
    if (!["SH", "PRN"].includes(holding.amount_type)) return false;
    if (!["SOLE", "DFND", "OTR"].includes(holding.investment_discretion)) return false;
    if (holding.other_manager != null && typeof holding.other_manager !== "string") return false;
    if (!Number.isSafeInteger(holding.amount) || holding.amount < 0) return false;
    if (!Number.isSafeInteger(holding.value_usd) || holding.value_usd < 0) return false;
    const voting = holding.voting_authority;
    if (!voting || typeof voting !== "object" || Array.isArray(voting)) return false;
    if (!["sole", "shared", "none"].every((key) => Number.isSafeInteger(voting[key]) && voting[key] >= 0)) return false;
  }
  return true;
}

function requiredEnv(env) {
  return Boolean(env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY && env.GRIOS_INGEST_TOKEN);
}

async function supabaseRequest(env, path, init = {}) {
  const base = String(env.SUPABASE_URL).replace(/\/$/, "");
  const upstream = await fetch(base + "/rest/v1/" + path, {
    ...init,
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      authorization: "Bearer " + env.SUPABASE_SERVICE_ROLE_KEY,
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!upstream.ok) throw new Error("SUPABASE_HTTP_" + upstream.status);
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


    if (url.pathname === "/v1/13f/snapshots" && request.method === "POST") {
      const declaredLength = Number(request.headers.get("content-length") || 0);
      if (declaredLength > MAX_13F_BODY_BYTES) return response({ error: "PAYLOAD_TOO_LARGE" }, 413);
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > MAX_13F_BODY_BYTES) return response({ error: "PAYLOAD_TOO_LARGE" }, 413);
      let payload;
      try { payload = JSON.parse(raw); } catch { return response({ error: "INVALID_JSON" }, 400); }
      if (payload?.schema_version !== SCHEMA_VERSION || !payload.snapshot || typeof payload.snapshot !== "object") {
        return response({ error: "INVALID_13F_ENVELOPE" }, 400);
      }
      if (!valid13fSnapshot(payload.snapshot)) return response({ error: "INVALID_13F_SNAPSHOT" }, 422);
      const result = await supabaseRequest(env, "rpc/ingest_grios_13f_snapshot", {
        method: "POST",
        body: JSON.stringify({ p_snapshot: payload.snapshot }),
      });
      const stored = await result.json();
      return response({
        status: "accepted",
        snapshot_id: payload.snapshot.snapshot_id,
        holdings_accepted: payload.snapshot.holdings.length,
        filings_accepted: payload.snapshot.applied_filings.length,
        database: stored,
        schema_version: SCHEMA_VERSION,
      }, 202);
    }

    if (url.pathname === "/v1/13f/latest" && request.method === "GET") {
      const cik = url.searchParams.get("cik") || "";
      const reportPeriod = url.searchParams.get("report_period") || "";
      if (!/^\d{10}$/.test(cik) || !validIsoDate(reportPeriod)) {
        return response({ error: "INVALID_13F_LOOKUP" }, 400);
      }
      const result = await supabaseRequest(env, "rpc/get_grios_latest_13f_snapshot", {
        method: "POST",
        body: JSON.stringify({ p_filer_cik: cik, p_report_period: reportPeriod }),
      });
      const snapshot = await result.json();
      return response({ schema_version: SCHEMA_VERSION, snapshot });
    }

    if (url.pathname === "/v1/markets/latest" && request.method === "GET") {
      const params = new URLSearchParams();
      params.set("select", "asset_key,symbol,name,asset_class,instrument,provider,feed_class,currency,observed_at,data_as_of,caveat,observations,extra,source_revision");
      if (url.searchParams.has("asset_class")) params.set("asset_class", "eq." + url.searchParams.get("asset_class"));
      if (url.searchParams.has("symbol")) params.set("symbol", "eq." + url.searchParams.get("symbol").toUpperCase());
      params.set("order", "observed_at.desc");
      const limit = Math.max(1, Math.min(500, Number.parseInt(url.searchParams.get("limit") || "100", 10) || 100));
      params.set("limit", String(limit));
      const result = await supabaseRequest(env, "grios_latest_market_observations?" + params.toString());
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
