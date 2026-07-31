#!/usr/bin/env python3
import sys
import re
import random
import requests

USE_CUSTOM_USER_AGENT = False
FLAG_RX = re.compile(r"[A-Z0-9]{31}=")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
]


def exploit(target_ip):
    flags = set()

    headers = {}
    if USE_CUSTOM_USER_AGENT:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    # -------------------------------------------------------------------------
    # TODO: IMPLEMENT YOUR EXPLOIT LOGIC HERE
    try: # example
        url = f"http://{target_ip}:8080/flag"

        r = requests.get(url, headers=headers, timeout=4)
        r.raise_for_status()

        for flag in FLAG_RX.findall(r.text):
            flags.add(flag)

    except requests.RequestException as e:
        print(f"[-] Request failed for {target_ip}: {e}", file=sys.stderr, flush=True)
    # -------------------------------------------------------------------------

    return flags


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target_ip>", file=sys.stderr, flush=True)
        sys.exit(1)

    target_ip = sys.argv[1]

    try:
        found_flags = exploit(target_ip)

        if found_flags is None:
            found_flags = []
        elif isinstance(found_flags, str):
            found_flags = [found_flags]

        for flag in found_flags:
            clean_flag = str(flag).strip()
            if FLAG_RX.fullmatch(clean_flag):
                print(clean_flag, flush=True)

    except Exception as e:
        print(f"[-] Exploit error for {target_ip}: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()