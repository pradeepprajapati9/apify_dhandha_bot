"""Eventbrite search page -> saaf event rows.

Yahan Apify ka koi zikr nahi hai. Isliye ye bina Apify ke test ho jaata hai
(dekho: test_eventbrite.py). Actor ka wrapper main.py me hai.

Eventbrite har search page ke HTML me `window.__SERVER_DATA__` daalta hai, jisme
poora event JSON hota hai. Na browser chahiye, na proxy -- isliye ye Actor sasta
padta hai. (Booking.com pe AWS WAF hai, wahan browser+proxy lagta -- aur wo cost
seedha profit se kat-ti hai.)
"""
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BASE = "https://www.eventbrite.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

_SERVER_DATA = re.compile(r"window\.__SERVER_DATA__\s*=\s*(\{.*?\});", re.S)


def build_url(location, category="all-events", page=1):
    """('india--mumbai', 'music', 2) -> search URL"""
    url = f"{BASE}/d/{location.strip('/')}/{category.strip('/')}/"
    return f"{url}?page={page}" if page > 1 else url


def page_url(base_url, page):
    """URL pe page number lagao -- purana `page` param HATA ke.

    Buyer aksar browser me page 2 pe jaake URL copy karta hai. Pehle hum blindly
    `&page=2` jod dete the -> `?page=2&page=2` -> wahi page dobara -> sab dedupe
    ho jaata -> crawl page 1 pe hi ruk jaata, aur buyer ko sirf ek page milta
    (bina kisi warning ke). Isliye ab purana param nikaal ke naya lagate hain.
    """
    parts = urlsplit(base_url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
         if k.lower() != "page"]
    if page > 1:
        q.append(("page", str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(q), parts.fragment))


def parse_page(html):
    """HTML -> (events, pagination). Mila hi nahi to (None, None) -- caller decide kare."""
    m = _SERVER_DATA.search(html)
    if not m:
        return None, None
    try:
        events = json.loads(m.group(1))["search_data"]["events"]
    except (ValueError, KeyError):
        return None, None
    return events.get("results", []), events.get("pagination", {})


def _venue(e):
    v = e.get("primary_venue") or {}
    addr = v.get("address") or {}
    return {
        "venueName": v.get("name"),
        "venueCity": addr.get("city"),
        "venueRegion": addr.get("region"),
        "venueCountry": addr.get("country"),
        "venueAddress": addr.get("localized_address_display"),
        "venueLatitude": addr.get("latitude"),
        "venueLongitude": addr.get("longitude"),
    }


def _tags(e):
    out = []
    for t in e.get("tags") or []:
        name = t.get("display_name")
        if name:
            out.append(name)
    return out


def clean_event(e):
    """Raw Eventbrite object -> wo row jo buyer ko chahiye."""
    img = e.get("image") or {}
    row = {
        "id": e.get("id"),
        "name": e.get("name"),
        "summary": e.get("summary"),
        "url": e.get("url"),
        "startDate": e.get("start_date"),
        "startTime": e.get("start_time"),
        "endDate": e.get("end_date"),
        "endTime": e.get("end_time"),
        "timezone": e.get("timezone"),
        "isOnlineEvent": e.get("is_online_event"),
        "isCancelled": e.get("is_cancelled"),
        "ticketsUrl": e.get("tickets_url"),
        "organizerId": e.get("primary_organizer_id"),
        "imageUrl": img.get("url"),
        "language": e.get("language"),
        "tags": _tags(e),
    }
    row.update(_venue(e))
    return row


def crawl(location=None, category="all-events", start_url=None,
          max_items=100, max_pages=50, seen=None):
    """Generator: URL yield karta hai, uska HTML `send()` se wapas leta hai.

    Isse crawl ka logic ek hi jagah rehta hai. Test ise sync `requests` se
    chalata hai, Actor ise async `httpx` se -- aur code dono ke liye same hai.
    Rows `StopIteration.value` me milte hain (dekho run_sync).

    `seen` BAAHAR se aata hai -- ye zaroori hai. Pehle har crawl apna naya `seen`
    banata tha, matlab dedupe sirf ek target ke andar chalta tha. Buyer agar
    'india--mumbai' aur uska hi startUrl dono deta, to POORA data DO BAAR push
    hota aur DO BAAR charge hota ($3/1,000 har baar). Ek hi `seen` poore run ka
    hona chahiye. README bhi yahi wada karta hai.

    max_pages ki wajah: New York pe 49 pages / 10,000 events hain. Bina limit ke
    ek run mahenga ho jaayega aur buyer ko bada bill chala jaayega.
    """
    if seen is None:
        seen = set()
    rows, page = [], 1
    while len(rows) < max_items and page <= max_pages:
        if start_url:
            url = page_url(start_url, page)
        else:
            url = build_url(location, category, page)

        html = yield url
        events, pg = parse_page(html)
        if events is None:
            raise RuntimeError(
                f"__SERVER_DATA__ nahi mila: {url} -- Eventbrite ne page badla hai")
        if not events:
            break

        fresh = 0
        for e in events:
            eid = e.get("id")
            if eid in seen:            # pagination overlap deta hai
                continue
            seen.add(eid)
            rows.append(clean_event(e))
            fresh += 1
            if len(rows) >= max_items:
                break

        if fresh == 0:
            break
        if page >= ((pg or {}).get("page_count") or 1):
            break
        page += 1

    return rows[:max_items]


def run_sync(fetch, **kw):
    """crawl() ko blocking fetch(url)->html se chalao. Test aur CLI ke liye."""
    gen = crawl(**kw)
    try:
        url = next(gen)
        while True:
            url = gen.send(fetch(url))
    except StopIteration as stop:
        return stop.value or []
