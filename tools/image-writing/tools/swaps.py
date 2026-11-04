#!/usr/bin/env python3
"""The swaps record (image-writing, stage 3): one structured file per run that says what the picture swaps, and what goes into it.

    swaps.py show  <run>              the record, as a table
    swaps.py check <run>              validate out/swaps.json (exit 1 on a problem)
    swaps.py stage <run>              write out/swaps.json from the stage 3 answer (03-injection.md)
    swaps.py backfill [<run>…|--all]  write out/swaps.json for runs made before stage 3 wrote one

`out/swaps.json` is the contract between the teardown and every picture maker (the static chain, the Prompt Bench):

    {"product_in_frame": true|false, "product_where": "<where it sits>"|null,
     "product_sides": ["front"|"three-quarter"|"back"|…],
     "product_kit": "<kit id under runs/ai-elements/<brand>/products/>"|null,
     "stays": ["…"],
     "swaps": [{"from": "<what is in the swipe>", "to": "<what it becomes>",
                "kind": "cast"|"product"|"library"|"drawn"|"words", "ref": "<cast id | product kit | library path>"|null}],
     "words": "set_on_top"|"drawn",
     "source": "stage3"|"backfill"}

Optional: `evidence` (why each call was made, for a person to audit) and `unclear` (a backfill the text did not settle;
then `product_in_frame` is null and the run is listed by name, never guessed).

RULES (the system's, stated once here):

  swaps rule 1  Every swap is its own entry with a kind. A kind is the thing a maker must put in: `cast` = a banked character's
         photo (ref: the cast id under runs/ai-elements/<brand>/casting/), `product` = the product's real pictures
         (ref: the kit under runs/ai-elements/<brand>/products/), `library` = a banked prop or set (ref: its path),
         `drawn` = made from words only, `words` = the caption or headline.
  swaps rule 2  `product_in_frame` is yes or no, with where it sits and which sides show when yes. No inference downstream.
  swaps rule 3  The pictures a maker sends are worked out from this record and from nothing else: the swipe, one photo per cast
         swap, product photos only on yes, one photo per library swap.
  swaps rule 4  `words: set_on_top` means the picture is made with no caption, headline or overlay text in it, and the brief's own
         type layer is set over it afterwards. `drawn` means the words are part of an object in the scene.
  swaps rule 6  `cast` only when `to` names a character that exists under runs/ai-elements/<brand>/casting/<id>/ (ref = that id).
         A made-up person is `drawn`. When the product is in frame the record names its kit (`product_kit`) so its photos can go in.
  swaps rule 5  A swap the text does not settle is written `unclear` and listed; it is not guessed.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The workspace's paths come from the image teardown, whose runs this record lives in (its writing seam,
# tools/image-teardown/CLAUDE.md). Found by walking up, never counted.
for _r in HERE.parents:
    if (_r / "tools" / "image-teardown" / "tools" / "paths.py").is_file():
        sys.path.insert(0, str(_r / "tools" / "image-teardown" / "tools"))
        break
import paths as P  # noqa: E402

KINDS = ("cast", "product", "library", "drawn", "words")
WORDS = ("set_on_top", "drawn")
SOURCES = ("stage3", "backfill")
FILE = "swaps.json"
READER_PROMPT = HERE.parent / "prompts" / "swaps-reader-v1-owner.md"


# ───────────────────────── the record ─────────────────────────

def validate(d):
    """Every way a record can break the contract; [] when it holds."""
    if not isinstance(d, dict):
        return ["the record is not an object"]
    bad = []
    pif = d.get("product_in_frame")
    if pif is None:
        if not d.get("unclear"):
            bad.append("product_in_frame is null but nothing says why (unclear)")
    elif not isinstance(pif, bool):
        bad.append("product_in_frame must be true or false")
    if pif is True:
        if not (d.get("product_where") or "").strip():
            bad.append("product_in_frame is true but product_where is empty")
        if not d.get("product_sides"):
            bad.append("product_in_frame is true but product_sides is empty")
    if pif is True and not d.get("product_kit") and not d.get("unclear"):
        bad.append("product_in_frame is true but product_kit is empty (name the kit, or list the run as unclear)")
    if pif is False and d.get("product_kit"):
        bad.append("product_in_frame is false but product_kit is set")
    if pif is False:
        if d.get("product_where"):
            bad.append("product_in_frame is false but product_where is set")
        if d.get("product_sides"):
            bad.append("product_in_frame is false but product_sides is set")
    if not isinstance(d.get("product_sides", []), list):
        bad.append("product_sides must be a list")
    if not isinstance(d.get("stays"), list) or not all(isinstance(x, str) and x.strip() for x in d.get("stays") or []):
        bad.append("stays must be a list of lines")
    sw = d.get("swaps")
    if not isinstance(sw, list):
        bad.append("swaps must be a list")
        sw = []
    for i, s in enumerate(sw, 1):
        if not isinstance(s, dict) or not str(s.get("from", "")).strip() or not str(s.get("to", "")).strip():
            bad.append(f"swap {i}: needs from and to")
            continue
        if s.get("kind") not in KINDS:
            bad.append(f"swap {i}: kind must be one of {', '.join(KINDS)}")
        if s.get("kind") == "cast" and not s.get("ref"):
            bad.append(f"swap {i}: a cast swap needs the cast id (a made-up person is drawn)")
        if s.get("kind") in ("library",) and not s.get("ref"):
            bad.append(f"swap {i}: a library swap needs its path")
        if s.get("kind") in ("drawn", "words") and s.get("ref"):
            bad.append(f"swap {i}: a {s['kind']} swap carries no ref")
        if s.get("kind") == "product" and pif is False:
            bad.append(f"swap {i}: a product swap while product_in_frame is false")
    if d.get("words") not in WORDS:
        bad.append("words must be set_on_top or drawn")
    if d.get("source") not in SOURCES:
        bad.append("source must be stage3 or backfill")
    return bad


def path_of(run):
    return Path(run) / "out" / FILE


def load(run):
    f = path_of(run)
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text())
    except ValueError:
        return None


def write(run, d):
    bad = validate(d)
    if bad:
        raise ValueError("; ".join(bad))
    f = path_of(run)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return f


# ───────────────────────── the banks ─────────────────────────

def bank_root(brand):
    return P.REPO / "runs" / "ai-elements" / brand


def cast_ids(brand):
    d = bank_root(brand) / "casting"
    return sorted(x.name for x in d.iterdir() if x.is_dir() and not x.name.startswith("_") and (x / "master.jpg").is_file()) if d.is_dir() else []


def cast_photo(brand, cid):
    f = bank_root(brand) / "casting" / str(cid) / "master.jpg"
    return f if f.is_file() else None


def product_kits(brand):
    d = bank_root(brand) / "products"
    return sorted(x.name for x in d.iterdir() if x.is_dir()) if d.is_dir() else []


def library_paths(brand):
    """props/<id> and sets/<id>, as repo-relative paths."""
    out = []
    for kind in ("props", "sets"):
        d = bank_root(brand) / kind
        if d.is_dir():
            out += [f"runs/ai-elements/{brand}/{kind}/{x.name}" for x in sorted(d.iterdir()) if x.is_dir() and not x.name.startswith("_")]
    return out


def _words(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def cast_bank_note(run):
    """out/.cast-bank.md: every banked character with a photo, by id and role, for the stage 3 prompt. Returns its path."""
    brand, rows = brand_of(run), []
    for cid in cast_ids(brand):
        c = bank_root(brand) / "casting" / cid / "character.md"
        head = c.read_text().splitlines()[0].lstrip("# ").strip() if c.is_file() and c.read_text().strip() else cid
        rows.append(f"- `{cid}`: {head.split('—', 1)[-1].strip() if '—' in head else head}")
    f = Path(run) / "out" / ".cast-bank.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(rows) + "\n" if rows else "No banked characters for this brand: every cast swap has ref null.\n")
    return f


def match_cast(brand, text):
    """The cast id a phrase names, or None. An id matches when all its words are in the phrase, or when its last
    word (4+ letters) is a whole word of it ("Grandma Yai" → yai). Longest id wins."""
    hay = " " + " ".join(_words(text)) + " "
    best = None
    for cid in cast_ids(brand):
        toks = _words(cid)
        if not toks:
            continue
        whole = " " + " ".join(toks) + " " in hay
        last = len(toks[-1]) >= 4 and f" {toks[-1]} " in hay and len(toks) == 1
        if whole or last:
            if best is None or len(cid) > len(best):
                best = cid
    return best


def match_kit(brand, text):
    hay = " " + " ".join(_words(text)) + " "
    best = None
    for k in product_kits(brand):
        if " " + " ".join(_words(k)) + " " in hay and (best is None or len(k) > len(best)):
            best = k
    return best


def kit_from_text(brand, text):
    """The kit a text is about: the kit with the most of its own words in the text, only when one kit clearly leads."""
    low = " " + " ".join(_words(text)) + " "
    scored = []
    for k in product_kits(brand):
        toks = [t for t in _words(k) if len(t) >= 3]
        have = [t for t in toks if f" {t} " in low]
        scored.append((len(have) / max(1, len(toks)) + 0.01 * sum(low.count(f" {t} ") for t in have), len(have), k))
    scored.sort(reverse=True)
    if scored and scored[0][1] and (len(scored) == 1 or scored[0][0] - scored[1][0] > 0.05):
        return scored[0][2]
    return None


def brand_of(run):
    f = Path(run) / "vars" / "brand_name.md"
    return f.read_text().strip().lower() if f.is_file() else Path(run).name.split("-", 1)[0]


# ───────────────────────── reading the texts ─────────────────────────

def _read(run, name):
    f = Path(run) / "out" / name
    return f.read_text() if f.is_file() else ""


def json_blocks(text):
    out = []
    for m in re.finditer(r"```json\s*(.*?)```", text, re.S):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return out


def record_block(text):
    """The swaps record in a stage answer: the last json block that holds `swaps`."""
    found = [b for b in json_blocks(text) if isinstance(b, dict) and "swaps" in b]
    return found[-1] if found else None


def type_layer(brief_text):
    """The brief's type layer: the last json block with an `elements` list."""
    found = [b for b in json_blocks(brief_text) if isinstance(b, dict) and isinstance(b.get("elements"), list)]
    return found[-1] if found else None


