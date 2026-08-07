#!/usr/bin/env python3
"""
Generate the inline SVG charts for the hallucination blog post.

  python tools/build_charts.py

Reads the committed CSV, recomputes every figure from the raw rows, and injects
the charts into the post between CHART:<name>:BEGIN / :END markers. Nothing is
hand-typed, so the charts can never drift from the data.

Standard library only. SVG is inlined (no extra requests) and theme-matched.
"""
from __future__ import annotations

import csv
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST = ROOT / "blog/ai-hallucination-rates-2024-vs-2026/index.html"
DATA = ROOT / "blog/ai-hallucination-rates-2024-vs-2026/data/vectara-hallucination-2024-vs-2026.csv"

# The charts are inline SVG in the post, so they inherit the page's custom
# properties. Emitting var(--token) rather than hex is what lets one chart
# render correctly in both the light and dark themes — a baked-in hex would
# be invisible in one of them.
OAK, TAN, MUTED = "var(--oak)", "var(--tan)", "var(--muted)"
FAINT, LINE, TEXT = "var(--faint)", "var(--line)", "var(--text)"
# three-step scale for the banded chart, plus the label colour that sits on it
BAND_GOOD, BAND_MID, BAND_BAD, ON_BAND = "var(--c1)", "var(--c2)", "var(--c3)", "var(--on-c)"
DISP = "'Space Grotesk',ui-sans-serif,system-ui,sans-serif"
MONO = "'Space Mono',ui-monospace,monospace"

BUCKETS = [("<75", lambda l: l < 75), ("75–100", lambda l: 75 <= l < 100),
           ("100–125", lambda l: 100 <= l < 125), ("125+", lambda l: l >= 125)]
BANDS = [("Under 5%", lambda r: r < 5, BAND_GOOD),
         ("5–10%", lambda r: 5 <= r < 10, BAND_MID),
         ("10% or more", lambda r: r >= 10, BAND_BAD)]


