# Eventbrite Events Scraper

Scrape Eventbrite events by **city** or **category** — no proxy, no login, no browser.

Give it a location (or a full Eventbrite search URL) and it returns clean event rows:
name, dates, venue with address and coordinates, organizer ID, ticket link and category tags.

## Input

| Field | Example | Notes |
|---|---|---|
| `locations` | `["india--mumbai", "united-states--new-york"]` | The slug from the Eventbrite URL: `eventbrite.com/d/<slug>/all-events/` |
| `category` | `music` | `all-events` (default), `music`, `business`, `food-and-drink`, … |
| `startUrls` | `["https://www.eventbrite.com/d/…/all-events/"]` | Advanced — paste full search URLs instead of locations |
| `maxItems` | `100` | Stop after this many events. **You are charged per event returned.** |
| `maxPagesPerSearch` | `20` | Safety cap — a big city has 49+ pages |

## Output

One record per event:

```json
{
  "id": "1987890717649",
  "name": "ASIASec 2026 | Anti-Counterfeit, Illicit Trade & Brand Protection",
  "url": "https://www.eventbrite.sg/e/asiasec-2026-...",
  "startDate": "2026-08-19", "startTime": "09:30",
  "endDate": "2026-08-20", "endTime": "19:00",
  "timezone": "Asia/Kolkata",
  "isOnlineEvent": false,
  "ticketsUrl": "https://www.eventbrite.com/checkout-external?eid=1987890717649",
  "organizerId": "34113777487",
  "tags": ["Environment & Sustainability", "Business & Professional"],
  "venueName": "Radisson Blu Mumbai International Airport",
  "venueCity": "Mumbai", "venueRegion": "MH", "venueCountry": "IN",
  "venueAddress": "Off Marol Maroshi Road, Mumbai, MH 400059",
  "venueLatitude": 19.1102222, "venueLongitude": 72.8786221
}
```

## How it works

Eventbrite embeds the full event JSON in each search page (`window.__SERVER_DATA__`),
so a plain HTTP request is enough — no headless browser, no residential proxy.
That keeps runs cheap and fast.

## Notes

- Pagination and de-duplication are handled automatically, across every location
  and start URL in a single run — you are never charged twice for the same event.
- If Eventbrite changes its page structure the run fails loudly rather than
  returning empty data — a daily health test catches this early.
