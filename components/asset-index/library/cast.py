#!/usr/bin/env python3
"""cast.py — the cast pass: who is on screen and what happens, per scene of a brand's owned footage, so a Real-lane
ad can cast people by role and pick shots from the index alone (owner direction 20 Nov 2026: cast and cut from the
footage we own; generate only true gaps).

One model look per clip at its local 360p proxy (low media resolution), asking
components/asset-index/prompts/cast-pass-v<N>-owner.md: the distinct persons in the clip (gender, age band, visible
skin tone, a look line, which one the clip is about), letterbox, and per scene who is on screen, face visible,
couple, action + action tags, product in use, competitor brand, room, framing, angle, camera move, emotion.

    python3 cast.py run      --brand <brand> --dry-run                 # count and price; send nothing
    python3 cast.py run      --brand <brand> --budget 5 [--limit N] [--workers 8] [--key-env NAME]
    python3 cast.py apply    --brand <brand>                           # write the fields onto library.json rows (free)
    python3 cast.py coverage --brand <brand>                           # story-beat coverage map (free)

Writes only runs/asset-index/<brand>/library/cast/ (results.jsonl, then results-02.jsonl ... near 9 MB; runs.json;
failed.jsonl), the rows of library.json (apply) and library/coverage-story.{json,md} (coverage). Resumable: a clip
already answered is skipped. Every line keeps the prompt as sent, the model and the token usage.

Person ids: the clip's main person carries the creator's id (`<brand>/<creator>`) when the row names a real creator
folder, so one person is findable across every clip they filmed; anyone else, or a main person whose creator is only
a bucket, gets `<brand>/clip/<clip>#<letter>`. Skin tone is the visible shade only; ethnicity stays the Drive filing's.

Proxies are read beside each record; when the records sit in a checkout without media, ASSET_INDEX_MEDIA_ROOTS
(colon-separated runs/asset-index folders of other checkouts) is searched for the same <brand>/<collection>/<clip>.
Rows that cannot be read say why in `cast_reason`.
"""
from __future__ import annotations

import argparse
import base64
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import library as LIB  # noqa: E402
sys.path.insert(0, str(REPO / "components" / "video-teardown" / "tools"))
import gemini_breakdown as gb  # noqa: E402  (key loader + HTTP retry)

MODEL = "gemini-3-flash-preview"   # the check pass's model (Model House fast read); measured on this pass before the backfill
PRICE = (0.50, 3.00)               # USD per 1M input / output tokens, components/models/models.json
CAP_S = 120                        # seconds of each clip sent
FPS = 1
THINK = "low"                     # minimal drifted scene-to-answer alignment on the sample (20 Nov); low held it
EST_PER_CLIP = 0.0020              # measured on a first sample; runs.json keeps the real figure

# The shared words. A brand adds its own (category actions, rooms, story beats) in brands/<brand>/footage-library.json.
ROOMS = ["bathroom", "bedroom", "kitchen", "living-room", "gym", "office", "car", "barbershop", "restaurant-bar",
         "party-club", "wedding-venue", "store", "street", "nature", "beach-pool", "studio-plain", "other-indoor",
         "other-outdoor", "unclear"]
ACTIONS = ["using-product", "applying-product", "showing-product", "unboxing", "mirror-check", "talking-to-camera", "working-out", "playing-sport", "walking", "driving",
           "dancing", "partying", "hugging-kissing", "eating-drinking", "cooking", "working-at-desk", "getting-dressed",
           "waking-up", "phone-use", "reacting", "laughing", "posing"]
EMOTIONS = ["neutral", "happy", "laughing", "confident", "relaxed", "focused", "flirty", "frustrated", "sad",
            "surprised", "unclear"]
FIELDS = ("people_count", "people", "person_ids", "main_person", "woman_present", "couple", "face_visible", "action",
          "action_tags", "product_in_use", "competitor", "room", "framing", "angle", "camera_move", "emotion",
          "letterbox", "cast_checked", "cast_reason")


_CFG: dict = {}


def config(brand: str) -> dict:
    """The brand's footage-library settings (library.brand_config: brands/<brand>/footage-library.json)."""
    if brand not in _CFG:
        _CFG[brand] = LIB.brand_config(brand)
    return _CFG[brand]


