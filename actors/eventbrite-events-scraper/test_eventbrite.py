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


def test_live():
    print("\n[live] asli Eventbrite (network chahiye)")
    import requests

    def fetch(u):
        r = requests.get(u, headers=eb.HEADERS, timeout=30)
        r.raise_for_status()
        return r.text

    rows = eb.run_sync(fetch, location="india--mumbai", max_items=25)
    check("events mile", len(rows) >= 10, f"sirf {len(rows)}")
    check("ids unique", len({r["id"] for r in rows}) == len(rows))
    check("naam bhara hai", all(r["name"] for r in rows))
    check("url bhara hai", all(r["url"] for r in rows))
    have_venue = sum(1 for r in rows if r["venueCity"])
    check("venue city zyadatar rows me", have_venue >= len(rows) * 0.5,
          f"{have_venue}/{len(rows)}")


if __name__ == "__main__":
    test_offline()
    if "--offline" not in sys.argv:
        test_live()
    print()
    if FAILED:
        print(f"{len(FAILED)} FAIL: {', '.join(FAILED)}")
        sys.exit(1)
    print("sab pass")
