# Tenderlens

Public-procurement intelligence on Databricks: every EU tender and award notice from TED, modelled
into who buys what from whom, at what price, and when contracts end. Swedish suppliers are joined to
the Bolagsverket company register.

**Status:** milestones 1–3 done (ingest → bronze → silver → dbt gold), running daily on Databricks Free Edition. See [docs/plan.md](docs/plan.md).

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
| `databricks.yml` | Asset bundle: schema, volume, pipeline, daily job ingest → pipeline → dbt build (serverless) |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
databricks bundle deploy            # needs `databricks auth login` first
databricks bundle run daily         # ingest new packages, then refresh bronze
```

The first run backfills 2024 → today (~700 packages, ~6.5 GB) into the volume, not your laptop.

dbt locally against the dev schema (short-lived OAuth token, nothing stored):

```bash
source scripts/dbt_env.sh && cd dbt && ../.venv/bin/dbt build --profiles-dir profiles
```

Refresh inputs by hand (shortcuts, see the comments in the code):

```bash
.venv/bin/python -m tenderlens.fx eurofxref-hist.csv dbt/seeds/fx_monthly.csv   # ECB rates
databricks fs cp --overwrite companies.parquet dbfs:/Volumes/workspace/<schema>/raw/bolagsvakt/   # register
```
