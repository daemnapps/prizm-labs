"""The Drama Ads lane: one film folder, one clip model, a mechanical check at every stage (micro-drama workflow).

A film lives in runs/higgsfield/<brand>/drama-ads-<label>/ (hf_route.py pack writes pack.json and REQUEST.md there).
This door adds what the micro-drama workflow needs between the pack and the edit:

  drama_lane.py models                                   the clip models the format allows, the default first
  drama_lane.py open  <film> --quote quote.json --approved-by NAME --said "<his words>" --cap N [--model ID] [--format F]
                                                         lane.json, state open: written only on the owner's own go on the
                                                         price in quote.json (the Studio's go, or his typed word)
  drama_lane.py check <film> <stage>                     stage = go | sheets | setups | takes; writes checks/<stage>.json
                                                         on a pass, prints every reason and exits 1 on a fail
  drama_lane.py request <film> <request.json>            one outgoing clip request against the lane (model, id, settings,
                                                         reference limits); run before every send
  drama_lane.py learnings <film>                         what earlier runs taught the video station for this brand and
                                                         format: the block every setup is written under, recorded in
                                                         learnings-handed.json (setups and requests are checked against it)
  drama_lane.py decide <film> <clip> <look> "<finding>"  a take finding the run keeps instead of stopping: filed through the
                                                         decision layer (runs/decisions/calls.jsonl) for the owner to agree
                                                         with or overrule; prints the call id that takes.json cites

ANY FORMAT ON A HIGGSFIELD STORY PRESET. The film's format is named when the lane opens (--format, default micro-drama;
song-ad runs /singing-ads) and kept on lane.json; every check reads it from there. What differs by format lives in
that format's playbook block `lane`: the preset, the looks a take is judged on, which sandbox checks must print PASS,
and for a song the plan rules (windows cut on the song's own lines, end to end, no gap).

THE ONLY STOP IS THE QUOTE (owner, 2026-11-27: "the only thing i need to see is quotes"). Every other call in the film
is made by the run and filed through the decision layer; the lane opens from his go on the price.

THE MODEL IS ONE SETTING. lane.json carries `clip_model` (a registry id) and its Higgsfield `clip_vendor_id`; the quote,
every setup, every request and every frozen job must name that one model. The default and the allowed models come from
the format's playbook (formats/playbooks/micro-drama.json, `clip_models`); the vendor id from the model registry
(components/models/models.json). Seedance 2.5 480p is the default; Wan 3.0 is an option priced beside it on every
quote, the owner picks at his go, and either runs the identical steps and checks.

Spends nothing, calls nothing. Brand-agnostic; Python 3.9, standard library.
"""
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMAT = "micro-drama"
STAGES = ("go", "sheets", "setups", "takes")
LOOKS = ("camera", "acting", "identity", "dialogue", "continuity")
LANE_DEFAULT = {"preset": "/drama-ads", "looks": list(LOOKS), "sandbox_checks": ["script", "plan"], "song": False}
CONTACT = re.compile(r"\b(hug|hugs|hugging|hugged|embrace|embraces|kiss|kisses|kissing|kissed)\b", re.I)


def lane_cfg(fmt):
    """The format's lane settings (playbook `lane`), on top of the dialogue defaults."""
    return dict(LANE_DEFAULT, **(_playbook().setting(fmt, "lane", {}) or {}))


def fmt_of(film, fmt=None):
    return fmt or (_read(Path(film) / "lane.json") or {}).get("format") or FORMAT
STILL_CAMERA = re.compile(r"\b(locked[- ]off|static camera|camera (does not|doesn't) move|no camera movement|slow push)\b", re.I)


def repo():
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace found upward of " + str(HERE))


def _playbook():
    f = repo() / "components" / "video-production" / "machine" / "playbook.py"
    s = importlib.util.spec_from_file_location("dl_playbook", str(f))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def models(fmt=FORMAT):
    """{"default": id, "models": {id: settings + vendor_id}} from the format's playbook and the model registry."""
    cm = _playbook().setting(fmt, "clip_models", {}) or {}
    if not cm.get("default") or cm["default"] not in (cm.get("models") or {}):
        raise SystemExit("the %s playbook names no default clip model" % fmt)
    reg = json.loads((repo() / "components" / "models" / "models.json").read_text())
    rows = reg.get("models", reg)
    rows = rows if isinstance(rows, list) else list(rows.values())
    vendor = {r.get("id"): ((r.get("doors") or {}).get("higgsfield") or {}).get("vendor_id") for r in rows if isinstance(r, dict)}
    out = {}
    for mid, spec in cm["models"].items():
        if not vendor.get(mid):
            raise SystemExit("%s is not a Higgsfield model in the registry" % mid)
        out[mid] = dict(spec, vendor_id=vendor[mid])
    return {"default": cm["default"], "models": out}


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(repo().resolve()))
    except ValueError:
        return str(p)


