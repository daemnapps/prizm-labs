#!/usr/bin/env python3
"""deliver — hand Video Edit any finished production and get the delivery back.

    python3 machine/run.py deliver <what> [--dry-run] [--no-file]

The owner's rule (2026-11-21): every edit is handed to Video Edit and comes back done. Format does not matter: the
edit only puts together what production already made (the swipe's order, the writing, the shots, the scenes, the
voice, the music, the AI clips, the pictures) and brings it to life in the detail. So there is one command, and it
finds the road the input needs:

| `<what>` is | road | ends at |
|---|---|---|
| a Video Studio production (`idea-36`, `0332`, …: a folder in the Studio's `briefs/`) | the Studio's edit stages, run by Video Edit's own code (`machine/studio/`): cut → check → render → edit moves → covers | every version (control + hooks) levelled at -14 LUFS, its covers, one card on the approval page |
| a video-production run (`runs/video-production/<brand>/<label>`) | `line.py` (the edit-map line) | renders, covers, a card in `meta/<brand>/1-check/video/` |
| a video-editor hand-off folder (has `manifest.json`) | `run.py handoff --versions` | the master in `returned/`, a card |
| a kit folder (has `edit-kit.json`) | `run.py start --versions` | the master and every version |

It runs straight through: no stops (the review points are the video editor role's, 2026-11-18). It never makes a
picture, a clip, a voice or a line: when production is not finished (shots, voice, AI shots, a song still to make),
it stops and names what production still owes. Every run writes `DELIVERY.md` + `delivery.json` beside the work:
what was made, what was held and why. `--dry-run` says which road and which stages are due, and runs nothing.
`--no-file` stops before the approval page.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VE = HERE.parent
REPO = VE.parents[1]
STUDIO = HERE / "studio"
EDIT_STAGES = ("cut", "check", "render", "edit", "covers")        # the edit's own stages of a Studio production
PRODUCTION_STAGES = {"shots": "the shots (footage search and picks)", "voice": "the narration read",
                     "aishots": "the AI shots", "maker": "the clips the maker still owes",
                     "song": "the song", "songcheck": "the song's check", "songcut": "the song's scene times"}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _studio():
    """The Video Studio's production side (where its productions live) and its stage engine, which now runs Video
    Edit's own stage code (machine/studio/)."""
    home = Path(os.environ.get("VIDEO_STUDIO_HOME") or VE.parent / "video-studio")
    for p in (str(STUDIO), str(home)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import video_studio as VS
    return VS


# ---------------------------------------------------------------- which road
def road_of(what):
    """(road, resolved) for what was handed over; road is studio | line | handoff | kit."""
    p = Path(what).expanduser()
    if p.is_dir():
        p = p.resolve()
        if (p / "manifest.json").is_file():
            return "handoff", p
        if (p / "edit-kit.json").is_file() or (p / "kit" / "edit-kit.json").is_file():
            return "kit", p
        if (p / "plan.json").is_file() and (p / "run.json").is_file():
            return "line", p
        if (p / "brief.json").is_file() and (p / "scenes").is_dir():
            return "studio", p.name
    VS = _studio()
    name = str(what).strip("/").split("/")[-1]
    if (Path(VS.BRIEFS) / name / "brief.json").is_file():
        return "studio", name
    hit = _studio_by_key(VS, name)
    if hit:
        return "studio", hit
    raise SystemExit("DELIVER  %s: not a Studio production, a video-production run, a hand-off or a kit. Name the "
                     "production (as the Studio lists it) or the folder." % what)


def _studio_by_key(VS, key):
    """A Studio production filed under this brief number or key (brief.json `brief_key`, its writing run's number)."""
    key = key.lower()
    for b in sorted(Path(VS.BRIEFS).glob("*/brief.json")):
        try:
            br = json.loads(b.read_text())
        except (OSError, ValueError):
            continue
        num = str((VS._run_json(br) or {}).get("brief") or "")
        names = {str(br.get("brief_key") or "").lower(), num.lower(), str(br.get("brief") or "").lower()}
        if key in names or any(x and (x.endswith("_" + key) or x.endswith("-" + key)) for x in names):
            return b.parent.name
    return None


# ---------------------------------------------------------------- the Studio road
def _run_stage(VS, n, stage):
    """One Studio stage run here, in this process, on the Studio's own job file: the Studio screen shows its steps as
    they go (the Studio is the view). Returns the job as it ended."""
    name, steps = VS.NEXT_STAGES[stage]
    f = os.path.join(VS.bdir(n), "next-job.json")
    jid = "%s-%s-%d" % (n, stage, int(datetime.datetime.now().timestamp()))
    job = {"id": jid, "idea": None, "n": n, "stage": stage, "name": name + " · Video Edit delivery", "done": False,
           "file": f, "open": {"stage": "production", "n": n},
           "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in steps]}
    VS.save(f, job)
    VS.run_next_job(n)
    return VS.load(f)


def _stopped(job):
    return [st for st in job.get("steps") or [] if st.get("state") == "stopped"]


def studio_road(n, dry_run=False, file=True, say=print):
    VS = _studio()
    B = Path(VS.bdir(n))
    rec = {"road": "studio", "production": n, "started": _now(), "stages": [], "held": [], "filed": None}
    running = VS._next_job(n)
    if running and not running.get("done"):
        rec["held"].append("a Next step is already running on this production (%s); delivery waits for it" % running.get("name"))
        return rec
    seen = {}
    for _ in range(12):
        due = VS.next_due(n)
        if due is None:
            break
        if due in PRODUCTION_STAGES:
            rec["held"].append("production is not finished: %s (%s). The edit only assembles what production made."
                               % (PRODUCTION_STAGES[due], due))
            break
        if due not in EDIT_STAGES:
            rec["held"].append("stage %s is not an edit stage" % due)
            break
        if dry_run:
            rec["stages"].append({"stage": due, "state": "due"})
            break
        seen[due] = seen.get(due, 0) + 1
        if seen[due] > 2:
            rec["held"].append("%s came due again after running twice: something it reads keeps changing" % due)
            break
        say("  %s …" % VS.NEXT_STAGES[due][0])
        job = _run_stage(VS, n, due)
        bad = _stopped(job)
        rec["stages"].append({"stage": due, "steps": [{k: st.get(k) for k in ("id", "name", "state", "said")}
                                                      for st in job.get("steps") or []]})
        for st in job.get("steps") or []:
            say("    %-8s %-8s %s" % (st.get("id"), st.get("state"), (st.get("said") or "")[:120]))
        if bad:
            rec["held"] += ["%s: %s" % (st.get("name"), st.get("said")) for st in bad]
            break
    rec["versions"] = [dict(v, video=str(Path(VS.BRIEFS) / v["file"])) for v in VS.versions(n)]
    if not dry_run and not rec["held"]:
        import used_everything as UE              # the edit proves it put together exactly what production made
        found = UE.check(n, B)
        rec["used_everything"] = [{"ok": ok, "check": c, "what": w} for ok, c, w in found]
        for ok, c, w in found:
            say("  %s %s: %s" % ("✓" if ok else "✗", c, w))
        rec["held"] += ["%s: %s" % (c, w) for ok, c, w in found if not ok]
    if not dry_run and file and not rec["held"] and rec["versions"]:
        rec["filed"] = file_studio(VS, n, B, rec["versions"])
        if rec["filed"].get("refused"):
            rec["held"].append("approval page: " + rec["filed"]["refused"])
    return rec


def file_studio(VS, n, B, vers):
    """Every version on one card in 1-check (control first): the approval page's own filer, the covers the cover stage
    handed over. Nothing goes to Meta; Approve is the owner's click."""
    import covers_stage as CS
    brief = CS.brief_of(B)
    key = CS.brief_key(brief, n)
    parts = key.split("_", 2)
    if len(parts) < 3:
        return {"refused": "no brief key of the form <brand>_<product>_<brief> for %s (got %r): number the brief first"
                % (n, key)}
    brand, product, number = parts
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import feed_video as FV
    try:
        p, src = FV.file_master(brand, number, product, FV.N.next_batch(brand), [v["video"] for v in vers],
                                production=n)
    except Exception as e:  # noqa: BLE001 - the filer's refusal is the delivery's hold, named
        return {"refused": str(e)[:300]}
    return {"state": p.get("state"), "card": str(p.get("target") or ""), "ad": (p.get("card") or {}).get("ad_name"),
            "words_from": src, "covers_from": p.get("covers_from"), "cover_checks": p.get("cover_checks")}


# ---------------------------------------------------------------- the other roads
def _cmd(args, say=print):
    say("  $ " + " ".join(str(a) for a in args))
    r = subprocess.run([sys.executable] + [str(a) for a in args], cwd=str(VE), text=True, capture_output=True)
    tail = [ln for ln in (r.stdout + "\n" + r.stderr).splitlines() if ln.strip()]
    for ln in tail[-12:]:
        say("    " + ln)
    return r.returncode, tail


def other_road(road, p, dry_run=False, file=True, say=print):
    rec = {"road": road, "input": str(p), "started": _now(), "held": []}
    if road == "line":
        args = [HERE / "line.py", p] + (["--no-file"] if not file else [])
    elif road == "handoff":
        args = [HERE / "run.py", "handoff", p, "--versions"] + (["--dry-run"] if dry_run else [])
    else:
        kit = p if (p / "edit-kit.json").is_file() else p / "kit"
        k = json.loads((kit / "edit-kit.json").read_text())
        brand, label = k.get("brand"), k.get("label") or p.name
        if not brand:
            raise SystemExit("DELIVER  the kit names no brand (edit-kit.json `brand`)")
        args = [HERE / "run.py", "start", kit, "--brand", brand, "--label", label, "--versions"] + (["--dry-run"] if dry_run else [])
    if dry_run and road == "line":
        rec["plan"] = [str(a) for a in args]
        return rec
    code, tail = _cmd(args, say)
    rec["exit"] = code
    if code:
        rec["held"].append(tail[-1] if tail else "the road stopped")
    return rec


# ---------------------------------------------------------------- the record
def write_record(rec, where):
    where = Path(where)
    where.mkdir(parents=True, exist_ok=True)
    rec["ended"] = _now()
    rec["state"] = "held" if rec.get("held") else ("planned" if rec.get("dry_run") else "delivered")
    (where / "delivery.json").write_text(json.dumps(rec, indent=1) + "\n")
    lines = ["# Delivery: %s" % (rec.get("production") or Path(rec.get("input", "")).name),
             "", "- road: %s" % rec["road"], "- state: **%s**" % rec["state"], "- started %s, ended %s" % (rec["started"], rec["ended"])]
    for st in rec.get("stages") or []:
        lines.append("- stage %s: %s" % (st["stage"], st.get("state") or ", ".join(
            "%s %s" % (x["id"], x["state"]) for x in st.get("steps") or [])))
    if rec.get("versions"):
        lines += ["", "## Versions"] + ["- %s: %s" % (v["id"], v["video"]) for v in rec["versions"]]
    if rec.get("filed"):
        lines += ["", "## Approval page", "```", json.dumps(rec["filed"], indent=1), "```"]
    if rec.get("held"):
        lines += ["", "## Held"] + ["- " + h for h in rec["held"]]
    (where / "DELIVERY.md").write_text("\n".join(lines) + "\n")
    return where


def deliver(what, dry_run=False, file=True, say=print):
    road, p = road_of(what)
    say("DELIVER  %s → the %s road%s" % (what, road, " (dry run)" if dry_run else ""))
    if road == "studio":
        rec = studio_road(p, dry_run=dry_run, file=file, say=say)
        where = Path(_studio().bdir(p))
    else:
        rec = other_road(road, p, dry_run=dry_run, file=file, say=say)
        where = p
    rec["dry_run"] = dry_run
    if dry_run:                                   # a dry run writes nothing, not even its record
        rec["state"] = "held" if rec.get("held") else "planned"
        say("DELIVER  %s (dry run: nothing written)" % rec["state"].upper())
        for st in rec.get("stages") or []:
            say("  next: %s" % st["stage"])
    else:
        out = write_record(rec, where)
        say("DELIVER  %s · %s" % (rec["state"].upper(), out / "DELIVERY.md"))
    for h in rec.get("held") or []:
        say("  held: " + h)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", help="a Studio production, a video-production run, a hand-off folder or a kit")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-file", action="store_true", help="stop before the approval page")
    a = ap.parse_args(argv)
    rec = deliver(a.what, dry_run=a.dry_run, file=not a.no_file)
    return 1 if rec.get("held") else 0


if __name__ == "__main__":
    sys.exit(main())
