#!/usr/bin/env python3
"""
Pre-deploy SEO / correctness gate for cheltenhamdata.co.uk.

  python tools/seo_audit.py            # audit, exit 1 on any ERROR
  python tools/seo_audit.py --stamp    # re-stamp today's date everywhere, then audit
  python tools/seo_audit.py --strict   # treat WARNs as failures too

Standard library only, so CI needs no install step.

What it catches, in the order things actually break:
  * broken internal anchors and missing local assets (the #1 silent regression)
  * canonical / robots / title / description mistakes
  * invalid JSON-LD, or @id references that point at nothing
  * og:image missing on disk or the wrong dimensions
  * sitemap, footer date and JSON-LD dateModified drifting out of sync
  * a reintroduced third-party font request (undoes the LCP work)
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://cheltenhamdata.co.uk"
# file on disk -> the canonical path it must declare, or None if it must be
# noindex. Add a row when you add a page; the sitemap check reads the same map.
PAGES: dict[str, str | None] = {
    "index.html": "/",
    "blog/index.html": "/blog/",
    "blog/uk-data-job-salary-transparency-2026/index.html":
        "/blog/uk-data-job-salary-transparency-2026/",
    "blog/ai-hallucination-rates-2024-vs-2026/index.html":
        "/blog/ai-hallucination-rates-2024-vs-2026/",
    "404.html": None,
    "social/index.html": None,
}

TITLE_MIN, TITLE_MAX = 15, 65
DESC_MIN, DESC_MAX = 70, 165
HTML_MAX_KB = 120

RESET, RED, YEL, GRN, DIM = "\033[0m", "\033[31m", "\033[33m", "\033[32m", "\033[2m"

errors: list[str] = []
warns: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def note(msg: str) -> None:
    notes.append(msg)


# --------------------------------------------------------------- parsing ---
class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.title = ""
        self._in_title = False
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.ids: set[str] = set()
        self.anchors: list[dict[str, str]] = []
        self.headings: list[tuple[int, str]] = []
        self._heading_level: int | None = None
        self.images: list[dict[str, str]] = []
        self.jsonld: list[str] = []
        self._in_ld = False
        self._svg_depth = 0
        self.asset_refs: set[str] = set()

    def handle_starttag(self, tag: str, attrs_list) -> None:
        a = {k.lower(): (v or "") for k, v in attrs_list}
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a and a["id"]:
            self.ids.add(a["id"])
        if tag == "svg":
            self._svg_depth += 1
        # inline SVGs carry their own <title>/<desc> for accessibility — those are
        # not the document title, and must not be concatenated into it
        if tag == "title" and not self._svg_depth:
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            href = a.get("href", "")
            if href.startswith("/"):
                self.asset_refs.add(href)
        elif tag == "a":
            self.anchors.append(a)
        elif tag == "img":
            self.images.append(a)
            src = a.get("src", "")
            if src.startswith("/"):
                self.asset_refs.add(src)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self.headings.append((self._heading_level, ""))
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.jsonld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "svg":
            self._svg_depth = max(0, self._svg_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag == "script":
            self._in_ld = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._in_ld and self.jsonld:
            self.jsonld[-1] += data
        elif self._heading_level is not None and self.headings:
            lvl, txt = self.headings[-1]
            self.headings[-1] = (lvl, (txt + data).strip())

    def meta(self, **kw) -> str | None:
        for m in self.metas:
            if all(m.get(k) == v for k, v in kw.items()):
                return m.get("content")
        return None

    def link(self, rel: str) -> str | None:
        for l in self.links:
            if l.get("rel", "").lower() == rel:
                return l.get("href")
        return None


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_bytes()[:24]
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", head[16:24])
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- checks ---
def check_page(name: str, raw: str, canon_path: str | None) -> Page:
    p = Page()
    p.feed(raw)
    idx = canon_path is not None
    tag = f"[{name}]"

    if not p.lang:
        err(f"{tag} <html> has no lang attribute")
    elif idx and p.lang != "en-GB":
        warn(f"{tag} lang is {p.lang!r}, expected 'en-GB'")

    title = p.title.strip()
    if not title:
        err(f"{tag} no <title>")
    elif not (TITLE_MIN <= len(title) <= TITLE_MAX):
        (err if idx else warn)(
            f"{tag} title is {len(title)} chars (aim {TITLE_MIN}-{TITLE_MAX}): {title!r}"
        )

    desc = p.meta(name="description")
    if idx:
        if not desc:
            err(f"{tag} no meta description")
        elif not (DESC_MIN <= len(desc) <= DESC_MAX):
            warn(f"{tag} meta description is {len(desc)} chars (aim {DESC_MIN}-{DESC_MAX})")

    robots = (p.meta(name="robots") or "").lower()
    if idx and "noindex" in robots:
        err(f"{tag} the indexable page is set to noindex")
    if not idx and "noindex" not in robots:
        err(f"{tag} should be noindex")

    canonical = p.link("canonical")
    if idx:
        if not canonical:
            err(f"{tag} no rel=canonical")
        elif canonical != f"{SITE}{canon_path}":
            err(f"{tag} canonical is {canonical!r}, expected {SITE}{canon_path}")

    h1s = [t for lvl, t in p.headings if lvl == 1]
    if idx:
        if len(h1s) != 1:
            err(f"{tag} expected exactly 1 <h1>, found {len(h1s)}")
        levels = [lvl for lvl, _ in p.headings]
        for a, b in zip(levels, levels[1:]):
            if b > a + 1:
                warn(f"{tag} heading level jumps h{a} -> h{b}")
                break

    # social cards
    if idx:
        for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
            if not p.meta(property=prop):
                err(f"{tag} missing {prop}")
        if not p.meta(name="twitter:card"):
            warn(f"{tag} missing twitter:card")
        og_url = p.meta(property="og:url")
        if og_url and canonical and og_url != canonical:
            warn(f"{tag} og:url {og_url!r} != canonical {canonical!r}")

        og_img = p.meta(property="og:image") or ""
        if og_img.startswith(SITE):
            local = ROOT / og_img[len(SITE):].lstrip("/")
            if not local.exists():
                err(f"{tag} og:image not in repo: {local.name}")
            else:
                dims = png_size(local)
                if dims and dims != (1200, 630):
                    warn(f"{tag} og:image is {dims[0]}x{dims[1]}, expected 1200x630")

    # images need alt
    for im in p.images:
        if "alt" not in im:
            err(f"{tag} <img src={im.get('src','?')!r}> has no alt attribute")

    # internal anchors resolve
    for a in p.anchors:
        href = a.get("href", "")
        if href.startswith("#") and len(href) > 1:
            if href[1:] not in p.ids:
                err(f"{tag} anchor {href} points at an id that does not exist")
        elif href.startswith("/"):
            p.asset_refs.add(href.split("#")[0].split("?")[0])
        elif href and not re.match(r"(https?:|mailto:|tel:|#)", href):
            # relative link — resolve against this page's folder
            rel = (Path(name).parent / href.split("#")[0].split("?")[0]).as_posix()
            if not (ROOT / rel).exists():
                err(f"{tag} relative link points at a missing file: {href}")
        if a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
            warn(f"{tag} target=_blank without rel=noopener: {href}")

    # local assets exist
    for ref in sorted(p.asset_refs):
        if not ref or ref == "/":
            continue
        if not (ROOT / ref.lstrip("/")).exists():
            err(f"{tag} references missing local file: {ref}")

    # CSS url() references (inline <style> blocks) point at real files too
    for ref in set(re.findall(r"url\((/[^)\"'\s]+)\)", raw)):
        if not (ROOT / ref.lstrip("/")).exists():
            err(f"{tag} CSS url() references missing local file: {ref}")

    # third-party font regression guard
    if "fonts.googleapis.com" in raw or "fonts.gstatic.com" in raw:
        err(f"{tag} loads fonts from Google — self-hosted fonts were undone")

    kb = len(raw.encode("utf-8")) / 1024
    if kb > HTML_MAX_KB:
        warn(f"{tag} HTML is {kb:.0f} KB (over {HTML_MAX_KB} KB)")
    else:
        note(f"{tag} HTML {kb:.0f} KB")

    return p


def check_jsonld(p: Page) -> str | None:
    """Validate the graph and return its dateModified."""
    if not p.jsonld:
        err("[index.html] no JSON-LD structured data")
        return None

    date_modified = None
    for i, blob in enumerate(p.jsonld):
        try:
            data = json.loads(blob)
        except json.JSONDecodeError as exc:
            err(f"[index.html] JSON-LD block {i + 1} is invalid JSON: {exc}")
            continue

        if data.get("@context", "").rstrip("/") != "https://schema.org":
            warn(f"[index.html] JSON-LD block {i + 1} has an unexpected @context")

        graph = data.get("@graph", [data])
        declared: set[str] = set()
        referenced: set[str] = set()
        types: set[str] = set()

        def walk(node, top=False):
            if isinstance(node, dict):
                keys = set(node)
                if "@id" in node:
                    if top or keys - {"@id"}:
                        declared.add(node["@id"])
                    if keys == {"@id"}:
                        referenced.add(node["@id"])
                t = node.get("@type")
                if top and t:
                    types.update([t] if isinstance(t, str) else t)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        for node in graph:
            walk(node, top=True)

        for node in graph:
            if node.get("@type") == "WebPage":
                date_modified = node.get("dateModified")

        dangling = referenced - declared
        for ref in sorted(dangling):
            err(f"[index.html] JSON-LD @id reference does not resolve: {ref}")

        for want in ("ProfessionalService", "Person", "WebSite", "WebPage"):
            if want not in types:
                warn(f"[index.html] JSON-LD has no {want} node")

        biz = next((n for n in graph if "ProfessionalService" in str(n.get("@type"))), None)
        if biz:
            for field in ("name", "url", "address", "areaServed", "email"):
                if field not in biz:
                    warn(f"[index.html] ProfessionalService missing {field!r}")

        if "FAQPage" in types:
            note("FAQPage present — Google dropped FAQ rich results (June 2026); "
                 "harmless, still used by Bing")

    return date_modified


def check_robots() -> None:
    path = ROOT / "robots.txt"
    if not path.exists():
        err("robots.txt is missing")
        return
    body = path.read_text(encoding="utf-8")
    if f"Sitemap: {SITE}/sitemap.xml" not in body:
        err("robots.txt has no correct Sitemap: line")
    for block in re.split(r"\n\s*\n", body):
        if re.search(r"^User-agent:\s*\*", block, re.M | re.I) and re.search(
            r"^Disallow:\s*/\s*$", block, re.M | re.I
        ):
            err("robots.txt blocks the whole site for all crawlers")


def check_sitemap(date_modified: str | None) -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        err("sitemap.xml is missing")
        return
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        err(f"sitemap.xml is not valid XML: {exc}")
        return

    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text.strip() for e in root.findall(".//s:loc", ns) if e.text]

    # every indexable page must be listed, and nothing else may be
    expected = {f"{SITE}{path}" for path in PAGES.values() if path is not None}
    for url in sorted(expected - set(locs)):
        err(f"sitemap.xml is missing an indexable page: {url}")
    for url in sorted(set(locs) - expected):
        warn(f"sitemap.xml lists a URL that is not a known page: {url}")
    for loc in locs:
        if not loc.startswith(SITE):
            err(f"sitemap.xml lists an off-site URL: {loc}")

    lastmods = [e.text.strip() for e in root.findall(".//s:lastmod", ns) if e.text]
    for lm in lastmods:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm):
            err(f"sitemap.xml lastmod is not ISO yyyy-mm-dd: {lm}")
    if date_modified and lastmods and date_modified not in lastmods:
        warn(f"sitemap lastmod {lastmods[0]} != JSON-LD dateModified {date_modified} "
             f"(run --stamp)")


def check_footer_date(raw: str, date_modified: str | None) -> None:
    m = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})">', raw)
    if not m:
        warn("no <time datetime> freshness stamp in the footer")
        return
    if date_modified and m.group(1) != date_modified:
        warn(f"footer date {m.group(1)} != JSON-LD dateModified {date_modified} (run --stamp)")


def check_live() -> None:
    """
    Verify production server configuration — the things a static file audit
    cannot see. These are Cloudflare zone/DNS settings, not repo content, so a
    failure here means 'go click something', not 'the code is wrong'.
    """
    import http.client
    import socket
    import urllib.error
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw):  # noqa: D102, ANN002, ANN003
            return None

    opener = urllib.request.build_opener(NoRedirect)
    ua = {"User-Agent": "seo-audit/1.0 (+https://cheltenhamdata.co.uk/)"}

    def head(url: str):
        req = urllib.request.Request(url, headers=ua, method="GET")
        try:
            with opener.open(req, timeout=20) as r:
                return r.status, dict(r.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers or {})
        except (urllib.error.URLError, socket.gaierror, http.client.HTTPException,
                TimeoutError, ConnectionError) as exc:
            return None, {"_error": str(getattr(exc, "reason", exc))}

    host = SITE.removeprefix("https://")

    # 1. http -> https must be a permanent redirect
    status, headers = head(f"http://{host}/")
    if status is None:
        err(f"[live] http://{host}/ is unreachable: {headers.get('_error')}")
    elif status in (301, 308):
        loc = headers.get("Location", "")
        if loc.startswith("https://"):
            note(f"[live] http -> https redirect OK ({status})")
        else:
            err(f"[live] http redirects to {loc!r}, not https")
    else:
        err(f"[live] http://{host}/ returns {status} instead of a 301 to https "
            f"— enable Cloudflare SSL/TLS > Edge Certificates > Always Use HTTPS")

    # 2. canonical host serves 200 with an explicit charset
    status, headers = head(f"{SITE}/")
    if status != 200:
        err(f"[live] {SITE}/ returns {status}")
    else:
        ctype = headers.get("Content-Type", "")
        if "charset" not in ctype.lower():
            err(f"[live] Content-Type has no charset: {ctype!r}")
        else:
            note(f"[live] Content-Type {ctype}")

    # 3. www must either redirect to the apex or not exist at all
    status, headers = head(f"https://www.{host}/")
    if status is None:
        warn(f"[live] www.{host} does not resolve. No duplicate-content risk, "
             f"but links and typed URLs using www are dead — add a proxied CNAME "
             f"plus a 301 to the apex")
    elif status in (301, 308):
        note(f"[live] www -> apex redirect OK ({status})")
    elif status == 200:
        err(f"[live] www.{host} serves 200 — duplicate content, must 301 to the apex")

    # 4. key URLs and a real 404
    for path in ("/robots.txt", "/sitemap.xml", "/og-image.png", "/favicon.ico"):
        status, _ = head(f"{SITE}{path}")
        if status != 200:
            err(f"[live] {path} returns {status}")
    status, _ = head(f"{SITE}/this-page-should-not-exist-9f3a")
    if status != 404:
        err(f"[live] unknown URLs return {status}, expected 404")


def stamp_today() -> None:
    """Push today's date into the footer, JSON-LD and sitemap."""
    today = date.today().isoformat()
    pretty = f"{date.today().day} {date.today():%B %Y}"

    page = ROOT / "index.html"
    s = page.read_text(encoding="utf-8")
    s = re.sub(r'"dateModified": "\d{4}-\d{2}-\d{2}"', f'"dateModified": "{today}"', s)
    s = re.sub(r'<time datetime="\d{4}-\d{2}-\d{2}">[^<]*</time>',
               f'<time datetime="{today}">{pretty}</time>', s)
    page.write_text(s, encoding="utf-8")

    sm = ROOT / "sitemap.xml"
    if sm.exists():
        t = sm.read_text(encoding="utf-8")
        t = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>",
                   f"<lastmod>{today}</lastmod>", t)
        sm.write_text(t, encoding="utf-8")
    print(f"{DIM}stamped {today}{RESET}")


