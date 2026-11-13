create table if not exists briefings (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  topic        text not null,
  time_of_day  time not null,          -- user's local time, e.g. 08:00
  timezone     text not null,          -- IANA, e.g. 'Asia/Kolkata'
  is_active    boolean not null default true,
  next_run_at  timestamptz not null,   -- UTC, includes generation lead time
  created_at   timestamptz not null default now()
);

create table if not exists episodes (
  id               uuid primary key default gen_random_uuid(),
  briefing_id      uuid not null references briefings(id) on delete cascade,
  user_id          uuid not null references auth.users(id) on delete cascade,
  status           text not null default 'researching'
                   check (status in ('researching', 'writing', 'synthesizing', 'ready', 'failed')),
  title            text,
  summary          text,
  script           text,
  sources          jsonb,
  audio_path       text,
  duration_seconds int,
  error            text,
  created_at       timestamptz not null default now()
);

create index if not exists briefings_user_idx on briefings (user_id, created_at desc);
create index if not exists briefings_next_run_idx on briefings (next_run_at) where is_active;
create index if not exists episodes_user_idx on episodes (user_id, created_at desc);
create index if not exists episodes_briefing_idx on episodes (briefing_id, created_at desc);

-- Only the backend (direct DB connection) reads these tables; with RLS on and no
-- policies, the public anon/publishable key gets nothing through Supabase's REST API.
alter table briefings enable row level security;
alter table episodes enable row level security;