NO_PRODUCT = re.compile(
    r"(?i)\bno\s+(?:\w+\s+){0,4}(?:product|tube|jar|bottle|pouch|packshot)\b[^.\n]{0,50}(?:in (?:the )?(?:frame|post|ad|picture|shot)|anywhere)"
    r"|\bno (?:product|tube|jar|bottle|packshot|device)\b"
    r"|\bthere is no place for (?:one|the product|a product)\b"
    r"|\bthe post has no place for (?:one|the product)\b"
    r"|\bproduct (?:is |does )?(?:not|never) (?:in|appear|shown|in frame)\b"
    r"|\bnot in this frame\b")
YES_PRODUCT = re.compile(
    r"(?i)\b(?:product|tube|jar|bottle|pouch)\b[^.\n]{0,60}\b(?:sits|rests|is held|held|in her hand|in his hand|lies|lying|on the (?:counter|shelf|table|desk)|replaces|in frame)\b")


def _line_of(text, m):
    """The sentence a match sits in, trimmed: what a person reads as the evidence."""
    a = max(text.rfind("\n", 0, m.start()), text.rfind(". ", 0, m.start()) + 1, 0)
    b = [i for i in (text.find("\n", m.end()), text.find(". ", m.end())) if i >= 0]
    return text[a:(min(b) + 1 if b else len(text))].strip()[:200]


