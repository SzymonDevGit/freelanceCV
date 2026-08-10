#!/usr/bin/env python3
"""
Clean the LinkedIn job scrape behind /blog/uk-data-job-salary-transparency-2026/.

Needs pandas and openpyxl. The raw scrape is not committed: the published
aggregates in that post's data/ directory are the redistributable output.

Original docstring:
Clean the LinkedIn job scrape and write a tidy dataset plus a cleaning report.

Every step prints what it changed, because the removals are part of the story:
a summary that says "9,559 postings" without saying what was dropped is not
auditable.
"""
import json
import re
import pandas as pd

SRC = "data.xlsx"        # the raw scrape, kept out of the repo (see .gitignore)
OUT = "."                # writes clean.pkl + clean_report.json alongside

report = {}


def log(step, **kw):
    report[step] = kw
    print(f"  {step}: " + ", ".join(f"{k}={v}" for k, v in kw.items()))


print("Loading ...")
frames = []
for sheet, group in [("Analyst", "Analyst"), ("Non-Analyst", "Non-analyst")]:
    df = pd.read_excel(SRC, sheet_name=sheet)
    df["role_group"] = group
    frames.append(df)
raw = pd.concat(frames, ignore_index=True)
raw = raw.drop(columns=[c for c in raw.columns if c.startswith("Unnamed")])
log("loaded", rows=len(raw), analyst=int((raw.role_group == "Analyst").sum()),
    non_analyst=int((raw.role_group == "Non-analyst").sum()))

df = raw.copy()

# ---------------------------------------------------------------- text tidy --
for col in ["title", "company", "location", "salary"]:
    df[col] = (df[col].astype(str)
               .str.replace(r"\s+", " ", regex=True)     # collapse whitespace
               .str.strip())
# a handful of titles carry a trailing requisition number: "... - 35714"
df["title_clean"] = df.title.str.replace(r"\s*[-–—]\s*\d{4,}$", "", regex=True).str.strip()
log("whitespace_and_reqno", titles_shortened=int((df.title_clean != df.title).sum()))

# ------------------------------------------------------------- duplicates --
before = len(df)
df = df.drop_duplicates(subset="job_id", keep="first")
log("dedupe_job_id", removed=before - len(df))

before = len(df)
df = df.drop_duplicates(subset="url", keep="first")
log("dedupe_url", removed=before - len(df))

# The same vacancy reposted under a new id: identical title, company and
# location. Genuinely distinct openings at one employer do exist, so this is
# reported separately rather than folded into the headline count.
dup_mask = df.duplicated(subset=["title_clean", "company", "location"], keep="first")
log("repostings_same_title_company_location", found=int(dup_mask.sum()))
df["is_repost"] = dup_mask

# ---------------------------------------------------------------- salary --
# Every salary string is a range: "£40,000.00/yr - £45,000.00/yr".
SAL = re.compile(
    r"(?P<cur>[£$€])\s*(?P<lo>[\d,]+(?:\.\d+)?)\s*/\s*(?P<unit>\w+)"
    r"\s*-\s*[£$€]\s*(?P<hi>[\d,]+(?:\.\d+)?)", re.I)
# hours a year at 37.5/wk, and working days a year — used only to put hourly
# and day rates on the same axis as annual ones, and flagged in the output.
HOURS_YEAR, DAYS_YEAR = 1950, 240
PERIOD = {"yr": 1.0, "hr": HOURS_YEAR, "daily": DAYS_YEAR, "day": DAYS_YEAR, "mo": 12.0}


def parse_salary(s):
    m = SAL.search(s or "")
    if not m:
        return pd.Series([None, None, None, None])
    lo = float(m.group("lo").replace(",", ""))
    hi = float(m.group("hi").replace(",", ""))
    unit = m.group("unit").lower()
    mult = PERIOD.get(unit)
    if mult is None:
        return pd.Series([None, None, None, m.group("cur")])
    return pd.Series([lo * mult, hi * mult, unit, m.group("cur")])


df[["sal_lo", "sal_hi", "sal_unit", "sal_cur"]] = df.salary.apply(parse_salary)
has_sal = df.sal_lo.notna()
log("salary_parsed", with_salary=int(has_sal.sum()),
    without=int((~has_sal).sum()),
    pct_with=round(has_sal.mean() * 100, 1))
log("salary_units", **df.loc[has_sal, "sal_unit"].value_counts().to_dict())
log("salary_currency", **df.loc[has_sal, "sal_cur"].value_counts().to_dict())

# Non-sterling postings are a rounding error and not comparable, so they are
# excluded from money figures (but kept in the posting counts).
df["gbp"] = has_sal & (df.sal_cur == "£")

# Implausible annualised values: below the 2026 NMW full-time floor or above
# £400k. These are almost always a unit the scrape mislabelled.
FLOOR, CEIL = 12_000, 400_000
bad = df.gbp & ((df.sal_lo < FLOOR) | (df.sal_hi > CEIL) | (df.sal_hi < df.sal_lo))
log("salary_implausible_excluded", n=int(bad.sum()))
df.loc[bad, "gbp"] = False

