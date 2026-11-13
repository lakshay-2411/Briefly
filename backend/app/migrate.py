"""Apply SQL migrations in order: python -m app.migrate

Migrations are written to be idempotent (create ... if not exists), so re-running is safe.
"""

from pathlib import Path

import psycopg

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def main() -> None:
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            conn.execute(path.read_text())
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()
