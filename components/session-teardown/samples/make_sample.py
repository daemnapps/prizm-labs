#!/usr/bin/env python3
"""Rebuild samples/basic/ — a RECORDED SAMPLE, made up, for building and testing without live data.

A fictional brand "sample" with one funnel: a quiz page and an offer page. 900 visits over 14 days. On the offer
page most visitors who leave never scroll past the price block and tap the reviews link instead; most who reach
checkout scroll far and tap the main button. The reviews link leads nowhere, so some taps on it do nothing.
Deterministic (seeds 7 and 11): the same files every time.
    python3 samples/make_sample.py
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "basic"
BRAND, PLACE = "sample", "body-cpk"
QUIZ, OFFER = "%s_%s_quiz" % (BRAND, PLACE), "%s_%s_landing" % (BRAND, PLACE)
HOST = "https://funnel.example.com/body-cpk"

# The offer page as captured text (page-teardown's capture format), so the sample run can read it into sections.
# Made up. Laid out so the offer box sits deep on the page, where the made-up visitors who leave never reach.
OFFER_PAGE = """URL: %s/landing/
TITLE: Your 3-step body routine

[HEADER] [LINK: Sample -> /]
# Smooth skin by Sunday, without scrubbing harder
## The routine your quiz answers point to: three minutes in the shower, three times a week
[IMAGE alt=Before and after on an upper arm · arm.jpg]
Rough, bumpy skin on the arms and legs is common. It is not dirt and it is not something you did wrong. Dead skin
builds up around each hair and hardens into a small bump, and scrubbing harder only makes it angry. What clears it
is a gentle routine that loosens the build-up, lifts it away and keeps the skin soft so it does not come back.
[LINK: See reviews -> #reviews]
> "Three weeks in and my arms are smooth. I stopped hiding them." — a customer
## What is inside: 5 ingredients, nothing else
[BUTTON: Read the 5 ingredients]
- A fine natural grain that lifts dead skin without scratching
- A gentle fruit acid that loosens the build-up around each hair
- A plant oil that keeps skin soft after rinsing
- A calming leaf extract for skin that reacts
- A light butter that seals in water
Every ingredient is listed on the tube, and none of them is a fragrance added for smell.
[IMAGE alt=The five ingredients laid out · ingredients.jpg]
## How to use it
1. In the shower, on wet skin, take a spoonful.
2. Massage in small circles for thirty seconds on each rough area.
3. Rinse, pat dry, and leave the skin alone. Three times a week is enough.
Most people feel a difference after the first use and see one in two to three weeks.
[IMAGE alt=The routine step by step · steps.jpg]
## Choose your routine
- 1 tube — $29 — about a month
- 3 tubes — $57 — about three months, most chosen
- 6 tubes — $86 — about six months
Free shipping on 3 tubes or more.
[BUTTON: Get mine — 3 tubes]
[IMAGE alt=Three tubes · tubes.jpg]
## Our promise
Use it for 60 days. If your skin is not smoother, write to us and we refund every cent, no return needed.
## Questions
- Will it work on my legs? Yes, anywhere the skin is rough and bumpy.
- Does it sting? The acid is mild; if your skin reacts, use it twice a week instead of three.
- How long does a tube last? About a month at three times a week.
[FOOTER] [LINK: Contact -> /contact]
""" % HOST


def main():
    rnd = random.Random(7)
    rnd2 = random.Random(11)
    t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
    views, outcomes, recs, events = [], [], {}, {}
    for i in range(900):
        s = "s%04d" % i
        start = t0 + timedelta(minutes=rnd.randrange(14 * 24 * 60))
        t = start
        ev = []

        def add(event, url="", text="", scroll=None, dt=0):
            nonlocal t
            t = t + timedelta(seconds=dt)
            ev.append({"at": t.isoformat(), "event": event, "url": url, "text": text, "scroll": scroll, "tag": ""})

        views.append({"session": s, "page_id": QUIZ, "step": "landing", "at": t.isoformat(), "brand": BRAND})
        add("$pageview", HOST + "/quiz/")
        add("$autocapture", text="Rough, bumpy skin", dt=rnd.randint(4, 12))
        add("$autocapture", text="See my routine", dt=rnd.randint(3, 9))
        if rnd.random() < 0.15:          # some leave at the quiz
            add("$pageleave", HOST + "/quiz/", scroll=rnd.randint(20, 60), dt=rnd.randint(2, 8))
            recs[s] = {"duration_s": 30, "active_s": rnd.randint(6, 20), "clicks": 2, "start_url": HOST + "/quiz/", "start": start.isoformat()}
            events[s] = ev
            continue
        add("$pageview", HOST + "/landing/", dt=2)
        views.append({"session": s, "page_id": OFFER, "step": "landing", "at": t.isoformat(), "brand": BRAND})
        converts = rnd.random() < 0.22
        if converts:
            add("$autocapture", text="Read the 5 ingredients", dt=rnd.randint(8, 20))
            if rnd.random() < 0.1:
                add("$autocapture", text="See reviews", dt=rnd.randint(3, 8))
            add("$pageleave", HOST + "/landing/", scroll=rnd.randint(70, 100), dt=rnd.randint(10, 40))
            add("$autocapture", text="Get mine — 3 tubes", dt=1)
            add("checkout_click", HOST + "/landing/", dt=0)
            add("$pageview", HOST + "/checkout/", dt=2)
            add("checkout_reached", HOST + "/checkout/", dt=0)
            outcomes.append({"session": s, "event": "checkout_reached", "revenue": 0, "at": t.isoformat(), "brand": BRAND})
            if rnd.random() < 0.45:
                add("purchase", HOST + "/receipt/", dt=rnd.randint(40, 120))
                outcomes.append({"session": s, "event": "purchase", "revenue": rnd.choice([29, 57, 57, 86]), "at": t.isoformat(), "brand": BRAND})
        else:
            if rnd.random() < 0.65:
                add("$autocapture", text="See reviews", dt=rnd.randint(5, 15))
                if rnd2.random() < 0.6:  # the reviews link jumps to nothing: a dead tap (seed 11, so no other number moves)
                    add("$dead_click", text="See reviews", dt=1)
                if rnd.random() < 0.5:
                    add("$rageclick", text="$57", dt=rnd.randint(2, 6))
                add("$pageleave", HOST + "/landing/", scroll=rnd.randint(15, 38), dt=rnd.randint(5, 20))
            else:
                add("$autocapture", text="Read the 5 ingredients", dt=rnd.randint(5, 15))
                add("$pageleave", HOST + "/landing/", scroll=rnd.randint(40, 75), dt=rnd.randint(10, 30))
        if rnd.random() < 0.8:           # not every visit was recorded
            recs[s] = {"duration_s": int((t - start).total_seconds()) + 5, "active_s": rnd.randint(4, 90),
                       "clicks": sum(1 for e in ev if e["event"] in ("$autocapture", "$rageclick")),
                       "start_url": HOST + "/quiz/", "start": start.isoformat()}
        events[s] = ev
    pages = {"pages": {}}
    for pid, page, kind in ((QUIZ, "quiz", "quiz"), (OFFER, "landing", "offer")):
        pages["pages"][pid] = {"brand": BRAND, "place": PLACE, "page": page, "step": "landing", "kind": kind,
                               "url": "%s/%s/" % (HOST, page), "product": "body-scrub", "status": "draft", "state": "live",
                               "versions": [{"version": "v1", "control": True, "url": "%s/%s/" % (HOST, page), "offer": "1"}],
                               "tests": []}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pages").mkdir(exist_ok=True)
    (OUT / "pages" / (OFFER + ".txt")).write_text(OFFER_PAGE)
    for name, data in (("page_views", views), ("outcomes", outcomes), ("recordings", recs), ("events", events), ("pages", pages)):
        (OUT / (name + ".json")).write_text(json.dumps(data, indent=0))
    print("samples/basic: %d views, %d outcomes, %d recordings" % (len(views), len(outcomes), len(recs)))


if __name__ == "__main__":
    main()
