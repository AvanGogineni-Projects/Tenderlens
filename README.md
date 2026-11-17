# Tenderlens

Public-procurement intelligence on Databricks: every EU tender and award notice from TED, modelled
into who buys what from whom, at what price, and when contracts end. Swedish suppliers are joined to
the Bolagsverket company register.

**Live:** https://tenderlens-eosin.vercel.app · **Status:** all five milestones done ([docs/plan.md](docs/plan.md)).
Production runs daily at 09:00 Stockholm: ingest → Lakeflow bronze/silver → `dbt build` → export to Postgres.

| | Numbers (17 Nov 2026) |
|---|---|
| Bronze | 728 TED daily packages, 2,443,328 notices (2024 → today) |
| Silver | 7.9M lots, 9.8M organisations, 8.0M award rows; 1,892 quarantined (legacy schema), 0 parse errors |
| Gold | 3.84M awards, 512k suppliers, 83k buyers; 32 dbt tests; full build < 1 min |
| App | Sweden slice: 72k awards, 13.7k suppliers, 1,057 buyers (Supabase, eu-west-3) |

## Layout

| Path | What |
|---|---|
| `src/tenderlens/ted.py` | TED daily packages: ids, fetch with retry + validation, unpack to notice rows |
| `src/tenderlens/ingest.py` | Job: download missing packages into the raw volume, atomically and idempotently |
| `src/tenderlens/pipelines/bronze.py` | Lakeflow pipeline: Auto Loader → `bronze_notices` with expectations |
| `src/tenderlens/eforms.py` | eForms parser: notice, lots, organisations, awards (privacy rules in the docstring) |
| `src/tenderlens/pipelines/silver.py` | Lakeflow silver: parse once, typed tables, quarantine |
| `src/tenderlens/fx.py` | ECB monthly rates → `dbt/seeds/fx_monthly.csv` |
| `dbt/` | Gold: `fct_awards`, `dim_supplier` (+ Bolagsverket register and Bolagsvakt risk), `dim_buyer`, `contract_expiries`, `market_share`, with tests |
| `src/tenderlens/export.py` | Prod job step: Sweden slice of gold → Postgres in one transaction (refuses to shrink awards by > half) |
| `src/tenderlens/api.py`, `asgi.py` | FastAPI, read-only role per request; deployed on Vercel |
| `migrations/` | Postgres serving schema |
| `web/` | Vite + React + Tailwind app |
| `databricks.yml` | Asset bundle: schema, volume, pipeline, daily job ingest → pipeline → dbt build (serverless) |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev,api]"
.venv/bin/pytest -q                       # export + API tests use Postgres (TEST_DATABASE_URL)
databricks bundle deploy                  # dev target: prefixed schema, schedule paused (needs `databricks auth login`)
databricks bundle run daily               # ingest → bronze/silver → dbt build
databricks bundle deploy -t prod          # prod target: schedule live, adds the export step
```

The first run backfills 2024 → today (~730 packages, ~6.5 GB) into the volume, not your laptop. The prod export
reads the Postgres connection string from the Databricks secret `tenderlens/database_url`; the web app reads
`DATABASE_URL` (transaction pooler) from Vercel's environment.

App locally (Postgres 17, then API on :8100 and web on :5180):

```bash
createdb tenderlens && DATABASE_URL=postgresql:///tenderlens .venv/bin/python -m tenderlens.db migrate
DATABASE_URL=postgresql:///tenderlens .venv/bin/uvicorn tenderlens.api:app --app-dir src --port 8100
npm --prefix web run dev -- --port 5180
```

dbt locally against the dev schema (short-lived OAuth token, nothing stored):

```bash
source scripts/dbt_env.sh && cd dbt && ../.venv/bin/dbt build --profiles-dir profiles
```

Refresh inputs by hand (shortcuts, see the comments in the code):

```bash
.venv/bin/python -m tenderlens.fx eurofxref-hist.csv dbt/seeds/fx_monthly.csv   # ECB rates
databricks fs cp --overwrite companies.parquet dbfs:/Volumes/workspace/<schema>/raw/bolagsvakt/   # register
```

## Known limits

- Framework agreements report a ceiling that every supplier on the framework repeats, so summed spend overstates
  what is billed; `framework` lets queries separate them.
- About two-thirds of award dates come from the contract signing date (`award_date_basis`); end dates are
  estimates when a notice only gives a duration.
- Values over EUR 5bn, or more than twice the notice's own total for ordinary contracts, are flagged
  (`value_suspect`) and left out of EUR totals.
- Databricks Free Edition is for non-commercial use; the data is open Delta, so a paid workspace is a target change.
