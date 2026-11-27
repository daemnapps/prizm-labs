#!/usr/bin/env python3
"""Re-render the "The bank" table in formats/README.md from formats/bank.json.

    python3 formats/render_bank.py

Replaces everything between the `<!-- bank:start -->` and `<!-- bank:end -->`
markers; touches nothing else in the file. Stdlib only.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "bank.json"
README = HERE / "README.md"
START = "<!-- bank:start -->"
END = "<!-- bank:end -->"


def render(bank):
    rows = ["| `format` (run.json) | Name | Status | What a scene contains | Proven on | Profile |",
            "|---|---|---|---|---|---|"]
    for f in bank["formats"]:
        profile = f"[`{f['profile']}`]({f['profile']})" if f.get("profile") else "—"
        proven = f.get("proven_on") or "not yet run end to end"
        status = f["status"] + (" ✓ signed" if f.get("signed") else "")
        rows.append(f"| `{f['id']}` | {f['name']} | {status} | {f.get('what', '')} | {proven} | {profile} |")
    return "\n".join(rows)


def main():
    bank = json.loads(BANK.read_text())
    text = README.read_text()
    if START not in text or END not in text:
        sys.exit(f"markers {START} / {END} not found in {README}")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    body = (
        f"{START}\n"
        f"Rendered from `bank.json` — edit that file, then `python3 formats/render_bank.py`.\n\n"
        f"{render(bank)}\n"
        f"{END}"
    )
    README.write_text(head + body + tail)
    print(f"rendered {len(bank['formats'])} formats into {README.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
