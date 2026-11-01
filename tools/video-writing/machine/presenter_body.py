"""Presenter body (stage 3p, 2026-10-20) — a proven ad retold by one presenter in their own world.

the owner, 2026-10-20, after the fight-ad barber bodies: "you did a great job getting an even
spicier script ... we need to add this to our writing tool for video." The body is the
winner's lines in the winner's order; the presenter's world, the culture layer and the
spoken shape are added in one pass (prompts/stage-3p-presenter-body/).

It stands beside writing v2, not inside it: v2 writes our version of a swipe, this writes
the body that is bolted on after a hook. Brand, product, avatar and presenter arrive only
as arguments and brand-folder reads.

    python3 presenter_body.py --brand B --product P --avatar A \
        --winner <teardown run of the proven ad> --presenter <casting folder> \
        --world "their world, in a few lines" --hook "the hook's last frame" \
        --label <label> [--lane paid|organic] [--cta "..."] [--dry-run]

Writes runs/video-writing/<brand>/<label>/presenter-body.md and the prompt as sent beside it.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TD = HERE.parents[1] / "video-teardown" / "machine"
sys.path.insert(0, str(TD))
import chain as C   # noqa: E402

WS = C.WS
PROMPTS = HERE.parent / "prompts" / "stage-3p-presenter-body"


def _read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


def live_prompt():
    files = sorted(PROMPTS.glob("presenter-body-v*-damon.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not files:
        raise SystemExit(f"no presenter-body prompt in {PROMPTS}")
    return files[-1]


def winner_transcript(run_dir):
    d = Path(run_dir)
    t = _read(d / "stages" / "1-transcript.md")
    if not t:
        tear = _read(d / "stages" / "1-teardown.md")
        i = tear.find("### VERBATIM TRANSCRIPT")
        t = tear[i:] if i >= 0 else ""
    if not t:
        raise SystemExit(f"no verbatim transcript in {d}")
    j = t.find("### VOICES")
    return t[:j] if j > 0 else t


def avatar_language(brand, avatar, limit=60):
    rows = []
    lang = WS / "brands" / brand / "core-avatars" / avatar / "language"
    for f in [lang / "prospects.json", lang / "leads.json"] + sorted((lang / "customers").glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        for e in data.get("entries", []):
            t = (e.get("text") or "").strip()
            if 15 < len(t) < 240:
                rows.append(f"- [{e.get('id')}] {t}")
    return "\n".join(rows[:limit]) or "[UNFILLED]"


def presenter_swipe(run_dir):
    """The presenter's swipe as one row per frame-map shot: id, span, who, what happens."""
    if not run_dir:
        return "[UNFILLED]"
    fm = Path(run_dir) / "framemap" / "framemap.json"
    if not fm.is_file():
        return "[UNFILLED]"
    rows = []
    for s in json.loads(fm.read_text()).get("shots") or []:
        m = s.get("map") or {}
        who = ", ".join(m.get("who") or [])
        does = "; ".join(str(x.get("does")) for x in (m.get("moments") or [])[:3])
        rows.append(f"- {s['id']} {s['start']:.2f}-{s['end']:.2f}s ({s['seconds']:.1f}s) · {who} · {does}")
    return "\n".join(rows) or "[UNFILLED]"


def plan_from_body(body_md, out_plan, who="PRESENTER"):
    """The written body's table → production's plan.json: one scene per line, its swipe shot as `source`."""
    scenes = []
    for line in body_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not re.match(r"^\d+$", cells[0]):
            continue
        n, tnums, shot, see, said = cells[:5]
        sc = {"id": f"S{n}", "who": who, "src": tnums, "happens": see or said[:80], "voice": said}
        m = re.match(r"(K\d+)\s+(\d+:\d{2}(?:\.\d+)?)\s*[-–]\s*(\d+:\d{2}(?:\.\d+)?)", shot)
        if m:
            sc.update(kind="motion", to_camera=False, voice_over=True,
                      source=f"{m.group(1)} {m.group(2)}-{m.group(3)}: {see}")
        elif re.search(r"before-and-after|archive|real footage|our footage", see, re.I):
            sc.update(kind="motion", to_camera=False, source_plan="cut", owned_file="archive: " + see[:60])
        else:
            sc.update(kind="talking", to_camera=bool(said), source="none")
        scenes.append(sc)
    Path(out_plan).write_text(json.dumps({"shape": "scene", "scenes": scenes}, indent=1))
    return len(scenes)


# The lane changes only the ask (VIDEO-RULINGS V1; video-system sync W28, 2026-10-21): the same body on
# both lanes, the paid ending taps the button, the organic one asks for the comment word or a follow.
LANE_CTA = {
    "paid": "The winner's own ending: tap the button below, to the offer page. No price.",
    "organic": ("The winner's own ending, with the organic ask: comment the word (one word the body already "
                "says, in capitals) to get the link, or follow. Never a button, never a URL. No price."),
}


