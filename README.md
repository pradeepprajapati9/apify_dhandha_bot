# apify_dhandha_bot

Apify Store pe paid Actors banane ka dhandha. Ye repo **Step 1** hai.

## Idea kya hai

[apify.com](https://apify.com/store) ek "scraper ki dukaan" hai. Log wahan aate hain
ek zarurat leke — *"mujhe Delhi ke 5000 restaurants ka phone number chahiye"* — search
karte hain, koi ready-made tool (**Actor**) milta hai, chala lete hain, data Excel me
aa jaata hai.

Wo Actor kisi ne banaya hota hai. Jab koi use chalata hai, wo Apify ko paisa deta hai.
**Apify usme se 80% Actor banane wale ko deta hai**, 20% khud rakhta hai. Rate aam
taur pe $1–$10 per 1,000 rows.

**Isme khaas kya hai:** YouTube pe pehle subscriber banane padte hain, blog pe pehle
traffic. Yahan **buyer pehle se maujood hai** aur paise dene ko taiyaar hai. Kisi ko
jodna nahi, kisi ko convince nahi karna. Bas tera tool wahan **mil jaana** chahiye jab
wo search kare.

## To dikkat kya hai

Store me **38,000+ Actors** pehle se pade hain. Agar tu "Google Maps Scraper" banayega,
to wahan pehle se ek hai jiske **5 lakh users** hain. Tera koi nahi kholega.

Ye winner-take-most bazaar hai — zyadatar Actors kuch nahi kamate.

**Isliye pehla kaam Actor banana NAHI hai. Pehla kaam khaali jagah dhoondhna hai.**

## Ye repo kya karta hai

`store_scanner.py` — poore store ka data kheench ke batata hai **kaun si jagah khaali hai**.

Ye **do step** me chalta hai, aur doosra step hi asli hai:

**Step 1 — candidate dhoondho.** 30,000+ actors ke titles se `niche` guess karo
(`Taobao SKU Scraper` → `taobao`). Ye **sirf andaza** hai.

**Step 2 — Apify ki apni search se verify karo.** Har top candidate ko
`search=` API me daalo aur dekho **buyer ko sach me kya dikhta hai**.
Grading yahan hoti hai, step 1 pe nahi.

Kyun? Kyunki step 1 ka andaza **jhooth bolta hai**. Asli misaal:

| niche | clustering ne kaha | search ne dikhaya | nateeja |
|---|---|---|---|
| `xiaohongshu` | #1 ke 198 users | **1,461 users** | A+ → B |
| `reddit reply` | #1 ke 392 users | **1,138 users** | A+ → C |
| `douyin` | — | **1,665 users** | B |

Verify ke baad har niche pe teen sawaal:

| Sawaal | Kaise nape |
|---|---|
| **Demand hai?** | search ke top-10 me pichhle 30 din ke users |
| **Jo #1 hai wo kamzor hai?** | search ke #1 actor ke total users < 500 |
| **Log paise de rahe hain?** | `PAY_PER_EVENT` pricing |

Teeno HAAN = `A+`. #1 bada hai par tuta pada hai / rating kharab = `B` (replace karne ka mauka).

## Chalao

```bash
pip install -r requirements.txt

python store_scanner.py            # cache se (24 ghante purana chalega)
python store_scanner.py --fresh    # taaza data kheencho
```

Output: `gaps.txt` (ranked list) + `dashboard.html` (double-click kholo).

### Sabse zaroori command

```bash
python store_scanner.py --check "bluesky"
```

Ye wahi search dikhata hai **jo asli buyer ko dikhti hai**.

## Scanner pe andha bharosa mat karna

Scanner **shortlist** deta hai, **faisla nahi**.

Agar kisi niche me leader ke sirf 200 users hain, iske **do** matlab ho sakte hain:

- **(a)** jagah khaali hai — mauka hai, **ya**
- **(b)** us data ki demand hi nahi hai — isiliye koi nahi aaya

**Ye farq scanner nahi bata sakta.** Isliye Actor banane se pehle top 3 niches
`--check` se dekho, leader ka page kholo, uske reviews padho.

## Do imaandaar baatein

1. **Ye passive income nahi hai, dhandha hai.** Jis site ka data nikaalte ho wo apna
   HTML badlegi, Actor fail hoga. Apify roz auto-test karta hai — **3 din lagatar fail =
   store me neeche dhakel diya jaayega.** Maintenance hameshaa teri.

2. **Personal data se door.** Apify ke terms me saaf likha hai ki community Actors ki
   legal zimmedari **100% developer ki** hai. `rules.py` un niches ko `F` grade deta hai
   jinka target hi insaan hai (LinkedIn, email harvesting, people-search).
   Business ka data (Google Maps se dukaan ka phone) alag cheez hai — wo allowed hai.

## Scanner ki apni haddein

- Apify ka API `offset=16000` ke baad **kuch nahi deta**, jabki store me 38k+ Actors hain.
  Isliye category-wise kheenchte hain (23 categories) aur `id` se dedupe karte hain.
  Jo phir bhi chhoot jaata hai wo run ke waqt **print** hota hai — chupaya nahi jaata.
  (Abhi sirf AUTOMATION ki ~4,600 sabse kam-popular tail chhoot rahi hai.)
- Sirf **top 60 candidates** search se verify hote hain (`VERIFY_TOP`). Baaki
  bina verify ke `gaps.txt` me aate hi nahi — kyunki bina verify ke number jhoothe hote hain.
- Candidate ke naam abhi bhi kabhi-kabhi bakwas hote hain (`google 15`, `redirect audit`)
  kyunki wo title se guess hote hain. Unke **numbers** phir bhi sahi hain (search se aaye hain),
  bas naam ajeeb hai.

## Aage kya

1. ✅ Scanner — khaali jagah dhoondho *(ye repo)*
2. ⬜ Us jagah ka Actor banao, Apify pe daalo (koi approval nahi, turant live)
3. ⬜ Daily health check — Actor toota to pehle **hum** pakdein, Apify se pehle
4. ⬜ 3–5 Actors ka portfolio (power law: ek chalega, chaar nahi)

**Paisa, sach me:** pehle 2–3 mahine ~₹0. Pehla dollar realistic 2–4 mahine me.
Achhi jagah mili to $100–400/mahina. Apify ke top creators $10k+/mo kamate hain —
wo top 1% hai, **baseline nahi**.
