#!/usr/bin/env python3
"""
Push URLs to IndexNow so Bing (and therefore ChatGPT's web retrieval) picks up
changes in minutes instead of waiting for a crawl.

  python tools/indexnow.py --dry-run     # show what would be submitted
  python tools/indexnow.py               # submit every URL in sitemap.xml
  python tools/indexnow.py https://cheltenhamdata.co.uk/   # submit one URL

Google does not support IndexNow — for Google, the sitemap plus Search Console
is the path. Participating engines: Bing, Yandex, Seznam, Naver.

The key lives in <key>.txt at the site root; IndexNow fetches that file to
prove you own the domain. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
HOST = "cheltenhamdata.co.uk"
ENDPOINT = "https://api.indexnow.org/IndexNow"
KEY_RE = re.compile(r"^[0-9a-f]{8,128}\.txt$")


def find_key() -> tuple[str, str]:
    """Locate the key file at the repo root and sanity-check its contents."""
    for path in sorted(ROOT.glob("*.txt")):
        if not KEY_RE.match(path.name):
            continue
        key = path.stem
        body = path.read_text(encoding="utf-8").strip()
        if body != key:
            sys.exit(f"{path.name} must contain exactly its own key ({key!r}), got {body!r}")
        return key, f"https://{HOST}/{path.name}"
    sys.exit("No IndexNow key file found at the repo root (expected <hexkey>.txt)")


def sitemap_urls() -> list[str]:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        sys.exit("sitemap.xml not found")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ElementTree.parse(path).getroot()
    return [e.text.strip() for e in root.findall(".//s:loc", ns) if e.text]


def submit(urls: list[str], key: str, key_location: str) -> int:
    payload = json.dumps({
        "host": HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "cheltenhamdata.co.uk-indexnow/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        code = exc.code
        body = exc.read().decode("utf-8", "replace").strip()
    except urllib.error.URLError as exc:
        print(f"network error: {exc.reason}")
        return 1

    # 200 accepted, 202 accepted pending key validation
    if code in (200, 202):
        print(f"OK ({code}) — submitted {len(urls)} URL(s)")
        return 0
    meaning = {
        400: "bad request — malformed URL list",
        403: "key not valid: check the key file is live at " + key_location,
        422: "URLs do not match the host, or the key does not match",
        429: "rate limited — too many submissions",
    }.get(code, "unexpected response")
    print(f"FAILED ({code}) {meaning}\n{body[:400]}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Submit URLs to IndexNow")
    ap.add_argument("urls", nargs="*", help="URLs to submit (default: all of sitemap.xml)")
    ap.add_argument("--dry-run", action="store_true", help="print, don't submit")
    args = ap.parse_args()

    key, key_location = find_key()
    urls = args.urls or sitemap_urls()

    bad = [u for u in urls if not u.startswith(f"https://{HOST}")]
    if bad:
        sys.exit(f"refusing to submit URLs from another host: {bad}")

    print(f"key       {key}")
    print(f"keyfile   {key_location}")
    for u in urls:
        print(f"  submit  {u}")

    if args.dry_run:
        print("\n(dry run — nothing sent)")
        return 0
    return submit(urls, key, key_location)


if __name__ == "__main__":
    raise SystemExit(main())
