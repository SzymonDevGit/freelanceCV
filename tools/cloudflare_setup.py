#!/usr/bin/env python3
"""
Bring both Cloudflare zones to the state the SEO work needs.

  python tools/cloudflare_setup.py                    # PLAN: read-only diff
  python tools/cloudflare_setup.py --apply            # make the changes
  python tools/cloudflare_setup.py --email --apply    # + set up the mailbox

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

--email is opt-in and does nothing unless you pass it, because enabling Email
Routing adds MX records to the zone — not a side effect anyone should get by
surprise from a run aimed at redirect rules. It sets up:

    szymon@cheltenhamdata.co.uk -> the personal inbox

as forwarding only: no mailbox is created, nothing is stored at Cloudflare, and
replies still come from the inbox you already use. There is one manual step the
API cannot do for you — Cloudflare emails the destination a verification link,
and nothing is delivered until it is clicked. The script says so when it hits
that state.

The site publishes the Gmail address until that forward is verified and tested.
Switching it over is a separate edit to index.html, 404.html and the two blog
pages (mailto links, the visible address, and the three JSON-LD "email" fields).
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

# The address published on the site, and the inbox it forwards to.
MAIL_FROM = f"szymon@{NEW}"
MAIL_TO = "szymonpecherski@gmail.com"
MAIL_RULE = "site contact address"

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


def zone(name: str) -> dict | None:
    res = call("GET", f"/zones?name={name}")
    result = res.get("result") or []
    if not result:
        problems.append(f"zone {name} not found — is it in this account, and does "
                        f"the token include it?")
        return None
    return result[0]


def zone_id(name: str) -> str | None:
    z = zone(name)
    return z["id"] if z else None


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
    # The phase-entrypoint endpoint takes "rules" only — sending name/kind/phase
    # is rejected with: invalid JSON: unknown field "kind". It creates the
    # entrypoint ruleset implicitly when one does not exist yet.
    call("PUT", f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint",
         {"rules": [strip_rule(r) for r in merged]})
    done(f"{zone}: redirect rule {rule['description']!r} deployed")


# ----------------------------------------------------------- email routing --
def ensure_email_routing(zid: str, account_id: str, zone_name: str,
                         apply: bool) -> None:
    """Forward MAIL_FROM to MAIL_TO. Forwarding only — no mailbox is created."""
    status = (call("GET", f"/zones/{zid}/email/routing").get("result") or {})
    enabled = bool(status.get("enabled"))

    if enabled:
        ok(f"{zone_name}: Email Routing enabled")
    elif apply:
        # Cloudflare adds the MX and SPF records for the zone as part of this.
        call("POST", f"/zones/{zid}/email/routing/enable", {})
        done(f"{zone_name}: Email Routing enabled (MX + SPF records added)")
        enabled = True
    else:
        todo(f"{zone_name}: enable Email Routing (adds MX + SPF records)")

    # The destination inbox is an account-level object and has to confirm by
    # email before any rule pointing at it will deliver.
    dests = (call("GET", f"/accounts/{account_id}/email/routing/addresses")
             .get("result") or [])
    dest = next((d for d in dests if d.get("email") == MAIL_TO), None)

    if dest is None:
        if apply:
            call("POST", f"/accounts/{account_id}/email/routing/addresses",
                 {"email": MAIL_TO})
            done(f"destination {MAIL_TO} added — "
                 f"{YEL}check that inbox and click the verification link{RESET}")
        else:
            todo(f"add destination {MAIL_TO} (sends it a verification email)")
    elif dest.get("verified"):
        ok(f"destination {MAIL_TO} verified")
    else:
        problems.append(f"destination {MAIL_TO} is not verified yet — click the "
                        f"link in the Cloudflare email; forwarding stays off "
                        f"until you do")

    if not enabled:
        todo(f"{zone_name}: route {MAIL_FROM} -> {MAIL_TO} "
             f"(after Email Routing is on)")
        return

    rules = (call("GET", f"/zones/{zid}/email/routing/rules").get("result") or [])
    wanted = {
        "name": MAIL_RULE,
        "enabled": True,
        "matchers": [{"type": "literal", "field": "to", "value": MAIL_FROM}],
        "actions": [{"type": "forward", "value": [MAIL_TO]}],
    }
    match = next((r for r in rules if r.get("name") == MAIL_RULE
                  or (r.get("matchers") or [{}])[0].get("value") == MAIL_FROM), None)

    if match:
        same = (match.get("enabled")
                and match.get("matchers") == wanted["matchers"]
                and match.get("actions") == wanted["actions"])
        if same:
            ok(f"{MAIL_FROM} -> {MAIL_TO}")
            return
        if apply:
            call("PUT", f"/zones/{zid}/email/routing/rules/{match['tag']}", wanted)
            done(f"updated route {MAIL_FROM} -> {MAIL_TO}")
        else:
            todo(f"update route {MAIL_FROM} -> {MAIL_TO}")
        return

    if apply:
        call("POST", f"/zones/{zid}/email/routing/rules", wanted)
        done(f"created route {MAIL_FROM} -> {MAIL_TO}")
    else:
        todo(f"create route {MAIL_FROM} -> {MAIL_TO}")


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
    ap.add_argument("--email", action="store_true",
                    help="also set up Email Routing for %s (opt-in: enabling it "
                         "adds MX records to the zone)" % MAIL_FROM)
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
    new_zone = zone(NEW)
    new_id = new_zone["id"] if new_zone else None
    account_id = (new_zone or {}).get("account", {}).get("id")

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
        if not args.email:
            print(f"  {DIM}skip    Email Routing — pass --email to set up "
                  f"{MAIL_FROM}{RESET}")
        elif account_id:
            ensure_email_routing(new_id, account_id, NEW, args.apply)
        else:
            problems.append("no account id on the zone — cannot configure Email "
                            "Routing; does the token include Account settings?")
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
