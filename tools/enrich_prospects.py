#!/usr/bin/env python3
"""
Find niche DTC brands in community forums, then find how to contact them.

  python tools/enrich_prospects.py discover --subs streetwearstartup smallbusinessuk
  python tools/enrich_prospects.py contacts --in tools/prospects.csv

Two stages, usable separately.

  discover   reads the places small brands actually talk about themselves —
             r/streetwearstartup, r/smallbusinessuk, r/ecommerce and friends —
             and pulls out the brand domains people post. This reaches the
             genuinely niche end that Companies House sorts by SIC code but
             cannot rank by interestingness, and that press coverage misses
             entirely because there is none.

  contacts   takes any CSV with a company or website column and fills in the
             real contact address by reading the brand's own contact page.

Both stages need outbound network access, so run them locally rather than in a
sandbox. Reddit's public JSON endpoints are used as published, one request at
a time with a real User-Agent.

The contact stage exists because guessing an address is the one thing you must
never do in cold outreach. A bounce is not a neutral outcome: mailbox providers
score your domain on it, so a batch of invented addresses quietly degrades
delivery for every legitimate email you send afterwards. Every address this
writes came from the brand's own page, and the column recording where it came
from is there so you can check any one of them.

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "CheltenhamData-Research/1.0 (+https://cheltenhamdata.co.uk; contact szymonpecherski@gmail.com)"

# Where small brands post about themselves. Ordered roughly by signal density:
# the first few are people building brands, the rest are people buying from them.
DEFAULT_SUBS = [
    "streetwearstartup", "smallbusinessuk", "ecommerce", "EtsySellers",
    "Entrepreneur", "smallbusiness", "somethingimade", "AusFemaleFashion",
    "findfashion", "malefashionadvice", "femalefashionadvice",
]

DISCOVER_QUERIES = [
    "my brand", "launched my", "started my", "our first drop",
    "feedback on my store", "my shopify", "small brand",
]

# Domains that are never a prospect: platforms, socials, marketplaces, and the
# big names that would fail the size filter anyway.
NOISE = {
    "reddit.com", "redd.it", "imgur.com", "instagram.com", "youtube.com",
    "youtu.be", "tiktok.com", "twitter.com", "x.com", "facebook.com",
    "etsy.com", "amazon.co.uk", "amazon.com", "ebay.co.uk", "depop.com",
    "shopify.com", "myshopify.com", "wix.com", "squarespace.com", "gumroad.com",
    "linktr.ee", "google.com", "docs.google.com", "imgse.com", "ibb.co",
    "kickstarter.com", "patreon.com", "discord.gg", "pinterest.com",
    "gymshark.com", "asos.com", "boohoo.com", "prettylittlething.com",
}

CONTACT_PATHS = [
    "/pages/contact", "/pages/contact-us", "/contact", "/contact-us",
    "/pages/about", "/about", "/pages/get-in-touch", "/support",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Addresses that are real but belong to the platform, not the brand.
EMAIL_NOISE = re.compile(
    r"(sentry|wixpress|godaddy|shopify|squarespace|example\.|domain\.com"
    r"|\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg|sentry\.io|@2x|placeholder)", re.I)

# Prefer a role address over a personal one: they are stable, monitored, and
# far less likely to read as scraped.
ROLE_ORDER = ["hello@", "hi@", "info@", "contact@", "team@", "enquiries@",
              "sales@", "support@", "hey@", "orders@"]


def get(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read(3_000_000).decode(charset, errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
            UnicodeDecodeError, ConnectionError):
        return None


def registrable(host: str) -> str:
    """Strip www down to something comparable."""
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def normalise_domain(value: str) -> str:
    """'https://www.Brand.co.uk/pages/x' -> 'brand.co.uk'.

    Scheme and path have to come off before registrable() looks for the www
    prefix, or a full URL keeps its www — which then fails every own-domain
    email comparison and builds a 'www.www.' fallback URL.
    """
    value = (value or "").strip()
    value = re.sub(r"^[a-z]+://", "", value, flags=re.I)
    value = value.split("/")[0].split("?")[0].split("@")[-1]
    value = value.split(":")[0]
    return registrable(value)


def is_noise(host: str) -> bool:
    host = registrable(host)
    return any(host == n or host.endswith("." + n) for n in NOISE)


# Forums that publish threads as plain HTML. Reddit blocks most crawlers but
# serves its own JSON fine to a normal client, so it stays on its own path.
# UK Business Forums is the better source for this brief: it is UK-only, and
# the people posting are running businesses the size of a one-person shop.
FORUMS = {
    "ukbf": {
        "name": "UK Business Forums",
        "base": "https://www.ukbusinessforums.co.uk",
        "listings": [
            "/forums/websites-ecommerce.59/",
            "/forums/general-business-forum.1/",
            "/forums/marketing-pr.10/",
            "/tags/ecommerce/",
        ],
        "thread_re": re.compile(r'href="(/threads/[a-z0-9][a-z0-9\-\.]*/?)"', re.I),
        "page_fmt": "page-{n}",
    },
}


# ---------------------------------------------------------------- discover

def forum_threads(forum: dict, pages: int, delay: float) -> list[str]:
    """Thread URLs from a forum's plain listing pages."""
    urls: set[str] = set()
    for listing in forum["listings"]:
        for n in range(1, pages + 1):
            path = listing if n == 1 else listing.rstrip("/") + "/" + forum["page_fmt"].format(n=n)
            body = get(forum["base"] + path)
            time.sleep(delay)
            if not body:
                break
            found = forum["thread_re"].findall(body)
            if not found:
                break
            urls.update(forum["base"] + f for f in found)
    return sorted(urls)


