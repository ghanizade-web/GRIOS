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


const sec13fSnapshot = {
  snapshot_id: "a".repeat(64),
  filer_cik: "0000123456",
  report_period: "2026-09-30",
  latest_filed_at: "2026-11-02T00:00:00Z",
  holdings_count: 1,
  source_revision: "grios-main-sha",
  applied_filings: [
    {
      accession_number: "0000123456-26-000001",
      form_type: "13F-HR",
      amendment_number: null,
      amendment_type: "ORIGINAL",
      filed_at: "2026-11-01T00:00:00Z",
      source_url: "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/infotable.xml",
      cover_page_source_url: "https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/primary_doc.xml",
      effect: "BASE_SNAPSHOT",
    },
    {
      accession_number: "0000123456-26-000002",
      form_type: "13F-HR/A",
      amendment_number: 1,
      amendment_type: "NEW HOLDINGS",
      filed_at: "2026-11-02T00:00:00Z",
      source_url: "https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/infotable.xml",
      cover_page_source_url: "https://www.sec.gov/Archives/edgar/data/123456/000012345626000002/primary_doc.xml",
      effect: "SUPPLEMENTED_PRIOR_SNAPSHOT",
    },
  ],
  holdings: [
    {
      row_id: "position-123456789",
      issuer: "Example Corporation",
      title_of_class: "COM",
      cusip: "123456789",
      figi: "BBG000B9XRY4",
      put_call: null,
      amount_type: "SH",
      investment_discretion: "SOLE",
      other_manager: null,
      amount: 1000000,
      value_usd: 125000000,
      voting_authority: { sole: 1000000, shared: 0, none: 0 },
    },
  ],
};

test("rejects invalid SEC 13F snapshot provenance before database access", async () => {
  const invalid = structuredClone(sec13fSnapshot);
  invalid.applied_filings[0].source_url = "https://example.com/filing.xml";
  const req = new Request("https://hub.test/v1/13f/snapshots", {
    method: "POST",
    headers: { ...auth, "content-type": "application/json" },
    body: JSON.stringify({ schema_version: "1.0", snapshot: invalid }),
  });
  const res = await handleRequest(req, env);
  assert.equal(res.status, 422);
  assert.equal((await res.json()).error, "INVALID_13F_SNAPSHOT");
});

test("ingests reconciled 13F snapshots through the atomic Supabase RPC", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url: String(url), init };
    return new Response(JSON.stringify({
      snapshot_id: sec13fSnapshot.snapshot_id,
      snapshot_inserted: true,
      filings_received: 2,
      holdings_received: 1,
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const req = new Request("https://hub.test/v1/13f/snapshots", {
      method: "POST",
      headers: { ...auth, "content-type": "application/json" },
      body: JSON.stringify({ schema_version: "1.0", snapshot: sec13fSnapshot }),
    });
    const res = await handleRequest(req, env);
    const body = await res.json();
    assert.equal(res.status, 202);
    assert.equal(body.holdings_accepted, 1);
    assert.match(captured.url, /rpc\/ingest_grios_13f_snapshot/);
    const saved = JSON.parse(captured.init.body).p_snapshot;
    assert.equal(saved.filer_cik, "0000123456");
    assert.equal(saved.holdings[0].figi, "BBG000B9XRY4");
  } finally { globalThis.fetch = originalFetch; }
});

test("reads the latest SEC 13F snapshot through the read RPC", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url: String(url), init };
    return new Response(JSON.stringify({ snapshot_id: sec13fSnapshot.snapshot_id }), {
      status: 200, headers: { "content-type": "application/json" },
    });
  };
  try {
    const req = new Request("https://hub.test/v1/13f/latest?cik=0000123456&report_period=2026-09-30", { headers: auth });
    const res = await handleRequest(req, env);
    const body = await res.json();
    assert.equal(res.status, 200);
    assert.equal(body.snapshot.snapshot_id, sec13fSnapshot.snapshot_id);
    assert.match(captured.url, /rpc\/get_grios_latest_13f_snapshot/);
    assert.deepEqual(JSON.parse(captured.init.body), {
      p_filer_cik: "0000123456", p_report_period: "2026-09-30",
    });
  } finally { globalThis.fetch = originalFetch; }
});

test("rejects invalid SEC 13F lookup identifiers", async () => {
  const req = new Request("https://hub.test/v1/13f/latest?cik=bad&report_period=2026-09-30", { headers: auth });
  const res = await handleRequest(req, env);
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error, "INVALID_13F_LOOKUP");
});


test("status verifies both market and SEC 13F storage capabilities", async () => {
  const originalFetch = globalThis.fetch;
  const checked = [];
  globalThis.fetch = async (url) => {
    checked.push(String(url));
    return new Response("[]", { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const req = new Request("https://hub.test/v1/status", { headers: auth });
    const res = await handleRequest(req, env);
    const body = await res.json();
    assert.equal(res.status, 200);
    assert.deepEqual(body.capabilities, ["market_observations", "sec_13f_snapshots"]);
    assert.equal(checked.length, 2);
    assert.ok(checked.some((url) => url.includes("grios_13f_snapshots")));
  } finally { globalThis.fetch = originalFetch; }
});

test("rejects non-monotonic amendment sequence", async () => {
  const invalid = structuredClone(sec13fSnapshot);
  invalid.applied_filings[1].amendment_number = 0;
  const req = new Request("https://hub.test/v1/13f/snapshots", {
    method: "POST",
    headers: { ...auth, "content-type": "application/json" },
    body: JSON.stringify({ schema_version: "1.0", snapshot: invalid }),
  });
  const res = await handleRequest(req, env);
  assert.equal(res.status, 422);
});
