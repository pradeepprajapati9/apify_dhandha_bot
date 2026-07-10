"""Apify Store ke actors ko "niche" me group karke gap grade karta hai.

Soch: har actor ka title ek target batata hai -- "Google Maps Scraper" ka target
google maps hai, "Bluesky Scraper" ka bluesky. Generic shabd (scraper, api, bot...)
hata do to jo bacha, wahi NICHE hai.

Fir har niche pe 3 sawaal:
  1. DEMAND  -- pichhle 30 din me log aa rahe hain?      (totalUsers30Days ka sum)
  2. KAMZOR  -- jo #1 pada hai wo kitna strong hai?       (leader ke totalUsers)
  3. PAISA   -- us niche me log paise de rahe hain?       (PAY_PER_EVENT pricing)

Teeno HAAN = jagah khaali hai.
"""
import re
from datetime import datetime, timezone

# ---- tuning knobs (asli data dekh ke badle ja sakte hain) --------------
WEAK_LEADER = 500        # leader ke itne se kam users = kamzor incumbent
SOFT_LEADER = 1000       # A grade ke liye thoda dheela
MIN_DEMAND = 50          # niche me 30-din ke kul users, isse kam = demand nahi
LOW_DEMAND = 20          # A grade ke liye kam se kam itna
STALE_DAYS = 30          # leader itne din se nahi chala = tuta pada hai
BAD_RATING = 4.2         # isse kam rating = log khush nahi = replace karne ka mauka
MOMENTUM_HOT = 1.2       # 7-din*4 / 30-din > isse = niche badh raha hai


# Ye shabd har doosre actor ke naam me hain -- inse niche pata nahi chalta.
GENERIC = {
    # kya karta hai
    "scraper", "scrapers", "scraping", "crawler", "crawl", "extractor", "extract",
    "downloader", "download", "exporter", "export", "parser", "parse", "checker",
    "finder", "find", "search", "searcher", "monitor", "tracker", "track",
    "generator", "converter", "convert", "sync", "importer", "uploader", "collector",
    "harvester", "fetcher", "grabber", "analyzer", "validator", "verifier", "cleaner",
    # kya hai
    "api", "bot", "tool", "actor", "agent", "mcp", "app", "service", "client",
    "data", "dataset", "database", "scrape",
    # kya nikaalta hai (target nahi, output hai)
    "url", "urls", "link", "links", "page", "pages", "detail", "details", "info",
    "list", "listing", "listings", "profile", "profiles", "post", "posts",
    "comment", "comments", "review", "reviews", "rating", "ratings",
    "video", "videos", "image", "images", "photo", "photos", "audio",
    "price", "prices", "pricing", "product", "products", "item", "items",
    "job", "jobs", "news", "article", "articles", "content", "media", "feed",
    "stats", "statistics", "analytics", "metrics", "result", "results",
    "follower", "followers", "following", "hashtag", "hashtags", "keyword", "keywords",
    "channel", "channels", "user", "users", "account", "accounts",
    "story", "stories", "reel", "reels", "short", "shorts", "transcript", "subtitle",
    "subtitles", "caption", "captions", "comment", "message", "messages",
    # tech noise
    "cheerio", "puppeteer", "playwright", "selenium", "python", "js", "node",
    "http", "https", "www", "com", "io", "ai", "gpt", "llm", "openai", "gemini",
    "cookie", "cookies", "token", "tokens", "proxy", "status", "broken",
    "demo", "test", "example", "sample", "template", "enterprise", "grade",
    # dukaan/kaarobar ke aam shabd -- ye target nahi batate
    "store", "stores", "shop", "shops", "sku", "skus", "thread", "threads",
    "company", "companies", "seller", "sellers", "buyer", "buyers", "market",
    # marketing fluff
    "fast", "fastest", "cheap", "cheapest", "best", "pro", "ultimate", "advanced",
    "simple", "easy", "smart", "super", "mega", "turbo", "lite", "plus", "free",
    "premium", "official", "unofficial", "new", "top", "live", "real", "realtime",
    "time", "bulk", "batch", "mass", "multi", "auto", "automatic", "automated",
    "no", "code", "nocode", "custom", "full", "complete", "all", "any", "my", "your",
    # grammar
    "and", "or", "the", "for", "with", "from", "to", "of", "by", "in", "on", "at",
    "a", "an", "is", "as", "via", "per", "up", "out", "get", "v1", "v2", "v3",
}

