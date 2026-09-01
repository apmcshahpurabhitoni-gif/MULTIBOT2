-- MULTIBOT2 production persistence schema.
-- No pending_sweeps table: that workflow was removed from MULTIBOT2.
-- Run once in Supabase SQL Editor for the MULTIBOT2 project.

create table if not exists public.accounts (
  name text primary key,
  starting_balance double precision not null default 100000,
  balance double precision not null default 100000,
  daily_trades integer not null default 0,
  trades_today integer not null default 0,
  planned_risk_used double precision not null default 0,
  last_reset_date text,
  reset_date text,
  updated_at timestamptz not null default now()
);

create table if not exists public.active_trades (
  id text primary key,
  symbol text not null default '',
  market text not null default 'NSE',
  account text not null default '',
  strat text not null default '',
  type text not null default 'LONG',
  entry double precision not null default 0,
  sl double precision not null default 0,
  tp double precision not null default 0,
  qty double precision not null default 0,
  trail_sl double precision not null default 0,
  ts_trigger text,
  opened_at timestamptz,
  time_str text,
  updated_at timestamptz not null default now()
);

create table if not exists public.closed_trades (
  id text primary key,
  symbol text not null default '',
  market text not null default 'NSE',
  account text not null default '',
  strat text not null default '',
  type text not null default 'LONG',
  entry double precision not null default 0,
  exit_price double precision not null default 0,
  pnl double precision not null default 0,
  result text not null default '',
  exit_reason text not null default '',
  close_time timestamptz,
  closed_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.sent_signals (
  sig_key text primary key,
  send_count integer not null default 0,
  last_sent_ts bigint,
  updated_at timestamptz not null default now()
);

create index if not exists active_trades_account_idx on public.active_trades(account);
create index if not exists closed_trades_account_idx on public.closed_trades(account);
create index if not exists closed_trades_closed_at_idx on public.closed_trades(closed_at);
create index if not exists sent_signals_last_sent_idx on public.sent_signals(last_sent_ts);

-- Keep this schema private to the bot's server-side service role.
-- Do not expose SUPABASE_KEY in browser/client code.
