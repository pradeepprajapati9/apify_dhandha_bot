# LinkedIn post

Short version. LinkedIn kills reach on posts with outbound links, so the link
goes in the FIRST COMMENT, not the post body. (Post the comment yourself,
immediately after publishing.)

---

## Post body

Eventbrite has no free search API. So most people reach for Selenium — a headless
browser, 4 seconds a page, fighting the DOM.

Turns out you don't need any of it.

Eventbrite server-renders the entire event list as JSON into every search page,
in a `window.__SERVER_DATA__` block. One plain HTTP request and you have it:
names, dates, venue addresses, coordinates, organizer IDs, ticket links, tags.

No browser. No proxy. No API key. About a second per page.

Three things that bit me while building it properly:

→ Paste a URL that already has "?page=2" and blindly append "&page=3", and
  Eventbrite honours the first one. You re-fetch the same page, every ID looks
  like a duplicate, and your crawler decides it's finished. Silently.

→ Online events appear in every city's results. Dedupe across the whole run,
  not per search, or you'll emit the same event five times.

→ The same code works from my laptop and returns 405 from a GitHub Actions
  runner. If your scraper "breaks" only in CI, check the IP before you debug
  the parser.

I wrote up the full approach with working code — link in the comments.

#python #webscraping #dataengineering

---

## First comment (post this right after)

Full write-up with the code: [dev.to link]

And if you'd rather not maintain it, I run it as a hosted tool here:
https://apify.com/dhandhabot_9953/eventbrite-events-scraper
