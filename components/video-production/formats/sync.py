#!/usr/bin/env python3
"""Write the chain's copies of every format that has a home folder.

    python3 formats/sync.py            write the copies
    python3 formats/sync.py --check    exit 1 when a copy differs from its home (nothing written)

A format's one home is `formats/<id>/format.json` (README.md, "One home per format"). The chain still reads
`formats/bank.json` and `formats/playbooks/<id>.json`, so for every home this writes:

  * its row in bank.json (replaced in place, or added at the end; every other row is left as it is);
  * formats/playbooks/<id>.json and its readable <id>.md (machine/playbook.py `write`);
  * the bank table in README.md (render_bank.py).

The copies carry `home` so a reader can tell they are generated. Edit the home, then run this. Stdlib only;
runs on Python 3.9.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.json"
PLAYBOOKS = HERE / "playbooks"
ROW_KEYS = ("id", "name", "what", "profile", "status", "signed", "proven_on", "notes")

sys.path.insert(0, str(HERE.parent / "machine"))
sys.path.insert(0, str(HERE))
import playbook as PB  # noqa: E402
import render_bank  # noqa: E402


def homes():
    """Every format.json under formats/<id>/, as written."""
    out = []
    for p in sorted(HERE.glob("*/format.json")):
        doc = json.loads(p.read_text())
        if doc.get("id") != p.parent.name:
            raise SystemExit("%s: id %r is not its folder name" % (p, doc.get("id")))
        out.append((p, doc))
    return out


def rel(p):
    return str(p.relative_to(HERE.parents[2]))


def bank_row(path, doc):
    row = {k: doc.get(k) for k in ROW_KEYS}
    row["profile"] = "%s/FORMAT.md" % doc["id"]
    row["home"] = rel(path)
    return row


def playbook_doc(path, doc):
    pb = {"format_id": doc["id"], "name": doc["name"], "status": doc["status"], "state": doc.get("state"),
          "signed": doc.get("signed"), "home": rel(path)}
    pb.update(doc.get("playbook") or {})
    pb.setdefault("what", doc.get("what"))
    return pb


def bank_text(found):
    bank = json.loads(BANK.read_text())
    rows = bank["formats"]
    for path, doc in found:
        row = bank_row(path, doc)
        at = next((i for i, r in enumerate(rows) if r.get("id") == doc["id"]), None)
        if at is None:
            rows.append(row)
        else:
            rows[at] = row
    return bank, json.dumps(bank, indent=1, ensure_ascii=False) + "\n"


def playbook_texts(path, doc):
    clean = {k: v for k, v in playbook_doc(path, doc).items() if not k.startswith("_")}
    return (json.dumps(clean, indent=2, ensure_ascii=False) + "\n", PB.render_md(clean))


def readme_text(bank):
    text = render_bank.README.read_text()
    a, b = text.index(render_bank.START), text.index(render_bank.END)
    note = "Rendered from `bank.json` — edit that file, then `python3 formats/render_bank.py`."
    return text[:a] + render_bank.START + "\n" + note + "\n\n" + render_bank.render(bank) + "\n" + text[b:]


def plan():
    """[(file, wanted text)] for every copy the homes decide."""
    found = homes()
    bank, btext = bank_text(found)
    out = [(BANK, btext)]
    for path, doc in found:
        js, md = playbook_texts(path, doc)
        out += [(PLAYBOOKS / ("%s.json" % doc["id"]), js), (PLAYBOOKS / ("%s.md" % doc["id"]), md)]
    out.append((render_bank.README, readme_text(bank)))
    return out


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    stale = [f for f, want in plan() if not f.is_file() or f.read_text() != want]
    if "--check" in args:
        for f in stale:
            print("stale: %s (run python3 formats/sync.py)" % rel(f))
        return 1 if stale else 0
    for f, want in plan():
        if not f.is_file() or f.read_text() != want:
            f.write_text(want)
            print("wrote", rel(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
