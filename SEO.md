# SEO — what was done, what you still need to do

Site: <https://cheltenhamdata.co.uk/> · Last reviewed: 2 August 2026

---

## ⚠️ Domain move: finish this or you will split your own signals

The canonical domain is now **cheltenhamdata.co.uk**. Every canonical tag,
schema `@id`, sitemap entry, robots directive and tool constant points there.

**But `szymonpecherski.online` still serves the same site on a 200.** Two domains
returning identical content is textbook duplicate content. The canonical tag
tells Google which one to keep, so the damage is contained, but the fix is a
five-minute job you should not leave:

1. Cloudflare → the `szymonpecherski.online` zone → **Rules → Redirect Rules**.
2. Create a rule: *if hostname equals `szymonpecherski.online`* →
   **static/dynamic redirect** to `https://cheltenhamdata.co.uk` + the original
   path, **301 permanent**, preserve query string.
3. Keep that domain registered and redirecting **permanently**. It costs a few
   pounds a year and it is what carries any existing links and typed traffic.
4. In Search Console, add a property for the old domain (if not already there),
   then use **Settings → Change of Address** to declare the move.

Two other Cloudflare settings still outstanding on the new zone:

- **SSL/TLS → Edge Certificates → Always Use HTTPS → On.** `http://` currently
  serves a 200 instead of redirecting.
- **www:** `www.cheltenhamdata.co.uk` does not resolve. Add a proxied CNAME to
  the apex plus a 301, so typed and linked www URLs don't die.

Verify all of it with `python tools/seo_audit.py --live`.

---

## The blog

`/blog/` now exists, with the first post at
`/blog/ai-hallucination-rates-2024-vs-2026/`. This is the single biggest
structural SEO gain available to the site: it turns a one-page brochure into
something with topical depth, real internal linking and a reason for other
people to link to you.

What makes that post worth having, in SEO terms:

- **Original analysis, not a stat round-up.** Every figure is computed from a
  157-row dataset that ships alongside the post as a downloadable CSV, with
  `Dataset` + `DataDownload` schema. Original data is the format most likely to
  earn citations and links, from both people and AI assistants.
- **An answer-first summary block** under the H1, which is the shape generative
  systems lift most readily.
- **Method and caveats stated openly** — what the benchmark does and does not
  measure, sample sizes per bucket, and why a rank correlation was used.
- **A number I refused to publish.** The widely-repeated "$67.4bn of losses"
  figure could not be traced to a primary source, so the post says so instead
  of scaling it into a bigger unverifiable number. That refusal is the credible
  move, and it is consistent with what your own AI policy page promises.

Charts are generated from the CSV by `tools/build_charts.py` and injected
between markers, so they cannot drift from the data. Re-run it if the data
changes.

### Adding another post

