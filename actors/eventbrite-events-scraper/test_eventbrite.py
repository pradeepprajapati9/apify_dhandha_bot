"""Eventbrite scraper ka test. Apify ki zarurat nahi.

Do tarah ke test:
  1. OFFLINE -- fake HTML pe logic check (dedupe, pagination, parsing)
  2. LIVE    -- asli Eventbrite pe. Ye wo test hai jo batayega ki site badal gayi.

Chalao:  python test_eventbrite.py
         python test_eventbrite.py --offline    (network ke bina)

Apify roz Actor ko auto-test karta hai aur 3 din lagatar fail = store me demote.
Isliye ye test CI me roz chalta hai -- taaki hum Apify se PEHLE pakad lein.
"""
import json
import sys

sys.path.insert(0, "src")
import eventbrite as eb           # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILED.append(name)


def _fake_html(ids, page_number, page_count):
    events = [{
        "id": str(i), "name": f"Event {i}", "url": f"https://e/{i}",
        "start_date": "2026-08-19", "start_time": "09:30",
        "image": {"url": "https://img/x.jpg"},
        "primary_venue": {"name": "Hall", "address": {"city": "Mumbai", "country": "IN"}},
        "tags": [{"display_name": "Music"}, {"prefix": "x"}],
    } for i in ids]
    blob = {"search_data": {"events": {
        "results": events,
        "pagination": {"page_number": page_number, "page_count": page_count},
    }}}
    return "<html><script>window.__SERVER_DATA__ = " + json.dumps(blob) + ";</script>"


def test_offline():
    print("\n[offline] parsing + dedupe + pagination")

    # page 1 aur page 2 me id 3 dono me hai -> dedupe hona chahiye
    pages = {
        eb.build_url("x", "all-events", 1): _fake_html([1, 2, 3], 1, 2),
        eb.build_url("x", "all-events", 2): _fake_html([3, 4, 5], 2, 2),
    }
    rows = eb.run_sync(lambda u: pages[u], location="x", max_items=100)
    check("dono pages crawl hue", len(rows) == 5, f"mile {len(rows)}")
    check("duplicate id hata", len({r["id"] for r in rows}) == 5)

    # max_items respect
    rows = eb.run_sync(lambda u: pages[u], location="x", max_items=2)
    check("max_items ruka", len(rows) == 2, f"mile {len(rows)}")

    # page_count 1 -> doosra page maanga hi nahi jaana chahiye
    seen = []

    def once(u):
        seen.append(u)
        return _fake_html([1, 2], 1, 1)

    eb.run_sync(once, location="y", max_items=100)
    check("page_count=1 pe ruk gaya", len(seen) == 1, f"{len(seen)} requests")

    # field mapping
    row = eb.clean_event(json.loads(_fake_html([9], 1, 1).split(" = ", 1)[1]
                                    .rsplit(";", 1)[0])["search_data"]["events"]["results"][0])
    check("venueCity nikla", row["venueCity"] == "Mumbai")
    check("tags sirf display_name", row["tags"] == ["Music"], row["tags"])
    check("imageUrl nikla", row["imageUrl"] == "https://img/x.jpg")

    # __SERVER_DATA__ gayab -> saaf error, chup-chaap 0 rows nahi
    try:
        eb.run_sync(lambda u: "<html>no data</html>", location="z")
        check("page badla to error aaya", False, "koi error nahi aaya")
    except RuntimeError as e:
        check("page badla to error aaya", "__SERVER_DATA__" in str(e))

    # ---- BILLING: do overlapping target = ek hi row do baar charge? ----
    # Ye wahi bug tha jo buyer se DO BAAR paisa le raha tha.
    shared = set()
    all_rows = []
    for _ in range(2):                       # wahi target do baar (jaise mumbai + uska startUrl)
        all_rows += eb.run_sync(lambda u: _fake_html([1, 2, 3], 1, 1),
                                location="dup", max_items=100, seen=shared)
    check("overlapping target pe duplicate charge NAHI", len(all_rows) == 3,
          f"{len(all_rows)} rows push hote (3 hone chahiye) -> buyer se extra vasooli")

    # ---- buyer ne page=2 wala URL paste kiya -> ?page=2&page=2 nahi banna chahiye ----
    # (pehle blindly &page=N judta tha -> wahi page dobara -> sab dedupe -> buyer
    #  ko sirf ek page milta, bina warning ke)
    got = []
    eb.run_sync(lambda u: (got.append(u), _fake_html([1, 2], 1, 3))[1],
                start_url="https://e.com/d/x/all-events/?page=2", max_items=4)
    check("koi URL me do baar page= nahi", all(u.count("page=") <= 1 for u in got), got)
    check("page 1 se shuru (paste kiya page param hata)",
          "page=" not in got[0], got[0])
    check("page 2 pe sahi param",
          len(got) > 1 and got[1].endswith("page=2"), got[:2])
    check("page_url purana param badal deta hai",
          eb.page_url("https://e.com/x/?page=5&q=a", 3) == "https://e.com/x/?q=a&page=3",
          eb.page_url("https://e.com/x/?page=5&q=a", 3))


