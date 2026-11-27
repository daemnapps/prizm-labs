#!/usr/bin/env python3
"""trybe_tag — the Trybe rule for an ad built from a creator's Trybe video (2026-11-15).

Trybe pays the creator and credits the sale only when BOTH hold:
  1. the ad's destination link carries  trybe=<trybe_id>
  2. the ad's name ENDS with the trybe_id

trybe_id is the 8 hex characters Trybe quotes for a submission (the last 8 of its uuid).
funnel-tracking reads the id back off the last 8 characters of the ad name
(components/funnel-tracking/machine/trybe.py: `right(ad_name, 8)` and `[0-9a-f]{8}$`).

The Meta ad name for a tagged card is the system's own name plus one tail:

    <brand>_<product>_<brief>_<batch>_<funnel>_trybe-<trybe_id>

`trybe-` keeps the name in the slug alphabet the naming standard uses; the name still
ends with the id. A card with no trybe_id is named and linked exactly as before.

No brand is named here. Nothing here reaches Meta or Trybe.
"""
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ID = re.compile(r"^[0-9a-f]{8}$")
TAIL = "_trybe-"
_ENDS = re.compile(r"^(?P<name>.+)" + re.escape(TAIL) + r"(?P<id>[0-9a-f]{8})$")


def clean(trybe_id):
    """The id as Trybe quotes it (8 lowercase hex), or ValueError. None/"" -> None."""
    if trybe_id in (None, ""):
        return None
    t = str(trybe_id).strip().lower()
    if not ID.match(t):
        raise ValueError(f"not a trybe_id (8 hex characters): {trybe_id!r}")
    return t


def meta_name(name, trybe_id):
    """The Meta ad name: `name` with the Trybe tail when the card has a trybe_id."""
    t = clean(trybe_id)
    if not t:
        return name
    if split(name)[1] == t:
        return name
    return f"{name}{TAIL}{t}"


def split(name):
    """(the name without its Trybe tail, the trybe_id) — (name, None) for an untagged name."""
    m = _ENDS.match(str(name or ""))
    return (m.group("name"), m.group("id")) if m else (name, None)


def link(url, trybe_id):
    """The destination link with trybe=<trybe_id> in its query (any other trybe= replaced)."""
    t = clean(trybe_id)
    if not t or not url:
        return url
    u = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k != "trybe"] + [("trybe", t)]
    return urlunparse(u._replace(query=urlencode(q, safe="{}")))


def tagged(meta_ad_name, url):
    """[] when a (name, link) pair obeys the rule for the id at the end of the name, else what is wrong."""
    _, t = split(meta_ad_name)
    if not t:
        return ["the ad name does not end with _trybe-<trybe_id>"]
    got = dict(parse_qsl(urlparse(url or "").query)).get("trybe")
    return [] if got == t else [f"the link carries trybe={got!r}, the name ends with {t}"]