def facts(run):
    """What the texts plainly say, with no model: the signals the product call and the words call rest on."""
    t3, t6 = _read(run, "03-injection.md"), _read(run, "06-brief.md")
    layer = type_layer(t6) or {}
    plate = [b for b in json_blocks(t6) if isinstance(b, dict) and "references" in b]
    refs = [r for b in plate for r in (b.get("references") or [])]
    comp = layer.get("composited") or []
    els = layer.get("elements") or []
    lay = layer.get("layout") or {}
    brand = brand_of(run)
    kits = product_kits(brand)
    prod_refs = [r for r in refs if any(k in str(r) for k in kits) or "product" in str(r).lower()]
    never = ""
    m = re.search(r"(?ms)^#+\s*\d+\s*·\s*Never on this ad(.*?)^#+\s", t6 + "\n# x")   # 8 in the v1 brief, 7 in v2
    if m:
        never = m.group(1)
    sentences = []
    for src in (never, t6, t3):
        for m in NO_PRODUCT.finditer(src):
            line = _line_of(src, m)
            if '":' not in line:                     # a "no product" inside a json field is a plate's negative list, not a statement about the ad
                sentences.append(line)
    return {
        "no_product_sentences": sentences[:3],
        "yes_product_sentences": [_line_of(t3, m) for m in YES_PRODUCT.finditer(t3)][:3],
        "plate_product_refs": prod_refs, "composited": comp,
        "on_product": any(e.get("on_product") for e in els),
        "elements": els, "marks": lay.get("marks") or [], "stickers": lay.get("stickers") or [],
        "has_layer": bool(layer), "layer": layer,
    }


