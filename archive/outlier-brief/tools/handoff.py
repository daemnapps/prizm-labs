#!/usr/bin/env python3
"""The hand-offs — an approved concept brief, packaged for each production
chain. Written by code, not by a model: a hand-off carries the brief Damon
approved WORD FOR WORD plus the rows that were picked, so nothing new can be
claimed between his approval and the chain that writes the asset.

This file STARTS NOTHING. It writes files under the run's `deliverable/` and
returns the exact command each chain would be started with. It imports no
other tool's code.

    video   deliverable/handoff--video.json   the CHOICE the existing second
            deliverable/handoff--video.md     door takes (brand · avatar · sub ·
                                              awareness · sophistication ·
                                              format · framework · route), in
                                              the names of its own flags, with
                                              the concept brief carried beside it
    image · copy · page · email
            deliverable/handoff--<medium>.md  a plain brief for that chain

Every hand-off is tagged `concept: <brand>/<label>`, so one idea's pieces sit
together wherever they end up.
"""
import json
import re
import shlex
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402

VIDEO_ROUTES = ("ai", "creator", "founder")                    # the second door's own three
VIDEO_DOOR = "components/video-teardown/machine/compose.py"

# How each chain is started today, and the honest state of its door for a
# brief that did not come from a swipe (SPEC §2 step 6).
CHAINS = {
    "video": {"entry": VIDEO_DOOR, "ready": True,
              "state": "the second door takes this choice today. It has no slot for the concept brief itself yet — "
                       "the brief travels in this hand-off for the day it does (SPEC: \"needs the brief as its input\")."},
    "image": {"entry": "image-production/machine.py", "ready": False,
              "state": "the image chain only knows swipes today; writing from a brief and a template's slots is still to build (SPEC step 6)."},
    "copy": {"entry": "components/copywriter/machine/copy.py", "ready": False,
             "state": "copy production takes a source file to write from; a concept brief as that source is not proven yet."},
    "page": {"entry": "pages/machine/run.py", "ready": False,
             "state": "the pages chain starts from a captured swipe page; entering it from a brief is still to build (SPEC step 6)."},
    "email": {"entry": "components/email-production/email.py", "ready": False,
              "state": "email production takes a source and an argument; a concept brief as that argument is close but not proven (SPEC step 6)."},
}


def slug(s, n=60):
    return (re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower() or "x")[:n]


def product_card(brand, offer):
    """The offer's own product card, if the brand keeps one under that key."""
    if offer:
        f = P.BRANDS / brand / "products" / f"{offer}.md"
        if f.is_file():
            return P.rel(f)
    return "<the product card, workspace-relative>"


def _cmd(parts):
    return " ".join(p if p.startswith("<") else shlex.quote(str(p)) for p in parts)


def command(medium, ctx, pick, file_rel):
    """The exact command that chain would be started with. Anything the concept
    brief cannot know is left as a plainly-marked <blank>, never guessed."""
    b, a, lab = ctx["brand"], ctx["avatar"], f"ob-{slug(ctx['label'], 30)}-{slug(pick['format']['id'], 24)}"
    if medium == "video":
        parts = ["python3", VIDEO_DOOR, "plan", "--brand", b, "--avatar", a]
        if ctx.get("sub"):
            parts += ["--sub", ctx["sub"]]
        parts += ["--awareness", ctx["awareness"], "--sophistication", ctx["sophistication"],
                  "--format", pick["format"]["id"], "--framework", pick["framework"]["id"],
                  "--route", ctx.get("route") or "creator", "--label", lab]
        if ctx.get("product"):
            parts += ["--product", ctx["product"]]
        return _cmd(parts)
    if medium == "copy":
        return _cmd(["python3", CHAINS[medium]["entry"], file_rel, "--brand", b, "--product",
                     product_card(b, ctx.get("offer")), "--avatar", a, "--label", lab, "--dry-run"])
    if medium == "email":
        parts = ["python3", CHAINS[medium]["entry"], file_rel, "--brand", b, "--avatar", a,
                 "--type", pick["format"]["id"]]
        if ctx.get("angle"):
            parts += ["--angle", ctx["angle"]]
        if ctx.get("offer"):
            parts += ["--offer", ctx["offer"]]
        return _cmd(parts + ["--label", lab, "--dry-run"])
    if medium == "page":
        return _cmd(["python3", CHAINS[medium]["entry"], file_rel, "--brand", b, "--avatar", a,
                     "--angle", ctx.get("angle") or "<a signed angle id>", "--funnel", "<the funnel this page is for>",
                     "--next", "<the offer page it hands off to>", "--label", lab,
                     "--source-url", "<none — there is no swipe>", "--product", product_card(b, ctx.get("offer")), "--dry"])
    if medium == "image":
        return _cmd(["python3", CHAINS[medium]["entry"], "<an image run made from this brief>", "--brand", b,
                     "--avatar", a, "--dry-run"])
    raise KeyError(medium)


