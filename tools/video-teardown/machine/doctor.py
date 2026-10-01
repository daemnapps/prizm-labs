#!/usr/bin/env python3
"""Is this machine ready to run, right now?

    python3 doctor.py

Every check here exists because something silently failed once. A run that
cannot finish should say so in a second, not eleven Opus stages later.
"""
import json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OK, WARN, BAD = "OK  ", "WARN", "MISS"
rows = []


def check(label, fn, why=""):
    try:
        state, detail = fn()
    except Exception as e:
        state, detail = BAD, str(e)[:90]
    rows.append((state, label, detail, why))


def main():
    import keys

    check("claude CLI (the thinking stages)",
          lambda: (OK, shutil.which("claude") or "") if shutil.which("claude")
          else (BAD, "not on PATH"),
          "install it and sign in — nobody can do this for you")

    check("ffmpeg (stills, and the movement check)",
          lambda: (OK, "") if shutil.which("ffmpeg") else (BAD, "not on PATH"),
          "brew install ffmpeg")

    for name, why in (("GEMINI_API_KEY", "the video-reading stages"),
                      ("APIFY_TOKEN", "pulling a creator's posts"),
                      ("GDRIVE_SA_KEY", "making the Google Doc"),
                      ("FAL_KEY", "some image work")):
        check(f"{name} ({why})",
              lambda n=name: (OK, "") if keys.get(n, required=False) else (BAD, "not in ~/.daemn/keys.env"),
              "add it to ~/.daemn/keys.env")

    check("APIFY_TOKEN_PERSONAL (spare account)",
          lambda: (OK, "") if keys.get("APIFY_TOKEN_PERSONAL", required=False)
          else (WARN, "no spare — a spent allowance will stop a pull"),
          "optional, but the main key does run out")

    def drive():
        import chain as C
        try:
            r = C.drive_root()
        except Exception as e:
            return BAD, str(e)[:80]
        return (OK, str(r)[-46:]) if r and r.exists() else (BAD, "not mounted")
    check("Shared Assets mounted", drive,
          "sign in to Google Drive for Desktop")

    def lib():
        import library as L
        r = L.root() / "creators"
        n = len([d for d in r.iterdir() if d.is_dir()]) if r.exists() else 0
        return (OK, f"{n} creators") if n else (WARN, "no creators pulled yet")
    check("creator library", lib)

    def sa():
        import drive as D
        D.service().files().get(fileId="root", fields="id").execute()
        return OK, "service account authenticates"
    check("Drive service account", sa, "GDRIVE_SA_KEY may be wrong")

    def prompts():
        """Ask chain.py where the prompts are rather than guessing the layout.
        A first version of this check globbed `stage1*` against folders named
        `stage-1-teardown` and reported three missing prompts on a machine that
        was running fine — a readiness check that cries wolf is worse than
        none."""
        import chain as C
        dirs = [d for d in C.PROMPT_DIRS] if hasattr(C, "PROMPT_DIRS") else []
        if not dirs:
            root = HERE.parent / "prompts"
            dirs = [d for d in root.iterdir() if d.is_dir()] if root.exists() else []
        # Some stages branch by lane (stage-5-brief has creator-lane,
        # hook-asset and so on), so the prompt sits one level down. Search the
        # whole subtree and skip archive/, which is retired versions.
        def live(d):
            return [f for f in d.rglob("*.md") if "archive" not in f.parts]
        empty = [d.name for d in dirs if d.is_dir() and not live(d)]
        n = sum(len(live(d)) for d in dirs if d.is_dir())
        return (OK, f"{len(dirs)} stage folders, {n} prompts") if not empty \
            else (BAD, "no prompt in " + ", ".join(empty[:3]))
    check("every stage has a prompt", prompts)

    print()
    for state, label, detail, why in rows:
        line = f"  {state}  {label}"
        if detail:
            line += f"  — {detail}"
        print(line)
        if state != OK and why:
            print(f"        {why}")
    bad = [r for r in rows if r[0] == BAD]
    print()
    print("  ready" if not bad else f"  {len(bad)} thing(s) would stop a run")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
