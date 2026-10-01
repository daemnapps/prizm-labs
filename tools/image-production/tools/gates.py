#!/usr/bin/env python3
"""The gates image production runs, and the record every batch files.

Three of the five shared gates (`components/quality-checks`) apply here:

    elements   before anything is made   the template, the style pack and the
                                         picture format a batch or brief names
                                         are real rows in the element library
                                         (`components/elements`)
    copy       before anything is made   the words burned into the picture —
                                         headline, subhead, offer bar — carry
                                         no UNFILLED note, and every price in
                                         them is one the brand's offer bank
                                         sells today
    media      after the judge           a picture the judge failed is HELD
                                         from delivery, with the judge's reason

`hold()` writes `check.json` into the run. **A held run says why**: printed
when it happens, in `check.json`, and in the filed record.

**The media gate does not judge.** The verdicts are `finish.py`'s and
`judge.py`'s, unchanged; this only writes them down as a gate and names what
was kept back. Survivors still ship — holding one picture never holds its
siblings.

    gates.py <run-dir>              print a run's check.json, plainly

Filing: every finished batch's record goes to
`runs/image-production/<brand>/<batch>/` at the repo root — `batch.json`, the
manifests, the verdicts, the prompts as sent, `elements.json`, `check.json`,
`report.md`. Text only. **Never a picture** — media stays on Drive.
"""
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

MODES = ("hold", "warn")
NO_TEMPLATE = (None, "", "prompted")      # the model draws its own type — no layout file
TEXT = {".json", ".md", ".txt"}           # the only things a record may carry
PICTURES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".psd",
            ".mp4", ".mov", ".heic", ".avif", ".bmp"}


def quality():
    """The shared checks — components/quality-checks."""
    if str(P.QUALITY) not in sys.path:
        sys.path.insert(0, str(P.QUALITY))
    import quality_checks as Q
    return Q


def library():
    """The element library — components/elements/machine/elements.py."""
    d = str(P.ELEMENTS / "machine")
    if d not in sys.path:
        sys.path.insert(0, d)
    import elements as E
    return E


def _gate(name, problems, run, mode="hold"):
    Q = quality()
    try:
        Q.hold(name, problems, Path(run) if run else None)
        return True
    except Q.Held as e:
        print(f"  ✗ {e}")
        if mode == "hold":
            raise
        print("  (gates are on warn — carrying on; check.json still says HELD)")
        return False


# ---------------------------------------------------------------- elements

def stem(v):
    """`confession`, `templates/confession.json` and a full path are one id."""
    v = str(v).strip()
    return Path(v).stem if ("/" in v or v.endswith(".json")) else v


def _ask(element, asset, value, where, problems):
    """One id, asked of the library. Unknown → refused with the real ids.
    A draft row that only reserves a name → refused as not defined yet."""
    E = library()
    try:
        row = E.get(element, asset, value)
    except E.Unknown as e:
        problems.append(f"{where}: {e.args[0]}")
        return
    if str(row.get("what") or "").lstrip().startswith("[TO DEFINE"):
        problems.append(f"{where}: `{value}` is named but not defined yet — the "
                        f"{element} list holds the name and no definition, so "
                        f"nothing can be built to it")


def picked_in_batch(spec, run=None):
    """(picked, problems) for a batch.json.

    template        `template` on the ad, else the batch. `prompted` means the
                    model draws its own type and no layout file is used.
    style pack      `pack` (or `style_pack`) on the ad, else the batch, else
                    the ad's slot file `slots/<slug>.json` when the run has one.
    picture format  `picture_format` on the ad, else the batch — a key of
                    `format-bank.json`. NOT the `format` field: that one is the
                    ad name's own vocabulary (components/naming) and is a
                    different list."""
    picked, problems = {"template": [], "style": [], "format": []}, []
    for ad in spec.get("ads") or []:
        slug = ad.get("slug", "?")
        t = ad.get("template", spec.get("template"))
        if t not in NO_TEMPLATE:
            t = stem(t)
            picked["template"].append(t)
            _ask("template", "image", t, slug, problems)
        pack = ad.get("pack") or ad.get("style_pack") or spec.get("pack") or spec.get("style_pack")
        if not pack and run:
            sf = Path(run) / "slots" / f"{slug}.json"
            if sf.is_file():
                try:
                    pack = json.loads(sf.read_text()).get("pack")
                except ValueError:
                    problems.append(f"{slug}: slots/{slug}.json is not valid JSON")
        if pack:
            picked["style"].append(pack)
            _ask("style", "image", pack, slug, problems)
        fmt = ad.get("picture_format") or spec.get("picture_format")
        if fmt:
            picked["format"].append(fmt)
            _ask("format", "image", fmt, slug, problems)
    picked = {k: sorted(set(v)) for k, v in picked.items()}
    return picked, sorted(set(problems))


