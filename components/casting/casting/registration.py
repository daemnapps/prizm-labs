"""Steps 7 and 8 — the bible and the registry row, PROPOSED.

**Registration is the brand's, not this component's.** A machine reads
`brands/<brand>/` and never writes there (`the team notes/CLAUDE.md` rule 5), and
the cast records are curated by people on purpose — they are the brand's truth
about who exists. So this writes, into the RUN folder:

    register/proposed-row.json   the row, ready to paste
    register/REGISTER.md         where it goes, and the one command after
    bible/character.md           the draft bible, for a person to finish

and a person moves them. Nothing here edits a registry, and nothing here
rebuilds `CAST.md` — the sheet is rendered from the records by the tool that
owns that job, and it is never edited by hand.

No brand, person or product is named in this file.
"""
import json
import time
from pathlib import Path

from . import paths as P

FILE_FOR = {"authority": "authority.json", "roster": "roster.json"}


def row_for(req, baseline=None):
    """The proposed row, in the shape the record already uses.

    Only fields the caller actually gave are written: a row invented to look
    complete is a row somebody will believe."""
    kind = req.get("kind")
    row = {"id": req.get("id"), "name": req.get("name") or str(req.get("id") or "").title()}
    if kind == "authority":
        row["role"] = req.get("role")
        row["fronts"] = req.get("fronts") or req.get("role")
    else:
        row["problem"] = req.get("problem") or ""
    for field in ("reads", "hair", "wardrobe", "setting", "register", "lane",
                  "build", "face", "age", "note"):
        if req.get(field):
            row[field] = req[field]
    row["reads"] = row.get("reads") or req.get("who")
    row["wardrobe"] = row.get("wardrobe") or req.get("wardrobe")
    row["setting"] = row.get("setting") or req.get("world")
    if baseline and baseline.get("baseline"):
        row["baseline"] = ("%s — a real frame used as the BASELINE, not a "
                           "likeness: the room, the light and the framing "
                           "carried; the person is different. %s"
                           % (P.rel(baseline["baseline"]), baseline.get("why") or ""))
    row["status"] = "draft"
    return dict((k, v) for k, v in row.items() if v not in (None, ""))


def proposal(req, baseline=None, answer=None, start=None):
    """`{file, path, row, still_open, md}` — what a person has to do."""
    kind = req.get("kind")
    name = FILE_FOR.get(kind)
    b = P.brand(req["brand"], start) if req.get("brand") else {}
    target = b.get("registry") / name if (b and name) else None
    row = row_for(req, baseline)

    still_open = [
        "the Element (the upload widget is a person at a machine, not a "
        "headless run). Until it exists this character runs on the image chain, "
        "which takes image urls, and NOT on the Cinema line, which takes "
        "element ids.",
        "the voice element. Every presenter needs one before fronting a Cinema "
        "Studio ad.",
    ]

    md = ["# %s — proposed, not registered" % (row.get("name") or row.get("id")), "",
          "*Written by the casting component on %s. It proposes; a person "
          "registers. `brands/` is read-only to machines this phase.*"
          % time.strftime("%Y-%m-%d"), "",
          "## 1 · the row", "",
          "Paste it into the `people` list of:", "",
          "    %s" % (P.rel(target, start) if target else
                      "(no `kind` declared — authority.json or roster.json)"), "",
          "```json", json.dumps(row, indent=1, ensure_ascii=False), "```", "",
          "## 2 · then rebuild the readable sheet", "",
          "The sheet is rendered from the records and is NEVER edited by hand —",
          "correct the JSON and rebuild it, with whatever tool owns that job today",
          "(`the team notes/casting/build_cast.py --brand %s` as of 2026-09-22)."
          % req.get("brand", "<brand>"), "",
          "## 3 · close the gap this build was for", "",
          "The role asked for was **%s**." % (req.get("role") or "(none named)")]
    for line in ((answer or {}).get("gap") or {}).get("open_items") or []:
        md += ["", "- open item on record: %s" % line]
    md += ["", "Replace the open item with what is *actually* still missing:", ""]
    md += ["- %s" % s for s in still_open]
    md += ["", "## 4 · the bible", "",
           "`bible/character.md` beside this file is a DRAFT: where he or she came",
           "from and what carried, the wardrobe that never varies, the register, the",
           "load-bearing details (the two or three things a re-roll drops first), the",
           "boards, and what is still open. Finish it, then move it to",
           "`%s`." % P.rel(P.character(req["brand"], req.get("id") or "<id>", start)["bible"], start)
           if req.get("brand") else "", ""]
    return {"file": name, "path": str(target) if target else None,
            "row": row, "still_open": still_open, "md": "\n".join(md)}


BIBLE = """# {name}

*Draft, written by the casting component on {date}. A person finishes it —
this file is what a HUMAN reads, and the registry is what a machine reads.*

## Where this person came from, and what carried

Baseline: {baseline}

{baseline_why}

The baseline is a BASELINE, not a likeness. What carried is the world — the
room, the framing, the light, the camera register, the wardrobe category — so
a generated shot cuts against filmed footage without a visible change of
world. The person is a different person.

## Who they are

{who}

## Wardrobe — this never varies

{wardrobe}

## The world they are shot in

{world}

## Register

*(to fill: how they talk, who they talk to, what they never do)*

## Lane, and what they front

Role asked for: {role}
Record: {kind}

## The load-bearing details

*(to fill: the two or three things a re-roll drops first. Write them as things
to CHECK, not as adjectives.)*

## The boards

{boards}

**The board outranks the prose.** Handedness is the thing a generator flips
without noticing. Match the board, correct the board, never the shot.

## Still open

{still_open}
"""


def bible(req, baseline=None, filed=None, still_open=None):
    boards = "\n".join("- `%s` — %s" % (P.rel(p), step)
                       for step, p in sorted((filed or {}).items())) or \
        "*(none filed — every sheet was held)*"
    return BIBLE.format(
        name=req.get("name") or str(req.get("id") or "").title(),
        date=time.strftime("%Y-%m-%d"),
        baseline=P.rel((baseline or {}).get("baseline") or "(none)"),
        baseline_why=(baseline or {}).get("why") or "",
        who=req.get("who") or "", wardrobe=req.get("wardrobe") or "",
        world=req.get("world") or "", role=req.get("role") or "",
        kind=req.get("kind") or "", boards=boards,
        still_open="\n".join("- %s" % s for s in (still_open or [])))


def write(out_dir, req, baseline=None, answer=None, filed=None, start=None):
    """Write the proposal and the draft bible INTO THE RUN, never into the
    brand. Returns the proposal."""
    p = proposal(req, baseline, answer, start)
    d = Path(out_dir) / "register"
    d.mkdir(parents=True, exist_ok=True)
    (d / "proposed-row.json").write_text(
        json.dumps({"file": p["file"], "path": p["path"], "list": "people",
                    "row": p["row"]}, indent=1, ensure_ascii=False) + "\n")
    (d / "REGISTER.md").write_text(p["md"] + "\n")
    bd = Path(out_dir) / "bible"
    bd.mkdir(parents=True, exist_ok=True)
    (bd / "character.md").write_text(
        bible(req, baseline, filed, p["still_open"]) + "\n")
    p["written"] = [str(d / "proposed-row.json"), str(d / "REGISTER.md"),
                    str(bd / "character.md")]
    return p
