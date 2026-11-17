import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from tenderlens import api, export
from tests.test_export import (  # noqa: F401 (conn fixture comes from there)
    URL,
    conn,
    rows,
)


@pytest.fixture
def client(conn):  # noqa: F811
    export.load(conn, rows(3), "s")
    api.pool = ConnectionPool(URL, open=True, min_size=1, max_size=2,
                              kwargs={"row_factory": dict_row, "prepare_threshold": None})
    yield TestClient(api.app)
    api.pool.close()


def test_health_and_stats(client):
    assert client.get("/health").json()["last_export"]["row_counts"]["awards"] == 4
    stats = client.get("/v1/stats").json()
    assert stats["awards"] == 4 and stats["expiring_by_month"] == []  # sample contracts ended in 2025


def test_search_by_name_and_orgnr(client):
    assert [s["key"] for s in client.get("/v1/search", params={"q": "bygg"}).json()["suppliers"]] == ["SWE:5560000001"]
    assert client.get("/v1/search", params={"q": "556000-0001"}).json()["suppliers"][0]["orgnr"] == "5560000001"
    assert client.get("/v1/search", params={"q": "k"}).status_code == 422


def test_supplier_and_buyer_pages(client):
    s = client.get("/v1/suppliers/SWE:5560000001").json()
    assert s["supplier"]["name"] == "Bygg AB" and len(s["awards"]) == 3 and s["buyers"][0]["name"] == "Kommunen"
    b = client.get("/v1/buyers/SWE:2021000001").json()
    assert len(b["awards"]) == 4 and b["suppliers"][0]["awards"] == 3  # the natural-person award has no supplier
    assert b["expiring_count"] == 0  # sample contracts ended in 2025
    assert client.get("/v1/suppliers/nope").status_code == 404


def test_expiring_validates_input(client):
    assert client.get("/v1/expiring", params={"cpv": "4"}).status_code == 422
    assert client.get("/v1/expiring", params={"months": 99}).status_code == 422
    assert client.get("/v1/expiring", params={"cpv": "45"}).status_code == 200


def test_requests_cannot_write(client):
    # the dependency's role is read-only: prove it with the same role on the API's own pool
    with api.pool.connection() as c, pytest.raises(psycopg.errors.InsufficientPrivilege), c.transaction():
        c.execute("set local role tenderlens_app")
        c.execute("insert into export_runs (source_schema, row_counts) values ('x', '{}')")


def test_cdn_caches_successes_only(client):
    assert "s-maxage=3600" in client.get("/v1/stats").headers["cache-control"]
    assert "cache-control" not in client.get("/v1/suppliers/nope").headers
    assert "cache-control" not in client.get("/health").headers  # health stays live
