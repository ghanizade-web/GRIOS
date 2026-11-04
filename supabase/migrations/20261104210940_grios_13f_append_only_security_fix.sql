alter table public.grios_13f_snapshot_filings
  drop constraint if exists grios_13f_snapshot_filings_source_url_check;
alter table public.grios_13f_snapshot_filings
  add constraint grios_13f_snapshot_filings_source_url_check
  check (source_url ~ '^https://(www[.])?sec[.]gov/');

alter table public.grios_13f_snapshot_filings
  drop constraint if exists grios_13f_snapshot_filings_cover_page_source_url_check;
alter table public.grios_13f_snapshot_filings
  add constraint grios_13f_snapshot_filings_cover_page_source_url_check
  check (cover_page_source_url is null or cover_page_source_url ~ '^https://(www[.])?sec[.]gov/');

revoke all on table public.grios_13f_snapshots from anon, authenticated, service_role;
revoke all on table public.grios_13f_snapshot_filings from anon, authenticated, service_role;
revoke all on table public.grios_13f_snapshot_holdings from anon, authenticated, service_role;

grant select, insert on table public.grios_13f_snapshots to service_role;
grant select, insert on table public.grios_13f_snapshot_filings to service_role;
grant select, insert on table public.grios_13f_snapshot_holdings to service_role;
