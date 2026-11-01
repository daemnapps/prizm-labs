"""File a merged card's fixes: one triage `change` record per issue its `- Fixes:` line names (ATL-46 (merge files fixes)).

    python3 components/triage/tools/file_fixes.py --card <ID> --commit <merge sha> --test <declared test>
        [--deck <task-cards.md>] [--atlas <data.json>] [--dry-run]

The card is found at `### <ID> ` in --deck, else in the one new-workflow-design/builds/*/task-cards.md that holds it.
Its line `- Fixes: <component>#<n>, …[; partial: <component>#<n>, …]` names the issues the card fully fixes; partial
ids are printed and NEVER filed; `none` files nothing. No `Fixes:` line → one warning, nothing filed, exit 0 (a merge
never stops for it). Every full id is checked against the atlas (system.flows[].component + flow.issues[].n) before
anything is written; one unknown id refuses the whole call. Each id is filed through file_record.main (imported, never
copied); every path written is printed. Run by the lead after each merge; commit the records in the same push.
Python 3.9-clean; stdlib only; no network, no credential."""
import argparse, contextlib, io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_record  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
TAGS = REPO / "team/id-tags.json"
ID = re.compile(r"([A-Za-z0-9._-]+)\s*#\s*(\d+)")


def refuse(msg):
    sys.exit(f"refused: {msg}")


def find_card(card, deck=None):
    """(deck path, card lines) for `### <card> `; --deck alone when given, else the one builds deck that holds it."""
    decks = [Path(deck)] if deck else sorted((REPO / "new-workflow-design/builds").glob("*/task-cards.md"))
    head = f"### {card} "
    hits = []
    for p in decks:
        if not p.is_file():
            refuse(f"deck {p} is not a file")
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith(head):
                end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("### ")), len(lines))
                hits.append((p, lines[i:end]))
    if len(hits) != 1:
        where = ", ".join(str(p) for p, _ in hits) or ", ".join(str(p) for p in decks)
        refuse(f"card {card} found {len(hits)} times (need exactly one): {where}")
    return hits[0]


def parse_ids(text, what):
    """`a#1, b #2` → ["a#1", "b#2"]; `none` → []; anything else refuses."""
    text = text.strip()
    if text.lower() == "none":
        return []
    ids = []
    for part in text.split(","):
        m = ID.fullmatch(part.strip())
        if not m:
            refuse(f"{what} id {part.strip()!r} is not <component>#<n>")
        ids.append(f"{m.group(1)}#{m.group(2)}")
    return ids


def parse_fixes(lines):
    """(full ids, partial ids) from the card's one `- Fixes:` line; None when the card has none."""
    found = [l for l in lines if l.startswith("- Fixes:")]
    if not found:
        return None
    if len(found) > 1:
        refuse(f"card carries {len(found)} `- Fixes:` lines (need one)")
    body = found[0][len("- Fixes:"):]
    full, _, rest = body.partition(";")
    partial = []
    if rest.strip():
        m = re.fullmatch(r"\s*partial:\s*(.+)", rest)
        if not m:
            refuse(f"after `;` the Fixes line takes only `partial: <ids>`, got {rest.strip()!r}")
        partial = parse_ids(m.group(1), "partial")
    return parse_ids(full, "Fixes"), partial


def atlas_ids(atlas):
    """Every `<component>#<n>` the atlas knows."""
    data = json.loads(Path(atlas).read_text(encoding="utf-8"))
    known = set()
    for f in (data.get("system") or {}).get("flows") or []:
        for issue in (f.get("flow") or {}).get("issues") or []:
            known.add(f"{f.get('component')}#{issue.get('n')}")
    return known


def tag_for(card):
    try:
        return json.loads(TAGS.read_text(encoding="utf-8")).get(card)
    except (OSError, ValueError):
        return None


def run(argv):
    """File the card's fixes; return the record paths written ([] on a warning or --dry-run)."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--card", required=True)
    ap.add_argument("--commit", required=True, help="the merge sha")
    ap.add_argument("--test", required=True, help="the card's declared test")
    ap.add_argument("--deck", help="the task-cards.md holding the card (default: search builds/*/task-cards.md)")
    ap.add_argument("--atlas", default=str(REPO / "platform/data/atlas/data.json"))
    ap.add_argument("--dry-run", action="store_true", help="print the records, write nothing")
    a = ap.parse_args(argv)

    deck, lines = find_card(a.card, a.deck)
    fixes = parse_fixes(lines)
    if fixes is None:
        print(f"warning: {a.card} in {deck} has no `- Fixes:` line; nothing filed", file=sys.stderr)
        return []
    full, partial = fixes
    if partial:
        print(f"partial, not filed: {', '.join(partial)}")
    known = atlas_ids(a.atlas)
    unknown = [i for i in full if i not in known]
    if unknown:
        refuse(f"{', '.join(unknown)} not in {a.atlas}; nothing filed")
    tag = tag_for(a.card)
    why = f"{a.card} ({tag}) merged at {a.commit}" if tag else f"{a.card} merged at {a.commit}"
    written = []
    for item in full:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            file_record.main(["change", "--item", item, "--who", "lead", "--theme", "components", "--commit", a.commit,
                              "--test", a.test, "--why", why] + (["--dry-run"] if a.dry_run else []))
        print(out.getvalue(), end="")
        if not a.dry_run:
            written.append(out.getvalue().strip())
    if not full:
        print(f"{a.card}: Fixes none; nothing filed")
    return written


def main():
    run(sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
