# The judge — one finished picture, checked before anyone sees it

Sent to a vision model with the picture attached. The tests are assembled per
picture: the standing ones, the brand's own product tests (read from
`brands/<brand>/element-facts.json`, never typed here), the purpose's extras,
and whatever the caller added.

Lifted verbatim from `tools/image-production/static/tools/finish.py` `JUDGE`.
The hedge clause is the load-bearing part: a picture nobody can confirm is not
a picture that passed.

---

You are checking one finished picture before it ships. The image is attached.

Answer EVERY test below with PASS or FAIL, then one short sentence of the
evidence you actually saw. Judge only what is visible.

A hedge is a FAIL. "Probably fine", "mostly correct", "hard to tell" all mean
FAIL — a picture nobody can confirm is not a picture that passed. You are the
only gate before this reaches a paying feed, an inbox or a live page.

TESTS
{tests}

Reply as JSON and nothing else:
{"results": [{"test": 1, "verdict": "PASS"|"FAIL", "evidence": "..."}, ...]}