def product_call(f):
    """(True|False|None, why) from the plain signals. None = the text does not settle it."""
    yes = f["plate_product_refs"] or f["on_product"] or [c for c in f["composited"] if "product" in json.dumps(c).lower()]
    if yes and not f["no_product_sentences"]:
        return True, "the brief carries a product reference or a composited product"
    if f["no_product_sentences"] and not yes:
        return False, f["no_product_sentences"][0]
    return None, None


def words_call(f):
    """(set_on_top|drawn|None, why). Set on top when the brief has a type layer the compositor can set (text elements,
    no marks or stickers it cannot draw); None when there is no layer to decide from."""
    if not f["has_layer"]:
        return None, None
    if f["marks"] or f["stickers"] or any(c for c in f["composited"] if "product" not in json.dumps(c).lower()):
        return "drawn", "the type layer carries marks, stickers or composited pieces the compositor does not set"
    return "set_on_top", "the brief has a type layer of text elements"


# ───────────────────────── stage 3 → record ─────────────────────────

def _clean(d, brand, source):
    """Normalise a model's record to the contract: kinds checked against the banks, refs resolved."""
    out = {
        "product_in_frame": d.get("product_in_frame"),
        "product_where": (d.get("product_where") or None),
        "product_sides": [str(x).strip().lower() for x in d.get("product_sides") or [] if str(x).strip()],
        "stays": [str(x).strip() for x in d.get("stays") or [] if str(x).strip()],
        "swaps": [], "words": d.get("words"), "source": source,
    }
    for s in d.get("swaps") or []:
        if not isinstance(s, dict):
            continue
        frm, to, kind, ref = str(s.get("from", "")).strip(), str(s.get("to", "")).strip(), s.get("kind"), s.get("ref") or None
        if not frm or not to:
            continue
        if kind == "cast":
            cid = (ref if ref in cast_ids(brand) else None) or match_cast(brand, to)
            ref = cid
        elif kind == "product":
            ref = ref if ref in product_kits(brand) else match_kit(brand, f"{to} {ref or ''}")
        elif kind == "library":
            ref = ref if ref in library_paths(brand) else next((p for p in library_paths(brand) if ref and p.endswith("/" + Path(str(ref)).name)), None)
            if not ref:                               # not in the library: there is no banked picture to send, so it is drawn
                kind = "drawn"
        elif kind in ("drawn", "words"):
            ref = None
        if kind == "cast" and not ref:                # not a banked character: a made-up person is drawn
            kind = "drawn"
        out["swaps"].append({"from": frm, "to": to, "kind": kind, "ref": ref})
    kit = d.get("product_kit")
    out["product_kit"] = kit if kit in product_kits(brand) else None
    if out["product_in_frame"] is True and not out["product_kit"]:
        # the record named its product swap but left product_kit empty (2026-10-28: all six Black Friday runs, each
        # costing a second stage-3 call): the kit is the product swap's own, else the one its words clearly name
        out["product_kit"] = (next((s["ref"] for s in out["swaps"] if s["kind"] == "product" and s["ref"]), None)
                              or kit_from_text(brand, " ".join([out.get("product_where") or ""]
                                                               + [s["to"] for s in out["swaps"] if s["kind"] == "product"])))
    if out["product_in_frame"] is False:
        out["product_where"], out["product_sides"], out["product_kit"] = None, [], None
    if out["product_in_frame"] is True and not out["product_sides"]:
        out["product_sides"] = ["front"]
    return out


def from_stage3(run):
    """out/swaps.json from the record stage 3 wrote at the end of its answer. Returns (record, problems)."""
    d = record_block(_read(run, "03-injection.md"))
    if d is None:
        return None, ["stage 3 wrote no swaps record (6. THE SWAPS RECORD)"]
    rec = _clean(d, brand_of(run), "stage3")
    bad = validate(rec)
    return (rec if not bad else None), bad


