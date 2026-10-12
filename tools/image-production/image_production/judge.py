"""The judge — one picture, checked before anyone sees it.

Lifted from `tools/image-production/static/tools/finish.py`: `STANDING_CHECKS`
(verbatim, minus the two that only exist for a paid static ad's offer bar),
`measured()` (counted off the pixels, runs first, short-circuits the model
call), `seen()` (the tests put to a vision model with the picture in front of
it) and the judge prompt. The product tests are `brand_facts.py`'s, read from
`brands/<brand>/ai-elements/element-facts.json`.

Why it exists at all: the alternative is his eyes on every frame, which is the
thing that eats the day. The machine kills what fails a checkable test and he
only ever looks at survivors. **Every kill is logged with its reason, because a
reject is a PROMPT defect — you fix the prompt, not the picture.**

`caller(prompt, image_path, entry) -> str` is the seam. Tests pass a stub;
nothing here opens a socket by itself.
"""
import base64
import json
import mimetypes
import re
from pathlib import Path

from . import prompting, route as R

# Four things, and only four. Narrowed 2026-09-05 on the owner's call: the job is
# replicated structure, brand injected correctly, consistent imagery — not a
# forensic QA pass. Finger-counting and micro-geometry killed good pictures and
# cost more time than the defects they caught.
STANDING_CHECKS = [
    "No third-party or competitor brand name, logo or wordmark is legible "
    "anywhere in the frame.",
    "Nothing is grossly broken — a limb attached wrongly, a face melted, a body "
    "with the wrong number of arms. Judge this the way a viewer scrolling past "
    "would. A partly hidden hand, a foreshortened grip, an odd-looking finger "
    "or a stylised illustration all PASS.",
]

# Only when the purpose allows words in the frame. Verbatim from finish.py.
READABLE = (
    "The text is READABLE. FAIL only for words that are garbled, corrupted, "
    "malformed or running into themselves (RPMPM, SAALE) — the kind of thing a "
    "reader would notice instantly. Normal repetition of a word across the copy "
    "is FINE. Small imperfections in a distressed or hand-drawn style are FINE.")

# The mirror of the "no invented text" standing rule, for every purpose whose
# frame carries no words.
NO_WORDS = (
    "There are NO words, letters, numbers, captions, labels, watermarks or "
    "user-interface elements rendered anywhere in the frame. FAIL if any legible "
    "text appears. Words that are part of a real object in the world — a sign on "
    "a wall behind the subject, a book's spine — PASS.")


# THE 4:5 ZONE, as a gate. the owner, 2026-09-22: assets are generated at 9:16
# only; faces and words must sit inside a centred 4:5 window of that frame.
# SAFE-ZONE.md (09-04) measured the clause alone failing — so the zone is
# asked of the judge, and a picture that breaks it is HELD. On a 9:16 frame
# the window is the middle 70%: the top 15% and bottom 15% are bleed.
SAFE_ZONE = (
    "SAFE ZONE — every headline, word, badge, price bar, logo, every face and "
    "the product sit entirely inside the centred 4:5 window of this 9:16 frame: "
    "the middle 70% of its height. The top 15% and the bottom 15% hold "
    "background only. FAIL if any of those touches or crosses into the top or "
    "bottom 15%.")


def direction_check(direction):
    """DIRECTION MATCH — the picture must show what the words asked for.

    finish.py's `headline_check`, generalised off the headline and onto the
    caller's direction, which every purpose has. Added 2026-09-09 on the owner's
    call: the gate read the type and the product and never asked the obvious
    question. A picture that argues something its own brief does not is slop,
    however clean it renders."""
    d = " ".join(str(direction or "").split())
    if not d:
        return []
    return [f'The picture was asked for like this: "{d}". The picture must SHOW '
            f'what that asks for — the subject, the moment or the thing the words '
            f'name, visible in frame. FAIL if the words and the picture are arguing '
            f'different things, or if what was asked for is not visible at all. Say '
            f'what you see.']


def tests_for(req, ctx):
    """Every test one picture is judged against, in order."""
    purpose = ctx["purpose"]
    tests = list(STANDING_CHECKS)
    if purpose.get("words") == "never":
        tests.append(NO_WORDS)
    else:
        tests.append(READABLE)
    if ctx["product"].get("key"):
        tests += ctx["product"]["judge_tests"]
    tests += list(purpose.get("judge") or [])
    tests += direction_check(req.get("direction"))
    if purpose.get("safe_zone") and req.get("_aspect") == "9:16" and not req.get("_finish"):
        tests.append(SAFE_ZONE)            # a native 9:16 leaving unfinished is judged on the zone
    tests += list(req.get("checks") or [])
    return tests


def measured(img_path, aspect, aspects=None):
    """Counted off the pixels. No model, no argument. Runs first, so a wrong
    frame never costs a judge call. Silent when the imaging library is not on
    this machine — a measurement we cannot take is not a failure."""
    aspects = aspects or R.aspects()
    want = aspects.get(aspect)
    if not want:
        return []
    try:
        from PIL import Image
    except ImportError:
        return []
    try:
        with Image.open(img_path) as im:
            w, h = im.size
    except Exception as e:                       # noqa: BLE001 — an unreadable file IS a failure
        return [f"the picture could not be read: {type(e).__name__}: {e}"]
    target = want["h"] / want["w"]
    got = h / w
    if abs(got - target) > 0.02:
        return [f"frame is {w}x{h} ({got:.3f}), the request asked for {aspect} ({target:.3f})"]
    return []