def test_live():
    """Asli Eventbrite se test. SIRF ghar/laptop se chalta hai.

    GitHub Actions ya kisi bhi datacenter IP se Eventbrite 405 deta hai. Isliye
    CI --offline chalata hai. Apify ke server se bilkul theek chalta hai (wahan
    hamara Actor roz 80+ events laata hai), to 405 ka matlab Actor toota NAHI --
    matlab bas is machine ka IP blocked hai.
    """
    print("\n[live] asli Eventbrite (network chahiye)")
    import requests

    probe = requests.get(eb.build_url("india--mumbai"), headers=eb.HEADERS, timeout=30)
    if probe.status_code in (403, 405, 429):
        print(f"  SKIP  Eventbrite ne is IP ko block kiya (HTTP {probe.status_code})")
        print("        Ye Actor ka fail nahi hai -- datacenter IP aksar block hote hain.")
        print("        Asli jaanch: python check_actor.py (Apify pe chalta hai)")
        return

    def fetch(u):
        r = requests.get(u, headers=eb.HEADERS, timeout=30)
        r.raise_for_status()
        return r.text

    pages = []

    def fetch_counted(u):
        pages.append(u)
        return fetch(u)

    # 25 maango -- ek page pe ~20 hote hain, to pagination zaroor chalegi.
    rows = eb.run_sync(fetch_counted, location="india--mumbai", max_items=25)
    check("events mile", len(rows) >= 10, f"sirf {len(rows)}")
    check("ids unique", len({r["id"] for r in rows}) == len(rows))

    # Pagination sach me chali? Warna page_count tootne pe hum chup-chaap
    # ek hi page dete rahenge aur test pass hota rahega.
    check("pagination chali (1 se zyada page)", len(pages) >= 2,
          f"sirf {len(pages)} request -- page_count toot gaya?")

    # Har column check -- warna Eventbrite ek field ka naam badle aur hum
    # buyer ko null bech dein, poore daam pe.
    must = ["id", "name", "url", "startDate"]
    for f in must:
        n = sum(1 for r in rows if r.get(f))
        check(f"{f} har row me", n == len(rows), f"{n}/{len(rows)}")

    mostly = ["summary", "startTime", "timezone", "imageUrl", "ticketsUrl",
              "organizerId", "tags", "venueName", "venueCity", "venueCountry",
              "venueAddress", "venueLatitude"]
    for f in mostly:
        n = sum(1 for r in rows if r.get(f))
        check(f"{f} zyadatar rows me", n >= len(rows) * 0.5, f"{n}/{len(rows)}")


if __name__ == "__main__":
    test_offline()
    if "--offline" not in sys.argv:
        test_live()
    print()
    if FAILED:
        print(f"{len(FAILED)} FAIL: {', '.join(FAILED)}")
        sys.exit(1)
    print("sab pass")
