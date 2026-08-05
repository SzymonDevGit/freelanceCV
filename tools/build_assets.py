#!/usr/bin/env python3
"""
Build every static asset the site needs, reproducibly.

  python tools/build_assets.py

Produces:
  fonts/*.woff2 + fonts/fonts.css   self-hosted webfonts (no third-party request)
  og-image.png                      1200x630 social/preview card
  logo.png                          512x512 square logo (schema.org "logo")
  apple-touch-icon.png              180x180
  icon-192.png, icon-512.png        PWA / manifest icons
  favicon.svg, favicon.ico          browser icons

Fonts are pulled from Google Fonts once and cached in .cache/. Re-run any time;
output is deterministic.
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

try:
    import requests
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Missing deps. Run:  python -m pip install Pillow requests")

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "fonts"
CACHE = ROOT / ".cache"

# --- brand tokens (kept in sync with the :root palette in index.html) --------
BG = "#14100c"
CARD = "#1f1912"
OAK = "#cd9c60"
TAN = "#e7c495"
WALNUT = "#8a5a30"
TEXT = "#f0e7da"
MUTED = "#9b8b79"
FAINT = "#7d6e5e"
LINE = "#332a20"

# family -> weights actually used by the stylesheet
FAMILIES = {
    "Space Grotesk": [400, 500, 600],
    "Inter Tight": [400, 500, 600],
    "Space Mono": [400],
}

UA_WOFF2 = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
UA_TTF = "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"


def css_url(family: str, weights: list[int]) -> str:
    fam = family.replace(" ", "+")
    return (
        "https://fonts.googleapis.com/css2?family="
        f"{fam}:wght@{';'.join(str(w) for w in weights)}&display=swap"
    )


def fetch(url: str, ua: str) -> str:
    r = requests.get(url, headers={"User-Agent": ua}, timeout=30)
    r.raise_for_status()
    return r.text


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return dest


# ---------------------------------------------------------------- webfonts --
BLOCK_RE = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", re.S)
SRC_RE = re.compile(r"url\((https://[^)]+\.woff2)\)")


# Everything an en-GB business site realistically needs: printable ASCII,
# Latin-1 supplement (accents, £, ©), and the typographic punctuation the copy
# uses (en/em dashes, curly quotes, ellipsis, arrows). Anything outside this
# falls back to the system font, which for this content never happens.
SUBSET = (
    list(range(0x20, 0x7F))
    + list(range(0xA0, 0x100))
    + [0x0131, 0x0152, 0x0153, 0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015,
       0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E, 0x2020, 0x2021, 0x2022,
       0x2026, 0x2030, 0x2032, 0x2033, 0x2039, 0x203A, 0x2044, 0x20AC, 0x2122,
       0x2190, 0x2191, 0x2192, 0x2193, 0x2212, 0x2215, 0xFEFF, 0xFFFD]
)


def subset_woff2(src: Path, dest: Path) -> None:
    """Cut a Google-Fonts woff2 down to the glyphs this site can actually use."""
    from fontTools.subset import Options, Subsetter
    from fontTools.ttLib import TTFont

    font = TTFont(str(src))
    opts = Options()
    opts.layout_features = ["*"]   # keep kerning and ligatures
    opts.name_IDs = ["*"]          # keep the OFL licence strings
    opts.notdef_outline = True
    sub = Subsetter(options=opts)
    sub.populate(unicodes=SUBSET)
    sub.subset(font)
    font.flavor = "woff2"
    font.save(str(dest))


def build_webfonts() -> None:
    """Download the latin woff2 files, subset them, emit fonts/fonts.css."""
    FONT_DIR.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    out_blocks: list[str] = []
    before = after = 0

    for family, weights in FAMILIES.items():
        css = fetch(css_url(family, weights), UA_WOFF2)
        for subset, block in BLOCK_RE.findall(css):
            # latin only — SUBSET below already covers the accented characters
            # that would otherwise need the latin-ext file.
            if subset != "latin":
                continue
            m = SRC_RE.search(block)
            if not m:
                continue
            remote = m.group(1)
            weight_m = re.search(r"font-weight:\s*(\d+)", block)
            weight = weight_m.group(1) if weight_m else "400"
            slug = family.lower().replace(" ", "-")
            name = f"{slug}-{weight}.woff2"

            raw = download(remote, CACHE / f"src-{slug}-{weight}.woff2")
            dest = FONT_DIR / name
            subset_woff2(raw, dest)
            before += raw.stat().st_size
            after += dest.stat().st_size

            # drop the unicode-range: the file is now the whole supported set
            rule = block.replace(remote, f"/fonts/{name}")
            rule = re.sub(r"\s*unicode-range:[^;]+;", "", rule)
            rule = re.sub(r"\s+", " ", rule).replace("@font-face {", "@font-face{")
            out_blocks.append(rule.strip())
            print(f"  font  {name}  {raw.stat().st_size // 1024}K -> "
                  f"{dest.stat().st_size // 1024}K")

    # remove any stale files from a previous (unsubsetted) build
    keep = {b.split("/fonts/")[1].split(")")[0] for b in out_blocks}
    for old in FONT_DIR.glob("*.woff2"):
        if old.name not in keep:
            old.unlink()
            print(f"  drop  {old.name}")

    header = (
        "/* Self-hosted, subsetted webfonts. Generated by tools/build_assets.py.\n"
        "   Do not edit: this block is injected into index.html automatically.\n"
        "   Source: Google Fonts (SIL Open Font License 1.1). */\n"
    )
    css_text = "\n".join(out_blocks)
    (FONT_DIR / "fonts.css").write_text(header + css_text + "\n", encoding="utf-8")
    print(f"  wrote fonts/fonts.css ({len(out_blocks)} faces, "
          f"{before // 1024}K -> {after // 1024}K)")
    inject_fonts(css_text)


FONT_BEGIN = "/* FONTS:BEGIN — generated by tools/build_assets.py, do not edit */"
FONT_END = "/* FONTS:END */"


def inject_fonts(css_text: str) -> None:
    """Keep the @font-face block inside index.html in sync with fonts/."""
    page = ROOT / "index.html"
    if not page.exists():
        print("  ! index.html not found, skipping font injection")
        return
    html = page.read_text(encoding="utf-8")
    if FONT_BEGIN not in html or FONT_END not in html:
        print("  ! FONTS:BEGIN/END markers missing in index.html, skipping injection")
        return
    start = html.index(FONT_BEGIN) + len(FONT_BEGIN)
    end = html.index(FONT_END)
    page.write_text(html[:start] + "\n" + css_text + "\n" + html[end:], encoding="utf-8")
    print("  synced @font-face block into index.html")


def ttf(family: str, weight: int) -> Path | None:
    """
    TrueType build of a family/weight for Pillow rendering.

    Google Fonts no longer serves .ttf to legacy user agents, so decompress the
    woff2 we already downloaded for the web instead. Keeps the OG card in the
    real brand typeface rather than a system fallback.
    """
    CACHE.mkdir(exist_ok=True)
    slug = family.lower().replace(" ", "-")
    dest = CACHE / f"{slug}-{weight}.ttf"
    if dest.exists():
        return dest

    src = FONT_DIR / f"{slug}-{weight}.woff2"
    if not src.exists():
        print(f"  ! no woff2 for {family} {weight} - run build_webfonts first")
        return None
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(str(src))
        font.flavor = None  # drop woff2 compression -> plain TTF/OTF
        font.save(str(dest))
        return dest
    except Exception as exc:  # noqa: BLE001
        print(f"  ! could not convert {family} {weight}: {exc}")
        return None


def load(family: str, weight: int, size: int) -> ImageFont.FreeTypeFont:
    path = ttf(family, weight)
    if path and path.exists():
        return ImageFont.truetype(str(path), size)
    for fallback in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ------------------------------------------------------------- og / images --
def draw_grid(d: ImageDraw.ImageDraw, w: int, h: int, step: int, colour: tuple) -> None:
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=colour, width=1)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=colour, width=1)


def build_og() -> None:
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")

    draw_grid(d, W, H, 56, (205, 156, 96, 16))

    # warm corner glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(34, 0, -1):
        a = int(2.4 * (34 - i))
        gd.ellipse([W - 300 - i * 22, -260 - i * 16, W + i * 22, 300 + i * 16],
                   fill=(205, 156, 96, max(a // 7, 1)))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")

    PAD = 76
    d.rectangle([0, 0, 6, H], fill=OAK)

    f_eyebrow = load("Space Mono", 400, 21)
    f_name = load("Space Grotesk", 600, 68)
    f_role = load("Space Grotesk", 500, 34)
    f_body = load("Inter Tight", 400, 26)
    f_stat = load("Space Grotesk", 600, 42)
    f_lab = load("Inter Tight", 400, 19)
    f_by = load("Inter Tight", 400, 22)

    y = PAD
    d.text((PAD, y), "CHELTENHAM  ·  GLOUCESTERSHIRE  ·  UK", font=f_eyebrow, fill=OAK)
    y += 58
    # The card leads with the trading name people see in emails, with the
    # person behind it named directly underneath.
    d.text((PAD, y), "Cheltenham Data", font=f_name, fill=TEXT)
    y += 84
    d.text((PAD, y), "Szymon Pecherski", font=f_by, fill=MUTED)
    y += 38
    d.text((PAD, y), "Data Analyst & BI Specialist", font=f_role, fill=OAK)
    y += 62
    d.text((PAD, y),
           "Dashboards, reporting and process automation",
           font=f_body, fill=MUTED)
    y += 38
    d.text((PAD, y), "for small brands outgrowing their spreadsheets.",
           font=f_body, fill=MUTED)

    # stat strip
    sy = H - 168
    d.line([(PAD, sy - 34), (W - PAD, sy - 34)], fill=LINE, width=1)
    stats = [("£42,500", "commercial income unlocked"),
             ("100+", "manual hours removed a year"),
             ("20+", "procedures automated")]
    col = (W - PAD * 2) // 3
    for i, (big, lab) in enumerate(stats):
        x = PAD + i * col
        d.text((x, sy), big, font=f_stat, fill=OAK)
        d.text((x, sy + 58), lab, font=f_lab, fill=FAINT)

    img.save(ROOT / "og-image.png", "PNG", optimize=True)
    print("  wrote og-image.png (1200x630)")


def build_og_post() -> None:
    """Social card for the hallucination post — the finding, not a stock graphic."""
    dest = ROOT / "blog/ai-hallucination-rates-2024-vs-2026/og.png"
    if not dest.parent.exists():
        print("  ! blog post folder missing, skipping post OG card")
        return

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    draw_grid(d, W, H, 56, (205, 156, 96, 14))
    d.rectangle([0, 0, 6, H], fill=OAK)

    f_eyebrow = load("Space Mono", 400, 20)
    f_head = load("Space Grotesk", 600, 60)
    f_sub = load("Inter Tight", 400, 24)
    f_big = load("Space Grotesk", 600, 76)
    f_lab = load("Inter Tight", 400, 19)
    f_by = load("Space Mono", 400, 18)

    PAD = 74
    d.text((PAD, 62), "SZYMON PECHERSKI  ·  ANALYSIS", font=f_eyebrow, fill=OAK)
    d.text((PAD, 118), "AI hallucination rates", font=f_head, fill=TEXT)
    d.text((PAD, 188), "went up, not down", font=f_head, fill=OAK)
    d.text((PAD, 278), "157 models across two snapshots of Vectara's leaderboard",
           font=f_sub, fill=MUTED)

    # the finding, as a before/after. The arrow is drawn, not typed: none of the
    # brand fonts ship U+2192 and Pillow has no glyph fallback, so it would tofu.
    by = 372
    d.line([(PAD, by - 26), (W - PAD, by - 26)], fill=LINE, width=1)
    d.text((PAD, by), "6.25%", font=f_big, fill=MUTED)

    ax, ay = PAD + 246, by + 44
    d.line([(ax, ay), (ax + 62, ay)], fill=WALNUT, width=7)
    d.polygon([(ax + 58, ay - 15), (ax + 88, ay), (ax + 58, ay + 15)], fill=WALNUT)

    d.text((ax + 112, by), "10.24%", font=f_big, fill=OAK)
    d.text((PAD, by + 96), "mean hallucination rate, 2024 to 2026", font=f_lab, fill=FAINT)

    d.text((PAD, H - 68), "cheltenhamdata.co.uk", font=f_by, fill=FAINT)

    img.save(dest, "PNG", optimize=True)
    print(f"  wrote {dest.relative_to(ROOT)} (1200x630)")


def mark(size: int, radius_ratio: float = 0.1875, bg: str = BG) -> Image.Image:
    """The three-bar mark used across favicons and the logo."""
    S = size * 4  # supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * radius_ratio), fill=bg)

    bar_h = int(S * 0.05)
    x0, x1 = int(S * 0.22), int(S * 0.78)
    short = int(S * 0.60)
    ys = [0.32, 0.50, 0.68]
    for i, yr in enumerate(ys):
        y = int(S * yr) - bar_h // 2
        end = short if i == 2 else x1
        d.rounded_rectangle([x0, y, end, y + bar_h], radius=bar_h // 2, fill=OAK)

    return img.resize((size, size), Image.LANCZOS)


def build_icons() -> None:
    mark(512).save(ROOT / "icon-512.png", "PNG", optimize=True)
    mark(192).save(ROOT / "icon-192.png", "PNG", optimize=True)
    # Apple flattens transparency and applies its own mask
    apple = Image.new("RGB", (180, 180), BG)
    apple.paste(mark(180, radius_ratio=0.0), (0, 0), mark(180, radius_ratio=0.0))
    apple.save(ROOT / "apple-touch-icon.png", "PNG", optimize=True)

    logo = mark(512)
    logo.save(ROOT / "logo.png", "PNG", optimize=True)

    ico = mark(64)
    ico.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"<rect width='32' height='32' rx='6' fill='{BG}'/>"
        f"<g stroke='{OAK}' stroke-width='1.6' stroke-linecap='round'>"
        "<path d='M7 11h18M7 16h18M7 21h11'/></g></svg>"
    )
    (ROOT / "favicon.svg").write_text(svg, encoding="utf-8")
    print("  wrote icon-512/192, apple-touch-icon, logo, favicon.ico, favicon.svg")


def check_glyph_coverage() -> int:
    """
    Warn if any character used in the site's HTML is missing from the subsetted
    fonts. Browsers fall back per glyph so it still renders, but in a mismatched
    face — and anything drawn with Pillow (the OG cards) tofus outright.
    """
    from fontTools.ttLib import TTFont

    used: set[str] = set()
    for page in ROOT.glob("**/*.html"):
        if ".cache" in page.parts:
            continue
        text = re.sub(r"<[^>]+>", " ", page.read_text(encoding="utf-8"))
        text = re.sub(r"&[#\w]+;", " ", text)
        used |= {c for c in text if ord(c) > 0x7E and not c.isspace()}

    problems = 0
    for font_path in sorted(FONT_DIR.glob("*.woff2")):
        cmap: set[int] = set()
        for table in TTFont(str(font_path))["cmap"].tables:
            cmap |= set(table.cmap)
        missing = sorted(c for c in used if ord(c) not in cmap)
        if missing:
            names = ", ".join(f"U+{ord(c):04X}" for c in missing)
            print(f"  ! {font_path.name} lacks glyphs used on the site: {names}")
            problems += 1
    if not problems:
        print(f"  glyph coverage OK ({len(used)} non-ASCII characters used)")
    return problems


def main() -> int:
    print("Building assets ...")
    build_webfonts()
    build_og()
    build_og_post()
    build_icons()
    check_glyph_coverage()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
