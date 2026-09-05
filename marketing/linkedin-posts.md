# LinkedIn posts — Pradeep Prajapati

Voice: a full-stack developer sharing a real, shipped, live product. Professional,
honest, no hype. Each post stands alone and takes a different angle, so scheduling
them a few days apart never looks repetitive.

Tool link (put it at the END of the post, or in the first comment — either is fine
for a profile this size):
https://apify.com/dhandhabot_9953/eventbrite-events-scraper

Schedule: LinkedIn's own scheduler (the clock icon under the post box). One post
every 3–4 days. Do NOT post two on the same day.

---

## POST 1 — The launch (post this first)

I shipped a small product this month, and I wanted to share it.

It's an Eventbrite Events Scraper — you give it a city or a search link, and it
returns clean, structured event data: names, dates, venue addresses with
coordinates, organizer IDs, ticket links and category tags. As JSON, CSV or Excel,
or straight from an API.

It runs fully hosted in the cloud, so there's nothing to install. It's live now
and anyone can try it on a free tier.

I built it end to end — the scraping engine, the input/output design, automated
tests, and a daily health check that catches breakage before users do.

If your work touches event data — market research, lead lists, competitive
tracking, building an events aggregator — this might save you some time.

Link below. Happy to answer anything about how it works.

#Python #WebScraping #SoftwareDevelopment #API #BuildInPublic

---

## POST 2 — The technical insight (shows skill)

A thing I learned building my Eventbrite scraper that's worth sharing:

You often don't need a headless browser to scrape a modern React site.

Most people reach for Selenium or Playwright — spin up a browser, wait for React
to render, then fight the DOM. Slow, heavy, and it needs proxies at scale.

But a lot of sites server-render their full data as JSON right into the page HTML,
in a script tag. Eventbrite does this. One plain HTTP request gives you the entire
event list — already structured — before any JavaScript runs.

No browser. No proxy. About a second per page instead of four.

The lesson: always read the raw page source before you automate a browser. The
data is often already sitting there.

I turned this into a live, hosted tool — link in the comments.

#Python #WebScraping #SoftwareEngineering #Backend

---

## POST 3 — Engineering discipline (great for recruiters)

Shipping a product taught me more about testing than any tutorial did.

After my Eventbrite scraper went live and started charging real users, I ran a
proper end-to-end audit of my own code. It found five real bugs I'd have never
caught by "it works on my machine":

→ A daily platform health-check would have failed on empty input and gotten the
  product delisted in 3 days.
→ Overlapping inputs billed a user twice for the same row.
→ A single rate-limit error killed an entire run instead of retrying.

None of these showed up in normal use. All of them would have cost real money or
real reputation.

What fixed it: writing tests that reproduce the exact failure, gating deploys on
those tests, and a health check that runs the *live* product every day — not just
the code in isolation.

Boring engineering is what keeps a live product alive.

#SoftwareEngineering #Testing #Python #BuildInPublic

---

## POST 4 — The "who is this for" angle (business value)

Who actually needs event data?

I built an Eventbrite scraper, and the interesting part was thinking about who it
helps:

• Event marketers tracking what competitors are running in a city
• Sales teams building lists of organizers and venues
• Researchers studying event trends, pricing, or attendance patterns
• Developers building an events aggregator or a "what's happening near me" app

They all need the same thing: clean, structured event data they can filter, sort
and export — without copy-pasting from a website for hours.

That's the whole product. Give it a city, get a spreadsheet (or an API response).
It's live and free to try.

Link in the comments.

#DataAnalytics #EventMarketing #Automation #NoCode

---

## POST 5 — Product thinking (shows you think, not just code)

Before I wrote a single line of my scraper, I wrote a tool to tell me what NOT to
build.

The marketplace I published on has 38,000+ tools. Building a random one is a
guaranteed way to get zero users — you'll just rebuild something that already has
half a million.

So I wrote a scanner that pulls the whole store and scores each niche on three
signals: is there real demand, is the current leader weak, and are people actually
paying there. Only then did I pick what to build.

The build was the easy part. Choosing correctly was the hard part.

Engineers love jumping straight to code. The best thing I did on this project was
resist that for a day.

#ProductDevelopment #SoftwareDevelopment #Startups #Python

---

## POST 6 — Honest reflection (relatable, human)

An honest update on the small product I launched.

The engineering is done — it's live, it's tested, it runs itself every day, and it
charges correctly. Technically, everything works.

Users so far: basically zero. 😅

And that's the real lesson. Building the thing was the part I knew how to do. Getting
it in front of the people who need it — that's the actual hard work, and it's just
beginning.

Marketplaces don't hand you customers. The first ones are always manual: showing up,
writing, answering questions, being useful.

So this post is part of that. If you or someone you know works with event data, my
Eventbrite scraper is live and free to try — link below. And if you've shipped
something and hit this same wall, I'd genuinely like to hear how you got your first
users.

#BuildInPublic #SoftwareDevelopment #Startups #IndieHacker