def carried(run):
    """Whether the stage 6 brief carries the same record as stage 3 wrote (swaps rule 3: the brief repeats it, never re-decides it)."""
    b = record_block(_read(run, "06-brief.md"))
    rec = load(run)
    if b is None or rec is None:
        return False
    return (b.get("product_in_frame") == rec.get("product_in_frame")
            and [(s.get("from"), s.get("to"), s.get("kind")) for s in b.get("swaps") or []]
            == [(s["from"], s["to"], s["kind"]) for s in rec["swaps"]])


# ───────────────────────── backfill ─────────────────────────

BULLET = re.compile(r"(?m)^\s*[-*]\s+\*\*(?P<from>.+?)\s+(?:becomes?|turns? into|is replaced by)\s+(?P<to>.+?)\.?\*\*")


def bullets(t3):
    """The plain `X becomes Y` swap lines of a stage 3 answer."""
    return [{"from": m["from"].strip(), "to": m["to"].strip()} for m in BULLET.finditer(t3)]


def reader_prompt(run, f):
    brand = brand_of(run)
    t3, t6 = _read(run, "03-injection.md"), _read(run, "06-brief.md")

    def sect(t, a, b, cap):
        m = re.search(r"(?ms)^" + a + r"(.*?)(?=^" + b + r"|\Z)", t)
        return (m.group(0) if m else "")[:cap]
    swaps = "\n\n".join(x for x in [
        sect(t3, r"\s*(?:-\s*)?\*\*THE SWIPE", r"\s*(?:-\s*)?\*\*WHY IT STILL", 5000),
        sect(t3, r"\*\*2\. THE SUBJECT\*\*", r"\*\*4\. SLOTS", 3500)] if x) or t3[:7000]
    pic = sect(t6, r"#+\s*3 · The picture", r"#+\s*4 ·", 3500)
    never = sect(t6, r"#+\s*8 · Never", r"#+\s*9 ·", 1800)
    vals = {
        "injection": swaps or t3[:6000], "brief_picture": (pic + "\n\n" + never).strip() or t6[:4000],
        "cast": ", ".join(cast_ids(brand)) or "(none)", "kits": ", ".join(product_kits(brand)) or "(none)",
        "library": ", ".join(p.rsplit("/", 2)[-2] + "/" + p.rsplit("/", 1)[-1] for p in library_paths(brand)[:400]) or "(none)",
        "facts": json.dumps({k: f[k] for k in ("no_product_sentences", "yes_product_sentences", "plate_product_refs", "composited", "on_product")}, ensure_ascii=False),
    }
    text = READER_PROMPT.read_text()
    for k, v in vals.items():
        text = text.replace("{" + k + "}", v)
    return text


def default_reader(prompt, label):
    sys.path.insert(0, str(P.REPO / "components" / "run-kit"))
    from run_kit import model as M
    return M.call(prompt, M.TIERS["reads"], label=label, tries=3, wait=20, timeout=300)


def _json_of(reply):
    m = re.search(r"\{.*\}", reply, re.S)
    return json.loads(m.group(0)) if m else None


