-- Muscle Analyzer: users テーブル（Supabase SQL Editor で実行）
create table if not exists public.users (
  id          text   primary key,
  email       text   not null,
  name        text   not null default '',
  password    text   not null,      -- bcryptハッシュ（平文は保存しない）
  created_at  bigint not null
);

-- メールは小文字で保存する前提。念のためDB側でも大文字小文字を区別せず一意にする
create unique index if not exists users_email_lower_key on public.users (lower(email));

-- RLSを有効化しポリシーは作らない:
--   anon / authenticated キーからは一切読み書きできない。
--   バックエンドの service_role キーだけが RLS をバイパスして操作できる。
alter table public.users enable row level security;
revoke all on public.users from anon, authenticated;