def lane_of(film):
    lane = _read(Path(film) / "lane.json")
    if not isinstance(lane, dict):
        raise SystemExit("no lane.json in " + str(film))
    return lane


def open_lane(film, quote, approved_by, said, cap, model=None, fmt=None, now=None):
    film = Path(film)
    fmt = fmt or FORMAT
    if not (film / "pack.json").is_file():
        raise SystemExit("no pack.json in %s: run hf_route.py pack first" % film)
    if (_read(film / "pack.json") or {}).get("ready") is not True:
        raise SystemExit("the pack is NOT READY; fix what it names before a price goes to the owner")
    q = _read(quote)
    if not isinstance(q, dict):
        raise SystemExit("the quote is not a JSON file: " + str(quote))
    cfg = models(fmt)
    model = model or q.get("clip_model") or cfg["default"]
    if model not in cfg["models"]:
        raise SystemExit("%s is not a clip model of %s (allowed: %s)" % (model, fmt, ", ".join(cfg["models"])))
    bad = []
    if q.get("clip_model") != model:
        bad.append("the quote is for %r, the lane would run %r: quote the lane's model" % (q.get("clip_model"), model))
    if not q.get("drama_ads_id"):
        bad.append("the quote carries no drama_ads_id (get_drama_ads_config answers it)")
    total = q.get("total_credits")
    if not isinstance(total, (int, float)) or total <= 0:
        bad.append("the quote has no total_credits read from get_drama_ads_config")
    elif float(cap) < float(total):
        bad.append("the cap %s is below the quote %s" % (cap, total))
    if not str(approved_by or "").strip() or not str(said or "").strip():
        bad.append("the owner's name and his own words are both needed: a lane opens only on his go")
    if bad:
        raise SystemExit("lane not opened:\n- " + "\n- ".join(bad))
    spec = cfg["models"][model]
    lane = {"lane": "higgsfield", "preset": lane_cfg(fmt)["preset"], "format": fmt, "drama_ads_id": q["drama_ads_id"],
            "clip_model": model, "clip_vendor_id": spec["vendor_id"], "clip_lane": spec.get("lane", "house"),
            "resolution": spec.get("resolution"), "aspect_ratio": spec.get("aspect_ratio"),
            "quote": _rel(quote), "quote_credits": total, "cap_credits": float(cap),
            "approved_by": approved_by, "approved": said,
            "approved_at": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "state": "open"}
    old = _read(film / "lane.json")
    if isinstance(old, dict) and old.get("state") == "open" and old.get("drama_ads_id") != lane["drama_ads_id"]:
        raise SystemExit("an open lane with another drama_ads_id is already here; close it first")
    (film / "lane.json").write_text(json.dumps(lane, indent=1, ensure_ascii=False) + "\n")
    return lane


def _limits(lane, fmt=FORMAT):
    cfg = models(fmt)
    if lane.get("clip_model") not in cfg["models"]:
        return None
    return cfg["models"][lane["clip_model"]]


def check_go(film, fmt=FORMAT):
    film = Path(film)
    bad, lane = [], _read(film / "lane.json")
    if not isinstance(lane, dict):
        return ["no lane.json: the owner's go on the price opens it (drama_lane.py open)"]
    if lane.get("state") != "open":
        bad.append("the lane is not open (state %r)" % lane.get("state"))
    for k in ("drama_ads_id", "approved_by", "approved", "approved_at", "cap_credits", "clip_model", "clip_vendor_id"):
        if not lane.get(k):
            bad.append("lane.json has no " + k)
    spec = _limits(lane, fmt)
    if spec is None:
        bad.append("clip_model %r is not one the format allows" % lane.get("clip_model"))
    elif spec["vendor_id"] != lane.get("clip_vendor_id"):
        bad.append("clip_vendor_id %r is not the registry's %r" % (lane.get("clip_vendor_id"), spec["vendor_id"]))
    q = _read(repo() / str(lane.get("quote") or "")) if lane.get("quote") else None
    if not isinstance(q, dict):
        bad.append("the lane names no readable quote")
    else:
        if q.get("clip_model") != lane.get("clip_model"):
            bad.append("the quote is for another clip model")
        if q.get("drama_ads_id") != lane.get("drama_ads_id"):
            bad.append("the quote is for another drama_ads_id")
        if float(q.get("total_credits") or 0) > float(lane.get("cap_credits") or 0):
            bad.append("the quote is above the cap")
    return bad


