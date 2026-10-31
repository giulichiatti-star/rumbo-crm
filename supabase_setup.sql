-- Pegá esto en Supabase > SQL Editor > Run. Se puede correr más de una vez sin problema.

-- 1) Los datos de cada persona (una fila por cuenta)
create table if not exists public.rumbo_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.rumbo_state enable row level security;
drop policy if exists "ver mis datos" on public.rumbo_state;
drop policy if exists "crear mis datos" on public.rumbo_state;
drop policy if exists "editar mis datos" on public.rumbo_state;
create policy "ver mis datos" on public.rumbo_state for select using (auth.uid() = user_id);
create policy "crear mis datos" on public.rumbo_state for insert with check (auth.uid() = user_id);
create policy "editar mis datos" on public.rumbo_state for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 2) Copias de seguridad (una por día y cada vez que se restaura o hay un choque entre aparatos)
create table if not exists public.rumbo_backups (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  motivo text,
  data jsonb not null,
  created_at timestamptz not null default now()
);
alter table public.rumbo_backups enable row level security;
drop policy if exists "ver mis copias" on public.rumbo_backups;
drop policy if exists "crear mis copias" on public.rumbo_backups;
drop policy if exists "borrar mis copias" on public.rumbo_backups;
create policy "ver mis copias" on public.rumbo_backups for select using (auth.uid() = user_id);
create policy "crear mis copias" on public.rumbo_backups for insert with check (auth.uid() = user_id);
create policy "borrar mis copias" on public.rumbo_backups for delete using (auth.uid() = user_id);

-- 3) Comentarios de quienes prueban la app (los lee quien administra el proyecto desde el panel de Supabase > Table Editor)
create table if not exists public.rumbo_feedback (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  email text,
  tipo text,
  texto text not null,
  pantalla text,
  version text,
  ancho int,
  aparato text,
  created_at timestamptz not null default now()
);
alter table public.rumbo_feedback enable row level security;
drop policy if exists "enviar comentarios" on public.rumbo_feedback;
create policy "enviar comentarios" on public.rumbo_feedback for insert with check (auth.uid() = user_id);
