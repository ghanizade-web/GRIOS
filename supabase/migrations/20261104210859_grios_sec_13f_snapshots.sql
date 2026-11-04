create table if not exists public.grios_13f_snapshots (
  snapshot_id text primary key check (snapshot_id ~ '^[0-9a-f]{64}$'),
  filer_cik text not null check (filer_cik ~ '^[0-9]{10}$'),
  report_period date not null,
  latest_filed_at timestamptz not null,
  holdings_count integer not null check (holdings_count >= 0),
  source_revision text,
  ingested_at timestamptz not null default now()
);

create index if not exists grios_13f_snapshots_latest_idx
  on public.grios_13f_snapshots (filer_cik, report_period, latest_filed_at desc);

create table if not exists public.grios_13f_snapshot_filings (
  snapshot_id text not null references public.grios_13f_snapshots(snapshot_id),
  accession_number text not null check (accession_number ~ '^[0-9]{10}-[0-9]{2}-[0-9]{6}$'),
  form_type text not null check (form_type in ('13F-HR', '13F-HR/A')),
  amendment_number integer,
  amendment_type text not null check (amendment_type in ('ORIGINAL', 'RESTATEMENT', 'NEW HOLDINGS')),
  filed_at timestamptz not null,
  source_url text not null check (source_url ~ '^https://(www\\.)?sec\\.gov/'),
  cover_page_source_url text check (
    cover_page_source_url is null or cover_page_source_url ~ '^https://(www\\.)?sec\\.gov/'
  ),
  effect text not null check (effect in ('BASE_SNAPSHOT', 'REPLACED_PRIOR_SNAPSHOT', 'SUPPLEMENTED_PRIOR_SNAPSHOT')),
  primary key (snapshot_id, accession_number),
  check (
    (form_type = '13F-HR' and amendment_number is null and amendment_type = 'ORIGINAL')
    or
    (form_type = '13F-HR/A' and amendment_number between 1 and 99 and amendment_type in ('RESTATEMENT', 'NEW HOLDINGS'))
  )
);

create index if not exists grios_13f_filings_accession_idx
  on public.grios_13f_snapshot_filings (accession_number);

create table if not exists public.grios_13f_snapshot_holdings (
  snapshot_id text not null references public.grios_13f_snapshots(snapshot_id),
  row_id text not null,
  issuer text not null,
  title_of_class text not null,
  cusip text not null check (cusip ~ '^[A-Z0-9*@#]{9}$'),
  figi text check (figi is null or figi ~ '^[A-Z0-9]{12}$'),
  put_call text check (put_call is null or put_call in ('Put', 'Call')),
  amount_type text not null check (amount_type in ('SH', 'PRN')),
  investment_discretion text not null check (investment_discretion in ('SOLE', 'DFND', 'OTR')),
  other_manager text,
  amount bigint not null check (amount >= 0),
  value_usd numeric(30,0) not null check (value_usd >= 0),
  voting_authority jsonb not null check (jsonb_typeof(voting_authority) = 'object'),
  primary key (snapshot_id, row_id)
);

create index if not exists grios_13f_holdings_cusip_idx
  on public.grios_13f_snapshot_holdings (cusip, snapshot_id);

alter table public.grios_13f_snapshots enable row level security;
alter table public.grios_13f_snapshot_filings enable row level security;
alter table public.grios_13f_snapshot_holdings enable row level security;

revoke all on table public.grios_13f_snapshots from anon, authenticated;
revoke all on table public.grios_13f_snapshot_filings from anon, authenticated;
revoke all on table public.grios_13f_snapshot_holdings from anon, authenticated;
grant select, insert on table public.grios_13f_snapshots to service_role;
grant select, insert on table public.grios_13f_snapshot_filings to service_role;
grant select, insert on table public.grios_13f_snapshot_holdings to service_role;

create or replace function public.ingest_grios_13f_snapshot(p_snapshot jsonb)
returns jsonb
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
  v_filing jsonb;
  v_holding jsonb;
  v_inserted integer := 0;
  v_snapshot_id text;
  v_filings_count integer;
  v_holdings_count integer;
