#!/usr/bin/env python3
"""reference_check — the proof that a returned file was made from its references.

    python3 tools/image-edit/reference_check.py <hand-off folder>              check every returned file
    python3 tools/image-edit/reference_check.py <hand-off folder> --no-judge   the same, without the look judge



A hand-off folder (`runs/handoffs/<role>/<brand>/<brief key>/`) holds the run sheet (`run.json`: per step the exact
prompt and every reference, in order) and `returned/` (what the maker sent back). Beside each returned file:

  <asset>.record.json   HIGGSFIELD'S OWN RECORD of the generation, saved unchanged by an agent with the Higgsfield tools
                        (show_generations / show_generation_by_ids): id, model, params.prompt (exactly what was sent),
                        params.medias[], params.reference_elements[], the settings, results.rawUrl. THE AUTHORITY: when
                        it is there it is what gets checked, never the maker's word (2026-10-28: a retyped prompt had
                        turned "Shaved" into "Shared", lost symbols and dropped never-rules; only the record showed it).
                        Higgsfield's public API cannot read it back: a web-app or MCP generation id is "Not found" on
                        GET /requests/<id>/status and "Job set not found" on GET /v1/job-sets/<id> (probed 2026-10-28).
  <asset>.receipt.json  the maker's own account (components/briefs runsheet.py's return step): used when no record
  <asset>.link.txt      a person in the web app: the generation's link, one line

Per returned file, against its own step in run.json, five checks:

  receipt   is there one, is it readable, is it for this asset and step, on the sheet's model (a record: its id, its
            status, its model, and whether its result is the returned file)
  prompt    the prompt sent equals the step's prompt word for word (whitespace aside; the step's element placeholders
            aside; an element put in for its files exactly as runsheet.element_swap_line says); a "Words set on top
            afterwards" block in the prompt is wrong on its own ("words appended to the prompt")
  inputs    every reference the step names went in, in order: matched by refs/ name, element name or id, bytes, or (a
            record's media) the picture itself, a downloaded public https file against the refs/ file
  settings  the step's settings (aspect, quality, resolution, variant, ...) against what was sent
  looks     a judge pass with the step's references in front of it: the product matches its sheet, each cast face its
            cast picture, the picture its reference (a video: its first frame against the start picture and cast)

Each is ok (✓), bad (✗), amber (–, not proven: no receipt, a link only, no judge) or n/a (a step with no model call).
The judge is image-production's (`judge.seen` with `route.judge_entry()`; the key by name through the one loader,
never printed); with no key or no network the look is "not judged", never faked. Writes `reference-check.json` and
`REFERENCE-CHECK.md` beside `returned/`, and each file's verdict into the brief's `delivery.json`
(`reference_check`). Reads the hand-off folder; writes only those three files. Never stops a delivery: delivery.py
calls `check()` after it brings files in and keeps going whatever happens here.
"""
import argparse
import difflib
import hashlib
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
from image_edit import paths as P  # noqa: E402

OK, BAD, AMBER, NA = "ok", "bad", "amber", "n/a"
MARK = {OK: "✓", BAD: "✗", AMBER: "–", NA: "n/a"}
RETURNED = "returned"
RECEIPT, LINK, RECORD = ".receipt.json", ".link.txt", ".record.json"
SIDECARS = (RECORD, RECEIPT, LINK)
COLS = ("receipt", "prompt", "inputs", "settings", "looks")
WORDS_BLOCK = re.compile(r"(?mi)^[ \t]*words set on top afterwards\b")
LOOK_BITS, LOOK_MAD = 4, 2.5      # the same picture re-encoded: a 16x16 difference hash and a 36x64 grey mean, both tight
MEDIA = {".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
         ".mp4": "video", ".mov": "video", ".m4v": "video"}
OUT_JSON, OUT_MD = "reference-check.json", "REFERENCE-CHECK.md"
FETCH_LIMIT = 80 * 1024 * 1024
JUDGE_SIDE = 1600                  # the long side a picture is sent to the judge at


UNCLEAR = "TOO SMALL TO TELL"     # the judge's word for "there, but not provable at this size": amber, not wrong


class NotJudged(Exception):
    """The look judge could not run (no key, no network, no frame): the look is amber, never a pass."""


# ---------------------------------------------------------------------------------------------- small helpers
def _read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _write_json(p, d):
    p = Path(p)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(p)


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(P.repo().resolve()))
    except (ValueError, FileNotFoundError):
        return str(p)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise(text):
    """Whitespace-normalised: every run of spaces, tabs and newlines is one space."""
    return " ".join(str(text or "").split())


def overall(*states):
    s = [x for x in states if x != NA]
    return BAD if BAD in s else AMBER if AMBER in s or not s else OK


# ---------------------------------------------------------------------------------------------- 1. the receipt
def sidecar(asset, suffix):
    """The receipt or link file beside a returned file: `<stem><suffix>` (the run sheet's form) or `<name><suffix>`."""
    asset = Path(asset)
    for cand in (asset.with_name(asset.stem + suffix), asset.with_name(asset.name + suffix)):
        if cand.is_file():
            return cand
    return None


def generation_record(data):
    """The one generation in what a Higgsfield tool returned: the record itself (it has `params`), or the tool's reply
    around it (`{"items": [record], "jobs": [...]}`, or a list). (record, None) or (None, why)."""
    if isinstance(data, dict) and isinstance(data.get("params"), dict):
        return data, None
    items = data.get("items") if isinstance(data, dict) else data if isinstance(data, list) else None
    if not isinstance(items, list):
        return None, "not a Higgsfield generation record (no params)"
    items = [x for x in items if isinstance(x, dict) and isinstance(x.get("params"), dict)]
    if len(items) == 1:
        return items[0], None
    return None, (f"holds {len(items)} generations: save the one this file came from" if items
                  else "not a Higgsfield generation record (no params)")


def _url_name(url):
    try:
        return Path(urlparse(str(url)).path).name
    except ValueError:
        return ""


