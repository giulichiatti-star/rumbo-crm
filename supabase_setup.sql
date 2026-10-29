-- Pegá esto en Supabase > SQL Editor > Run (una sola vez)
create table if not exists public.rumbo_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.rumbo_state enable row level security;

create policy "ver mis datos" on public.rumbo_state
  for select using (auth.uid() = user_id);
create policy "crear mis datos" on public.rumbo_state
  for insert with check (auth.uid() = user_id);
create policy "editar mis datos" on public.rumbo_state
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
