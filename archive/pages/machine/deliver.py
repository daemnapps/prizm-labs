#!/usr/bin/env python3
"""Carry a finished run's words into the brand's funnel record.

    python3 deliver.py scrub-base-01

For every brief the run produced (stage6 = the base page, stage6-<sub> = each
variation) this writes the page's words as
brands/<brand>/funnels/<funnel>/<format>/<page-name>.md — front matter carrying
the page's key, then the copy in page order — and, once per run, the construct
beside them as <base-page-name>-construct.md (the brand-free construct, the
substitution log and the collisions, the close's note). The run folder stays
the working record; this is the finished element a person then reads.

This is the ONE place the chain touches brands/, and it only ever writes the
files named above. Existing files with those names are replaced — a page's
words are its latest run, and the run folder keeps every earlier one.

    python3 deliver.py scrub-base-01 --force    # deliver a run the copy gate held

A run the copy gate HELD (check.json in the run folder) is refused — the words
carry an unfilled note or a price the offer files do not sell. `--force` carries
them anyway, and says so in the page's front matter.

Runs are found in both homes: runs/page-machine/<brand>/<label>/ at the repo
root, then the old runs/ beside the code (machine/page_paths.py).
"""
import json, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_paths as P                                     # noqa: E402
import page_gates as G                                     # noqa: E402

HERE = P.HERE
WORKSPACE = P.WORKSPACE
RUNS = P.RUNS


def section(text, heading_words, until_words=()):
    """The body under a heading containing all `heading_words`, up to the next
    heading of the same or higher level (or one containing `until_words`)."""
    lines = text.splitlines()
    start = None
    for i, l in enumerate(lines):
        # a heading is a whole short line — `## WHAT TO WATCH` or `**WHAT TO WATCH**` —
        # never a body line that happens to mention the heading's words
        is_heading = re.match(r"^\s*#{1,3}\s+\S.{0,60}$", l) or re.match(r"^\s*\*\*[^*]{1,60}\*\*\s*$", l)
        if is_heading and all(w.lower() in l.lower() for w in heading_words):
            start = i; lvl = len(re.match(r"^\s*(#*)", l).group(1)) or 2; break
    if start is None:
        return ""
    out = []
    for l in lines[start + 1:]:
        m = re.match(r"^\s*(#{1,6})\s", l)
        if m and len(m.group(1)) <= lvl and not re.match(r"^\s*#{1,6}\s*\[\d+\]", l):
            break
        if l.strip().startswith("**") and l.strip().endswith("**") and any(w.lower() in l.lower() for w in until_words):
            break
        out.append(l)
    return "\n".join(out).strip()


def manifest(text):
    m = re.search(r"```ya?ml\n(.*?)```", text, re.S)
    if not m:
        return {}
    d = {}
    for l in m.group(1).splitlines():
        k, _, v = l.partition(":")
        if k.strip():
            d[k.strip()] = v.strip()
    return d


def copy_block(text):
    """Everything from the first `## [1]` heading to the offer/what-to-watch section."""
    m = re.search(r"^\s*#{1,4}\s*\[1\][^\n]*$", text, re.M)
    if not m:
        return ""
    rest = text[m.start():]
    end = re.search(r"^\s*(#{1,3}\s+|\*\*)(THE OFFER IT HANDS TO|WHAT TO WATCH|BEFORE YOU BUILD)", rest, re.M | re.I)
    body = rest[:end.start()] if end else rest
    # normalise headings to `## [n] title`
    body = re.sub(r"^\s*#{1,4}\s*\[(\d+)\]\s*", r"## [\1] ", body, flags=re.M)
    body = re.sub(r"\n+(## \[)", r"\n\n\1", body)
    return body.strip()