def words(brand: str) -> tuple[list, list, list]:
    """(rooms, actions, emotions): the shared words plus the brand's own."""
    c = config(brand)
    add = lambda base, more: base[:-1] + [x for x in more if x not in base] + base[-1:] if base[-1] == "unclear" \
        else base + [x for x in more if x not in base]
    return add(ROOMS, c.get("rooms") or []), add(ACTIONS, c.get("actions") or []), EMOTIONS


def latest_prompt() -> tuple[Path, str]:
    ps = sorted((REPO / "components" / "asset-index" / "prompts").glob("cast-pass-v*-owner.md"),
                key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return ps[-1], ps[-1].read_text()


def outdir(brand: str) -> Path:
    d = LIB.libdir(brand) / "cast"
    d.mkdir(parents=True, exist_ok=True)
    return d


def proxy_of(brand: str, r: dict) -> Path | None:
    if not r.get("frame"):
        return None
    rel = Path(r["frame"]).parent                      # <collection>/<clip>
    roots = [LIB.RUNS] + [Path(x) for x in os.environ.get("ASSET_INDEX_MEDIA_ROOTS", "").split(":") if x]
    for root in roots:
        p = root / brand / rel / "proxy.mp4"
        if p.is_file():
            return p
    return None


def drive_input(clip: str) -> tuple | None:
    """(ffmpeg -headers args, url) for a clip with no local proxy: a ranged read straight from the Drive by the key,
    through the team's one Drive door (gdrive-creator engine.media_request, as moments.py reads). None if not a Drive id."""
    if not LIB.DRIVE_ID.fullmatch(str(clip)):
        return None
    root = REPO / "components" / "gdrive-creator"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from gdrive_creator import engine as E
    url, head = E.media_request(clip)
    return ["-headers", head], url


def clips(brand: str) -> dict:
    out = {}
    for r in LIB.rows_of(brand):
        if r.get("kind") == "picture":
            continue
        px = proxy_of(brand, r)
        c = out.setdefault(r["clip"], {"clip": r["clip"], "proxy": px,
                                       "drive": px is None and bool(LIB.DRIVE_ID.fullmatch(str(r["clip"]))), "scenes": [],
                                       "named": bool(_person_creator(brand, r.get("creator")))})
        c["scenes"].append((r["scene"], r["in"], r["out"], r["shows"]))
    return out


def answered(brand: str) -> tuple[dict, float]:
    got, spent = {}, 0.0
    for line in LIB.check_lines(outdir(brand)):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        got[d["clip"]] = d
        spent += (d.get("usage") or {}).get("usd", 0)
    return got, spent


def clip_bytes(proxy: Path | None, clip: str = "") -> bytes:
    if proxy is None:                                  # no local copy: the first CAP_S seconds from the Drive, at 360p
        head, url = drive_input(clip)
        r = subprocess.run(["ffmpeg", "-v", "error", *head, "-t", str(CAP_S), "-i", url, "-an", "-vf", "scale=-2:360",
                            "-r", "2", "-c:v", "libx264", "-crf", "32", "-preset", "veryfast",
                            "-movflags", "frag_keyframe+empty_moov", "-f", "mp4", "pipe:1"],
                           capture_output=True, check=True, timeout=600)
        return r.stdout
    base = ["ffmpeg", "-v", "error", "-t", str(CAP_S), "-i", str(proxy), "-an"]
    tail = ["-movflags", "frag_keyframe+empty_moov", "-f", "mp4", "pipe:1"]
    r = subprocess.run(base + ["-c:v", "copy"] + tail, capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 1000:
        r = subprocess.run(base + ["-vf", "scale=-2:360", "-c:v", "libx264", "-crf", "32", "-preset", "veryfast"] + tail,
                           capture_output=True, check=True)
    return r.stdout


def prompt_for(c: dict, template: str, brand: str = "") -> str:
    scenes = "\n".join(f"{n}. {a:g}-{b:g} s: {v}" + ("  (after the first %d s, not sent)" % CAP_S if a >= CAP_S else "")
                       for n, a, b, v in sorted(c["scenes"]))
    looks = LIB.BRAND.get("looks") or {k: k for k in ((LIB.D.get("product") or {}).get("values") or {})}
    q = lambda xs: ", ".join(f'"{x}"' for x in xs)
    rooms, actions, emotions = words(brand)
    cfg = config(brand)
    comp = cfg.get("competitors") or []
    return (template.replace("{scenes}", scenes)
            .replace("{category}", cfg.get("category") or "product in the brand's category")
            .replace("{competitors}", ("Competitor brands we know of: " + ", ".join(comp) + ".") if comp else "")
            .replace("{products}", "\n".join(f"- {k}: {v}" for k, v in looks.items()))
            .replace("{actions}", q(actions)).replace("{rooms}", q(rooms)).replace("{emotions}", q(emotions)))


def one(c: dict, template: str, k: str, brand: str = "") -> dict:
    prompt = prompt_for(c, template, brand)
    blob = clip_bytes(c["proxy"], c["clip"])
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "video/mp4", "data": base64.b64encode(blob).decode()}, "video_metadata": {"fps": FPS}},
        {"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2,
                             "mediaResolution": "MEDIA_RESOLUTION_LOW",
                             "thinkingConfig": {"thinkingLevel": THINK}}}
    t0 = time.time()
    res = gb.req(f"{gb.BASE}/v1beta/models/{MODEL}:generateContent?key={k}", data=json.dumps(body).encode(),
                 headers={"Content-Type": "application/json"})
    text = res["candidates"][0]["content"]["parts"][0]["text"]
    ans = json.loads(text)
    if isinstance(ans, list):
        ans = ans[0]
    u = res.get("usageMetadata") or {}
    usage = {"prompt": u.get("promptTokenCount") or 0,
             "output": (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)}
    usage["usd"] = round((usage["prompt"] * PRICE[0] + usage["output"] * PRICE[1]) / 1e6, 6)
    return {"clip": c["clip"], "model": MODEL, "answer": ans, "usage": usage, "seconds": round(time.time() - t0, 1),
            "sent_bytes": len(blob), "sent_prompt": prompt}


