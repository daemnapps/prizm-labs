#!/usr/bin/env python3
"""Stage 8 — her brand-side profile, refreshed by the machine itself.

Damon's ruling (2026-08-30): a retained creator gets the same distillation as
an avatar, and the refresh is AUTOMATIC — when a teardown run of her own
content finishes, her profile is rebuilt from everything the machine now
holds on her. No manual step, no session remembering to do it.

The machine stays brand-agnostic (rule 4): it never knows where profiles
live or what shape they take. The BRAND says both, in
`brands/<brand>/content-creators/profile-home.json` (old: channels/creators/) — `spec` is the
document that defines a profile (its template is the output's shape), `home`
is the folder that holds one subfolder per creator. No file, no profiles:
the brand has not opted in, and stage 8 records itself skipped rather than
inventing a destination.

    python3 creator_profile.py <handle> --brand <brand>    refresh one by hand
    python3 creator_profile.py --all --brand <brand>       every creator with a run here
"""

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C
import brand_folders as BF

RECORDS = C.CM / "records"
CONFIG_NAME = "profile-home.json"

# A creator with many runs can outgrow a context window. Newest material
# first, each document clipped rather than dropped — a clipped teardown still
# carries its psychology read, which sits at the top.
CAP_FILE = 12000
CAP_ALL = 120000


def home(brand):
    """What the brand declared, or None. Malformed counts as absent — a half
    config must not send profiles somewhere half-named."""
    if not brand:
        return None
    f = BF.home(C.WS / "brands" / brand, "content-creators") / CONFIG_NAME
    if not f.is_file():
        return None
    try:
        cfg = json.loads(f.read_text())
    except Exception:
        return None
    return cfg if cfg.get("spec") and cfg.get("home") else None


def skip_reason(st):
    """Why stage 8 should not run for this run — or None, meaning run it."""
    if st.get("lane") != "creator" or not st.get("creator"):
        return "swipe research — there is no creator to profile"
    cfg = home(st.get("brand"))
    if cfg is None:
        return (f"brands/{st.get('brand')}/content-creators/{CONFIG_NAME} "
                "names no profile home — this brand keeps no distilled profiles")
    if not (C.WS / cfg["spec"]).is_file():
        return f"the profile spec is missing: {cfg['spec']}"
    return None


def _clip(text, cap=CAP_FILE):
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n\n[... cut for length — {len(text):,} chars on record]"


def creator_record(handle):
    """Everything the records plane holds on her: who she is, every post,
    her captions and the comments they drew."""
    d = RECORDS / "creators" / handle
    if not d.is_dir():
        return (f"(no record at records/creators/{handle} — the records "
                "adapter has not filed her yet)")
    parts = []
    for name in ("creator.md", "posts.md", "selected.md"):
        f = d / name
        if f.is_file():
            parts.append(f"### {name}\n\n{_clip(f.read_text())}")
    copy = d / "copy"
    if copy.is_dir():
        for f in sorted(copy.glob("*.md")):
            parts.append(f"### copy/{f.name}\n\n{_clip(f.read_text(), 6000)}")
    return "\n\n".join(parts) or "(her record folder is empty)"


def teardown_material(handle):
    """Her teardown runs on this machine, newest first: the stage-1 read of
    each video — the psychology and audience half is what the profile mines —
    and the brief the run became."""
    rows = []
    for rd in sorted(C.runs_root().iterdir(), reverse=True):
        rj = rd / "run.json"
        if not rj.is_file():
            continue
        try:
            st = json.loads(rj.read_text())
        except Exception:
            continue
        if (st.get("creator") or "") != handle:
            continue
        chunk = [f"## run {rd.name}"]
        rec = (st.get("stages") or {}).get("stage1") or {}
        if rec.get("out") and (rd / rec["out"]).is_file():
            chunk.append("### the teardown\n\n" + _clip((rd / rec["out"]).read_text()))
        if (rd / "brief-final.md").is_file():
            chunk.append("### the brief it became\n\n"
                         + _clip((rd / "brief-final.md").read_text(), 8000))
        if len(chunk) > 1:
            rows.append("\n\n".join(chunk))
    text = "\n\n---\n\n".join(rows)
    if not text:
        return "(no finished teardown runs for her on this machine yet)"
    if len(text) > CAP_ALL:
        text = text[:CAP_ALL] + "\n\n[... older runs cut for length]"
    return text


def dest_for(st):
    cfg = home(st.get("brand"))
    return C.WS / cfg["home"] / (st.get("creator") or "") / "profile.md"


def inputs(st):
    """The per-run values stage 8's prompt binds with `~name`. run.py calls
    this when the chain reaches the stage; anything wrong here fails the
    stage, which the plan loop treats as non-fatal — a brief must never be
    lost to a profile."""
    cfg = home(st.get("brand"))
    if cfg is None:
        raise RuntimeError("this brand names no profile home")
    handle = st.get("creator") or ""
    dest = dest_for(st)
    existing = (dest.read_text() if dest.is_file()
                else "(none yet — this is her first profile)")
    return {
        "profile_spec": (C.WS / cfg["spec"]).read_text(),
        "creator_record": creator_record(handle),
        "teardown_material": teardown_material(handle),
        "existing_profile": existing,
        "handle": handle,
    }


def publish(st, text):
    """The stage's output, landed where the brand said profiles live.
    Returns the workspace-relative path it wrote."""
    dest = dest_for(st)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text if text.endswith("\n") else text + "\n")
    return dest.relative_to(C.WS)


# ---------------------------------------------------------------- by hand

def refresh(handle, brand):
    """One creator, outside a run — backfill, or a re-run after a prompt or
    spec change. Same prompt, same inputs, same destination as stage 8."""
    import run as R
    st = {"creator": handle, "brand": brand, "lane": "creator"}
    why = skip_reason(st)
    if why:
        raise SystemExit(f"{handle}: {why}")
    path, ver, _ = C.newest("stage8")
    if not path:
        raise SystemExit("no stage-8 prompt found")
    import datetime
    vals = dict(inputs(st),
                brand_name=brand.replace("-", " ").title(),
                today=datetime.date.today().strftime("%A, %-d %B %Y"))
    filled = path.read_text()
    for var, text in vals.items():
        filled = filled.replace("{" + var + "}", text)
    out = C.MACHINE / ".tmp" / f"profile-{handle}.md"
    out.parent.mkdir(exist_ok=True)
    R.with_retry(lambda: R.claude(filled, out), f"profile {handle}")
    dest = publish(st, out.read_text())
    print(f"{handle}: profile refreshed ({path.name}) -> {dest}")


def main():
    ap = argparse.ArgumentParser(description="Refresh creator profiles by hand.")
    ap.add_argument("handle", nargs="*")
    ap.add_argument("--brand", required=True,
                    help="which brand's profile home to write to. Named every "
                         "time — a default would hand one brand's creators to "
                         "another (rule 4).")
    ap.add_argument("--all", action="store_true",
                    help="every creator that has a run on this machine")
    a = ap.parse_args()
    handles = list(a.handle)
    if a.all:
        seen = set()
        for rd in sorted(C.runs_root().iterdir()):
            rj = rd / "run.json"
            if rj.is_file():
                try:
                    h = json.loads(rj.read_text()).get("creator")
                except Exception:
                    h = None
                if h and h not in seen:
                    seen.add(h)
                    handles.append(h)
    if not handles:
        raise SystemExit("give me a handle, or --all")
    for h in handles:
        refresh(h, a.brand)


if __name__ == "__main__":
    main()