def tail_sections(text):
    """The brief's own closing notes, kept with the page so nothing is smoothed over."""
    out = []
    for words in (("OFFER IT HANDS TO",), ("WHAT TO WATCH",), ("BEFORE YOU BUILD",)):
        s = section(text, words)
        if s:
            out.append(f"## {words[0].title().replace('Offer It Hands To', 'The offer it hands to').replace('What To Watch', 'What to watch').replace('Before You Build', 'Before you build it')}\n\n{s}")
    return "\n\n".join(out)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in argv
    argv = [x for x in argv if x != "--force"]
    if len(argv) != 1:
        sys.exit("usage: deliver.py <label> [--force]")
    label = argv[0]
    run = P.need_run(label)
    state = json.loads((run / "run.json").read_text())
    held = G.held(run)
    if held:
        print(f"run {label} is HELD ({P.rel(run)}/check.json):")
        for gate, problems in held.items():
            for prob in problems:
                print(f"  - [{gate}] {prob}")
        if not force:
            sys.exit("refused: a held run is not delivered. Fix it and rerun with --resume, "
                     "or pass --force to carry it anyway.")
        print("  --force: delivering it anyway")
    brand, funnel, fmt = state["brand"], state["funnel"], state["format"]
    base = state["page_name"]
    dest = WORKSPACE / "brands" / brand / "funnels" / funnel / fmt
    dest.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    written = []

    briefs = [("stage6", base, [])] + [(f"stage6-{s}", f"{base}-{re.sub(r'[^a-z0-9]', '', s)}", [s]) for s in state.get("subs", [])]
    for key, page_name, subs in briefs:
        info = state["stages"].get(key, {})
        if info.get("status") != "done":
            print(f"  skip {key}: not done"); continue
        text = (run / info["out"]).read_text()
        man = manifest(text)
        body = copy_block(text)
        if not body:
            print(f"  !! {key}: no `## [1]` copy block found in the brief — nothing written"); continue
        fm = {
            "page_name": page_name, "page_format": fmt, "page_avatar": state["avatar"],
            "page_subs": "[" + ", ".join(subs) + "]" if subs else "[all — the base page]",
            "page_concept": state["angle"], "page_swipe": man.get("page_swipe") or f"swipe:landing-pages:{state.get('swipe','')}",
            "page_next": state["next"], "narrator": man.get("narrator", "(see brief)"),
            "status": f"words from the page machine, run {label}, {today} · not built"
                      + (f" · DELIVERED WHILE HELD at the {', '.join(held)} gate (--force)" if held else ""),
            "run": f"{P.rel(run)}/{info['out']}",
        }
        head = "---\n" + "\n".join(f"{k + ':':<14}{v}" for k, v in fm.items()) + "\n---\n\n"
        notes = tail_sections(text)
        (dest / f"{page_name}.md").write_text(head + body + ("\n\n" + notes if notes else "") + "\n")
        written.append(dest / f"{page_name}.md")

    # the construct, once per run
    spec = (run / "stage2--spec.md").read_text() if (run / "stage2--spec.md").exists() else ""
    inj = (run / "stage3--injection.md").read_text() if (run / "stage3--injection.md").exists() else ""
    close = (run / "stage4--close.md").read_text() if (run / "stage4--close.md").exists() else ""
    sub_log = section(inj, ("SUBSTITUTION LOG",)); coll = section(inj, ("COLLISIONS",))
    close_note = section(close, ("ONE LINE",))
    tri = (run / "stage0--triage.md").read_text() if (run / "stage0--triage.md").exists() else ""
    con = (dest.parent / f"{base}-construct.md")
    con.write_text(f"""# {base} — construct and injection

_From the page machine, run `{label}`, {today}. Source: {state.get('source_url')} (swipe {state.get('swipe')}). The run folder holds every stage's prompt as sent and its output: `{P.rel(run)}/`._

## Triage

```
{tri.strip()}
```

## The construct — brand-free, category-free

{spec.strip()}

## What went in each slot

{sub_log or '(no substitution log in the injection output)'}

## Collisions — where the construct and the brand fought

{coll or '(none logged)'}

## The close

{close_note or ''}
""")
    written.append(con)
    for w in written:
        print("wrote", w.relative_to(WORKSPACE))


if __name__ == "__main__":
    main()