def run(a) -> int:
    LIB.BRANDNAME[0] = a.brand
    LIB.use_brand(a.brand)
    out = outdir(a.brand)
    done, spent = answered(a.brand)
    pfile, template = latest_prompt()
    allc = clips(a.brand)
    todo = [c for c in allc.values() if c["clip"] not in done and (c["proxy"] or c["drive"])]
    todo.sort(key=lambda c: (not c["named"], c["proxy"] is None))   # named creators first, local copies before Drive reads
    no_media = sum(1 for c in allc.values() if not c["proxy"] and not c["drive"])
    from_drive = sum(1 for c in todo if not c["proxy"])
    if a.limit:
        todo = todo[: a.limit]
    per = EST_PER_CLIP
    hist = json.loads((out / "runs.json").read_text()) if (out / "runs.json").is_file() else []
    measured = [h for h in hist if h.get("ok")]
    if measured:
        per = sum(h["spent_usd_run"] for h in measured) / max(1, sum(h["ok"] for h in measured))
    if a.dry:
        print(json.dumps({"would_cast": len(todo), "read_from_drive": from_drive, "est_usd": round(len(todo) * per, 2), "per_clip": round(per, 5),
                          "already": len(done), "no_local_media": no_media, "spent_so_far": round(spent, 4)}))
        return 0
    k = os.environ.get(a.key_env, "").strip() if a.key_env else gb.key()
    if not k:
        sys.exit("no key in %s" % (a.key_env or "GEMINI_API_KEY"))
    lock = threading.Lock()
    st = {"spent": 0.0, "ok": 0, "failed": 0, "stopped": None, "errors": collections.Counter()}

    def work(c):
        with lock:
            if st["spent"] >= a.budget:
                st["stopped"] = "budget $%.2f reached" % a.budget
                return
        try:
            r = one(c, template, k, a.brand)
        except Exception as e:  # noqa: BLE001 — one clip never stops the rest
            msg = f"{type(e).__name__}: {str(e)[:200]}"
            with lock:
                st["failed"] += 1
                st["errors"][msg[:60]] += 1
                with (out / "failed.jsonl").open("a") as f:
                    f.write(json.dumps({"clip": c["clip"], "error": msg}) + "\n")
            return
        r["prompt_file"] = pfile.name
        with lock:
            st["spent"] += r["usage"]["usd"]; st["ok"] += 1
            line = json.dumps(r, ensure_ascii=False) + "\n"
            with LIB.check_append_file(out, len(line.encode())).open("a") as f:
                f.write(line)
            if st["ok"] % 50 == 0:
                print(f"  {st['ok']} done, ${st['spent']:.2f}", flush=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": MODEL, "prompt_file": pfile.name,
           "prompt_sha256": hashlib.sha256(template.encode()).hexdigest(), "asked": len(todo), "ok": st["ok"],
           "failed": st["failed"], "errors": dict(st["errors"]), "spent_usd_run": round(st["spent"], 4),
           "spent_usd_total": round(spent + st["spent"], 4), "wall_s": round(time.time() - t0),
           "stopped": st["stopped"], "price_per_1m": PRICE, "cap_seconds": CAP_S, "fps": FPS, "media_resolution": "low",
           "key": a.key_env or "GEMINI_API_KEY (shared loader)"}
    hist.append(rec)
    (out / "runs.json").write_text(json.dumps(hist, indent=1) + "\n")
    print(json.dumps(rec))
    return 0