# Personal data = legal risk. Apify ke terms: zimmedari 100% developer ki.
#
# ZAROORI FARQ: "business ka data" aur "insaan ka data" alag cheez hai.
#   Google Maps se dukaan ka naam+phone nikaalna  = business data, aam baat hai.
#   LinkedIn se banda ka profile/email nikaalna   = personal data, risk hai.
# Isliye poora LEAD_GENERATION block nahi kiya (wo store ka sabse bada paid
# bazaar hai). Sirf wo niches block hain jinka TARGET hi insaan hai.
PERSONAL_DATA = {
    "linkedin", "xing", "email", "emails", "phone", "phones", "people", "person",
    "resume", "cv", "recruiter", "candidate", "dating", "tinder", "bumble",
    "whatsapp", "contact", "contacts", "lead", "leads", "prospect",
    # naam se hi pata chalta hai -- ye log-dhoondhne wale platforms hain
    "skiptrace", "zoominfo", "rocketreach", "apollo", "signalhire", "snov",
    "truepeoplesearch", "whitepages", "spokeo", "usphonebook", "beenverified",
}

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(actor):
    title = (actor.get("title") or actor.get("name") or "").lower()
    return [w for w in _WORD.findall(title) if w not in GENERIC and len(w) > 1]


def niche_key(actor):
    """Actor ka title -> ek CANDIDATE SEARCH TERM (2 shabd).

    'Google Maps Reviews Scraper' -> 'google maps'
    'Taobao SKU Scraper'          -> 'taobao'

    ZAROORI: ye sirf candidate hai, sach nahi. Title se niche guess karne ke
    3 tareeke try kiye -- 2-shabd, pehla-shabd, sabse-aam-shabd -- teeno ne
    kachra diya ('welcome', 'uk', 'text' niche ban gaye the).

    Isliye ab grading is guess pe NAHI hoti. Ye term Apify ki apni search me
    daala jaata hai (verify.py wala step), aur muqabla wahan se aata hai --
    kyunki wahi buyer ko dikhta hai.
    """
    words = _tokens(actor)
    if not words:
        return ""
    return " ".join(words[:2])


def _age_days(iso):
    if not iso:
        return 9999
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return 9999


def build_niches(actors):
    """actors list -> { niche: {...aggregated...} }"""
    groups = {}
    for a in actors:
        k = niche_key(a)
        if not k:
            continue
        groups.setdefault(k, []).append(a)

    niches = {}
    for k, members in groups.items():
        members.sort(key=lambda a: a["stats"].get("totalUsers", 0), reverse=True)
        leader = members[0]
        d30 = sum(a["stats"].get("totalUsers30Days", 0) for a in members)
        d7 = sum(a["stats"].get("totalUsers7Days", 0) for a in members)
        paid = [a for a in members
                if (a.get("currentPricingInfo") or {}).get("pricingModel") == "PAY_PER_EVENT"]

        niches[k] = {
            # top 3 = jo buyer ko search me sabse upar dikhenge = asli muqabla
            "rivals": [(a.get("title", ""), a["stats"].get("totalUsers", 0),
                        a["stats"].get("totalUsers30Days", 0)) for a in members[:3]],
            "niche": k,
            "actors": len(members),
            "demand30": d30,
            "demand7": d7,
            "momentum": (d7 * 4 / d30) if d30 else 0,
            "paid_share": len(paid) / len(members),
            "leader_title": leader.get("title", ""),
            "leader_url": leader.get("url", ""),
            "leader_users": leader["stats"].get("totalUsers", 0),
            "leader_rating": leader.get("actorReviewRating") or 0,
            "leader_reviews": leader.get("actorReviewCount") or 0,
            "leader_stale_days": _age_days(leader["stats"].get("lastRunStartedAt")),
            "personal": bool(set(k.split()) & PERSONAL_DATA),
        }
    return niches


