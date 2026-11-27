#!/usr/bin/env python3
"""The Footage Library board: a page on this machine for sifting a brand's footage and picking shots for an edit.

    python3 components/asset-index/library/board/serve.py [--port 8915] [--pull]     # http://localhost:8915

Reads the built library live (runs/asset-index/<brand>/library/library.json, the output of library.py build),
so a rebuild shows on the next reload; nothing is generated or published. Every brand with a built library gets
its own board at /<brand>/, never mixed. Each scene's picture is its own frame: the frame cache, else cut free
from the record's local proxy (library.scene_frame), else the record's saved still; on a machine without the
footage the page falls back to the file's Drive thumbnail, which shows when the viewer is signed in to Drive.
Picks live in the viewer's browser until they are put into a brief: "Put in brief" writes them beside that brief
(runs/video-writing/<brand>/<brief>/deliverable/picks.json, via the video chain's footage.write_picks), where a pick
for a scene makes that scene a cut from the picked clip. The copied shot list is the other way out.

The brand's page words (name, colours, what each beat holds) come from runs/asset-index/<brand>/library/board.json;
without it the page uses the brand folder's name and the shared beat names. No brand is named in this file.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
_sp = importlib.util.spec_from_file_location("asset_library", HERE.parent / "library.py")
L = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(L)

PORT = 8915
LOCK = threading.Lock()
CACHE: dict = {}          # brand -> (library mtime, data rows, rows by id)
PULL = {"on": False, "at": 0.0}   # --pull: keep a checkout nobody edits current with origin/main (fast-forward only)


def keep_current():
    """With --pull, at most every 30 minutes and only on a fast-forward: fetch the newest library from origin."""
    if not PULL["on"] or time.time() - PULL["at"] < 1800:
        return
    PULL["at"] = time.time()
    threading.Thread(target=lambda: subprocess.run(["git", "-C", str(HERE), "pull", "-q", "--ff-only", "origin", "main"],
                                                   capture_output=True), daemon=True).start()

BEAT_ORDER = ["mechanism", "routine", "product", "problem", "failed-solutions", "transformation", "proof",
              "identification", "presence", "presenter", "other"]
BEAT_SHARED = {"mechanism": "Mechanism · product working", "routine": "Routine · the steps", "product": "Product · in hand, box",
               "problem": "Problem · what it fixes", "failed-solutions": "Failed solutions · the old way",
               "transformation": "Transformation · the after", "proof": "Proof · before/after, reactions",
               "identification": "Their world · daily life", "presence": "Presence · on screen, no product",
               "presenter": "Talking to camera", "other": "Unsorted"}
DEFAULT_LIGHT = ("--bg:#f4f5f1; --panel:#ffffff; --fg:#141713; --mute:#5f655d; --line:#dcdfd7;"
                 " --accent:#1f3a2a; --accent-ink:#ffffff; --gold:#9a7a2f; --chip:#eceee8;")
DEFAULT_DARK = ("--bg:#0f120f; --panel:#181c18; --fg:#eef0ea; --mute:#a0a79c; --line:#2c322b;"
                " --accent:#3f8a5f; --accent-ink:#ffffff; --gold:#d2ab57; --chip:#232823;")

EN_WORDS = {"the", "and", "you", "it", "is", "this", "that", "my", "your", "to", "of", "so", "we", "i", "a", "in", "for",
            "with", "skin", "have", "just", "can", "are", "what", "but", "not", "on", "be", "do", "was", "like", "really"}
try:
    DICT = {w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8", errors="ignore")} | EN_WORDS
except OSError:
    DICT = set(EN_WORDS)


def language(said: str) -> str:
    """What a scene's spoken lines are in, read from the words kept: Thai or Chinese script, English, other or unclear, or no speech."""
    t = (said or "").strip()
    if not t:
        return "no speech"
    if re.search(r"[฀-๿]", t):
        return "Thai"
    if re.search(r"[一-鿿]", t):
        return "Chinese"
    words = [w.split("'")[0] for w in re.findall(r"[a-z']+", t.lower()) if w.split("'")[0]]
    if not words:
        return "no speech"
    common = sum(w in EN_WORDS for w in words)
    share = sum(any(x in DICT for x in (w, w.rstrip("s"), w.rstrip("ed"), w.rstrip("d"))) for w in words) / len(words)
    return "English" if share >= 0.9 or (share >= 0.7 and common) else "other or unclear"


