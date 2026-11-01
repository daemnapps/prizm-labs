#!/usr/bin/env python3
"""Keep the posts that belong to this avatar's market.

A hashtag is global; an avatar is not. The first real pass on `#freshcut`
returned a 5.7M-view Berlin barber with comments in four languages — a genuine
barbershop post, and the wrong room.

This does not detect language properly and does not pretend to. It reads three
cheap signals and says which one fired, so a drop can always be argued with:

- non-Latin script in the caption
- a market-specific word in the caption or hashtags
- a hashtag naming another place

**Every drop is reported with its reason.** Nothing is silently discarded —
over-collecting and saying so beats quietly filtering the room down to what a
regex expected.
"""
import re

# Deliberately thin. A long word list is a guess dressed as a rule; these are
# only the signals that fired on real harvested data.
MARKETS = {
    "US": {
        "foreign_word": re.compile(
            r"\b(coiffeur|friseur|peluquer|barbeiro|parrucchier|фото|理髪|이발)\b", re.I),
        "foreign_tag": re.compile(
            r"(berlin|paris|madrid|milano|lisboa|deutschland|france|espana|"
            r"brasil|italia|nederland|polska|turkiye|dubai|london|toronto)", re.I),
    },
}
NON_LATIN = re.compile(r"[^\x00-\x7FÀ-ɏ -➿️\U0001F000-\U0001FAFF]")


def why_drop(post, market):
    m = MARKETS.get(market.upper())
    if not m:
        return None
    cap = post.get("caption") or ""
    tags = " ".join(post.get("hashtags") or [])
    if len(NON_LATIN.findall(cap)) > 3:
        return "caption is largely non-Latin script"
    if m["foreign_word"].search(cap):
        return f"caption carries a non-{market} word for barber"
    hit = m["foreign_tag"].search(tags + " " + cap)
    if hit:
        return f"tagged to another market ({hit.group(0)})"
    return None


def keep(posts, market):
    """-> (kept, [(post, why_dropped)])"""
    good, dropped = [], []
    for p in posts:
        w = why_drop(p, market)
        (dropped.append((p, w)) if w else good.append(p))
    return good, dropped
