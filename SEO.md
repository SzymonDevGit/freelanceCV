# SEO — what was done, what you still need to do

Site: <https://szymonpecherski.online/> · Last reviewed: 2 August 2026

---

## ⚠️ Read this first: the repo and the live site are not in sync

On the live site, `/` serves exactly the HTML that was in `index_2.html`, but
`/index_2.html` returns **404**. So Cloudflare is *not* serving this repo's file
layout — the page was almost certainly uploaded to Cloudflare separately rather
than built from this repository.

**That matters because every new file below (`/fonts/*`, `og-image.png`,
`sitemap.xml`, `robots.txt`, the icons) will 404 unless they get deployed too.**
The page will still render, but with fallback fonts and no social image.

Fix it once, properly:

1. Cloudflare dashboard → **Workers & Pages** → create/select a **Pages** project.
2. **Connect to Git** → `SzymonDevGit/freelanceCV`, branch `main`.
3. Build command: *(none)*. Build output directory: `/`.
4. Custom domains → add `szymonpecherski.online` and `www.szymonpecherski.online`.
5. Push to `main` → Cloudflare deploys automatically.

After that, `git push` is the whole deploy process. (Wrangler CLI is the other
option but it needs Node, which this machine doesn't have — so the Git
integration is the right route.)

---

## What changed

| Area | Before | After |
|---|---|---|
| Entry file | `index_2.html` (root `/` 404s on a normal static host) | `index.html` |
| `robots.txt` | Cloudflare's managed file only, no sitemap | Own file, sitemap declared, AI **retrieval** bots explicitly allowed |
| `sitemap.xml` | **404** | Present, with `lastmod` + image entry |
| `og-image.png` | **404** — every share showed a blank card | Generated 1200×630 brand card |
| Favicons | One inline SVG data URI | `favicon.ico`, `favicon.svg`, `apple-touch-icon`, 192/512 PNGs, web manifest |
| Fonts | 3 render-blocking requests to `fonts.googleapis.com` + `fonts.gstatic.com` | Self-hosted, subsetted, inlined `@font-face`, 2 critical files preloaded. **Zero third-party requests on the whole page** |
| LCP animations | Hero copy hidden until 0.62–0.82 s; headline words staggered to ~0.47 s | 0.16–0.32 s; headline stagger ~0.16 s |
| Headings | `h1 → h3` and `h2 → h4` jumps | Clean `h1 → h2 → h3` outline |
| Structured data | 4 nodes | 6 nodes: added `WebPage`, `AdministrativeArea`, `ContactPoint`, logo, `sameAs`, per-service `@id`s, `hasOccupation`, postal address |
| Meta description | 177 chars (truncated in results) | 150 chars |
| 404 page | None | Branded, `noindex`, links home |
| Headers | Defaults | `_headers`: HSTS, nosniff, referrer policy, permissions policy, 1-year immutable font cache |
| Accessibility | No skip link | Skip-to-content link |
| Freshness | None | Visible `<time>` stamp + `dateModified` + sitemap `lastmod`, all kept in sync |

Live page weight: 78 KB HTML (~15 KB over the wire after Brotli) + 182 KB of
fonts, cached for a year. Seven requests total, all first-party.

---

## The tooling

```bash
python tools/seo_audit.py
```

Fails the build on: broken internal anchors, missing local assets (including
CSS `url()` refs), bad canonical/robots/title/description, invalid JSON-LD or
`@id` references that resolve to nothing, `og:image` missing or not 1200×630,
`img` without `alt`, sitemap/footer/JSON-LD dates drifting apart, a
reintroduced Google Fonts request, and a whole-site `Disallow`. Standard
library only. `--strict` also fails on warnings; `--stamp` re-dates everything
to today first.

```bash
python tools/build_assets.py
```

Downloads and subsets the webfonts, regenerates the OG card, logo and every
icon, then **injects the `@font-face` block straight into `index.html`** between
the `FONTS:BEGIN/END` markers, so the CSS can never drift from the files on
disk. Re-run after any brand change.