def record_view(rec):
    """A generation record read the way a receipt is: id, model, prompt, inputs in order (medias, then elements),
    settings (`variant` is the record's params.model), status, result. Nothing in it is the maker's word."""
    p = rec.get("params") or {}
    ins = []
    for m in p.get("medias") or []:
        d = (m.get("data") or {}) if isinstance(m, dict) else {}
        ins.append({"kind": (m.get("role") if isinstance(m, dict) else None) or "image", "media_id": d.get("id"),
                    "url": d.get("url"), "name": _url_name(d.get("url"))})
    for e in p.get("reference_elements") or []:
        if isinstance(e, dict):
            ins.append({"kind": "element", "element_id": e.get("id"), "name": e.get("name"), "file": e.get("name")})
    st = {k: p[k] for k in ("aspect_ratio", "quality", "resolution", "width", "height", "duration", "generate_audio",
                            "seed") if p.get(k) is not None}
    if p.get("model") and _model_word(p["model"]) != _model_word(rec.get("model")):
        st["variant"] = p["model"]
    return {"higgsfield_generation_id": rec.get("id"), "model": rec.get("model"), "prompt": p.get("prompt"),
            "inputs": ins, "settings": st, "status": rec.get("status"),
            "result": (rec.get("results") or {}).get("rawUrl") or rec.get("result_url")}


def read_receipt(asset):
    """{"kind": "record"|"json"|"link"|None, "file", "data", "error"}. Higgsfield's own record first, then the maker's
    receipt, then a link. One that will not parse is named, not guessed (and never falls back to the maker's word)."""
    r = sidecar(asset, RECORD)
    if r:
        try:
            raw = json.loads(r.read_text())
        except ValueError as e:
            return {"kind": "record", "file": r.name, "data": None, "error": f"{r.name} is not readable JSON ({e})"}
        rec, why = generation_record(raw)
        if why:
            return {"kind": "record", "file": r.name, "data": None, "error": f"{r.name}: {why}"}
        return {"kind": "record", "file": r.name, "data": record_view(rec), "error": None}
    j = sidecar(asset, RECEIPT)
    if j:
        try:
            data = json.loads(j.read_text())
        except ValueError as e:
            return {"kind": "json", "file": j.name, "data": None, "error": f"{j.name} is not readable JSON ({e})"}
        if not isinstance(data, dict):
            return {"kind": "json", "file": j.name, "data": None, "error": f"{j.name} is not one JSON object"}
        return {"kind": "json", "file": j.name, "data": data, "error": None}
    k = sidecar(asset, LINK)
    if k:
        line = next((x.strip() for x in k.read_text(errors="replace").splitlines() if x.strip()), "")
        if not re.match(r"https?://\S+$", line):
            return {"kind": "link", "file": k.name, "data": None, "error": f"{k.name} holds no link"}
        return {"kind": "link", "file": k.name, "data": {"link": line}, "error": None}
    return {"kind": None, "file": None, "data": None, "error": None}


def generation_id(data):
    for k in ("higgsfield_generation_id", "generation_id", "job_id", "higgsfield_job_id", "id"):
        if data.get(k):
            return str(data[k])
    return None


def _model_word(x):
    return re.sub(r"[^a-z0-9]+", "", str(x or "").lower())


def check_receipt(rc, step, asset_name):
    """The receipt column: present, readable, for this asset and this step, on the sheet's model."""
    if step and step.get("job") == "words-only":
        return {"state": NA, "why": "no model call in this step: nothing to receipt"}
    if not rc["kind"]:
        return {"state": AMBER, "why": "no receipt: can't prove the references"}
    if rc["error"]:
        return {"state": BAD, "why": rc["error"], "file": rc["file"]}
    if rc["kind"] == "link":
        return {"state": OK, "why": f"a generation link only ({rc['data']['link']})", "file": rc["file"],
                "link": rc["data"]["link"]}
    d, bad = rc["data"], []
    if rc["kind"] == "record":
        if str(d.get("status") or "completed").lower() != "completed":
            bad.append(f"the generation is {d['status']}, not completed")
    if d.get("asset") and Path(str(d["asset"])).stem != Path(asset_name).stem and step \
            and Path(str(d["asset"])).stem != Path(step["asset"]).stem:
        bad.append(f"it is for {d['asset']}, not this file")
    if step and d.get("step") not in (None, "") and str(d["step"]) != str(step["n"]):
        bad.append(f"it names step {d['step']}, this file is step {step['n']}'s")
    if step and step.get("job") != "set-change" and d.get("model") and _model_word(d["model"]) not in {_model_word(step.get("higgsfield_model")),
                                                                    _model_word(step.get("model_name"))}:
        bad.append(f"made with {d['model']}, the sheet says {step.get('higgsfield_model')}")
    if not generation_id(d):
        bad.append("no generation or job id")
    out = {"file": rc["file"], "source": "higgsfield record" if rc["kind"] == "record" else "maker's receipt",
           "generation": generation_id(d), "made_by": d.get("made_by"), "made_at": d.get("made_at"),
           "model": d.get("model")}
    if bad:
        return {"state": BAD, "why": "; ".join(bad), **out}
    return {"state": OK, "why": ("Higgsfield's own record of " if rc["kind"] == "record" else "") +
            f"generation {generation_id(d)}" + (f" by {d['made_by']}" if d.get("made_by") else ""), **out}


def result_match(rc, asset, fetch_media):
    """Is the returned file the record's own result? 'bytes' · 'looks' (the same picture) · 'differs' · None (not read).
    Said, never scored: the words set on top afterwards make most finished files differ from the raw result."""
    if not (rc.get("kind") == "record" and rc.get("data") and rc["data"].get("result") and fetch_media):
        return None
    data = fetch_media(rc["data"]["result"])
    if not data:
        return None
    if hashlib.sha256(data).hexdigest() == sha256(asset):
        return "bytes"
    return "looks" if same_picture(look_sig(data), look_sig(asset)) else "differs"


# ---------------------------------------------------------------------------------------------- 2. the prompt
def element_marks(step):
    """(ids, names) of every Higgsfield element the step may carry: the products' and the cast's."""
    ids, names = set(), set()
    for r in step.get("references") or []:
        el = ((r.get("element") or {}).get("element")) or {}
        if el.get("id"):
            ids.add(el["id"])
        if el.get("name"):
            names.add(el["name"])
    for c in step.get("cast") or []:
        el = c.get("element") or {}
        if el.get("id"):
            ids.add(el["id"])
        if el.get("name"):
            names.add(el["name"])
    return ids, names