def main() -> int:
    ap = argparse.ArgumentParser(description="SEO gate for cheltenhamdata.co.uk")
    ap.add_argument("--stamp", action="store_true", help="re-stamp today's date first")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    ap.add_argument("--live", action="store_true",
                    help="also check production server config (redirects, charset)")
    args = ap.parse_args()

    if args.stamp:
        stamp_today()

    index_page = None
    index_raw = ""
    for name, canon_path in PAGES.items():
        path = ROOT / name
        if not path.exists():
            err(f"{name} is missing")
            continue
        raw = path.read_text(encoding="utf-8")
        page = check_page(name, raw, canon_path)
        if name == "index.html":
            index_page, index_raw = page, raw

    date_modified = check_jsonld(index_page) if index_page else None
    check_robots()
    check_sitemap(date_modified)
    if index_raw:
        check_footer_date(index_raw, date_modified)

    for expected in ("site.webmanifest", "_headers", "og-image.png", "favicon.ico"):
        if not (ROOT / expected).exists():
            err(f"{expected} is missing")

    if args.live:
        check_live()

    print()
    for n in notes:
        print(f"{DIM}  ·  {n}{RESET}")
    for w in warns:
        print(f"{YEL}  WARN  {w}{RESET}")
    for e in errors:
        print(f"{RED}  ERROR {e}{RESET}")

    print()
    if errors:
        print(f"{RED}FAILED — {len(errors)} error(s), {len(warns)} warning(s){RESET}")
        return 1
    if warns and args.strict:
        print(f"{YEL}FAILED (strict) — {len(warns)} warning(s){RESET}")
        return 1
    print(f"{GRN}PASSED — 0 errors, {len(warns)} warning(s){RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