```bash
python tools/indexnow.py --dry-run   # then drop --dry-run to submit
```

Pushes URLs to IndexNow → Bing, Yandex, Seznam, Naver. Worth doing because
**ChatGPT's web retrieval runs on Bing's index** — this is the cheapest
AI-visibility lever available. Google ignores IndexNow; for Google it's the
sitemap plus Search Console.

`.github/workflows/seo.yml` runs the audit on every push and PR, then after a
push to `main` waits for the deploy, smoke-tests the live URLs (including that
404s really 404), and pings IndexNow.

---

## What you need to do — 40 minutes, in this order

1. **Deploy the new files** (see the warning at the top). Nothing below works
   until `sitemap.xml` and `og-image.png` return 200.
2. **Google Search Console** — <https://search.google.com/search-console>. Add a
   **Domain property** (DNS TXT record in Cloudflare, covers every subdomain and
   protocol). Submit `https://szymonpecherski.online/sitemap.xml`. Then
   **immediately turn on the BigQuery bulk export** (Settings → Bulk data
   export): it is not backfilled, so every day you delay is data you never get.
   That's also the cleanest source for the kind of dashboard you build for
   clients.
3. **Bing Webmaster Tools** — <https://www.bing.com/webmasters>. Import from GSC
   in one click. This is what feeds ChatGPT.
4. **Google Business Profile** — <https://business.google.com>. This is the single
   biggest lever for "data analyst Cheltenham" style searches and you don't have
   one. Service-area business (hide the address), primary category
   *Business management consultant* or *Software company*, add services, and ask
   your last few clients for reviews. Reviews are roughly a fifth of local pack
   ranking and you currently have zero.
5. **Cloudflare AI crawler settings** — your live `robots.txt` currently blocks
   `GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot`, `Amazonbot`,
   `Applebot-Extended`, `Bytespider` and `meta-externalagent` via Cloudflare's
   managed rules. That blocks **model training**, which is a reasonable choice —
   and it does *not* block the retrieval bots that cite you (`OAI-SearchBot`,
   `ChatGPT-User`, `PerplexityBot`, `Claude-User`), which my `robots.txt`
   explicitly allows. Blocking `Google-Extended` also has **no effect** on Google
   Search or AI Overviews. So the current setup is fine — just know it's a
   deliberate choice, in Cloudflare → AI Crawl Control.
6. **LinkedIn** — make sure your profile headline and About match the site's
   wording ("data analyst and business intelligence specialist, Cheltenham").
   Consistent entity wording across site + LinkedIn + GBP is what makes you
   resolvable to both Google's Knowledge Graph and the AI assistants. LinkedIn
   is also one of the most-cited domains in AI answers for professional queries.

---

## Seobility audit — findings triaged (2 Aug 2026)

Verified each against the live site rather than taking the tool's word for it.

| Finding | Verdict | Action |
|---|---|---|
| "Redirect to HTTPS not configured correctly" | **Real.** `http://szymonpecherski.online/` returns `200 OK` with the full page — no redirect at all | **Cloudflare dashboard** (below) |
| "Uses both www and non-www URLs" | **False positive.** `www.szymonpecherski.online` is `NXDOMAIN` — no A record, no CNAME. There is no www version to duplicate; the tool flags this whenever it can't observe a www→apex 301, without checking whether www resolves | Worth adding anyway, for dead links |
| "Charset missing in HTTP header" | **Real.** `Content-Type: text/html` with no charset | **Fixed** in `_headers` |
| "Some anchor texts used more than once" | **Non-issue.** The six nav anchors appear 3× (header, mobile nav, footer) and every instance points at the *same* target. Duplicate anchor text to an identical destination cannot dilute or confuse anything | None |
| "33 headings… should be more in proportion to text" | **Non-issue.** 2,348 visible words across 36 headings = **65 words per heading**, normal for a sectioned landing page. Removing headings would make it harder to scan and harder for AI systems to extract | None |
| "Few social sharing options" | **Declined.** Share widgets mean third-party JavaScript, which would destroy the zero-third-party-request property and add main-thread work that hurts INP. Nobody shares a freelancer's homepage via a button | None |
| "Only 5 backlinks / 5 referring domains" | **Real, and the biggest remaining constraint.** Not fixable in code | See below |