def check_sheets(film, fmt=FORMAT):
    """Every person, place and prop sheet made once; the product only from its approved casting sheet in the pack."""
    film = Path(film)
    bad = check_go(film, fmt)
    pack = _read(film / "pack.json") or {}
    allowed = {f for p in (pack.get("here") or {}).get("product") or [] for f in p.get("files") or []}
    sheets = _read(film / "film" / "sheets.json")
    if not isinstance(sheets, dict) or not isinstance(sheets.get("sheets"), list) or not sheets["sheets"]:
        return bad + ["film/sheets.json lists no sheets"]
    seen = set()
    products = 0
    for s in sheets["sheets"]:
        key = (s.get("kind"), s.get("name"))
        if key in seen:
            bad.append("%s %s is made twice: one sheet each, once" % key)
        seen.add(key)
        if s.get("kind") == "product":
            products += 1
            if s.get("source") not in allowed:
                bad.append("product sheet %r is not the approved casting sheet the pack names (%s)" % (s.get("source"), ", ".join(sorted(allowed)) or "none"))
            if s.get("job_id"):
                bad.append("the product is never generated: %s carries a job id" % s.get("name"))
        elif not (s.get("job_id") or s.get("source")):
            bad.append("%s %s has no job id and no banked source" % key)
    if not products:
        bad.append("no product sheet: the product's approved casting sheet goes in every film")
    return bad


def _clips(film):
    script = _read(Path(film) / "film" / "script.json") or {}
    return [c for c in script.get("clips") or [] if isinstance(c, dict) and c.get("id")]


def check_setups(film, fmt=FORMAT):
    """script.json and plan.json passed checks.py; every clip's exact setup is on the page before it is sent."""
    film = Path(film)
    bad = check_sheets(film, fmt)
    lane = _read(film / "lane.json") or {}
    spec = _limits(lane, fmt) or {}
    clips = _clips(film)
    if not clips:
        return bad + ["film/script.json has no clips"]
    if not (film / "film" / "plan.json").is_file():
        bad.append("no film/plan.json")
    cfg = lane_cfg(fmt)
    checks = _read(film / "film" / "checks.json") or {}
    for k in cfg["sandbox_checks"]:
        if str(checks.get(k, "")).strip().upper() != "PASS":
            bad.append("checks.py %s has not printed PASS (film/checks.json)" % k)
    clip_checks = checks.get("clips") or {}
    if cfg.get("song"):
        bad += _song_plan(film, clips, spec)
    setups = _read(film / "film" / "setups.json") or {}
    rows = {s.get("clip"): s for s in setups.get("setups") or [] if isinstance(s, dict)}
    page = setups.get("page")
    if not page or not ((film / str(page)).is_file() or str(page).startswith("https://")):
        bad.append("the setups page is not published (film/setups.json 'page')")
    lim = spec.get("refs") or {}
    lo, hi = (spec.get("duration") or [1, 999])[:2]
    for c in clips:
        cid = c["id"]
        if cfg["sandbox_checks"] and str(clip_checks.get(cid, "")).strip().upper() != "PASS":
            bad.append("checks.py clip %s has not printed PASS" % cid)
        if c.get("make") == "extension" and not spec.get("extension", True):
            bad.append("%s is an extension; %s has none: plan it as a fresh clip" % (cid, lane.get("clip_model")))
        for kind, field in (("image", "images"), ("video", "videos"), ("audio", "voices")):
            n = len(c.get(field) or [])
            if kind in lim and n > lim[kind]:
                bad.append("%s carries %d %s references; %s takes %d" % (cid, n, kind, lane.get("clip_model"), lim[kind]))
        s = rows.get(cid)
        if not s:
            bad.append("%s has no setup on the page" % cid)
            continue
        if s.get("model") != lane.get("clip_vendor_id"):
            bad.append("%s setup is on %r, the lane runs %r" % (cid, s.get("model"), lane.get("clip_vendor_id")))
        for k in ("resolution", "aspect_ratio"):
            if spec.get(k) and s.get(k) != spec[k]:
                bad.append("%s setup %s is %r, the format runs %r" % (cid, k, s.get(k), spec[k]))
        d = s.get("duration")
        if not isinstance(d, (int, float)) or not lo <= d <= hi:
            bad.append("%s duration %r is outside %s-%s s" % (cid, d, lo, hi))
        if not s.get("refs"):
            bad.append("%s setup lists no ordered references" % cid)
        pf = film / str(s.get("prompt_file") or "")
        if not pf.is_file():
            bad.append("%s prompt file is missing" % cid)
        else:
            if s.get("prompt_sha256") != _sha(pf):
                bad.append("%s prompt changed after the setup was published" % cid)
            if not s.get("static_ok") and (STILL_CAMERA.search(pf.read_text()) or not str(s.get("camera") or "").strip()):
                bad.append("%s: every story shot carries a physical camera move (recipe drama-camera-v1); a still shot needs static_ok with its reason" % cid)
        if pf.is_file() and CONTACT.search(pf.read_text()) and not str(s.get("contact_ok") or "").strip():
            bad.append("%s: the prompt has a hug or kiss; house rule: men never hug or kiss men. Restage it, or name who "
                       "touches in contact_ok when it is not two men" % cid)
        if not isinstance(s.get("quote_credits"), (int, float)):
            bad.append("%s setup has no quote" % cid)
        bad += ["%s: %s" % (cid, x) for x in learned_findings(film, fmt, pf.read_text() if pf.is_file() else "",
                                                              {"refs": s.get("refs")})]
    learnings(film, fmt)
    return bad