df["sal_mid"] = None
df.loc[df.gbp, "sal_mid"] = (df.loc[df.gbp, "sal_lo"] + df.loc[df.gbp, "sal_hi"]) / 2
df["range_width"] = None
df.loc[df.gbp, "range_width"] = df.loc[df.gbp, "sal_hi"] - df.loc[df.gbp, "sal_lo"]

# -------------------------------------------------------------- location --
def norm_location(s):
    s = (s or "").strip()
    parts = [p.strip() for p in s.split(",")]
    city = parts[0] if parts else s
    city = re.sub(r"\s+Area$", "", city, flags=re.I)          # "London Area" -> "London"
    city = re.sub(r"\s+(Metropolitan|Greater)\s+", " ", city, flags=re.I).strip()
    return city


df["city"] = df.location.apply(norm_location)
# country-or-region-only values are not a city
REGIONS = {"United Kingdom", "England", "Scotland", "Wales", "Northern Ireland",
           "Great Britain", "UK"}
df.loc[df.city.isin(REGIONS), "city"] = "Not specified"
log("location_normalised", unique_before=int(df.location.nunique()),
    unique_after=int(df.city.nunique()))

# ------------------------------------------------------------- seniority --
def seniority(t):
    t = " " + (t or "").lower() + " "
    if re.search(r"\b(head of|director|vp|chief|cto|cdo)\b", t):        return "Head / Director"
    if re.search(r"\b(principal|lead|manager|management)\b", t):        return "Lead / Manager"
    if re.search(r"\b(senior|snr|sr)\b", t):                            return "Senior"
    if re.search(r"\b(junior|jnr|graduate|trainee|intern|apprentice|entry)\b", t):
        return "Junior / Graduate"
    return "Mid / Unspecified"


df["seniority"] = df.title_clean.apply(seniority)
log("seniority", **df.seniority.value_counts().to_dict())

# ------------------------------------------------------- description text --
# Descriptions arrive as raw HTML. Matching against that miscounts: "R&amp;D
# tax credit" was being read as the R language, and tags can split a phrase
# like "Power BI" in two. Strip the markup and unescape entities once, then
# do every text match against the result.
import html as _html
plain = (df.description.astype(str)
         .str.replace(r"<[^>]+>", " ", regex=True)
         .map(_html.unescape)
         .str.replace(r"\s+", " ", regex=True))
df["desc_text"] = plain
log("description_html_stripped", median_chars_before=int(df.description.str.len().median()),
    median_chars_after=int(plain.str.len().median()))

# ------------------------------------------------------------ work model --
# LinkedIn puts this in the description far more reliably than in the location.
desc = plain.str.lower()
df["is_remote"] = desc.str.contains(r"\b(?:fully remote|100% remote|remote[- ]first|work from home)\b", regex=True)
df["is_hybrid"] = desc.str.contains(r"\bhybrid\b", regex=True)
df["work_model"] = "Not stated"
df.loc[df.is_remote, "work_model"] = "Remote"
df.loc[df.is_hybrid, "work_model"] = "Hybrid"          # hybrid wins if both appear
log("work_model", **df.work_model.value_counts().to_dict())

# ---------------------------------------------------------------- skills --
SKILLS = {
    "SQL": r"\bsql\b", "Excel": r"\bexcel\b", "Python": r"\bpython\b",
    "Power BI": r"\bpower\s?bi\b", "Tableau": r"\btableau\b",
    "AWS": r"\baws\b|\bamazon web services\b", "Azure": r"\bazure\b",
    "Snowflake": r"\bsnowflake\b", "Databricks": r"\bdatabricks\b",
    "dbt": r"\bdbt\b", "Spark": r"\bspark\b", "Qlik": r"\bqlik\b",
    "Alteryx": r"\balteryx\b", "SAS": r"\bsas\b", "SPSS": r"\bspss\b",
    "Looker": r"\blooker\b", "VBA": r"\bvba\b", "Salesforce": r"\bsalesforce\b",
    "R": r"(?<![\w.&])R(?![\w.&])",   # case-sensitive; & guards exclude "R&D"
    "Machine learning": r"\bmachine learning\b",
    "Google Analytics": r"\bgoogle analytics\b",
}
raw_desc = plain
for name, pat in SKILLS.items():
    series = raw_desc if name == "R" else desc
    df["skill_" + name] = series.str.contains(pat, regex=True)
log("skills_extracted", n=len(SKILLS))

df.to_parquet(f"{OUT}/clean.parquet") if False else None
df.drop(columns=["description","desc_text"]).to_csv(f"{OUT}/clean_no_desc.csv", index=False)
df.to_pickle(f"{OUT}/clean.pkl")
json.dump(report, open(f"{OUT}/clean_report.json", "w"), indent=2, default=str)
print(f"\nFinal dataset: {len(df):,} postings, {df.gbp.sum():,} with a usable GBP salary")
