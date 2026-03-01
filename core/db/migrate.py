from __future__ import annotations

import argparse
from pathlib import Path

from core.db.postgres import PostgresDB


def apply_migrations(db: PostgresDB, migrations_dir: Path) -> None:
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"No migration files found in {migrations_dir}")

    with db.connection() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            for path in migration_files:
                version = path.name
                cur.execute("SELECT 1 FROM schema_migrations WHERE version=%s", (version,))
                if cur.fetchone():
                    continue

                sql = path.read_text()
                cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations(version) VALUES(%s)", (version,))


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply PostgreSQL migrations")
    parser.add_argument("--migrations-dir", default=str(Path(__file__).parent / "migrations"))
    args = parser.parse_args()

    db = PostgresDB()
    apply_migrations(db, Path(args.migrations_dir))
    print("migrations_applied")


if __name__ == "__main__":
    main()
