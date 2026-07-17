"""Apify Actor wrapper.

Scraping ka logic yahan NAHI hai -- wo eventbrite.py me hai, aur wahi test hota hai
(test_eventbrite.py). Yahan sirf: input padho, crawl chalao, data push karo, charge karo.
"""
import asyncio

import httpx
from apify import Actor

from .eventbrite import HEADERS, crawl

# CHARGING: yahan koi charge code NAHI hai -- jaan-boojh ke.
#
# Console me pricing `apify-default-dataset-item` pe set hai ($3/1,000), aur wo
# event Apify KHUD lagata hai jab bhi push_data() se dataset me row jaati hai.
# Pehle yahan Actor.charge("event-scraped") tha -- agar wo rehta to buyer se
# DO BAAR paisa katta (ek Apify ka automatic, ek hamara). Isliye hata diya.
#
# Matlab: charge = jitni rows push hongi, utna. Bas push_data() sahi rakho.


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

                # push_data() hi charge kar deta hai -- dekho upar wala note
                await Actor.push_data(rows)
                pushed += len(rows)
                Actor.log.info(f"{len(rows)} events pushed from {label}")

        Actor.log.info(f"done -- {pushed} events")
