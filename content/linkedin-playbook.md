# LinkedIn playbook — Cheltenham Data

Working notes, not published. Standing brief for writing posts for Szymon
Pecherski / Cheltenham Data in the data + AI niche.

Compiled 12 August 2026.

---

## What this is based on, and what it is not

You asked me to scroll your Chrome and read the feed directly. I could not, and
it is worth being precise about why, because it changes how much you should
trust what follows.

1. This session runs in an ephemeral cloud container. Your Chrome profile and
   your logged-in LinkedIn session are on your machine; nothing here reaches
   them.
2. `linkedin.com` is blocked outright by this environment's egress policy — the
   gateway returns 403 on CONNECT. That is a network policy, not an obstacle to
   route around.
3. The feed is behind an auth wall regardless, so unauthenticated fetching would
   have returned sign-in pages, not posts.

So this is **not** first-hand observation of posts, their engagement counts and
their authors' follower numbers. It is a synthesis of published studies. That
distinction is the difference between "I measured this" and "someone says they
measured this", and given you run a blog that refused to print a $67.4bn figure
it could not trace, you would rightly want it stated.

### Evidence quality, graded honestly

Most of what is written about the LinkedIn algorithm is content marketing
published by companies selling LinkedIn AI tools. They have an obvious incentive
toward impressive round numbers, and they cite each other in circles until an
unsourced claim looks like consensus. Grading what I found:

**Tier 1 — a real, sizeable dataset behind it.**
- Richard van der Blom's *Algorithm Insights 2026*: 1.3M posts, 50k creators.
  The only serious independent longitudinal study of the platform.
- Buffer's engagement study: 52M+ posts cross-platform; a sub-analysis of 72k
  posts from 25k accounts on reply behaviour.
- Socialinsider's organic benchmarks: large agency panel, published quarterly.

**Tier 2 — plausible, direction probably right, exact number unverified.**
Format engagement rates, optimal character counts, the golden-hour window.
Different studies broadly agree on *direction* while disagreeing on magnitude.

**Tier 3 — treat as folklore.** Dwell-time percentages quoted to one decimal
place, "97% detection accuracy", "reach drops of 96% overnight". These appear
with no methodology attached, usually on pages selling a scheduling tool. I have
kept a couple below because the *shape* of the claim is probably true, but do
not build a strategy on the digits.

**Where sources conflict, I say so rather than picking the tidy one.**

---

## How reach actually works now

The single most important structural change, and the one most creators have not
internalised:

**LinkedIn moved from a Relationship Graph to an Interest Graph.** Distribution
is no longer primarily "who follows you". Roughly 31% of the average feed comes
from first-degree connections, ~25% from second and third degree, and ~10% is
suggested content from people the algorithm decided are topically relevant to
the viewer. (Tier 1/2 — van der Blom.)

Three consequences that should drive everything you do:

**1. Follower count is largely decoupled from reach.** An account with 8,000
focused followers can outperform one with 80,000 unfocused ones. Followers are a
*lagging indicator* of past performance, not a moat protecting future reach.

This is the finding that matters most for you, because it means starting small
in a tight niche is not a handicap. It is the intended path.

**2. Topic consistency compounds; range dilutes.** The algorithm builds a topical
fingerprint of your account and matches it to interest clusters. Posting about
data quality, then hiring, then a conference selfie, then AI evals, trains a
blurry fingerprint that matches nobody strongly. Narrow beats broad.

**3. The first 60–90 minutes decide most of it.** Early engagement determines
whether the post is pushed into cold interest-based feeds. Figures quoted range
from "70% of reach determined in 90 minutes" to "the first 60 minutes decide"
(Tier 2 — the precise number varies by source, the mechanism is agreed).

The practical read: post when *your specific audience* is awake and reachable,
and be present to reply for the hour after. A post you fire and forget is a post
you have handicapped.

---

## The macro picture: it got harder

Against the same period last year, van der Blom's data has views down ~50%,
follower growth down ~59%, and reach for active creators down ~60% over two
years. But **engagement per post rose 12–39%**.

LinkedIn is deliberately trading raw reach for engagement quality. Fewer people
see any given post; the ones who do are better matched. Do not benchmark
yourself against screenshots of 2023 impression counts — that number is gone and
is not coming back.

---

## What separates viral from mediocre

Taking the variables you specifically asked about.

### Format

Consistent across Socialinsider and van der Blom — **native document posts
(uploaded PDF carousels) win**, and it is not close:

| Format | Avg engagement rate |
|---|---|
| Native document / carousel | 6.6–7.0% |
| Multi-image | 6.45% |
| Video | 6.0% |
| Text-only | 3.95% |

Text-only posts are declining fastest as a format even though text engagement
grew ~12% YoY in absolute terms — the field around them moved up faster.

Two independent sources agreeing that documents lead, at similar magnitudes, is
about as good as the evidence on this platform gets. **For a data consultant this
is the most actionable single fact in this document**: a 6–10 page PDF carousel
of your own charts is both the highest-performing native format *and* the thing
you can produce more credibly than almost anyone else in your feed.

