#!/usr/bin/env python3
"""The comment-reply sticker (owner, 17 Nov 2026: "we need the comment reply at the top with the variations"): the
platform's native reply bubble laid over a scene as its HyperFrames card, and one hook version per comment.

    python3 reply_card.py <production>          the opening gets the control comment; every other comment in the
                                                 writing brief's hooks becomes a hook version (H1, H2, ...) that
                                                 replaces the opening with the same shots and its own comment

What it reads: the writing brief's `hooks` (each hook's `card` or `text`: the comment) and its `layers.hook.look`.
What it writes, in briefs/<production>/: a new take of the opening scene with a `hyperframes.card` step and its
`card/` project; scenes/H<k>/take-1.json (+ card/) for each variation, `replaces` the opening; brief.json `hooks`.
Takes already there are never changed: a new take is saved and picked. Brand-agnostic: the words come from the brief.
"""
import copy
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves
import settings as ST  # noqa: E402

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
html,body{margin:0;background:#000}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden;background:#000;
  font-family:-apple-system,"SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif}
#bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
#reply{position:absolute;left:70px;top:300px;max-width:760px;background:#fff;border-radius:26px;padding:22px 30px 24px 22px;
  display:flex;gap:18px;align-items:flex-start;box-shadow:0 8px 28px rgba(0,0,0,.28);opacity:0;transform-origin:0 0}
#av{flex:0 0 64px;height:64px;border-radius:50%;background:#d9d9d9}
#who{font-size:26px;color:#8a8a8a;font-weight:500;margin:2px 0 6px}
#txt{font-size:40px;line-height:1.22;color:#111;font-weight:600}
</style></head><body>
<div id="stage" data-composition-id="comment-reply" data-start="0" data-width="1080" data-height="1920" data-fps="30" data-duration="{{DUR}}">
<video id="bg" class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="1" data-timeline-label="scene, original sound" src="assets/bg.mp4" data-media-start="0" muted playsinline></video>
<div class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="2" data-timeline-label="comment reply">
<div id="reply"><div id="av"></div><div><div id="who">__WHO__</div><div id="txt">__TEXT__</div></div></div>
</div>
<script>
const IN={{IN}}, OUT={{OUT}};
const tl = gsap.timeline({ paused: true });
tl.fromTo("#reply",{opacity:0,scale:.82,y:-18},{opacity:1,scale:1,y:0,duration:.28,ease:"back.out(2.2)"},IN);
tl.to("#reply",{opacity:0,duration:.18},Math.max(IN+0.3,OUT-0.18));
window.__timelines = window.__timelines || {};
window.__timelines["comment-reply"] = tl;
</script>
</div></body></html>
"""


def lay(scene_dir, text, who="Reply to comment", project="card"):
    """Write the sticker's HyperFrames project into the scene folder; -> the scene step that plays it."""
    proj = Path(scene_dir) / project
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    page = TEMPLATE.replace("__TEXT__", html.escape(str(text))).replace("__WHO__", html.escape(str(who)))
    (proj / "index.template.html").write_text(page)
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components",
                                                                 "assets": "assets"}}))
    (proj / "meta.json").write_text(json.dumps({"id": "comment-reply", "name": "comment-reply"}))
    return {"id": "card-reply", "tool": "hyperframes.card", "model": None, "prompt": str(text), "seed": None,
            "inputs": {"project": project}, "params": {"in": 0.0, "kind": "comment_reply"},
            "note": "the comment-reply sticker, top left, the whole opening (reply_card.py)"}


PROOF = """<!doctype html>
<html><head><meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
html,body{margin:0;background:#000}
#stage{position:relative;width:1080px;height:1920px;overflow:hidden;background:#000}
#bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(.55)}
.pr{position:absolute;left:171px;top:448px;width:640px;border-radius:28px;overflow:hidden;
  border:8px solid #fff;box-shadow:0 18px 50px rgba(0,0,0,.6);opacity:0}
.pr img{width:100%;display:block}
</style></head><body>
<div id="stage" data-composition-id="proof" data-start="0" data-width="1080" data-height="1920" data-fps="30" data-duration="{{DUR}}">
<video id="bg" class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="1" data-timeline-label="scene, original sound" src="assets/bg.mp4" data-media-start="0" muted playsinline></video>
<div class="clip" data-start="0" data-duration="{{DUR}}" data-track-index="2" data-timeline-label="before and after">
__IMGS__
</div>
<script>
const IN={{IN}}, OUT={{OUT}}, N=__N__, EACH=(OUT-IN)/N;
const tl = gsap.timeline({ paused: true });
for (let i = 0; i < N; i++) {
  const s = IN + i * EACH, el = "#p" + i;
  tl.fromTo(el,{opacity:0,scale:.86},{opacity:1,scale:1,duration:.22,ease:"back.out(2)"},s);
  if (i < N - 1) tl.to(el,{opacity:0,duration:.12},s + EACH - .12);
}
window.__timelines = window.__timelines || {};
window.__timelines["proof"] = tl;
</script>
</div></body></html>
"""


def proofs_for(brand, band="", n=3):
    """The before-and-after proof pictures for the ad's audience (asset index proof rows: the brand's own customer
    results), best first; the band's skin words when the filing gives them. -> [(drive id, file name)]."""
    sys.path.insert(0, str(ST.part("asset-index") / "library"))
    import library as LB
    rows = [r for r in LB.rows_of(brand) if r.get("source") == "proof" and "before and after" in str(r.get("shows")).lower()]
    want = {"black": "deep skin", "white": "light skin", "latino": "medium skin", "south-asian": "medium skin"}
    words = next((v for k, v in want.items() if ("/%s/" % k) in "/%s/" % band), "")
    pick = [r for r in rows if words and words in str(r.get("shows")).lower()] or rows
    return [(r["clip"], r["label"].split("/")[-1]) for r in pick[:n]]