def strip_marks(text, ids, names):
    """The prompt as sent, with the element placeholders the run sheet itself asks for set aside: `<<<id>>>` (the MCP
    route) and `@name` (the web app's @-mention), for this step's own elements only."""
    t, n = str(text or ""), 0
    for i in ids:
        t, k = re.subn(r"\s*<<<\s*" + re.escape(i) + r"\s*>>>", " ", t)
        n += k
    for nm in sorted(names, key=len, reverse=True):
        t, k = re.subn(r"(?<!\S)@" + re.escape(nm) + r"(?![\w-])", " ", t)
        n += k
    return normalise(t), n


def word_diff(want, got, hunks=6, context=5):
    """The places the sent prompt differs from the sheet's, word by word: [{"at", "sheet", "sent"}]."""
    a, b = want.split(), got.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        out.append({"at": " ".join(a[max(0, i1 - context):i1]), "sheet": " ".join(a[i1:i2]), "sent": " ".join(b[j1:j2])})
        if len(out) >= hunks:
            break
    return out


def _runsheet():
    """components/briefs/runsheet.py, for `element_swap_line` only (the one wording of an element put in for its files)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("briefs_runsheet_for_reference_check", P.sibling("briefs", "runsheet.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def element_groups(step):
    """The step's references an element carries, by element: [{"el": the reference's element, "images": [n, ...]}],
    the shape runsheet.element_swap_line takes."""
    by = {}
    for r in step.get("references") or []:
        e = r.get("element") or {}
        if (e.get("element") or {}).get("id"):
            by.setdefault(e["element"]["id"], {"el": e, "images": []})["images"].append(r["n"])
    return list(by.values())


_IMAGE_AT = re.compile(r"(?m)(?:^|(?<=[.:;] ))IMAGE (\d+) is ")


def swap_in_elements(prompt, step, swap_line=None):
    """The step's prompt with each element put in for its files, exactly as runsheet.element_swap_line says: the
    IMAGE lines it covers become its one line, every IMAGE numbered after them moves down. None when the step has no
    element or the line cannot be read."""
    groups = element_groups(step)
    if not groups:
        return None
    try:
        swap_line = swap_line or _runsheet().element_swap_line
    except Exception:                                                     # noqa: BLE001 — no sheet code, no swap form
        return None
    text = str(prompt)
    for g in sorted(groups, key=lambda x: min(x["images"]), reverse=True):
        imgs = sorted(g["images"])
        m = re.search(r'become this one line: "(.*?)" Any IMAGE', swap_line(g), re.S)
        if not m:
            return None
        starts = [(x.start(), int(x.group(1))) for x in _IMAGE_AT.finditer(text)]
        spans = []
        for i, (at, n) in enumerate(starts):
            eol = text.find("\n", at)
            eol = len(text) if eol < 0 else eol
            end = min(eol, starts[i + 1][0]) if i + 1 < len(starts) else eol
            if n in imgs:
                spans.append((at, end, n))
        if not spans:
            return None
        for at, end, n in reversed(spans):
            text = text[:at] + (m.group(1) + " " if n == imgs[0] else "") + text[end:]
        drop = len(imgs) - 1
        if drop:
            text = re.sub(r"\bIMAGE (\d+)\b",
                          lambda x: f"IMAGE {int(x.group(1)) - drop}" if int(x.group(1)) > imgs[-1] else x.group(0), text)
    return text


def name_marks(text, step):
    """The prompt as sent with the step's element placeholders (`<<<id>>>`, `@name`) read as the element's name."""
    t = str(text or "")
    for g in element_groups(step):
        hf = g["el"]["element"]
        name = hf.get("name") or hf["id"]
        t = re.sub(r"<<<\s*" + re.escape(hf["id"]) + r"\s*>>>", name, t)
        if hf.get("name"):
            t = re.sub(r"(?<!\S)@" + re.escape(hf["name"]) + r"(?![\w-])", name, t)
    return t


def split_words(sent):
    """(the prompt, the words block appended to it or None)."""
    m = WORDS_BLOCK.search(str(sent or ""))
    return (sent, None) if not m else (sent[:m.start()], sent[m.start():])


def words_lines(step):
    return "\n".join(f"- {w['zone']}: `{w['words']}`" for w in step.get("words_on_top") or [])


TRANSIT = "text altered in transit (Drive connector?)"


def _one_edit(a, b):
    """a and b differ by exactly one character put in, taken out or changed."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def _idish(word):
    """A word that is (or carries) an id or a number: it has a digit in it."""
    return any(c.isdigit() for c in word)


def is_transit(hunk):
    """One diff hunk whose only change is single characters inside ids or numbers: the same words, each changed one
    differing by one character, each with a digit in it (an element id with an extra 0, "11.15" become "11.5")."""
    a, b = hunk["sheet"].split(), hunk["sent"].split()
    pairs = [(x, y) for x, y in zip(a, b) if x != y]
    return len(a) == len(b) and bool(pairs) and all(_one_edit(x, y) and (_idish(x) or _idish(y)) for x, y in pairs)


def repair_marks(text, step):
    """`<<<id>>>` placeholders one character off one of the step's element ids: the text with the real id back, and
    [(sent, real)] — read as changed in transit, never as the element going in."""
    ids, _names = element_marks(step)
    found = []

    def fix(m):
        got = m.group(1).strip()
        real = next((i for i in ids if got != i and _one_edit(got, i)), None)
        if real:
            found.append((got, real))
            return m.group(0).replace(got, real)
        return m.group(0)
    return re.sub(r"<<<\s*([^<>]+?)\s*>>>", fix, str(text or "")), found