### The two Cloudflare settings (2 minutes, can't be done from a git push)

These are DNS and zone settings — they live in Cloudflare, not in this repo.

1. **SSL/TLS → Edge Certificates → Always Use HTTPS → On.** This is the entire
   fix for the HTTPS error. Note the HSTS header alone does *not* cover it:
   browsers ignore `Strict-Transport-Security` on plain-HTTP responses (RFC
   6797), so the first request still needs a real 301.
2. **www:** DNS → add CNAME `www` → `szymonpecherski.online`, proxied. Then add
   `www.szymonpecherski.online` as a custom domain on the Pages project, and a
   Redirect Rule `www` → apex, 301.

Do **not** enable HSTS preload while you're in there — it is baked into browsers
and effectively irreversible for months.

Verify both afterwards with:

```bash
python tools/seo_audit.py --live
```

Then delete the `continue-on-error: true` line from `.github/workflows/seo.yml`
so a future regression actually fails the build.

### On the backlinks warning

5 referring domains is the honest bottleneck, and no amount of on-page work
substitutes for it. Cheapest real links, in order: Google Business Profile,
your Companies House listing, Cheltenham/Gloucestershire chamber and business
directories, any client or supplier happy to add a "who built this" credit,
plus your LinkedIn profile and posts. One piece of original data — a survey of
SME reporting habits, say — is worth more than fifty directory submissions.

## Deliberate omissions, and why

- **No `llms.txt`.** Google confirmed in June 2026 it doesn't use them, John
  Mueller compared them to the meta keywords tag, and Ahrefs found ~97% of
  published `llms.txt` files got zero requests. It's cargo cult.
- **FAQ schema kept, but it earns nothing on Google.** Google removed FAQ rich
  results and deleted the documentation in June 2026. It's retained because Bing
  still renders it and it costs nothing — not because it will win you snippets.
- **No "AEO/GEO" restructuring.** Google's own May 2026 guidance is explicit:
  no special files, no content chunking, no special writing style, no required
  schema. Generative features run on the normal ranking systems. Your existing
  clear structure and direct answers are already the right shape.
- **No analytics installed.** That needs your account IDs. Cloudflare Web
  Analytics is the privacy-friendly, cookie-free option and adds no consent
  banner obligation — one script tag from the Cloudflare dashboard.
- **No fabricated markup.** No `aggregateRating`, no reviews, no opening hours,
  no invented languages. Fake review markup is exactly what Google's July 2026
  review-snippet guidance targets, and it's the sort of thing that ends in a
  manual action.

---

## The honest ceiling on a one-page site

The page is now technically about as good as a single page gets. The remaining
constraint is structural: **one page can only be the best result for one topic.**
You're asking it to rank for business intelligence, process automation, AI
workflows, web scraping, and about nine locations at once.

If you want to compete for the money queries — *power bi consultant
gloucestershire*, *process automation consultant uk*, *excel automation
freelancer* — the next step is one substantial page per service, each with its
own case study, pricing shape and FAQ, all linking back to the homepage. Four
pages of real depth, not four thin variants of the same copy (that's Google's
"scaled content abuse" policy and it backfires).

That's a content project needing your input on real client detail, not something
to auto-generate. Until then, expect this page to do well on your name, on
"data analyst cheltenham", and on long-tail automation queries — which for a
freelancer taking limited projects alongside a full-time role may be exactly
enough.

## Measuring it

Give it 4–6 weeks before judging anything. Then, monthly:

- GSC: clicks and impressions split **branded vs non-brand**; queries in
  positions 5–20 (cheapest wins); pages indexed vs submitted.
- GSC → Core Web Vitals: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 at the 75th
  percentile of *field* data. A Lighthouse score is not a Core Web Vital.
- Enquiries, attributed by asking people how they found you. On this volume that
  beats any attribution model.
