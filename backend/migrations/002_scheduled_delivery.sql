-- Episodes are generated ahead of time, but the email goes out at the user's chosen time.
alter table episodes add column if not exists deliver_at timestamptz;
alter table episodes add column if not exists email_sent_at timestamptz;

-- Episodes created before this change were emailed as soon as they were ready.
update episodes set deliver_at = created_at, email_sent_at = created_at where deliver_at is null;

alter table episodes alter column deliver_at set default now();
alter table episodes alter column deliver_at set not null;

create index if not exists episodes_unsent_idx on episodes (deliver_at)
  where status = 'ready' and email_sent_at is null;