def google_caller(prompt, img_path, entry, transport=None, key=None):
    """The default eyes: one prompt and one picture to a vision model.

    Lifted from `tools/image-production/static/tools/gemini_image.py` — images
    inline (base64) rather than through a Files API, and a short timeout,
    because one judge call answers in seconds or it is stuck."""
    from . import providers
    transport = transport or providers.http_transport
    k = key if key is not None else R.key_value(entry.get("key"))
    if not k:
        raise SystemExit(f"no {entry.get('key')} on this machine — the judge cannot run, "
                         f"so nothing is delivered. Read from the environment, else the "
                         f"macOS Keychain (service daemn-{entry.get('key')}, account damon).")
    p = Path(img_path)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    payload = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime,
                         "data": base64.b64encode(p.read_bytes()).decode()}},
        {"text": prompt}]}],
        "generationConfig": {"temperature": entry.get("temperature", 0.2)}}
    url = entry["endpoint"].replace("{model}", entry["vendor_model"]) + f"?key={k}"
    status, _h, body = transport("POST", url, {"Content-Type": "application/json"},
                                 json.dumps(payload).encode())
    data = json.loads(body.decode())
    if status is not None and status >= 400:
        raise RuntimeError(f"judge error {status}: {json.dumps(data)[:300]}")
    return "".join(p.get("text", "")
                   for p in (data["candidates"][0]["content"]["parts"]))


def seen(img_path, tests, entry, caller=None, folder=None):
    """The tests put to a vision model with the picture in front of it.
    Returns (fails, raw) so a kill can quote its evidence.

    **The judge failing is not the picture passing.** A judge that did not run
    holds the picture (finish.py, verbatim reasoning). **A test the judge was
    asked and did not answer is not a pass either** — a `{}` reply or one
    result for two tests used to come back with no fails (SI-147 (image
    engine honest))."""
    caller = caller or google_caller
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tests))
    prompt = prompting.body(prompting.latest("judge", folder)).replace("{tests}", numbered)
    try:
        raw = caller(prompt, str(img_path), entry)
    except (Exception, SystemExit) as e:         # noqa: BLE001 — a missing key exits; that is a hold too
        return [f"judge did not run: {type(e).__name__}: {str(e)[:200]}"], ""
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        data = json.loads(raw[start:end])
    except Exception:                            # noqa: BLE001
        return ["judge returned unreadable output"], raw
    fails = []
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        fails.append("judge returned no list of results")
        results = []
    answered = set()
    for res in results:
        if not isinstance(res, dict):
            continue
        try:
            i = int(res.get("test", 0)) - 1
        except (TypeError, ValueError):
            i = -1
        if 0 <= i < len(tests):
            answered.add(i)
        if str(res.get("verdict", "")).upper() != "PASS":
            t = tests[i] if 0 <= i < len(tests) else f"test {res.get('test')}"
            fails.append(f"{t.split('.')[0]} — {res.get('evidence', '')}")
    # Only the indices the prompt numbered: a vendor that batches still has to
    # answer every one of them, and the reject says which it skipped.
    for i in range(len(tests)):
        if i not in answered:
            fails.append(f"judge answered {len(answered)} of {len(tests)} tests — "
                         f"test {i + 1} was asked and not answered: {tests[i].split('.')[0]}")
    return fails, raw


def verdict(img_path, req, ctx, entry=None, caller=None, folder=None, aspects=None):
    """One picture's verdict. Measured failures short-circuit the model call —
    a wrong frame is not worth a judge's time or its money."""
    entry = entry or R.judge_entry()
    tests = tests_for(req, ctx)
    fails = measured(img_path, req.get("_gen_aspect") or req["_aspect"], aspects)
    raw = ""
    if not fails:
        fails, raw = seen(img_path, tests, entry, caller, folder)
    return {"file": str(img_path),
            "verdict": "reject" if fails else "pass",
            "fails": fails,
            "checks_run": tests,
            "judge_model": entry.get("vendor_model", "unknown"),
            "coverage": "measured + seen",
            "raw": raw}


def why_md(name, fails, raw=""):
    """The reject note. A kill is a work item, not a verdict: fix the prompt,
    never the picture (PIPELINE.md §4b)."""
    out = [f"# {name} — rejected", ""]
    out += [f"- {f}" for f in fails]
    out += ["", "Every one of these is a prompt to fix, not a picture to patch.", ""]
    if raw:
        out += ["<details><summary>judge, raw</summary>", "", "```", raw.strip(), "```",
                "</details>", ""]
    return "\n".join(out)


_SAFE = re.compile(r"[^a-z0-9._-]+")


def slug(text):
    return _SAFE.sub("-", str(text).lower()).strip("-") or "picture"
