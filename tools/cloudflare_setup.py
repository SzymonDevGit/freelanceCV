#!/usr/bin/env python3
"""
Bring both Cloudflare zones to the state the SEO work needs.

  python tools/cloudflare_setup.py            # PLAN: read-only, shows the diff
  python tools/cloudflare_setup.py --apply    # make the changes

Reads the API token from the CLOUDFLARE_API_TOKEN environment variable. The
token is never printed, logged or written anywhere.

What it does, all idempotent — re-running is safe and reports "ok" for anything
already correct:

  szymonpecherski.online (the old domain, currently unreachable)
    - A  @    -> 192.0.2.1, proxied   } so Cloudflare has something to answer
    - A  www  -> 192.0.2.1, proxied   } on; nothing ever reaches an origin
    - redirect rule: everything -> https://cheltenhamdata.co.uk<path>, 301
    - Always Use HTTPS: on

  cheltenhamdata.co.uk (the live site)
    - redirect rule: www -> apex, 301, path and query preserved
    - Always Use HTTPS: on
    - TXT _dmarc (p=none, monitor only — cannot affect mail delivery)

Redirect rules are merged by description: an existing rule with the same
description is replaced, everything else in the ruleset is left alone.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.cloudflare.com/client/v4"
OLD = "szymonpecherski.online"
NEW = "cheltenhamdata.co.uk"
DUMMY_IP = "192.0.2.1"          # RFC 5737 TEST-NET-1: reserved, never routable
DMARC = "v=DMARC1; p=none; rua=mailto:szymonpecherski@gmail.com"

RESET, RED, YEL, GRN, DIM, BOLD = (
    "\033[0m", "\033[31m", "\033[33m", "\033[32m", "\033[2m", "\033[1m")

planned: list[str] = []
problems: list[str] = []


def token() -> str:
    t = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not t:
        sys.exit(
            "CLOUDFLARE_API_TOKEN is not set in this shell.\n"
            "Set it first (session-only, disappears when you close the window):\n"
            '  $env:CLOUDFLARE_API_TOKEN = "your-token"'
        )
    return t


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token()}",
                 "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            data = json.loads(raw)
            if exc.code == 404:
                return data
            msgs = "; ".join(e.get("message", "?") for e in data.get("errors", []))
            raise SystemExit(f"{RED}Cloudflare API {exc.code} on {method} {path}: "
                             f"{msgs}{RESET}") from None
        except json.JSONDecodeError:
            raise SystemExit(f"{RED}Cloudflare API {exc.code} on {method} {path}"
                             f"{RESET}") from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"{RED}network error: {exc.reason}{RESET}") from None


def ok(msg: str) -> None:
    print(f"  {GRN}ok{RESET}      {msg}")


def todo(msg: str) -> None:
    planned.append(msg)
    print(f"  {YEL}change{RESET}  {msg}")


def done(msg: str) -> None:
    print(f"  {GRN}done{RESET}    {msg}")


def zone_id(name: str) -> str | None:
    res = call("GET", f"/zones?name={name}")
    result = res.get("result") or []
    if not result:
        problems.append(f"zone {name} not found — is it in this account, and does "
                        f"the token include it?")
        return None
    return result[0]["id"]


# ------------------------------------------------------------------ records --
def ensure_a_record(zid: str, zone: str, name: str, apply: bool) -> None:
    fqdn = zone if name == "@" else f"{name}.{zone}"
    res = call("GET", f"/zones/{zid}/dns_records?name={fqdn}&type=A")
    existing = res.get("result") or []

    if not existing:
        if apply:
            call("POST", f"/zones/{zid}/dns_records",
                 {"type": "A", "name": fqdn, "content": DUMMY_IP,
                  "proxied": True, "ttl": 1,
                  "comment": "redirect-only host; answered at the edge"})
            done(f"created A {fqdn} -> {DUMMY_IP} (proxied)")
        else:
            todo(f"create A {fqdn} -> {DUMMY_IP} (proxied)")
        return

    rec = existing[0]
    needs = rec["content"] != DUMMY_IP or not rec.get("proxied")
    if not needs:
        ok(f"A {fqdn} -> {DUMMY_IP} (proxied)")
        return
    if apply:
        call("PATCH", f"/zones/{zid}/dns_records/{rec['id']}",
             {"content": DUMMY_IP, "proxied": True, "ttl": 1})
        done(f"updated A {fqdn} -> {DUMMY_IP} (proxied)")
    else:
        todo(f"update A {fqdn}: {rec['content']} proxied={rec.get('proxied')} "
             f"-> {DUMMY_IP} proxied=True")


def ensure_txt(zid: str, zone: str, name: str, content: str, apply: bool) -> None:
    fqdn = f"{name}.{zone}"
    res = call("GET", f"/zones/{zid}/dns_records?name={fqdn}&type=TXT")
    existing = res.get("result") or []
    if existing:
        ok(f"TXT {fqdn} already present")
        return
    if apply:
        call("POST", f"/zones/{zid}/dns_records",
             {"type": "TXT", "name": fqdn, "content": content, "ttl": 1})
        done(f"created TXT {fqdn}")
    else:
        todo(f"create TXT {fqdn} = {content!r}")


# ----------------------------------------------------------------- settings --
def ensure_https(zid: str, zone: str, apply: bool) -> None:
    res = call("GET", f"/zones/{zid}/settings/always_use_https")
    current = (res.get("result") or {}).get("value")
    if current == "on":
        ok(f"{zone}: Always Use HTTPS is on")
        return
    if apply:
        call("PATCH", f"/zones/{zid}/settings/always_use_https", {"value": "on"})
        done(f"{zone}: Always Use HTTPS -> on")
    else:
        todo(f"{zone}: Always Use HTTPS {current!r} -> 'on'")


# ------------------------------------------------------------ redirect rules --
PHASE = "http_request_dynamic_redirect"


def build_rule(description: str, expression: str, target_expr: str) -> dict:
    return {
        "description": description,
        "expression": expression,
        "action": "redirect",
        "enabled": True,
        "action_parameters": {
            "from_value": {
                "status_code": 301,
                "target_url": {"expression": target_expr},
                "preserve_query_string": True,
            }
        },
    }


def ensure_redirect(zid: str, zone: str, rule: dict, apply: bool) -> None:
    res = call("GET", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint")
    entry = res.get("result") or {}
    rules = entry.get("rules") or []

    match = next((r for r in rules if r.get("description") == rule["description"]), None)
    if match:
        same = (
            match.get("expression") == rule["expression"]
            and match.get("enabled")
            and (match.get("action_parameters", {}).get("from_value", {})
                 .get("target_url", {}).get("expression") == rule["action_parameters"]
                 ["from_value"]["target_url"]["expression"])
            and (match.get("action_parameters", {}).get("from_value", {})
                 .get("status_code") == 301)
        )
        if same:
            ok(f"{zone}: redirect rule {rule['description']!r}")
            return

    if not apply:
        verb = "replace" if match else "create"
        todo(f"{zone}: {verb} redirect rule {rule['description']!r} — "
             f"{rule['expression']} -> 301")
        return

    # keep every other rule in the phase untouched
    merged = [r for r in rules if r.get("description") != rule["description"]]
    merged.append(rule)
    payload = {"rules": [strip_rule(r) for r in merged]}
    if not entry:
        payload |= {"name": "default", "kind": "zone", "phase": PHASE}
    call("PUT", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint", payload)
    done(f"{zone}: redirect rule {rule['description']!r} deployed")


def strip_rule(r: dict) -> dict:
    """Drop server-managed fields so the rule can be PUT back."""
    return {k: v for k, v in r.items()
            if k in ("action", "action_parameters", "description", "enabled",
                     "expression", "logging", "ref")}


# ---------------------------------------------------------------------- main --
def main() -> int:
    ap = argparse.ArgumentParser(description="Configure Cloudflare for the SEO setup")
    ap.add_argument("--apply", action="store_true",
                    help="actually make the changes (default is a read-only plan)")
    args = ap.parse_args()

    verify = call("GET", "/user/tokens/verify")
    if not verify.get("success"):
        sys.exit("token failed verification")
    print(f"{DIM}token verified, status "
          f"{(verify.get('result') or {}).get('status')}{RESET}\n")

    mode = f"{BOLD}APPLYING CHANGES{RESET}" if args.apply else \
           f"{BOLD}PLAN ONLY{RESET} {DIM}(re-run with --apply to make changes){RESET}"
    print(f"{mode}\n")

    old_id = zone_id(OLD)
    new_id = zone_id(NEW)

    if old_id:
        print(f"{BOLD}{OLD}{RESET} {DIM}(old domain — must 301 to the new one){RESET}")
        ensure_a_record(old_id, OLD, "@", args.apply)
        ensure_a_record(old_id, OLD, "www", args.apply)
        ensure_redirect(old_id, OLD, build_rule(
            "301 to cheltenhamdata.co.uk",
            f'(http.host eq "{OLD}" or http.host eq "www.{OLD}")',
            f'concat("https://{NEW}", http.request.uri.path)'), args.apply)
        ensure_https(old_id, OLD, args.apply)
        print()

    if new_id:
        print(f"{BOLD}{NEW}{RESET} {DIM}(live site){RESET}")
        ensure_redirect(new_id, NEW, build_rule(
            "www to apex",
            f'(http.host eq "www.{NEW}")',
            f'concat("https://{NEW}", http.request.uri.path)'), args.apply)
        ensure_https(new_id, NEW, args.apply)
        ensure_txt(new_id, NEW, "_dmarc", DMARC, args.apply)
        print()

    for p in problems:
        print(f"  {RED}problem{RESET} {p}")

    if args.apply:
        print(f"{GRN}Applied.{RESET} Verify with:  python tools/seo_audit.py --live")
    elif planned:
        print(f"{YEL}{len(planned)} change(s) planned.{RESET} "
              f"Re-run with --apply to make them.")
    else:
        print(f"{GRN}Nothing to do — everything already correct.{RESET}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