def backfill(run, reader=None, force=False, redo=False):
    """out/swaps.json for a run made before stage 3 wrote one. What the text plainly says is read without a model; what it
    does not settle is read by one fast reading call, cached in out/.swaps-reader.json (re-running costs nothing).
    Returns (record, problems)."""
    run = Path(run)
    if load(run) and not force and not redo:
        return load(run), []
    if not (_read(run, "03-injection.md") or _read(run, "06-brief.md")):
        return None, ["no stage 3 or stage 6 output to read"]
    brand = brand_of(run)
    f = facts(run)
    cache = run / "out" / ".swaps-reader.json"
    raw = None
    if cache.is_file() and not force:
        try:
            raw = json.loads(cache.read_text())
        except ValueError:
            raw = None
    if raw is None:
        try:
            for _try in range(3):                                # a reply that is not whole json is asked for again
                try:
                    raw = _json_of((reader or default_reader)(reader_prompt(run, f), "swaps-" + run.name))
                    break
                except ValueError:
                    raw = None
        except Exception as e:                                  # noqa: BLE001  a failed read is a listed problem
            return None, [f"the reading call failed: {type(e).__name__}: {str(e)[:160]}"]
        if raw is None:
            return None, ["the reader did not return a record"]
        cache.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    rec = _clean(raw, brand, "backfill")
    ev = {}
    # the plain signals win over the reader where they settle a call
    pc, why = product_call(f)
    if pc is not None:
        rec["product_in_frame"] = pc
        ev["product"] = why
        if pc is False:
            rec["product_where"], rec["product_sides"], rec["product_kit"] = None, [], None
            rec["swaps"] = [s for s in rec["swaps"] if s["kind"] != "product"]
        elif not rec["product_where"]:
            rec["product_where"] = (raw.get("product_where") or "where the brief places it")
    elif rec["product_in_frame"] in (True, False):
        ev["product"] = "read by the fast reader: " + str(raw.get("product_evidence") or "no evidence given")
        if rec["product_in_frame"] is False and any(x["kind"] == "product" for x in rec["swaps"]):
            rec["product_in_frame"] = None            # the reading contradicts itself: listed, not guessed
            rec["swaps"] = [x for x in rec["swaps"] if x["kind"] != "product"]
            raw = {**raw, "product_evidence": "the reading says no product in frame yet lists product swaps: " + str(raw.get("product_evidence") or "")[:160]}
    wc, wwhy = words_call(f)
    if wc is not None:
        rec["words"], ev["words"] = wc, wwhy
    elif rec["words"] in WORDS:
        ev["words"] = "read by the fast reader: " + str(raw.get("words_evidence") or "no evidence given")
    else:
        rec["words"], ev["words"] = "set_on_top", "no type layer and no words in the scene named: nothing to draw"
    if rec["product_in_frame"] is True and not rec["product_kit"]:
        prod_text = " ".join([rec.get("product_where") or ""] + [x["to"] for x in rec["swaps"] if x["kind"] == "product"]
                             + [raw.get("product_evidence") or ""] + f["yes_product_sentences"] + [str(f["plate_product_refs"])])
        rec["product_kit"] = (next((x["ref"] for x in rec["swaps"] if x["kind"] == "product" and x["ref"]), None)
                              or kit_from_text(brand, prod_text) or kit_from_text(brand, _read(run, "03-injection.md") + " " + _read(run, "06-brief.md")))
        ev["product_kit"] = "named in the text" if rec["product_kit"] else "the text names no product kit"
        if not rec["product_kit"]:
            rec["unclear"] = ["product is in frame but the text names no kit"]
    if rec["product_in_frame"] is None:
        rec["unclear"] = [str(raw.get("product_evidence") or "the text does not say whether the product is in frame")]
    if rec["product_in_frame"] is True and not rec["product_where"]:
        rec["product_where"] = "where the brief places it"
    if not rec["swaps"]:                                         # the reader gave none: the plain `X becomes Y` lines
        rec["swaps"] = [{"from": b["from"], "to": b["to"],
                         "kind": "cast" if match_cast(brand, b["to"]) else "drawn",
                         "ref": match_cast(brand, b["to"])} for b in bullets(_read(run, "03-injection.md"))]
    rec["evidence"] = ev
    bad = validate(rec)
    if bad:
        return None, bad
    write(run, rec)
    return rec, []


# ───────────────────────── what a maker takes from the record ─────────────────────────

def pictures_for(run, rec=None):
    """The reference pictures this record calls for, as [(path, role)]: one cast photo per cast swap whose id has one, a
    library photo per library swap. The swipe and the product's own pictures are sent by the maker (swaps rule 3)."""
    rec = rec or load(run)
    if not rec:
        return []
    brand, out = brand_of(run), []
    for s in rec["swaps"]:
        if s["kind"] == "cast" and s.get("ref"):
            ph = cast_photo(brand, s["ref"])
            if ph:
                out.append((ph, f"{s['to']}: her face and look, exactly as in this photo (replaces {s['from']})"))
        elif s["kind"] == "library" and s.get("ref"):
            d = P.REPO / s["ref"]
            ph = next((x for x in sorted(d.glob("*.jp*g")) + sorted(d.glob("*.png"))), None) if d.is_dir() else None
            if ph:
                out.append((ph, f"{s['to']}: exactly as in this photo (replaces {s['from']})"))
    return out


