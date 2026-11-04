import test from "node:test";
import assert from "node:assert/strict";
import { handleRequest } from "../src/index.js";

const env = { GRIOS_INGEST_TOKEN: "unit-test-token", SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "server-only-test-key" };
const auth = { authorization: "Bearer unit-test-token" };
const observation = { asset_key: "crypto:btc", symbol: "BTC", name: "Bitcoin", asset_class: "crypto", instrument: "spot token", provider: "CoinGecko", feed_class: "spot", currency: "USD", observed_at: "2026-11-04T20:00:00Z", data_as_of: "2026-11-04", observations: [{ date: "2026-11-04", close: 70000 }], extra: {} };

test("rejects requests without bearer authentication", async () => {
  const res = await handleRequest(new Request("https://hub.test/v1/status"), env);
  assert.equal(res.status, 401);
});

test("rejects malformed ingest envelope before database access", async () => {
  const req = new Request("https://hub.test/v1/ingest", { method: "POST", headers: { ...auth, "content-type": "application/json" }, body: JSON.stringify({ schema_version: "0", observations: [observation] }) });
  const res = await handleRequest(req, env);
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error, "INVALID_INGEST_ENVELOPE");
});

test("rejects invalid timestamps and missing required provenance", async () => {
  const bad = { ...observation, observed_at: "yesterday", provider: "" };
  const req = new Request("https://hub.test/v1/ingest", { method: "POST", headers: { ...auth, "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", observations: [bad] }) });
  const res = await handleRequest(req, env);
  assert.equal(res.status, 422);
});

test("ingests normalized observations without leaking upstream response bodies", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url: String(url), init };
    return new Response(null, { status: 201 });
  };
  try {
    const req = new Request("https://hub.test/v1/ingest", { method: "POST", headers: { ...auth, "content-type": "application/json" }, body: JSON.stringify({ schema_version: "1.0", source_revision: "abc123", observations: [observation] }) });
    const res = await handleRequest(req, env);
    const body = await res.json();
    assert.equal(res.status, 202);
    assert.equal(body.accepted, 1);
    assert.match(captured.url, /grios_market_observations/);
    const saved = JSON.parse(captured.init.body)[0];
    assert.equal(saved.symbol, "BTC");
    assert.equal(saved.source_revision, "abc123");
    assert.equal(saved.run_id, body.run_id);
  } finally { globalThis.fetch = originalFetch; }
});

test("reports missing server configuration without attempting upstream calls", async () => {
  const req = new Request("https://hub.test/v1/status", { headers: auth });
  const res = await handleRequest(req, { GRIOS_INGEST_TOKEN: "unit-test-token" });
  assert.equal(res.status, 503);
});

test("returns latest records through the normalized read view", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    assert.match(String(url), /grios_latest_market_observations/);
    return new Response(JSON.stringify([{ symbol: "BTC" }]), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const req = new Request("https://hub.test/v1/markets/latest?asset_class=crypto&limit=5", { headers: auth });
    const res = await handleRequest(req, env);
    const body = await res.json();
    assert.equal(res.status, 200);
    assert.equal(body.count, 1);
    assert.equal(body.observations[0].symbol, "BTC");
  } finally { globalThis.fetch = originalFetch; }
});