def brands() -> list:
    return sorted(d.name for d in L.RUNS.iterdir() if (d / "library" / "library.json").is_file()) if L.RUNS.is_dir() else []


def board_words(brand: str) -> dict:
    try:
        cfg = json.loads((L.libdir(brand) / "board.json").read_text())
    except (OSError, ValueError):
        cfg = {}
    try:
        bv = json.loads((L.libdir(brand) / "brand-vocabulary.json").read_text())
    except (OSError, ValueError):
        bv = {}
    name = cfg.get("name") or brand.title()
    prods = {}
    for pid in bv.get("products") or {}:
        look = str((bv.get("looks") or {}).get(pid) or "")
        prods[pid] = (look.split(":", 1)[0].strip() if ":" in look else
                      "Set / box" if pid == "set-or-box" else f"Other {name}" if pid.startswith("other-") else pid.replace("-", " ").title())
    prods["none"] = "No product"
    beats = {b: (cfg.get("beats") or {}).get(b) or BEAT_SHARED[b] for b in BEAT_ORDER}
    return {"name": name, "light": cfg.get("light") or DEFAULT_LIGHT, "dark": cfg.get("dark") or DEFAULT_DARK,
            "beats": beats, "products": prods, "named": (bv.get("named_folders") or cfg.get("named_folders") or {}).get("values") or {}}


def rows(brand: str):
    """The board's rows for a brand, rebuilt whenever library.json changes."""
    f = L.libdir(brand) / "library.json"
    mt = f.stat().st_mtime
    with LOCK:
        hit = CACHE.get(brand)
        if hit and hit[0] == mt:
            return hit[1], hit[2]
        src = L.read_rows(f)
        L.BRANDNAME[0] = brand
        words = board_words(brand)
        prefix = f"Shared Assets/brands/{brand}/"
        tier_rank = {"A": 0, "B": 1, "P": 2}
        src.sort(key=lambda r: (r.get("kind") == "picture", tier_rank.get(r.get("tier"), 3),
                                BEAT_ORDER.index(r["beat"]) if r.get("beat") in BEAT_ORDER else 99, str(r["clip"]), r.get("scene", 0)))
        data, by = [], {}
        for r in src:
            pic = r.get("kind") == "picture"
            rid = f"{r['clip']}:{r.get('scene', 0)}"
            path = (r.get("label") or r.get("rel") or "").replace(prefix, "")
            who, source = r.get("creator"), r.get("source")
            for folder, person in words["named"].items():
                if path.startswith(folder + "/"):
                    rest = path[len(folder) + 1:]
                    who = f"{person['who']} · {rest.split('/')[0]}" if "/" in rest else person["who"]
                    source = person.get("role") or source
            gid = r["clip"] if re.fullmatch(r"[0-9A-Za-z_-]{25,44}", str(r["clip"])) else None
            data.append({
                "id": rid, "gid": gid, "beat": r.get("beat"), "prod": r.get("products") or [],
                "tier": "photo" if pic else r.get("tier"), "pol": r.get("polish"), "marks": r.get("text_marks") or ["clean"],
                "size": r.get("text_size"), "hand": r.get("handles") or [], "words": r.get("on_screen_text"),
                "g": r.get("creator_gender"), "e": r.get("creator_ethnicity"), "a": r.get("creator_age"),
                "og": r.get("on_screen_gender"), "oa": r.get("on_screen_age"), "set": r.get("setting"), "src": source, "who": who,
                "in": r["cut_in"] if r.get("cut_in") is not None else r.get("in"),
                "out": r["cut_out"] if r.get("cut_out") is not None else r.get("out"),
                "cut": r.get("cut_source"), "shows": (r.get("shows") or "")[:220], "says": (r.get("says") or "")[:220],
                "file": r.get("file"), "path": path, "lang": language(r.get("says") or ""),
                "drive": r.get("drive_url") or (f"https://drive.google.com/file/d/{gid}/view" if gid else None),
                "prob": r.get("problem"), "stage": r.get("stage"), "ad": r.get("used_in"),
            })
            by[rid] = r
        CACHE[brand] = (mt, data, by)
        return data, by


