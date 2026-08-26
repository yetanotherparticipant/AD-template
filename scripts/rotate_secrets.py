#!/usr/bin/env python3

import argparse
import json
import secrets
from pathlib import Path


SECRETS = {
    "packmate": {
        "web_password": 32,
        "db_password": 32,
    },
    "firegex": {
        "password": 32,
    },
    "s4dfarm": {
        "server_password": 32,
        "external_redis_password": 32,
    },
}

SERVICE_TAGS = {
    "packmate": "packmate",
    "firegex": "firegex",
    "s4dfarm": "farm",
}


def generate_secrets():
    return {
        service: {
            key: secrets.token_urlsafe(length)[:length]
            for key, length in keys.items()
        }
        for service, keys in SECRETS.items()
    }


def read_sls(path: Path):
    values = {service: {} for service in SECRETS}
    urls = {}

    lines = path.read_text().splitlines()
    current = None

    for line in lines:
        stripped = line.strip()

        if not line.startswith("  ") and stripped.endswith(":"):
            current = stripped[:-1]
            continue

        if current not in SECRETS:
            continue

        if stripped.startswith("url:"):
            urls[current] = stripped.split(":", 1)[1].strip()
            continue

        for key in SECRETS[current]:
            prefix = f"{key}:"

            if stripped.startswith(prefix):
                values[current][key] = stripped[len(prefix):].strip()
                break

    return values, urls


def update_sls(path: Path, values, urls):
    lines = path.read_text().splitlines()
    result = []

    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not line.startswith("  ") and stripped.endswith(":"):
            service = stripped[:-1]
            result.append(line)
            i += 1

            if service not in SECRETS:
                continue

            seen_url = False

            while i < len(lines):
                line = lines[i]

                if not line.startswith("  ") and line.strip().endswith(":"):
                    break

                if line.startswith("  url:"):
                    if service in urls and not seen_url:
                        result.append(f"  url: {urls[service]}")
                        seen_url = True
                    else:
                        result.append(line)
                        seen_url = True
                else:
                    replaced = False

                    for key, value in values[service].items():
                        if line.startswith(f"  {key}:"):
                            result.append(f"  {key}: {value}")
                            replaced = True
                            break

                    if not replaced:
                        result.append(line)

                i += 1

            if service in urls and not seen_url:
                result.append(f"  url: {urls[service]}")

            continue

        result.append(line)
        i += 1

    path.write_text("\n".join(result) + "\n")


def update_services(path: Path, values, urls):
    data = json.loads(path.read_text())

    for service, tag in SERVICE_TAGS.items():
        if service not in values:
            continue

        password = (
            values[service].get("server_password")
            or values[service].get("password")
            or values[service].get("web_password")
        )

        if password is None:
            print(
                f"warning: no password found for '{service}' in secrets data; "
                f"skipping credential update for this service"
            )
            continue

        item = next(
            (item for item in data if item.get("tag") == tag),
            None,
        )

        if item is None:
            item = {
                "id": secrets.token_hex(6),
                "name": service.capitalize(),
                "url": urls.get(service, ""),
                "tag": tag,
                "note": "",
                "creds": [],
            }
            data.append(item)

        if service in urls:
            item["url"] = urls[service]

        cred = next(
            (
                cred
                for cred in item.get("creds", [])
                if cred.get("key") == "pass"
            ),
            None,
        )

        if cred is None:
            item.setdefault("creds", []).append({
                "key": "pass",
                "value": password,
            })
        else:
            cred["value"] = password

    path.write_text(json.dumps(data, indent=2) + "\n")


def parse_url_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"invalid --url value {value!r}; expected format service=url"
        )

    service, url = value.split("=", 1)

    if not service or not url:
        raise argparse.ArgumentTypeError(
            f"invalid --url value {value!r}; expected format service=url"
        )

    return service, url


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "secrets_path",
        type=Path,
    )

    parser.add_argument(
        "--services-path",
        type=Path,
    )

    parser.add_argument(
        "--url",
        action="append",
        default=[],
        type=parse_url_arg,
    )

    parser.add_argument(
        "--sync",
        action="store_true",
        help="sync existing secrets.sls to services.json without rotating secrets",
    )

    args = parser.parse_args()

    if args.sync:
        values, urls = read_sls(args.secrets_path)

        if args.services_path is None:
            parser.error("--services-path is required with --sync")

    else:
        values = generate_secrets()
        urls = dict(args.url)

        update_sls(
            args.secrets_path,
            values,
            urls,
        )

    if args.services_path:
        update_services(
            args.services_path,
            values,
            urls,
        )


if __name__ == "__main__":
    main()
