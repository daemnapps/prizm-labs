"""The design line, step 2b, for any brand: choose a laid-out email's real pictures again, change nothing else.

    python3 design/repick.py <brand> --run <run folder> [--run ...] [--no-build] [--dry-run]

An email laid out before 2026-10-28 got its brand photos by file name: the layout never saw them and wrote what it
guessed into the alt (a "Black man's jaw, CRUSH in frame" that was a white man's face with no product). Laying it
out again rewrites its sections and words, which a person already approved. This keeps every section and word and
only looks again at each slot holding a brand photo or a customer picture: keep it when what it shows fits the
words around it, else pick one we own by what is IN it (asset-index tags), else name a picture to make (a `todo`).
Made pictures (run:), product cut-outs and slots still to make are never touched; nor is a customer picture whose
section carries that customer's own words. Every real picture's alt becomes what was seen in it (line.true_alts).

Prompt: prompts/design2b-repick-v1-pm.md, written beside the output as sent (design/repick--prompt.md); what
changed and why is kept in email.json under `repick`. Then the email is rebuilt and re-checked as a picture change
on the emails page is (design/build.py, design/check.py, the card's marks kept) unless --no-build.
A picture another email of the brand already uses is not offered; the batch goes in the order given.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import line as LI  # noqa: E402

L, EN, REPO = LI.L, LI.EN, LI.REPO
PROMPT = LI.PROMPTS / "design2b-repick-v1-pm.md"
PICTURE_KEYS = ("photo", "proof", "todo", "stage", "glow", "band")
OWN_WORDS = ("example", "selfies")             # a customer's picture here sits with that customer's words


def _is_pic(x):
    return isinstance(x, dict) and "s" not in x and any(k in x for k in PICTURE_KEYS)


def _words(x):
    """Every line of words in a section, its pictures left out."""
    out = []
    if isinstance(x, dict):
        if _is_pic(x):
            return out
        for k, v in x.items():
            if k in ("s", "ratio", "focus", "style"):
                continue
            out += [v] if isinstance(v, str) and len(v) > 2 else _words(v)
    elif isinstance(x, list):
        for v in x:
            out += [v] if isinstance(v, str) and len(v) > 2 else _words(v)      # paras, arrow pairs
    return out


def slots(spec):
    """[(n, section index, section kind, picture dict)] for every brand photo or customer picture to look at again."""
    return [(n, i, k, p) for n, i, k, p, _ in _slots(spec)]


def _slots(spec):
    """slots(), each with the dict the picture sits in (a tile, a card, the section itself): its own words."""
    out = []
    for i, sec in enumerate(spec.get("sections", [])):
        def walk(x, holder):
            if _is_pic(x):
                if str(x.get("photo", "")).startswith("drive:") or ("proof" in x and sec.get("s") not in OWN_WORDS):
                    out.append((len(out) + 1, i, sec.get("s"), x, holder))
                return
            if isinstance(x, dict):
                for v in x.values():
                    walk(v, x)
            elif isinstance(x, list):
                for v in x:
                    walk(v, holder)
        walk(sec, sec)
    return out


def refs_in(spec):
    found = []

    def walk(x):
        if _is_pic(x):
            found.extend(r for r in (x.get("photo"), x.get("proof")) if r and not str(r).startswith("run:"))
            return
        for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []):
            walk(v)
    walk(spec.get("sections", []))
    return found


def used_elsewhere(brand, skip):
    """{ref: run name} for every brand photo and customer picture the brand's other laid-out emails use."""
    used = {}
    for f in sorted((LI.RUNS / brand).glob("*/design/email.json")):
        if f.parent.parent.name in skip:
            continue
        try:
            spec = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for r in refs_in(spec):
            used.setdefault(r, f.parent.parent.name)
    return used


def sells(spec):
    names = sorted({str(x.get("stage") or x.get("glow")).split(":", 1)[1] for x in _all_pics(spec)
                    if str(x.get("stage") or x.get("glow") or "").startswith("product:")})
    return ", ".join(names) or "(no product cut-out in the email: read the words)"


def _all_pics(spec):
    found = []

    def walk(x):
        if _is_pic(x):
            found.append(x)
            return
        for v in (x.values() if isinstance(x, dict) else x if isinstance(x, list) else []):
            walk(v)
    walk(spec.get("sections", []))
    return found


