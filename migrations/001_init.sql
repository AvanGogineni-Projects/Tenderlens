-- Serving tables for the public app: a Sweden slice of the Databricks gold layer, replaced by each export.
-- Public procurement data only; Bolagsvakt risk scores are deliberately not exported.
create extension if not exists pg_trgm;

create table buyers (
    buyer_key text primary key,
    name text not null,
    awards integer not null,
    suppliers integer not null,
    value_eur double precision,
    avg_tenders_received real,
    first_award date,
    last_award date
);

create table suppliers (
    supplier_key text primary key,
    name text not null,
    country text,
    orgnr text,
    size text,
    awards integer not null,
    buyers integer not null,
    value_eur double precision,
    first_award date,
    last_award date,
    registered_name text,
    legal_form text,
    deregistered_on date,
    deregistration_reason text
);

create table awards (
    award_id text primary key,
    publication_number text not null,
    lot_id text,
    award_date date not null,
    award_date_basis text not null,
    title text,
    cpv text,
    cpv_division text,
    contract_nature text,
    procedure_type text,
    framework text,
    buyer_key text not null references buyers on delete cascade,
    supplier_key text references suppliers on delete cascade,  -- null for natural persons
    supplier_name text,                                        -- null for natural persons
    value numeric(22, 2),
    currency text,
    value_eur double precision,
    value_suspect boolean not null,
    tenders_received integer,
    expected_end date
);
create index awards_buyer on awards (buyer_key, award_date desc);
create index awards_supplier on awards (supplier_key, award_date desc);
create index awards_expiring on awards (expected_end) where expected_end is not null;
create index awards_cpv on awards (cpv_division, expected_end);

create table market_share (
    cpv_division text not null,
    year integer not null,
    supplier_key text not null references suppliers on delete cascade,
    supplier_name text not null,
    awards integer not null,
    value_eur double precision not null,
    share double precision not null,
    rank integer not null,
    primary key (cpv_division, year, supplier_key)
);

create table export_runs (
    id bigint generated always as identity primary key,
    finished_at timestamptz not null default now(),
    source_schema text not null,
    row_counts jsonb not null
);

create index buyers_name_trgm on buyers using gist (lower(name) gist_trgm_ops);
create index suppliers_name_trgm on suppliers using gist (lower(name) gist_trgm_ops);
create index suppliers_orgnr on suppliers (orgnr);

-- The API runs every request as this role: read-only on purpose.
do $$ begin
    if not exists (select 1 from pg_roles where rolname = 'tenderlens_app') then
        create role tenderlens_app nologin;
    end if;
end $$;
grant tenderlens_app to current_user;  -- lets the API's login role `set local role tenderlens_app`
grant usage on schema public to tenderlens_app;
grant select on buyers, suppliers, awards, market_share, export_runs to tenderlens_app;

-- On Supabase: the built-in API roles get nothing (the Data API is also switched off).
do $$ begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        revoke all on all tables in schema public from anon, authenticated;
        alter default privileges in schema public revoke all on tables from anon, authenticated;
    end if;
end $$;
