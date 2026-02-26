#!/usr/bin/env python3
import os
from pathlib import Path


def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url or not db_url.startswith('postgresql://'):
        raise SystemExit('DATABASE_URL must be a postgresql:// URL (sqlite disabled)')

    try:
        import psycopg2
    except Exception as e:
        raise SystemExit(f'psycopg2 required for postgres DATABASE_URL: {e}')

    schema_path = Path('/home/marten/.openclaw/workspace/horus/db/schema.sql')
    sql = schema_path.read_text()

    con = psycopg2.connect(db_url)
    con.autocommit = True
    try:
        with con.cursor() as cur:
            cur.execute(sql)
        print('SCHEMA_OK postgres')
    finally:
        con.close()


if __name__ == '__main__':
    main()