def _person_creator(brand: str, creator: str) -> str | None:
    """The creator id when the row names a real person folder (no bucket path, no '?')."""
    c = str(creator or "")
    c = (config(brand).get("person_aliases") or {}).get(c, c)     # one person filed under two names
    if not c or c == "?" or "/" in c or c.startswith("ai-") or re.match(r"^\d+\.", c):
        return None
    return f"{brand}/{c}"


def fields_for(brand: str, row: dict, ans: dict) -> dict:
    persons = {str(p.get("p")): p for p in (ans.get("persons") or []) if isinstance(p, dict) and p.get("p")}
    main = next((k for k, p in persons.items() if p.get("main")), None)
    cid = _person_creator(brand, row.get("creator"))

    def pid(letter):
        if letter == main and cid:
            return cid
        return f"{brand}/clip/{row['clip']}#{letter}"
    sc = next((s for s in (ans.get("scenes") or []) if isinstance(s, dict) and s.get("n") == row["scene"]), None)
    if sc is None:
        return {"cast_checked": False, "cast_reason": "scene not answered (past the first %d s or skipped)" % CAP_S,
                "letterbox": bool(ans.get("letterbox")),
                "main_person": pid(main) if main else None}
    on = [str(x) for x in (sc.get("on_screen") or [])]
    hands = on == ["hands"]
    who = [x for x in on if x in persons]
    people = [{"person_id": pid(x), "gender": persons[x].get("gender"), "age": persons[x].get("age"),
               "skin_tone": persons[x].get("skin_tone"), "look": persons[x].get("look"), "main": x == main}
              for x in who]
    n = len(who)
    rooms, actions, emotions = words(brand)
    tags = [t for t in (sc.get("action_tags") or []) if t in actions]
    ours = (LIB.D.get("product") or {}).get("values") or {}
    prod = sc.get("product_in_use") if sc.get("product_in_use") in ours else "none"
    return {
        "people_count": "hands" if hands else (n if n < 3 else "3+"),
        "people": people,
        "person_ids": [p["person_id"] for p in people],
        "main_person": pid(main) if main else None,
        "woman_present": any(p["gender"] == "woman" for p in people),
        "couple": bool(sc.get("couple")),
        "face_visible": bool(sc.get("face_visible")),
        "action": sc.get("action") or "",
        "action_tags": tags,
        "product_in_use": prod,
        "competitor": sc.get("competitor") or None,
        "room": sc.get("room") if sc.get("room") in rooms else "unclear",
        "framing": sc.get("framing") or "unclear",
        "angle": sc.get("angle") or "unclear",
        "camera_move": sc.get("camera") or "unclear",
        "emotion": sc.get("emotion") if sc.get("emotion") in emotions else "unclear",
        "letterbox": bool(ans.get("letterbox")),
        "cast_checked": True,
        "cast_reason": None,
    }


def apply(a) -> int:
    LIB.BRANDNAME[0] = a.brand
    LIB.use_brand(a.brand)
    f = LIB.libdir(a.brand) / "library.json"
    rows = LIB.read_rows(f)
    got, _ = answered(a.brand)
    failed = set()
    ff = outdir(a.brand) / "failed.jsonl"
    if ff.is_file():
        for line in ff.read_text().splitlines():
            try:
                failed.add(json.loads(line)["clip"])
            except (ValueError, KeyError):
                pass
    n = collections.Counter()
    for r in rows:
        if r.get("kind") == "picture":
            r.update({"cast_checked": False, "cast_reason": "picture (proof row): people come from its tags"})
            n["picture"] += 1
            continue
        d = got.get(r["clip"])
        if d:
            r.update(fields_for(a.brand, r, d["answer"]))
            n["checked" if r["cast_checked"] else "unanswered-scene"] += 1
        else:
            why = ("model call failed; retried next pass" if r["clip"] in failed
                   else "no local copy and not a Drive file" if not proxy_of(a.brand, r)
                   and not LIB.DRIVE_ID.fullmatch(str(r["clip"]))
                   else "not yet cast; next pass")
            r.update({k: r.get(k) for k in FIELDS if k in r})
            r.update({"cast_checked": False, "cast_reason": why})
            n[why] += 1
    LIB.write_rows(f.parent, rows)
    print(json.dumps({"rows": len(rows), **n}))
    return 0