def check_prompt(rc, step):
    if not step:
        return {"state": NA, "why": "no step in the run sheet for this file"}
    if step.get("job") == "words-only" or not step.get("prompt"):
        return {"state": NA, "why": "no prompt in this step"}
    if rc["kind"] is None or rc["error"]:
        return {"state": AMBER, "why": "no receipt: the prompt sent is not known"}
    if rc["kind"] == "link":
        return {"state": AMBER, "why": "a link only: open it to read the prompt; not compared here"}
    sent = rc["data"].get("prompt")
    if not sent:
        return {"state": BAD, "why": ("the record" if rc["kind"] == "record" else "the receipt") + " carries no prompt"}
    body, words = split_words(sent)
    body, altered = repair_marks(body, step)
    ids, names = element_marks(step)
    got, marks = strip_marks(body, ids, names)
    want = normalise(step["prompt"])
    swapped = swap_in_elements(step["prompt"], step)
    cands = [(want, got, f" ({marks} element placeholder(s) set aside)" if marks else "")]
    if swapped:
        cands.append((normalise(swapped), normalise(name_marks(body, step)), " (the element line in for its files, "
                                                                              "as the run sheet says)"))
    same = next((note for w, g, note in cands if w == g), None)
    out, why = {}, []
    if words:
        why.append("words appended to the prompt (they are set on top afterwards, never sent)")
        out["words_appended"] = words.strip()
        listed = words.split("\n", 1)[1] if "\n" in words else ""            # the lines under its heading
        wd = word_diff(normalise(words_lines(step)), normalise(listed), hunks=12)
        if wd and step.get("words_on_top"):
            why.append(f"and those words differ from the sheet's in {len(wd)} place(s)")
            out["words_diff"] = wd
    if same is None:
        w, g, _ = max(cands, key=lambda c: difflib.SequenceMatcher(None, c[0].split(), c[1].split(),
                                                                    autojunk=False).ratio())
        cap = 12 if rc["kind"] == "record" else 6
        d = word_diff(w, g, hunks=cap)
        moved = [h for h in d if is_transit(h)]
        if d and len(moved) == len(d) and len(d) < cap:
            why.insert(0, f"{TRANSIT}: the prompt differs from the sheet's only in single characters inside ids or "
                          f"numbers, in {len(d)} place(s)")
        else:
            why.insert(0, f"the prompt sent differs from the sheet's in {len(d)}{'+' if len(d) >= cap else ''} place(s)"
                       + (f", {len(moved)} of them single characters inside ids or numbers ({TRANSIT})" if moved else ""))
        out["diff"] = d
        if moved:
            out["transit"] = moved
    if altered:
        why.insert(0, f"{TRANSIT}: element id " + ", ".join(f"<<<{g}>>> for <<<{r}>>>" for g, r in altered))
        out["altered_ids"] = [{"sent": g, "sheet": r} for g, r in altered]
    if why:
        return {"state": BAD, "why": "; ".join(why), **out}
    return {"state": OK, "why": "word for word" + same}


# ---------------------------------------------------------------------------------------------- 3. the inputs
def _ref_path(r, folder):
    """A step reference's file on this machine: the hand-off folder's refs/ copy, else its repo path, else its source."""
    for cand in (Path(folder) / r["local"] if r.get("local") else None,
                 P.repo() / r["file"] if r.get("file") and "(not " not in str(r["file"]) else None,
                 P.repo() / r["source"] if r.get("source") else None):
        if cand and cand.is_file():
            return cand
    return None


def expected_inputs(step, folder):
    """What the step says goes in: its references in order, then its cast. [{"n", "kind", "label", "names",
    "element_ids", "element_names", "path", "cast"}]."""
    out = []
    for r in step.get("references") or []:
        if r.get("look_only"):                        # a set change's kept print: the look check's, not an input
            continue
        el = (r.get("element") or {})
        hf = el.get("element") or {}
        names = {Path(str(x)).name.lower() for x in (r.get("local"), r.get("file"), r.get("source")) if x}
        out.append({"n": r["n"], "kind": r.get("kind", "image"),
                    "label": f"{'IMAGE' if r.get('kind', 'image') == 'image' else str(r.get('kind')).upper()} {r['n']}"
                             f" ({Path(str(r.get('local') or r.get('file'))).name})",
                    "names": names, "element_ids": {hf["id"]} if hf.get("id") else set(),
                    "element_names": {hf["name"].lower()} if hf.get("name") else set(),
                    "path": _ref_path(r, folder), "cast": None, "product": el.get("kind") == "product"})
    for c in step.get("cast") or []:
        el, fb = c.get("element") or {}, c.get("fallback") or {}
        names = {Path(str(x)).name.lower() for x in (fb.get("local"), fb.get("file"), fb.get("source")) if x}
        path = None
        for cand in ((Path(folder) / fb["local"]) if fb.get("local") else None,
                     (P.repo() / fb["source"]) if fb.get("source") else None):
            if cand and cand.is_file():
                path = cand
                break
        out.append({"n": None, "kind": "cast", "label": f"cast {c['who']}", "names": names,
                    "element_ids": {el["id"]} if el.get("id") else set(),
                    "element_names": {el["name"].lower()} if el.get("name") else set(),
                    "path": path, "cast": c["who"], "product": False})
    return out


def is_public_https(url):
    """Only a public https address is ever downloaded: no http, no localhost, no private or link-local address."""
    try:
        u = urlparse(str(url))
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if u.scheme != "https" or not host or host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." in host
    return ip.is_global


