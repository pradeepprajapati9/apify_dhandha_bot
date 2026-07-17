"""Deployed Actor pe WAHI test jo Apify roz karta hai -- Apify se pehle.

Apify roz Actor ko uske default input se chalata hai. Pass hone ke liye:
  - status SUCCEEDED
  - dataset NON-EMPTY   <- sirf "crash nahi hua" kaafi nahi hai
  - 5 minute ke andar
2-3 din fail = "under maintenance" = store me demote + buyer ko "Similar Actors"
dikhne lagte hain (yaani Apify khud tere buyer ko competitor pe bhej deta hai).

Ye khaali input {} se chalata hai -- kyunki wahi sabse kamzor kadi hai. Ek baar
Actor khaali input pe ValueError phenk raha tha; poora Actor 3 din me mar jaata
aur test_eventbrite.py GREEN rehta (wo sirf Python logic dekhta hai, deployed
Actor ko nahi).

Chalao:  APIFY_TOKEN=... python check_actor.py
"""
import os
import sys
import time

import requests

ACTOR = "dhandhabot_9953~eventbrite-events-scraper"
TIMEOUT_S = 300          # Apify ki 5-minute limit
POLL_S = 5


def main():
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("APIFY_TOKEN nahi mila")
        return 1

    base = "https://api.apify.com/v2"
    p = {"token": token}

    print(f">>> {ACTOR} ko KHAALI input {{}} se chala rahe hain (Apify ka roz ka test)")
    t0 = time.time()
    r = requests.post(f"{base}/acts/{ACTOR}/runs", params=p, json={}, timeout=60)
    r.raise_for_status()
    run = r.json()["data"]
    rid = run["id"]
    print(f"    run: https://console.apify.com/actors/runs/{rid}")

    while time.time() - t0 < TIMEOUT_S:
        time.sleep(POLL_S)
        d = requests.get(f"{base}/actor-runs/{rid}", params=p, timeout=30).json()["data"]
        st = d["status"]
        if st in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        print(f"    {st}... {int(time.time()-t0)}s")
    else:
        print(f"FAIL: 5 minute me pura nahi hua -- Apify ise fail maanega")
        requests.post(f"{base}/actor-runs/{rid}/abort", params=p, timeout=30)
        return 1

    took = int(time.time() - t0)
    items = requests.get(f"{base}/datasets/{d['defaultDatasetId']}/items",
                         params={**p, "limit": 5}, timeout=30).json()
    charged = d.get("chargedEventCounts") or {}

    print(f"\n    status : {st}")
    print(f"    time   : {took}s (limit 300s)")
    print(f"    rows   : {len(items)} (sample)")
    print(f"    charged: {charged}")

    ok = True
    if st != "SUCCEEDED":
        print(f"\nFAIL: status {st} -- 3 din aisa hua to Actor demote ho jaayega")
        ok = False
    if not items:
        print("\nFAIL: dataset KHAALI -- Apify ise fail ginta hai chahe status SUCCEEDED ho")
        ok = False
    if took > TIMEOUT_S:
        print(f"\nFAIL: {took}s > 5 min")
        ok = False

    if ok:
        first = items[0]
        for f in ("id", "name", "url", "startDate"):
            if not first.get(f):
                print(f"\nFAIL: '{f}' khaali aa raha hai -- Eventbrite ne page badla?")
                ok = False

    print("\n" + ("PASS -- Actor tandurust hai" if ok else "FAIL -- ise abhi theek karo"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