def picked_in_brief(brief_path):
    """(picked, problems) for a teardown brief — the ```json block's `template`,
    `pack` / `style_pack`, and `picture_format`. A brief that still carries its
    own geometry names none of them, and that is a real answer."""
    import re
    picked, problems = {"template": [], "style": [], "format": []}, []
    m = re.search(r"```json\s*(\{.*?\})\s*```", Path(brief_path).read_text(errors="replace"), re.S)
    try:
        d = json.loads(m.group(1)) if m else {}
    except ValueError:
        d = {}
    where = Path(brief_path).parent.parent.name
    for key, (el, asset) in (("template", ("template", "image")),
                             ("pack", ("style", "image")),
                             ("style_pack", ("style", "image")),
                             ("picture_format", ("format", "image"))):
        v = d.get(key)
        if v in NO_TEMPLATE or not isinstance(v, str):
            continue
        v = stem(v)
        picked[el].append(v)
        _ask(el, asset, v, where, problems)
    return {k: sorted(set(v)) for k, v in picked.items()}, sorted(set(problems))


def _record_elements(run, picked, problems):
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    (run / "elements.json").write_text(json.dumps(
        {"asked": "components/elements", "picked": picked, "problems": problems,
         "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        indent=1, ensure_ascii=False) + "\n")


def elements_gate(run, spec, mode="hold"):
    picked, problems = picked_in_batch(spec, run)
    _record_elements(run, picked, problems)
    return _gate("elements", problems, run, mode)


def elements_gate_for_brief(run, brief_path, mode="hold"):
    picked, problems = picked_in_brief(brief_path)
    _record_elements(run, picked, problems)
    return _gate("elements", problems, run, mode)


# -------------------------------------------------------------------- copy

def built_words(brief_path):
    """The part of a teardown brief that gets built — documents one and two.
    Document three is the evidence table: it quotes the SOURCE ad and the
    market, and is not our copy."""
    import re
    text = Path(brief_path).read_text(errors="replace")
    m = re.search(r"^##\s*DOCUMENT THREE\b", text, re.M | re.I)
    return text[:m.start()] if m else text


def burned_words(spec):
    """[(where, text)] — every word that ends up inside the picture."""
    out = []
    bar = (spec.get("offer") or {}).get("bar_text")
    if bar:
        out.append(("offer bar", str(bar)))
    for ad in spec.get("ads") or []:
        for slot, text in (ad.get("copy") or {}).items():
            if isinstance(text, str) and text.strip():
                out.append((f"{ad.get('slug', '?')} · {slot}", text))
    return out


def copy_problems(spec, bank_text):
    Q = quality()
    key = (spec.get("offer") or {}).get("id")
    block = Q.offer_block(bank_text, key) if key else ""
    # No entry under this offer's key is not "no offer": brands key their bank
    # differently, so fall back to every price the bank holds rather than
    # holding every batch of a brand whose keys differ from its offer ids.
    against, label = (block, key) if block else (bank_text, None)
    problems = []
    for where, text in burned_words(spec):
        problems += [f"{where}: {p}" for p in Q.unfilled_check(text)]
        problems += [f"{where}: {p}" for p in Q.price_check(text, against, label)]
    return problems


def copy_gate(run, spec, mode="hold"):
    P.need_brand(spec.get("brand"), "the offer bank")
    bank = P.brand(spec["brand"])["offer"]
    bank_text = bank.read_text(errors="replace") if bank.is_file() else ""
    return _gate("copy", copy_problems(spec, bank_text), run, mode)


# ------------------------------------------------------------------- media

def media_gate(run, killed):
    """`killed` is the judge's own list: [(slug, [reason, ...])]. Writes the
    media gate into check.json — HELD naming each picture and why — and returns
    whether it is clean. It never raises: the survivors of a batch still ship,
    and the held pictures were already kept out of `ads/` by the judge."""
    problems = [f"{slug} — held from delivery: {'; '.join(map(str, fails)) or 'failed the judge'}"
                for slug, fails in killed]
    try:
        return _gate("media", problems, run, mode="warn") if problems else _gate("media", [], run)
    except Exception as e:                       # noqa: BLE001 — a gate that cannot write must say so, not stop a delivery
        print(f"  ! media gate could not be recorded: {e}")
        return not problems


def state(run):
    f = Path(run) / "check.json"
    try:
        return json.loads(f.read_text()) if f.is_file() else {}
    except ValueError:
        return {}


def held(run, gates=None):
    """{gate: [problems]} for every gate this run is held at."""
    return {g: v.get("problems", []) for g, v in state(run).items()
            if v.get("result") == "HELD" and (gates is None or g in gates)}


# ------------------------------------------------------------------ filing

def _copy_text(src, dst):
    """Text in, or nothing. The suffix is a whitelist, so a picture cannot
    travel even if something upstream starts writing them beside the text."""
    src = Path(src)
    if not src.is_file() or src.suffix.lower() not in TEXT or src.suffix.lower() in PICTURES:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return True


def _file(run, brand, label, pairs, extra):
    dst = P.RECORDS / brand / label
    dst.mkdir(parents=True, exist_ok=True)
    filed = []
    for src, rel in pairs:
        if _copy_text(src, dst / rel):
            filed.append(rel)
    try:
        lane_run = str(Path(run).resolve().relative_to(P.REPO))
    except ValueError:
        lane_run = str(run)
    h = held(run)
    (dst / "run.json").write_text(json.dumps(
        {"machine": P.TOOL, "brand": brand, "label": label, "lane_run": lane_run,
         **extra, "files": sorted(filed),
         "state": "held" if h else "filed", "held": h,
         "media": "on Drive — a record never carries a picture",
         "filed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        indent=1, ensure_ascii=False) + "\n")
    return dst


def file_record(run):
    """A finished batch's record → runs/image-production/<brand>/<batch>/."""
    run = Path(run).resolve()
    spec = json.loads((run / "batch.json").read_text())
    brand = P.need_brand(spec.get("brand"), "where the record files")
    label = run.name
    pairs = [(run / n, n) for n in ("batch.json", "check.json", "elements.json",
                                    "verdicts.json", "report.md")]
    pairs.append((run / "inbox/jobs.json", "jobs.json"))
    pairs += [(f, f"prompts-as-sent/{f.name}") for f in sorted((run / "prompts").glob("*.txt"))]
    pairs += [(f, f"manifests/{f.parent.name}.json") for f in sorted(run.glob("ads/*/manifest.json"))]
    pairs += [(f, f"rejected/{f.name}") for f in sorted(run.glob("rejected/*-why.md"))]
    pairs += [(f, f"rejected/{f.parent.parent.name}--{f.name}")
              for f in sorted(run.glob("ads/*/rejected/*-why.md"))]
    return _file(run, brand, label, pairs,
                 {"batch": spec.get("batch"), "ads": [a.get("slug") for a in spec.get("ads") or []]})


def file_swipe_record(run, brand):
    """A brief-driven run's record (`run_production.py`) → the same place."""
    run = Path(run).resolve()
    pairs = [(f, f.name) for f in sorted(run.glob("out/*.md"))]
    pairs += [(f, f.name) for f in sorted(run.glob("out/*.json"))]
    pairs += [(run / n, n) for n in ("check.json", "elements.json")]
    return _file(run, brand, run.name, pairs, {"from": "a teardown brief"})


def file_quietly(fn, *a):
    """Filing never stops a delivery. A failure prints SKIP and the reason."""
    try:
        dst = fn(*a)
        try:
            shown = dst.relative_to(P.REPO)
        except ValueError:
            shown = dst
        print(f"  record → {shown}")
        return dst
    except BaseException as e:                   # noqa: BLE001 — SystemExit too: a refusal here is still only a skip
        if isinstance(e, KeyboardInterrupt):
            raise
        print(f"  SKIP filing the record — {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = Path(sys.argv[1])
    st = state(r)
    if not st:
        print(f"{r.name}: no gate has run yet")
    for g, v in st.items():
        print(f"{g}: {v.get('result')}")
        for p in v.get("problems", []):
            print(f"   - {p}")
