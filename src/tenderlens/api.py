"""Tenderlens API: read-only views of Swedish public procurement.

    uvicorn tenderlens.api:app --reload

Every request runs in a transaction as `tenderlens_app`, a role that can only SELECT, so a bug here
can't change data. No accounts: everything served is public procurement data. Bolagsvakt risk scores
are not in this database on purpose.
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from tenderlens.db import DATABASE_URL

# prepare_threshold=None: Supabase's transaction pooler hands each transaction to any backend, so
# server-side prepared statements must be off. Small pool: each serverless instance holds its own.
pool = ConnectionPool(DATABASE_URL, open=False, min_size=1, max_size=int(os.environ.get("DB_POOL_MAX", "5")),
                      kwargs={"row_factory": dict_row, "prepare_threshold": None})
CPV_DIVISION = r"^\d{2}$"


def db_pool() -> ConnectionPool:
    """The pool, opened on first use: a serverless runtime may not run the lifespan hook."""
    pool.open()  # no-op when already open
    return pool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_pool()
    yield
    pool.close()


app = FastAPI(title="Tenderlens", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
                   allow_methods=["GET"], allow_headers=["Content-Type"])


# Data changes once a day, so let Vercel's CDN answer repeats: each URL reads Postgres at most once an hour.
# (Elvarsel blew through Supabase's 5 GB free egress without this.) Errors are never cached.
CACHE_CONTROL = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"


@app.middleware("http")
async def cache_headers(request, call_next):
    response = await call_next(request)
    if request.method == "GET" and request.url.path.startswith("/v1/") and response.status_code == 200:
        response.headers["Cache-Control"] = CACHE_CONTROL
    return response


def read_db():
    with db_pool().connection() as conn, conn.transaction():
        conn.execute("set local role tenderlens_app")
        yield conn


DB = Depends(read_db)

AWARD_COLUMNS = """a.award_id, a.publication_number, a.award_date, a.title, a.cpv, a.cpv_division,
    a.contract_nature, a.procedure_type, a.framework, a.value, a.currency, a.value_eur, a.value_suspect,
    a.tenders_received, a.expected_end, a.buyer_key, b.name as buyer_name, a.supplier_key, a.supplier_name"""


@app.get("/health")
def health(conn=DB):
    run = conn.execute("select finished_at, row_counts from export_runs order by id desc limit 1").fetchone()
    return {"ok": True, "last_export": run}


@app.get("/v1/stats")
def stats(conn=DB):
    totals = conn.execute("""
        select (select count(*) from awards) as awards, (select count(*) from buyers) as buyers,
               (select count(*) from suppliers) as suppliers,
               (select count(*) from awards where expected_end between current_date
                                                    and current_date + interval '12 months') as expiring_12m,
               (select min(award_date) from awards) as since""").fetchone()
    by_month = conn.execute("""
        select to_char(date_trunc('month', expected_end), 'YYYY-MM') as month, count(*) as contracts,
               sum(value_eur) as value_eur
        from awards where expected_end between current_date and current_date + interval '12 months'
        group by 1 order by 1""").fetchall()
    divisions = conn.execute("""
        select cpv_division, count(*) as contracts from awards
        where expected_end between current_date and current_date + interval '12 months' and cpv_division is not null
        group by 1 order by 2 desc limit 12""").fetchall()
    return {**totals, "expiring_by_month": by_month, "expiring_by_division": divisions}


@app.get("/v1/search")
def search(q: str = Query(min_length=2, max_length=80), conn=DB):
    """Buyers and suppliers by name (fuzzy), or a supplier by org number."""
    digits = "".join(ch for ch in q if ch.isdigit())
    if len(digits) == 10:
        suppliers = conn.execute("select supplier_key as key, name, orgnr, awards from suppliers where orgnr = %s",
                                 [digits]).fetchall()
        return {"buyers": [], "suppliers": suppliers}
    pattern = q.lower()
    # names starting with the query, then containing it, then fuzzy matches; busiest first within each
    rank = """where lower(name) %% %(q)s or lower(name) like '%%' || %(q)s || '%%'
              order by lower(name) like %(q)s || '%%' desc, lower(name) like '%%' || %(q)s || '%%' desc,
                       similarity(lower(name), %(q)s) desc, awards desc limit 8"""
    buyers = conn.execute("select buyer_key as key, name, awards from buyers " + rank, {"q": pattern}).fetchall()
    suppliers = conn.execute("select supplier_key as key, name, orgnr, awards from suppliers " + rank,
                             {"q": pattern}).fetchall()
    return {"buyers": buyers, "suppliers": suppliers}


@app.get("/v1/suppliers/{key}")
def supplier(key: str, conn=DB):
    row = conn.execute("select * from suppliers where supplier_key = %s", [key]).fetchone()
    if row is None:
        raise HTTPException(404, "supplier not found")
    awards = conn.execute(f"""select {AWARD_COLUMNS} from awards a join buyers b using (buyer_key)
                              where a.supplier_key = %s order by a.award_date desc limit 100""", [key]).fetchall()
    buyers = conn.execute("""select a.buyer_key as key, b.name, count(*) as awards, sum(a.value_eur) as value_eur
                             from awards a join buyers b using (buyer_key) where a.supplier_key = %s
                             group by 1, 2 order by awards desc, value_eur desc nulls last limit 10""", [key]).fetchall()
    markets = conn.execute("""select cpv_division, year, share, rank, value_eur from market_share
                              where supplier_key = %s and rank <= 10 order by year desc, share desc limit 12""",
                           [key]).fetchall()
    return {"supplier": row, "awards": awards, "buyers": buyers, "markets": markets}


@app.get("/v1/buyers/{key}")
def buyer(key: str, conn=DB):
    row = conn.execute("select * from buyers where buyer_key = %s", [key]).fetchone()
    if row is None:
        raise HTTPException(404, "buyer not found")
    awards = conn.execute(f"""select {AWARD_COLUMNS} from awards a join buyers b using (buyer_key)
                              where a.buyer_key = %s order by a.award_date desc limit 100""", [key]).fetchall()
    suppliers = conn.execute("""select supplier_key as key, max(supplier_name) as name, count(*) as awards,
                                       sum(value_eur) as value_eur
                                from awards where buyer_key = %s and supplier_key is not null
                                group by 1 order by awards desc, value_eur desc nulls last limit 10""", [key]).fetchall()
    expiring = conn.execute(f"""select {AWARD_COLUMNS} from awards a join buyers b using (buyer_key)
                                where a.buyer_key = %s and a.expected_end >= current_date
                                order by a.expected_end limit 20""", [key]).fetchall()
    expiring_count = conn.execute("select count(*) from awards where buyer_key = %s and expected_end >= current_date",
                                  [key]).fetchone()["count"]
    return {"buyer": row, "awards": awards, "suppliers": suppliers, "expiring": expiring,
            "expiring_count": expiring_count}


@app.get("/v1/expiring")
def expiring(cpv: str | None = Query(None, pattern=CPV_DIVISION), months: int = Query(12, ge=1, le=36),
             limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=10_000), conn=DB):
    """Contracts ending within `months`, soonest first: the next tender for this work is coming."""
    rows = conn.execute(f"""select {AWARD_COLUMNS} from awards a join buyers b using (buyer_key)
                            where a.expected_end between current_date and current_date + make_interval(months => %(m)s)
                              and (%(cpv)s::text is null or a.cpv_division = %(cpv)s)
                            order by a.expected_end, a.value_eur desc nulls last
                            limit %(limit)s offset %(offset)s""",
                        {"m": months, "cpv": cpv, "limit": limit, "offset": offset}).fetchall()
    return {"contracts": rows}


@app.get("/v1/markets/{cpv}")
def market(cpv: str, year: int | None = Query(None, ge=2023, le=2100), conn=DB):
    if not cpv.isdigit() or len(cpv) != 2:
        raise HTTPException(422, "cpv must be a 2-digit CPV division")
    year = year or conn.execute("select max(year) from market_share where cpv_division = %s", [cpv]).fetchone()["max"]
    rows = conn.execute("""select supplier_key as key, supplier_name as name, awards, value_eur, share, rank
                           from market_share where cpv_division = %s and year = %s order by rank limit 20""",
                        [cpv, year]).fetchall()
    return {"cpv_division": cpv, "year": year, "suppliers": rows}
