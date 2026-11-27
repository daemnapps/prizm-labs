"""Prompt upgrade test: old version against new version, frozen cases, one held back, judged blind.

Does not call a model and does not switch a live version. It prepares the test and reads the
judgments; the person or model that judges does the reading in between.

The method, from short-drama-factory's evaluation notes (MIT licence, references on how to
prove a prompt change is better), written here as code:

  1. FREEZE   the cases before anything is tuned. Their input hashes are recorded and the
              record cannot be changed afterwards. At least one case is held back: its id is
              not shown by `status` or `pack` until the final run, and it is run once.
  2. PACK     for each case the old and the new output go into one file as drafts A and B,
              in an order fixed by a seeded shuffle. Version labels are stripped. The key
              that maps A and B back to old and new is kept apart and not printed.
  3. JUDGE    one JSON object per case: what is better in A, what is better in B, and how the
              rules of each draft could be gotten around. No score, no stars, no total.
  4. REVEAL   maps the judgments through the key and reports, per case, what the new version
              FIXED (new better), what it BROKE (old better), and for the held-back case
              whether it HOLDS (the new version is not worse). Then lists what could be
              gotten around. A score field in a judgment is refused.

Blinding here is by label only. If a new prompt adds a visible section that the old one never
printed (for example new output blocks), a judge can still tell the drafts apart; the packet
lists any such tell as a LEAK warning so the owner knows.

Commands (all take --dir, the folder that holds the test's state):

  freeze  --stage S --old LABEL --new LABEL --case ID=PATH ... --heldout ID=PATH ...
  status
  pack    --old-out DIR --new-out DIR [--final]     (DIR holds ID.md per case)
  reveal  --judgments FILE.json

Every command only reads and writes inside --dir. Python 3.9, standard library only.
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

MANIFEST = "manifest.json"
SEALED = "heldout.sealed.json"
KEY = "key.json"
LEDGER = "ledger.json"
BLIND = "blind"
BANNED_FIELDS = ("score", "scores", "rating", "stars", "total", "grade")
GENERIC_VERSION = re.compile(r"\bstage\w*(?:-\w+)*?-v\d+(?:-\w+)*\b", re.I)   # a prompt file name; bare V1, V2 are content


class BakeoffError(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path, default=None):
    p = Path(path)
    if not p.is_file():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def parse_case(spec):
    if "=" not in spec:
        raise BakeoffError("case must be ID=PATH, got %r" % spec)
    cid, path = spec.split("=", 1)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", cid):
        raise BakeoffError("case id may hold letters, digits, dot, dash, underscore: %r" % cid)
    p = Path(path).expanduser()
    if not p.is_file():
        raise BakeoffError("case input not found: %s" % path)
    return cid, p


# ---- 1 freeze ---------------------------------------------------------------
def freeze(d, stage, old, new, cases, heldout):
    d = Path(d)
    if (d / MANIFEST).exists():
        raise BakeoffError("already frozen: %s exists and a frozen test is never changed" % (d / MANIFEST))
    if not cases:
        raise BakeoffError("at least one frozen case is needed")
    if not heldout:
        raise BakeoffError("at least one held-back case is needed")
    parsed = [parse_case(c) for c in cases]
    held = [parse_case(c) for c in heldout]
    ids = [c for c, _ in parsed + held]
    if len(set(ids)) != len(ids):
        raise BakeoffError("case ids must be unique")
    if old.strip().lower() == new.strip().lower():
        raise BakeoffError("old and new need different labels")
    d.mkdir(parents=True, exist_ok=True)
    manifest = {"stage": stage, "old": old, "new": new,
                "cases": [{"id": c, "input": str(p), "sha256": sha(p.read_bytes())} for c, p in parsed],
                "heldout_count": len(held)}
    manifest["seal"] = sha(json.dumps(manifest, sort_keys=True).encode())
    write_json(d / MANIFEST, manifest)
    write_json(d / SEALED, {"heldout": [{"id": c, "input": str(p), "sha256": sha(p.read_bytes())} for c, p in held],
                            "manifest_seal": manifest["seal"]})
    write_json(d / LEDGER, {"heldout_run": False})
    return manifest


def load(d):
    d = Path(d)
    m = read_json(d / MANIFEST)
    if m is None:
        raise BakeoffError("nothing frozen in %s: run freeze first" % d)
    seal = m.pop("seal", None)
    if sha(json.dumps(m, sort_keys=True).encode()) != seal:
        raise BakeoffError("the frozen manifest was changed after freezing")
    m["seal"] = seal
    return m


def status(d):
    m = load(d)
    led = read_json(Path(d) / LEDGER, {"heldout_run": False})
    return {"stage": m["stage"], "old": m["old"], "new": m["new"],
            "frozen_cases": [c["id"] for c in m["cases"]],
            "heldout": "%d held back, %s" % (m["heldout_count"], "run" if led["heldout_run"] else "not run"),
            "packed": (Path(d) / KEY).is_file()}


# ---- 2 pack -----------------------------------------------------------------
def strip_labels(text, labels):
    """Remove the version names from a draft. Returns (clean text, remaining tells)."""
    out = GENERIC_VERSION.sub("[version]", text)
    for lab in labels:
        out = re.sub(re.escape(lab), "[version]", out, flags=re.I)
    tells = [l for l in labels if re.search(re.escape(l), out, re.I)]
    return out, tells


def _order(seal, cid):
    """True when the new version is draft A. Fixed by the seal and the case id."""
    return random.Random("%s:%s" % (seal, cid)).random() < 0.5


def _leaks(old_text, new_text):
    """Headings in one draft that the other never prints: a visible tell for the judge."""
    heads = lambda t: {l.strip().strip("*# ").lower()[:50] for l in t.splitlines()
                       if l.strip().startswith(("#", "**")) and len(l.strip()) < 60}
    only_new, only_old = heads(new_text) - heads(old_text), heads(old_text) - heads(new_text)
    return sorted(only_new)[:5], sorted(only_old)[:5]


def pack(d, old_out, new_out, final=False):
    d = Path(d)
    m = load(d)
    led = read_json(d / LEDGER, {"heldout_run": False})
    sealed = read_json(d / SEALED)
    ids = [c["id"] for c in m["cases"]]
    if final:
        if led["heldout_run"]:
            raise BakeoffError("the held-back case was already run once; it is not run again")
        ids = [c["id"] for c in sealed["heldout"]]
    elif (d / KEY).is_file():
        raise BakeoffError("frozen cases are already packed; start a new test to repack")
    (d / BLIND).mkdir(exist_ok=True)
    key = read_json(d / KEY, {})
    warnings = []
    for cid in ids:
        o, n = Path(old_out) / (cid + ".md"), Path(new_out) / (cid + ".md")
        for p in (o, n):
            if not p.is_file():
                raise BakeoffError("missing output: %s" % p)
        ot, nt = strip_labels(o.read_text(encoding="utf-8"), [m["old"], m["new"]])[0], \
            strip_labels(n.read_text(encoding="utf-8"), [m["old"], m["new"]])[0]
        new_first = _order(m["seal"], cid)
        a, b = (nt, ot) if new_first else (ot, nt)
        key[cid] = {"A": "new" if new_first else "old", "B": "old" if new_first else "new"}
        only_new, only_old = _leaks(ot, nt)
        tell = only_new + only_old
        if tell:
            warnings.append("LEAK %s: a heading only one draft prints: %s" % (cid, "; ".join(tell)))
        sheet = ("# Case %s: two drafts, versions hidden\n\n"
                 "Answer in JSON, no scores, no stars, no total:\n"
                 '{"case": "%s", "a_better": ["what is better in A than B"], "b_better": ["what is better in B than A"], '
                 '"gets_around": {"A": ["how A\'s rules could be gotten around"], "B": ["..."]}}\n\n'
                 "## Draft A\n\n%s\n\n## Draft B\n\n%s\n") % (cid, cid, a.rstrip(), b.rstrip())
        (d / BLIND / (cid + ".md")).write_text(sheet, encoding="utf-8")
    write_json(d / KEY, key)
    if final:
        led["heldout_run"] = True
        write_json(d / LEDGER, led)
    return {"packed": ids, "warnings": warnings, "folder": str(d / BLIND)}


# ---- 4 reveal ---------------------------------------------------------------
def reveal(d, judgments):
    d = Path(d)
    m = load(d)
    key = read_json(d / KEY)
    if not key:
        raise BakeoffError("nothing packed yet")
    sealed = {c["id"] for c in read_json(d / SEALED)["heldout"]}
    frozen = [c["id"] for c in m["cases"]]
    by_case = {}
    for j in judgments:
        bad = [f for f in BANNED_FIELDS if f in j]
        if bad:
            raise BakeoffError("judgment for %s has %s: no scores, stars or totals" % (j.get("case"), "/".join(bad)))
        if j.get("case") not in key:
            raise BakeoffError("judgment for a case that was not packed: %r" % j.get("case"))
        by_case[j["case"]] = j
    missing = [c for c in frozen if c not in by_case]
    if missing:
        raise BakeoffError("frozen cases not judged: %s" % ", ".join(missing))
    report = {"stage": m["stage"], "old": m["old"], "new": m["new"], "cases": {}, "heldout": {}}
    for cid, j in by_case.items():
        k = key[cid]
        side = lambda who: "a_better" if k["A"] == who else "b_better"
        row = {"fixed": list(j.get(side("new"), [])), "broke": list(j.get(side("old"), [])),
               "gets_around": {}}
        for letter, items in (j.get("gets_around") or {}).items():
            row["gets_around"][k[letter]] = list(items)
        if cid in sealed:
            row["holds"] = not row["broke"]
            report["heldout"][cid] = row
        else:
            report["cases"][cid] = row
    if not report["heldout"]:
        report["heldout_status"] = "held-back case not run yet"
    return report


def render(report):
    out = ["BAKE-OFF %s: %s (old) against %s (new). No score. The owner picks the output." %
           (report["stage"], report["old"], report["new"])]
    for title, group in (("FROZEN", report["cases"]), ("HELD BACK", report["heldout"])):
        for cid, r in sorted(group.items()):
            out.append("%s %s: fixed %d · broke %d%s" % (title, cid, len(r["fixed"]), len(r["broke"]),
                       (" · holds: %s" % ("yes" if r["holds"] else "no")) if "holds" in r else ""))
            for lab, items in (("FIXED", r["fixed"]), ("BROKE", r["broke"])):
                for it in items:
                    out.append("    %s: %s" % (lab, it))
            for ver, items in sorted(r["gets_around"].items()):
                for it in items:
                    out.append("    GETS AROUND (%s): %s" % (ver, it))
    if "heldout_status" in report:
        out.append(report["heldout_status"])
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prompt upgrade test: frozen cases, held back, blind. No model calls.")
    ap.add_argument("command", choices=["freeze", "status", "pack", "reveal"])
    ap.add_argument("--dir", required=True)
    ap.add_argument("--stage")
    ap.add_argument("--old")
    ap.add_argument("--new")
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--heldout", action="append", default=[])
    ap.add_argument("--old-out")
    ap.add_argument("--new-out")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--judgments")
    a = ap.parse_args(argv)
    try:
        if a.command == "freeze":
            m = freeze(a.dir, a.stage or "", a.old or "", a.new or "", a.case, a.heldout)
            print("frozen %d cases, %d held back, seal %s" % (len(m["cases"]), m["heldout_count"], m["seal"][:12]))
        elif a.command == "status":
            print(json.dumps(status(a.dir), indent=2))
        elif a.command == "pack":
            r = pack(a.dir, a.old_out, a.new_out, a.final)
            print("packed %s into %s" % (", ".join(r["packed"]), r["folder"]))
            for w in r["warnings"]:
                print(w)
        else:
            data = read_json(a.judgments)
            report = reveal(a.dir, data if isinstance(data, list) else [data])
            print(render(report))
    except BakeoffError as e:
        print("bakeoff: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
