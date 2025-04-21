-- Категории
create table if not exists public.categories (
  id uuid primary key,
  name text not null,
  parent_id uuid,
  created_at timestamp default now()
);

-- Товары
create table if not exists public.products (
  id uuid primary key,
  name text not null,
  description text,
  image_url text,
  category_id uuid references public.categories(id),
  prices jsonb,
  stock jsonb,
  created_at timestamp default now()
);

-- Модификации
create table if not exists public.modifications (
  id uuid primary key,
  product_id uuid references public.products(id),
  name text,
  characteristics jsonb,
  image_url text,
  prices jsonb,
  stock jsonb,
  created_at timestamp default now()
);

-- Статус синхронизации
create table if not exists public.sync_status (
  id serial primary key,
  last_sync timestamp
);

-- Склады
-- create table if not exists public.stores (
--   id uuid primary key,
--   name text not null
-- );

-- Включаем RLS
alter table public.categories enable row level security;
alter table public.products enable row level security;
alter table public.modifications enable row level security;
alter table public.sync_status enable row level security;
-- alter table public.stores enable row level security;
