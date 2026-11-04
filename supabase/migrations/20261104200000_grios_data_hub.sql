-- GRIOS Data Hub: append-only, provider-attributed market observations.
create table if not exists public.grios_market_observations (
  id bigint generated always as identity primary key,
  run_id uuid not null,
  asset_key text not null,
  symbol text not null,
  name text not null,
  asset_class text not null,
  instrument text not null,
  provider text not null,
  feed_class text not null,
  currency text not null,
  observed_at timestamptz not null,
  data_as_of date not null,
  caveat text,
  observations jsonb not null default '[]'::jsonb,
  extra jsonb not null default '{}'::jsonb,
  source_revision text,
  generated_at timestamptz not null default now(),
  inserted_at timestamptz not null default now(),
  constraint grios_market_observations_run_asset_provider_key
    unique (run_id, asset_key, provider),
  constraint grios_market_observations_asset_key_length
    check (length(asset_key) between 1 and 240),
  constraint grios_market_observations_observations_array
    check (jsonb_typeof(observations) = 'array'),
  constraint grios_market_observations_extra_object
    check (jsonb_typeof(extra) = 'object')
);

create index if not exists grios_market_observations_asset_time_idx
  on public.grios_market_observations (asset_key, observed_at desc);
create index if not exists grios_market_observations_class_time_idx
  on public.grios_market_observations (asset_class, observed_at desc);
create index if not exists grios_market_observations_symbol_time_idx
  on public.grios_market_observations (symbol, observed_at desc);

alter table public.grios_market_observations enable row level security;
revoke all on public.grios_market_observations from public, anon, authenticated;
grant all on public.grios_market_observations to service_role;
grant usage, select on sequence public.grios_market_observations_id_seq to service_role;

create or replace view public.grios_latest_market_observations
with (security_invoker = true)
as
select distinct on (asset_key, provider)
  id, run_id, asset_key, symbol, name, asset_class, instrument,
  provider, feed_class, currency, observed_at, data_as_of,
  caveat, observations, extra, source_revision, generated_at, inserted_at
from public.grios_market_observations
order by asset_key, provider, observed_at desc, inserted_at desc;

revoke all on public.grios_latest_market_observations from public, anon, authenticated;
grant select on public.grios_latest_market_observations to service_role;