### External links — the genuinely contested one

The studies disagree sharply, and anyone quoting you a single confident number
is not reading carefully:

- van der Blom (1.3M posts): one external link in the body reduces **median**
  reach by **18.8%**.
- A 900k-post study: **26.5%** penalty vs. no link.
- Forbes / other coverage: up to **60%**.
- One analysis found in-body plain links roughly *at parity* (858 vs 786 median
  impressions) while **attached preview cards** halved reach (414 vs 795).

That last one is the most useful hypothesis on offer, and it reconciles the
others: the penalty may be substantially about the **auto-generated preview
card** — which visually shouts "leaving now" and collapses dwell time — rather
than the URL itself. Studies that don't separate the two would produce exactly
this spread of numbers.

Reported mitigation: a link in the **first comment** costs ~5–10% versus ~40–50%
for in-body. But note LinkedIn now also suppresses comments containing external
links (claimed up to 80%), so the old "link in comments" trick is degrading.

**What I'd actually do:** make the post free-standing and valuable with no link
at all, and put the URL in the first comment *and* edit it into the post body
after the first hour once early distribution is locked. Do not paste a bare URL
that generates a preview card. Track it — with your own analytics you can settle
this for your own audience in ~10 posts, which beats any of these studies for
your purposes.

### Tags and hashtags

Hashtags are close to spent as a distribution mechanism — the Interest Graph
reads your actual text semantically now, so hashtags mostly signal era. Three at
most, or none. They do not hurt much; they just no longer do the job people
think.

**@-mentions of people are a different matter and still work**, because a
mention that earns a reply from the mentioned person delivers real early
engagement from an adjacent audience. But only mention someone with a genuine
reason to respond. Tagging six semi-famous strangers is engagement bait and is
now actively penalised.

### Length and shape

Converging range: **1,300–1,900 characters** (some sources say 900–1,300). Long
enough to be worth a "see more" click, short enough to finish.

The mechanism that matters is **dwell time** — seconds spent on the post — and
the **"see more" click**, which is itself an engagement signal. Quoted figures
like "61+ seconds dwell = 15.6% engagement vs 1.2% for 0–3 seconds" are Tier 3;
ignore the decimals, keep the mechanism, which is real and agreed.

Mobile truncates at roughly **210 characters / 3 lines**. Everything before that
cut is the only text most people will ever see from you.

### Replying to comments

**Tier 1, and the highest-confidence tactic here.** Posts where the author
replies to comments see ~**30% higher engagement** across the post's lifecycle,
and Buffer found this holds for **83% of the 25,000 accounts** studied.

That is a rare thing in this literature: a large sample, a clear effect, and a
consistency figure attached. It is also free. If you take one behavioural change
from this document, take this one.

### The March 2026 Authenticity Update — read this one carefully

LinkedIn now detects and demotes content that reads as machine-drafted and
posted without meaningful human editing. Reported penalties: ~30% less reach and
~55% less engagement for "low-effort AI" content (Tier 2/3 on the digits, Tier 1
on the fact that the update happened and targets this).

The important nuance, repeated across sources: **using an AI tool is not the
trigger. Publishing content with no original insight is the trigger** —
regardless of how it was produced.

This directly constrains how I should write for you, so let me be blunt about
it. If I generate polished, competent, generic posts about "5 ways AI is
transforming data teams", they will underperform *and* they will train your
account's topical fingerprint toward the exact centroid of slop the classifier
is built to find. The posts I write for you need to carry something only you
have: your numbers, your client situations, your refusals. My job is drafting
and structure. The substance has to come from your actual work, which means I
will keep asking you for specifics rather than inventing them.

Also killed by the same update: engagement pods, comment automation, "comment
DATA and I'll send you the guide" mechanics, and polls.

---

## The data/AI niche specifically

Your niche has a structural problem and a structural opportunity.

**The problem:** AI is the single most saturated topic on the platform. Generic
AI commentary is the most-produced content category in existence, and the
authenticity classifier was effectively trained on it. You cannot win by having
opinions about GPT releases. Everyone has those, and theirs are indistinguishable
from yours.

**The opportunity:** almost nobody posting about data and AI does original
measurement. The feed is saturated with *opinion* and starved of *evidence*.
When someone posts an actual number they computed themselves, with a method and
a caveat, it stands out violently against that background — and it is the format
most likely to be screenshotted, quoted and cited, which is what actually drives
reach through the Interest Graph.

You already do this. Your hallucination-rates post computes every figure from a
157-row dataset that ships as a downloadable CSV. Your salary-transparency post
does original aggregation on scraped job data. **This is your unfair advantage
and you are currently not spending it on LinkedIn.**

### The specific play

Every piece of original analysis you do becomes:

1. A **document carousel** (highest-performing format) of 6–10 slides: one
   finding per slide, your charts, big numbers, minimal text.
2. A **text post** stating one counter-intuitive finding, with the method in the
   body and the caveat stated openly.
