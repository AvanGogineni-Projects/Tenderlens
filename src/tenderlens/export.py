"""Daily job step: copy the Sweden slice of gold into the app's Postgres.

    tenderlens-export --schema tenderlens      # on Databricks, after dbt; DB URL from secret tenderlens/database_url

All four tables are replaced in one transaction with DELETE + COPY: readers keep seeing the previous
export until the commit (TRUNCATE would lock them out for the whole load). A load that would shrink
`awards` below half of what is there now is refused, so a broken upstream run can't wipe the app.
"""

import argparse
import json
import re

import psycopg

COUNTRY = "SWE"
TABLES = {  # app table -> (columns, query against gold); order = insert order (parents first)
    "buyers": (
        ["buyer_key", "name", "awards", "suppliers", "value_eur", "avg_tenders_received", "first_award", "last_award"],
        ("select buyer_key, coalesce(name, '?') as name, awards, suppliers, value_eur, avg_tenders_received,"
        " first_award, last_award from {s}.dim_buyer where country = '{c}'"),
    ),
    "suppliers": (
        ["supplier_key", "name", "country", "orgnr", "size", "awards", "buyers", "value_eur", "first_award",
         "last_award", "registered_name", "legal_form", "deregistered_on", "deregistration_reason"],
        # suppliers that won from a Swedish buyer; counts are their totals in this slice
        ("select s.supplier_key, coalesce(s.name, '?') as name, s.country, s.swedish_orgnr as orgnr, s.size,"
        " count(*) as awards, count(distinct a.buyer_key) as buyers, sum(a.value_eur) as value_eur,"
        " min(a.award_date) as first_award, max(a.award_date) as last_award, s.registered_name, s.legal_form,"
        " s.deregistered_on, s.deregistration_reason"
        " from {s}.dim_supplier s join {s}.fct_awards a using (supplier_key)"
        " where a.buyer_country = '{c}' group by all"),
    ),
    "awards": (
        ["award_id", "publication_number", "lot_id", "award_date", "award_date_basis", "title", "cpv",
         "cpv_division", "contract_nature", "procedure_type", "framework", "buyer_key", "supplier_key",
         "supplier_name", "value", "currency", "value_eur", "value_suspect", "tenders_received", "expected_end"],
        ("select award_id, publication_number, lot_id, award_date, award_date_basis, title, cpv, cpv_division,"
        " contract_nature, procedure_type, framework, buyer_key,"
        " case when supplier_is_person then null else supplier_key end as supplier_key,"
        " case when supplier_is_person then null else supplier_name end as supplier_name,"
        " value, currency, value_eur, value_suspect, tenders_received, expected_end"
        " from {s}.fct_awards where buyer_country = '{c}' and buyer_key is not null"),
    ),
    "market_share": (
        ["cpv_division", "year", "supplier_key", "supplier_name", "awards", "value_eur", "share", "rank"],
        ("select cpv_division, year, supplier_key, coalesce(supplier_name, '?') as supplier_name, awards,"
        " value_eur, share, rank from {s}.market_share where buyer_country = '{c}'"),
    ),
}
MIN_RATIO = 0.5


def queries(schema: str, country: str = COUNTRY) -> dict[str, str]:
    """Gold queries for `schema` ('catalog.schema'); both are interpolated, so both are validated."""
    if not re.fullmatch(r"\w+(\.\w+)?", schema) or not re.fullmatch(r"[A-Z]{3}", country):
        raise ValueError("schema must be [catalog.]schema and country a 3-letter code")
    return {t: q.format(s=schema, c=country) for t, (_, q) in TABLES.items()}


def load(conn: psycopg.Connection, rows: dict[str, list[tuple]], source: str, min_ratio: float = MIN_RATIO) -> dict:
    """Replace the app tables with `rows` (tuples in TABLES column order) in one transaction."""
    counts = {t: len(rows[t]) for t in TABLES}
    with conn.transaction():
        current = conn.execute("select count(*) from awards").fetchone()[0]
        if current and counts["awards"] < current * min_ratio:
            raise RuntimeError(f"refusing export: {counts['awards']} awards would replace {current}")
        for table in reversed(list(TABLES)):  # children first
            conn.execute(f"delete from {table}")
        for table, (columns, _) in TABLES.items():
            with conn.cursor().copy(f"copy {table} ({', '.join(columns)}) from stdin") as copy:
                for row in rows[table]:
                    copy.write_row(row)
        conn.execute("insert into export_runs (source_schema, row_counts) values (%s, %s)",
                     [source, json.dumps(counts)])
    return counts


def main(argv: list[str] | None = None) -> None:  # pragma: no cover (runs on Databricks)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schema", required=True, help="catalog.schema of the gold tables, e.g. workspace.tenderlens")
    p.add_argument("--secret-scope", default="tenderlens")
    a = p.parse_args(argv)

    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    url = WorkspaceClient().dbutils.secrets.get(a.secret_scope, "database_url")
    rows = {table: [tuple(r) for r in spark.sql(sql).collect()] for table, sql in queries(a.schema).items()}
    with psycopg.connect(url) as conn:
        print("exported", load(conn, rows, a.schema))


if __name__ == "__main__":
    main()