def build(a):
    tpl = live_prompt()
    presenter = _read(Path(a.presenter) / "character.md") or "[UNFILLED]"
    fill = {
        "presenter_swipe": presenter_swipe(a.swipe_run),
        "winner_transcript": winner_transcript(a.winner),
        "presenter": presenter + ("\n\n## Their world\n" + a.world if a.world else ""),
        "hook_last_frame": a.hook or "[UNFILLED]",
        "avatar_language": avatar_language(a.brand, a.avatar),
        "culture_map": _read(WS / "brands" / a.brand / "core-avatars" / a.avatar / "culture-map.md") or "[UNFILLED]",
        "product_facts": _read(WS / "brands" / a.brand / "products" / f"{a.product}.md") or "[UNFILLED]",
        "rulings": _read(WS / "runs" / "rulings" / f"{a.brand}.md") or "[UNFILLED]",
        "cta": a.cta or LANE_CTA[a.lane],
    }
    text = tpl.read_text()
    for k, v in fill.items():
        text = text.replace("{" + k + "}", v)
    missing = [k for k, v in fill.items() if v == "[UNFILLED]"]
    return tpl, text, missing


def write(text, out):
    import run as R          # the teardown's engine: clean env, model names, the plain-text rule
    # NO ACCOUNT IS WIRED IN (the owner, 2026-10-23): started through run_kit's claude_door
    # by the teardown's own _claude_run.
    r = R._claude_run(["--model", R._cli_model("opus"), "--output-format", "json",
                       "--allowed-tools", "", "--append-system-prompt", R.PURE_TEXT],
                      text, timeout=1500, cwd=str(C.MACHINE))
    try:
        j = json.loads(r.stdout)
    except ValueError:
        raise SystemExit((r.stderr or r.stdout or "claude failed")[-1200:])
    body = j.get("result") or ""
    if j.get("is_error") or not body.strip():
        raise SystemExit(("claude failed: " + body)[-1200:])
    out.write_text(body)
    return round(j.get("total_cost_usd") or 0, 4)


def main(argv=None):
    p = argparse.ArgumentParser(description="Write a presenter body from a proven ad (stage 3p).")
    for f in ("brand", "product", "avatar", "winner", "presenter", "label"):
        p.add_argument(f"--{f}", required=True)
    p.add_argument("--world", default="", help="the presenter's world in a few lines")
    p.add_argument("--swipe-run", default="", help="the teardown run of the presenter's swipe (its frame map)")
    p.add_argument("--plan", default="", help="also write production's plan.json here from the body's table")
    p.add_argument("--who", default="PRESENTER", help="the presenter's name in the plan")
    p.add_argument("--title", default="", help="the piece's name on the Queue card")
    p.add_argument("--hook", default="", help="the hook's last frame")
    p.add_argument("--lane", choices=["paid", "organic"], default="paid",
                   help="where the piece runs; it changes only the ask (VIDEO-RULINGS V1, 2026-10-21)")
    p.add_argument("--cta", default="", help="the ending, word for word; without it the lane's ask is used")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    tpl, text, missing = build(a)
    out = WS / "runs" / "video-writing" / a.brand / a.label
    print(f"prompt: {tpl.name} · {len(text):,} chars · unfilled: {', '.join(missing) or 'none'}")
    if a.dry_run:
        print(f"would write: {out / 'presenter-body.md'} (nothing sent)")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    (out / "presenter-body.prompt.md").write_text(text)
    cost = write(text, out / "presenter-body.md")
    print(f"wrote {out / 'presenter-body.md'} · ${cost}")
    # FILED ON THE WRITING SHELF (2026-10-20): the body is this piece's brief, so it can take its brief number and
    # its card on the Queue (lab/damon/suite/creative_queue.py production_runs reads `writing_run`).
    (out / "deliverable").mkdir(exist_ok=True)
    (out / "deliverable" / "5-brief.md").write_text((out / "presenter-body.md").read_text())
    (out / "run.json").write_text(json.dumps({"machine": "video-writing", "brand": a.brand, "product": a.product,
                                              "slug": a.label, "label": a.label, "production_route": "ai",
                                              "title": a.title or a.label, "presenter": Path(a.presenter).name,
                                              "stage": "3p presenter body"}, indent=1) + "\n")
    if a.plan:
        n = plan_from_body((out / "presenter-body.md").read_text(), a.plan, a.who)
        prod = Path(a.plan).parent
        rj = prod / "run.json"
        pm = json.loads(rj.read_text()) if rj.is_file() else {}
        pm.update(machine="video-production", brand=a.brand, product=a.product, label=prod.name,
                  writing_run=str(out.relative_to(WS)))
        if a.swipe_run:
            pm["brief_from"] = str(Path(a.swipe_run) / "stages" / "5-brief.md")
        rj.write_text(json.dumps(pm, indent=1) + "\n")
        print(f"plan: {n} scenes → {a.plan} (production routes each one from its swipe shot)")
        # the brief number, then the Queue shows the piece as one card in Production
        r = subprocess.run([sys.executable, str(WS / "tools/image-teardown/tools/briefs.py"), "open", a.label,
                            "--brand", a.brand, "--product", a.product, "--avatar", a.avatar, "--type", "video-ai"],
                           capture_output=True, text=True, cwd=str(WS))
        m = re.search(r"\b\w+_\w+_brief-\d{4}\b", r.stdout + r.stderr)
        if m:
            for p in (rj, out / "run.json"):
                d = json.loads(p.read_text())
                d["brief"] = m.group(0)
                p.write_text(json.dumps(d, indent=1) + "\n")
            print(f"brief number: {m.group(0)} — on the Queue in Production at the next sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
