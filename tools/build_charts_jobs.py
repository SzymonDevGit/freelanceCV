#!/usr/bin/env python3
"""
Build the charts for the UK job-market post and inject them between the
CHART:<name>:BEGIN / :END markers in the post.

  python tools/build_charts_jobs.py

Reads the published aggregate CSVs in the post's own data/ directory, so the
charts are reproducible by anyone who downloads them — the raw scrape is
deliberately not republished (see the post's method section).

Fills are emitted as var(--token) rather than hex: the SVG is inline in the
page, so it inherits the theme and renders correctly in both light and dark.
Standard library only.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST = ROOT / "blog/uk-data-job-salary-transparency-2026/index.html"
DATA = ROOT / "blog/uk-data-job-salary-transparency-2026/data"

DISP = "'Space Grotesk',ui-sans-serif,system-ui,sans-serif"
MONO = "'Space Mono',ui-monospace,monospace"
TEXT, MUTED, FAINT, LINE = "var(--text)", "var(--muted)", "var(--faint)", "var(--line)"
BAR, BAR_HI, ON_BAR = "var(--c2)", "var(--c1)", "var(--on-c)"
NATIONAL = 14.9   # % of all postings stating a salary


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rows(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def chart_transparency() -> str:
    data = sorted(rows("salary-transparency-by-city.csv"),
                  key=lambda r: float(r["pct_stating_salary"]), reverse=True)
    ml, mt, bar_h, gap = 108, 34, 20, 12
    pw, W = 470, 720
    H = mt + len(data) * (bar_h + gap) + 46
    xmax = 25.0
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-labelledby="t1 d1" style="width:100%;height:auto">',
           '<title id="t1">Share of postings stating a salary, by city</title>',
           '<desc id="d1">Sheffield leads on 21.1% and Liverpool on 19.8%, while Belfast is lowest '
           'at 5.8% and London — the largest market with 2,035 postings — states a salary in only '
           '12.7% of adverts. The national average across all 9,559 postings is 14.9%.</desc>']

    # national average reference line
    ax = ml + (NATIONAL / xmax) * pw
    out.append(f'<line x1="{ax:.1f}" y1="{mt - 12}" x2="{ax:.1f}" y2="{H - 40}" '
               f'stroke="{LINE}" stroke-width="1" stroke-dasharray="3 3"/>')
    out.append(f'<text x="{ax:.1f}" y="{mt - 18}" text-anchor="middle" font-family="{MONO}" '
               f'font-size="9.5" fill="{FAINT}">UK average {NATIONAL}%</text>')

    for i, r in enumerate(data):
        pct = float(r["pct_stating_salary"])
        y = mt + i * (bar_h + gap)
        w = max((pct / xmax) * pw, 2)
        colour = BAR_HI if pct >= NATIONAL else BAR
        out.append(f'<text x="{ml - 10}" y="{y + bar_h - 5}" text-anchor="end" font-family="{DISP}" '
                   f'font-size="12.5" font-weight="600" fill="{TEXT}">{esc(r["city"])}</text>')
        out.append(f'<rect x="{ml}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="1.5" fill="{colour}"/>')
        out.append(f'<text x="{ml + w + 8:.1f}" y="{y + bar_h - 5}" font-family="{DISP}" '
                   f'font-size="12" font-weight="600" fill="{TEXT}">{pct}%</text>')
        out.append(f'<text x="{W - 4}" y="{y + bar_h - 5}" text-anchor="end" font-family="{MONO}" '
                   f'font-size="9.5" fill="{FAINT}">n={int(r["postings"]):,}</text>')

    out.append(f'<text x="{ml}" y="{H - 12}" font-family="{MONO}" font-size="9.5" fill="{FAINT}">'
               f'% of postings that state a salary &#183; cities with 100+ postings</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_skills() -> str:
    data = [r for r in rows("skills-and-pay.csv") if r["median_advertised_gbp"]][:9]
    data.sort(key=lambda r: float(r["pct_of_postings"]), reverse=True)
    # 124px of gutter: "Machine learning" is the longest label and was being
    # clipped to "chine learning" at 96
    ml, mt, bar_h, gap = 124, 30, 22, 14
    pw, W = 330, 720
    H = mt + len(data) * (bar_h + gap) + 46
    xmax = 35.0
    med_x = ml + pw + 74
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-labelledby="t2 d2" style="width:100%;height:auto">',
           '<title id="t2">Most-requested tools, and the median salary advertised alongside them</title>',
           '<desc id="d2">Excel is named in 32.1% of postings but carries the lowest median '
           'advertised salary at £51,198. Python appears in 17.3% at £60,500 and machine learning '
           'in 5.5% at £67,500. The most-requested tool pays the least of those measured.</desc>']
    out.append(f'<text x="{med_x}" y="{mt - 12}" font-family="{MONO}" font-size="9.5" '
               f'fill="{FAINT}">median advertised</text>')

    for i, r in enumerate(data):
        pct = float(r["pct_of_postings"])
        med = int(float(r["median_advertised_gbp"]))
        y = mt + i * (bar_h + gap)
        w = max((pct / xmax) * pw, 2)
        out.append(f'<text x="{ml - 10}" y="{y + bar_h - 6}" text-anchor="end" font-family="{DISP}" '
                   f'font-size="12.5" font-weight="600" fill="{TEXT}">{esc(r["skill"])}</text>')
        out.append(f'<rect x="{ml}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="1.5" fill="{BAR_HI}"/>')
        out.append(f'<text x="{ml + w + 8:.1f}" y="{y + bar_h - 6}" font-family="{DISP}" '
                   f'font-size="12" font-weight="600" fill="{TEXT}">{pct}%</text>')
        out.append(f'<text x="{med_x}" y="{y + bar_h - 6}" font-family="{DISP}" font-size="13" '
                   f'font-weight="600" fill="{TEXT}">&#163;{med:,}</text>')
        out.append(f'<text x="{med_x + 74}" y="{y + bar_h - 6}" font-family="{MONO}" font-size="9.5" '
                   f'fill="{FAINT}">n={int(r["postings_with_salary"])}</text>')

    out.append(f'<text x="{ml}" y="{H - 12}" font-family="{MONO}" font-size="9.5" fill="{FAINT}">'
               f'% of all 9,559 postings naming the tool &#183; median of the 1,429 that state pay</text>')
    out.append("</svg>")
    return "\n".join(out)


def inject(html: str, name: str, svg: str) -> str:
    begin, end = f"<!--CHART:{name}:BEGIN-->", f"<!--CHART:{name}:END-->"
    if begin not in html or end not in html:
        raise SystemExit(f"markers for {name} not found in {POST}")
    return html[:html.index(begin) + len(begin)] + "\n" + svg + "\n" + html[html.index(end):]


def main() -> int:
    html = POST.read_text(encoding="utf-8")
    html = inject(html, "transparency", chart_transparency())
    html = inject(html, "skills", chart_skills())
    POST.write_text(html, encoding="utf-8")
    print(f"injected 2 charts into {POST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
