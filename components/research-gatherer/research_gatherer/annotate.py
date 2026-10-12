"""Annotate + file — how every row the gatherer writes is read and filed.

Two reads per row, two owners:
  1. INTAKE (this component, `prompts/annotate-row.md`): keep or drop, a
     cancel/refund exit, use tags, topics, sub-avatar, ad use, the names and
     signature to strip. What only an intake needs.
  2. LABEL (the language layer's own labeller, `tools/language-layer/
     tools/label.py`, its newest `label-awareness-v*.md` prompt):
     awareness, sophistication, the lane the words point to. The ruled
     reading (brands/language-schema.md, "Lanes by language …", 2026-09-28) —
     called, never restated, so there is one set of awareness rules.

What a filed row carries (brands/language-schema.md, plus):
  id              language_<brand>_<avatar>_<lane>_<NNNN> — the Naming Standard's
                  two-mark rule (components/naming, v5), numbered across
                  the whole avatar bank
  text            the exact words (names -> [name], signature cut; nothing else touched)
  source          name, type, date (the day it was PULLED), ref (permalink to the exact
                  comment / message), post (the post or video it sits under), said (the
                  day it was written, when known). No handle.
  signal          likes, replies (when the source measured them); tier left for a person
  lane_by         "relationship" (an order on file) | "language" (the words decided)
  awareness       {level, why, by, model, date}   — written exactly as label.py writes it
  sophistication  {signal, by, date}
  lane_words, origin, voice                        — as label.py writes them
  use, topics, sub, ad_use, intake

The lane, first match wins (the ruling): an order on file -> customers/unsegmented,
or churned/ when the words exit; else the labeller's lane_words: customer ->
customers/unsegmented with attribution "assumed", lead -> leads, prospect -> prospects.
A row the labeller did not answer is HELD, never guessed.
"""
import datetime as _dt
import importlib.util
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from . import engine

PROMPT = engine.ROOT / "prompts" / "annotate-row.md"
LANE_FILE = {
    "customer": "customers/unsegmented.json",
    "lead": "leads.json",
    "prospect": "prospects.json",
    "churned-subscriber": "churned/subscriber.json",
    "churned-non-subscriber": "churned/non-subscriber.json",
}
LANE_FUNNEL = {"customer": "customer", "lead": "lead", "prospect": "prospect",
               "churned-subscriber": "churned", "churned-non-subscriber": "churned"}
LEVELS = ("unaware", "problem-aware", "solution-aware", "product-aware", "most-aware", "unclear")
AD_USES = ("hook", "objection", "proof", "offer", "question", "none")
JOKE_TAGS = ("transformation-reaction", "result-language", "taste", "in-word", "subculture", "cringe")
# The culture tags (2026-10-06, the bottom-up culture build): what the culture
# map is built from. `laugh` is new — the line is a joke or reacts to one.
# `gather.py retag --culture` adds these to rows already in the bank, and
# `bank_apply` accepts only these in a proposal's `add_use`.
CULTURE_TAGS = ("taste", "cringe", "subculture", "in-word", "community-voice", "role-claimed", "laugh")
LABEL_MODEL = "claude-sonnet-5"   # the labeller's own default — its registry id in components/models/models.json (alias `sonnet`)