def forum_discover(key: str, pages: int, delay: float) -> dict[str, dict]:
    """Read a forum's threads and pull out the brand domains people post."""
    forum = FORUMS[key]
    threads = forum_threads(forum, pages, delay)
    print(f"  {forum['name']}: {len(threads)} threads", file=sys.stderr)

    seen: dict[str, dict] = {}
    for url in threads:
        body = get(url)
        time.sleep(delay)
        if not body:
            continue
        title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        title = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()[:120] if title else ""
        # Links inside posts, plus bare domain mentions in the prose.
        text = html.unescape(body)
        hosts = set()
        for m in re.finditer(r'https?://([A-Za-z0-9.\-]+)', text):
            hosts.add(registrable(m.group(1)))
        for m in re.finditer(r'\b([a-z0-9][a-z0-9\-]{2,}\.(?:co\.uk|com|shop|store|uk))\b',
                             text.lower()):
            hosts.add(registrable(m.group(1)))
        for host in hosts:
            if is_noise(host) or host.endswith("ukbusinessforums.co.uk"):
                continue
            entry = seen.setdefault(host, {
                "website": host, "mentions": 0, "source": forum["name"],
                "example_post": url, "post_title": title,
            })
            entry["mentions"] += 1
    return seen


def reddit_search(sub: str, query: str, pages: int = 1) -> list[dict]:
    """Reddit's public search JSON. One request at a time, as published."""
    out, after = [], None
    for _ in range(pages):
        params = {
            "q": query, "restrict_sr": "1", "limit": "100",
            "sort": "new", "t": "year", "raw_json": "1",
        }
        if after:
            params["after"] = after
        url = f"https://www.reddit.com/r/{sub}/search.json?{urllib.parse.urlencode(params)}"
        body = get(url)
        time.sleep(2.0)                       # be a good citizen
        if not body:
            return out
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return out
        children = data.get("data", {}).get("children") or []
        out.extend(c.get("data", {}) for c in children)
        after = data.get("data", {}).get("after")
        if not after:
            break
    return out


def domains_in(post: dict) -> set[str]:
    """Every external domain a post points at, from its link and its text."""
    found = set()
    text = " ".join(filter(None, [
        post.get("url_overridden_by_dest") or post.get("url") or "",
        post.get("selftext") or "",
    ]))
    for match in re.finditer(r"https?://([A-Za-z0-9.\-]+)", text):
        host = registrable(match.group(1))
        if host and "." in host and not is_noise(host):
            found.add(host)
    # bare mentions like "check out brandname.co.uk"
    for match in re.finditer(r"\b([a-z0-9][a-z0-9\-]{2,}\.(?:co\.uk|com|shop|store|uk))\b",
                             (post.get("selftext") or "").lower()):
        host = registrable(match.group(1))
        if not is_noise(host):
            found.add(host)
    return found