def lay_proof(scene_dir, pictures, project="card"):
    """The before-and-afters laid over a scene, one after the other, full size; -> the scene step that plays them.
    pictures: [(drive id, file name)] fetched by id from Shared Assets (gdrive-creator), never through the mount."""
    proj = Path(scene_dir) / project
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ST.part("gdrive-creator")))
    from gdrive_creator import engine as E
    imgs = []
    for i, (fid, name) in enumerate(pictures):
        dest = proj / "assets" / ("proof-%d%s" % (i, Path(name).suffix.lower() or ".jpg"))
        if not dest.is_file():
            E.get_media(fid, str(dest))
        imgs.append('<div class="pr" id="p%d"><img src="assets/%s"></div>' % (i, dest.name))
    page = PROOF.replace("__IMGS__", "\n".join(imgs)).replace("__N__", str(len(imgs)))
    (proj / "index.template.html").write_text(page)
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components",
                                                                 "assets": "assets"}}))
    (proj / "meta.json").write_text(json.dumps({"id": "proof", "name": "proof"}))
    return {"id": "card-proof", "tool": "hyperframes.card", "model": None, "prompt": "before and after", "seed": None,
            "inputs": {"project": project}, "params": {"in": 0.2, "kind": "before_after"},
            "note": "the brand's own before-and-afters, one after the other (reply_card.py proofs_for)"}


def proof_scene(n, scene):
    """A new take of the scene with the before-and-afters over its shots (picked)."""
    import video_studio as VS
    B = Path(VS.bdir(n))
    brief = VS.load(B / "brief.json")
    cfg = brief.get("shot_fill") or {}
    band = ((cfg.get("hands_like") or [""])[0]).strip("/")
    pics = proofs_for(cfg.get("brand") or "", band)
    if not pics:
        raise SystemExit("the asset index has no before-and-after proof for this brand")
    base = VS.load(VS._pick_take(n, scene, brief))
    steps = [s for s in base.get("steps") or [] if s.get("tool") != "hyperframes.card"]
    sd = Path(VS.sdir(n, scene))
    k = 1 + max([int(m.group(1)) for f in sd.glob("take-*.json") for m in [re.match(r"take-(\d+)\.json$", f.name)] if m] or [0])
    wf = dict(copy.deepcopy(base), take="take-%d" % k, steps=steps + [lay_proof(sd, pics)], from_take=brief["picks"][scene])
    VS.save(str(sd / ("take-%d.json" % k)), wf)
    brief["picks"][scene] = "take-%d" % k
    VS.save(str(B / "brief.json"), brief)
    print(json.dumps({"scene": scene, "take": "take-%d" % k, "proof": [nm for _, nm in pics]}))


def _brief_doc(run):
    t = (Path(ST.WRITING) / run / "stages" / "5-brief.md").read_text()
    return json.loads(re.findall(r"```json\s*\n(.*?)\n```", t, re.S)[-1])


def comments(doc):
    """(control, [variations]) comment texts from the writing brief's hooks, in order."""
    hs = [h for h in doc.get("hooks") or [] if isinstance(h, dict) and (h.get("card") or h.get("text"))]
    if not hs:
        return None, []
    ctrl = next((h for h in hs if (h.get("take") == "control" or "control" in str(h.get("id", "")).lower())), hs[0])
    pick = lambda h: str(h.get("card") or h.get("text")).strip()  # noqa: E731
    seen, rest = {pick(ctrl).lower()}, []
    for h in hs:                                  # one version per distinct comment: a repeat of one already used is dropped
        if h is ctrl or pick(h).lower() in seen:
            continue
        seen.add(pick(h).lower())
        rest.append((h.get("id") or "", pick(h)))
    return pick(ctrl), rest


def main(n):
    import video_studio as VS
    B = Path(VS.bdir(n))
    brief = VS.load(B / "brief.json")
    doc = _brief_doc(brief.get("run") or brief["brief"])
    ctrl, rest = comments(doc)
    if not ctrl:
        raise SystemExit("the writing brief names no hook comments")
    first = brief["order"][0]
    base = VS.load(VS._pick_take(n, first, brief))
    steps = [s for s in base.get("steps") or [] if s.get("tool") != "hyperframes.card"]
    # the opening: a new take, its shots as they are, the control comment over them
    sd = Path(VS.sdir(n, first))
    k = 1 + max([int(m.group(1)) for f in sd.glob("take-*.json") for m in [re.match(r"take-(\d+)\.json$", f.name)] if m] or [0])
    wf = dict(copy.deepcopy(base), take="take-%d" % k, steps=steps + [lay(sd, ctrl)], from_take=brief["picks"][first])
    VS.save(str(sd / ("take-%d.json" % k)), wf)
    brief["picks"][first] = "take-%d" % k
    hooks = []
    for i, (hid, text) in enumerate(rest, 1):
        h = "H%d" % i
        hd = Path(VS.sdir(n, h))
        hd.mkdir(parents=True, exist_ok=True)
        hw = dict(copy.deepcopy(base), scene=h, take="take-1", kind="hook", replaces=first,
                  title="%s · %s" % (hid or h, text[:40]), steps=steps + [lay(hd, text)])
        VS.save(str(hd / "take-1.json"), hw)
        brief["picks"][h] = "take-1"
        hooks.append(h)
    brief["hooks"] = hooks
    VS.save(str(B / "brief.json"), brief)
    print(json.dumps({"opening": first, "control": ctrl, "versions": {h: t for h, (_, t) in zip(hooks, rest)}},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1:2] == ["proof"]:
        proof_scene(sys.argv[2], sys.argv[3])
    else:
        main(sys.argv[1])
