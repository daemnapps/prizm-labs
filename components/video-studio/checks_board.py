"""Every check a production has run, in one record the board draws (canvas Checks panel, GET /api/checks/<production>).
Rule (owner, 12 Nov): all checks run and stay visible, so a change can be pinpointed to the check that asked for it.
Nothing here judges; it collects what each check wrote:
  swipe   SWIPE-CHECK.json (swipe_check.py)          shots   SHOT-COPY.json (shot_copy.py), ours beside the swipe's frame
  voice   voice/continuous/body.json + its audio     render  next-job.json (last render) + versions/
  takes   every scenes/**/take.json (take.py): motion source, cast sheets, what was sent
  casts   brief.json "cast": element ids, each one's de-slop record (make_character.py step 2)
  covers  covers/stage.json (covers_stage.py): each version's cover, the frame and swipe it came from, its checks
  eye     checks-eye.json: checks made by eye (faces against the cast, frame sweeps), written by whoever looked
  edit    edit/stage.json (edit_stage.py): every edit move of the swipe, its second in ours, laid or why not
  motion  every scene's motion chain (components/motion/board.py): its stages and each clip's motion match
"""
import json
import os
import subprocess
from pathlib import Path

CASTING = Path(os.environ.get("VIDEO_STUDIO_CASTING") or
               Path(__file__).resolve().parents[2] / "runs" / "ai-elements")


def _load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _dur(p):
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                    capture_output=True, text=True, timeout=20).stdout)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def _url(n, B, p):
    if not p:
        return None
    p = Path(p)
    try:
        return "/files/%s/%s" % (n, p.resolve().relative_to(B.resolve()))
    except ValueError:
        return None


