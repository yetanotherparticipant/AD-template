#!/usr/bin/env python3

import json
import os
import sys
import sqlite3
from typing import Any, Dict, Iterable, List


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=3)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(conn: sqlite3.Connection) -> List[str]:
    tables: List[str] = []
    try:
        cur = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        rows = cur.fetchall()
        tables = [r[0] for r in rows]
    except Exception as ex:
        eprint(f"[!] Failed to list tables: {ex}")
    return tables


def stream_table_rows(conn: sqlite3.Connection, table: str, batch: int = 1000) -> Iterable[Dict[str, Any]]:
    try:
        cur = conn.execute(f"SELECT * FROM \"{table}\"")
        while True:
            rows = cur.fetchmany(batch)
            if not rows:
                break
            for row in rows:
                try:
                    yield {k: row[k] for k in row.keys()}
                except Exception:
                    desc = [d[0] for d in cur.description] if cur.description else []
                    yield {desc[i]: row[i] for i in range(len(desc))}
    except Exception as ex:
        eprint(f"[!] Failed to read table {table}: {ex}")
        return


def dump_all_sqlite(db_path: str) -> None:
    if not os.path.exists(db_path):
        eprint(f"[!] SQLite database file not found: {db_path}")
        return

    try:
        conn = connect(db_path)
    except Exception as ex:
        eprint(f"[!] Failed to connect to SQLite db {db_path}: {ex}")
        return

    try:
        tables = list_tables(conn)
        for table in tables:
            for row in stream_table_rows(conn, table):
                try:
                    print(
                        json.dumps(
                            {
                                "db": db_path,
                                "table": table,
                                "row": row,
                            },
                            default=str,
                        ),
                        flush=True,
                    )
                except Exception as jex:
                    eprint(f"[!] JSON encode error for {db_path}.{table}: {jex}")
                    continue
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <sqlite_db_path>")
        return 1

    db_path = sys.argv[1]
    dump_all_sqlite(db_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