def slot_lines(spec, sl, seen):
    """Each slot with the words it sits with (its own tile or card) and, when it is one of several, its section's."""
    out = []
    for n, i, kind, p, holder in _slots(spec):
        sec = spec["sections"][i]
        own = _words(holder)
        around = "" if holder is sec else "\n   in the section: %s" % (" / ".join(_words({k: v for k, v in sec.items() if not isinstance(v, list)})) or "(none)")
        ref = p.get("photo") or p.get("proof")
        out.append("%d. section [%d] %s\n   its own words: %s%s\n   picture now: %s\n   it shows: %s" % (
            n, i, kind, " / ".join(own) or "(none)", around, ref, seen.get(LI._nfc(ref)) or "(never described)"))
    return "\n\n".join(out)


def answer_of(text):
    """The first JSON object in a model's answer; whatever follows it (a note, a second object) is left out."""
    i = text.find("{")
    if i < 0:
        raise ValueError("the answer has no JSON object")
    return json.JSONDecoder().raw_decode(text[i:])[0]


def problems(answer, sl, photo_refs, proof_ids, used):
    """Why an answer cannot be kept, slot by slot ({n: reason})."""
    bad, taken = {}, {}
    chosen = {}
    for e in answer.get("slots", []):
        try:
            chosen[int(e.get("n"))] = e
        except (TypeError, ValueError):
            continue
    for n, i, kind, p in sl:
        e = chosen.get(n)
        if e is None:
            bad[n] = "no answer for slot %d" % n
            continue
        ref = None if e.get("keep") else (e.get("photo") or e.get("proof"))
        if e.get("keep"):
            ref = p.get("photo") or p.get("proof")
            if ref in used:
                bad[n] = "slot %d keeps %s, already used in %s" % (n, ref, used[ref])
        elif e.get("photo") and e["photo"] not in photo_refs:
            bad[n] = "slot %d: %r is not one of BRAND PHOTOS" % (n, e["photo"])
        elif e.get("proof") and e["proof"] not in proof_ids:
            bad[n] = "slot %d: %r is not in REAL PROOF" % (n, e["proof"])
        elif ref and ref in used:
            bad[n] = "slot %d: %s is already used in %s" % (n, ref, used[ref])
        elif not ref and not e.get("todo"):
            bad[n] = "slot %d: keep, photo, proof or todo" % n
        if ref and n not in bad:
            if ref in taken:
                bad[n] = "slot %d repeats slot %d's picture" % (n, taken[ref])
            taken[ref] = n
    return bad


def apply(sl, answer, seen):
    """Write each choice into its picture slot; returns what changed, for the record."""
    chosen = {int(e["n"]): e for e in answer.get("slots", []) if str(e.get("n", "")).isdigit()}
    changed = []
    for n, i, kind, p in sl:
        e = chosen.get(n) or {"keep": True}
        before = p.get("photo") or p.get("proof")
        if e.get("keep"):
            continue
        keep = {k: p[k] for k in ("ratio", "focus", "style") if k in p}
        p.clear()
        if e.get("photo"):
            p.update({"photo": e["photo"], "ratio": keep.get("ratio", 0.8), "focus": keep.get("focus", [0.5, 0.4]),
                      "source": "photo"})
        elif e.get("proof"):
            p.update({"proof": e["proof"], "source": "proof"})
        else:
            p.update({"todo": e["todo"], "brief": e.get("brief", ""), "use": "story", "alt": e["todo"], "source": "make"})
        if "style" in keep:
            p["style"] = keep["style"]
        changed.append({"n": n, "section": i, "from": before, "to": e.get("photo") or e.get("proof") or "todo: " + e["todo"],
                        "why": e.get("why", "")})
    return changed