def _motion_rows(B):
    """The motion chain's rows, from its own board reader (components/motion/board.py, loaded by path; this workspace
    copy, else the one the Studio's data sits in). No component here means no rows."""
    import importlib.util
    roots = [Path(__file__).resolve().parents[1], Path(os.environ.get("VIDEO_STUDIO_MOTION") or "")]
    for root in roots:
        f = root / "motion" / "board.py" if root.name != "motion" else root / "board.py"
        if f.is_file():
            try:
                spec = importlib.util.spec_from_file_location("motion_board", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.rows(B)
            except Exception:  # noqa: BLE001
                return []
    return []


def _beat(b):
    """One beat as read on the board: its own fields (who, action, prop, target) when it has them, else its `do`."""
    if b.get("action"):
        return " ".join(x for x in (b.get("who"), b["action"], ("with the " + b["prop"]) if b.get("prop") else "",
                                    ("to " + b["target"]) if b.get("target") else "") if x)
    return str(b.get("do") or "")


def checks(n, B):
    B = Path(B)
    out = []

    def add(group, name, ok, short, detail="", pics=None, video=None):
        out.append({"group": group, "name": name, "ok": ok, "short": short, "detail": detail, "pics": pics or [], "video": video})

    sw = _load(B / "SWIPE-CHECK.json")
    if sw:
        for c in sw.get("checks", []):
            add("Swipe check", str(c.get("check", "?")).replace("_", " "), None if c.get("note") else bool(c.get("pass")),
                "noted" if c.get("note") else ("pass" if c.get("pass") else "fails"),
                c.get("detail", ""))
    else:
        add("Swipe check", "swipe check", None, "not run", "swipe_check.py has not run on this production")

    sc = _load(B / "SHOT-COPY.json")
    for s in (sc or {}).get("shots", []):
        v = s.get("verdict", "")
        # V57: a shot that differs from the swipe's is ours — shown as a note (grey), never red
        add("Shots vs the swipe", s.get("id", "?"), True if v in ("COPIES", "OWNER", "ADDED") else None, v.lower(),
            "Swipe: %s\nOurs: %s\nWhy: %s\nNeeds: %s" % (s.get("does", ""), s.get("shows", ""), s.get("why", ""), s.get("need", "")),
            [x for x in (_url(n, B, s.get("swipe", "")), _url(n, B, s.get("ours", ""))) if x])

    body = _load(B / "voice" / "continuous" / "body.json")
    if body and body.get("match") is not None:
        a = B / "voice" / "continuous" / body.get("file", "")
        d = _dur(a) if a.exists() else None
        w = len(body.get("text", "").split())
        add("Voice", "heard back", body["match"] >= 0.95, "%.0f%% heard" % (100 * body["match"]), body.get("text", ""))
        if d:
            rate = w / d
            swipe_rate = (_load(B / "voice" / "reads.json") or {}).get("swipe_rate")
            ok = None     # V57: our pace is ours; the swipe's rate is shown for reference, never graded
            add("Voice", "pace", ok, "%.1f words/s" % rate + (" vs swipe %.1f" % swipe_rate if swipe_rate else ""),
                "%d words in %.1f s, model %s" % (w, d, body.get("model")), video=_url(n, B, a))
    else:
        add("Voice", "narration", None, "not read")

    job = _load(B / "next-job.json")
    if job and job.get("stage") == "render":
        for st in job.get("steps", []):
            add("Render", st.get("name", "?"), {"done": True, "stopped": False}.get(st.get("state")), st.get("state", ""), st.get("said", ""))
    cuts = sorted(B.glob("rough-cut-v*-sdr.mp4"), key=lambda f: f.stat().st_mtime)
    if cuts:
        add("Render", "main version", True, cuts[-1].name.split("-sdr")[0].replace("rough-cut-", ""), "", video=_url(n, B, cuts[-1]))
    for v in sorted((B / "versions").glob("*/*.mp4")):
        if v.name != "raw.mp4":
            add("Render", "version " + v.parent.name, True, "rendered", "", video=_url(n, B, v))

    for tj in sorted(B.glob("scenes/*/**/take.json")):
        t = _load(tj)
        if not t:
            continue
        rel = str(tj.parent.relative_to(B / "scenes"))
        mo = (t.get("motion") or {}).get("source")
        out_f = t.get("out")                 # a take not made yet has no "out" (an empty path would read as this folder)
        made = bool(out_f) and Path(out_f).is_file()
        add("AI takes", rel, made, "made" if made else "not made",
            "First frame above. Motion: the 3D rehearsal, %s–%s s\nPeople: %s\nBeats: %s\nWhy: %s" % (
                (t.get("motion") or {}).get("from"), (t.get("motion") or {}).get("to"),
                ", ".join(t.get("cast", {})), " / ".join(_beat(b) for b in t.get("script") or []), t.get("why", "")),
            [x for x in (_url(n, B, t.get("picture", "")),) if x], _url(n, B, out_f) if made else None)
        add("Motion", rel, bool(mo and Path(mo).is_file()), "3D rehearsal" if mo else "none",
            ("The stand-ins' rehearsal, %s–%s s. The take was made to move like this."
             % ((t.get("motion") or {}).get("from"), (t.get("motion") or {}).get("to"))) if mo else "No motion given: the take moved on its own.",
            video=_url(n, B, mo) if mo else None)

    brief = _load(B / "brief.json") or {}
    brand = (brief.get("shot_fill") or {}).get("brand", "")
    for el in brief.get("cast") or []:
        d = CASTING / brand / "casting" / el
        ds = _load(d / "deslop" / "deslop.json")
        add("Casts", el, bool(ds and (d / "full" / "master.png").exists()), "de-slopped" if ds else "no de-slop",
            ("Left: raw. Right: de-slopped (the master every sheet is made from).\nSkin: %s\nHair: %s" % ((ds.get("skin") or {}).get("shows", ""), (ds.get("hair") or {}).get("shows", ""))) if ds else
            "make_character.py step 2 has not run for this cast",
            ["/castfile/%s/%s/%s" % (brand, el, f) for f in ("full/master-raw.png", "full/master.png") if (d / f).exists()])

    # the motion chain (components/motion): every scene's stages (real reference, track, motion read, 3D rehearsal,
    # camera, preview, approval) and every clip's motion match against the real footage, beat by beat
    try:                             # the edit pass (edit_stage.py): every swipe edit move, laid or why not
        import edit_stage as ES
        for r in ES.board_rows(B):
            add(r["group"], r["name"], r["ok"], r["short"], r.get("detail", ""))
    except Exception:  # noqa: BLE001
        pass

    for r in _motion_rows(B):
        add(r.get("group", "Motion"), r.get("name", "?"), r.get("ok"), r.get("short", ""), r.get("detail", ""),
            [u for u in (_url(n, B, x) for x in r.get("pics") or []) if u], _url(n, B, r.get("video")))

    # the cover stage (covers_stage.py): per version the frame it started from, the cover, and why it is held
    for r in ((_load(B / "covers" / "stage.json") or {}).get("versions") or []):
        add("Covers", r.get("version", "?"), True if r.get("ready") else (False if r.get("held") else None),
            "ready" if r.get("ready") else (r.get("held") or "not made")[:80],
            "Frame: %s\nSwipe: %s %s\nWords: \"%s\"\n%s" % (
                (r.get("frame") or {}).get("why", ""), (r.get("swipe") or {}).get("id", ""),
                (r.get("swipe") or {}).get("why", ""), r.get("headline") or "",
                "\n".join("%s %s: %s" % ("✗" if c.get("ok") is False else "✓" if c.get("ok") else "–", c.get("name"), c.get("short"))
                          for c in r.get("checks") or [])),
            [u for u in (_url(n, B, (r.get("frame") or {}).get("file")), _url(n, B, r.get("file"))) if u])

    for e in (_load(B / "checks-eye.json") or []):
        add("By eye", e.get("what", "?"), e.get("ok"), e.get("short", ""), e.get("note", ""))
    return {"production": n, "checks": out,
            "fails": sum(1 for c in out if c["ok"] is False), "open": sum(1 for c in out if c["ok"] is None)}
