# Tenderlens — plan

Public-procurement intelligence on Databricks. Ingest every EU tender and award notice from TED, model
who buys what from whom and when contracts end, and join Swedish suppliers to the Bolagsverket company
register (from Bolagsvakt).

## Product question it answers

For a company selling to the public sector:

1. Which open tenders fit me (by CPV code, region, value)?
2. Who wins these contracts, at what price, against how many bidders?
3. Which of my competitors' contracts expire in the next 6–18 months (the next tender is coming)?

## Data (verified 2026-11-16)

| Source | Access | Size |
|---|---|---|
| TED daily packages `ted.europa.eu/packages/daily/{yyyy}{issue:05d}` | No key, tar.gz of eForms XML | ~9 MB / ~2,000 notices per day, ~250 days a year |
| TED Search API v3 `POST api.ted.europa.eu/v3/notices/search` | No key | Used for spot checks only |
| Bolagsverket register (via Bolagsvakt silver) | Open data | 982k active companies |

Notices from 2024 on are all eForms (UBL). Older TED-schema notices are out of scope. Swedish award
notices carry the winner's org number, so they join directly to the register.

## Architecture

```
TED daily .tar.gz ──ingest job──▶ UC Volume raw/ted/daily/{yyyy}/       (idempotent, atomic)
                                   │ Auto Loader (binaryFile, incremental)
                                   ▼
                       bronze_notices     one row per notice XML, expectations
                                   │ eForms parser (pure Python, unit-tested)
                                   ▼
          silver: notices · lots · buyers · organisations · tenders · contracts
                                   │ dbt (tests, docs, lineage)
                                   ▼
          gold: fct_awards · dim_buyer · dim_supplier (+ register) · contract_expiries · market_share
                                   │ export
                                   ▼
                       Postgres + FastAPI + React (as Bolagsvakt), deployed on Vercel
```

- **Platform:** Databricks Free Edition (serverless, Unity Catalog, Lakeflow pipelines, Jobs), deployed
  as a Databricks Asset Bundle from git. Free Edition is non-commercial; the data stays in open Delta
  format, so a paid workspace later is a config change, not a rewrite.
- **Parsing logic is plain Python** (stdlib XML) and runs inside Spark via `mapInPandas`, so it is
  unit-tested locally without a cluster.

## Milestones

1. **Ingest → bronze.** Package discovery, download with retry, atomic write to a volume, Auto Loader
   bronze table with expectations, daily job, backfill 2024 → today.
2. **eForms → silver.** Parse the notice graph (lot → result → tender → party → organisation →
   contract), currency and value handling, duplicates/corrections (notice versions), quarantine table.
3. **dbt → gold.** Awards fact, buyer/supplier dims joined to the register, contract expiry estimates,
   market share per CPV and region; dbt tests and docs.
4. **Product.** Export gold to Postgres, API + UI: supplier page, buyer page, "contracts expiring"
   alerts by CPV. Deploy.
5. **Story.** Launch film, portfolio entry, Data Engineer resume.
