#!/usr/bin/env python3
"""Is a send ready to be written? A free check, run before any writing is spent (LD-106 (readiness check),
email_lead's proposal card 6, 2026-11-04).

In the Nov 3-4 run emails were written and then held for things knowable beforehand: a product sold out, a price
not in the offer bank, missing research, a calendar send that changed. `check()` asks those questions first, for
one version of one send, and answers ready / not ready, naming what is missing:

- **stock, as a US shopper sees it**: `<site>/products/<handle>.js?country=US`, for the send's product and its
  offer's product (the handle is read off the bank's `- Link:` line, else the key itself). Sold out, or not on the
  store, is NOT READY. The store rate-limits, so every answer is cached
  (`runs/email-production/<brand>/readiness/stock-cache.json`, kept `TTL` seconds; a 429 is never cached) and live
  reads are paced. A store that will not answer is a note, never a stop: unknown is not sold out. A brand whose
  store publishes no Shopify feed is not read, and the line says so.
- **the price in the offer bank**: the offer this version carries (`brief.offer_for`) and the rest of the brand's
  mix must be offers `offers.refuse` accepts on the send's day, each with a price in the bank.
- **the moment's research and look**: a send on a moment key needs that moment's research for its avatar and a
  moment look in the brand's design system. Missing either is a NOTE FOR editor, never a stop (decision log
  2026-11-04, decision 3: that email is built in the brand's base look with a note for editor).
- **the calendar identity**: `calendar_handoff.inspect` on the send (date, hour, audience, buyer language for
  leads). A version already written whose calendar send changed since is a note: rewriting it is the fix.

No model, no key, no write outside its own cache. Brand-agnostic: every brand fact is read from `brands/<brand>/`.
The store read is a seam (`fetch(url) -> (status, text)`), so tests never touch the network.
"""
import datetime
import json
import re
import subprocess
import sys
import time

from paths import WORKSPACE, brand_runs
import brief
import calendar_handoff as CH
import offers as OFFERS

PACE = 5            # seconds between live store reads (design/check.py's pace for the same store)
RETRIES = 2         # a 429 is asked again after the store's named wait (at most 90 s), this many times
TTL = 2 * 3600      # a cached stock answer is trusted this long
CACHE = "stock-cache.json"


def _curl(url):
    """(HTTP status, body, Retry-After) for a GET; status 0 when the store could not be reached. Shells out to
    curl, as store.py does: this folder's `email.py` shadows the stdlib package urllib needs."""
    r = subprocess.run(["curl", "-sS", "--max-time", "20", "-H", "Accept-Language: en-US", "-D", "/dev/stderr",
                        "-w", "\n%{http_code}", url], capture_output=True, text=True)
    body, _, code = (r.stdout or "").rpartition("\n")
    after = re.search(r"(?im)^retry-after:\s*(\S+)", r.stderr or "")
    try:
        return int(code), body, after.group(1) if after else ""
    except ValueError:
        return 0, (r.stderr or "").strip()[-200:], ""


FETCH = _curl       # the seam: tests set their own


