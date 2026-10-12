#!/usr/bin/env python3
"""creators — the creator manager as one command: pick, hand off, track.

    creators.py pick    --brand <b> --brief <id> [--lane creator|ai] [--ask ask.json] [--into <creator-manager folder>]
    creators.py handoff --brand <b> --brief <id> --creator <card id> [--staging DIR] [--ids ids.json] [--offline]
    creators.py track   [--brand <b>] [--staging DIR ...] [--no-take-back] [--out status.json]

PICK reads what the brief asks for — avatar and sub-avatar, gender, age band,
look, language, lane — from the brief register, the brief itself, its
teardown record and the avatar files, and scores every talent card of the
brand against it (`brands/<brand>/ai-elements/characters/casting/cards-v6.json`,
checked by `components/casting/casting/cards.py` before it is read). The
ranking comes back top pick first, every point with its reason. Who may be
cast at all:
  - creator lane (a real person films it): real creators on a card only;
  - ai lane: AI characters that are current with a casting sheet — made from
    existing assets and customer information — and never a retired id;
  - the protagonist is a ugc / customer / founder card, never an authority
    or interviewer, unless the ask says otherwise.

HANDOFF writes the creator's folder with the hand-off tool itself
(`handoff.py`, role `creator`) — the same gather, checks, folder and ledger —
then adds who it is for: `references/creator.json` (the card),
`references/message-draft.md` (the words to send, DRAFT, NOT SENT) and
`creator` in manifest.json. Nothing is sent and nothing is shared: messaging
a creator, and putting the folder on Drive for her, is the owner's go.

TRACK scans every creator hand-off on disk and on the Drive mount, says which
are waiting and which have footage back, runs `handoff.py take-back creator`
on every folder whose returned/ has files the ledger has not recorded yet,
and writes one status file.
"""
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import handoff as H  # noqa: E402  (the hand-off tool; reused, never rebuilt)

WS = H.WS
N, BR = H.N, H.BR
sys.path.insert(0, str(WS / "components/casting"))
from casting import cards as CARDS  # noqa: E402  (the talent-card schema check)

PRINT_RUN_STAGING = WS / "lab/print-run/handoffs"
IDS_DIR = PRINT_RUN_STAGING / "_ids"
TEARDOWN_RECORDS = WS / "platform/data/records/teardown-runs"
VIDEO_RUNS = WS / "runs/video-teardown"
PROTAGONIST_ROLES = {"ugc", "customer", "founder"}
MEDIA = {".mp4", ".mov", ".m4v", ".avi", ".jpg", ".jpeg", ".png", ".heic", ".webp", ".wav", ".mp3", ".m4a", ".aiff"}
NOT_WORK = {"README.md", "index.json", ".DS_Store"}
BAND = {"18-24": (18, 24), "25-34": (25, 34), "35-44": (35, 44), "45-54": (45, 54),
        "55-64": (55, 64), "65-plus": (65, 85)}