def slug(x):
    """An account or room as a Naming Standard value: lowercase, and dots and
    underscores become hyphens (`_` is the separator between values)."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9-]", "-", str(x or "").lower().replace(".", "-").replace("_", "-"))).strip("-")


def say(m):
    print(m, flush=True)


# ---------------------------------------------------------------- cleaning (verbatim-safe)

QUOTE_CUT = re.compile(
    r"(On (Mon|Tue|Wed|Thu|Fri|Sat|Sun)[^\n]{0,120}wrote:|-{3,}\s*Original Message|"
    r"^From: |\nFrom: |Sent from my (iPhone|iPad|Galaxy|T-Mobile|Samsung|Android)[^\n]*)",
    re.I | re.M)
REDACT = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"), "[phone]"),
    (re.compile(r"\b\d{2,6}\s+(?:[NSEW]\.?\s+|\w+\s+){0,4}(?:St|Street|Rd|Road|Dr|Drive|Ave|Avenue|Ct|Court|"
                r"Pkwy|Parkway|Ln|Lane|Blvd|Boulevard|Way|Pl|Place|Cir|Circle|Hwy|Trl|Ter)\b\.?[^\n]{0,60}?\b\d{5}(?:-\d{4})?\b",
                re.I), "[address]"),
    (re.compile(r"(order|invoice)\s*(#|no\.?|number)?\s*:?\s*#?\d{5,}", re.I), r"\1 [number]"),
    (re.compile(r"#\d{5,}"), "[number]"),
    (re.compile(r"\b[A-Z0-9]{17}\b"), "[number]"),
    (re.compile(r"(?<![\w.])@[\w.]{3,}"), "@[name]"),
]
SIGNOFF = re.compile(r"^\s*(thank you|thanks|thank u|regards|kind regards|kindest regards|best|best regards|"
                     r"sincerely|respectfully( submitted)?|blessings|cheers|warmly)\b[^\n]{0,40}$", re.I | re.M)
ADDRESS_LINE = re.compile(r"(\b\d{1,6}\s+\w+.*\b(St|Street|Rd|Road|Dr|Drive|Ave|Avenue|Ct|Court|Pkwy|Parkway|Ln|Lane|"
                          r"Blvd|Boulevard|Way|Pl|Place|Cir|Circle|Hwy)\b)|(\b[A-Z]{2}\s+\d{5}\b)|"
                          r"(\b(apt|suite|ste)\.?\s*\w+)", re.I)
JUNK_LINE = re.compile(r"^\s*(from:|subject:|to:|cc:|date:|sent:|-+\s*forwarded message|get outlook|yahoo mail|"
                       r"<?https?://\S+>?\s*$|this (message|e-?mail) (and any attachment|is intended|contains))", re.I)
AUTO = re.compile(r"(automatic reply|autoreply|out of (the )?office|away from (the )?office|"
                  r"will return on|limited access to (my )?e-?mail|testflight)", re.I)


def clean(text):
    t = (text or "").replace("\r", "")
    m = QUOTE_CUT.search(t)
    if m:
        t = t[:m.start()]
    offs = list(SIGNOFF.finditer(t))
    if offs and len(t) - offs[-1].end() < 400:
        t = t[:offs[-1].end()]
    t = "\n".join(l for l in t.split("\n")
                  if not (len(l) <= 70 and ADDRESS_LINE.search(l)) and not JUNK_LINE.search(l))
    for rx, rep in REDACT:
        t = rx.sub(rep, t)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{2,}", "\n", t)).strip()


TITLE_LINE = re.compile(r"^[^\n]{0,60}\b(CEO|CFO|COO|Founder|President|Partner|Director|Manager|Ph\.?D|"
                        r"LLC|Inc\.?|Ltd|Corp|Esq|MD|RN)\b[^\n]{0,60}$")


def cut_signature(text, marker):
    """Cut where the sort says the signature begins (whitespace-tolerant);
    then drop short trailing lines that are only a title or a company."""
    m = re.sub(r"\s+", " ", (marker or "").strip())
    if len(m) >= 3:
        rx = re.compile(r"\s+".join(re.escape(w) for w in m.split(" ")))
        hit = rx.search(text)
        if hit and hit.start() > 0:
            text = text[:hit.start()].rstrip()
    lines = text.rstrip().split("\n")
    while len(lines) > 1 and (TITLE_LINE.match(lines[-1].strip()) or lines[-1].strip() in ("", "[name]")):
        lines.pop()
    return "\n".join(lines).rstrip()


def remove_names(text, names):
    for n in sorted({n.strip() for n in names or [] if n and len(n.strip()) > 1}, key=len, reverse=True):
        text = re.sub(re.escape(n), "[name]", text)
    return text


# ---------------------------------------------------------------- what the intake prompt is filled with

def vocabulary(root=None, top=90):
    """The bank's own use vocabulary, most-used first, across every brand."""
    ws = Path(root) if root else engine.WORKSPACE
    c = Counter()
    for f in (ws / "brands").glob("*/core-avatars/*/language/**/*.json"):
        if "/used/" in str(f):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            u = e.get("use")
            for x in (u if isinstance(u, list) else [u]):
                if isinstance(x, str) and x:
                    c[x] += 1
    tags = [t for t, _ in c.most_common(top)]
    for t in JOKE_TAGS + CULTURE_TAGS + ("mechanism", "accepted-belief", "skepticism", "subscription-behavior"):
        if t not in tags:
            tags.append(t)
    return tags


