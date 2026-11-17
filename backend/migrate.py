"""Apply or roll back the versioned local PostgreSQL schema."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = (
    (
        "001_initial",
        ROOT / "migrations" / "001_initial.sql",
        ROOT / "migrations" / "001_initial_down.sql",
    ),
    (
        "002_forecast_metadata",
        Path(__file__).resolve().parent / "migrations" / "002_forecast_metadata.sql",
        Path(__file__).resolve().parent / "migrations" / "002_forecast_metadata_down.sql",
    ),
)


def migrate(database_url: str, rollback: bool = False) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS public.schema_migrations "
                    "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
                )
                if rollback:
                    applied = cursor.execute(
                        "SELECT version FROM public.schema_migrations ORDER BY version DESC"
                    ).fetchall()
                    for (version,) in applied:
                        migration = next(item for item in MIGRATIONS if item[0] == version)
                        cursor.execute(migration[2].read_text(encoding="utf-8"))
                        cursor.execute(
                            "DELETE FROM public.schema_migrations WHERE version = %s",
                            (version,),
                        )
                    return
                for version, script, _rollback in MIGRATIONS:
                    cursor.execute(
                        "SELECT 1 FROM public.schema_migrations WHERE version = %s",
                        (version,),
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(script.read_text(encoding="utf-8"))
                        cursor.execute(
                            "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                            (version,),
                        )


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
