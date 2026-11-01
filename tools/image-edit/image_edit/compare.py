"""The two-picture judge: the reference beside the result.

`tools/image-production`'s judge sees one picture and answers "is this a
good picture". An edit needs a second question that judge cannot ask: **did
only the named thing change?** So this one sends BOTH pictures to the same
vision model, with the change that was asked for, and the two standing tests
plus whatever the fix or variation adds.

The model door and the transport are `image_production.judge`'s — this file
adds the second image and nothing else. `caller(prompt, paths, entry) -> str`
is the seam; tests pass a stub.
"""
import base64
import json
import mimetypes
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


def google_caller(prompt, paths, entry, transport=None, key=None):
    """Both pictures inline, then the prompt — the judge's own door, twice the
    pictures. Imported lazily so this module loads without the sibling."""
    ip = P.image_production()
    providers, R = ip.providers, ip.route
    transport = transport or providers.http_transport
    k = key if key is not None else R.key_value(entry.get("key"))
    if not k:
        raise SystemExit(f"no {entry.get('key')} on this machine — the compare judge "
                         f"cannot run, so nothing is delivered.")
    parts = []
    for p in paths:
        p = Path(p)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text": prompt})
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"temperature": entry.get("temperature", 0.2)}}
    url = entry["endpoint"].replace("{model}", entry["vendor_model"]) + f"?key={k}"
    status, _h, raw = transport("POST", url, {"Content-Type": "application/json"},
                                json.dumps(payload).encode())
    data = json.loads(raw.decode())
    if status is not None and status >= 400:
        raise RuntimeError(f"compare judge error {status}: {json.dumps(data)[:300]}")
    return "".join(x.get("text", "") for x in data["candidates"][0]["content"]["parts"])


def compare(reference, result, change, extra_tests=(), entry=None, caller=None, folder=None):
    """(verdict, fails, tests, raw). The judge not running is a FAIL, never a
    pass — the same rule the one-picture judge holds."""
    tests = list(STANDING) + list(extra_tests)
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tests))
    prompt = body(latest(folder)).replace("{change}", change).replace("{tests}", numbered)
    caller = caller or google_caller
    if entry is None:
        entry = P.image_production().route.judge_entry()
    try:
        raw = caller(prompt, [str(reference), str(result)], entry)
    except (Exception, SystemExit) as e:         # noqa: BLE001 — a missing key exits
        return "reject", [f"compare judge did not run: {type(e).__name__}: {str(e)[:200]}"], tests, ""
    try:
        data = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception:                            # noqa: BLE001
        return "reject", ["compare judge returned unreadable output"], tests, raw
    # Exactly one PASS/FAIL per test asked. An answer to part of the test is
    # not a pass: "no FAIL seen" on {} or one of N is how a skip got through.
    got, bad = [], 0
    for res in (data.get("results") if isinstance(data, dict) else None) or []:
        try:
            v, n = str(res.get("verdict", "")).upper(), int(res.get("test"))
        except (AttributeError, TypeError, ValueError):
            bad += 1
            continue
        if v in ("PASS", "FAIL"):
            got.append(n)
        else:
            bad += 1
    want = list(range(1, len(tests) + 1))
    if bad or sorted(got) != want:
        missing = [n for n in want if n not in got]
        extra = sorted({n for n in got if n not in want or got.count(n) > 1})
        return "reject", [f"judge answer incomplete: {len(got)} PASS/FAIL for {len(tests)} tests"
                          + (f"; missing {', '.join(map(str, missing))}" if missing else "")
                          + (f"; extra or repeated {', '.join(map(str, extra))}" if extra else "")
                          + (f"; {bad} not a PASS/FAIL on a numbered test" if bad else "")], tests, raw
    fails = []
    for res in data.get("results", []):
        if str(res.get("verdict", "")).upper() != "PASS":
            i = int(res.get("test", 0)) - 1
            t = tests[i] if 0 <= i < len(tests) else f"test {res.get('test')}"
            fails.append(f"{t.split(' — ')[0]} — {res.get('evidence', '')}")
    return ("reject" if fails else "pass"), fails, tests, raw
