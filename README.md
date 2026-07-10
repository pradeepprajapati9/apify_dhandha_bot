# apify_dhandha_bot

Building paid Actors on the Apify Store. **This repo is Step 1.**

## The idea

[apify.com](https://apify.com/store) is a marketplace for scrapers. People arrive
with a job to do — *"I need the name and phone number of 5,000 restaurants in Delhi"* —
they search, find a ready-made tool (an **Actor**), click run, and get their data.

Someone built that Actor. When a buyer runs it, they pay Apify.
**Apify pays 80% of that to the Actor's author** and keeps 20%.
Typical rates are $1–$10 per 1,000 rows.

**Why this is different:** on YouTube you have to build subscribers first. On a blog,
traffic first. Here, the **buyer already exists and is already willing to pay**.
You don't recruit anyone or convince anyone. Your tool just has to **be found**
when they search.

## So what's the catch

There are already **38,000+ Actors** in the store. If you build a "Google Maps Scraper",
there's one sitting there with **500,000 users**. Nobody will ever open yours.

This is a winner-take-most market — most Actors earn nothing.

**That's why the first job is not to build an Actor. The first job is to find the gap.**

## What this repo does

`store_scanner.py` pulls the whole store and tells you **where the gaps are**.

It runs in **two steps**, and the second one is the one that matters:

**Step 1 — find candidates.** Guess a niche from each of 30,000+ Actor titles
(`Taobao SKU Scraper` → `taobao`). This is **only a guess**.

**Step 2 — verify against Apify's own search.** Feed each top candidate into the
`search=` API and look at **what the buyer actually sees**. Grading happens here,
not in step 1.

Why? Because the step-1 guess **lies**. Real examples from a live run:

| niche | what clustering claimed | what search showed | result |
|---|---|---|---|
| `xiaohongshu` | top actor has 198 users | **1,461 users** | A+ → B |
| `reddit reply` | top actor has 392 users | **1,138 users** | A+ → C |
| `douyin` | — | **1,665 users** | B |

After verification, each niche is judged on three questions:

| Question | How it's measured |
|---|---|
| **Is there demand?** | 30-day users across the search's top 10 |
| **Is the incumbent weak?** | the #1 actor in search has < 500 total users |
| **Are people paying?** | `PAY_PER_EVENT` pricing |

All three yes = `A+`. Incumbent is big but broken / badly rated = `B` (a replacement opportunity).

## Usage

```bash
pip install -r requirements.txt

python store_scanner.py            # use cache (accepts data up to 24h old)
python store_scanner.py --fresh    # re-pull the store
```

Outputs: `gaps.txt` (ranked list) and `dashboard.html` (just open it).

### The command that matters most

```bash
python store_scanner.py --check "taobao"
```

This shows you **exactly what a real buyer sees** when they search that term.

## Do not trust the scanner blindly

The scanner produces a **shortlist, not a decision.**

If a niche's leader has only 200 users, there are **two** possible reasons:

- **(a)** the gap is real — an opportunity, **or**
- **(b)** nobody wants that data — which is why nobody came

**The scanner cannot tell these apart.** So before building anything, run `--check`
on the top 3 niches, open the leader's page, and read its reviews.

## Two honest caveats

1. **This is a business, not passive income.** The sites you scrape will change their
   HTML and your Actor will break. Apify auto-tests every Actor daily —
   **3 consecutive failures and you get demoted in the store.** Maintenance is forever yours.

2. **Stay away from personal data.** Apify's terms state plainly that legal responsibility
   for a community Actor is **100% the developer's**. `rules.py` grades a niche `F` when
   its target is a *person* (LinkedIn, email harvesting, people-search).
   *Business* data — a shop's phone number from Google Maps — is a different thing,
   and it's allowed.

## Known limits of the scanner

- Apify's API **returns nothing past `offset=16000`**, even though the store holds 38k+
  Actors. So we pull category by category (23 categories) and dedupe by `id`.
  Whatever still gets cut is **printed at runtime** — never silently dropped.
  (Currently only the ~4,600 least-popular AUTOMATION Actors are missed.)
- Only the **top 60 candidates** get search-verified (`VERIFY_TOP`). Nothing unverified
  reaches `gaps.txt`, because unverified numbers are wrong numbers.
- Candidate *names* are still sometimes nonsense (`google 15`, `redirect audit`) because
  they're guessed from titles. Their *numbers* are still correct — those come from search —
  the label just reads oddly.

## Roadmap

1. ✅ Scanner — find the gap *(this repo)*
2. ⬜ Build an Actor for that gap, publish to Apify (no approval gate, live instantly)
3. ⬜ Daily health check — catch a broken Actor before Apify does
4. ⬜ A portfolio of 3–5 Actors (power law: one will work, four won't)

**Money, honestly:** roughly ₹0 for the first 2–3 months. First dollar realistically at
2–4 months. If a niche lands, $100–400/month. Apify's top creators clear $10k+/month —
that's the top 1%, **not a baseline**.
