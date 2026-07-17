---
title: Scrape Eventbrite events without a headless browser
published: false
tags: python, webscraping, api, datascience
canonical_url:
---

Eventbrite has no free public API for searching events any more. The usual reaction is to reach for Selenium or Playwright, wait 4 seconds per page for React to settle, and then fight the DOM.

You don't need any of that. Eventbrite server-renders the **entire event list as JSON** into every search page. One `requests.get` and you have structured data — names, dates, venue addresses, coordinates, organizer IDs, ticket links, category tags.

Here's the whole thing.

## The trick

Open any Eventbrite search page and look at the HTML source (not the inspector — the actual source). You'll find:

```html
<script>window.__SERVER_DATA__ = { ... a very large JSON object ... };</script>
```

That object contains `search_data.events.results` — the full, already-parsed event records that React is about to render. The browser is just decoration. Skip it:

```python
import json, re, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
SERVER_DATA = re.compile(r"window\.__SERVER_DATA__\s*=\s*(\{.*?\});", re.S)

def eventbrite_events(location, page=1):
    url = f"https://www.eventbrite.com/d/{location}/all-events/"
    if page > 1:
        url += f"?page={page}"
    html = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
    m = SERVER_DATA.search(html)
    if not m:
        raise RuntimeError("__SERVER_DATA__ not found — page structure changed")
    blob = json.loads(m.group(1))["search_data"]["events"]
    return blob["results"], blob["pagination"]

events, pagination = eventbrite_events("india--mumbai")
print(f"{len(events)} events, page {pagination['page_number']} of {pagination['page_count']}")

e = events[0]
print(" name  :", e["name"])
print(" date  :", e["start_date"], e["start_time"])
print(" venue :", (e.get("primary_venue") or {}).get("name"))
```

Output:

```
17 events, page 1 of 5
 name  : ASIASec 2026 | Anti-Counterfeit, Illicit Trade & Brand Protection
 date  : 2026-08-19 09:30
 venue : Radisson Blu Mumbai International Airport
```

No browser, no proxy, no API key. ~1 second.

## Finding the location slug

It's just the URL segment. Browse to your city on Eventbrite and read the address bar:

```
https://www.eventbrite.com/d/india--mumbai/all-events/
                             ^^^^^^^^^^^^^
https://www.eventbrite.com/d/united-states--new-york/music/
                             ^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^
```

The second segment is the category — `all-events`, `music`, `business`, `food-and-drink`, and so on.

## What's in a record

More than you'd expect. The fields worth knowing about:

| Field | Notes |
|---|---|
| `name`, `summary` | title and one-line description |
| `start_date` / `start_time` / `end_date` / `end_time` | plus `timezone` as an IANA name |
| `primary_venue.name` | venue name |
| `primary_venue.address` | `localized_address_display`, `city`, `region`, `country`, **`latitude`/`longitude`** |
| `primary_organizer_id` | stable ID to group events by organizer |
| `tickets_url` | direct checkout link |
| `tags[]` | category tags, with `display_name` |
| `is_online_event`, `is_cancelled` | worth filtering on |

The coordinates are the pleasant surprise — you get a geocoded venue for free, no Places API call.

## The parts that actually bite

The snippet above is the easy 80%. What took me longer:

**1. Pagination lies if you're careless.** `pagination.page_count` tells you when to stop, but if you paste a URL that already has `?page=2` and blindly append `&page=3`, you get `?page=2&page=3` — Eventbrite honours the *first* one, you re-fetch the same page, every ID looks like a duplicate, and your crawler silently concludes it has reached the end. Strip the existing param before setting yours:

```python
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

def page_url(base_url, page):
    parts = urlsplit(base_url)
    q = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() != "page"]
    if page > 1:
        q.append(("page", str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
```

**2. Deduplicate across the whole run, not per search.** Online events show up in *every* city's results. Two nearby cities overlap. If you keep a `seen` set per search instead of per run, you'll emit the same event several times. One set for the entire job.

**3. Datacenter IPs get different treatment.** This code works from my laptop and from a cloud runner I tested — but Eventbrite returns `405 Not Allowed` to GitHub Actions runners. If your scraper "suddenly breaks" only in CI, test the IP before you debug the parser. (This is a general lesson: I lost an hour to it, and separately found that Booking.com serves an AWS WAF challenge to plain HTTP that no header tweak gets past.)

**4. Fail loudly.** If `__SERVER_DATA__` disappears, raise — don't return `[]`. A scraper that quietly returns nothing when a site changes is worse than one that crashes, because you'll ship empty data for weeks without noticing. Same for partial changes: assert on the fields you promise.

## Be a good citizen

Sleep between requests (300ms is plenty), cap your page count, and set a real User-Agent. This is public event listing data — venue, time, ticket link — the same information Eventbrite publishes for humans to read. Don't harvest attendee or organizer personal data, and check Eventbrite's terms for your use case.

## If you'd rather not maintain it

I run this as a hosted Actor on Apify, which handles the pagination, dedupe, retries and daily breakage checks:

**[Eventbrite Events Scraper](https://apify.com/dhandhabot_9953/eventbrite-events-scraper)** — give it a city or a search URL, get clean JSON/CSV/Excel rows out, or call it from an API. It costs $3 per 1,000 events, and there's a free tier to try it on.

But honestly — the snippet at the top is most of it. If you only need one city once, just use that.

---

*Questions or a field I missed? Happy to answer in the comments.*
