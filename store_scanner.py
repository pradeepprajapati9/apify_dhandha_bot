"""Apify Store — GAP scanner.

Kaam ek hi: Actor banane se PEHLE pata karo ki kaun si jagah khaali hai.
Store me 38,000+ actors hain. Guess karke banaya to wahi banega jo pehle se
5 lakh users wala mojood hai -> teen hafte barbaad.

Ye script:
  1. /v2/store se saare actors kheenchta hai (public API, login nahi chahiye)
  2. data/store.json me cache -- baar-baar API mat maaro
  3. rules.py se niche banata + grade karta hai
  4. gaps.txt + dashboard.html likhta hai

Chalao:  python store_scanner.py
Taaza data:  python store_scanner.py --fresh
"""
import html
import io
import json
import os
import sys
import time

import requests

import rules

API = "https://api.apify.com/v2/store"
PAGE = 1000
OFFSET_CAP = 16000       # API isse aage 0 items deta hai -- ye Apify ki limit hai, meri nahi
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "store.json")
OUT_TXT = os.path.join(HERE, "gaps.txt")
OUT_HTML = os.path.join(HERE, "dashboard.html")
CACHE_HOURS = 24

# Poora store ek saath maangoge to API 16,000 pe ruk jaata hai (38k+ hone ke bawajood).
# Isliye category-wise maangte hain -- har category chhoti hai. Actor kai categories me
# ho sakta hai, isliye id se dedupe zaroori.
CATEGORIES = [
    "AUTOMATION", "LEAD_GENERATION", "DEVELOPER_TOOLS", "SOCIAL_MEDIA", "ECOMMERCE",
    "OTHER", "AI", "JOBS", "REAL_ESTATE", "SEO_TOOLS", "INTEGRATIONS", "VIDEOS",
    "BUSINESS", "AGENTS", "NEWS", "TRAVEL", "MARKETING", "MCP_SERVERS",
    "OPEN_SOURCE", "EDUCATION", "SPORTS", "FOR_CREATORS", "GAMES",
]


