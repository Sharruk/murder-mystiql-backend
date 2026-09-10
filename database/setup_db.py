"""
Database Setup Script for MurderMystiQL.
Executes roles.sql, game_schema.sql, investigation_schema.sql, and seed.sql.
Can be run with:
    python database/setup_db.py --admin-url postgresql://postgres:postgres@localhost:5432/murdermystiql
"""

import argparse
import os
import sys
from pathlib import Path


def run_sql_files(admin_url: str):
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    db_dir = Path(__file__).parent

    # Split into database name
    print(f"Connecting to database via: {admin_url}")
    conn = psycopg2.connect(admin_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    sql_files = [
        "roles.sql",
        "game_schema.sql",
        "investigation_schema.sql",
        "seed.sql",
    ]

    for fname in sql_files:
        fpath = db_dir / fname
        if not fpath.exists():
            print(f"Error: {fname} not found at {fpath}")
            continue
        print(f"Executing {fname}...")
        with open(fpath, "r", encoding="utf-8") as f:
            sql_content = f.read()
        try:
            cursor.execute(sql_content)
            print(f"Successfully executed {fname}.")
        except Exception as e:
            print(f"Failed executing {fname}: {e}")
            raise

    cursor.close()
    conn.close()
    print("Database setup complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup MurderMystiQL PostgreSQL Database")
    parser.add_argument(
        "--admin-url",
        default=os.getenv("ADMIN_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/murdermystiql"),
        help="PostgreSQL connection string with superuser privileges (e.g. postgres)",
    )
    args = parser.parse_args()
    try:
        run_sql_files(args.admin_url)
    except Exception as exc:
        print(f"Setup aborted: {exc}")
        sys.exit(1)
