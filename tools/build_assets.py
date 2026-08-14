#!/usr/bin/env python3
"""
Build every static asset the site needs, reproducibly.

  python tools/build_assets.py

Produces:
  fonts/*.woff2 + fonts/fonts.css   self-hosted webfonts (no third-party request)
  og-image.png                      1200x630 social/preview card
  blog/*/og.png                     per-post social cards
  cork.svg                          300x300 seamless cork tile (evidence board)
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


# --- the paper look, shared by every card -----------------------------------
def paper_bg(W: int, H: int) -> Image.Image:
    """Warm stock, a cutting-mat grid, and a lamp in the top-right corner."""
    img = Image.new("RGB", (W, H), P_BG)
    d = ImageDraw.Draw(img, "RGBA")
    draw_grid(d, W, H, 56, (120, 92, 54, 16))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(34, 0, -1):
        gd.ellipse([W - 300 - i * 22, -260 - i * 16, W + i * 22, 300 + i * 16],
                   fill=(255, 251, 240, max(int(2.4 * (34 - i)) // 7, 1)))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    ImageDraw.Draw(img, "RGBA").rectangle([0, 0, 6, H], fill=P_ACCENT)
    return img


def sticky(size: int, angle: float = -6.0) -> Image.Image:
    """
    The house motif: a post-it with a small bar chart on it. Drawn at 3x and
    rotated with expand, so the edges stay clean once it is scaled back down.
    """
    S = size * 3
    note = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(note, "RGBA")
    d.rectangle([0, 0, S, S], fill=(242, 220, 130, 255))
    # the adhesive strip along the top sits a shade darker, as it does on paper
    d.rectangle([0, 0, S, int(S * 0.20)], fill=(190, 158, 48, 46))
    # three ascending bars
    bw, gap = int(S * 0.155), int(S * 0.075)
    x0 = int((S - (bw * 3 + gap * 2)) / 2)
    base_y, top = int(S * 0.79), int(S * 0.30)
    for i, frac in enumerate((0.34, 0.66, 1.0)):
        h = int((base_y - top) * frac)
        x = x0 + i * (bw + gap)
        d.rectangle([x, base_y - h, x + bw, base_y], fill=P_ACCENT)
    out = note.rotate(angle, expand=True, resample=Image.BICUBIC)
    return out.resize((int(out.width / 3), int(out.height / 3)), Image.LANCZOS)


def paste_sticky(img: Image.Image, size: int, xy: tuple, angle: float = -6.0) -> None:
    note = sticky(size, angle)
    shadow = Image.new("RGBA", note.size, (0, 0, 0, 0))
    shadow.paste((84, 60, 32, 70), (0, 0), note.split()[3])
    img.paste(Image.alpha_composite(Image.new("RGBA", note.size, (0, 0, 0, 0)), shadow),
              (xy[0] + 5, xy[1] + 9), shadow)
    img.paste(note, xy, note)


def build_og() -> None:
    W, H = 1200, 630
    img = paper_bg(W, H)
    paste_sticky(img, 168, (W - 250, 58), angle=-7)
    d = ImageDraw.Draw(img, "RGBA")

    PAD = 76
    f_eyebrow = load("Space Mono", 400, 21)
    f_name = load("Space Grotesk", 600, 68)
    f_role = load("Space Grotesk", 500, 34)
    f_body = load("Inter Tight", 400, 26)
    f_stat = load("Space Grotesk", 600, 42)
    f_lab = load("Inter Tight", 400, 19)
    f_by = load("Inter Tight", 400, 22)

    y = PAD
    d.text((PAD, y), "CHELTENHAM  \u00b7  GLOUCESTERSHIRE  \u00b7  UK", font=f_eyebrow, fill=P_ACCENT)
    y += 58
    # The card leads with the trading name people see in emails, with the
    # person behind it named directly underneath.
    d.text((PAD, y), "Cheltenham Data", font=f_name, fill=P_TEXT)
    y += 84
    d.text((PAD, y), "Szymon Pecherski", font=f_by, fill=P_MUTED)
    y += 38
    d.text((PAD, y), "Data Analyst & BI Specialist", font=f_role, fill=P_ACCENT)
    y += 62
    d.text((PAD, y), "Dashboards, reporting and process automation", font=f_body, fill=P_MUTED)
    y += 38
    d.text((PAD, y), "for small brands outgrowing their spreadsheets.", font=f_body, fill=P_MUTED)

    sy = H - 168
    d.line([(PAD, sy - 34), (W - PAD, sy - 34)], fill=P_LINE, width=1)
    stats = [("\u00a342,500", "commercial income unlocked"),
             ("100+", "manual hours removed a year"),
             ("20+", "procedures automated")]
    col = (W - PAD * 2) // 3
    for i, (big, lab) in enumerate(stats):
        x = PAD + i * col
        d.text((x, sy), big, font=f_stat, fill=P_ACCENT)
        d.text((x, sy + 58), lab, font=f_lab, fill=P_FAINT)

    img.save(ROOT / "og-image.png", "PNG", optimize=True)
    print("  wrote og-image.png (1200x630)")


# ------------------------------------------------------------------ cork --
# The evidence board's surface. Cork is dense, low-contrast and granular:
# irregular chips of light and dark pressed together, with almost no base
# showing through. Two approaches that look obvious and are not: a lattice of
# CSS radial-gradients tiles on a visible grid and reads as polka dots, and
# feTurbulence — filtered or raw — reads as smooth hardboard while emitting
# per-channel colour noise that tints the board into confetti.
#
# So the chips are drawn explicitly. Anything crossing a tile edge is redrawn
# on the far side, which is what makes the result wrap seamlessly at any size.
CORK_BASE = "#c69c62"
CORK_DARK = ["#b08a4f", "#a17c42", "#bb9660", "#96733a"]
CORK_LIGHT = ["#dcb47e", "#dfba86", "#cba268", "#e3c391"]
CORK_TILE = 300
CORK_SEED = 23


def build_cork() -> None:
    """
    Emitted as SVG rather than a raster, which is counter-intuitive for a noise
    texture but measurably right here: ~1,160 tiny shapes are enormously
    repetitive, so the file is 45 KB raw but 8 KB gzipped. A lossless WebP of
    the same tile is 29 KB and cannot compress any further, because it already
    has. Over the wire — which is the number that matters — SVG wins 3.5x.
    It also stays diffable in git.
    """
    import random

    rnd = random.Random(CORK_SEED)
    # group by (fill, opacity) so each colour's attributes are written once
    groups: dict[tuple[str, float], list[str]] = {}

    def chip(x: float, y: float, rx: float, ry: float, fill: str, op: float) -> None:
        key = (fill, round(op, 2))
        # redraw across every edge the chip touches, so the tile wraps
        for dx in (-CORK_TILE, 0, CORK_TILE):
            for dy in (-CORK_TILE, 0, CORK_TILE):
                cx, cy = x + dx, y + dy
                if cx < -rx or cx > CORK_TILE + rx or cy < -ry or cy > CORK_TILE + ry:
                    continue
                shape = (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}"/>'
                         if abs(rx - ry) > 0.05 else
                         f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rx:.1f}"/>')
                groups.setdefault(key, []).append(shape)

    # three passes: coarse dark chips, lighter grains, then fine speckle
    for n, palette, r_lo, r_hi, o_lo, o_hi, squash in (
        (270, CORK_DARK, 2.6, 5.4, 0.22, 0.38, True),
        (300, CORK_LIGHT, 1.8, 3.8, 0.24, 0.42, False),
        (360, CORK_LIGHT + CORK_DARK, 1.0, 2.0, 0.20, 0.28, False),
    ):
        for _ in range(n):
            r = rnd.uniform(r_lo, r_hi)
            chip(
                rnd.uniform(0, CORK_TILE), rnd.uniform(0, CORK_TILE),
                r, r * rnd.uniform(0.62, 1.0) if squash else r,
                rnd.choice(palette), rnd.uniform(o_lo, o_hi),
            )

    body = "".join(f'<g fill="{f}" opacity="{o}">{"".join(v)}</g>' for (f, o), v in groups.items())
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CORK_TILE}" height="{CORK_TILE}">'
           f'<rect width="{CORK_TILE}" height="{CORK_TILE}" fill="{CORK_BASE}"/>{body}</svg>')

    out = ROOT / "cork.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"  wrote cork.svg ({CORK_TILE}x{CORK_TILE}, {len(svg) / 1024:.0f} KB, ~8 KB gzipped)")


def build_og_post() -> None:
    """Social card for the hallucination post — the finding, not a stock graphic."""
    dest = ROOT / "blog/ai-hallucination-rates-2024-vs-2026/og.png"
    if not dest.parent.exists():
        print("  ! blog post folder missing, skipping post OG card")
        return

    W, H = 1200, 630
    img = paper_bg(W, H)
    paste_sticky(img, 150, (W - 226, 54), angle=6)
    d = ImageDraw.Draw(img, "RGBA")

    f_eyebrow = load("Space Mono", 400, 20)
    f_head = load("Space Grotesk", 600, 60)
    f_sub = load("Inter Tight", 400, 24)
    f_big = load("Space Grotesk", 600, 76)
    f_lab = load("Inter Tight", 400, 19)
    f_by = load("Space Mono", 400, 18)

    PAD = 74
    d.text((PAD, 62), "SZYMON PECHERSKI  \u00b7  ANALYSIS", font=f_eyebrow, fill=P_ACCENT)
    d.text((PAD, 118), "AI hallucination rates", font=f_head, fill=P_TEXT)
    d.text((PAD, 188), "went up, not down", font=f_head, fill=P_ACCENT)
    d.text((PAD, 278), "157 models across two snapshots of Vectara's leaderboard",
           font=f_sub, fill=P_MUTED)

    # the finding, as a before/after. The arrow is drawn, not typed: none of the
    # brand fonts ship U+2192 and Pillow has no glyph fallback, so it would tofu.
    by = 372
    d.line([(PAD, by - 26), (W - PAD, by - 26)], fill=P_LINE, width=1)
    d.text((PAD, by), "6.25%", font=f_big, fill=P_MUTED)

    ax, ay = PAD + 246, by + 44
    d.line([(ax, ay), (ax + 62, ay)], fill=P_SIGNAL, width=7)
    d.polygon([(ax + 58, ay - 15), (ax + 88, ay), (ax + 58, ay + 15)], fill=P_SIGNAL)

    d.text((ax + 112, by), "10.24%", font=f_big, fill=P_ACCENT)
    d.text((PAD, by + 96), "mean hallucination rate, 2024 to 2026", font=f_lab, fill=P_FAINT)

    d.text((PAD, H - 68), "cheltenhamdata.co.uk", font=f_by, fill=P_FAINT)

    img.save(dest, "PNG", optimize=True)
    print(f"  wrote {dest.relative_to(ROOT)} (1200x630)")


# --- paper palette, matching the live site's light theme -------------------
P_BG, P_CARD, P_TEXT = "#e7dfd1", "#f9f4ec", "#221c15"
P_ACCENT, P_MUTED, P_FAINT, P_LINE = "#2c6244", "#6b6050", "#8c8070", "#cfc3ad"
P_SIGNAL = "#a8620f"


def build_og_jobs() -> None:
    """Social card for the UK job market post, in the current paper brand."""
    dest = ROOT / "blog/uk-data-job-salary-transparency-2026/og.png"
    if not dest.parent.exists():
        print("  ! job post folder missing, skipping its OG card")
        return

    W, H = 1200, 630
    img = paper_bg(W, H)
    paste_sticky(img, 150, (W - 226, 54), angle=6)
    d = ImageDraw.Draw(img, "RGBA")

    f_eyebrow = load("Space Mono", 400, 20)
    f_head = load("Space Grotesk", 600, 62)
    f_sub = load("Inter Tight", 400, 24)
    f_big = load("Space Grotesk", 600, 104)
    f_lab = load("Inter Tight", 400, 20)
    f_by = load("Space Mono", 400, 18)

    PAD = 74
    d.text((PAD, 60), "SZYMON PECHERSKI  ·  ANALYSIS", font=f_eyebrow, fill=P_ACCENT)
    d.text((PAD, 116), "85% of UK data job ads", font=f_head, fill=P_TEXT)
    d.text((PAD, 188), "don't tell you the salary", font=f_head, fill=P_ACCENT)
    d.text((PAD, 282), "9,559 postings scraped, cleaned and analysed", font=f_sub, fill=P_MUTED)

    by = 372
    d.line([(PAD, by - 24), (W - PAD, by - 24)], fill=P_LINE, width=1)
    d.text((PAD, by), "14.9%", font=f_big, fill=P_ACCENT)
    d.text((PAD, by + 118), "state a salary", font=f_lab, fill=P_FAINT)

    d.text((PAD + 470, by), "12.7%", font=f_big, fill=P_MUTED)
    d.text((PAD + 470, by + 118), "in London, the biggest market", font=f_lab, fill=P_FAINT)

    d.text((PAD, H - 66), "cheltenhamdata.co.uk", font=f_by, fill=P_FAINT)

    img.save(dest, "PNG", optimize=True)
    print(f"  wrote {dest.relative_to(ROOT)} (1200x630)")


def mark(size: int, radius_ratio: float = 0.1875, bg: str | None = None) -> Image.Image:
    """
    The brand mark: a sticky note with three ascending bars.

    Same motif as the cards, and it survives being shrunk to a 16px favicon —
    a yellow square with three green bars is still readable at that size, which
    is the only test a favicon has to pass.
    """
    S = size * 4  # supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    r = int(S * radius_ratio)

    if bg is not None:                       # opaque tile, for apple-touch-icon
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=bg)

    pad = int(S * 0.10)
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=int(S * 0.055),
                        fill=(242, 220, 130, 255))
    # adhesive strip
    d.rounded_rectangle([pad, pad, S - pad, pad + int(S * 0.17)],
                        radius=int(S * 0.055), fill=(190, 158, 48, 52))

    bw = int(S * 0.135)
    gap = int(S * 0.070)
    x0 = int((S - (bw * 3 + gap * 2)) / 2)
    base_y, top = int(S * 0.735), int(S * 0.305)
    for i, frac in enumerate((0.34, 0.66, 1.0)):
        h = int((base_y - top) * frac)
        x = x0 + i * (bw + gap)
        d.rounded_rectangle([x, base_y - h, x + bw, base_y],
                            radius=int(S * 0.012), fill=P_ACCENT)

    return img.resize((size, size), Image.LANCZOS)


def build_icons() -> None:
    mark(512).save(ROOT / "icon-512.png", "PNG", optimize=True)
    mark(192).save(ROOT / "icon-192.png", "PNG", optimize=True)
    # Apple flattens transparency and applies its own mask, so it needs a tile
    apple = Image.new("RGB", (180, 180), P_ACCENT)
    tile = mark(180, radius_ratio=0.0, bg=P_ACCENT)
    apple.paste(tile, (0, 0), tile)
    apple.save(ROOT / "apple-touch-icon.png", "PNG", optimize=True)

    logo = Image.new("RGB", (512, 512), P_ACCENT)
    lm = mark(512, bg=P_ACCENT)
    logo.paste(lm, (0, 0), lm)
    logo.save(ROOT / "logo.png", "PNG", optimize=True)

    ico = mark(64, bg=P_ACCENT)
    ico.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
        f"<rect width='32' height='32' rx='6' fill='{P_ACCENT}'/>"
        "<rect x='3.2' y='3.2' width='25.6' height='25.6' rx='1.8' fill='#f2dc82'/>"
        "<rect x='3.2' y='3.2' width='25.6' height='4.4' rx='1.8' fill='#be9e30' opacity='.2'/>"
        f"<g fill='{P_ACCENT}'>"
        "<rect x='7.6' y='18.5' width='4.4' height='5.0' rx='.4'/>"
        "<rect x='13.8' y='14.6' width='4.4' height='8.9' rx='.4'/>"
        "<rect x='20.0' y='10.2' width='4.4' height='13.3' rx='.4'/>"
        "</g></svg>"
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
    build_og_jobs()
    build_icons()
    build_cork()
    check_glyph_coverage()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