def _page(params):
    r = requests.get(API, params=params, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def fetch_category(cat):
    """Ek category ke saare actors. (items, api_total) -- truncation pakadne ke liye."""
    items, offset, total = [], 0, 0
    while offset < OFFSET_CAP:
        d = _page({"limit": PAGE, "offset": offset, "category": cat})
        total = d["total"]
        batch = d["items"]
        if not batch:
            break
        items.extend(batch)
        offset += len(batch)
        time.sleep(0.15)
    return items, total


def fetch_all():
    """Har category se kheencho, id se dedupe. Kitna chhoot gaya wo bhi batao."""
    by_id, missed = {}, []
    for i, cat in enumerate(CATEGORIES, 1):
        items, total = fetch_category(cat)
        for a in items:
            by_id[a["id"]] = a          # dedupe -- wahi actor kai categories me hota hai
        if total > len(items):
            missed.append((cat, total - len(items)))
        print(f"    [{i:2}/{len(CATEGORIES)}] {cat:16} {len(items):>5} liye "
              f"(api total {total})  |  ab tak unique: {len(by_id)}")

    if missed:
        # Chup-chaap mat kaato -- bata do kya chhoot gaya.
        print("\n    [!] API ke 16k offset cap ki wajah se ye chhoot gaye:")
        for cat, n in missed:
            print(f"        {cat}: ~{n} actors (ye sabse KAM popular the)")
        print("        Ye tail hai -- inme demand waise bhi na ke barabar hoti hai.")
    return list(by_id.values())


VERIFY_TOP = 60          # itne candidates search se verify honge (itni hi API calls)
SEARCH_N = 10            # search ke top itne actors = asli muqabla


def search_niche(term):
    """Apify ki APNI search -- yahi sach hai, meri clustering nahi.

    Buyer jab ye term type karta hai, use jo dikhta hai wahi lauta rahe hain.
    """
    d = _page({"limit": SEARCH_N, "search": term})
    items = d["items"]
    if not items:
        return {"niche": term, "results": 0, "personal": rules.is_personal(term),
                "demand30": 0, "demand7": 0, "momentum": 0, "paid_share": 0,
                "leader_title": "", "leader_users": 0, "leader_rating": 0,
                "leader_reviews": 0, "leader_stale_days": 9999, "leader_url": "",
                "rivals": [], "actors": 0}

    items.sort(key=lambda a: a["stats"].get("totalUsers", 0), reverse=True)
    lead = items[0]
    d30 = sum(a["stats"].get("totalUsers30Days", 0) for a in items)
    d7 = sum(a["stats"].get("totalUsers7Days", 0) for a in items)
    paid = [a for a in items
            if (a.get("currentPricingInfo") or {}).get("pricingModel") == "PAY_PER_EVENT"]
    rivals = [(a.get("title", ""), a["stats"].get("totalUsers", 0),
               a["stats"].get("totalUsers30Days", 0)) for a in items[:3]]
    return {
        "niche": term,
        "results": d["total"],
        # niche ka naam saaf ho sakta hai par actors personal data bech rahe hon
        "personal": rules.is_personal(term, rivals),
        "actors": len(items),
        "demand30": d30,
        "demand7": d7,
        "momentum": (d7 * 4 / d30) if d30 else 0,
        "paid_share": len(paid) / len(items),
        "leader_title": lead.get("title", ""),
        "leader_url": lead.get("url", ""),
        "leader_users": lead["stats"].get("totalUsers", 0),
        "leader_rating": lead.get("actorReviewRating") or 0,
        "leader_reviews": lead.get("actorReviewCount") or 0,
        "leader_stale_days": rules._age_days(lead["stats"].get("lastRunStartedAt")),
        "rivals": rivals,
    }


def verify(candidates):
    """Top candidates ko Apify search se verify karo. Yahi asli grading hai."""
    out = []
    for i, c in enumerate(candidates, 1):
        try:
            v = search_niche(c["niche"])
        except Exception as e:
            print(f"    [{i:2}/{len(candidates)}] {_safe(c['niche']):<24} search fail: {e}")
            continue
        v["grade"], v["why"] = rules.verify_grade(v)
        v["guess_demand"] = c["demand30"]          # meri clustering ka andaza
        out.append(v)
        print(f"    [{i:2}/{len(candidates)}] {_safe(c['niche'])[:24]:<24} "
              f"-> {v['grade']:2}  (#1 = {v['leader_users']} users)")
        time.sleep(0.15)
    return out


def check_niche(term):
    """Wahi search jo ASLI BUYER karta hai. Scanner pe bharosa mat kar -- ye dekh."""
    d = _page({"limit": 10, "search": term})
    print(f"\n>>> Buyer '{term}' search kare to ye dikhta hai ({d['total']} results):\n")
    for a in d["items"]:
        s = a["stats"]
        pm = (a.get("currentPricingInfo") or {}).get("pricingModel", "-")
        print(f"  {_safe(a['title'])[:44]:<44} {s.get('totalUsers',0):>6} users "
              f"| {s.get('totalUsers30Days',0):>4}/30d | {a.get('actorReviewRating') or 0:.1f}* "
              f"| {pm}")
    print(f"\n  Sawaal: kya ye log SACH me kamzor hain, ya is data ki demand hi nahi?")
    print(f"  Khud dekh: https://apify.com/store?search={term.replace(' ', '+')}")


def load_actors(fresh=False):
    if not fresh and os.path.exists(CACHE):
        age_h = (time.time() - os.path.getmtime(CACHE)) / 3600
        if age_h < CACHE_HOURS:
            with io.open(CACHE, encoding="utf-8") as f:
                actors = json.load(f)
            print(f">>> cache se {len(actors)} actors ({age_h:.1f} ghante purana)")
            return actors

    print(">>> Apify Store se data kheench raha hun...")
    actors = fetch_all()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with io.open(CACHE, "w", encoding="utf-8") as f:
        json.dump(actors, f)
    print(f">>> {len(actors)} actors cache me: {CACHE}")
    return actors


def _safe(s):
    """Windows console utf-8 pe rota hai."""
    return str(s).encode("ascii", "ignore").decode()


def write_txt(graded, total_actors):
    fit = [n for n in graded if n["grade"] in ("A+", "A", "B")]
    with io.open(OUT_TXT, "w", encoding="utf-8") as f:
        if fit:
            b = fit[0]
            f.write("#" * 72 + "\n")
            f.write("AAJ YE KAR  ->  ye niche kholo apify.com pe, AANKH se check karo:\n\n")
            f.write(f"   >>>  {b['niche'].upper()}  <<<\n")
            f.write(f"   kyun: {b['why']}\n")
            f.write(f"   30-din demand: {b['demand30']} users  |  is niche me {b['actors']} actors\n")
            f.write(f"   jo #1 hai: {b['leader_title']}  ({b['leader_users']} users, "
                    f"rating {b['leader_rating']:.1f})\n")
            f.write(f"   uska link: {b['leader_url']}\n\n")
            f.write("   >>> KYA CHECK KARNA HAI (scanner ye nahi bata sakta):\n")
            f.write("       Leader ke kam users ke DO matlab hote hain --\n")
            f.write("         (a) jagah khaali hai   YA   (b) is data ki demand hi nahi.\n")
            f.write("       Link kholo. Reviews padho. Tab hi Actor banao.\n")
            f.write("#" * 72 + "\n\n")

        f.write(f"APIFY STORE GAPS -- {total_actors} actors scanned, "
                f"{len(graded)} niches, {len(fit)} FIT\n")
        f.write("A+ = demand hai + leader kamzor + log paise de rahe hain\n")
        f.write("A  = wahi, par leader thoda bada\n")
        f.write("B  = leader bada hai PAR tuta/kharab rating -> replace karne ka mauka\n")
        f.write("=" * 72 + "\n\n")
        for n in graded:
            if n["grade"] in ("C", "F"):
                continue
            f.write(f"[{n['grade']}] {n['niche']}\n")
            f.write(f"     {n['why']}\n")
            f.write(f"     demand {n['demand30']}/30din (7din: {n['demand7']})  |  "
                    f"{n['actors']} actors  |  {int(n['paid_share']*100)}% paid\n")
            f.write("     muqabla (top 3, jo buyer ko search me dikhenge):\n")
            for t, u, u30 in n["rivals"]:
                f.write(f"        - {t}  [{u} users, {u30}/30d]\n")
            f.write(f"     {n['leader_url']}\n")
            f.write(f"     khud dekh: python store_scanner.py --check \"{n['niche']}\"\n\n")
    return len(fit)


CARD_CSS = """
body{background:#0f1115;color:#e6e6e6;font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#8b93a1;margin-bottom:20px;font-size:13px}
.warn{background:#2a1f00;border:1px solid #5c4400;color:#ffd27a;padding:12px 14px;
      border-radius:8px;margin-bottom:20px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.card{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:14px}
.card h2{font-size:16px;margin:0 0 6px;text-transform:capitalize}
.g{display:inline-block;font-weight:700;font-size:12px;padding:2px 8px;border-radius:5px;
   margin-right:6px;vertical-align:2px}
.gA\\+{background:#0e4429;color:#3fb950}
.gA{background:#123a5c;color:#58a6ff}
.gB{background:#4a3800;color:#e3b341}
.why{color:#e3b341;font-size:13px;margin:6px 0}
.row{color:#8b93a1;font-size:12px;margin:3px 0}
.rivals{border-left:2px solid #262b36;padding-left:8px;margin:8px 0;font-size:12px;color:#8b93a1}
b{color:#e6e6e6}
a{color:#58a6ff;text-decoration:none;font-size:12px}
a:hover{text-decoration:underline}
"""


def write_dashboard(graded, total_actors):
    fit = [n for n in graded if n["grade"] in ("A+", "A", "B")]
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>Apify Store Gaps</title>",
        f"<style>{CARD_CSS}</style>",
        "<h1>Apify Store — khaali jagah</h1>",
        f"<div class='sub'>{total_actors} actors scanned &middot; {len(graded)} niches "
        f"&middot; {len(fit)} fit</div>",
        "<div class='warn'><b>Scanner shortlist deta hai, faisla nahi.</b> Leader ke kam "
        "users ka matlab ya to <b>jagah khaali hai</b>, ya to <b>us data ki demand hi nahi</b>. "
        "Neeche ka link kholo, reviews padho — tab Actor banao.</div>",
        "<div class='grid'>",
    ]
    for n in fit:
        e = html.escape
        rivals = "".join(
            f"<div class='row'>&middot; {e(t)} <b>[{u}]</b> {u30}/30d</div>"
            for t, u, u30 in n["rivals"]
        )
        parts.append(
            f"<div class='card'>"
            f"<h2><span class='g g{e(n['grade'])}'>{e(n['grade'])}</span>{e(n['niche'])}</h2>"
            f"<div class='why'>{e(n['why'])}</div>"
            f"<div class='row'>demand <b>{n['demand30']}</b> users/30din "
            f"&middot; 7din {n['demand7']} &middot; {n['actors']} actors "
            f"&middot; {int(n['paid_share']*100)}% paid</div>"
            f"<div class='rivals'>muqabla:{rivals}</div>"
            f"<div class='row'>#1 rating {n['leader_rating']:.1f} "
            f"({n['leader_reviews']} reviews) &middot; last run "
            f"{n['leader_stale_days']}d ago</div>"
            f"<a href='{e(n['leader_url'])}' target='_blank'>leader kholo &rarr;</a>"
            f"</div>"
        )
    parts.append("</div>")
    with io.open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return len(fit)


