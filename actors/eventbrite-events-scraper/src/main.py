"""Apify Actor wrapper.

Scraping ka logic yahan NAHI hai -- wo eventbrite.py me hai, aur wahi test hota hai
(test_eventbrite.py). Yahan sirf: input padho, crawl chalao, data push karo, charge karo.
"""
import asyncio

import httpx
from apify import Actor

from .eventbrite import HEADERS, crawl

# PAY_PER_EVENT: har event row pe charge lagta hai. Ye naam Apify Console ke
# pricing me BILKUL yahi hona chahiye, warna charge chup-chaap fail hota rahega.
CHARGE_EVENT = "event-scraped"


async def run_async(fetch, **kw):
    """crawl() generator ko async fetch se chalao. Logic wahi, transport alag."""
    gen = crawl(**kw)
    try:
        url = next(gen)
        while True:
            html = await fetch(url)
            await asyncio.sleep(0.3)      # Eventbrite pe daya karo
            url = gen.send(html)
    except StopIteration as stop:
        return stop.value or []


async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        locations = inp.get("locations") or []
        category = inp.get("category") or "all-events"
        start_urls = [u["url"] if isinstance(u, dict) else u
                      for u in (inp.get("startUrls") or [])]
        max_items = int(inp.get("maxItems") or 100)
        max_pages = int(inp.get("maxPagesPerSearch") or 20)

        if not locations and not start_urls:
            raise ValueError("locations ya startUrls me se kuch to do "
                             "(misaal: locations = ['india--mumbai'])")

        targets = [{"start_url": u} for u in start_urls]
        targets += [{"location": loc, "category": category} for loc in locations]

        pushed = 0
        # ek hi client sab requests ke liye = connection reuse = tez aur sasta
        async with httpx.AsyncClient(headers=HEADERS, timeout=30,
                                     follow_redirects=True) as client:
            async def fetch(url):
                r = await client.get(url)
                r.raise_for_status()
                return r.text

            for t in targets:
                budget = max_items - pushed
                if budget <= 0:
                    break
                label = t.get("start_url") or f"{t['location']}/{t['category']}"
                Actor.log.info(f"scraping {label} (budget {budget})")

                rows = await run_async(fetch, max_items=budget,
                                       max_pages=max_pages, **t)
                if not rows:
                    Actor.log.warning(f"kuch nahi mila: {label}")
                    continue

                await Actor.push_data(rows)
                pushed += len(rows)

                try:
                    await Actor.charge(event_name=CHARGE_EVENT, count=len(rows))
                except Exception as e:
                    # FREE plan pe / monetization band hone pe charge fail hota hai.
                    # Ye run ko marne ki wajah nahi -- data phir bhi mila.
                    Actor.log.warning(f"charge nahi hua ({len(rows)} rows): {e}")

                Actor.log.info(f"{len(rows)} events pushed from {label}")

        Actor.log.info(f"done -- {pushed} events")
