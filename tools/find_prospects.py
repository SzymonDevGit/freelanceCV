#!/usr/bin/env python3
"""
Find founder-led UK e-commerce businesses run by young founders.

  export CH_API_KEY=your_companies_house_key
  python tools/find_prospects.py --max-age 30 --target 100

Companies House is the only free source that ties the three things we care
about to one company record:

  young      officers endpoint returns each director's date of birth
             (month + year), so age is computed rather than guessed
  founder-led  a director appointed within days of incorporation founded the
             thing; one appointed three years later is a hire
  small      micro-entity / total-exemption accounts, and a short officer list

Everything below is a filter over those three signals. Nothing is inferred
from press coverage, which is why it reaches the brands that have none — the
ones small enough to actually want a free first project.

Pipeline, cheapest rejection first:

  advanced-search   by SIC code, active only, incorporated in a date window
  /officers         compute age, drop anyone too old or appointed too late
  /company          only for survivors — confirms size from filed accounts

Output is a CSV of prospects plus, with --emails, one ready-to-send draft per
prospect written in the same voice as the rest of the outreach.

Deliberately NOT produced: email addresses and LinkedIn profile URLs. Neither
is in Companies House, and both are things you cannot guess — a bounced cold
email costs sender reputation, and a wrong LinkedIn profile means addressing a
stranger by a founder's name. The CSV carries a LinkedIn people-search URL
that lands on the right human in one click, and a blank email column to fill
from the brand's own contact page.

Standard library only. Respects the published 600-request / 5-minute limit.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path

API = "https://api.company-information.service.gov.uk"
ROOT = Path(__file__).resolve().parent.parent

# Companies House publishes 600 requests per rolling five minutes. Sitting a
# little under it keeps a long run from ever tripping a 429.
RATE_LIMIT = 570
RATE_WINDOW = 300.0

# SIC codes that map to "sells things on the internet". 47910 is the core one
# and will be most of the yield; the apparel-manufacture codes catch clothing
# brands that register as makers rather than retailers, which a lot of the
# small print-on-demand and cut-and-sew labels do.
SIC_PRESETS = {
    "ecommerce": ["47910", "47990"],
    "clothing": ["14131", "14132", "14190", "14390", "47710", "47721", "46420"],
    "accessories": ["32120", "32130", "15120", "47770"],
    "beauty": ["20420", "47750"],
    "food": ["10890", "47290", "11070"],
    "digital": ["62012", "63120", "73110", "58290"],
}

# The "what made me think of you" line, keyed by what the company actually
# sells. This is the sentence that decides whether the email reads as written
# for them or blasted at them, so each one names a problem that is specific to
# the shape of that business and that data work genuinely fixes.
HOOKS = {
    "clothing": (
        "clothing carries the hardest stock problem there is - every style "
        "multiplied by every size and colour, sold through your own site and "
        "any stockists at completely different margins. Knowing which sizes to "
        "reorder, and which ones come back often enough to wipe out the margin "
        "on the ones that don't, usually takes a spreadsheet rebuild each season"
    ),
    "ecommerce": (
        "once you're past a few hundred orders a month, revenue stops telling "
        "you much - what matters is contribution per order after shipping, "
        "payment fees, discount codes and returns, and that number almost never "
        "lives anywhere you can see it"
    ),
    "accessories": (
        "small-basket products live or die on postage and payment fees, and "
        "those are exactly the costs that never make it into the product-level "
        "numbers - so the lines that look like your best sellers are sometimes "
        "the ones earning least"
    ),
    "beauty": (
        "beauty runs on repeat purchase, so the number that actually matters is "
        "how much a customer is worth over a year rather than what they spent "
        "today - and that's hard to see when the reporting is per-order"
    ),
    "food": (
        "short shelf life makes forecasting unforgiving - over-order and it's "
        "waste, under-order and it's a stockout, and both get decided on gut "
        "feel far longer than anyone admits"
    ),
    "digital": (
        "the reporting that worked at launch tends to break once there are a "
        "few channels feeding it, and rebuilding it by hand every month quietly "
        "eats a day you'd rather spend on the product"
    ),
}
HOOKS["default"] = HOOKS["ecommerce"]

SUBJECTS = {
    "clothing": "Free stock and returns analysis for {company}",
    "ecommerce": "Free profit-per-order analysis for {company}",
    "accessories": "Free margin analysis for {company}",
    "beauty": "Free repeat-purchase analysis for {company}",
    "food": "Free demand forecasting for {company}",
    "digital": "Free reporting automation for {company}",
}
SUBJECTS["default"] = SUBJECTS["ecommerce"]

# Filed-accounts types, by how big the business behind them is. A company
# filing full accounts has outgrown the offer entirely.
#
# "micro" is the tier that matches a one-person shop self-promoting in forums:
# micro-entity accounts mean under roughly £632k turnover, and a company that
# has filed nothing yet is usually a first-year business, which is the target
# rather than a disqualification. "small" widens to companies with staff.
ACCOUNT_TIERS = {
    "micro": {"micro-entity", "total-exemption-small", ""},
    "small": {"micro-entity", "total-exemption-small", "total-exemption-full", "small", ""},
}

CORPORATE = re.compile(r"\b(limited|ltd|llp|plc|holdings|group|inc|corp)\b", re.I)


class RateLimiter:
    """Sliding window over the last RATE_WINDOW seconds of requests."""

    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW) -> None:
        self.limit, self.window, self.calls = limit, window, deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self.calls and now - self.calls[0] > self.window:
            self.calls.popleft()
        if len(self.calls) >= self.limit:
            sleep = self.window - (now - self.calls[0]) + 0.5
            print(f"  rate limit reached, pausing {sleep:.0f}s", file=sys.stderr)
            time.sleep(sleep)
            return self.wait()
        self.calls.append(now)


class Client:
    def __init__(self, key: str) -> None:
        token = base64.b64encode(f"{key}:".encode()).decode()
        self.auth = f"Basic {token}"
        self.limiter = RateLimiter()
        self.requests = 0

    def get(self, path: str, **params) -> dict | None:
        url = f"{API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)

        for attempt in range(5):
            self.limiter.wait()
            req = urllib.request.Request(url, headers={"Authorization": self.auth})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self.requests += 1
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 429:
                    delay = float(e.headers.get("Retry-After", 2**attempt))
                    print(f"  429, backing off {delay:.0f}s", file=sys.stderr)
                    time.sleep(delay)
                    continue
                if e.code >= 500:
                    time.sleep(2**attempt)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                time.sleep(2**attempt)
        return None


def age_of(dob: dict | None, today: date) -> int | None:
    """Companies House gives birth month and year only, so age is +/- 1."""
    if not dob or "year" not in dob:
        return None
    year, month = int(dob["year"]), int(dob.get("month", 7))
    age = today.year - year
    if (today.month, 15) < (month, 15):
        age -= 1
    return age


def days_between(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except (ValueError, TypeError):
        return None


def segment_for(sic_codes: list[str]) -> str:
    for name, codes in SIC_PRESETS.items():
        if any(c in codes for c in sic_codes):
            return name
    return "default"


def first_name(officer_name: str) -> str:
    """Companies House stores officers as 'SURNAME, Forename Middle'."""
    if "," in officer_name:
        forenames = officer_name.split(",", 1)[1].strip()
    else:
        forenames = officer_name.strip()
    first = forenames.split()[0] if forenames.split() else forenames
    return first.capitalize() if first.isupper() else first


def pretty_name(officer_name: str) -> str:
    if "," not in officer_name:
        return officer_name.title()
    surname, forenames = (p.strip() for p in officer_name.split(",", 1))
    return f"{forenames.title()} {surname.title()}"


def pretty_company(name: str) -> str:
    """'BRIGHT THREADS LTD' -> 'Bright Threads'. Used in the email body."""
    cleaned = re.sub(r"\b(LIMITED|LTD\.?|LLP|PLC)\b", "", name, flags=re.I).strip(" .,")
    return cleaned.title() if cleaned.isupper() else cleaned


def find_founders(client: Client, company: dict, max_age: int, max_officers: int,
                  founding_window: int, today: date) -> list[dict]:
    """Young directors who were there at the start. Empty list means skip."""
    number = company["company_number"]
    data = client.get(f"/company/{number}/officers", items_per_page=50)
    if not data:
        return []

    active = [o for o in data.get("items", []) if not o.get("resigned_on")]
    directors = [o for o in active if "director" in (o.get("officer_role") or "").lower()]
    if not directors or len(directors) > max_officers:
        return []

    incorporated = company.get("date_of_creation", "")
    founders = []
    for o in directors:
        name = o.get("name", "")
        if CORPORATE.search(name):          # corporate director, not a person
            return []
        age = age_of(o.get("date_of_birth"), today)
        if age is None or age > max_age:
            continue
        gap = days_between(o.get("appointed_on", ""), incorporated)
        if gap is None or gap > founding_window:
            continue                        # joined later; a hire, not a founder
        founders.append({"name": name, "age": age, "appointed": o.get("appointed_on")})
    return founders


def is_right_size(client: Client, number: str, tier: str) -> tuple[bool, str]:
    allowed = ACCOUNT_TIERS[tier]
    profile = client.get(f"/company/{number}")
    if not profile:
        return "" in allowed, ""
    accounts = (profile.get("accounts") or {}).get("last_accounts") or {}
    kind = (accounts.get("type") or "").lower()
    if not kind:
        return "" in allowed, "none filed"
    return kind in allowed, kind


def compose(prospect: dict) -> tuple[str, str]:
    segment = prospect["segment"]
    company = prospect["trading_name"]
    body = f"""Hi {prospect['first_name']},