def lang_dir(brand, avatar):
    return engine.WORKSPACE / "brands" / brand / "core-avatars" / avatar / "language"


def subs_block(brand, avatar):
    d = engine.WORKSPACE / "brands" / brand / "core-avatars" / avatar / "sub-avatars"
    files = sorted(d.glob("*.md")) if d.is_dir() else []
    lines = []
    for f in files:
        first = next((l.strip("# ").strip() for l in f.read_text().splitlines() if l.strip()), "")
        lines.append(f"- `{engine.sub_slug(f)}` — {first[:140]}")
    return "\n".join(lines) or "(none on file — always null)", [engine.sub_slug(f) for f in files]


def rules_text(brand, avatar):
    try:
        return (lang_dir(brand, avatar) / "rules.md").read_text()[:6000]
    except Exception:
        return "(no rules.md on file for this avatar)"


# ---------------------------------------------------------------- read 1: intake

def annotate(rows, brand, avatar, label, source, model, batch=30, claude=None):
    """{i: intake verdict}. A batch the model cannot answer is left out —
    never guessed, never filed. `claude` is a seam for tests."""
    claude = claude or shutil.which("claude")
    if not claude:
        say("  intake read: MISSING (no `claude` command) — nothing will be filed")
        return {}
    subs, _ = subs_block(brand, avatar)
    tmpl = PROMPT.read_text().split("\n---\n", 1)[-1]
    base = (tmpl.replace("{{BRAND}}", label).replace("{{RULES}}", rules_text(brand, avatar))
            .replace("{{SUBS}}", subs).replace("{{VOCAB}}", ", ".join(vocabulary())).replace("{{SOURCE}}", source))
    out = {}
    for start in range(0, len(rows), batch):
        chunk = rows[start:start + batch]
        listing = "\n".join(f"{start + k}. [{r['kind']} · {r.get('relationship', 'unknown relationship')}] "
                            f"{r['text'][:1500]}" for k, r in enumerate(chunk))
        try:
            p = subprocess.run([claude, "-p", "--output-format", "text", "--model", model],
                               input=base.replace("{{ROWS}}", listing), capture_output=True, text=True, timeout=900)
            txt = p.stdout.strip()
            for v in json.loads(txt[txt.find("["): txt.rfind("]") + 1]):
                if isinstance(v, dict) and isinstance(v.get("i"), int):
                    out[v["i"]] = v
        except Exception as e:
            say(f"  intake read: rows {start}-{start + len(chunk) - 1} failed ({str(e)[:80]}) — held")
        say(f"  read {min(start + batch, len(rows))}/{len(rows)}")
    return out


# ---------------------------------------------------------------- read 2: the language layer's labeller

def _labeller():
    p = engine.WORKSPACE / "tools" / "language-layer" / "tools" / "label.py"
    if not p.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_ll_label", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    except Exception as e:
        say(f"  labeller: MISSING ({str(e)[:80]})")
        return None


def label_rows(rows, brand, labeller=None, model=LABEL_MODEL):
    """{i: label} from the language layer's labeller — awareness, sophistication,
    lane_words, why, plus origin/voice read off the row. {} when it cannot run."""
    lab = labeller or _labeller()
    if lab is None:
        say("  labeller: MISSING (tools/language-layer/tools/label.py) — rows held")
        return {}
    tmp = []
    for i, r in enumerate(rows):
        ordered = r.get("relationship") == "ordered"
        tmp.append({"id": f"row-{i}", "text": r["text"],
                    "speaker": "customer" if ordered else "commenter" if r.get("kind") == "comment" else "prospect",
                    "funnel": "customer" if ordered else "prospect",
                    "source": {"name": r.get("source_name"), "type": r.get("source_type")},
                    "_file": "prospects.json" if r.get("relationship") != "ordered" else "unsegmented.json"})
    try:
        got = lab.label(tmp, brand, model)
    except Exception as e:
        say(f"  labeller: failed ({str(e)[:100]}) — rows held")
        return {}
    out = {}
    for i, t in enumerate(tmp):
        g = got.get(t["id"])
        if g:
            out[i] = dict(g, origin=lab.origin_of(t), voice=lab.voice_of(t), model=model)
    return out


