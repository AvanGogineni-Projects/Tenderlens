import datetime as dt
import os

import psycopg
import pytest

from tenderlens import db, export

URL = os.environ.get("TEST_DATABASE_URL", "postgresql:///tenderlens_test")
D = dt.date(2025, 3, 1)


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(URL, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("no test database")
    c.execute("drop schema public cascade; create schema public")
    c.autocommit = False
    db.migrate(c)
    yield c
    c.close()


def rows(n_awards: int):
    buyers = [("SWE:2021000001", "Kommunen", n_awards, 1, 100.0, 2.5, D, D)]
    suppliers = [("SWE:5560000001", "Bygg AB", "SWE", "5560000001", "sme", n_awards, 1, 100.0, D, D,
                  "BYGG AB", "AB", None, None)]
    awards = [(f"p|LOT-{i}|ORG-2", "1-2025", f"LOT-{i}", D, "award", "Skola", "45000000", "45", "works", "open",
               "none", "SWE:2021000001", "SWE:5560000001", "Bygg AB", 100, "SEK", 9.0, False, 3, D)
              for i in range(n_awards)]
    awards.append(("p|LOT-x|ORG-9", "1-2025", "LOT-x", D, "signed", None, None, None, None, None, None,
                   "SWE:2021000001", None, None, None, None, None, False, None, None))  # natural person winner
    share = [("45", 2025, "SWE:5560000001", "Bygg AB", n_awards, 100.0, 1.0, 1)]
    return {"buyers": buyers, "suppliers": suppliers, "awards": awards, "market_share": share}


def test_load_replaces_everything_and_records_the_run(conn):
    assert export.load(conn, rows(4), "workspace.tenderlens")["awards"] == 5
    assert export.load(conn, rows(3), "workspace.tenderlens")["awards"] == 4
    assert conn.execute("select count(*) from awards").fetchone()[0] == 4
    runs = conn.execute("select row_counts->>'awards' from export_runs order by id").fetchall()
    assert runs == [("5",), ("4",)]


def test_refuses_to_shrink_awards_by_more_than_half(conn):
    export.load(conn, rows(10), "s")
    with pytest.raises(RuntimeError, match="refusing export"):
        export.load(conn, rows(2), "s")
    assert conn.execute("select count(*) from awards").fetchone()[0] == 11  # previous export intact


def test_app_role_is_read_only(conn):
    export.load(conn, rows(1), "s")
    with conn.transaction():
        conn.execute("set local role tenderlens_app")
        assert conn.execute("select count(*) from awards").fetchone()[0] == 2
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
        conn.execute("set local role tenderlens_app")
        conn.execute("delete from awards")


def test_queries_validate_identifiers():
    assert "from workspace.tenderlens.fct_awards" in export.queries("workspace.tenderlens")["awards"]
    for bad in ("x; drop table y", "a.b.c", ""):
        with pytest.raises(ValueError):
            export.queries(bad)
    assert set(export.queries("s")) == set(export.TABLES)


def test_migrations_are_committed_for_other_connections(conn):
    with psycopg.connect(URL) as other:
        assert other.execute("select count(*) from schema_migrations").fetchone()[0] >= 1
        assert other.execute("select 1 from pg_roles where rolname = 'tenderlens_app'").fetchone()
