# LinkedIn posts — batch 01

Drafts built from published Cheltenham Data analysis. Every figure below is
taken from your own posts — nothing invented. Check each one before posting
anyway.

Target length 1,300–1,900 characters. Counts noted per post.

---

## 1. The refusal — "the number I wouldn't publish"

*Highest-differentiation post here. It is about method, not data, so it is
legible to non-specialists and travels further than the analysis itself.*

> I spent an afternoon trying to trace a statistic, and then deleted it from my
> article.
>
> The figure was "$67.4 billion in losses from AI hallucinations". It is
> everywhere. It gets quoted in decks, in newsletters, in other people's blog
> posts. I wanted to use it too, because it is a great number — big, precise,
> alarming.
>
> Precise numbers are supposed to have a source. So I went looking for it.
>
> I couldn't find one. Every citation pointed at another article, which pointed
> at another article. Nobody I could reach was pointing at a study, a
> methodology, or a dataset. The trail just ran out.
>
> That decimal place is doing a lot of work. ".4" tells you someone measured
> something carefully. If nobody can show me what was measured, it isn't a
> measurement — it's a number wearing the costume of one.
>
> So the article says that instead. It names the figure, says I couldn't trace
> it, and moves on to numbers I computed myself from a dataset I published
> alongside it.
>
> This is not a purity thing. It's a practical one. If I'll repeat an
> impressive-sounding number I haven't checked, you have no way of knowing which
> of my other numbers I checked. The whole document becomes untrustworthy,
> including the parts that are fine.
>
> The unglamorous version of data work is mostly this. Not modelling. Not AI.
> Just refusing to pass things along that you haven't verified.
>
> Anyone else got a stat they've quietly stopped quoting?

**1,414 characters.** Ends on a genuine question people can answer from
experience, which is the kind of comment prompt that isn't engagement bait.

---

## 2. The measurement — hallucination rates

> Everyone assumes AI models get more reliable with each release.
>
> I checked. On one benchmark, the average got worse.
>
> I pulled two snapshots of Vectara's hallucination leaderboard — 52 models from
> 2024, 105 from 2026 — and compared them.
>
> Mean hallucination rate: 6.25% → 10.24%
> Median: 5.10% → 9.60%
> Models scoring under 5%: 44% of them → 9%
> Models hallucinating on 10%+ of summaries: 10% → 47%
>
> Something else changed too, and I think it's the more useful finding. In 2026,
> longer summaries hallucinate more — 13.0% at 125+ words against 8.1% under 75
> words. In 2024 that relationship did not exist at all (rank correlation +0.02,
> now +0.42).
>
> So the failure mode moved. Length didn't used to predict unreliability. Now it
> does.
>
> The caveat matters as much as the numbers, so here it is plainly: this
> benchmark measures one narrow thing — given a document and an instruction to
> summarise using only that document, how often does the model add something the
> document doesn't support. It is summarisation faithfulness, not general
> factual accuracy. The judge is itself a model, with its own error rate. And
> the 2026 field is twice the size, with more small and experimental models in
> it, which will drag an average around.
>
> It is a yardstick, not a verdict.
>
> But if you are putting a model between your source documents and your
> customers, "newer is safer" is not an assumption the data supports — and asking
> for shorter outputs may do more for reliability than upgrading the model.

**1,482 characters.** Note the caveat block is load-bearing: it is the part that
makes a stranger trust the numbers above it.

---

## 3. The buyer-facing one — salary transparency

*Aimed at business owners and hiring managers, not data peers. Widest reach of
the three.*

> 85% of UK data job ads don't tell you the salary.
>
> I scraped 9,559 live UK postings across 3,891 employers and counted. Only
> 1,429 of them — 14.9% — state a figure.
>
> The pattern inside that is more interesting than the headline.
>
> Remote roles are more than twice as likely to tell you as roles that say
> nothing about working pattern: 24.9% against 12.0%. London is the biggest
> market in the country and one of the least forthcoming, disclosing in 12.7% of
> adverts. Sheffield manages 21.1%.
>
> And my favourite detail: of the employers who do publish a "range", 7.8% list
> the same number twice. £45,000 to £45,000. That is not a range. That is a
> number in a costume.
>
> What this measures, precisely: what employers publish on one platform. Not
> what they pay. If a company withholds the salary in the advert and tells you at
> first interview, I've counted that as withholding — because at the point where
> you're deciding whether to spend an evening on an application, it is.
>
> Every pay figure comes only from the 14.9% who disclose, which is not a random
> sample. Public bodies and organisations with banded pay publish more readily.
> So the median advertised midpoint of £54,000 is best read as "typical of
> employers willing to publish", not "typical of the market".
>
> If you're hiring and you're not publishing a number, you are filtering your
> applicants on tolerance for wasted time rather than ability.

**1,397 characters.**

---

## 4. Document carousel outline — the hallucination data

Highest-performing native format (6.6–7.0% engagement). Export as PDF, upload
natively. Reuse the charts already generated by `tools/build_charts.py`.

1. **Cover.** "AI hallucination rates went up, not down." Subtitle: 52 models in
   2024 vs 105 in 2026.
2. **The headline.** 6.25% → 10.24% mean. One big number, nothing else.
3. **The collapse.** Models scoring under 5%: 44% → 9%.
4. **The other end.** Models over 10%: 10% → 47%.
5. **The new pattern.** Length vs hallucination scatter, 2024 vs 2026 side by
   side. +0.02 → +0.42.
6. **What this measures.** The caveat slide. Summarisation faithfulness only;
   model-judged; larger 2026 field.
7. **So what.** Shorter outputs may buy more reliability than a newer model.
8. **Close.** "Full analysis and the dataset — link in comments." Name, Cheltenham
   Data.

Keep one idea per slide and set type large. Most people read these on a phone at
thumbnail size.

---

## Posting notes

- Do **not** paste the blog URL into the post body — the preview card is the
  part most likely to halve reach. First comment, then edit into the body after
  an hour if you want it there.
- Post when you can be present for the following 60–90 minutes. That window
  decides most of the distribution.
- Reply substantively to every comment. ~30% lifecycle engagement lift, Tier 1
  evidence, costs nothing.
- Space these out. Two to three posts a week, same topical territory.
- Post 1 (the refusal) is the strongest opener if you are restarting a dormant
  account, because it needs no prior credibility to land.