# look words, by what they mean: the brief's words on one side, the card's on the other
LOOK = {
    "grey hair": r"gr[ae]y|silver|salt-and-pepper|white hair",
    "curly hair": r"\bcurl|curly|ringlet",
    "blonde hair": r"blonde?",
    "dark hair": r"dark hair|brunette|black hair",
    "short hair": r"\bshort\b|\bbob\b|pixie",
    "long hair": r"\blong\b",
    "freckles": r"freckl",
    "visible spots": r"\bspots\b|age spots|sun spots|sun damage|brown spots",
    "real, unretouched skin": r"unretouched|not retouched|real skin|real texture",
    "glasses": r"(?<!sun)glasses",
}
W = {"avatar": 25, "sub_avatar": 10, "age": 30, "gender": 15, "look": 15, "language": 5, "ethnic": 10, "own_post": 10}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def alnum(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


# ---- the cards --------------------------------------------------------------
def cards_file(brand):
    return WS / "brands" / brand / "ai-elements/characters/casting/cards-v6.json"


def load_cards(brand, path=None):
    """(cards, retired ids). The file is checked by the talent-card schema
    first; a file that fails is refused, never read around."""
    f = Path(path or cards_file(brand))
    if not f.is_file():
        raise H.Refused([f"no talent cards for {brand} at {f}"])
    errs = CARDS.validate_file(f)
    if errs:
        raise H.Refused([f"talent cards fail their check: {e}" for e in errs[:10]])
    d = json.loads(f.read_text())
    retired = {p.get("id") for p in ((d.get("_retired") or {}).get("people") or []) if isinstance(p, dict)}
    return d["cards"], retired


def card_age(card):
    """(lo, hi, exact): a stated age wins over the band; the band otherwise."""
    for line in (card.get("notes") or []) + [card.get("reads") or ""]:
        s = str(line)
        if not re.search(r"\bage\b", s, re.I):
            continue
        m = re.search(r"\[(\d{2})\s*[-–]\s*(\d{2})\]", s)
        if m:
            return int(m.group(1)), int(m.group(2)), False
        m = re.search(r"\bage[^0-9\n]{0,25}?(\d{2})\b(?!s)", s, re.I) or re.search(r"\b(\d{2})\s+self-stated", s)
        if m:
            n = int(m.group(1))
            return n, n, True
    b = BAND.get(card.get("age-band") or "")
    return (b[0], b[1], False) if b else (None, None, False)


def card_matches_handle(card, handle):
    """Is this card the creator the record names (`nova`, `@nova`)?"""
    want = alnum(handle)
    if not want:
        return False
    names = [card.get("handle"), card.get("id"), card.get("drive-folder"), *(card.get("old-ids") or [])]
    src = str(card.get("source") or "")
    m = re.search(r"/(?:creators|content-creators)/([^/]+)/", src)
    if m:
        names.append(m.group(1))
    return any(alnum(n) == want for n in names if n)


# ---- what the brief asks for ------------------------------------------------
def _read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


def _run_record(rec, brand):
    run = rec.get("run")
    if not run:
        return {}, []
    texts = []
    rj = {}
    for d in (VIDEO_RUNS / brand / run, VIDEO_RUNS / run):
        if (d / "run.json").is_file():
            rj = json.loads(_read(d / "run.json") or "{}")
            break
    tr = TEARDOWN_RECORDS / run
    for name in ("3-injection.md", "7-final-brief.md", "brief-final.md", "5-brief.md"):
        if (tr / name).is_file():
            texts.append((f"teardown record {run}/{name}", _read(tr / name)))
    return rj, texts


def _avatar_texts(brand, avatar, sub):
    out = []
    if not avatar:
        return out
    base = WS / "brands" / brand / "core-avatars" / avatar
    if sub:
        for f in sorted((base / "sub-avatars").glob(f"*{sub}*.md")):
            out.append((f"sub-avatar {sub}", _read(f)))
    if (base / "profile.md").is_file():
        out.append((f"avatar {avatar} profile", _read(base / "profile.md")))
    return out


AGE_WHO = re.compile(r"\b(woman|women|female|man|men|male)\b[^\n|.;]{0,20}?(\d{2})\s*(?:–|-|to)\s*(\d{2})\b", re.I)
AGE_ONE = re.compile(r"\b(woman|man)\b,\s*(\d{2})\b", re.I)


def brief_ask(brand, brief, lane=None, ask_file=None):
    """Everything the brief asks of the person on camera, each with where it
    was read. Nothing is guessed: a field the records do not carry stays None
    and is not scored."""
    reg = BR.load()
    try:
        key, rec = BR.get(reg, brief, brand)
    except N.AmbiguousBrief as e:
        raise H.Refused([str(e)])
    if rec is None:
        raise H.Refused([f"{brief} — unknown brief: not in the brief register"])
    if rec.get("brand") and rec["brand"] != brand:
        raise H.Refused([f"{brief} — belongs to {rec['brand']}, not {brand}"])
    rec = dict(rec, id=key)
    bid = N.brief_id(key)
    src = {}
    ask = {"brief": bid, "title": rec.get("title"), "avatar": None, "sub_avatar": None, "gender": None,
           "age": None, "ethnic": None, "look": [], "language": None, "lane": None, "role": "protagonist",
           "own_creator": None, "written_for": rec.get("creator"), "sources": src}
    declares = rec.get("declares") or {}
    rj, td_texts = _run_record(rec, brand)

    ask["avatar"] = rec.get("avatar") or declares.get("avatar") or (rj.get("audience") or {}).get("_avatar")
    if ask["avatar"]:
        src["avatar"] = "brief register"
    sub = rec.get("sub_avatar") or declares.get("sub_avatar") or (rj.get("audience") or {}).get("_sub_avatar")
    if sub and str(sub).lower() not in ("none", "null", ""):
        ask["sub_avatar"] = sub
        src["sub_avatar"] = "brief register / teardown audience stage"

    typ = str(rec.get("type") or "")
    route = str(rj.get("production_route") or "")
    if lane:
        ask["lane"], src["lane"] = lane, "asked"
    elif "-ai" in typ or route == "ai":
        ask["lane"], src["lane"] = "ai", f"brief type {typ or route}"
    elif "creator" in typ or route == "creator":
        ask["lane"], src["lane"] = "creator", f"brief type {typ}" + (f", production route {route}" if route else "")

    own = rj.get("creator") or rec.get("creator")
    if own and (route == "creator" or str(rj.get("lane")) == "creator" or rec.get("creator")):
        ask["own_creator"] = own
        src["own_creator"] = "the swipe is this creator's own post (teardown run)" if rj.get("creator") else "brief register"

    bf = H.brief_file(rec, brand)
    brief_txt = _read(bf) if bf else ""
    texts = ([("brief", brief_txt)] if brief_txt else []) + td_texts + _avatar_texts(brand, ask["avatar"], ask["sub_avatar"])

    for where, t in texts:
        m = AGE_WHO.search(t)
        if m:
            g = m.group(1).lower()
            ask["gender"] = "female" if g in ("woman", "women", "female") else "male"
            ask["age"] = [int(m.group(2)), int(m.group(3))]
            src["gender"] = src["age"] = f"{where}: \"{m.group(0).strip()}\""
            break
        m = AGE_ONE.search(t)
        if m:
            g = m.group(1).lower()
            ask["gender"] = "female" if g == "woman" else "male"
            n = int(m.group(2))
            ask["age"] = [n - 5, n + 5]
            src["gender"] = src["age"] = f"{where}: \"{m.group(0).strip()}\" (±5 years)"
            break
    if not ask["gender"] and brief_txt:
        she = len(re.findall(r"\b(she|her|herself)\b", brief_txt, re.I))
        he = len(re.findall(r"\b(he|him|his|himself)\b", brief_txt, re.I))
        if she != he:
            ask["gender"] = "female" if she > he else "male"
            src["gender"] = f"brief: she/her {she} times, he/him {he} times"

    # look: the brief's own hair/wear lines + the protagonist line of the teardown
    look_txt = "\n".join(l for l in brief_txt.splitlines() if re.search(r"\bhair\b", l, re.I))
    for where, t in td_texts:
        for l in t.splitlines():
            if re.search(r"protagonist|the subject\b", l, re.I):
                look_txt += "\n" + l
                src.setdefault("look", f"brief hair lines + {where} protagonist line")
                break
    src.setdefault("look", "brief hair lines")
    ask["look"] = [k for k, rx in LOOK.items() if re.search(rx, look_txt, re.I)]

    if re.search(r"\bspanish\b|en español", brief_txt, re.I):
        ask["language"], src["language"] = "spanish", "brief asks for Spanish"
    elif brief_txt:
        ask["language"], src["language"] = "english", "the brief's spoken lines are English"

    if ask_file:
        extra = json.loads(Path(ask_file).read_text())
        for k, v in extra.items():
            if k in ask and k != "sources":
                ask[k] = v
                src[k] = f"--ask {Path(ask_file).name}"
    return ask


# ---- the score --------------------------------------------------------------
def excluded_why(card, ask, retired):
    cid = card.get("id")
    if cid in retired:
        return "retired — a retired id is never cast"
    kind = card.get("kind")
    lane = ask.get("lane")
    if lane == "creator" and kind != "real-creator":
        return "AI character — this brief is filmed by a real creator"
    if lane == "ai" and kind != "ai-character":
        return "real creator — this brief is an AI production"
    if kind == "ai-character" and (card.get("casting-sheet") != "yes" or card.get("status") != "current"):
        return "AI character with no casting sheet — not current"
    if ask.get("role") == "protagonist" and card.get("role") not in PROTAGONIST_ROLES:
        return f"{card.get('role')} card — not the person the brief follows"
    if ask.get("gender") and card.get("gender") and card["gender"] != ask["gender"]:
        return f"{card['gender']} — the brief asks for a {'woman' if ask['gender'] == 'female' else 'man'}"
    return None


def score(card, ask):
    """(points, max points, reasons) — every point carries its reason."""
    pts, mx, why = 0.0, 0, []

    def add(n, w, text):
        nonlocal pts, mx
        pts += n
        mx += w
        why.append(f"{'+' if n > 0 else '·'}{round(n):g} {text}")

    if ask.get("avatar"):
        fits = ask["avatar"] in (card.get("avatars-fit") or [])
        add(W["avatar"] if fits else 0, W["avatar"], f"fits {ask['avatar']}" if fits else f"card does not fit {ask['avatar']}")
    if ask.get("sub_avatar"):
        fits = ask["sub_avatar"] in (card.get("sub-avatars-fit") or [])
        add(W["sub_avatar"] if fits else 0, W["sub_avatar"],
            f"fits sub-avatar {ask['sub_avatar']}" if fits else f"not carded for sub-avatar {ask['sub_avatar']}")
    if ask.get("age"):
        lo, hi = ask["age"]
        clo, chi, exact = card_age(card)
        w = W["age"]
        if clo is None:
            add(5, w, "age not on the card")
        elif exact:
            if lo <= clo <= hi:
                add(w, w, f"age {clo} (stated) — inside {lo}–{hi}")
            elif min(abs(clo - lo), abs(clo - hi)) <= 5:
                add(10, w, f"age {clo} (stated) — just outside {lo}–{hi}")
            else:
                add(0, w, f"age {clo} — outside {lo}–{hi}")
        else:
            overlap = max(0, min(hi, chi) - max(lo, clo) + 1) / (chi - clo + 1)
            band = card.get("age-band") or f"{clo}-{chi}"
            if overlap >= 1:
                add(w - 3, w, f"age band {band} — inside {lo}–{hi} (band, not a stated age)")
            elif overlap > 0:
                add(round((w - 3) * overlap), w, f"age band {band} — partly inside {lo}–{hi}")
            else:
                add(0, w, f"age band {band} — outside {lo}–{hi}")
    if ask.get("gender"):
        g = card.get("gender")
        add(W["gender"] if g == ask["gender"] else 5, W["gender"],
            "woman" if g == "female" else "man" if g == "male" else "gender not on the card")
    if ask.get("ethnic"):
        e = card.get("ethnic-appearance")
        add(W["ethnic"] if e == ask["ethnic"] else (3 if not e else 0), W["ethnic"],
            f"appearance {e}" if e else "appearance not on the card")
    if ask.get("look"):
        txt = " ".join([str(card.get("reads") or "")] + [str(n) for n in card.get("notes") or []])
        hit = [k for k in ask["look"] if re.search(LOOK[k], txt, re.I)]
        n = W["look"] * len(hit) / len(ask["look"])
        add(n, W["look"], ("look: " + ", ".join(hit)) if hit else "look: nothing the brief names is on the card")
    if ask.get("language"):
        txt = json.dumps(card).lower()
        if ask["language"] in txt:
            add(W["language"], W["language"], f"speaks {ask['language']} (on the card)")
        else:
            add(0, W["language"], "language not on the card")
    if ask.get("own_creator"):
        own = card_matches_handle(card, ask["own_creator"])
        add(W["own_post"] if own else 0, W["own_post"],
            "the brief is rebuilt from her own post" if own else "not the creator whose post this is")
    return round(pts), mx, why


def pick(brand, brief, lane=None, ask_file=None, cards_path=None):
    ask = brief_ask(brand, brief, lane=lane, ask_file=ask_file)
    cards, retired = load_cards(brand, cards_path)
    ranked, out = [], []
    for c in cards:
        why = excluded_why(c, ask, retired)
        if why:
            out.append({"card": c["id"], "kind": c.get("kind"), "why": why})
            continue
        pts, mx, reasons = score(c, ask)
        ranked.append({"card": c["id"], "name": c.get("name"), "handle": c.get("handle"), "kind": c.get("kind"),
                       "score": pts, "of": mx, "reasons": reasons})
    ranked.sort(key=lambda r: (-r["score"], r["card"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    written_for = None
    if ask.get("written_for"):
        hit = next((c["id"] for c in cards if card_matches_handle(c, ask["written_for"]) and c.get("kind") == "real-creator"), None)
        written_for = {"record": ask["written_for"], "card": hit,
                       "agrees": bool(ranked and hit and ranked[0]["card"] == hit)}
    return {"schema": "creator-pick/1", "brand": brand, "brief": ask["brief"], "title": ask.get("title"),
            "ask": ask, "ranking": ranked, "excluded": out, "written_for": written_for,
            "picked": ranked[0]["card"] if ranked else None, "created": now(),
            "via": "components/handoff-standard/skill/creators.py pick"}


def write_matches(cm_folder, result, due=None):
    """The creator manager's returned/matches.json — brief id → card id, due,
    why. Merged by brief id; nothing else in the folder is touched."""
    ret = Path(cm_folder) / "returned"
    if not (Path(cm_folder) / "manifest.json").is_file():
        raise H.Refused([f"{cm_folder} is not a hand-off folder (no manifest.json)"])
    ret.mkdir(exist_ok=True)
    f = ret / "matches.json"
    cur = json.loads(f.read_text()) if f.is_file() else {}
    top = result["ranking"][0] if result["ranking"] else None
    cur[result["brief"]] = {
        "creator": top["card"] if top else "unmatched",
        "due": due,
        "why": top["reasons"] if top else ["no carded creator passes the brief's gates"],
        "score": f"{top['score']}/{top['of']}" if top else None,
        "next": [f"{r['card']} {r['score']}/{r['of']}" for r in result["ranking"][1:4]],
        "picked": result["created"], "via": result["via"],
    }
    f.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + "\n")
    return f


# ---- hand-off ---------------------------------------------------------------
def ids_sidecar_for(brief):
    """A sidecar under the print run's _ids/ that names this brief (the page a
    creator brief does not carry yet) — used only when one says so."""
    bid = N.brief_id(brief)
    for f in sorted(IDS_DIR.glob("*.json")) if IDS_DIR.is_dir() else []:
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and (bid in d or N.brief_code(bid) in d):
            return f
    return None


def draft_message(card, ask, manifest, due=None):
    first = (card.get("name") or "").split(" ")[0] or "there"
    return "\n".join([
        "# Message to the creator — DRAFT, NOT SENT",
        "",
        "Sending this is the owner's go. Nothing in this folder has been sent or shared.",
        "",
        "---",
        "",
        f"Hi {first},",
        "",
        f"New brief for you: \"{ask.get('title') or ask['brief']}\" ({ask['brief']}).",
        "The folder has the brief, the product and the page — start with handoff.md.",
        f"Please film exactly what the brief asks, 9:16, no watermark, and name each file {ask['brief']}_asset-01, {ask['brief']}_asset-02, …",
        "Put the files in the returned/ folder inside it.",
        f"Due: {due or 'to agree'}.",
        "",
        "Thank you!",
        "",
    ])


def handoff(brand, brief, creator, staging=None, ids_file=None, online=True, due=None, lane=None,
            catalog=None, when=None, cards_path=None, ask_file=None):
    """The creator's folder through handoff.py (role `creator`), then who it is
    for. A card that is not castable for this brief refuses; nothing is sent."""
    ask = brief_ask(brand, brief, lane=lane, ask_file=ask_file)
    cards, retired = load_cards(brand, cards_path)
    card = next((c for c in cards if c["id"] == creator), None)
    if card is None:
        raise H.Refused([f"{creator} — no talent card with that id for {brand}"])
    why = excluded_why(card, ask, retired)
    if why:
        raise H.Refused([f"{creator} — {why}"])
    if ids_file is None:
        ids_file = ids_sidecar_for(brief)
    staging = Path(staging or H.DEFAULT_STAGING)
    root, manifest = H.run("creator", brand, [ask["brief"]], catalog=catalog, staging=staging,
                           ids_file=str(ids_file) if ids_file else None, online=online, when=when, drive=False)
    pts, mx, reasons = score(card, ask)
    who = {"card": card["id"], "name": card.get("name"), "handle": card.get("handle"), "kind": card.get("kind"),
           "fit": f"{pts}/{mx}", "why": reasons, "due": due, "message": "references/message-draft.md — DRAFT, NOT SENT",
           "sent": False}
    (root / "references" / "creator.json").write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    (root / "references" / "message-draft.md").write_text(draft_message(card, ask, manifest, due))
    manifest["creator"] = who
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    md = (root / "handoff.md").read_text()
    line = (f"\n**Cast:** {card.get('name')} (`{card['id']}`{', ' + card['handle'] if card.get('handle') else ''}) — "
            f"fit {pts}/{mx}: " + "; ".join(r.lstrip('+·0123456789 ') for r in reasons if r.startswith('+')) +
            ". The card is in references/creator.json. The message to her is a draft (references/message-draft.md) — not sent.\n")
    md = md.replace("\n## 3 What's inside", line + "\n## 3 What's inside", 1)
    (root / "handoff.md").write_text(md)
    return root, manifest, ids_file


# ---- track ------------------------------------------------------------------
def staging_roots(extra=None, drive=True):
    roots = [Path(p) for p in (extra or [])] or [H.DEFAULT_STAGING, PRINT_RUN_STAGING]
    out = [("repo", r) for r in roots if r.is_dir()]
    if drive and (Path(H.DRIVE_MOUNT) / "handoffs").is_dir():
        out.append(("drive", Path(H.DRIVE_MOUNT) / "handoffs"))
    return out


def _returned(folder):
    ret = folder / "returned"
    files = [f for f in sorted(ret.rglob("*")) if f.is_file() and f.name not in NOT_WORK] if ret.is_dir() else []
    return files


def _ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def who_for(manifest, brand, cards_by_brand):
    c = manifest.get("creator")
    if c:
        return c.get("card"), "picked by creators.py"
    reg = BR.load()
    for b in manifest.get("briefs") or []:
        _, rec = BR.get(reg, b.get("id"))
        if rec and rec.get("creator"):
            cards = cards_by_brand.get(brand) or []
            hit = next((x["id"] for x in cards if card_matches_handle(x, rec["creator"]) and x.get("kind") == "real-creator"), None)
            return hit or rec["creator"], "brief written for (register)"
    return None, "not recorded"


def track(brand=None, staging=None, take_back=True, drive=True, ledger=None):
    rows = {}
    cards_by_brand = {}
    for where, root in staging_roots(staging, drive):
        base = root / "creator"
        if not base.is_dir():
            continue
        for bdir in sorted(p for p in base.iterdir() if p.is_dir()):
            if brand and bdir.name != brand:
                continue
            if bdir.name not in cards_by_brand:
                try:
                    cards_by_brand[bdir.name] = load_cards(bdir.name)[0]
                except H.Refused:
                    cards_by_brand[bdir.name] = []
            for folder in sorted(p for p in bdir.iterdir() if (p / "manifest.json").is_file()):
                m = json.loads((folder / "manifest.json").read_text())
                files = _returned(folder)
                footage = [f for f in files if f.suffix.lower() in MEDIA]
                taken = _ts(((m.get("returned") or {}).get("taken_back")))
                got = set((m.get("returned") or {}).get("received") or [])
                # new = not recorded yet, or changed after the last take-back (its stamp is whole seconds)
                new = [f for f in files if taken is None or str(f.relative_to(folder / "returned")) not in got
                       or f.stat().st_mtime > taken + 1]
                did = None
                if files and new and take_back:
                    lg = Path(ledger) if ledger else (root / "ledger.jsonl" if where == "repo" else H.DEFAULT_STAGING / "ledger.jsonl")
                    idx = H.take_back("creator", bdir.name, folder.name, root, lg)
                    did = {"files": len(idx["files"]), "ledger": str(lg.relative_to(WS)) if lg.is_relative_to(WS) else str(lg)}
                    m = json.loads((folder / "manifest.json").read_text())
                card, how = who_for(m, bdir.name, cards_by_brand)
                key = (bdir.name, folder.name)
                row = rows.setdefault(key, {
                    "handoff": folder.name, "brand": bdir.name,
                    "briefs": [b.get("id") for b in m.get("briefs") or []],
                    "creator": card, "creator_from": how,
                    "sent_to_creator": bool((m.get("creator") or {}).get("sent")),
                    "where": [], "returned_files": 0, "footage": 0, "taken_back": None, "took_back_now": None,
                })
                rel = str(folder.relative_to(WS)) if folder.is_relative_to(WS) else f"Drive: Shared Assets/handoffs/creator/{bdir.name}/{folder.name}"
                row["where"].append(rel)
                row["returned_files"] = max(row["returned_files"], len(files))
                row["footage"] = max(row["footage"], len(footage))
                row["taken_back"] = (m.get("returned") or {}).get("taken_back") or row["taken_back"]
                if did:
                    row["took_back_now"] = did
    out = []
    for r in rows.values():
        r["status"] = ("footage back" if r["footage"] else "files back, no footage") if r["returned_files"] else "waiting"
        out.append(r)
    out.sort(key=lambda r: (r["status"] == "waiting", r["brand"], r["handoff"]))
    return {"schema": "creator-status/1", "checked": now(), "handoffs": out,
            "counts": {"waiting": sum(r["status"] == "waiting" for r in out),
                       "footage back": sum(r["status"] == "footage back" for r in out),
                       "files back, no footage": sum(r["status"] == "files back, no footage" for r in out)},
            "note": "sent_to_creator is false until the owner's go is recorded; this tool never sends.",
            "via": "components/handoff-standard/skill/creators.py track"}


# ---- the command ------------------------------------------------------------
def _print_pick(res, top):
    a = res["ask"]
    print(f"PICK {res['brief']} — {res.get('title') or ''}")
    print("  the brief asks: " + " · ".join(x for x in [
        f"lane {a['lane']}" if a.get("lane") else None,
        f"avatar {a['avatar']}" if a.get("avatar") else None,
        f"sub-avatar {a['sub_avatar']}" if a.get("sub_avatar") else "no sub-avatar",
        ({"female": "a woman", "male": "a man"}[a["gender"]]) if a.get("gender") else None,
        f"age {a['age'][0]}–{a['age'][1]}" if a.get("age") else None,
        ("look " + ", ".join(a["look"])) if a.get("look") else None,
        a.get("language"),
    ] if x))
    for k, v in a["sources"].items():
        print(f"    {k}: {v}")
    print(f"  ranking ({len(res['ranking'])} castable, {len(res['excluded'])} not castable):")
    for r in res["ranking"][:top]:
        print(f"  {r['rank']:>2}. {r['card']:<14} {r['score']:>5}/{r['of']}  {r.get('handle') or ''}")
        for why in r["reasons"]:
            print(f"        {why}")
    groups = {}
    for e in res["excluded"]:
        groups.setdefault(e["why"], []).append(e["card"])
    for why, ids in groups.items():
        print(f"  not castable — {why}: {len(ids)} ({', '.join(ids[:6])}{'…' if len(ids) > 6 else ''})")
    wf = res.get("written_for")
    if wf:
        print(f"  the brief was written for {wf['record']} (card {wf['card'] or 'none'}) — "
              f"{'the top pick agrees' if wf['agrees'] else 'the top pick differs'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick", help="rank the brand's carded creators for a brief")
    p.add_argument("--brand", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--lane", choices=["creator", "ai"])
    p.add_argument("--ask", help="a JSON file overriding what the brief asks (gender, age [lo,hi], look, sub_avatar, ethnic, language, lane)")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--json", action="store_true", help="print the whole result as JSON")
    p.add_argument("--into", help="a creator-manager hand-off folder: write the pick to its returned/matches.json")
    p.add_argument("--due", help="due date to record with the match")
    h = sub.add_parser("handoff", help="write the creator's hand-off folder (handoff.py creator) for a picked card")
    h.add_argument("--brand", required=True)
    h.add_argument("--brief", required=True)
    h.add_argument("--creator", required=True, help="the talent card id (e.g. nova-2)")
    h.add_argument("--staging", help=f"default {H.DEFAULT_STAGING.relative_to(WS)} (the hand-off tool's own)")
    h.add_argument("--ids", help="sidecar for ids the brief record does not carry (default: the print run's _ids/ file naming this brief, if any)")
    h.add_argument("--catalog")
    h.add_argument("--offline", action="store_true")
    h.add_argument("--due")
    h.add_argument("--lane", choices=["creator", "ai"])
    t = sub.add_parser("track", help="which creator hand-offs are waiting and which have footage back; take back what landed")
    t.add_argument("--brand")
    t.add_argument("--staging", action="append", help="a staging root to scan (repeatable; default the hand-off tool's and the print run's)")
    t.add_argument("--no-drive", action="store_true", help="do not scan the Drive mount")
    t.add_argument("--no-take-back", action="store_true", help="report only")
    t.add_argument("--out", help=f"status file (default {(H.DEFAULT_STAGING / 'creator-status.json').relative_to(WS)})")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "pick":
            res = pick(a.brand, a.brief, lane=a.lane, ask_file=a.ask)
            if a.into:
                f = write_matches(a.into, res, due=a.due)
                res["written"] = str(f)
            if a.json:
                print(json.dumps(res, indent=1, ensure_ascii=False))
            else:
                _print_pick(res, a.top)
                if a.into:
                    print(f"  match written to {res['written']}")
            return 0 if res["ranking"] else 1
        if a.cmd == "handoff":
            root, m, ids = handoff(a.brand, a.brief, a.creator, staging=a.staging, ids_file=a.ids,
                                   online=not a.offline, due=a.due, lane=a.lane, catalog=a.catalog)
            print(f"READY {m['name']} for {m['creator']['card']} ({m['creator']['fit']})")
            print(f"  folder   {root}")
            print(f"  ids      {ids.relative_to(WS) if ids else 'none'}")
            print(f"  message  {root / 'references/message-draft.md'}  — DRAFT, NOT SENT")
            print("  stops    sending the brief to the creator is the owner's go; nothing was sent or shared")
            return 0
        if a.cmd == "track":
            res = track(a.brand, a.staging, take_back=not a.no_take_back, drive=not a.no_drive)
            out = Path(a.out or H.DEFAULT_STAGING / "creator-status.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
            print(f"TRACK {len(res['handoffs'])} creator hand-off(s): " + " · ".join(f"{k} {v}" for k, v in res["counts"].items()))
            for r in res["handoffs"]:
                tb = f"  — taken back now ({r['took_back_now']['files']} file(s))" if r["took_back_now"] else ""
                print(f"  {r['status']:<22} {r['handoff']}  {', '.join(r['briefs'])}  creator {r['creator'] or '—'}"
                      f"  returned {r['returned_files']} (footage {r['footage']}){tb}")
                for w in r["where"]:
                    print(f"      {w}")
            print(f"  status  {out}")
            return 0
    except H.Refused as e:
        print("REFUSED — nothing written:")
        for r in e.reasons:
            print(f"  - {r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
