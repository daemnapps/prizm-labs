"""The two-picture judge: the reference beside the result.

image-production's judge sees one picture and answers "is this a good
picture". An edit needs a second question that judge cannot ask: **did only
the named thing change?** So this one puts BOTH pictures in front of a vision
model, with the change that was asked for, the two standing tests, and
whatever the fix or variation adds.

Two ways it runs, one prompt and one reader for both:

- **Gemini**, the same model and the same key image-production's judge uses
  (`tools/image-production/tools/gemini_image.py`) — when the key is here.
- **The session**: the prompt is written, filled in, into the edit's
  `job.json`; the agent that made the picture can answer it and hand the reply
  back with the result. Same tests, same JSON, same reader.

`caller(prompt, paths, entry) -> str` is the seam; tests pass a stub.
"""
import base64
import json
import mimetypes
import urllib.request
from pathlib import Path

from . import paths as P

STANDING = [
    "CHANGE PRESENT — the change that was asked for is visibly there in IMAGE 2.",
    "NOTHING ELSE MOVED — apart from that change, IMAGE 2 is the same picture as "
    "IMAGE 1: the same people with the same faces, the same layout, the same type "
    "in the same places, the same colours, the same product. IMAGE 2 may be a "
    "taller frame than IMAGE 1 — scene continuing above and below what IMAGE 1 "
    "shows is expected and is NOT a change; judge the part IMAGE 1 shows. FAIL "
    "if anything inside that part is different.",
]

ENTRY = {"model": "gemini-3.1-pro-preview",        # image-production's judge default
         "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
         "temperature": 0.2}


def latest(folder=None):
    folder = Path(folder or P.home() / "prompts")
    best, best_v = None, -1
    for f in folder.glob("compare-judge-v*-damon.md"):
        try:
            v = int(f.name.split("-v")[1].split("-")[0])
        except ValueError:
            continue
        if v > best_v:
            best, best_v = f, v
    if best is None:
        raise SystemExit(f"no compare-judge prompt under {folder}")
    return best


def body(path):
    text = Path(path).read_text()
    return text.split("\n", 1)[1].lstrip() if text.startswith("#") else text


def tests_for(extra_tests=()):
    return list(STANDING) + list(extra_tests)


def prompt_for(change, extra_tests=(), folder=None):
    """The judge's prompt exactly as it is sent — written into job.json too."""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tests_for(extra_tests)))
    return body(latest(folder)).replace("{change}", change).replace("{tests}", numbered)


def gemini_caller(prompt, paths, entry, transport=None):
    """Both pictures inline, labelled, then the prompt. The key is read by
    image-production's own reader; with no key this raises, and the caller
    turns that into a HOLD."""
    try:
        key = P.gemini().key()
    except SystemExit as e:                      # its reader stops when no key is set
        raise RuntimeError(f"no judge key on this machine ({e})") from None
    parts = []
    for i, p in enumerate(paths, 1):
        p = Path(p)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append({"text": f"IMAGE {i}"})
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text": prompt})
    payload = json.dumps({"contents": [{"parts": parts}],
                          "generationConfig": {"temperature": entry.get("temperature", 0.2)}}).encode()
    url = entry["endpoint"].replace("{model}", entry["model"]) + f"?key={key}"
    if transport:
        raw = transport(url, payload)
    else:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    return "".join(x.get("text", "") for x in data["candidates"][0]["content"]["parts"])


def read(raw, tests):
    """(verdict, fails) from the judge's JSON reply."""
    data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    fails = []
    for res in data.get("results", []):
        if str(res.get("verdict", "")).upper() != "PASS":
            i = int(res.get("test", 0)) - 1
            t = tests[i] if 0 <= i < len(tests) else f"test {res.get('test')}"
            fails.append(f"{t.split(' — ')[0]} — {res.get('evidence', '')}")
    return ("reject" if fails else "pass"), fails


def compare(reference, result, change, extra_tests=(), entry=None, caller=None, folder=None):
    """(verdict, fails, tests, raw). The judge not running is a FAIL, never a
    pass — the same rule the one-picture judge holds."""
    tests = tests_for(extra_tests)
    prompt = prompt_for(change, extra_tests, folder)
    caller = caller or gemini_caller
    try:
        raw = caller(prompt, [str(reference), str(result)], entry or ENTRY)
    except Exception as e:                       # noqa: BLE001
        return "reject", [f"compare judge did not run: {type(e).__name__}: {str(e)[:200]}"], tests, ""
    try:
        verdict, fails = read(raw, tests)
    except Exception:                            # noqa: BLE001
        return "reject", ["compare judge returned unreadable output"], tests, raw
    return verdict, fails, tests, raw
