# Brief manifest — v1

*v1 (2026-09-24): the last check between a brief and AI production. the owner: "There needs to be a manifest at the end of every brief to make sure teardown record, and final brief has the core elements that literally make this ad work before we can go into ai production — i do not have time to babysit this anymore."*

You are checking one thing: **does the final brief still carry every element that makes the swipe work?** The swipe's replication spec names those elements — each with its MANDATE — and says what is LOAD-BEARING. You are not judging the words, the brand, the product or the quality. Our brand, product, names and prices are SUPPOSED to replace theirs, and an organic swipe is SUPPOSED to gain expansion beats (product, mechanism, objection, close) that it never had.

An element is **carried** when a scene of the brief (its words, its on-screen text, its pictures, its sound) does what the MANDATE asks, adapted to our brand. It is **missing** when no scene does it, or when the brief changed it so it no longer does its job (for example, the experts no longer disagree, or the receipt graphic lost its sound cue). An expansion beat placed after or around an element does not remove the element — judge whether the element itself is still there and still does its job.

Here are the swipe's core elements and what is load-bearing, from its replication spec: {spec}

Here is the final brief: {brief}

Answer with ONE JSON object and nothing else — no prose, no code fence:

{"elements": [{"id": "E1", "element": "<its name from the spec>", "mandate": "<the mandate, short>", "carried": true, "where": ["S1"], "how": "<quote the brief's own words or describe the scene that carries it>"}],
 "load_bearing": [{"id": "L1", "item": "<its name from the spec>", "carried": true, "where": ["S2", "S5"], "how": "<quote or describe>"}]}

- Number the spec's elements E1, E2, … in the spec's order and its load-bearing items L1, L2, … in its order. List every one — never skip one because it seems minor.
- `carried` is false when you cannot point at the scene that does it. Say why in `how`.
- Quote the brief; never assume. Being strict costs one question to the owner; being lenient costs an ad.
