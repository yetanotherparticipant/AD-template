#!/usr/bin/env python3
import sys
import re
import random
import requests

USE_CUSTOM_USER_AGENT = False
ATTACK_DATA_URL = "http://N.N.N.N"
FLAG_RX = re.compile(r"[A-Z0-9]{31}=")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
]


def get_attack_data(target_ip):
    """
    Download attack data and return data for the target.

    TODO:
    Adapt this function to the attack data format used by the current farm.

    Common examples:

        {"10.10.10.5": {...}}
            -> return data.get(target_ip, {})

        {"service": {"10.10.10.5": {...}}}
            -> return data.get("service", {}).get(target_ip, {})

        {"5": {...}}
            -> team_id = target_ip.split(".")[-1] # Or another way to get it
               return data.get(team_id, {})
    """

    headers = {}
    if USE_CUSTOM_USER_AGENT:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    try:
        r = requests.get(ATTACK_DATA_URL, headers=headers, timeout=3)
        r.raise_for_status()

        data = r.json()

        if not isinstance(data, dict):
            return {}

        # TODO: Replace this line according to the attack data structure.
        return data.get(target_ip, {})

    except requests.RequestException as e:
        print(f"[-] Failed to fetch attack data: {e}", file=sys.stderr, flush=True)
        return {}
    except ValueError as e:
        print(f"[-] Invalid JSON received: {e}", file=sys.stderr, flush=True)
        return {}


def exploit(target_ip, team_data):
    flags = set()

    headers = {}
    if USE_CUSTOM_USER_AGENT:
        headers["User-Agent"] = random.choice(USER_AGENTS)

    # -------------------------------------------------------------------------
    # TODO: IMPLEMENT YOUR EXPLOIT LOGIC HERE
    try: # example
        token = team_data.get("token")
        if token:
            headers["X-Auth-Token"] = token

        url = f"http://{target_ip}:8080/flag"
        r = requests.get(url, headers=headers, timeout=4)

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
    team_data = get_attack_data(target_ip)

    try:
        found_flags = exploit(target_ip, team_data)

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