begin
  if jsonb_typeof(p_snapshot) <> 'object' then
    raise exception 'INVALID_SNAPSHOT_OBJECT';
  end if;
  v_snapshot_id := p_snapshot->>'snapshot_id';
  if v_snapshot_id !~ '^[0-9a-f]{64}$'
     or (p_snapshot->>'filer_cik') !~ '^[0-9]{10}$'
     or (p_snapshot->>'report_period') is null
     or (p_snapshot->>'latest_filed_at') is null then
    raise exception 'INVALID_SNAPSHOT_IDENTITY';
  end if;
  if jsonb_typeof(p_snapshot->'applied_filings') <> 'array'
     or jsonb_typeof(p_snapshot->'holdings') <> 'array' then
    raise exception 'INVALID_SNAPSHOT_ARRAYS';
  end if;
  v_filings_count := jsonb_array_length(p_snapshot->'applied_filings');
  v_holdings_count := jsonb_array_length(p_snapshot->'holdings');
  if v_filings_count < 1 or v_filings_count > 100
     or v_holdings_count <> (p_snapshot->>'holdings_count')::integer
     or v_holdings_count > 25000 then
    raise exception 'INVALID_SNAPSHOT_COUNTS';
  end if;
  if (
    select count(*) from jsonb_array_elements(p_snapshot->'applied_filings') f
    where f->>'form_type' = '13F-HR'
  ) <> 1 then
    raise exception 'SNAPSHOT_REQUIRES_ONE_ORIGINAL_FILING';
  end if;

  insert into public.grios_13f_snapshots (
    snapshot_id, filer_cik, report_period, latest_filed_at,
    holdings_count, source_revision
  ) values (
    v_snapshot_id, p_snapshot->>'filer_cik', (p_snapshot->>'report_period')::date,
    (p_snapshot->>'latest_filed_at')::timestamptz,
    v_holdings_count, p_snapshot->>'source_revision'
  ) on conflict (snapshot_id) do nothing;
  get diagnostics v_inserted = row_count;

  for v_filing in select value from jsonb_array_elements(p_snapshot->'applied_filings')
  loop
    insert into public.grios_13f_snapshot_filings (
      snapshot_id, accession_number, form_type, amendment_number,
      amendment_type, filed_at, source_url, cover_page_source_url, effect
    ) values (
      v_snapshot_id,
      v_filing->>'accession_number',
      v_filing->>'form_type',
      nullif(v_filing->>'amendment_number', '')::integer,
      v_filing->>'amendment_type',
      (v_filing->>'filed_at')::timestamptz,
      v_filing->>'source_url',
      v_filing->>'cover_page_source_url',
      v_filing->>'effect'
    ) on conflict (snapshot_id, accession_number) do nothing;
  end loop;

  for v_holding in select value from jsonb_array_elements(p_snapshot->'holdings')
  loop
    insert into public.grios_13f_snapshot_holdings (
      snapshot_id, row_id, issuer, title_of_class, cusip, figi, put_call,
      amount_type, investment_discretion, other_manager, amount, value_usd,
      voting_authority
    ) values (
      v_snapshot_id,
      v_holding->>'row_id',
      v_holding->>'issuer',
      v_holding->>'title_of_class',
      v_holding->>'cusip',
      nullif(v_holding->>'figi', ''),
      nullif(v_holding->>'put_call', ''),
      v_holding->>'amount_type',
      v_holding->>'investment_discretion',
      nullif(v_holding->>'other_manager', ''),
      (v_holding->>'amount')::bigint,
      (v_holding->>'value_usd')::numeric,
      v_holding->'voting_authority'
    ) on conflict (snapshot_id, row_id) do nothing;
  end loop;

  return jsonb_build_object(
    'snapshot_id', v_snapshot_id,
    'snapshot_inserted', v_inserted = 1,
    'filings_received', v_filings_count,
    'holdings_received', v_holdings_count
  );
end;
$$;

create or replace function public.get_grios_latest_13f_snapshot(
  p_filer_cik text,
  p_report_period date
)
returns jsonb
language sql
stable
security invoker
set search_path = pg_catalog, public
as $$
  select jsonb_build_object(
    'snapshot_id', s.snapshot_id,
    'filer_cik', s.filer_cik,
    'report_period', s.report_period,
    'latest_filed_at', s.latest_filed_at,
    'holdings_count', s.holdings_count,
    'applied_filings', coalesce((
      select jsonb_agg(to_jsonb(f) - 'snapshot_id' order by f.filed_at, f.accession_number)
      from public.grios_13f_snapshot_filings f
      where f.snapshot_id = s.snapshot_id
    ), '[]'::jsonb),
    'holdings', coalesce((
      select jsonb_agg(to_jsonb(h) - 'snapshot_id' - 'row_id' order by h.cusip, h.put_call, h.amount_type)
      from public.grios_13f_snapshot_holdings h
      where h.snapshot_id = s.snapshot_id
    ), '[]'::jsonb)
  )
  from public.grios_13f_snapshots s
  where s.filer_cik = p_filer_cik
    and s.report_period = p_report_period
  order by s.latest_filed_at desc, s.ingested_at desc
  limit 1;
$$;

revoke all on function public.ingest_grios_13f_snapshot(jsonb) from public, anon, authenticated;
revoke all on function public.get_grios_latest_13f_snapshot(text, date) from public, anon, authenticated;
grant execute on function public.ingest_grios_13f_snapshot(jsonb) to service_role;
grant execute on function public.get_grios_latest_13f_snapshot(text, date) to service_role;