3. A **"number I refused to publish"** post — the untraceable $67.4bn figure is
   genuinely a better LinkedIn post than the analysis itself, because it is a
   story about integrity in a feed full of people repeating unsourced stats.
   That post writes itself and nobody else in your niche will write it.

Note that (3) is a *methodology* post, not a data post, and those travel further
because they are legible to non-specialists.

### Positioning

You are a Cheltenham/Gloucestershire freelance data analyst serving small
brands — dashboards, reporting, automation. That is a much better LinkedIn
position than "AI thought leader", for two reasons:

- **The Interest Graph rewards a narrow fingerprint.** "Practical data work for
  small UK businesses" is a cluster you can own. "AI" is not.
- Your buyers are not other data people. A post that makes a data scientist nod
  is often the wrong post. A post where a Gloucestershire business owner
  recognises their own spreadsheet problem is the right one.

Write for the buyer, not the peer group. The peer group gives you likes; the
buyer gives you work. If you have to choose, resist optimising for your own
professional community's approval — it is the most common way technical
consultants build an audience that will never hire them.

---

## Post shapes that work

**The measurement.** "I measured X. Here's what I found." Original number, one
chart, method in two lines, one honest caveat. Your highest-differentiation
format.

**The refusal.** "Everyone quotes this stat. I tried to trace it. I couldn't."
Integrity content. Very high share rate.

**The specific client story.** Anonymised, concrete, with a number. "A shop in
Cheltenham was spending 6 hours a week rebuilding the same report by hand."
Small and true beats big and vague.

**The correction.** "I was wrong about X." Almost unbeatable engagement, and
almost nobody does it because it costs ego. Only when actually true.

**The teardown.** Take a common practice in small-business reporting and show
why it produces wrong answers, with an example.

Avoid: prediction posts, "X is dead" posts, tool round-ups, anything that
could have been written by someone who has never done the work.

### Hook rules

The first ~210 characters are the whole game.

- Lead with the finding or the number, never with throat-clearing.
- No "I'm excited to share", no "Let's talk about", no rhetorical question
  opener, no one-word-per-line ladder.
- Specific beats dramatic. "Four of the six dashboards I audited last month were
  double-counting refunds" outperforms "Most dashboards are lying to you" —
  because the first one is evidently from someone who was there.

---

## Cadence and measurement

- **2–3 posts a week**, consistently, beats daily bursts followed by silence.
  Frequency matters less than topical consistency.
- **Be available for 60–90 minutes after posting.** This is a scheduling
  constraint, not an optional extra — it is the window that decides reach.
- **Reply to every comment**, with a substantive sentence, not "Thanks!". This
  is the Tier 1 tactic.
- **Comment thoughtfully on other people's posts** in your cluster. Under the
  Interest Graph this trains your topical fingerprint and puts you in front of
  adjacent audiences without needing your own reach.

**Track these, not likes:** impressions, "see more" click-through where visible,
comments (weighted far above likes), saves, shares, profile views in the 48h
after a post, and enquiries. Likes are the least informative number LinkedIn
shows you.

Log every post in a sheet with format, whether it had a link, where the link
was, post time, and the above metrics. **After ~20 posts you will have better
data about your own audience than any study cited here** — all of which are
averages across wildly different niches, and none of which are about
Gloucestershire small businesses. That dataset is also, itself, a future post.

---

## Sources

- [Richard van der Blom — The state of LinkedIn in 2026 (1.3M posts)](https://podcasts.apple.com/gb/podcast/richard-van-der-blom-the-state-of-linkedin-in-2026/id1498801064?i=1000770726473) · [site](https://richardvanderblom.com/)
- [Buffer — State of Social Media Engagement 2026 (52M+ posts)](https://buffer.com/resources/state-of-social-media-engagement-2026/)
- [Socialinsider — LinkedIn Organic Benchmarks 2026](https://www.socialinsider.io/social-media-benchmarks/linkedin)
- [Forbes — The LinkedIn Link Penalty Cutting Your Reach By 60%](https://www.forbes.com/sites/jodiecook/2026/07/30/the-linkedin-link-penalty-cutting-your-reach-by-60/)
- [Forbes — 5 LinkedIn Content Moves LinkedIn Started Punishing In 2026](https://www.forbes.com/sites/jodiecook/2026/07/23/5-linkedin-content-moves-linkedin-started-punishing-in-2026/)
- [900k-post link penalty study](https://www.tryordinal.com/blog/linkedin-link-penalty-study)
- [Melanie Goodman — LinkedIn Algorithm 2026: why reach dropped](https://melaniegoodmanlinkedinconsultant.substack.com/p/linkedin-algorithm-2026-reach-topic-authority)
- [Social Media Today — document posts see more engagement](https://www.socialmediatoday.com/news/report-shows-document-posts-on-linkedin-see-more-engagement/816551/)
- [The State of Brand — follower count stopped driving reach](https://www.thestateofbrand.com/news/follower-count-stopped-driving-linkedin-reach)

Tier 3 claims noted above came from tool-vendor blogs (zoomsphere, linkboost,
viralbrain, connectsafely, meet-lea and similar) and are flagged as such in the
text rather than linked as authorities.
