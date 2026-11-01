#!/usr/bin/env python3
"""vision_judge.py — ONE door every picture check asks through (2026-10-09).

The Gemini prepaid credit ran out mid-run (HTTP 402) and every zone, face and
review check came back UNCHECKED, holding every picture. the owner: "can we use a
different model … there should be something … local … so not using credit to
run this type of stuff, this is basically editing, not generation."

So a picture check no longer names a vendor. It calls

    ask(prompt, images, want_json=False) -> Answer      (a str)
    ask_parts(parts, want_json=False)    -> Answer      (Gemini-style parts, as review.py builds them)

and the door tries the judges in the order providers.json "vision_judge"
declares (env VISION_JUDGE_ORDER=local,claude overrides it for one run):

  claude  — the `claude` CLI on the owner's plan, headless, Read-only, the
            images handed over as files (the teardown chain's own pattern:
            video-teardown/machine/run.py `claude()` + `_clean_env()`).
  local   — a vision model on this Mac, free (local-studio jobs/vision_ask.py
            in its own .venv-vlm, MLX).
  gemini  — the old paid call, last; a 402/quota falls through, never crashes.

A judge that errors, times out or answers unreadably (want_json and no JSON
object in it) falls through to the next. The Answer carries who answered:
`.backend`, `.model`, `.seconds`, `.tried` — verdict files say "checked by
claude (sonnet)". Every judge failing raises VisionJudgeError, which each
caller already turns into UNCHECKED.

    python3 machine/vision_judge.py "<prompt>" pic.png [pic2.png] [--json] [--order local]
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
PROVIDERS = HERE / "providers.json"
IMG = {".png", ".jpg", ".jpeg", ".webp"}
MAX_SIDE = 1568                      # what a vision model reads anyway; smaller is faster


def _vp_keys():
    """The shared key reader (vp_keys -> components/keys/loader.py), loaded by path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("vm_vp_keys", HERE / "vp_keys.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class VisionJudgeError(RuntimeError):
    pass


class Answer(str):
    """The judge's text, carrying who answered it."""
    backend: str = ""
    model: str = ""
    seconds: float = 0.0
    tried: list = []

    def by(self) -> str:
        return f"{self.backend} ({self.model})" if self.model else self.backend


# ---------------------------------------------------------------- config

def config() -> dict:
    try:
        return json.loads(PROVIDERS.read_text()).get("vision_judge") or {}
    except Exception:                                   # noqa: BLE001
        return {}


def order(cfg: dict | None = None) -> list[str]:
    env = os.environ.get("VISION_JUDGE_ORDER", "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    return list((cfg if cfg is not None else config()).get("order") or ["claude", "local", "gemini"])


# --------------------------------------------------------------- helpers

def json_of(text: str):
    """The first {...} object in a judge's answer, or None."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:                                   # noqa: BLE001
        return None


def _small(src, dst_dir: Path, n: int) -> Path:
    """A copy of one picture, longest side MAX_SIDE, in the judge's own folder."""
    src = Path(src)
    dst = dst_dir / f"image{n}{src.suffix.lower() if src.suffix.lower() in IMG else '.png'}"
    try:
        from PIL import Image
        with Image.open(src) as im:
            if max(im.size) > MAX_SIDE:
                im = im.convert("RGB"); im.thumbnail((MAX_SIDE, MAX_SIDE))
                dst = dst.with_suffix(".jpg"); im.save(dst, "JPEG", quality=90)
                return dst
    except Exception:                                   # noqa: BLE001
        pass
    shutil.copyfile(src, dst)
    return dst


def _clean_env() -> dict:
    """The CLI's own login, never the calling session's — the teardown chain's
    pattern (video-teardown/machine/run.py `_clean_env`, 2026-09-03 / 10-07):
    a plain Terminal-like environment, plus the long-life chain token or the
    company API key from the Keychain when there is one."""
    keep = ("HOME", "PATH", "TERM", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    def key(name):
        return _vp_keys().key(name)
    tok = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN_CHAIN") or key("CLAUDE_CODE_OAUTH_TOKEN")
    if tok and tok.startswith("sk-ant-"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = tok
    api = os.environ.get("ANTHROPIC_API_KEY_CHAIN") or key("ANTHROPIC_API_KEY")
    if api and api.startswith("sk-ant-api"):
        env["ANTHROPIC_API_KEY"] = api
        env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    return env


# --------------------------------------------------------------- backends
# each: (prompt, images, want_json, cfg) -> (text, model)

def claude_backend(prompt, images, want_json, cfg):
    if not shutil.which("claude"):
        raise VisionJudgeError("the claude CLI is not on this Mac")
    model = cfg.get("cli_model") or "sonnet"
    tmp = Path(tempfile.mkdtemp(prefix="vision-judge-"))
    try:
        files = [_small(p, tmp, i + 1) for i, p in enumerate(images)]
        head = ""
        if files:
            head = ("Before answering, open and look at every image below with the Read tool, in order. "
                    "They are the pictures the question refers to (Image 1 is the first listed, and so on).\n"
                    + "\n".join(f"Image {i + 1}: {f}" for i, f in enumerate(files)) + "\n\n")
        tail = ("\n\nReply with the JSON object only — no preamble, no code fence, nothing after it."
                if want_json else "")
        args = ["--model", model, "--allowed-tools", "Read", "--output-format", "json"]
        limit = int(cfg.get("timeout_s") or 300)
        if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN_CHAIN") or os.environ.get("ANTHROPIC_API_KEY_CHAIN"):
            # the mini routed this run to its requester: exactly that credential, never another account's
            kit = str(WS / "components" / "run-kit")
            if kit not in sys.path:
                sys.path.append(kit)
            from run_kit.claude_flags import effort_args   # LD-73 (explicit effort)
            r = subprocess.run(["claude", "-p", *args, *effort_args()], input=head + prompt + tail, capture_output=True,
                               text=True, cwd=str(tmp), env=_clean_env(), timeout=limit)
        else:
            # NO ACCOUNT IS WIRED IN (the owner, 2026-10-23): run_kit's claude_door picks the
            # credential — company key, long-life token, then this machine's login.
            kit = str(WS / "components" / "run-kit")
            if kit not in sys.path:
                sys.path.append(kit)
            from run_kit import claude_door
            r = claude_door.run(args, head + prompt + tail, timeout=limit, cwd=str(tmp))
        try:
            data = json.loads(r.stdout or "{}")
        except Exception:                               # noqa: BLE001
            data = {}
        text = data.get("result") or ""
        if r.returncode or data.get("is_error") or not text.strip():
            raise VisionJudgeError(f"claude failed: {(text or r.stderr or r.stdout or '')[-300:]}")
        return text, model
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def local_backend(prompt, images, want_json, cfg):
    venv = WS / (cfg.get("venv") or "components/local-studio/.venv-vlm")
    py = venv / "bin" / "python"
    job = WS / (cfg.get("job") or "components/local-studio/jobs/vision_ask.py")
    model = (cfg.get("models") or {}).get(cfg.get("role") or "check") or cfg.get("model")
    if not (py.exists() and job.exists() and model):
        raise VisionJudgeError("the local vision model is not set up on this Mac")
    tmp = Path(tempfile.mkdtemp(prefix="vision-judge-"))
    try:
        files = [_small(p, tmp, i + 1) for i, p in enumerate(images)]
        (tmp / "prompt.md").write_text(prompt + ("\n\nAnswer with the JSON object only." if want_json else ""))
        env = dict(os.environ)
        env["HF_HOME"] = str(WS / "components" / "local-studio" / "models" / "hf")   # local-studio's weights folder
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        r = subprocess.run([str(py), str(job), "--model", model, "--prompt-file", str(tmp / "prompt.md"),
                            "--max-tokens", str(cfg.get("max_tokens") or 1200), *map(str, files)],
                           capture_output=True, text=True, env=env, timeout=int(cfg.get("timeout_s") or 600))
        line = (r.stdout or "").strip().splitlines()[-1:] or [""]
        try:
            out = json.loads(line[0])
        except Exception:                               # noqa: BLE001
            out = {}
        if r.returncode or not (out.get("answer") or "").strip():
            raise VisionJudgeError(f"local model failed: {(r.stderr or r.stdout or '')[-300:]}")
        return out["answer"], model.split("/")[-1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _gemini_key():
    k = (_vp_keys().key("GEMINI_API_KEY") or "").strip()
    return k or None


def _inline(p) -> dict:
    p = Path(p)
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}


def gemini_backend(prompt, images, want_json, cfg, parts=None):
    k = _gemini_key()
    if not k:
        raise VisionJudgeError("no GEMINI_API_KEY")
    model = cfg.get("model")
    if not model:
        raise VisionJudgeError("providers.json vision_judge.gemini names no model")
    if str(model).startswith("house:"):
        # the Model House names the judge (components/generative-model-house behind.judge, P26)
        import importlib.util as _u
        _sp = _u.spec_from_file_location("vm_vj_house", Path(__file__).resolve().parent / "house.py")
        _h = _u.module_from_spec(_sp); _sp.loader.exec_module(_h)
        model = str(_h.model(str(model).split(":", 1)[1]))
    tmp = Path(tempfile.mkdtemp(prefix="vision-judge-"))
    try:
        if parts is None:
            parts = [{"text": prompt}] + [_inline(_small(p, tmp, i + 1)) for i, p in enumerate(images)]
        gc = {"temperature": 0}
        if want_json:
            gc["responseMimeType"] = "application/json"
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}",
            data=json.dumps({"contents": [{"parts": parts}], "generationConfig": gc}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=int(cfg.get("timeout_s") or 300)) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:                 # 402 / 429: out of credit — fall through
            raise VisionJudgeError(f"gemini HTTP {e.code}") from None
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        return text, model
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


BACKENDS = {"claude": claude_backend, "local": local_backend, "gemini": gemini_backend}


# ------------------------------------------------------------------ door

def _try(names, call, want_json, backends, cfg, role="check") -> Answer:
    backends = backends or BACKENDS
    tried = []
    for name in names:
        fn = backends.get(name)
        if fn is None:
            tried.append({"backend": name, "error": "no such judge"}); continue
        t = time.time()
        try:
            text, model = call(name, fn, {**(cfg.get(name) or {}), "role": role})
        except Exception as e:                          # noqa: BLE001 — every failure falls through
            tried.append({"backend": name, "error": f"{type(e).__name__}: {str(e)[:200]}",
                          "seconds": round(time.time() - t, 1)})
            continue
        if not (text or "").strip() or (want_json and json_of(text) is None):
            tried.append({"backend": name, "error": "unreadable answer", "raw": (text or "")[:200],
                          "seconds": round(time.time() - t, 1)})
            continue
        a = Answer(text)
        a.backend, a.model, a.seconds = name, model or "", round(time.time() - t, 1)
        a.tried = tried + [{"backend": name, "ok": True, "seconds": a.seconds}]
        return a
    raise VisionJudgeError("no judge answered: " + "; ".join(f"{x['backend']}: {x.get('error')}" for x in tried))


def ask(prompt: str, images=(), want_json: bool = False, backends: dict | None = None,
        order_: list | None = None, role: str = "check") -> Answer:
    """One question about zero or more pictures; the first judge that answers wins.
    role: "check" (a yes/no or a box — the fast local model) or "review" (the
    creative review — the bigger one); providers.json vision_judge.local.models."""
    cfg = config()
    images = [str(p) for p in images or []]
    return _try(order_ or order(cfg), lambda n, fn, c: fn(prompt, images, want_json, c),
                want_json, backends, cfg, role)


def ask_parts(parts: list[dict], want_json: bool = False, backends: dict | None = None,
              order_: list | None = None, role: str = "check") -> Answer:
    """Gemini-style parts ({"text"} / {"inline_data"}) — the shape review.py builds.
    For claude and local the pictures become files and the text keeps its order,
    each picture standing in it as [Image N]; gemini gets the parts unchanged."""
    cfg = config()
    tmp = Path(tempfile.mkdtemp(prefix="vision-parts-"))
    try:
        text, images = [], []
        for p in parts or []:
            if "text" in p:
                text.append(p["text"])
            elif "inline_data" in p:
                d = p["inline_data"]
                ext = mimetypes.guess_extension(d.get("mime_type") or "image/png") or ".png"
                f = tmp / f"part{len(images) + 1}{'.jpg' if ext == '.jpe' else ext}"
                f.write_bytes(base64.b64decode(d.get("data") or ""))
                images.append(str(f))
                text.append(f"[Image {len(images)}]")
        prompt = "\n".join(text)

        def call(name, fn, c):
            if fn is gemini_backend:
                return fn(prompt, images, want_json, c, parts=parts)
            return fn(prompt, images, want_json, c)
        return _try(order_ or order(cfg), call, want_json, backends, cfg, role)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt"); ap.add_argument("images", nargs="*")
    ap.add_argument("--json", action="store_true"); ap.add_argument("--order")
    ap.add_argument("--role", default="check")
    a = ap.parse_args(argv)
    ans = ask(a.prompt, a.images, want_json=a.json, order_=a.order.split(",") if a.order else None, role=a.role)
    print(json.dumps({"by": ans.by(), "seconds": ans.seconds, "tried": ans.tried, "answer": str(ans)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