# WHAT EARLIER RUNS TAUGHT (2026-11-27): the video station's learnings in force (components/run-kit
# run_kit/learnings.py, runs/learnings/) are handed to every setup and checked on every setup and every request; a
# take finding filed here is a candidate the next run learns from.
def _ln():
    kit = str(repo() / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import learnings as LN
    return LN


def _brand(film):
    return (_read(Path(film) / "pack.json") or {}).get("brand")


def learnings(film, fmt=None):
    """The block every setup prompt of this film is written under; the film records which learnings it was handed."""
    try:
        return _ln().handed(film, "video", _brand(film), fmt=fmt_of(film, fmt))
    except Exception:  # noqa: BLE001 -- a store that will not read never stops the lane
        return ""


def learned_findings(film, fmt, prompt, request):
    try:
        LN, b, f = _ln(), _brand(film), fmt_of(film, fmt)
        return (LN.findings(prompt, b, ("video",), f)
                + LN.findings(json.dumps(request, ensure_ascii=False), b, ("video",), f, field="request"))
    except Exception:  # noqa: BLE001
        return []


def _song_plan(film, clips, spec):
    """A song's windows (film/plan.json `windows`: [{clip, start, end}]) run end to end over the song with no gap or
    overlap, each start on a line of lines.tsv when the pack has one, each within the model's length."""
    bad = []
    plan = _read(Path(film) / "film" / "plan.json") or {}
    wins = sorted((w for w in plan.get("windows") or [] if isinstance(w, dict)), key=lambda w: float(w.get("start", 0)))
    song = plan.get("song_seconds")
    if not wins or not isinstance(song, (int, float)):
        return ["film/plan.json needs windows [{clip, start, end}] and song_seconds"]
    ids = {c["id"] for c in clips}
    if [w.get("clip") for w in wins if w.get("clip") not in ids]:
        bad.append("a window names a clip script.json does not have")
    if abs(float(wins[0]["start"])) > 0.05:
        bad.append("the first window does not start at 0")
    for a, b in zip(wins, wins[1:]):
        if abs(float(b["start"]) - float(a["end"])) > 0.05:
            bad.append("windows %s and %s leave a gap or overlap" % (a.get("clip"), b.get("clip")))
    if abs(float(wins[-1]["end"]) - float(song)) > 0.5:
        bad.append("the last window ends at %s, the song at %s" % (wins[-1]["end"], song))
    lo, hi = (spec.get("duration") or [1, 999])[:2]
    for w in wins:
        n = float(w["end"]) - float(w["start"])
        if n > hi:
            bad.append("window %s is %.2f s, over the model's %s s: split it on a line" % (w.get("clip"), n, hi))
    starts = set()
    lines = Path(film) / "lines.tsv"
    if lines.is_file():
        for row in lines.read_text().splitlines():
            parts = row.split("\t")
            try:
                starts.add(round(float(parts[0]), 1))
            except (ValueError, IndexError):
                continue
        for w in wins[1:]:
            if starts and not any(abs(round(float(w["start"]), 1) - x) <= 0.3 for x in starts):
                bad.append("window %s starts at %s, not on a sung line (lines.tsv)" % (w.get("clip"), w["start"]))
    return bad


def check_request(film, req, fmt=None):
    """One outgoing clip request (the params the batch tool will carry) against the lane and its model."""
    film = Path(film)
    fmt = fmt_of(film, fmt)
    lane = _read(film / "lane.json") or {}
    spec = _limits(lane, fmt) or {}
    p = req.get("params", req) if isinstance(req, dict) else {}
    bad = []
    if lane.get("state") != "open":
        bad.append("no open lane")
    if p.get("drama_ads_id") != lane.get("drama_ads_id"):
        bad.append("drama_ads_id is not the lane's")
    if p.get("model") != lane.get("clip_vendor_id"):
        bad.append("model %r is not the lane's %r" % (p.get("model"), lane.get("clip_vendor_id")))
    for k in ("resolution", "aspect_ratio"):
        if spec.get(k) and p.get(k) != spec[k]:
            bad.append("%s %r is not %r" % (k, p.get(k), spec[k]))
    for k, v in (spec.get("params") or {}).items():
        if p.get(k) != v:
            bad.append("%s %r is not %r" % (k, p.get(k), v))
    for k in spec.get("refuse_params") or []:
        if k in p:
            bad.append("%s is not a setting of %s" % (k, lane.get("clip_model")))
    lo, hi = (spec.get("duration") or [1, 999])[:2]
    if not isinstance(p.get("duration"), (int, float)) or not lo <= p["duration"] <= hi:
        bad.append("duration %r is outside %s-%s s" % (p.get("duration"), lo, hi))
    lim = spec.get("refs") or {}
    roles = {"image": "image_references", "video": "video_references", "audio": "audio_references"}
    for kind, role in roles.items():
        n = sum(1 for m in p.get("medias") or [] if isinstance(m, dict) and m.get("role") == role)
        if kind in lim and n > lim[kind]:
            bad.append("%d %s references; %s takes %d" % (n, kind, lane.get("clip_model"), lim[kind]))
    if not str(p.get("prompt") or "").strip():
        bad.append("no prompt")
    bad += learned_findings(film, fmt, str(p.get("prompt") or ""), {"medias": p.get("medias")})
    return bad


def _decide():
    f = repo() / "components" / "video-teardown" / "machine" / "decide.py"
    s = importlib.util.spec_from_file_location("dl_decide", str(f))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def decide_take(film, clip, look, finding):
    """File one kept take finding through the decision layer; the run continues. Returns the call id."""
    looks = lane_cfg(fmt_of(film))["looks"]
    if look not in looks:
        raise SystemExit("look is one of " + ", ".join(looks))
    film = Path(film)
    pack = _read(film / "pack.json") or {}
    item = {"n": "%s-%s" % (clip, look), "element": str(finding)[:400], "status": look}
    calls = _decide().auto(film, {"brand": pack.get("brand")}, "take", [item])
    cid = None if calls else _last_call(film.name, item["n"])
    try:                                                 # the finding teaches the next run (a candidate; twice = in force)
        _ln().harvest(calls=[{"id": cid, "brand": pack.get("brand"), "run": film.name, "gate": "take", "item": item}])
    except Exception:  # noqa: BLE001
        pass
    return cid


def _last_call(run, n):
    q = repo() / "runs" / "decisions" / "calls.jsonl"
    hit = None
    for line in (q.read_text().splitlines() if q.is_file() else []):
        try:
            c = json.loads(line)
        except ValueError:
            continue
        if c.get("run") == run and c.get("gate") == "take" and (c.get("item") or {}).get("n") == n:
            hit = c.get("id")
    return hit


def check_takes(film, fmt=FORMAT):
    """Every request frozen with its job id and matching its published setup; every clip has a take that was looked at."""
    film = Path(film)
    bad = check_setups(film, fmt)
    setups = {s.get("clip"): s for s in (_read(film / "film" / "setups.json") or {}).get("setups") or []}
    jobs = _read(film / "jobs.json") or {}
    sent = [j for j in jobs.get("clips") or [] if isinstance(j, dict)]
    by_job = {j.get("job_id"): j for j in sent if j.get("job_id")}
    for j in sent:
        for why in check_request(film, j.get("request") or {}, fmt):
            bad.append("%s take %s: %s" % (j.get("clip"), j.get("take"), why))
        s = setups.get(j.get("clip")) or {}
        p = (j.get("request") or {}).get("params") or {}
        pf = film / str(s.get("prompt_file") or "")
        if pf.is_file() and p.get("prompt") != pf.read_text():
            bad.append("%s take %s: the prompt sent is not the published setup's prompt" % (j.get("clip"), j.get("take")))
        if [m.get("value") for m in p.get("medias") or []] != [r.get("value") for r in s.get("refs") or []]:
            bad.append("%s take %s: the references sent are not the published setup's, in its order" % (j.get("clip"), j.get("take")))
    takes = _read(film / "film" / "takes.json") or {}
    acc = {t.get("clip"): t for t in takes.get("takes") or [] if isinstance(t, dict) and t.get("accepted")}
    for c in _clips(film):
        t = acc.get(c["id"])
        if not t:
            bad.append("%s has no accepted take" % c["id"])
            continue
        if t.get("job_id") not in by_job:
            bad.append("%s accepted take %s is not a frozen job in jobs.json" % (c["id"], t.get("job_id")))
        looked = t.get("looked") or {}
        for k in lane_cfg(fmt)["looks"]:
            v = looked.get(k)
            if v == "pass":
                continue
            if isinstance(v, dict) and v.get("decided") and v["decided"] == _last_call(film.name, "%s-%s" % (c["id"], k)):
                continue
            bad.append("%s: the take's %s was not looked at and passed, or its finding filed through the decision layer "
                       "(drama_lane.py decide)" % (c["id"], k))
    return bad


CHECKS = {"go": check_go, "sheets": check_sheets, "setups": check_setups, "takes": check_takes}


def check(film, stage, fmt=None):
    if stage not in CHECKS:
        raise SystemExit("stage is one of " + ", ".join(STAGES))
    film = Path(film)
    fmt = fmt_of(film, fmt)
    bad = CHECKS[stage](film, fmt)
    if not bad:
        lane = _read(film / "lane.json") or {}
        out = film / "checks" / (stage + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        files = sorted(str(p.relative_to(film)) for p in [film / "lane.json", film / "pack.json"] + sorted((film / "film").glob("*.json"))
                       + [film / "jobs.json"] if p.is_file())
        out.write_text(json.dumps({"stage": stage, "result": "PASS", "clip_model": lane.get("clip_model"),
                                   "drama_ads_id": lane.get("drama_ads_id"),
                                   "files": {f: _sha(film / f) for f in files}}, indent=1) + "\n")
    return bad


def main(argv):
    if not argv or argv[0] not in ("models", "open", "check", "request", "decide", "learnings"):
        print(__doc__)
        return 2
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None               # noqa: E731
    if argv[0] == "models":
        print(json.dumps(models(opt("--format") or FORMAT), indent=1))
        return 0
    if argv[0] == "open":
        lane = open_lane(argv[1], opt("--quote"), opt("--approved-by"), opt("--said"), opt("--cap") or 0, opt("--model"), opt("--format"))
        print(json.dumps(lane, indent=1, ensure_ascii=False))
        return 0
    if argv[0] == "learnings":
        print(learnings(argv[1]) or "(no learnings in force for this station yet)")
        return 0
    if argv[0] == "decide":
        cid = decide_take(argv[1], argv[2], argv[3], argv[4])
        print(cid or "shadow: the call is logged and the run waits")
        return 0 if cid else 1
    if argv[0] == "request":
        bad = check_request(argv[1], _read(argv[2]) or {})
    else:
        bad = check(argv[1], argv[2])
    print("PASS" if not bad else "\n".join("FAIL " + b for b in bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