def grade(n):
    """(grade, why) -- clip_bot/scanner.py wale grade() jaisa."""
    if n["personal"]:
        return "F", "personal data (legal risk) - plan me skip tay hua tha"

    if n["demand30"] < LOW_DEMAND:
        return "F", f"demand nahi ({n['demand30']} users/30din)"

    if n["paid_share"] < 0.5:
        return "F", f"is niche me log paise nahi de rahe ({int(n['paid_share']*100)}% paid)"

    hot = n["momentum"] > MOMENTUM_HOT
    tags = []
    if hot:
        tags.append("BADH raha hai")

    # Sabse achha: demand hai, aur jo #1 hai wo chhota hai
    if n["demand30"] >= MIN_DEMAND and n["leader_users"] < WEAK_LEADER:
        tags.append(f"leader sirf {n['leader_users']} users")
        return "A+", " | ".join(tags) or "khaali jagah"

    if n["demand30"] >= LOW_DEMAND and n["leader_users"] < SOFT_LEADER:
        tags.append(f"leader {n['leader_users']} users (thoda bada)")
        return "A", " | ".join(tags)

    # Leader bada hai par tuta/nakaam hai -> replace karne ka mauka
    rot = []
    if n["leader_stale_days"] > STALE_DAYS:
        rot.append(f"leader {n['leader_stale_days']} din se nahi chala")
    if n["leader_reviews"] >= 3 and n["leader_rating"] < BAD_RATING:
        rot.append(f"leader rating {n['leader_rating']:.1f}")
    if rot and n["demand30"] >= MIN_DEMAND:
        return "B", " | ".join(tags + rot)

    return "C", f"leader strong ({n['leader_users']} users) - seedha muqabla mat kar"


def verify_grade(v):
    """Grade SIRF Apify ki apni search ke numbers pe.

    v = search_niche() ka result. Yahan 'leader' wo hai jo buyer ko sabse upar
    dikhta hai -- meri clustering ka andaza nahi.
    """
    if v["personal"]:
        return "F", "personal data (legal risk)"
    if v["results"] == 0:
        return "F", "search me kuch nahi -- term hi galat hai"
    if v["demand30"] < LOW_DEMAND:
        return "F", f"search me demand nahi ({v['demand30']} users/30din)"
    if v["paid_share"] < 0.5:
        return "F", f"log paise nahi de rahe ({int(v['paid_share']*100)}% paid)"

    tags = []
    if v["momentum"] > MOMENTUM_HOT:
        tags.append("BADH raha hai")

    if v["demand30"] >= MIN_DEMAND and v["leader_users"] < WEAK_LEADER:
        tags.append(f"search me #1 sirf {v['leader_users']} users ka")
        return "A+", " | ".join(tags)

    if v["demand30"] >= LOW_DEMAND and v["leader_users"] < SOFT_LEADER:
        tags.append(f"search me #1 {v['leader_users']} users (thoda bada)")
        return "A", " | ".join(tags)

    rot = []
    if v["leader_stale_days"] > STALE_DAYS:
        rot.append(f"#1 {v['leader_stale_days']} din se nahi chala")
    if v["leader_reviews"] >= 3 and v["leader_rating"] < BAD_RATING:
        rot.append(f"#1 ki rating {v['leader_rating']:.1f}")
    if rot and v["demand30"] >= MIN_DEMAND:
        return "B", " | ".join(tags + rot)

    return "C", f"search me #1 strong hai ({v['leader_users']} users)"


def is_personal(term):
    return bool(set(term.split()) & PERSONAL_DATA)


GRADE_ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3, "F": 4}
