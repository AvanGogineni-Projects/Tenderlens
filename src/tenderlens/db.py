"""Postgres for the app: migrations.

    python -m tenderlens.db migrate      # apply new migrations/*.sql in order (DATABASE_URL)
"""

import argparse
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql:///tenderlens")


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply each migrations/NNN_*.sql not yet recorded, each in its own transaction."""
    conn.execute("create table if not exists schema_migrations (name text primary key, "
                 "applied_at timestamptz not null default now())")
    conn.commit()
    done = {r[0] for r in conn.execute("select name from schema_migrations")}
    conn.commit()  # close the read's implicit transaction, or each file below would only be a savepoint
    applied = []
    for path in sorted((ROOT / "migrations").glob("*.sql")):
        if path.name in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("insert into schema_migrations (name) values (%s)", [path.name])
        applied.append(path.name)
    return applied


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["migrate"])
    p.parse_args(argv)
    with psycopg.connect(DATABASE_URL) as conn:
        print("applied:", migrate(conn) or "nothing new")


if __name__ == "__main__":
    main()