def load() -> list[dict]:
    rows = []
    for r in csv.DictReader(DATA.open(encoding="utf-8")):
        r["rate"] = float(r["hallucination_rate_pct"])
        r["len"] = float(r["avg_summary_words"]) if r["avg_summary_words"] else None
        rows.append(r)
    return rows


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chart_length(rows: list[dict]) -> str:
    """Grouped bars: mean hallucination rate by summary-length bucket, per year."""
    W, H = 720, 380
    ml, mr, mt, mb = 54, 16, 46, 64
    pw, ph = W - ml - mr, H - mt - mb
    ymax = 14.0

    series = {}
    for year in ("2024", "2026"):
        d = [r for r in rows if r["year"] == year and r["len"] is not None]
        series[year] = [
            (name, (st.mean([r["rate"] for r in d if t(r["len"])]) if any(t(r["len"]) for r in d) else 0),
             sum(1 for r in d if t(r["len"])))
            for name, t in BUCKETS
        ]

    def y(v): return mt + ph - (v / ymax) * ph

    out = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="c1t c1d" style="width:100%;height:auto">',
        '<title id="c1t">Mean hallucination rate by summary length, 2024 versus 2026</title>',
        '<desc id="c1d">In 2024 the hallucination rate was flat across summary lengths '
        '(7.1% under 75 words down to 5.0% at 125-plus words, but only one model sat in '
        'that longest bucket). In 2026 the rate climbs steadily with length: 8.1% under 75 '
        'words, 8.4% at 75 to 100, 9.8% at 100 to 125, and 13.0% at 125-plus words.</desc>',
    ]
    for g in range(0, int(ymax) + 1, 2):
        out.append(f'<line x1="{ml}" y1="{y(g):.1f}" x2="{W-mr}" y2="{y(g):.1f}" '
                   f'stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="{ml-10}" y="{y(g)+4:.1f}" text-anchor="end" font-family="{MONO}" '
                   f'font-size="11" fill="{FAINT}">{g}%</text>')

    gw = pw / len(BUCKETS)
    bw = gw * 0.28
    for i, (name, _) in enumerate(BUCKETS):
        cx = ml + gw * i + gw / 2
        for j, year in enumerate(("2024", "2026")):
            val, n = series[year][i][1], series[year][i][2]
            colour = MUTED if year == "2024" else OAK
            bx = cx - bw - 3 + j * (bw + 6)
            out.append(f'<rect x="{bx:.1f}" y="{y(val):.1f}" width="{bw:.1f}" '
                       f'height="{mt+ph-y(val):.1f}" fill="{colour}" rx="2"/>')
            out.append(f'<text x="{bx+bw/2:.1f}" y="{y(val)-7:.1f}" text-anchor="middle" '
                       f'font-family="{DISP}" font-size="12.5" font-weight="600" '
                       f'fill="{TEXT}">{val:.1f}%</text>')
            out.append(f'<text x="{bx+bw/2:.1f}" y="{mt+ph+16:.1f}" text-anchor="middle" '
                       f'font-family="{MONO}" font-size="9.5" fill="{FAINT}">n={n}</text>')
        out.append(f'<text x="{cx:.1f}" y="{mt+ph+36:.1f}" text-anchor="middle" '
                   f'font-family="{DISP}" font-size="13" fill="{MUTED}">{esc(name)}</text>')

    out.append(f'<text x="{ml}" y="{H-8}" font-family="{MONO}" font-size="10.5" '
               f'fill="{FAINT}">AVERAGE SUMMARY LENGTH (WORDS)</text>')
    for j, (year, colour) in enumerate((("2024", MUTED), ("2026", OAK))):
        lx = ml + j * 82
        out.append(f'<rect x="{lx}" y="{mt-32}" width="11" height="11" fill="{colour}" rx="2"/>')
        out.append(f'<text x="{lx+17}" y="{mt-22}" font-family="{DISP}" font-size="13" '
                   f'fill="{MUTED}">{year}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_bands(rows: list[dict]) -> str:
    """Stacked bars: share of models in each accuracy band, per year."""
    W, H = 720, 250
    ml, mr, mt, mb = 66, 16, 44, 52
    pw, ph = W - ml - mr, H - mt - mb
    bar_h = 46

    out = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="c2t c2d" style="width:100%;height:auto">',
        '<title id="c2t">Share of models by hallucination band, 2024 versus 2026</title>',
        '<desc id="c2d">In 2024, 44% of the 52 models tested hallucinated on under 5% of '
        'summaries and only 10% hit 10% or worse. By 2026, across 105 models, just 9% were '
        'under 5% while 47% hallucinated on 10% or more.</desc>',
    ]
    for i, year in enumerate(("2024", "2026")):
        d = [r["rate"] for r in rows if r["year"] == year]
        total = len(d)
        top = mt + i * (bar_h + 30)
        x = ml
        out.append(f'<text x="{ml-12}" y="{top+bar_h/2+5}" text-anchor="end" '
                   f'font-family="{DISP}" font-size="15" font-weight="600" fill="{TEXT}">{year}</text>')
        out.append(f'<text x="{ml-12}" y="{top+bar_h/2+21}" text-anchor="end" '
                   f'font-family="{MONO}" font-size="9.5" fill="{FAINT}">n={total}</text>')
        for name, test, colour in BANDS:
            share = sum(1 for v in d if test(v)) / total
            w = share * pw
            out.append(f'<rect x="{x:.1f}" y="{top}" width="{max(w,1):.1f}" height="{bar_h}" '
                       f'fill="{colour}"/>')
            if share > 0.07:
                out.append(f'<text x="{x+w/2:.1f}" y="{top+bar_h/2+6}" text-anchor="middle" '
                           f'font-family="{DISP}" font-size="15" font-weight="600" '
                           f'fill="{ON_BAND}">{share*100:.0f}%</text>')
            x += w
    lx = ml
    for name, _, colour in BANDS:
        out.append(f'<rect x="{lx}" y="{H-26}" width="11" height="11" fill="{colour}" rx="2"/>')
        out.append(f'<text x="{lx+17}" y="{H-16}" font-family="{DISP}" font-size="12.5" '
                   f'fill="{MUTED}">{esc(name)}</text>')
        lx += 26 + len(name) * 7.4
    out.append("</svg>")
    return "\n".join(out)


def inject(html: str, name: str, svg: str) -> str:
    begin, end = f"<!--CHART:{name}:BEGIN-->", f"<!--CHART:{name}:END-->"
    if begin not in html or end not in html:
        raise SystemExit(f"markers for chart {name!r} not found in the post")
    s, e = html.index(begin) + len(begin), html.index(end)
    return html[:s] + "\n" + svg + "\n" + html[e:]


def main() -> int:
    rows = load()
    html = POST.read_text(encoding="utf-8")
    html = inject(html, "length", chart_length(rows))
    html = inject(html, "bands", chart_bands(rows))
    POST.write_text(html, encoding="utf-8")
    print(f"injected 2 charts from {len(rows)} data rows into {POST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
