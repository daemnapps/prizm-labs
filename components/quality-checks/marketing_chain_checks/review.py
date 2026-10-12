"""THE CREATIVE REVIEW — the reviewer half of the QC loop, for every tool and
every stage (the owner, 2026-10-02: "i want this kind of creative QC process
installed for each of my production tools … not just the production folder but
this should exist for all stages in the creation process").

The loop, the same everywhere:
  1. machine checks  — the tool's own gates (hold(), check.json, qc.py …)
  2. the review      — a model reads the stage's OUTPUT against what it must
                       agree with (its SOURCE: the swipe, the brief, the
                       elements, the stage before, the brand's banks) and the
                       stage's HARD BARS, and returns findings per item
  3. the log         — every round filed in the repo beside the run
                       (qc_log.py: <run>/qc-log/QC-LOG.md + raw findings)
  4. the fix         — at the stage that caused it; a cause that would recur
                       becomes a chain change, written back into the log row
  5. re-make         — only what failed, then QC again

What each stage is compared against and its hard bars live in
`definitions/stages.json` — one entry per tool + stage. Nothing here names a
brand. The reviewer prompt: `prompts/creative-review-v1-damon.md`.

    from marketing_chain_checks import review
    review.after_stage("copywriter", "stage6-hooks", run_dir,
                       output="…/stage6--x.md", sources=["…/stage1--x.md", …])

`after_stage` never crashes the caller: a review that cannot run (no key, no
network) is filed as UNCHECKED and says so. It returns the findings; with
`hold=True` a BLOCKER raises marketing_chain_checks.Held. Off: QC_REVIEW=0.
"""
from __future__ import annotations

import base64, json, mimetypes, os, re, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
PROMPT = COMP / "prompts" / "creative-review-v1-damon.md"
STAGES = COMP / "definitions" / "stages.json"
MODEL = os.environ.get("QC_REVIEW_MODEL", "gemini-3.1-pro-preview")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
IMG = {".png", ".jpg", ".jpeg", ".webp"}
MAX_TEXT = 60000


def definitions() -> dict:
    return json.loads(STAGES.read_text()) if STAGES.exists() else {}


def stage_def(tool: str, stage: str) -> dict:
    t = (definitions().get("tools") or {}).get(tool) or {}
    st = t.get("stages") or {}
    if stage in st:
        return st[stage]
    for k, v in st.items():               # a stage key may be a prefix ("stage4" covers "stage4b")
        if stage.startswith(k):
            return v
    return t.get("default") or {}



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def _key() -> str | None:
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        return _shared_keys().lookup("GEMINI_API_KEY")
    except Exception:
        return None


def _part(p) -> dict:
    p = Path(p)
    if p.suffix.lower() in IMG:
        mime = mimetypes.guess_type(str(p))[0] or "image/png"
        data = p.read_bytes()
        if len(data) > 600_000:
            try:
                from PIL import Image
                import io
                im = Image.open(p).convert("RGB"); im.thumbnail((1280, 1280))
                b = io.BytesIO(); im.save(b, "JPEG", quality=85); data, mime = b.getvalue(), "image/jpeg"
            except Exception:
                pass
        return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
    t = p.read_text(errors="replace")
    return {"text": f"--- {p.name} ---\n{t[:MAX_TEXT]}"}


def _labelled(label: str, things) -> list[dict]:
    out = [{"text": f"\n=== {label} ===\n"}]
    for x in things or []:
        if isinstance(x, (str, Path)) and Path(x).exists():
            out.append(_part(x))
        elif x:
            out.append({"text": str(x)[:MAX_TEXT]})
    return out


def ask(parts: list[dict], caller=None) -> dict:
    if caller:
        return caller(parts)
    k = _key()
    if not k:
        raise RuntimeError("no GEMINI_API_KEY")
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{BASE}/{MODEL}:generateContent?key={k}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    t = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    return json.loads(re.search(r"\{.*\}", t, re.S).group(0))


def review(tool: str, stage: str, items: list[dict], sources=None, caller=None) -> dict:
    """items: [{id, output: [paths|text], compare: [paths|text]}] — per-item sources
    sit beside the shared `sources`. Returns {id: {ok, severity, problems, fix_at,
    prompt_change}} — the same shape the picture reviewer files."""
    d = stage_def(tool, stage)
    head = PROMPT.read_text() if PROMPT.exists() else ""
    head = (head.replace("{tool}", tool).replace("{stage}", stage)
                .replace("{what}", d.get("what", "the stage's output"))
                .replace("{compare_against}", d.get("compare_against", "its sources"))
                .replace("{bars}", "\n".join(f"- {b}" for b in d.get("hard_bars") or ["it does what its sources say, and nothing they contradict"]))
                .replace("{fix_at}", d.get("fix_at", stage)))
    parts = [{"text": head}] + _labelled("SOURCES (what every item must agree with)", sources)
    for it in items:
        parts += _labelled(f"ITEM {it['id']} — its sources", it.get("compare"))
        parts += _labelled(f"ITEM {it['id']} — the output to review", it.get("output"))
    # THE INVENTORY (the owner, 2026-10-02: "a full inventory list every single time
    # we make an image"): a stage with a checklist answers every line, every item
    cl = d.get("checklist") or []
    if cl:
        parts.append({"text": "\nFor EVERY item also return \"checklist\": {" + ", ".join(
            f'\"{c["key"]}\": {{\"mark\": \"✓|~|✗|n/a\", \"note\": \"one short line\"}}' for c in cl)
            + "} — answering each line:\n" + "\n".join(f"- {c['key']}: {c['ask']}" for c in cl)
            + "\nAny ✗ makes the item not ok."})
    parts.append({"text": "\nReturn the JSON now, one entry per ITEM id: " + ", ".join(i["id"] for i in items)})
    return ask(parts, caller=caller)


def after_stage(tool: str, stage: str, run_dir, output=None, sources=None, items=None,
                hold: bool = False, caller=None) -> dict:
    """Review one finished stage and file the round. Never crashes the caller."""
    if os.environ.get("QC_REVIEW", "1") == "0":
        return {}
    import sys as _sys
    if caller is None and "unittest" in _sys.modules:   # a tool's own tests never spend on a review
        return {}
    from . import qc_log
    run_dir = Path(run_dir)
    items = items or [{"id": stage, "output": [output] if output else []}]
    try:
        # a big batch is reviewed three items at a time (one call stays small)
        findings = {}
        for i in range(0, len(items), 3):
            findings.update(review(tool, stage, items[i:i + 3], sources, caller=caller))
        by = f"reviewer ({MODEL})"
    except Exception as e:  # filed, never swallowed silently
        findings = {i["id"]: {"ok": None, "severity": "UNCHECKED",
                              "problems": [f"the review could not run: {type(e).__name__}: {str(e)[:160]}"]} for i in items}
        by = "reviewer (did not run)"
    try:
        qc_log.add(run_dir, f"{tool} · {stage}", by, findings,
                   method="creative review: output against " + (stage_def(tool, stage).get("compare_against") or "its sources"))
    except Exception:
        pass
    if hold:
        bad = [f"{k}: {'; '.join(v.get('problems') or [])}" for k, v in findings.items()
               if isinstance(v, dict) and v.get("severity") == "BLOCKER"]
        if bad:
            from . import Held
            raise Held("media" if any(Path(str(o)).suffix.lower() in IMG for i in items for o in i.get("output") or []) else "copy", bad)
    return findings