def _json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Stock:
    """Stock as a US shopper sees it, one answer per product per `TTL`, shared by every send in a batch."""

    def __init__(self, brand, fetch=None, pace=None, ttl=None, wait=None):
        self.brand = brand
        self.fetch = fetch or FETCH
        self.pace = PACE if pace is None else pace
        self.wait = wait or time.sleep
        self.unread = {}             # this batch's unanswered reads: never asked twice in one batch
        self.ttl = TTL if ttl is None else ttl
        machine = _json(WORKSPACE / "brands" / brand / "email-sms" / "machine.json", {}) or {}
        self.shopify = bool(machine.get("store_feed"))
        self.site = (machine.get("site") or "").rstrip("/")
        self.file = brand_runs(brand) / "readiness" / CACHE
        self.cache = _json(self.file, {}) or {}
        self._last = 0.0

    def _fresh(self, row):
        try:
            age = (datetime.datetime.now() - datetime.datetime.fromisoformat(row["read"])).total_seconds()
        except (KeyError, TypeError, ValueError):
            return False
        return 0 <= age <= self.ttl

    def _save(self):
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self.file.write_text(json.dumps(self.cache, indent=1, sort_keys=True) + "\n")
        except OSError:
            pass

    def _ask(self, url):
        got = tuple(self.fetch(url))
        return got if len(got) == 3 else (got[0], got[1], "")

    def read(self, handle):
        """{"state": in-stock | sold-out | not-on-store | unread | not-read, "why": ..., "url": ...}"""
        if not self.shopify or not self.site:
            return {"state": "not-read", "why": "this brand's store publishes no Shopify product feed"}
        url = "%s/products/%s.js?country=US" % (self.site, handle)
        row = self.cache.get(handle)
        if row and self._fresh(row):
            return row
        if handle in self.unread:
            return self.unread[handle]
        wait = self.pace - (time.time() - self._last)
        if wait > 0 and self._last:
            self.wait(wait)
        status, body, after = self._ask(url)
        for _ in range(RETRIES):
            if status != 429:
                break
            self.wait(min(int(after) if str(after).isdigit() else 60, 90))
            status, body, after = self._ask(url)
        self._last = time.time()
        if status == 200:
            try:
                d = json.loads(body)
                live = bool(d.get("available")) or any(v.get("available") for v in d.get("variants") or [])
                row = {"state": "in-stock" if live else "sold-out", "url": url, "read": _now()}
            except (ValueError, AttributeError):
                row = {"state": "unread", "why": "the store's answer was not readable", "url": url}
                self.unread[handle] = row
                return row
        elif status == 404:
            row = {"state": "not-on-store", "url": url, "read": _now()}
        else:
            row = {"state": "unread", "url": url,
                   "why": "the store answered %s" % status if status else "the store could not be reached"}
            self.unread[handle] = row
            return row
        self.cache[handle] = row
        self._save()
        return row


def _bank(brand):
    try:
        return {r["key"]: r for r in OFFERS.parse(brand)}
    except Exception:                       # noqa: BLE001 -- an unreadable bank is named by the offer check
        return {}


def _handle(key, bank):
    m = re.search(r"/products/([^/?#\s]+)", (bank.get(key) or {}).get("url") or "")
    return m.group(1) if m else key


def _offer_problems(slot, brand, avatar, bank):
    out = []
    eff = brief.offer_for(slot, brand, avatar)
    keys = [eff] if eff and eff != "none" else []
    if keys:
        keys += [k for k in slot.get("offer_mix") or [] if k not in keys and k != "none"]
    mix = slot.get("offer_mix") or []
    for key in keys:
        why = OFFERS.refuse(brand, key, avatar=None if key in mix else avatar, on=slot.get("date"))
        if why:
            out.append("offer bank: " + why.replace("`", ""))
            continue
        row = bank.get(key) or {}
        if not (row.get("price") or row.get("states_prices") or row.get("subs")):
            out.append("offer bank: no price for %s in the offer bank" % key)
    return keys, out


def moment_of(slot):
    """The moment key a send sits on, or None: the same reading as design/line.py `moment_of` (a key, never the
    calendar's prose occasions)."""
    occ = (slot.get("occasion") or "").split(":")[0].strip()
    if not occ or occ in ("none", "affiliate"):
        return None
    return occ if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", occ) else None


def _avatar_folder(brand, avatar):
    """The avatar's folder as the brand keeps it, from a profile id, a new name or an old name (naming/PEOPLE.md)."""
    try:
        import importlib.util
        from pathlib import Path
        f = next(d / "naming" / "people.py" for d in Path(__file__).resolve().parents if d.name == "components")
        spec = importlib.util.spec_from_file_location("naming_people", f)
        people = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(people)
        return people.folders(brand, avatar)[0] or avatar
    except Exception:                                  # noqa: BLE001  without the door the name stands as given
        return avatar