def discover(args: argparse.Namespace) -> int:
    seen: dict[str, dict] = {}

    if "ukbf" in args.sources:
        for host, entry in forum_discover("ukbf", args.pages, args.delay).items():
            existing = seen.setdefault(host, entry)
            if existing is not entry:
                existing["mentions"] += entry["mentions"]

    if "reddit" in args.sources:
        for sub in args.subs:
            for query in DISCOVER_QUERIES:
                posts = reddit_search(sub, query, pages=args.pages)
                print(f"  r/{sub} '{query}': {len(posts)} posts", file=sys.stderr)
                for post in posts:
                    for host in domains_in(post):
                        entry = seen.setdefault(host, {
                            "website": host, "mentions": 0, "source": f"r/{sub}",
                            "example_post": f"https://reddit.com{post.get('permalink','')}",
                            "post_title": (post.get("title") or "")[:120],
                        })
                        entry["mentions"] += 1

    if not seen:
        print("Nothing found. If you asked for reddit, it may be rate limiting.",
              file=sys.stderr)
        return 1

    # Niche-first. Mention count is a popularity signal, so ranking by it
    # descending surfaces the brands everyone already knows — the opposite of
    # what this list is for. A domain posted once by the person who runs it is
    # exactly the target; the contacts stage then confirms it is a real shop
    # rather than a stray link, by looking for a store platform on the page.
    reverse = args.rank == "popular"
    rows = sorted(seen.values(), key=lambda r: (r["mentions"], r["website"]),
                  reverse=reverse)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} candidate brand domains -> {out}", file=sys.stderr)
    print("Next: python tools/enrich_prospects.py contacts --in "
          f"{out} to find their addresses.", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- contacts

def score_email(addr: str, domain: str) -> tuple[int, int]:
    """Lower sorts first. Own-domain role addresses win."""
    addr = addr.lower()
    own = 0 if addr.endswith("@" + domain) or addr.endswith("." + domain) else 1
    for i, role in enumerate(ROLE_ORDER):
        if addr.startswith(role):
            return (own, i)
    return (own, len(ROLE_ORDER))


def emails_on_page(body: str, domain: str) -> list[str]:
    text = html.unescape(body)
    found = set()
    for match in EMAIL_RE.finditer(text):
        addr = match.group(0).strip(".,;:'\"()<>").lower()
        if EMAIL_NOISE.search(addr) or len(addr) > 90:
            continue
        found.add(addr)
    return sorted(found, key=lambda a: score_email(a, domain))


def is_shopify(body: str) -> bool:
    return "cdn.shopify.com" in body or "Shopify.theme" in body


def find_contact(domain: str, delay: float) -> dict:
    """Read the brand's own pages. Returns what was found and where from."""
    result = {"email": "", "email_source": "", "platform": "", "site_title": ""}
    base = f"https://{domain}"

    home = get(base)
    if home is None:
        home = get(f"https://www.{domain}")
        if home is None:
            result["email_source"] = "site unreachable"
            return result
    time.sleep(delay)

    if is_shopify(home):
        result["platform"] = "Shopify"
    title = re.search(r"<title[^>]*>(.*?)</title>", home, re.S | re.I)
    if title:
        result["site_title"] = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()[:120]

    for path in [""] + CONTACT_PATHS:
        body = home if path == "" else get(base + path)
        if path:
            time.sleep(delay)
        if not body:
            continue
        found = emails_on_page(body, domain)
        if found:
            result["email"] = found[0]
            result["email_source"] = base + (path or "/")
            return result

    result["email_source"] = "no address published"
    return result


def contacts(args: argparse.Namespace) -> int:
    src = Path(args.infile)
    if not src.exists():
        print(f"No such file: {src}", file=sys.stderr)
        return 2

    with src.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("Input CSV is empty.", file=sys.stderr)
        return 1

    if "website" not in rows[0]:
        print("Input needs a 'website' column (a domain per row).", file=sys.stderr)
        return 2

    found = 0
    for i, row in enumerate(rows, 1):
        domain = normalise_domain(row.get("website") or "")
        if not domain or "." not in domain:
            continue
        info = find_contact(domain, args.delay)
        row.update(info)
        if info["email"]:
            found += 1
            print(f"  [{i}/{len(rows)}] {domain} -> {info['email']}", file=sys.stderr)
        else:
            print(f"  [{i}/{len(rows)}] {domain} -> {info['email_source']}", file=sys.stderr)

    out = Path(args.out or args.infile)
    fields = list(dict.fromkeys(list(rows[0].keys())))
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{found}/{len(rows)} addresses found -> {out}", file=sys.stderr)
    print("Every one is traceable via the email_source column. Spot-check a few\n"
          "before sending — an address that came from a page is worth far more\n"
          "than one that came from a pattern.", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="find niche brand domains in forums")
    d.add_argument("--sources", nargs="+", default=["ukbf"],
                   choices=["ukbf", "reddit"],
                   help="ukbf is UK-only and the better fit for micro businesses; "
                        "reddit is broader but blocks most crawlers, so it only "
                        "works from your own machine")
    d.add_argument("--subs", nargs="+", default=DEFAULT_SUBS,
                   help="subreddits, when reddit is in --sources")
    d.add_argument("--pages", type=int, default=3, help="listing pages per source")
    d.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    d.add_argument("--rank", choices=["niche", "popular"], default="niche",
                   help="niche puts the least-mentioned domains first (default)")
    d.add_argument("--out", default="tools/discovered.csv")
    d.set_defaults(fn=discover)

    c = sub.add_parser("contacts", help="find contact addresses for brand domains")
    c.add_argument("--in", dest="infile", required=True)
    c.add_argument("--out", help="defaults to overwriting the input")
    c.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    c.set_defaults(fn=contacts)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