def frame(brand: str, rid: str) -> Path | None:
    _, by = rows(brand)
    r = by.get(rid)
    if not r:
        return None
    if r.get("kind") == "picture":
        f = L.FRAMES / f"proof_{r['clip']}.jpg"
        return f if f.is_file() else None
    L.BRANDNAME[0] = brand
    got = L.scene_frame(r)
    return Path(got) if got and Path(got).is_file() else None


def page(brand: str) -> str:
    w = board_words(brand)
    lab = {"name": w["name"], "brand": brand, "beats": w["beats"], "products": w["products"],
           "brands": [[b, board_words(b)["name"]] for b in brands()]}
    return ((HERE / "page.html").read_text().replace("__TITLE__", f"{w['name']} Footage Library")
            .replace("/*LIGHT*/", w["light"]).replace("/*DARK*/", w["dark"])
            .replace("/*BRAND*/", json.dumps(lab, ensure_ascii=False)))


def home() -> str:
    links = "".join(f'<li><a href="/{b}/">{board_words(b)["name"]} Footage Library</a></li>' for b in brands())
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Footage Library</title><style>body{font:16px system-ui;margin:24px 16px;background:#f4f5f1;color:#141713}"
            "@media (prefers-color-scheme:dark){body{background:#0f120f;color:#eef0ea}a{color:#7fc79a}}li{margin:10px 0}</style>"
            f"<h1>Footage Library</h1><ul>{links or '<li>No brand has a built library on this machine.</li>'}</ul>")


# ------------------------------------------------------------ picks into a brief
# The board sends picks to one brief: runs/video-writing/<brand>/<brief>/deliverable/picks.json, written by the
# video chain's own footage step (footage.write_picks), which also refreshes that brief's footage ledger.

def _footage():
    sp = importlib.util.spec_from_file_location("vp_footage", L.REPO / "components" / "video-production" / "machine" / "footage.py")
    m = importlib.util.module_from_spec(sp)
    sys.path.insert(0, str(L.REPO / "components" / "video-production" / "machine"))
    sp.loader.exec_module(m)
    return m


def briefs(brand: str) -> list:
    """Every brief of a brand with a deliverable: its folder, title, B-roll scenes and picks so far, newest first."""
    base = L.REPO / "runs" / "video-writing" / brand
    out = []
    for f in base.glob("*/deliverable/5-brief.md") if base.is_dir() else []:
        d = f.parent
        title = next((ln.lstrip("# ").strip() for ln in f.read_text(errors="ignore").splitlines() if ln.startswith("# ")), d.parent.name)
        scenes = []
        try:
            led = json.loads((d / "footage.json").read_text())
            scenes = [{"id": r["scene"], "shows": (r.get("shows") or "")[:90]} for r in led.get("scenes") or [] if r.get("role") == "broll"]
        except (OSError, ValueError, KeyError):
            pass
        try:
            n = len(json.loads((d / "picks.json").read_text()).get("picks") or [])
        except (OSError, ValueError):
            n = 0
        out.append({"brief": d.parent.name, "title": title[:120], "scenes": scenes, "picks": n, "t": f.stat().st_mtime})
    return [{k: v for k, v in b.items() if k != "t"} for b in sorted(out, key=lambda b: -b["t"])]


