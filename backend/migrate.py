"""Apply or roll back the versioned local PostgreSQL schema."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "migrations" / "001_initial.sql"
ROLLBACK = ROOT / "migrations" / "001_initial_down.sql"
VERSION = "001_initial"


def migrate(database_url: str, rollback: bool = False) -> None:
    script = ROLLBACK if rollback else MIGRATION
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                if rollback:
                    cursor.execute(script.read_text(encoding="utf-8"))
                    cursor.execute(
                        "CREATE TABLE IF NOT EXISTS public.schema_migrations "
                        "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
                    )
                    cursor.execute("DELETE FROM public.schema_migrations WHERE version = %s", (VERSION,))
                    return
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS public.schema_migrations "
                    "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
                )
                cursor.execute("SELECT 1 FROM public.schema_migrations WHERE version = %s", (VERSION,))
                if cursor.fetchone() is None:
                    cursor.execute(script.read_text(encoding="utf-8"))
                    cursor.execute("INSERT INTO public.schema_migrations (version) VALUES (%s)", (VERSION,))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    migrate(args.database_url, args.rollback)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