1. Create `blog/<slug>/index.html` (copy the existing post's `<head>`).
2. Add a row to `PAGES` in `tools/seo_audit.py` and a `<url>` to `sitemap.xml` —
   the audit fails if a known page is missing from the sitemap.
3. Add a card to `blog/index.html` and the `blogPost` array in its schema.
4. `python tools/seo_audit.py --strict`, then push.

---

## The Cheltenham Data brand (5 Aug 2026)

Five outreach emails went out signed *Cheltenham Data* while every surface on
the site still said *Szymon Pecherski* — header, footer, `og:site_name`, page
title. Anyone clicking through landed on a differently-named brand, and Google
Business Profile's name rule wants a name you demonstrably trade under.

The site now leads with **Cheltenham Data** and names the person underneath it,
rather than replacing him. It is a sole trader practice, not a registered
company, so nothing here claims a legal entity that doesn't exist:

- Header and footer carry a two-line lockup — *Cheltenham Data.* over
  *Szymon Pecherski* — and the blog chrome matches.
- `og:site_name` is `Cheltenham Data`; titles read
  *Cheltenham Data | Data Analyst in Cheltenham — Szymon Pecherski*.
- Structured data keeps both entities: the `ProfessionalService` is named
  *Cheltenham Data*, with the `Person` as its `founder` and `provider`, and the
  old person-led naming preserved in `alternateName` so existing signals for it
  aren't stranded. No `legalName` — that would assert a registration.
- Hero copy, the footer notice and a new FAQ entry all state plainly that
  Cheltenham Data is the practice of Szymon Pecherski.
### The one piece still outstanding: a domain email address

The site still publishes `szymonpecherski@gmail.com`, deliberately — a
published address that bounces is worse than a Gmail one that works, and
`szymon@cheltenhamdata.co.uk` does not exist yet. But you have just pitched five
media outlets and a county charity body from a Gmail address, which undercuts
the brand the rest of this section just built.

Fixing it is free and takes about five minutes:

1. `python tools/cloudflare_setup.py --email` to see the plan, then
   `--email --apply` to make it. It enables Cloudflare Email Routing on the zone
   and forwards `szymon@cheltenhamdata.co.uk` to your existing inbox. Forwarding
   only: no mailbox, nothing stored at Cloudflare, replies still come from the
   inbox you already use. `--email` is opt-in because enabling routing adds MX
   records to the zone.
2. Click the verification link Cloudflare emails to the Gmail inbox. **Nothing
   is delivered until you do.**
3. Send yourself a test message and confirm it arrives.
4. Only then switch the site over: the mailto links and visible address in
   `index.html` and `404.html`, the footer link on both blog pages, and the
   three `"email"` fields in the JSON-LD graph. One commit.

Sending *from* the new address is a separate thing — routing forwards inbound
mail but doesn't let Gmail send as it. Add it in Gmail under Settings → Accounts
→ "Send mail as", which needs an SMTP relay; until then, replying from Gmail is
fine and still lands in the right conversation.

---

## The Bench design, and the dark theme (7 Aug 2026)

The site was rebuilt on the design mockup you picked — `design/d-paper/`, the
green pen — and now ships **light and dark**, defaulting to whichever the
visitor's operating system is set to. There is a switch in the header if they
disagree, and that choice is remembered.

### How the theming works, and why it looks like this

Every colour on the site is a custom property. There are two palettes and
nothing else: `:root` is paper, and the dark block overrides the same names.
Dark is deliberately **not** a variable swap — on light stock the materials
have to behave the other way round, so:

* the steel rule down the page edge goes from dark ticks bitten into bright
  metal to light ticks scored into dark metal;
* masking tape darkens the sheet under it on paper and lightens it in the dark;
* shadows warm and shorten in the light, lengthen and cool in the dark;
* the cork board is one image either way, veiled darker at night by a multiply
  layer (`--cork-veil`, which is plain white on light and so multiplies to
  nothing).

The dark palette is applied **twice**, on purpose: once by attribute for the
toggle, once inside `@media (prefers-color-scheme: dark)` for visitors with no
JavaScript. The two blocks are identical and must stay that way — change one,
change the other. A tiny script in `<head>` resolves the theme *before* first
paint, so the page never flashes the wrong one.

The blog, the post and the 404 page were rethemed to match. Leaving them on the
old dark-wood palette would have meant clicking "Notes" dropped you into what
looked like a different company's website.

### Two things worth not re-learning

**The cork tile is baked, not inlined.** `tools/build_assets.py` draws ~1,160
chips into one seamless 300 px tile and writes `cork.webp` (29 KB, cached a
week). It was 45 KB of inline SVG in the mockup, which would have pushed the
HTML over the audit's 120 KB budget for something the browser can cache
separately. Two approaches that look obvious and are not: a lattice of CSS
radial-gradients tiles on a visible grid and reads as polka dots, and
`feTurbulence` — filtered or raw — reads as smooth hardboard while emitting
per-channel colour noise that tints the board into confetti.

**Resting tilts use `rotate:`, not `transform: rotate()`.** Sheets on the page
sit a fraction off true, and the reveal animation moves elements with
`transform`. When both used the same property, every tilt had to be restored by
hand on `.in` — and one of those restore rules silently stopped matching, which
left the whole FAQ invisible. `rotate` and `translate` are independent
properties; the reveal and the tilt no longer touch each other.

### What did not change

The copy, every figure, the whole JSON-LD graph, the canonical, the meta
description and the heading outline are all as they were. The four results
states still ship in the markup rather than being written by script, so every
figure is readable with JavaScript off. The charts in the blog post now emit
`fill="var(--token)"` instead of baked hex, which is what lets one chart render
correctly in both themes.

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
| Key figures | `£0` / `0%` in the markup, real values written only by the scroll counter | Real figures in the HTML (`£42,500`, `30%`, `47.55%`…), animated from there — the strongest sales evidence on the page is now readable with JavaScript off, by crawlers and by any AI system asked about the business |
| 404 page | None | Branded, `noindex`, links home |
| Headers | Defaults | `_headers`: HSTS, nosniff, referrer policy, permissions policy, 1-year immutable font cache |
| Accessibility | No skip link | Skip-to-content link |
| Freshness | None | Visible `<time>` stamp + `dateModified` + sitemap `lastmod`, all kept in sync |
| Theme | Dark only | Light and dark, following the OS by default, with a switch in the header that is remembered. Resolved before first paint; works with JavaScript off via `prefers-color-scheme` |

Live page weight: 92 KB HTML (two full palettes and the whole page's CSS are
inline, so it is one request, not two) + 182 KB of fonts cached for a year +
a 29 KB cork tile. All first-party; still zero third-party requests.

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
   protocol). Submit `https://cheltenhamdata.co.uk/sitemap.xml`. Then
   **immediately turn on the BigQuery bulk export** (Settings → Bulk data
   export): it is not backfilled, so every day you delay is data you never get.
   That's also the cleanest source for the kind of dashboard you build for
   clients.
3. **Bing Webmaster Tools** — <https://www.bing.com/webmasters>. Import from GSC
   in one click. This is what feeds ChatGPT.
4. **Google Business Profile** — <https://business.google.com>. This is the single
   biggest lever for "data analyst Cheltenham" style searches and you don't have
   one. Use **Cheltenham Data** as the name: the name rule requires you actually
   trade under it, and the site and your email signature now say so
   consistently. Service-area business (hide the address), primary category
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
| "Redirect to HTTPS not configured correctly" | **Real.** `http://cheltenhamdata.co.uk/` returns `200 OK` with the full page — no redirect at all | **Cloudflare dashboard** (below) |
| "Uses both www and non-www URLs" | **False positive.** `www.cheltenhamdata.co.uk` is `NXDOMAIN` — no A record, no CNAME. There is no www version to duplicate; the tool flags this whenever it can't observe a www→apex 301, without checking whether www resolves | Worth adding anyway, for dead links |
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
2. **www:** DNS → add CNAME `www` → `cheltenhamdata.co.uk`, proxied. Then add
   `www.cheltenhamdata.co.uk` as a custom domain on the Pages project, and a
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
