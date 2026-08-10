# The pitch: contribution margin per variant

For young founder-led DTC brands. Use this on the 15-minute call.

## The one-liner

> Shopify tells you what you sold. It doesn't tell you what you *earned* — and
> for a clothing brand the gap between those two numbers usually hides inside
> one or two sizes that come back too often to pay for themselves.

## Why this lands

A founder running a small clothing brand is making reorder and ad-spend
decisions off two numbers: revenue and ROAS. Both are gross. Neither nets off
returns, outbound and return postage, payment fees, pick and pack, or the
stock that comes back unsellable.

The result is a specific, expensive mistake: they scale the product that looks
best on the Shopify product report, when the product report averages every
size together. A hoodie is not one product. It is six, and they do not earn
the same.

## The worked example — use this, it does the persuading

Same £45 hoodie. Same COGS of £14. Same £12 blended CAC. Per 100 orders.

| | High-return size | Low-return size |
|---|---|---|
| Return rate | 22% | 8% |
| Net revenue after refunds | £3,510 | £4,140 |
| COGS + unsellable returns | £1,138 | £1,305 |
| Outbound + return postage | £497 | £448 |
| Pick, pack, restock | £176 | £160 |
| Payment fees | £88 | £88 |
| Ad spend | £1,200 | £1,200 |
| **Contribution** | **£411** | **£940** |
| **Per order** | **£4.11** | **£9.40** |

Assumptions, so anyone can check it: £45 price, £14 landed COGS, £4.20 outbound
postage, £3.50 return postage, £1.50 pick and pack, £1.20 restock, 1.5% + 20p
payment fees charged on all 100 orders and not refunded, 15% of returned units
unsellable, £12 blended CAC.

The punchline: blended together these average £6.75 an order, which looks
perfectly healthy. The healthy average is what stops anyone looking. One
variant is earning 2.3x the other, and the reporting cannot show it.

Ask them on the call: *"Do you know your return rate by size?"* Almost nobody
does. That question is the whole pitch — it opens the gap for them rather than
you asserting it.

## What I actually build

A contribution model, per SKU and per variant, from data they already have:

1. **Pull** — Shopify order export, returns/refunds, supplier invoices for true
   landed COGS, courier invoices, payment processor fees, ad spend by channel.
2. **Join** — one row per order line, every real cost allocated against it.
   Returns matched back to the original order, not counted as separate events.
3. **Surface** — contribution per variant, return rate per variant, blended vs
   channel CAC, and the dead stock report: units held, weeks of cover, cash tied up.
4. **Hand over** — they own it, it refreshes from a fresh export, and the SOP
   is in plain English so it survives without me.

Typical build: a few days. Output is one dashboard and one decision list —
which variants to reorder, which to discontinue, which to stop advertising.

## Credibility — real numbers, already delivered

- Optimised supplier terms across 1,200 codes at a national foodservice
  wholesaler: **£42,500** of margin found, checked against the group P&L.
- Automated twenty manual procedures out of existence at another: **100+ hours
  a year** returned.
- Built SQL and Crystal Reports reporting giving managers **20%** more accurate
  insight into their teams.

Same skill, smaller scale: find where the money is actually going, put a number
on it, build the fix.

## The offer

First project free, in exchange for an honest review and permission to write it
up as a case study. If it turns out there's nothing worth building, say so on
the call and don't take the project — that honesty is the thing that makes the
free offer credible rather than suspicious.

## Handling the two objections

**"We're too small for this."** Small is exactly when it matters — a brand doing
£200k with 20% of orders going out at £4 contribution instead of £9 is leaving
five figures on the table, and it costs nothing to find out which orders those
are.

**"My accountant does this."** An accountant tells you the business made money
last quarter. This tells you which size in which colourway to reorder on
Thursday. Different question, different tool.