def _moment_notes(slot, brand, avatar):
    moment = moment_of(slot)
    if not moment:
        return []
    notes = []
    bdir = WORKSPACE / "brands" / brand
    who = avatar if avatar and avatar not in ("mixed", "none") else None
    if who:
        folder = _avatar_folder(brand, who)
        places = [bdir / "core-avatars" / folder / "moments" / (moment + ".md"),
                  bdir / "core-avatars" / folder / "moments" / (moment + ".research.md"),
                  WORKSPACE / "runs" / "moment-research" / brand / who / (moment + ".md"),
                  WORKSPACE / "runs" / "moment-research" / brand / who / (moment + ".research.md")]
        if not any(p.is_file() for p in places):
            notes.append("for editor: no research on file for the moment %s for %s yet "
                         "(runs/moment-research/%s/%s/%s.research.md); it is laid out from the copy"
                         % (moment, who, brand, who, moment))
    themes = (_json(bdir / "email-sms" / "design-system.json", {}) or {}).get("themes") or {}
    if moment not in themes:
        notes.append("for editor: no look for the moment %s yet; built in the brand's own look" % moment)
    return notes


def _calendar(slot, brand, avatar, label, calendar):
    missing, notes = [], []
    if calendar:
        audit = CH.inspect(WORKSPACE, brand, WORKSPACE / "runs" / "email-production" / brand / "_unwritten",
                           slot=slot, state={"assignment": {"avatar": avatar, "offer": slot.get("offer")}})   # nothing written yet
        missing += [p if p.startswith("calendar") else "calendar handoff: " + p for p in audit["problems"]]
    run = WORKSPACE / "runs" / "email-production" / brand / label
    state = _json(run / "run.json")
    if state and not missing:
        audit = CH.inspect(WORKSPACE, brand, run, slot=slot, state=state)
        changed = [p for p in audit["problems"] if "since writing" in p or "not a current calendar" in p]
        if changed:
            notes.append("written before; " + "; ".join(changed) + " (this run rewrites it)")
    return missing, notes


def check(slot, brand, avatar=None, label=None, stock=None, calendar=True):
    """One version of one send: {"label", "slot", "ready", "missing": [...], "notes": [...]}.
    `calendar=False` when the caller has already bound the calendar contract (run_month's chain_argv did)."""
    label = label or slot.get("id")
    stock = stock or Stock(brand)
    bank = _bank(brand)
    missing, notes = _calendar(slot, brand, avatar, label, calendar)
    keys, offer_missing = _offer_problems(slot, brand, avatar, bank)
    missing += offer_missing
    products = []
    if slot.get("product") and slot["product"] != "none":
        products.append(slot["product"])
    products += [k for k in keys if k not in products and (bank.get(k) or {}).get("url")]
    for key in products:
        handle = _handle(key, bank)
        got = stock.read(handle)
        if got["state"] == "sold-out":
            missing.append("stock: %s is sold out as a US shopper sees it (%s)" % (key, got.get("url")))
        elif got["state"] == "not-on-store":
            missing.append("stock: %s is not on the store as a US shopper sees it (%s)" % (key, got.get("url")))
        elif got["state"] == "unread":
            notes.append("stock of %s unread: %s" % (key, got.get("why")))
        elif got["state"] == "not-read":
            notes.append("stock not read: " + got["why"])
    notes += _moment_notes(slot, brand, avatar)
    return {"label": label, "slot": slot.get("id"), "ready": not missing,
            "missing": missing, "notes": list(dict.fromkeys(notes))}


def line(r):
    """ready      <label>[  (note; note)]   or   NOT READY  <label>  because a; b"""
    if r["ready"]:
        return "ready      %s" % r["label"] + ("  (%s)" % "; ".join(r["notes"]) if r["notes"] else "")
    return "NOT READY  %s  because %s" % (r["label"], "; ".join(r["missing"]))


if __name__ == "__main__":
    sys.exit("run it through run_month.py <calendar month> --readiness: it lists every send, nothing spent")