Hope you are well,

I recently found {company} and wanted to reach out - building this yourself \
and getting it to where it is now is genuinely impressive.

I'm a freelance data analyst based in Cheltenham, and I wondered if you'd want \
help with reporting or process automation. What made me think of you is that \
{HOOKS.get(segment, HOOKS['default'])}.

Since I'm still building up my case studies I wouldn't expect payment for the \
first project, I'd only want a very honest review in return. If I don't think \
I can add value, I'll tell you honestly. If I can, I'll show you exactly where \
I think the improvements are before you decide whether to go ahead.

Would you be open to a quick 15-20 minute call sometime next week?

Thanks for your time, and I hope to hear from you.

Thank you!

Szymon Pecherski
Data Analyst & Automation Specialist
https://cheltenhamdata.co.uk
"""
    subject = SUBJECTS.get(segment, SUBJECTS["default"]).format(company=company)
    return subject, body


def linkedin_search(name: str, company: str) -> str:
    query = urllib.parse.quote(f"{name} {company}")
    return f"https://www.linkedin.com/search/results/people/?keywords={query}"


def run(args: argparse.Namespace) -> int:
    key = args.api_key or os.environ.get("CH_API_KEY")
    if not key:
        print("Set CH_API_KEY, or pass --api-key.\n"
              "Free key: https://developer.company-information.service.gov.uk/",
              file=sys.stderr)
        return 2

    client = Client(key)
    today = date.today()
    sic_codes = []
    for name in args.segments:
        sic_codes.extend(SIC_PRESETS[name])

    print(f"Searching SIC {', '.join(sic_codes)}", file=sys.stderr)
    print(f"Incorporated {args.from_year}-01-01 to {args.to_year}-12-31, "
          f"founders under {args.max_age}\n", file=sys.stderr)

    prospects: list[dict] = []
    seen: set[str] = set()
    start, screened = 0, 0

    while len(prospects) < args.target:
        page = client.get(
            "/advanced-search/companies",
            sic_codes=sic_codes,
            company_status="active",
            incorporated_from=f"{args.from_year}-01-01",
            incorporated_to=f"{args.to_year}-12-31",
            size=100,
            start_index=start,
        )
        items = (page or {}).get("items") or []
        if not items:
            print("\nNo more results from Companies House.", file=sys.stderr)
            break

        for company in items:
            number = company.get("company_number")
            if not number or number in seen:
                continue
            seen.add(number)
            screened += 1

            founders = find_founders(client, company, args.max_age, args.max_officers,
                                     args.founding_window, today)
            if not founders:
                continue

            ok, accounts = is_right_size(client, number, args.size)
            if not ok:
                continue

            founder = min(founders, key=lambda f: f["age"])
            legal = company.get("company_name", "")
            trading = pretty_company(legal)
            full = pretty_name(founder["name"])
            segment = segment_for(company.get("sic_codes") or [])
            address = company.get("registered_office_address") or {}

            prospects.append({
                "company": legal,
                "trading_name": trading,
                "company_number": number,
                "founder": full,
                "first_name": first_name(founder["name"]),
                "founder_age": founder["age"],
                "incorporated": company.get("date_of_creation", ""),
                "segment": segment,
                "sic_codes": " ".join(company.get("sic_codes") or []),
                "accounts": accounts,
                "locality": address.get("locality", ""),
                "postcode": address.get("postal_code", ""),
                "linkedin_search": linkedin_search(full, trading),
                "companies_house": f"https://find-and-update.company-information.service.gov.uk/company/{number}",
                "email": "",
                "website": "",
            })

            print(f"  [{len(prospects):>3}] {trading} - {full}, {founder['age']} "
                  f"({segment}, {address.get('locality') or 'UK'})", file=sys.stderr)
            if len(prospects) >= args.target:
                break

        start += len(items)

    if not prospects:
        print("\nNothing matched. Try --max-age 35 or a wider year range.", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(prospects[0].keys()))
        writer.writeheader()
        writer.writerows(prospects)

    print(f"\n{len(prospects)} prospects from {screened} screened "
          f"({client.requests} API calls) -> {out}", file=sys.stderr)

    if args.emails:
        maildir = Path(args.emails)
        maildir.mkdir(parents=True, exist_ok=True)
        for p in prospects:
            subject, body = compose(p)
            slug = re.sub(r"[^a-z0-9]+", "-", p["trading_name"].lower()).strip("-")
            (maildir / f"{slug}.txt").write_text(
                f"To: {p['email'] or '<fill in from their site>'}\n"
                f"Subject: {subject}\n\n{body}", encoding="utf-8")
        print(f"{len(prospects)} drafts -> {maildir}/", file=sys.stderr)

    print("\nNext: fill the email and website columns from each brand's own\n"
          "contact page, then send. Do not guess addresses - bounces cost you\n"
          "sender reputation on every later send.", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Find young, founder-led UK e-commerce businesses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Free API key: https://developer.company-information.service.gov.uk/",
    )
    p.add_argument("--api-key", help="defaults to $CH_API_KEY")
    p.add_argument("--target", type=int, default=100, help="how many to find (default 100)")
    p.add_argument("--max-age", type=int, default=30, help="founder age ceiling (default 30)")
    p.add_argument("--segments", nargs="+", default=["ecommerce", "clothing"],
                   choices=sorted(SIC_PRESETS), help="which SIC presets to search")
    p.add_argument("--from-year", type=int, default=date.today().year - 6,
                   help="earliest incorporation year")
    p.add_argument("--to-year", type=int, default=date.today().year,
                   help="latest incorporation year (default: this year — first-year "
                        "businesses are the target, not a disqualification)")
    p.add_argument("--max-officers", type=int, default=3,
                   help="skip companies with more directors than this (default 3)")
    p.add_argument("--founding-window", type=int, default=90,
                   help="days between incorporation and appointment to count as "
                        "a founder rather than a hire (default 90)")
    p.add_argument("--size", choices=["micro", "small"], default="micro",
                   help="micro is a one-person shop (default); small allows staff")
    p.add_argument("--out", default="tools/prospects.csv")
    p.add_argument("--emails", nargs="?", const="tools/prospect_emails",
                   help="also write one draft per prospect to this directory")
    return run(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