def main():
    if "--check" in sys.argv:
        i = sys.argv.index("--check")
        term = " ".join(sys.argv[i + 1:]).strip()
        if not term:
            print('use: python store_scanner.py --check "bluesky"')
            return
        check_niche(term)
        return

    fresh = "--fresh" in sys.argv
    actors = load_actors(fresh)

    # STEP 1: clustering se sirf CANDIDATE terms nikaalo. Ye andaza hai, sach nahi.
    niches = rules.build_niches(actors)
    cands = []
    for n in niches.values():
        n["grade"], n["why"] = rules.grade(n)
        cands.append(n)
    cands = [c for c in cands if c["grade"] in ("A+", "A", "B")]
    cands.sort(key=lambda c: -c["demand30"])
    cands = cands[:VERIFY_TOP]
    print(f">>> {len(niches)} candidate terms -> top {len(cands)} verify kar raha hun")

    # STEP 2: har candidate ko Apify ki APNI search se verify karo. Yahi grading hai.
    print(">>> Apify search se muqabla check (yahi buyer dekhta hai):")
    graded = verify(cands)
    graded.sort(key=lambda n: (rules.GRADE_ORDER[n["grade"]], -n["demand30"]))

    n_fit = write_txt(graded, len(actors))
    write_dashboard(graded, len(actors))

    counts = {}
    for n in graded:
        counts[n["grade"]] = counts.get(n["grade"], 0) + 1
    print(f"\n===== {len(actors)} actors | {len(cands)} verified =====")
    print("   " + "  ".join(f"{g}:{counts.get(g,0)}" for g in ["A+", "A", "B", "C", "F"]))
    print()
    for n in graded[:15]:
        if n["grade"] in ("C", "F"):
            break
        print(f"[{n['grade']:2}] {_safe(n['niche'])[:24]:<24} "
              f"demand {n['demand30']:>4}  #1 {n['leader_users']:>5}  {_safe(n['why'])[:40]}")

    print(f"\n>>> Poori list : {OUT_TXT}   ({n_fit} fit)")
    print(f">>> Dashboard  : {OUT_HTML}  (double-click kholo)")
    print(">>> Top 3 gaps AANKH se check kar -- scanner jhooth bol sakta hai.")


if __name__ == "__main__":
    main()
