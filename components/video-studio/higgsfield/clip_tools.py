#!/usr/bin/env python3
"""clip_tools.py — the finishing tools a clip can go through (tools.json), one door for all of them.

  clip_tools.py list
  clip_tools.py plan <tool> <clip> --brand B [--start S --end S] [--say "<what to change>"] [--ref <picture>]... [--look L] [--move M] [--seconds N] [--lang spa]
  clip_tools.py make <the same> --out <file> [--cap <credits>]

`plan` spends nothing and calls nothing: the exact words that would be sent, the seconds, the credits, what it replaces, and
what we already have that would do (asset-index made.py). `make` asks Higgsfield for the live quote first (refuses above --cap when one is given), goes through the spend guard (size, inputs, never the same request twice), puts the clip's own sound back, sets the new
seconds into the clip on the exact frames it took out, and adds the piece to the register of what we made.

Only the broken seconds are bought: a fix is cut out of the clip (4 seconds at least), edited, and put back.
A row that says engine "ours" is run by its own tool and is refused here by name. Python 3.9, standard library.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parents[1]
KEEP = ("KEEP THE SHOT: @Video1 is the original. Keep the same place, every object, every person, their faces, hair, clothes, skin "
        "and race, their positions, movements, expressions and lip movement, the framing, the camera movement and the timing. "
        "Keep every product exactly as it is: its shape, colour, label and size. Keep every word on screen exactly as it is. "
        "Nobody gets a new accessory. Add nothing, remove nothing.")


class Refused(RuntimeError):
    pass


def _mod(rel, name):
    if name not in sys.modules:
        f = COMP / rel
        sys.path.append(str(f.parent))
        s = importlib.util.spec_from_file_location(name, str(f))
        m = importlib.util.module_from_spec(s)
        sys.modules[name] = m
        s.loader.exec_module(m)
    return sys.modules[name]


def tools():
    return json.loads((HERE / "tools.json").read_text())["tools"]


def tool(tid):
    t = next((x for x in tools() if x["id"] == tid), None)
    if not t:
        raise Refused("no tool called %s; there are: %s" % (tid, ", ".join(x["id"] for x in tools())))
    return t


def window(length, start, end, least, most):
    """(a, b): the seconds that are bought. The asked seconds, widened inside the clip to the shortest the tool takes."""
    a, b = (0.0, length) if start is None else (float(start), float(end if end is not None else length))
    if a < 0 or b > length + 0.05 or b <= a:
        raise Refused("those seconds are not in the clip (it is %.2f s long)" % length)
    if length + 0.05 < least:
        raise Refused("the clip is %.2f s; this tool takes %g s at least" % (length, least))
    if b - a < least:
        mid = (a + b) / 2
        a = max(0.0, min(mid - least / 2, length - least))
        b = a + least
    if b - a > most:
        raise Refused("%.1f s asked; this tool takes %g s at most. Give it the seconds that need it" % (b - a, most))
    return round(a, 3), round(min(b, length), 3)


def words(t, say="", look=None, move=None, refs=()):
    """The words sent. The change first, then everything that must not move."""
    say = (say or "").strip()
    if t["id"] == "fix":
        if not say:
            raise Refused("say what is wrong and what it should be")
        seen = "".join("@Image%d is the real thing itself: the same shape, colour, size, label and words, never redrawn.\n" % i for i, _ in enumerate(refs, 1))
        return "CHANGE ONLY THIS: %s\n%s\n%s" % (say, seen, KEEP.replace("Add nothing, remove nothing.", "Change nothing that the first line does not name."))
    if t["id"] == "relight":
        if look not in t["looks"]:
            raise Refused("pick a light: " + ", ".join(t["looks"]))
        return "LIGHT AND COLOUR CHANGE ONLY.\n\n%s\n\nNEW LIGHT: %s%s Light wraps faces and bodies and moves with them, never a flat filter." % (
            KEEP, t["looks"][look], (" " + say.rstrip(".") + "." if say else ""))
    if t["id"] == "angle":
        if move not in t["moves"]:
            raise Refused("pick a camera: " + ", ".join(t["moves"]))
        return ("The same moment as @Video1, filmed again by another camera: %s.%s The same place, people, faces, race, clothes, product and label, "
                "light, colour and actions in the same order. Only the camera is new. No words on screen." % (t["moves"][move], (" " + say.rstrip(".") + "." if say else "")))
    if t["id"] == "extend":
        if not say:
            raise Refused("say what happens next")
        return ("Carry @Video1 on from its last frame without a cut: %s. The same person, face, race, clothes, place, light, lens and camera. "
                "The product keeps its exact shape, colour, label and size. No words on screen." % say.rstrip("."))
    return say


def plan(tid, clip, brand, start=None, end=None, say="", look=None, move=None, seconds=None, lang=None, length=None, refs=()):
    t = tool(tid)
    if t["engine"] == "ours":
        raise Refused("%s is ours and free: use %s" % (t["name"], t["by"]))
    if t.get("by"):
        raise Refused("%s has its own door: %s" % (t["name"], t["by"]))
    clip = Path(clip)
    if length is None:
        if not clip.is_file():
            raise Refused("the file is not there: " + clip.name)
        length = _mod("video-edit/machine/shot_engine.py", "ct_shot_engine").length(clip)
    r = {"tool": tid, "name": t["name"], "clip": str(clip), "brand": brand, "clip_seconds": round(length, 2), "instead_of": t.get("instead_of")}
    if t.get("workflow"):
        if lang not in t["languages"]:
            raise Refused("pick a language: " + ", ".join(t["languages"]))
        r.update(workflow=t["workflow"], params={"target_language": lang}, seconds=round(length, 2), words="")
        if length > t["max_s"]:
            raise Refused("%.0f s is longer than %g s" % (length, t["max_s"]))
    else:
        if tid == "extend":
            n = float(seconds or t["min_s"])
            if not t["min_s"] <= n <= t["max_s"]:
                raise Refused("carry it on by %g to %g seconds" % (t["min_s"], t["max_s"]))
            r["seconds"] = n
        else:
            a, b = window(length, start, end, t["min_s"], t["max_s"])
            r.update(start=a, end=b, seconds=round(b - a, 2))
        refs = [str(x) for x in refs or []]
        if tid == "fix":                                                # a casting sheet's letters are too small to read: its front view goes, big
            PF = _mod("video-production/machine/product_front.py", "ct_product_front")
            refs = [str(PF.front(x)) if Path(x).name.endswith("product-sheet.png") and Path(x).is_file() else x for x in refs]
        bad = [Path(x).name for x in refs if not Path(x).is_file()]
        if bad:
            raise Refused("the file is not there: " + ", ".join(bad))
        if tid == "fix" and not refs and re.search(r"missing|add |put |should (hold|have|be holding)|product|label|bottle|tube|jar|box|book", say or "", re.I):
            raise Refused("this puts a thing in the shot: attach its picture (--ref), or it will be made up")
        r["refs"] = refs
        r["words"] = words(t, say, look, move, refs)
        r["params"] = {"mode": t["mode"], "resolution": "480p", "duration": int(-(-r["seconds"] // 1)), "aspect_ratio": "auto", "generate_audio": False}
        if tid == "extend":
            r["params"]["extension_mode"] = "forward"
    r["credits"] = round(t["credits_s"] * r["seconds"], 1)
    r["remake_credits"] = round(3 * length, 1)                       # the whole clip made again at 480p
    r["cheaper_than_a_remake"] = r["credits"] < r["remake_credits"]
    if tid in ("extend", "angle"):
        try:
            r["already_have"] = [{k: x.get(k) for k in ("id", "file", "url", "what", "score")} for x in
                                 _mod("asset-index/machine/made.py", "ct_made").close(brand, "clip", say or r["words"], floor=0.55)]
        except (OSError, ValueError):
            r["already_have"] = []
    return r


def _cli(p, piece, price=False):
    """The command line, as a list: the quote (free) or the job."""
    hc = _mod("video-production/machine/higgsfield_cli.py", "ct_higgsfield_cli")
    if p.get("workflow"):
        a = ["generate", "cost" if price else "workflow"] + (["workflow"] if price else []) + [p["workflow"]]
        a += ["--duration", str(p["seconds"])] if price else ["--video", str(piece)]
        return hc, a + [x for k, v in p["params"].items() if not price for x in ("--" + k, str(v))] + ["--json"]
    a = ["generate", "cost" if price else "create", p["job"], "--prompt", p["words"], "--video-references", str(piece)]
    for x in p.get("refs") or []:
        a += ["--image-references", str(x)]
    for k, v in p["params"].items():
        a += ["--" + (k if k != "aspect_ratio" else "aspect-ratio"), str(v).lower() if isinstance(v, bool) else str(v)]
    return hc, a + ["--json"]


def quote(p, piece, run=None):
    hc, a = _cli(p, piece, price=True)
    code, out, err = (run or hc._run)(a, timeout=600)
    m = re.search(r"\"credits(?:_exact)?\"\s*:\s*([0-9.]+)", out) or re.search(r"([0-9.]+)\s*credits", out)
    if code != 0 or not m:
        raise Refused("no live quote, nothing sent: " + (out + err).strip()[:200])
    return float(m.group(1))


def fit(new, seconds, out, SE):
    """The piece that came back, held to the exact seconds it replaces (it can come back a few frames short)."""
    have = SE.length(new)
    if abs(have - seconds) > 0.06 * seconds + 0.1:
        raise Refused("it came back %.2f s long, not %.2f s: not put in" % (have, seconds))
    SE._run(["ffmpeg", "-v", "error", "-y", "-i", str(new), "-an", "-vf", "setpts=PTS*%.6f,fps=30,tpad=stop_mode=clone:stop_duration=0.1" % (seconds / have),
             "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", str(out)])
    return out


def put_back(clip, new, a, b, out, SE):
    """The clip with its seconds a to b replaced, the sound and the length untouched."""
    n = SE.length(clip)
    size = [int(x) for x in SE._run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
                                     str(clip)]).stdout.strip().split("x")[:2]]
    size = (size[0] // 2 * 2, size[1] // 2 * 2)
    items = [x for x in ({"file": clip, "in": 0, "seconds": a}, {"file": new, "in": 0, "seconds": b - a}, {"file": clip, "in": b, "seconds": n - b})
             if x["seconds"] > 0.05]
    return SE.build(items, out, audio=clip if SE.has_audio(clip) else None, size=size)


def make(p, out, cap=None, hc=None, sp=None, job=None):
    SE = _mod("video-edit/machine/shot_engine.py", "ct_shot_engine")
    out = Path(out)
    if p.get("already_have") and not (sp or _mod("generative-model-house/spend.py", "gmh_spend"))._yes():
        raise Refused("we already made one that fits, nothing sent: " + p["already_have"][0]["id"])
    if not p.get("workflow"):
        m = _mod("generative-model-house/model_house.py", "ct_model_house").model(tool(p["tool"])["house"])
        p = dict(p, job=m["id"])
    sp = sp or _mod("generative-model-house/spend.py", "gmh_spend")
    with tempfile.TemporaryDirectory() as d:
        piece = Path(p["clip"])
        if p.get("start") is not None and (p["start"] > 0.02 or p["end"] < p["clip_seconds"] - 0.05):
            piece = Path(d) / "piece.mp4"
            SE._run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % p["start"], "-i", p["clip"], "-t", "%.3f" % (p["end"] - p["start"]),
                     "-c:v", "libx264", "-crf", "14", "-c:a", "aac", str(piece)])
        jt = p.get("job") or p["workflow"]
        hcm = hc or _mod("video-production/machine/higgsfield_cli.py", "ct_higgsfield_cli")
        fp = sp.fingerprint(jt, dict(p["params"], prompt=p["words"], clip=Path(p["clip"]).name, at=p.get("start")), [p["clip"]] + list(p.get("refs") or []))
        asked, jid = p.get("credits"), job                               # a job already sent is collected, never sent again
        if not jid:
            sp.check(jt, p["params"])
            sp.inputs(p["words"], [piece] + list(p.get("refs") or []))
            asked = quote(p, piece, run=hcm._run)
            if cap is not None and asked > float(cap):
                raise Refused("the quote is %g credits, over the cap of %g: nothing sent" % (asked, float(cap)))
            fp = sp.once(jt, dict(p["params"], prompt=p["words"], clip=Path(p["clip"]).name, at=p.get("start")), [p["clip"]] + list(p.get("refs") or []))
            _, args = _cli(p, piece)
            code, txt, err = hcm._run(args, timeout=900)
            jid = hcm._job_id(txt) if code == 0 else None
            if not jid:
                raise Refused("not confirmed: read the account's recent jobs before sending again. " + (txt + err).strip()[:200])
        raw = out.with_name(out.stem + "-piece.mp4")
        sp.record(jt, fp, jid, raw)                                      # on the books the moment it is sent
        body = hcm.wait(jid)
        urls = hcm.outputs(body)
        if not urls:
            raise Refused("job %s ended %s with nothing to download" % (jid, body.get("status")))
        hcm.download(urls[0], raw)
        if p["tool"] in ("fix", "relight"):
            put_back(p["clip"], fit(raw, p["end"] - p["start"], Path(d) / "fit.mp4", SE), p["start"], p["end"], out, SE)
        elif p["tool"] == "angle":
            fit(raw, p["end"] - p["start"], out, SE)
        else:
            out.write_bytes(raw.read_bytes())
    try:
        SE.sheet([(out, 0, SE.length(out))], out.with_name(out.stem + "-look-first.png"))
    except (RuntimeError, OSError):
        pass
    try:
        mk = _mod("asset-index/machine/made.py", "ct_made")
        if hc is None:
            mk.pull()
            mk.build(p["brand"])
    except Exception:  # noqa: BLE001  the piece is made and kept; the register catches up at the next build
        pass
    return {"file": str(out), "credits": asked, "job": jid, "seconds": round(SE.length(out), 2)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["list", "plan", "make"])
    ap.add_argument("tool", nargs="?")
    ap.add_argument("clip", nargs="?")
    ap.add_argument("--brand")
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--say", default="")
    ap.add_argument("--look")
    ap.add_argument("--move")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--lang")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--cap", type=float)
    ap.add_argument("--job", help="collect a job already sent")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for t in tools():
            print("%-11s %-32s %s" % (t["id"], t["name"], "free, ours" if t["engine"] == "ours" else "%g credits a second" % t["credits_s"]))
        return 0
    try:
        p = plan(a.tool, a.clip, a.brand, a.start, a.end, a.say, a.look, a.move, a.seconds, a.lang, refs=a.ref)
        if a.cmd == "make":
            if not a.out:
                raise Refused("make needs --out")
            p = make(p, a.out, a.cap, job=a.job)
        print(json.dumps(p, indent=1, ensure_ascii=False))
        return 0
    except RuntimeError as e:
        print("REFUSED: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