# ---------------------------------------------------------------- lane + entry

def decide_lane(row, v, lab):
    """(lane, lane_by, attribution) — the ruling, first match wins."""
    exit_ = (v or {}).get("exit") or "none"
    if row.get("relationship") == "ordered":
        if exit_ == "cancel-subscription":
            return "churned-subscriber", "relationship", None
        if exit_ == "refund-or-return":
            return "churned-non-subscriber", "relationship", None
        return "customer", "relationship", None
    words = (lab or {}).get("lane_words")
    if words == "customer":
        return "customer", "language", "assumed"
    if words == "lead":
        return "lead", "language", None
    return "prospect", "language", None


def build_entry(row, v, lab, avatar, run_label, subs=(), today=None):
    today = today or _dt.date.today().isoformat()
    lane, lane_by, attribution = decide_lane(row, v, lab)
    text = remove_names(cut_signature(row["text"], v.get("cut")), v.get("names") or [])
    use = [u for u in v.get("use") or [] if isinstance(u, str)] or ["question"]
    src = {"name": row["source_name"], "type": row["source_type"], "date": row["pulled"], "ref": row["ref"]}
    # Proposal 5 (PROPOSAL.md, 2026-09-28): the source named by the Naming Standard.
    for k_row, k_src in (("source_id", "id"), ("source_kind", "kind"), ("property", "property"), ("ad", "ad")):
        if row.get(k_row):
            src[k_src] = row[k_row]
    src["question"] = row.get("question")
    src["pulled"] = row["pulled"]
    if row.get("post"):
        src["post"] = row["post"]
    if row.get("said"):
        src["said"] = row["said"]
    sig = {k: row.get(k) for k in ("likes", "replies") if row.get(k) is not None}
    e = {
        "text": text[:2000], "avatar": avatar, "funnel": LANE_FUNNEL[lane],
        "speaker": ("commenter" if row["kind"] == "comment" and lane == "prospect"
                    else "prospect" if lane == "prospect" else LANE_FUNNEL[lane]),
        "source": src, "signal": sig or None,
        "topics": [t for t in v.get("topics") or [] if isinstance(t, str)][:6],
        "use": use[0] if len(use) == 1 else use,
        "status": "active", "sub": v.get("sub") if v.get("sub") in subs else None,
        "lane_by": lane_by,
        "ad_use": v.get("ad_use") if v.get("ad_use") in AD_USES else "none",
        "intake": {"by": "research-gatherer", "run": run_label},
    }
    if lab:
        e["awareness"] = {"level": lab.get("awareness") if lab.get("awareness") in LEVELS else "unclear",
                          "why": lab.get("why", ""), "by": "model", "model": lab.get("model", LABEL_MODEL), "date": today}
        e["sophistication"] = {"signal": lab.get("sophistication") or "none", "by": "model", "date": today}
        e["lane_words"] = lab.get("lane_words")
        e["origin"] = lab.get("origin")
        e["voice"] = lab.get("voice")
    if attribution:
        e["attribution"] = attribution
    return lane, e


# ---------------------------------------------------------------- filing

def bank_refs(ldir):
    refs = set()
    for f in ldir.parent.rglob("*.json"):
        if "/used/" in str(f):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            r = (e.get("source") or {}).get("ref")
            if r:
                refs.add(r)
    return refs


def next_ids(entries, n):
    """Continue a sequence: language_x_y_customer_0192 -> _0193 (and the old
    hyphen shapes, psn-cus-0192 -> psn-cus-0193, for banks not yet renamed)."""
    best = (None, 0, 4)
    for e in entries:
        m = re.match(r"^(.*[-_])(\d+)$", e.get("id", ""))
        if m and int(m.group(2)) >= best[1]:
            best = (m.group(1), int(m.group(2)), len(m.group(2)))
    prefix, last, width = best
    if prefix is None:
        return None
    return [f"{prefix}{last + k:0{width}d}" for k in range(1, n + 1)]