def repick(brand, run_dir, lk, used, dry=False):
    """One email: its real pictures chosen again; email.json and preview.html rewritten. Returns the record."""
    from run_kit import model as M
    import promises as PM
    lean_call = PM.lean()
    d = run_dir / "design"
    spec = json.loads((d / "email.json").read_text())
    seen = LI.seen_in(brand)
    sl = slots(spec)
    if not sl:
        print("  %-30s no brand photo or customer picture to look at again" % run_dir.name)
        return {"label": run_dir.name, "slots": 0, "changed": []}
    photo_refs, photos_txt = LI.described_photos(lk)
    proof_ids, proof_txt = LI.proof_of(brand)
    offered = set(photo_refs) | set(proof_ids)
    p = LI.fill(LI._read(PROMPT), learnings=LI.LN.block(brand, ("design", "picture")),
                concept=json.dumps({k: (spec.get("job") or {}).get(k) for k in ("reader", "concept", "cut")}, indent=1, ensure_ascii=False),
                sells=sells(spec), slots=slot_lines(spec, sl, seen), photos=photos_txt, proof=proof_txt,
                used=json.dumps({r: w for r, w in used.items() if r in offered}, indent=1, ensure_ascii=False) or "{}")
    (d / "repick--prompt.md").write_text(p)
    if dry:
        print("  %-30s %d slot(s), prompt written (%d chars), nothing spent" % (run_dir.name, len(sl), len(p)))
        return {"label": run_dir.name, "slots": len(sl), "changed": []}
    original = json.loads(json.dumps(spec))
    copy_ = json.loads((run_dir / "deliverable" / "email.json").read_text())
    ask, bad, probs, changed = p, {}, [], []
    for attempt in range(2):               # the promise check reads what each picture really shows: a miss goes back once
        model, _ = M.pick("designs", len(ask))
        answer = answer_of(M.call(ask, model, label="design2b-" + run_dir.name, runner=lean_call.design_runner(M)))
        bad = problems(answer, slots(original), set(photo_refs), set(proof_ids), used)
        answer["slots"] = [e for e in answer.get("slots", []) if str(e.get("n", "")).isdigit() and int(e["n"]) not in bad]
        spec = json.loads(json.dumps(original))
        changed = apply(slots(spec), answer, seen)
        LI.true_alts(spec, seen)
        probs = LI.validate(spec, lk, set(proof_ids), used, photo_refs)
        try:
            probs += PM.problems(PM.check(run_dir, spec, spec.get("job") or {}, copy_))
        except Exception as e:  # noqa: BLE001 — a reader that won't answer never sinks the email; it is noted
            print("   promise check not run: %r" % e)
        if not probs and not bad:
            break
        ask = p + "\n\nYOUR LAST ANSWER WAS HELD FOR: " + "; ".join(list(bad.values()) + probs) + \
            ". Fix exactly those. Where no picture we own shows what the check asks for, name a picture to make (todo) for that slot."
    if spec.get("kind") == "design" and LI.dna_of(brand).startswith("(no visual DNA"):
        probs.append("no visual DNA on file for %s: a designed email is held until the brand's DNA is written" % brand)
    th = spec.get("theme")
    if th and th not in (lk.get("themes") or {}):
        probs.append("no %s look for the moment `%s` yet: make it (the brand's moment looks) before this email builds" % (brand, th))
    spec["held"] = probs + ["slot %s kept as it was: %s" % (n, why) for n, why in sorted(bad.items())]
    spec["repick"] = changed
    (d / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    for r in refs_in(spec):
        used.setdefault(r, run_dir.name)
    try:
        html = EN.render(spec, L.load(brand, run_dir))
        (d / "preview.html").write_text('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#222"><div style="max-width:400px;margin:24px auto">%s</div>' % html)
    except Exception as e:  # noqa: BLE001 — a picture that will not render is a held email, never a crash of the batch
        spec["held"].append("preview: %s" % e)
        (d / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    print("  %-30s %d slot(s), %d changed%s" % (run_dir.name, len(sl), len(changed),
                                                 "  HELD: " + "; ".join(spec["held"]) if spec["held"] else ""))
    return {"label": run_dir.name, "slots": len(sl), "changed": changed, "held": spec["held"]}


def rebuild(runs):
    """As a picture change on the emails page (adapter/sync.py _rebuild): build.py then check.py, per email, the card's
    marks kept (prepare.keep_card), so an email the team marked Done stays Done."""
    sys.path.insert(0, str(LI.COMP / "adapter"))
    from prepare import keep_card

    def steps(r):
        for args in (["design/build.py", str(r)], ["design/check.py", str(r)]):
            p = subprocess.run([sys.executable] + args, cwd=str(LI.COMP), capture_output=True, text=True)
            if p.returncode:
                raise RuntimeError("%s stopped: %s" % (args[0], (p.stderr or p.stdout)[-300:]))
    for r in runs:
        keep_card(r, lambda: steps(r))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("brand")
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--no-build", action="store_true", help="rewrite the layout only; no Klaviyo build or check")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    runs = [Path(r).resolve() for r in a.run]
    lk = L.load(a.brand)
    used = used_elsewhere(a.brand, {r.name for r in runs})
    print("%s · %d email(s): pictures chosen again, words kept" % (a.brand, len(runs)))
    out, done = [], []
    for r in runs:
        try:
            out.append(repick(a.brand, r, lk, used, a.dry_run))
            done.append(r)
        except Exception as e:  # noqa: BLE001 — one email that will not answer never sinks the batch; it stays as it was
            print("  %-30s NOT CHANGED: %s: %s" % (r.name, type(e).__name__, e))
            out.append({"label": r.name, "error": "%s: %s" % (type(e).__name__, e)})
    if done and not (a.dry_run or a.no_build):
        rebuild(done)
    return out


if __name__ == "__main__":
    main()