def words_layer(run):
    """The brief's own type layer, for the compositor (swaps rule 4): the words as the brief sets them, over a picture made with none.
    No brief yet (since 2026-10-27 it is written after the first picture is approved): the swipe's own layout from the
    replication spec, every colour moved to the nearest one in the brand's palette (the swipe's colours are never ours)."""
    got = type_layer(_read(run, "06-brief.md"))
    if got:
        return got
    spec = type_layer(_read(run, "02-replication-spec.md"))
    return _in_brand_colours(spec, brand_of(run)) if spec else None


HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def _in_brand_colours(layer, brand):
    """Every #rrggbb in a layer moved to the nearest colour the brand's palette.md names; unchanged with no palette."""
    try:
        text = (P.REPO / "brands" / brand / "brand-identity" / "palette.md").read_text()
    except OSError:
        return layer
    pal = sorted({h.upper() for h in HEX.findall(text)})
    if not pal:
        return layer
    # the swipe's ACCENT (a strong, bright colour: its giant sale word, its button) becomes the brand's accent, never just
    # the nearest swatch by distance (2026-10-28: a bright orange "SALE" came out in the brand's dull shadow colour)
    # only the palette's own colour rows (a "|" table row) name the accent; a note further down the page quoting another
    # brand's colour is not ours (2026-10-28: a swiped pink, quoted as a past mistake, was taken as the accent)
    rows = [line for line in text.splitlines() if line.lstrip().startswith("|")]
    accent = next((HEX.findall(line)[0].upper() for line in rows if "accent" in line.lower() and HEX.search(line)), None)
    pal = sorted({h.upper() for line in rows for h in HEX.findall(line)}) or pal
    rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

    def strong(h):
        c = rgb(h)
        return max(c) >= 160 and (max(c) - min(c)) / max(c) >= 0.6
    near = lambda h: min(pal, key=lambda p: sum((a - b) ** 2 for a, b in zip(rgb(h), rgb(p))))
    return json.loads(HEX.sub(lambda m: accent if accent and strong(m.group(0)) else near(m.group(0)), json.dumps(layer)))


def show(rec):
    lines = [f"product in frame: {rec['product_in_frame']}"
             + (f" · {rec.get('product_where')} · {', '.join(rec.get('product_sides') or [])}" if rec["product_in_frame"] else ""),
             f"words: {rec['words']} · source: {rec['source']}", "stays: " + "; ".join(rec["stays"])[:160]]
    lines += [f"  [{s['kind']:7}] {s['from'][:50]} → {s['to'][:60]}" + (f"  ({s['ref']})" if s.get("ref") else "") for s in rec["swaps"]]
    return "\n".join(lines)


def _runs(names, all_):
    # every run works in runs/image-teardown/<brand>/<label>/ since 2026-10-28: the teardown's paths find it
    if all_:
        return [d for d in P.all_runs() if (d / "out" / "03-injection.md").is_file() or (d / "out" / "06-brief.md").is_file()]
    return [Path(n) if Path(n).is_dir() else P.run_dir(n) for n in names]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "check", "stage", "backfill"])
    ap.add_argument("run", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="read again with the model, ignoring what was remembered")
    ap.add_argument("--redo", action="store_true", help="write the record again from what was remembered (no model call)")
    a = ap.parse_args()
    runs = _runs(a.run, a.all)
    code = 0
    for r in runs:
        if a.cmd == "show":
            rec = load(r)
            print(f"{r.name}\n{show(rec) if rec else '  no record'}\n")
        elif a.cmd == "check":
            rec = load(r)
            bad = validate(rec) if rec else ["no out/swaps.json"]
            print(f"{r.name}: " + ("ok" if not bad else "; ".join(bad)))
            code |= bool(bad)
        elif a.cmd == "stage":
            rec, bad = from_stage3(r)
            if rec:
                write(r, rec)
            print(f"{r.name}: " + ("written" if rec else "; ".join(bad)))
            code |= bool(bad)
        else:
            rec, bad = backfill(r, force=a.force, redo=a.redo)
            print(f"{r.name}: " + (f"product {rec['product_in_frame']} · words {rec['words']} · {len(rec['swaps'])} swaps" if rec else "; ".join(bad)))
            code |= bool(bad)
    sys.exit(code)


if __name__ == "__main__":
    main()