def _match(r: dict, rule: dict) -> bool:
    if rule.get("product_in_use") and r.get("product_in_use") in (None, "none"):
        return False
    if rule.get("couple") and not r.get("couple"):
        return False
    if rule.get("face_visible") and not r.get("face_visible"):
        return False
    if rule.get("framing") and r.get("framing") not in rule["framing"]:
        return False
    rooms, acts = rule.get("rooms"), rule.get("actions")
    if rooms or acts:
        hit = (rooms and r.get("room") in rooms) or (acts and set(acts) & set(r.get("action_tags") or []))
        if rule.get("couple") and acts and not rooms:     # couple + an action: both must hold
            hit = bool(set(acts) & set(r.get("action_tags") or []))
        return bool(hit)
    return True


def coverage(a) -> int:
    LIB.BRANDNAME[0] = a.brand
    LIB.use_brand(a.brand)
    f = LIB.libdir(a.brand) / "library.json"
    rows = [r for r in LIB.read_rows(f) if r.get("kind") != "picture" and r.get("cast_checked")]
    spec = json.loads((HERE / "story-beats.json").read_text())
    own = config(a.brand).get("story_beats") or {}
    spec["beats"].update(own)                          # the brand's own beats (its category's routine) join the shared ones
    out = {"brand": a.brand, "at": time.strftime("%Y-%m-%d"), "scenes_cast": len(rows), "beats": {}}
    for name, rule in spec["beats"].items():
        hit = [r for r in rows if _match(r, rule)]
        clean = [r for r in hit if r.get("text_marks") == ["clean"] and not r.get("letterbox")]
        people = {p for r in hit for p in (r.get("person_ids") or []) if "/clip/" not in p}
        tones = collections.Counter(p.get("skin_tone") for r in hit for p in (r.get("people") or []) if p.get("main"))
        genders = collections.Counter(p.get("gender") for r in hit for p in (r.get("people") or []))
        gap = len(clean) < spec["min_scenes"] or len(people) < spec["min_people"]
        out["beats"][name] = {
            "scenes": len(hit), "clean_scenes": len(clean), "clean_seconds": round(sum(r["seconds"] for r in clean), 1),
            "named_creators": len(people), "top_creators": collections.Counter(
                p for r in hit for p in (r.get("person_ids") or []) if "/clip/" not in p).most_common(5),
            "main_skin_tone": dict(tones), "genders_on_screen": dict(genders),
            "status": "gap: generate" if gap else "owned",
            "examples": [{"clip": r["clip"], "scene": r["scene"], "creator": r.get("creator"), "action": r.get("action"),
                          "frame": r.get("frame")} for r in sorted(clean or hit, key=lambda r: -r["seconds"])[:4]],
        }
    d = LIB.libdir(a.brand)
    (d / "coverage-story.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    lines = [f"# Story coverage from owned footage — {a.brand} ({out['at']})", "",
             f"{out['scenes_cast']} scenes cast. A beat is a gap under {spec['min_scenes']} clean scenes or "
             f"{spec['min_people']} named creators; gaps are what generation fills.", "",
             "| Beat | Status | Clean scenes | Clean s | Named creators | Top creators |", "|---|---|---|---|---|---|"]
    for name, b in sorted(out["beats"].items(), key=lambda kv: (kv[1]["status"] != "gap: generate", kv[0])):
        top = ", ".join("%s (%d)" % (p.split("/")[-1], c) for p, c in b["top_creators"])
        lines.append(f"| {name} | {b['status']} | {b['clean_scenes']} of {b['scenes']} | {b['clean_seconds']} | "
                     f"{b['named_creators']} | {top} |")
    (d / "coverage-story.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["run", "apply", "coverage"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--budget", type=float, default=2.0)
    ap.add_argument("--key-env", default="")
    a = ap.parse_args(argv)
    return {"run": run, "apply": apply, "coverage": coverage}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
