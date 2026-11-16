# Tenderlens

Public-procurement intelligence on Databricks: every EU tender and award notice from TED, modelled
into who buys what from whom, at what price, and when contracts end. Swedish suppliers are joined to
the Bolagsverket company register.

**Status:** milestone 1 (ingest → bronze). See [docs/plan.md](docs/plan.md).

## Layout

| Path | What |
|---|---|
| `src/tenderlens/ted.py` | TED daily packages: ids, fetch with retry + validation, unpack to notice rows |
| `src/tenderlens/ingest.py` | Job: download missing packages into the raw volume, atomically and idempotently |
| `src/tenderlens/pipelines/bronze.py` | Lakeflow pipeline: Auto Loader → `bronze_notices` with expectations |
| `databricks.yml` | Asset bundle: schema, volume, pipeline, daily job (Free Edition, serverless) |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
databricks bundle deploy            # needs `databricks auth login` first
databricks bundle run daily         # ingest new packages, then refresh bronze
```

The first run backfills 2024 → today (~700 packages, ~6.5 GB) into the volume, not your laptop.
