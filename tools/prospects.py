#!/usr/bin/env python3
"""
Build a prospect list of small, founder-led product businesses from the free
Companies House bulk data, then pull each one's *published* contact address.

  # 1. download the monthly snapshot (~450 MB zipped, no API key needed)
  #    http://download.companieshouse.gov.uk/en_output.html
  python tools/prospects.py build BasicCompanyDataAsOneFile-2026-08-01.csv

  # 2. add a website column to prospects/companies.csv (see --help on contacts),
  #    then collect the addresses those sites publish
  python tools/prospects.py contacts

Two things this deliberately does not do.

It never guesses an address. No first.last@, no info@ on spec. A guessed
address that bounces costs sending reputation on a domain that has none to
spare yet, and a 5% bounce rate is enough for Google to start filing the good
ones under spam. Every address here came from a page that published it, and
the row records which page, which is also the answer when someone asks where
you got it.

It never ignores robots.txt. The services page promises collectors that
respect a site's terms; a prospecting script that did otherwise would make
that a lie.

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "prospects"

UA = ("CheltenhamDataBot/1.0 (+https://cheltenhamdata.co.uk; "
      "szymonpecherski@gmail.com)")

# ---------------------------------------------------------------- filters --

# Makers of physical consumer goods — the shape of business that ends up with
# landed cost spread over several suppliers and no single view of it.
SIC = {
    "20420": "Perfumes & toiletries",
    "20410": "Soap & detergents",          # LAVOIR's own code, kept for sizing
    "32990": "Other manufacturing (candles, homeware)",
    "11010": "Distilling & blending spirits",
    "11020": "Wine",
    "11030": "Cider & other fruit wines",
    "11050": "Beer",
    "10821": "Cocoa, chocolate & confectionery",
    "10832": "Tea & coffee processing",
    "10390": "Other fruit & vegetable processing",
    "10890": "Other food products",
    "10710": "Bread & fresh bakery",
    "23410": "Ceramic household goods",
    "15120": "Luggage & leather goods",
    "13990": "Other textiles",
    "47910": "Retail via mail order or internet",
}

# Gloucestershire out through the Cotswolds and the near South West.
POSTCODE_AREAS = ("GL", "HR", "WR", "OX", "SN", "BA", "BS", "CV")

# Micro and small filers only. A company filing full accounts is past the point
# where the founder is still doing the numbers in a spreadsheet at the weekend.
ACCOUNT_CATEGORIES = {
    "MICRO ENTITY", "TOTAL EXEMPTION SMALL", "TOTAL EXEMPTION FULL",
    "SMALL", "ACCOUNTS TYPE NOT AVAILABLE", "NO ACCOUNTS FILED",
}

INCORPORATED_FROM, INCORPORATED_TO = 2017, 2025

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Addresses that belong to the website's builder, not its owner.
EMAIL_SKIP = re.compile(
    r"(example|sentry|wixpress|squarespace|shopify|godaddy|"
    r"@(2x|3x)\.|\.(png|jpg|jpeg|gif|webp|svg|css|js)$)", re.I)
CONTACT_PATHS = ("/contact", "/contact-us", "/pages/contact", "/about",
                 "/pages/about-us", "/get-in-touch", "/")


def area(postcode: str) -> str:
    """GL52 3AB -> GL. The area is the letters before the first digit."""
    m = re.match(r"([A-Z]{1,2})", (postcode or "").upper().strip())
    return m.group(1) if m else ""


# ------------------------------------------------------------------ build --

def build(src: Path) -> int:
    OUT.mkdir(exist_ok=True)
    dest = OUT / "companies.csv"
    kept, seen = 0, 0

    # The snapshot is ~5.5 million rows and about 2.5 GB unzipped, so it is
    # streamed rather than loaded. pandas would work too and would need ~8 GB.
    with open(src, newline="", encoding="utf-8", errors="replace") as fh, \
            open(dest, "w", newline="", encoding="utf-8") as out:
        r = csv.DictReader(fh)
        # the bulk file ships with a leading space in most header names
        fields = {k.strip(): k for k in r.fieldnames or []}

        def get(row, name, default=""):
            return (row.get(fields.get(name, name)) or default).strip()

        w = csv.writer(out)
        w.writerow(["company_number", "company_name", "sic_label", "postcode",
                    "town", "incorporated", "accounts_category",
                    "website", "contact_name", "contact_email", "source_url",
                    "segment", "notes"])

        for row in r:
            seen += 1
            if get(row, "CompanyStatus") != "Active":
                continue
            pc = get(row, "RegAddress.PostCode")
            if area(pc) not in POSTCODE_AREAS:
                continue
            if get(row, "Accounts.AccountCategory").upper() not in ACCOUNT_CATEGORIES:
                continue

            inc = get(row, "IncorporationDate")          # DD/MM/YYYY
            year = int(inc[-4:]) if inc[-4:].isdigit() else 0
            if not INCORPORATED_FROM <= year <= INCORPORATED_TO:
                continue

            codes = [get(row, f"SICCode.SicText_{i}")[:5] for i in range(1, 5)]
            hits = [c for c in codes if c in SIC]
            if not hits:
                continue
            # 47910 is the catch-all every D2C brand registers alongside what it
            # actually makes. Label the row by the maker code when there is one,
            # or a chocolate maker comes out of this as "mail order".
            hit = next((c for c in hits if c != "47910"), hits[0])

            w.writerow([get(row, "CompanyNumber"), get(row, "CompanyName"),
                        SIC[hit], pc, get(row, "RegAddress.PostTown"), inc,
                        get(row, "Accounts.AccountCategory"),
                        "", "", "", "", "", ""])
            kept += 1

    print(f"read {seen:,} companies, kept {kept:,} -> {dest.relative_to(ROOT)}")
    print("\nNext: fill the website column. Companies House does not hold URLs,\n"
          "so either paste them in for the ones worth pursuing, or run the\n"
          "names through a search API and write the first own-domain result.")
    return 0


# --------------------------------------------------------------- contacts --

class Site:
    """One host, with its robots.txt read once and obeyed."""

    def __init__(self, url: str):
        p = urllib.parse.urlparse(url if "//" in url else "https://" + url)
        self.base = f"{p.scheme}://{p.netloc}"
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(self.base + "/robots.txt")
        try:
            self.rp.read()
        except Exception:
            # No robots.txt is permission; an unreachable one is not, but the
            # stdlib parser cannot tell them apart, so treat silence as allowed
            # and let the per-request failure handle a genuinely dead host.
            pass

    def fetch(self, path: str, timeout: int = 12) -> str:
        url = urllib.parse.urljoin(self.base, path)
        if not self.rp.can_fetch(UA, url):
            raise PermissionError(f"robots.txt disallows {url}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise urllib.error.HTTPError(url, resp.status, "", {}, None)
            body = resp.read(500_000)
        return body.decode("utf-8", errors="replace")


def first_email(html: str) -> str | None:
    # mailto: first — it is the address the site owner chose to publish,
    # rather than whatever a plugin left in the markup
    m = re.search(r'mailto:([^"\'?>\s]+)', html)
    if m and not EMAIL_SKIP.search(m.group(1)):
        return m.group(1)
    for cand in EMAIL_RE.findall(html):
        if not EMAIL_SKIP.search(cand):
            return cand
    return None


def contacts(delay: float, limit: int) -> int:
    path = OUT / "companies.csv"
    if not path.exists():
        sys.exit(f"{path} not found — run `build` first")
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))

    todo = [r for r in rows if r["website"] and not r["contact_email"]][:limit]
    print(f"{len(todo)} sites to try, {delay}s apart\n")
    found = 0

    for i, row in enumerate(todo, 1):
        try:
            site = Site(row["website"])
        except Exception as e:
            row["notes"] = f"bad url: {e}"
            continue

        for p in CONTACT_PATHS:
            try:
                html = site.fetch(p)
            except PermissionError as e:
                # robots.txt is checked per URL, so a rule covering /contact
                # says nothing about /about — note it and try the next one
                row["notes"] = str(e)
                continue
            except Exception:
                continue
            email = first_email(html)
            if email:
                row["contact_email"] = email
                row["source_url"] = urllib.parse.urljoin(site.base, p)
                row["notes"] = ""
                found += 1
                break
            time.sleep(delay)
        else:
            row["notes"] = row["notes"] or "no address published"

        print(f"  {i:>3}/{len(todo)}  {row['company_name'][:38]:<38} "
              f"{row['contact_email'] or row['notes']}")
        time.sleep(delay)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    print(f"\n{found} addresses found, written back to {path.relative_to(ROOT)}")
    print("Every one records the page it came from — keep that column. It is\n"
          "the answer to 'where did you get my address', and under UK GDPR you\n"
          "are the one who has to have an answer.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="filter the Companies House bulk snapshot")
    b.add_argument("csv", type=Path, help="BasicCompanyDataAsOneFile-*.csv")

    c = sub.add_parser("contacts", help="collect published contact addresses")
    c.add_argument("--delay", type=float, default=2.0,
                   help="seconds between requests (default 2, be generous)")
    c.add_argument("--limit", type=int, default=250)

    a = ap.parse_args()
    return build(a.csv) if a.cmd == "build" else contacts(a.delay, a.limit)


if __name__ == "__main__":
    raise SystemExit(main())