def put_in_brief(brand: str, brief: str, sent: list) -> dict:
    d = L.REPO / "runs" / "video-writing" / brand / brief / "deliverable"
    if not re.fullmatch(r"[0-9A-Za-z._-]+", brief) or not (d / "5-brief.md").is_file():
        raise ValueError("no such brief")
    data, by = rows(brand)
    shown = {r["id"]: r for r in data}
    picks = []
    for x in sent:
        r, v = by.get(x.get("id")), shown.get(x.get("id"))
        if not r:
            continue
        picks.append({"id": v["id"], "clip_id": r["clip"], "library_scene": r.get("scene"),
                      "for_scene": x.get("for_scene") or None, "in": v["in"], "out": v["out"], "cut_source": v["cut"],
                      "shared_path": r.get("label") or r.get("rel"), "drive": v["drive"], "beat": v["beat"],
                      "products": v["prod"], "tier": v["tier"], "text_marks": v["marks"], "shows": v["shows"]})
    if not picks:
        raise ValueError("none of those picks are in this library")
    doc = _footage().write_picks(d, brand, brief, picks)
    shared = False
    if PULL["on"]:
        files = [str(d / n) for n in ("picks.json", "footage.json", "footage.md") if (d / n).is_file()]
        git = ["git", "-C", str(HERE)]
        subprocess.run(git + ["add", "--sparse", *files], capture_output=True)
        c = subprocess.run(git + ["commit", "-q", "-m", f"footage picks: {brand} {brief}, {len(picks)} from the Footage Library board"],
                           capture_output=True)
        if c.returncode == 0:
            for _ in range(3):
                if subprocess.run(git + ["pull", "-q", "--rebase", "origin", "main"], capture_output=True).returncode == 0 and \
                   subprocess.run(git + ["push", "-q", "origin", "HEAD:main"], capture_output=True).returncode == 0:
                    shared = True
                    break
                time.sleep(3)
    return {"ok": True, "brief": brief, "sent": len(picks), "in_brief": len(doc["picks"]), "shared": shared}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code: int, body: bytes, ctype: str, cache: str = "no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
        if len(parts) <= 1:
            keep_current()
        known = brands()
        try:
            if not parts:
                if len(known) == 1:
                    self.send_response(302); self.send_header("Location", f"/{known[0]}/"); self.end_headers(); return
                return self.send(200, home().encode(), "text/html; charset=utf-8")
            brand = parts[0]
            if brand not in known:
                return self.send(404, b"no such library", "text/plain")
            if len(parts) == 1:
                if not self.path.split("?")[0].endswith("/"):
                    self.send_response(301); self.send_header("Location", f"/{brand}/"); self.end_headers(); return
                return self.send(200, page(brand).encode(), "text/html; charset=utf-8")
            if parts[1] == "data.json":
                data, _ = rows(brand)
                return self.send(200, json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(), "application/json")
            if parts[1] == "briefs":
                return self.send(200, json.dumps(briefs(brand), ensure_ascii=False).encode(), "application/json")
            if parts[1] == "frame" and len(parts) == 3:
                f = frame(brand, parts[2].removesuffix(".jpg"))
                if not f:
                    return self.send(404, b"", "image/jpeg")
                return self.send(200, f.read_bytes(), "image/jpeg", "max-age=86400")
            return self.send(404, b"not found", "text/plain")
        except (BrokenPipeError, ConnectionResetError):
            return


    def do_POST(self):
        parts = [unquote(p) for p in urlparse(self.path).path.split("/") if p]
        try:
            if len(parts) != 2 or parts[1] != "picks" or parts[0] not in brands():
                return self.send(404, b"not found", "text/plain")
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            res = put_in_brief(parts[0], str(body.get("brief") or ""), body.get("picks") or [])
            return self.send(200, json.dumps(res).encode(), "application/json")
        except ValueError as e:
            return self.send(400, json.dumps({"ok": False, "error": str(e)}).encode(), "application/json")
        except (BrokenPipeError, ConnectionResetError):
            return


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--pull", action="store_true", help="only for a checkout nobody edits: fast-forward it from origin every "
                    "30 min, and commit and push the picks it puts into a brief")
    a = ap.parse_args(argv)
    PULL["on"] = a.pull
    print(f"Footage Library board on http://localhost:{a.port}  ({', '.join(brands()) or 'no built library'})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