def _made_in(medium, ctx, pick):
    rows = [("Concept", f"`{ctx['brand']}/{ctx['label']}`"),
            ("Medium", medium),
            ("Format", f"{pick['format'].get('name') or ''} (`{pick['format']['id']}`) — {pick['format'].get('what') or ''}"),
            ("Style", f"{pick['style']['name']} (`{pick['style']['id']}`) — {pick['style'].get('what') or ''}"
             if pick.get("style") else "none carried"),
            ("Framework", f"{pick['framework']['name']} (`{pick['framework']['id']}`)" if pick.get("framework") else "none carried"),
            ("Awareness entry", f"`{ctx['awareness']}`"),
            ("Sophistication", f"`{ctx['sophistication']}`"),
            ("Written for", f"`{ctx['avatar']}`" + (f" · sub `{ctx['sub']}`" if ctx.get("sub") else "")),
            ("Angle", f"`{ctx['angle']}`" if ctx.get("angle") else "none named"),
            ("Offer", f"`{ctx['offer']}`" if ctx.get("offer") else "none named"),
            ("Approved", f"{ctx['approved_by']} · {ctx['approved_at']} · brief `{ctx['brief_sha']}`")]
    return "\n".join(["| | |", "|---|---|"] + [f"| **{k}** | {str(v).replace('|', '/')} |" for k, v in rows])


def brief_md(medium, ctx, pick, brief, cmd):
    chain = CHAINS[medium]
    notes = [f"- {n}" for n in (pick.get("notes") or [])]
    if pick.get("why"):
        notes.insert(0, f"- Why this format: {pick['why']}")
    return "\n".join([
        f"# Hand-off to {medium} — concept `{ctx['brand']}/{ctx['label']}`",
        "",
        "**There is no swipe.** This came through the second door: Damon's own idea, rounded out into a concept "
        "brief he approved. It enters this chain at its WRITING step. The brief below is the approved brief, word "
        "for word — nothing was added after the approval.",
        "",
        _made_in(medium, ctx, pick),
        "",
        *(["## Notes", "", *notes, ""] if notes else []),
        "## Where this chain stands",
        "",
        ("Ready: " if chain["ready"] else "Not ready: ") + chain["state"],
        "",
        "## The command",
        "",
        "```",
        cmd,
        "```",
        "",
        "Nothing was started. Anything in `<angle brackets>` is something the concept brief cannot know; "
        "it is left blank on purpose, not guessed.",
        "",
        "---",
        "",
        "## The approved concept brief",
        "",
        brief.strip(),
        "",
    ])


def video_json(ctx, pick, brief, cmd):
    """The second door's CHOICE, in the names of its own flags."""
    return {
        "concept": f"{ctx['brand']}/{ctx['label']}",
        "for": VIDEO_DOOR,
        "choice": {
            "brand": ctx["brand"], "avatar": ctx["avatar"], "sub": ctx.get("sub"),
            "awareness": ctx["awareness"], "sophistication": ctx["sophistication"],
            "format": pick["format"]["id"], "framework": pick["framework"]["id"],
            "route": ctx.get("route") or "creator", "funnel": "prospect", "topics": [],
            "product": ctx.get("product"),
            "label": f"ob-{slug(ctx['label'], 30)}-{slug(pick['format']['id'], 24)}",
        },
        "style": (pick.get("style") or {}).get("id"),
        "angle": ctx.get("angle"), "offer": ctx.get("offer"),
        "approved": {"by": ctx["approved_by"], "at": ctx["approved_at"], "brief_sha256_12": ctx["brief_sha"]},
        "command": {"plan": cmd, "run": cmd.replace(" plan ", " run ", 1)},
        "state": CHAINS["video"]["state"],
        "concept_brief": brief.strip(),
    }


def held_back(medium, pick):
    """Why a medium gets no hand-off, or None."""
    if not pick.get("format"):
        return pick.get("held_back") or "no format was picked"
    if not pick.get("hand_off"):
        return pick.get("held_back") or "held back"
    if medium == "video":
        if not pick.get("framework"):
            return "the second door needs a framework and none was picked"
        if "additions.json" in str(pick["format"].get("source") or ""):
            return (f"format `{pick['format']['id']}` is in the library but not yet in the video chain's own format bank, "
                    f"which is the list the second door reads")
    return None


def write(deliverable, ctx, picks, brief):
    """Write every hand-off that may be written. → [{medium, files, command, ready, state} | {medium, held_back}]"""
    out = []
    for medium, pick in picks.items():
        why = held_back(medium, pick)
        if why:
            out.append({"medium": medium, "handed_off": False, "held_back": why})
            continue
        deliverable.mkdir(parents=True, exist_ok=True)
        md = deliverable / f"handoff--{medium}.md"
        cmd = command(medium, ctx, pick, P.rel(md))
        files = [md.name]
        if medium == "video":
            (deliverable / "handoff--video.json").write_text(
                json.dumps(video_json(ctx, pick, brief, cmd), indent=1, ensure_ascii=False) + "\n")
            files.insert(0, "handoff--video.json")
        md.write_text(brief_md(medium, ctx, pick, brief, cmd))
        out.append({"medium": medium, "handed_off": True, "files": files, "command": cmd,
                    "chain_ready": CHAINS[medium]["ready"], "chain_state": CHAINS[medium]["state"]})
    return out