def fetch_bytes(url, timeout=60):
    """A public https file's bytes, read to at most FETCH_LIMIT and kept in memory, never written to disk. None if not
    read. Cached per run: a record's result and its media are read once."""
    import urllib.request
    if not is_public_https(url):
        return None
    if url in _FETCHED:
        return _FETCHED[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "reference-check/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:      # noqa: S310 — https only, checked above
            buf, n = [], 0
            for chunk in iter(lambda: resp.read(1 << 20), b""):
                n += len(chunk)
                if n > FETCH_LIMIT:
                    return None
                buf.append(chunk)
            data = b"".join(buf)
    except Exception:                                                     # noqa: BLE001 — not read is not a match
        return None
    if len(_FETCHED) > 16:
        _FETCHED.clear()
    _FETCHED[url] = data
    return data


_FETCHED = {}


def fetch_hash(url, timeout=30):
    """sha256 of a public https file (fetch_bytes). None if not read."""
    data = fetch_bytes(url, timeout)
    return hashlib.sha256(data).hexdigest() if data else None


def look_sig(src):
    """A picture's look, for "the same picture, re-encoded": (16x16 difference hash, 36x64 grey thumbnail), or None
    (no Pillow, not a picture). `src` is a path or the bytes."""
    try:
        import io
        from PIL import Image, ImageOps
        im = Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
        g = im.convert("L")
        d = list(ImageOps.fit(g, (17, 16)).getdata())
        bits = [d[r * 17 + c] > d[r * 17 + c + 1] for r in range(16) for c in range(16)]
        return bits, list(ImageOps.fit(g, (36, 64)).getdata())
    except Exception:                                                     # noqa: BLE001 — unreadable is not a match
        return None


def same_picture(a, b):
    """Two look signatures are the same picture: tight on both measures, so a picture and an edit of it are NOT the
    same (measured 2026-10-28 on a plate and its one-change edit: 7 bits, 4.9 grey apart)."""
    if not a or not b:
        return False
    bits = sum(x != y for x, y in zip(a[0], b[0]))
    mad = sum(abs(x - y) for x, y in zip(a[1], b[1])) / max(1, len(a[1]))
    return bits <= LOOK_BITS and mad <= LOOK_MAD


def _strings(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)
    elif x is not None:
        yield str(x)


def match_input(inp, expected, hashes, fetch, fetch_media=None, looks=None):
    """Which expected references one receipt input is: (indices, how). An element covers every reference it carries.
    With `fetch_media` (url -> bytes) a url is read once: its bytes, then (with `looks`, i -> the refs/ file's look) the
    picture itself, re-encoded or resized by the uploader."""
    if not isinstance(inp, dict):
        inp = {"file": str(inp)}
    text = " ".join(_strings(inp)).lower()
    hit = [i for i, e in enumerate(expected) if any(x.lower() in text for x in e["element_ids"])]
    if hit:
        return hit, "element id"
    fname = Path(str(inp.get("file") or inp.get("name") or "")).name.lower()
    if fname:
        hit = [i for i, e in enumerate(expected) if fname in e["element_names"]]
        if hit:
            return hit, "element name"
        hit = [i for i, e in enumerate(expected) if fname in e["names"]]
        if hit:
            return hit, "file name"
    digest, data = str(inp.get("sha256") or "").lower() or None, None
    if not digest and inp.get("url"):
        if fetch_media:
            data = fetch_media(inp["url"])
            digest = hashlib.sha256(data).hexdigest() if data else None
        else:
            digest = fetch(inp["url"])
    if digest:
        hit = [i for i, e in enumerate(expected) if hashes(i) == digest]
        if hit:
            return hit, "file bytes"
    if data and looks:
        sig = look_sig(data)
        hit = [i for i, e in enumerate(expected) if e["path"] and not e["element_ids"] and same_picture(sig, looks(i))]
        if hit:
            return hit[:1], "the picture"
    return [], None


def check_inputs(rc, step, folder, fetch=fetch_hash, fetch_media=None):
    if not step:
        return {"state": NA, "why": "no step in the run sheet for this file"}
    if step.get("job") == "words-only":
        return {"state": NA, "why": "no model call in this step"}
    expected = expected_inputs(step, folder)
    if rc["kind"] is None or rc["error"]:
        return {"state": AMBER, "why": "no receipt: which references went in is not known",
                "expected": [e["label"] for e in expected]}
    if rc["kind"] == "link":
        return {"state": AMBER, "why": "a link only: open it to see the references; not matched here",
                "expected": [e["label"] for e in expected]}
    got = rc["data"].get("inputs")
    if not isinstance(got, list):
        return {"state": BAD, "why": "the receipt lists no inputs", "expected": [e["label"] for e in expected]}
    cache, seen = {}, {}

    def hashes(i):
        if i not in cache:
            p = expected[i]["path"]
            cache[i] = sha256(p) if p else None
        return cache[i]

    def looks(i):
        if i not in seen:
            seen[i] = look_sig(expected[i]["path"]) if expected[i]["path"] else None
        return seen[i]

    covered, extra, order, rows = set(), [], [], []
    for k, inp in enumerate(got):
        idx, how = match_input(inp, expected, hashes, fetch, fetch_media, looks)
        name = (inp.get("file") or inp.get("name") or inp.get("url") or inp.get("media_id")) if isinstance(inp, dict) else inp
        if not idx:
            extra.append(f"input {k + 1} ({name})")
            continue
        covered.update(idx)
        rows.append({"input": k + 1, "is": [expected[i]["label"] for i in idx], "by": how})
        refs = [expected[i]["n"] for i in idx if expected[i]["n"] is not None]
        if how in ("file name", "file bytes", "the picture") and len(refs) == 1:
            said = inp.get("n") if isinstance(inp, dict) else None
            order.append((refs[0], said, name))
    missing = [expected[i]["label"] for i in range(len(expected)) if i not in covered]
    wrong = []
    for j, (n, said, name) in enumerate(order):
        if said not in (None, "") and str(said) != str(n):
            wrong.append(f"{name} went in as {said}, the sheet makes it {n}")
        if j and n < order[j - 1][0]:
            wrong.append(f"{name} (the sheet's {n}) went in after the sheet's {order[j - 1][0]}")
    why = []
    if missing:
        why.append("missing: " + ", ".join(missing))
    if extra:
        why.append("extra (not one of this step's references): " + ", ".join(extra))
    if wrong:
        why.append("out of order: " + "; ".join(wrong))
    base = {"matched": rows, "missing": missing, "extra": extra, "order": wrong}
    if why:
        return {"state": BAD, "why": "; ".join(why), **base}
    return {"state": OK, "why": f"all {len(expected)} in, in order", **base}


# ---------------------------------------------------------------------------------------------- 3b. the settings
SETTING_SKIP = {"endpoint", "count"}       # how the sheet calls it and how many rolls: not a setting of one generation


def _setting_word(v):
    return str(v).strip().lower()


def check_settings(rc, step):
    """The step's settings against what was sent: each one the sheet names must be there and the same."""
    if not step:
        return {"state": NA, "why": "no step in the run sheet for this file"}
    if step.get("job") == "words-only":
        return {"state": NA, "why": "no model call in this step"}
    want = {k: v for k, v in (step.get("settings") or {}).items() if k not in SETTING_SKIP and v not in (None, "")}
    if not want:
        return {"state": NA, "why": "the sheet names no settings for this step"}
    if rc["kind"] is None or rc["error"]:
        return {"state": AMBER, "why": "no receipt: the settings sent are not known"}
    if rc["kind"] == "link":
        return {"state": AMBER, "why": "a link only: open it to read the settings; not compared here"}
    sent = rc["data"].get("settings")
    if not isinstance(sent, dict):
        return {"state": AMBER, "why": ("the record" if rc["kind"] == "record" else "the receipt") + " names no settings"}
    bad = [f"{k} {sent[k]}, the sheet says {v}" for k, v in want.items()
           if k in sent and _setting_word(sent[k]) != _setting_word(v)]
    unsaid = [k for k in want if k not in sent]
    said = " · ".join(f"{k} {want[k]}" for k in want if k in sent)
    if bad:
        return {"state": BAD, "why": "; ".join(bad), "sent": sent}
    if unsaid:
        return {"state": AMBER, "why": "not stated: " + ", ".join(unsaid) + (f" (the rest match: {said})" if said else ""),
                "sent": sent}
    return {"state": OK, "why": said, "sent": sent}


# ---------------------------------------------------------------------------------------------- 4. the look
def look_plan(step, folder, medium):
    """The judge's tests and the reference pictures it sees beside the returned file: [(test)], [(path, label)]."""
    refs = step.get("references") or []
    imgs, tests = [], []

    def add(path, label):
        imgs.append((path, label))
        return len(imgs) + 1                      # IMAGE 1 is the returned file

    scene = None
    if medium == "video":
        scene = next((r for r in refs if r.get("kind") == "image" and "start" in f"{r.get('role')} {r.get('local')}".lower()),
                     None)
    scene = scene or next((r for r in refs if r.get("kind", "image") == "image" and not (r.get("element") or {}).get("kind")
                           and r.get("n") == 1), None)
    if scene and _ref_path(scene, folder):
        if medium == "video":
            k = add(_ref_path(scene, folder), "the clip's start picture")
            tests.append(f"FIRST FRAME FROM ITS START PICTURE — IMAGE 1 (the clip's first frame) shows the same scene as "
                         f"IMAGE {k} (its start picture): the same setting, people, framing and pose. FAIL if it is "
                         "plainly a different scene, person or framing.")
        elif step.get("job") == "words-only":
            k = add(_ref_path(scene, folder), "the plate this picture is set on")
            tests.append(f"BUILT ON ITS PLATE — IMAGE 1 is IMAGE {k} with words set on top: the same scene, people, "
                         "product and framing. FAIL if anything but the words differs.")
        else:
            role = str(scene.get("role") or "the reference").split(":")[0]
            k = add(_ref_path(scene, folder), role)
            tests.append(f"BUILT ON ITS REFERENCE — IMAGE 1 is built on IMAGE {k} ({role}): the same setting, camera "
                         "angle, framing and pose. People may be lookalikes and the things the brief swaps may differ; "
                         "FAIL only if IMAGE 1 is plainly a different scene or composition.")
    if step.get("job") == "set-change":
        tests.append(f"THE SET CHANGE IS THERE — {(step.get('set_request') or {}).get('change')}. FAIL if IMAGE 1 does not "
                     "show it, or if anything else in the set moved.")
    prods = {}
    for r in refs:
        el = r.get("element") or {}
        if el.get("kind") == "product" and _ref_path(r, folder):
            prods.setdefault(el.get("name") or el.get("id"), []).append(r)
    for name, rs in prods.items():
        rs = sorted(rs, key=lambda r: (0 if "sheet" in str(r.get("local") or r.get("file")) else 1, r["n"]))[:2]
        ks = [add(_ref_path(r, folder), f"the real {name}, {'its product sheet' if 'sheet' in str(r.get('local')) else 'a photo of it'}")
              for r in rs]
        tests.append(f"PRODUCT MATCHES ITS SHEET — the {name} that appears in IMAGE 1 is the real {name} shown in "
                     f"IMAGE {' and IMAGE '.join(map(str, ks))}: the same shape, colour, finish and label or wordmark. "
                     f"FAIL if it differs in any of these, or if no {name} can be seen in IMAGE 1. If it is there but "
                     f"too small or too soft to tell, FAIL and start the evidence with {UNCLEAR}.")
    for c in step.get("cast") or []:
        e = [x for x in expected_inputs({"cast": [c]}, folder) if x["path"]]
        if e:
            k = add(e[0]["path"], f"{c['who']}'s cast picture")
            tests.append(f"FACE MATCHES THE CAST — {c['who']}: the person in IMAGE 1 who plays {c['who']} has the same "
                         f"face as IMAGE {k} (their cast picture): face shape, skin tone, hair and age. FAIL if it is a "
                         f"different person, or {c['who']} cannot be found in IMAGE 1.")
    return tests, imgs


def _judge_copy(src, dest_dir, tag):
    """A judge-sized JPEG of a picture (Pillow; the original when Pillow is not here)."""
    try:
        from PIL import Image
    except ImportError:
        return Path(src)
    out = Path(dest_dir) / f"{tag}.jpg"
    with Image.open(src) as im:
        im = im.convert("RGB")
        im.thumbnail((JUDGE_SIDE, JUDGE_SIDE))
        im.save(out, "JPEG", quality=90)
    return out


def first_frame(video, dest_dir):
    out = Path(dest_dir) / "first-frame.png"
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-frames:v", "1", str(out)],
                       check=True, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise NotJudged(f"no first frame read from the clip ({type(e).__name__})")
    if not out.is_file():
        raise NotJudged("no first frame read from the clip")
    return out


def gemini_judge(img, tests, images):
    """image-production's judge door: `judge.seen` with `route.judge_entry()`, the returned file as IMAGE 1 and the
    references after it (image-edit's compare caller, which sends several pictures through the same door). Returns
    (fails, raw, model). A judge that cannot run raises NotJudged; it is never a pass."""
    ip = P.image_production()
    R, J = ip.route, ip.judge
    entry = R.judge_entry()
    if not R.key_value(R.key_name(entry)):             # asked by name through the one loader; never printed
        raise NotJudged(f"no {R.key_name(entry)} on this machine")
    from image_edit import compare
    lead = ("IMAGE 1 is the picture being checked. " + " ".join(f"IMAGE {i + 2} is {lab}." for i, (_p, lab) in
                                                                 enumerate(images))
            + " The other images are only the references it is compared against.\n\n")
    caller = (lambda prompt, path, ent: compare.google_caller(lead + prompt, [path] + [str(p) for p, _ in images], ent))
    fails, raw = J.seen(str(img), tests, entry, caller=caller)
    if any(f.startswith("judge did not run") for f in fails):
        raise NotJudged(fails[0][:240])
    return fails, raw, entry.get("vendor_model")


def _per_test(tests, fails, raw):
    ev = {}
    try:
        for r in json.loads(raw[raw.index("{"):raw.rindex("}") + 1]).get("results") or []:
            ev[int(r.get("test"))] = (str(r.get("verdict", "")).upper(), str(r.get("evidence", "")))
    except Exception:                                                      # noqa: BLE001 — evidence is a nicety
        pass
    out = []
    for i, t in enumerate(tests):
        name = t.split(" — ")[0]
        v, e = ev.get(i + 1, ("", ""))
        said_fail = any(f.startswith(t.split(".")[0]) for f in fails)
        if not v and not said_fail:                       # asked and not answered: not judged, never a pass or a fail
            out.append({"test": name, "verdict": "unclear", "evidence": "the judge did not answer this test"})
            continue
        failed = said_fail or v != "PASS"
        unclear = failed and e.strip().upper().startswith(UNCLEAR)
        out.append({"test": name, "verdict": "unclear" if unclear else "fail" if failed else "pass", "evidence": e})
    return out


def check_looks(asset, step, folder, judge, prior=None):
    if not step:
        return {"state": NA, "why": "no step in the run sheet for this file"}
    medium = MEDIA.get(Path(asset).suffix.lower(), "image")
    tests, images = look_plan(step, folder, medium)
    if not tests:
        return {"state": NA, "why": "no reference picture on this machine to judge against"}
    digest = sha256(asset)
    if prior and prior.get("sha256") == digest and prior.get("tests") == tests and prior.get("state") in (OK, BAD):
        return {**prior, "cached": True}
    base = {"sha256": digest, "tests": tests, "against": [lab for _p, lab in images]}
    if judge is False:
        return {"state": AMBER, "why": "not judged (switched off for this run)", **base}
    try:
        with tempfile.TemporaryDirectory(prefix="refcheck-") as tmp:
            src = first_frame(asset, tmp) if medium == "video" else Path(asset)
            img = _judge_copy(src, tmp, "checked")
            sent = [(_judge_copy(p, tmp, f"ref-{i + 1}"), lab) for i, (p, lab) in enumerate(images)]
            fails, raw, model = (judge or gemini_judge)(img, tests, sent)
    except NotJudged as e:
        return {"state": AMBER, "why": f"not judged: {e}", **base}
    except Exception as e:                                                 # noqa: BLE001 — never stops the check
        return {"state": AMBER, "why": f"not judged: {type(e).__name__}: {str(e)[:200]}", **base}
    rows = _per_test(tests, fails, raw)
    bad = [r for r in rows if r["verdict"] == "fail"]
    unclear = [r for r in rows if r["verdict"] == "unclear"]
    stray = [f for f in fails if not any(f.startswith(t.split(".")[0]) for t in tests)]   # an unanswered or unreadable reply
    state = BAD if bad else AMBER if unclear or stray else OK
    why = ("; ".join(f"{r['test']}: {r['evidence'] or 'failed'}" for r in bad) if bad
           else "; ".join(stray) if stray
           else "; ".join(f"{r['test']}: not provable at this size ({r['evidence']})" for r in unclear) if unclear
           else f"all {len(rows)} look tests pass")
    return {"state": state, "model": model, "results": rows, "fails": fails, "why": why, **base}


# ---------------------------------------------------------------------------------------------- the whole folder
def step_for(name, steps):
    stem = Path(name).stem
    for s in steps:
        st = Path(s["asset"]).stem
        if stem == st or re.match(re.escape(st) + r"-\d+$", stem):
            return s
    return None


def returned_files(folder):
    back = Path(folder) / RETURNED
    if not back.is_dir():
        return []
    return sorted(f for f in back.rglob("*") if f.is_file() and f.suffix.lower() in MEDIA
                  and not f.name.startswith("."))


def check(folder, judge=None, fetch=fetch_hash, write=True, fetch_media=None):
    """Every returned file in one hand-off folder, checked against its run sheet. `judge`: None = image-production's
    judge, False = no look judge, or a callable (img, tests, [(path, label)]) -> (fails, raw, model) (tests).
    `fetch_media` (url -> bytes) reads a record's media and result; by default the public https reader, unless the
    caller gave its own `fetch` (then only that is used).
    Writes reference-check.json, REFERENCE-CHECK.md and delivery.json's per-file verdict unless write=False."""
    folder = Path(folder)
    if fetch_media is None and fetch is fetch_hash:
        fetch_media = fetch_bytes
    sheet = _read_json(folder / "run.json")
    prior = {a["file"]: a.get("looks") for a in (_read_json(folder / OUT_JSON, {}) or {}).get("assets", [])}
    steps = (sheet or {}).get("steps") or []
    rows = []
    for f in returned_files(folder):
        rel = f.relative_to(folder).as_posix()
        step = step_for(f.name, steps)
        rc = read_receipt(f)
        row = {"file": rel, "step": step["n"] if step else None, "what": step["what"] if step else
               ("the cut, made from the clips" if f.stem.endswith("-control") else "not a step's asset name"),
               "medium": MEDIA[f.suffix.lower()],
               "source": {"record": "Higgsfield's record", "json": "the maker's receipt", "link": "a link"}.get(rc["kind"])}
        if not sheet:
            for k in COLS:
                row[k] = {"state": AMBER, "why": "no run.json in this folder: nothing to check against"}
        else:
            row["receipt"] = check_receipt(rc, step, f.name) if step else {"state": NA, "why": row["what"]}
            if step and rc["kind"] == "record" and not rc["error"]:
                same = result_match(rc, f, fetch_media)
                row["receipt"]["result"] = same
                if same:
                    row["receipt"]["why"] += {"bytes": "; the returned file IS its result, byte for byte",
                                              "looks": "; the returned file is its result (the same picture)",
                                              "differs": "; the returned file is not its raw result as saved (words set "
                                                         "on top, a resize, or another take)"}[same]
            row["prompt"] = check_prompt(rc, step)
            row["inputs"] = check_inputs(rc, step, folder, fetch, fetch_media)
            row["settings"] = check_settings(rc, step)
            row["looks"] = check_looks(f, step, folder, judge, prior.get(rel))
        if not step and sheet:
            row["overall"] = AMBER
        else:
            row["overall"] = overall(*(row[k]["state"] for k in COLS))
        rows.append(row)
    rep = {"what": "proof that each returned file was made from its run sheet's prompt and references",
           "checked": time.strftime("%Y-%m-%dT%H:%M"), "folder": _rel(folder),
           "brief_key": (sheet or {}).get("brief_key"), "run_sheet": "run.json" if sheet else None,
           "legend": {MARK[OK]: "proven", MARK[BAD]: "wrong", MARK[AMBER]: "not proven", MARK[NA]: "not needed"},
           "summary": {s: sum(1 for r in rows if r["overall"] == s) for s in (OK, AMBER, BAD)}, "assets": rows}
    if write:
        _write_json(folder / OUT_JSON, rep)
        (folder / OUT_MD).write_text(render_md(rep))
        record(folder, rep)
    return rep


def record(folder, rep):
    """Each file's verdict into the brief's delivery.json (`reference_check`), when the folder has one."""
    dj = Path(folder) / "delivery.json"
    d = _read_json(dj)
    if not isinstance(d, dict) or not isinstance(d.get("files"), list):
        return False
    by = {Path(r["file"]).name: r for r in rep["assets"]}
    for f in d["files"]:
        r = by.get(f.get("name") or Path(str(f.get("file"))).name)
        if r:
            f["reference_check"] = {"overall": r["overall"], **{k: r[k]["state"] for k in COLS},
                                    "source": r.get("source"), "checked": rep["checked"], "see": OUT_MD}
    _write_json(dj, d)
    return True


def summary(rep):
    s = rep["summary"]
    return f"{s[OK]} {MARK[OK]} · {s[AMBER]} {MARK[AMBER]} · {s[BAD]} {MARK[BAD]}"


def render_md(rep):
    L = [f"# Reference check · {rep.get('brief_key') or Path(rep['folder']).name}", "",
         "Was each returned file made from the run sheet's prompt and references? "
         f"{MARK[OK]} proven · {MARK[BAD]} wrong · {MARK[AMBER]} not proven · n/a not needed. "
         f"Checked {rep['checked']}.", "",
         "| File | Step | Proof from | Receipt | Prompt | Inputs | Settings | Looks | |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rep["assets"]:
        L.append(f"| `{Path(r['file']).name}` | {r['step'] or '-'} | {r.get('source') or 'nothing'} | " +
                 " | ".join(MARK[r[k]["state"]] for k in COLS) +
                 f" | **{MARK[r['overall']]}** |")
    if not rep["assets"]:
        L.append("| nothing in returned/ yet | | | | | | | | |")
    notes = []
    for r in rep["assets"]:
        bits = [f"{k}: {r[k]['why']}" for k in COLS if r[k]["state"] in (BAD, AMBER)]
        for d in (r["prompt"].get("diff") or [])[:12]:
            bits.append(f"prompt after “{d['at']}”: sheet “{d['sheet']}” · sent “{d['sent']}”")
        for d in (r["prompt"].get("words_diff") or [])[:6]:
            bits.append(f"appended words after “{d['at']}”: sheet “{d['sheet']}” · sent “{d['sent']}”")
        if bits or r["looks"].get("results"):
            notes.append(f"- **{Path(r['file']).name}**: " + (" · ".join(bits) or "every check proven"))
        for t in (r["looks"].get("results") or []):
            notes.append(f"  - {MARK[{'pass': OK, 'unclear': AMBER}.get(t['verdict'], BAD)]} {t['test']}: {t['evidence']}")
    if notes:
        L += ["", "## What is not proven, and what the judge saw", ""] + notes
    L += ["", "A ✗ is fixed in the chain (the prompt, the references) or the file is re-made; never patched by hand. "
          "A missing proof is asked for: `<asset>.record.json` beside the file, Higgsfield's own record of the generation "
          "saved unchanged by an agent with the Higgsfield tools (the authority), else `<asset>.receipt.json` (the run "
          "sheet's Return step says what goes in it), or `<asset>.link.txt` with the generation's link.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", help="a hand-off folder: runs/handoffs/<role>/<brand>/<brief key>")
    ap.add_argument("--no-judge", action="store_true", help="skip the look judge (spends nothing)")
    a = ap.parse_args(argv)
    folder = Path(a.folder)
    if not folder.is_absolute() and not folder.is_dir():
        folder = P.repo() / a.folder
    if not folder.is_dir():
        print(f"REFUSED: no folder {a.folder}")
        return 1
    rep = check(folder, judge=False if a.no_judge else None)
    print(f"{rep.get('brief_key') or folder.name}: {summary(rep)}  ->  {_rel(folder / OUT_MD)}")
    for r in rep["assets"]:
        print(f"  {Path(r['file']).name}  " + " ".join(f"{k} {MARK[r[k]['state']]}" for k in COLS) +
              f"  = {MARK[r['overall']]}" + (f"  ({r['looks']['why'][:160]})" if r['looks']['state'] != NA else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
