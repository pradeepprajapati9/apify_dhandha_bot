"""Apify Actor wrapper.

Scraping ka logic yahan NAHI hai -- wo eventbrite.py me hai, aur wahi test hota hai
(test_eventbrite.py). Yahan sirf: input padho, crawl chalao, data push karo.
"""
import asyncio

import httpx
from apify import Actor

from .eventbrite import HEADERS, crawl

# Bilkul khaali input aane pe kya karein.
#
# ZAROORI: Apify roz is Actor ko uske default input se auto-test karta hai. Agar
# 5 min me non-empty dataset na mile aur ye 3 din lagatar ho -> "under maintenance"
# + store me demote. Pehle yahan khaali input pe ValueError uthta tha, matlab Actor
# 3 din me mar jaata. Isliye ab khaali input = ye default sheher.
#
# input_schema me `default` nahi daala jaan-boojh ke: tab buyer sirf startUrls deta
# to Apify locations ko default se bhar deta aur wo bina maange scrape hokar
# CHARGE ho jaata. Fallback sirf tab jab DONO khaali hon.
DEFAULT_LOCATIONS = ["india--mumbai"]

# CHARGING: yahan koi charge code NAHI hai -- jaan-boojh ke.
#
# Console me pricing `apify-default-dataset-item` pe set hai ($3/1,000), aur wo
# event Apify KHUD lagata hai jab bhi push_data() se dataset me row jaati hai.
# Pehle yahan Actor.charge("event-scraped") tha -- agar wo rehta to buyer se
# DO BAAR paisa katta (ek Apify ka automatic, ek hamara). Isliye hata diya.
#
# Matlab: charge = jitni rows push hongi, utna. Bas push_data() sahi rakho.

RETRY_STATUS = (429, 500, 502, 503, 504)
MAX_RETRIES = 3


async def fetch_with_retry(client, url):
    """429/5xx pe ruk ke dobara koshish karo.

    Bina iske: Eventbrite ek 429 bhejta hai -> exception poore run ko le doobti
    hai -> run FAILED. Aur FAILED runs seedha Actor ki "Reliability" giraate hain,
    jo store ranking ka hissa hai. Ek hichki se poora run marna theek nahi.
    """
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            r = await client.get(url)
            if r.status_code in RETRY_STATUS:
                wait = 2 ** attempt * 2          # 2s, 4s, 8s
                Actor.log.warning(f"HTTP {r.status_code} -> {wait}s baad retry: {url}")
                await asyncio.sleep(wait)
                last = RuntimeError(f"HTTP {r.status_code} for {url}")
                continue
            r.raise_for_status()
            return r.text
        except (httpx.TimeoutException, httpx.TransportError) as e:
            wait = 2 ** attempt * 2
            Actor.log.warning(f"network error -> {wait}s baad retry: {e}")
            await asyncio.sleep(wait)
            last = e
    raise last or RuntimeError(f"fetch fail: {url}")


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


def _urls(raw):
    """startUrls kai shakl me aate hain -- sabko sambhaalo.

    `requestListSources` editor "Link to a file with URLs" bhi deta hai, jo
    {"requestsFromUrl": "..."} bhejta hai -- usme `url` key hoti hi nahi.
    Pehle yahan u["url"] tha -> KeyError -> run turant FAIL, buyer ko bas
    traceback dikhta.
    """
    out = []
    for u in raw or []:
        val = u.get("url") if isinstance(u, dict) else u
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
        elif isinstance(u, dict) and u.get("requestsFromUrl"):
            Actor.log.warning(
                "startUrls me 'link to a file with URLs' abhi support nahi hai -- "
                f"skip: {u.get('requestsFromUrl')}. Seedha URL ya locations do.")
    return out


async def main():
    async with Actor:
        inp = await Actor.get_input() or {}
        locations = [l.strip() for l in (inp.get("locations") or []) if str(l).strip()]
        category = (inp.get("category") or "all-events").strip() or "all-events"
        start_urls = _urls(inp.get("startUrls"))
        max_items = int(inp.get("maxItems") or 100)
        max_pages = int(inp.get("maxPagesPerSearch") or 20)

        if not locations and not start_urls:
            locations = DEFAULT_LOCATIONS
            Actor.log.info(f"koi input nahi mila -> default location: {locations}")

        targets = [{"start_url": u} for u in start_urls]
        targets += [{"location": loc, "category": category} for loc in locations]

        # EK hi `seen` poore run ke liye -- har target ke liye alag nahi.
        # Warna overlapping targets (mumbai + uska startUrl, ya online events jo
        # har sheher me dikhte hain) DO BAAR push aur DO BAAR charge hote.
        seen = set()
        pushed = 0
        failed = []

        async with httpx.AsyncClient(headers=HEADERS, timeout=30,
                                     follow_redirects=True) as client:
            async def fetch(url):
                return await fetch_with_retry(client, url)

            for t in targets:
                budget = max_items - pushed
                if budget <= 0:
                    break
                label = t.get("start_url") or f"{t['location']}/{t['category']}"

                try:
                    rows = await run_async(fetch, max_items=budget,
                                           max_pages=max_pages, seen=seen, **t)
                except Exception as e:
                    # Ek target ka fail hona baaki targets ko nahi maarna chahiye.
                    # Aur run ko FAILED bhi nahi karna -- jo mila wo buyer ko de do.
                    Actor.log.exception(f"target fail: {label} -- {e}")
                    failed.append(label)
                    continue

                if not rows:
                    Actor.log.warning(f"kuch nahi mila: {label}")
                    continue

                # push_data() hi charge kar deta hai -- dekho upar wala note
                res = await Actor.push_data(rows)
                pushed += len(rows)
                Actor.log.info(f"{len(rows)} events pushed from {label}")

                # Buyer apne run pe max kharcha set kar sakta hai. Limit lagne pe
                # SDK charge aur push dono chup-chaap band kar deta hai PAR Actor
                # chalta rehta hai -> compute jalta hai, kamai zero. Khud ruko.
                if getattr(res, "event_charge_limit_reached", False):
                    Actor.log.info("buyer ki charge limit aa gayi -- yahin rok rahe hain")
                    break

        if failed:
            Actor.log.warning(f"{len(failed)} target fail hue: {failed}")
        if pushed == 0 and failed:
            # Kuch bhi na mila AUR fail bhi hua -> tab run ko FAIL hone do,
            # warna Apify ka roz ka test "sab theek hai" samajh lega.
            raise RuntimeError(f"koi data nahi mila, saare target fail: {failed}")

        Actor.log.info(f"done -- {pushed} events")