def _all_ids(ldir):
    ids = []
    for f in ldir.parent.rglob("*.json"):
        if "/used/" in str(f):
            continue
        try:
            ids += [{"id": e.get("id", "")} for e in json.loads(f.read_text()).get("entries", [])]
        except Exception:
            pass
    return ids


def standard_prefix(ldir, lane):
    """language_<brand>_<avatar>_<lane>_ from the folder the bank sits in."""
    avatar = ldir.parent.name
    brand = ldir.parent.parent.parent.name
    return f"language_{brand}_{avatar}_{LANE_FUNNEL[lane]}_"


def lane_prefix(ldir, lane, own_entries):
    """The standard shape when the file is empty or already on it; a bank not
    yet renamed keeps its own shape until its rename (one bank, one shape)."""
    own = next_ids(own_entries, 1)
    if own and not own[0].startswith("language_"):
        return re.match(r"^(.*[-_])\d+$", own[0]).group(1)
    return standard_prefix(ldir, lane)


def _fmt(raw):
    m = re.search(r"\n( +)\"", raw)
    return (len(m.group(1)) if m else 1), raw.endswith("\n"), "\\u" in raw


def _dump(d, raw):
    ind, nl, asc = _fmt(raw)
    return json.dumps(d, indent=ind, ensure_ascii=asc) + ("\n" if nl else "")


def assign_ids(ldir, lane_entries, all_ids=None):
    """[(lane, entry)] -> entries with ids, numbered across the whole avatar bank."""
    all_ids = _all_ids(ldir) if all_ids is None else all_ids
    out = []
    for lane, e in lane_entries:
        prefix = standard_prefix(ldir, lane)
        i = (next_ids([x for x in all_ids if x["id"].startswith(prefix)], 1) or [f"{prefix}0001"])[0]
        all_ids.append({"id": i})
        out.append({"id": i, **{k: v for k, v in e.items() if k != "id"}})
    return out


def file_lanes(ldir, by_lane):
    """Append rows to the avatar's lane files. Ids continue the prefix's
    sequence across the whole bank (two lane files can share one). Each file
    keeps its own indent, escaping and trailing newline."""
    all_ids = _all_ids(ldir)
    filed = []
    for lane, entries in by_lane.items():
        f = ldir / LANE_FILE[lane]
        try:
            raw = f.read_text()
            d = json.loads(raw)
        except Exception:
            say(f"  file: MISSING {f} — {len(entries)} rows held")
            continue
        prefix = lane_prefix(ldir, lane, d.get("entries", []))
        ids = next_ids([x for x in all_ids if x["id"].startswith(prefix)], len(entries)) or \
            [f"{prefix}{k:04d}" for k in range(1, len(entries) + 1)]
        for i, e in zip(ids, entries):
            e2 = {"id": i, **e}
            d.setdefault("entries", []).append(e2)
            all_ids.append({"id": i})
            filed.append({**e2, "_file": str(f.relative_to(engine.WORKSPACE))})
        f.write_text(_dump(d, raw))
    return filed


# ---------------------------------------------------------------- the run report

def report(filed, dropped, held):
    """Rows per lane, per awareness level, per sub-avatar, and the thin levels."""
    lanes = Counter(r["funnel"] + ("/assumed" if r.get("attribution") == "assumed" else "") for r in filed)
    levels = Counter((r.get("awareness") or {}).get("level") or "not labelled" for r in filed)
    soph = Counter((r.get("sophistication") or {}).get("signal") or "not labelled" for r in filed)
    subc = Counter(r.get("sub") or "(no sub)" for r in filed)
    ad = Counter(r.get("ad_use") or "none" for r in filed)
    thin = [l for l in LEVELS[:5] if levels.get(l, 0) < 3]
    aw = {l: levels.get(l, 0) for l in LEVELS}
    if levels.get("not labelled"):
        aw["not labelled"] = levels["not labelled"]
    return {"filed": len(filed), "dropped": len(dropped), "held": len(held),
            "lanes": dict(lanes), "awareness": aw, "sophistication": dict(soph),
            "subs": dict(subc), "ad_use": dict(ad), "thin_levels": thin,
            "drop_reasons": dict(Counter((d.get("why") or "").split(":")[0] for d in dropped))}


def report_md(rep, title):
    L = [f"# {title}", "", f"Filed {rep['filed']} · dropped {rep['dropped']} · held {rep['held']}", "",
         "## Rows per lane", ""] + [f"- {k}: {v}" for k, v in sorted(rep["lanes"].items())] + \
        ["", "## Rows per awareness level", ""] + [f"- {k}: {v}" for k, v in rep["awareness"].items()] + \
        ["", f"**Thin levels (fewer than 3 rows):** {', '.join(rep['thin_levels']) or 'none'}", "",
         "## Sophistication signals", ""] + [f"- {k}: {v}" for k, v in rep["sophistication"].items()] + \
        ["", "## Rows per sub-avatar", ""] + [f"- {k}: {v}" for k, v in rep["subs"].items()] + \
        ["", "## Why rows were dropped", ""] + [f"- {k}: {v}" for k, v in rep["drop_reasons"].items()]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- the pipeline every mode shares

def read_and_sort(fresh, brand, avatar, label, source, cfg, run_label, labeller=None, claude=None):
    """intake read -> labeller on the kept rows -> [(lane, entry)], dropped, held."""
    verdicts = annotate(fresh, brand, avatar, label, source, cfg["model"], cfg["batch"], claude=claude)
    kept = [(i, r) for i, r in enumerate(fresh) if (verdicts.get(i) or {}).get("keep")]
    labels = label_rows([r for _, r in kept], brand, labeller=labeller) if kept else {}
    _, subs = subs_block(brand, avatar)
    lane_entries, dropped, held = [], [], []
    k = 0
    for i, r in enumerate(fresh):
        v = verdicts.get(i)
        if v is None:
            held.append(r)
        elif not v.get("keep"):
            dropped.append({"why": v.get("drop_why") or "dropped", "ref": r["ref"], "text": r["text"]})
        else:
            lab = labels.get(k)
            k += 1
            if lab is None:
                held.append(r)
                continue
            lane_entries.append(build_entry(r, v, lab, avatar, run_label, subs))
    return lane_entries, dropped, held


# ---------------------------------------------------------------- the deep pull's rows

def enrich_deep(entries, brand, avatar, sub, label, model, batch=30, today=None, labeller=None):
    """The deep pull's accepted rows get the labeller's fields and a standard
    id. They stay where the deep pull files them (the sub-avatar's own
    folder). When the labeller cannot run, the rows go out as before, with a
    standard id."""
    today = today or _dt.date.today().isoformat()
    rows = [dict(kind="community", text=e.get("text", ""), relationship="community poster, relationship unknown",
                 source_name=(e.get("source") or {}).get("name"), source_type=(e.get("source") or {}).get("type"))
            for e in entries]
    labels = label_rows(rows, brand, labeller=labeller) if entries else {}
    pairs = []
    for i, e in enumerate(entries):
        lab = labels.get(i)
        lane = "prospect"
        if lab:
            lane, lane_by, attribution = decide_lane({}, {}, lab)
            e["funnel"] = LANE_FUNNEL[lane]
            if lane != "prospect":
                e["speaker"] = LANE_FUNNEL[lane]
            e["lane_by"] = lane_by
            if attribution:
                e["attribution"] = attribution
            e["awareness"] = {"level": lab.get("awareness") if lab.get("awareness") in LEVELS else "unclear",
                              "why": lab.get("why", ""), "by": "model", "model": lab.get("model", LABEL_MODEL), "date": today}
            e["sophistication"] = {"signal": lab.get("sophistication") or "none", "by": "model", "date": today}
            e["lane_words"], e["origin"], e["voice"] = lab.get("lane_words"), lab.get("origin"), lab.get("voice")
        src = e.setdefault("source", {})
        if src.get("date") and src.get("date") != today:
            src["said"] = src["date"]
        src["date"] = today
        pairs.append((lane, e))
    return assign_ids(lang_dir(brand, avatar), pairs)
