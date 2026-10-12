#!/usr/bin/env python3
"""Let a SESSION run a chain stage when the machine's CLI account is capped.

    python3 _agent_stage.py prep <label> <product> <video> <stage-id>
    python3 _agent_stage.py done <label> <stage-id>

`prep` fills the stage's prompt exactly as a run would (the model call then
fails, harmlessly) and prints where the filled prompt and the expected output
live. A session reads the prompt, writes the document, then calls `done`.

the owner, 2026-09-30: "we should be able to pick up work from any account."
The chain shells out to `claude -p`, which authenticates as the machine's own
login; when that login is the one that is capped, every writing stage dies even
though a working session is right there. This is the seam that lets the session
do the stage itself. Temporary — the real fix is the CLI's login.
"""
import json, os, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C

def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def plan_for(label):
    slug = slugify(label)
    d = C.runs_root() / slug
    st = json.loads((d / "run.json").read_text())
    plan = C.stages(st["brand"], "", st.get("production_route") or "creator",
                    st.get("triage_lane") or "")
    return d, st, plan

def find(plan, sid):
    for s in plan:
        if s["id"] == sid: return s
    raise SystemExit(f"no stage {sid} in this run's plan")

def approvals():
    """the owner's numbers, and only his. This seam used to hand run.py
    `--approve-structure all` on every call — passing the structure lock, the
    swipe match, the manifest, the hook format and the audit all at once,
    without him ever seeing a number (found 2026-10-01). His ruling on the
    lock is explicit: "literally this cannot happen again UNLESS I DISCRETELY
    SAY SO." So nothing is approved unless he has said so, through the same
    variable run.py itself reads.
    """
    v = os.environ.get("DAEMN_STRUCTURE_APPROVALS", "").strip()
    return ["--approve-structure", v] if v else []


def main():
    if len(sys.argv) < 3: raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "prep":
        _, label, product, video, sid = sys.argv[1:6]
        d, st, plan = plan_for(label)
        s = find(plan, sid)
        out = f"stages/{s['id']}-{slugify(s['name'])}.md"
        subprocess.run([sys.executable, "run.py", video, "--brand", st["brand"],
                        "--product", product, "--route", "creator", "--label", label,
                        "--no-frames", "--only", sid, "--redo", *approvals()],
                       cwd=str(HERE), capture_output=True, timeout=1800)
        sent = d / "prompts" / Path(out).name
        print(f"PROMPT {sent}")
        print(f"OUTPUT {d / out}")
        print(f"READY  {sent.is_file()}")
    elif cmd == "next":
        # What is left, in order, and which of it needs a session. The
        # model-free stages are run here and now, so an agent never has to
        # know that 5u and 7 sit between the brief and the page (that gap
        # stalled two runs on 2026-09-30).
        _, label, product, video = sys.argv[1:5]
        d, st, plan = plan_for(label)
        # Frames were retired 2026-09-30 (gate 9: "no more frames"), so stage 6
        # never runs and never records — leaving it in `todo` made this loop
        # re-run a no-op and print CONTINUE forever instead of ALL-DONE.
        todo = [x for x in plan
                if (st["stages"].get(x["key"]) or {}).get("status") not in ("done", "skipped")
                and x["engine"] != "frames"]
        for x in todo:
            if x["engine"] in ("claude",):
                print(f"NEEDS-SESSION {x['id']}")
                return
            subprocess.run([sys.executable, "run.py", video, "--brand", st["brand"],
                            "--product", product, "--route", "creator", "--label", label,
                            "--no-frames", "--only", x["id"], *approvals()],
                           cwd=str(HERE), capture_output=True, timeout=1800)
            d, st, plan = plan_for(label)
            print(f"RAN-FREE {x['id']}")
        print("ALL-DONE" if not todo else "CONTINUE")
    elif cmd == "done":
        _, label, sid = sys.argv[1:4]
        d, st, plan = plan_for(label)
        s = find(plan, sid)
        out = f"stages/{s['id']}-{slugify(s['name'])}.md"
        f = d / out
        if not f.is_file() or len(f.read_text().strip()) < 200:
            raise SystemExit(f"NOT DONE — {f} missing or too short")
        # THE SCRIPT (the owner, 2026-09-18: "we still want the script"). run.py
        # appends it after stage 7b from stage 7's output; this seam bypasses
        # that handler, so two briefs came out without the one thing he ruled
        # had to stay (2026-09-30). Same lift, same marker, same source.
        if s["key"] == "stage7b":
            import run as R
            # The script is lifted from the finished spec. Stage 7 USED to be
            # that spec; with frames retired (gate 9) it is a vestigial pass
            # and on 2026-10-01 it returned only the manifest tail, so the
            # page came out with no script at all. Take stage 7 when it still
            # looks like a shot list, else take stage 5, which always is one.
            spec = ""
            for key in ("stage7", "stage5"):
                rec = st["stages"].get(key) or {}
                f2 = (d / rec["out"]) if rec.get("out") else None
                if f2 and f2.exists():
                    t = f2.read_text()
                    if "### The frames" in t:
                        spec = t
                        break
            block = R.script_block(spec)
            body = f.read_text()
            if block and "## The script, straight through" not in body:
                marker = "## How it might look"
                body = (body.replace(marker, block + "\n" + marker, 1) if marker in body
                        else body.rstrip() + "\n\n" + block)
                f.write_text(body)
                print(f"  script appended · {len(block):,} chars")
        st["stages"][s["key"]] = dict(status="done", name=s["name"], version=s["version"],
            engine="session", prompt_name=Path(s["prompt"]).name, out=out,
            sent="prompts/" + Path(out).name, chars_out=len(f.read_text()),
            finished=__import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        (d / "run.json").write_text(json.dumps(st, indent=2))
        print(f"DONE {s['id']} · {len(f.read_text()):,} chars")
        # THE AUDIT HOLD (gate 1, 2026-09-30: a verdict other than SHIP holds
        # the chain). It lives in run.py's stage-4e handler, which this seam
        # also bypasses — so a RE-RUN verdict sailed straight on to the spice
        # pass and the brief (2026-10-01). Reported, never auto-approved.
        if s["key"] == "stage4e":
            body = f.read_text()
            fails = []
            for line in body.splitlines():
                c = [x.strip().strip("*").strip() for x in line.strip().strip("|").split("|")]
                if len(c) >= 3 and c[0].isdigit() and c[2].upper().startswith("FAIL"):
                    fails.append(f"A{c[0]} {c[1][:60]}")
            m = re.search(r"VERDICT\W*\s*(SHIP|RE-RUN|STOP)", body, re.I)
            v = m.group(1).upper() if m else "?"
            if v != "SHIP" or fails:
                (d / "AUDIT-HOLD.md").write_text(
                    f"# The audit returned {v}\n\nNothing after it should run until the failed "
                    "check is fixed and the audit re-run, or the owner passes it by number "
                    "(`--approve-structure A5`).\n\n" + "\n".join(f"- {x}" for x in fails))
                print(f"  AUDIT: {v}" + (f" · {len(fails)} FAIL(s): {'; '.join(fails)[:160]}" if fails else "")
                      + " — HELD (AUDIT-HOLD.md). the owner rules by number.")
            else:
                print("  audit: SHIP")
        # THE TWO STAGE-5 GATES (video-teardown CLAUDE.md, gates 4 and 5).
        # They live inside run.py's own stage-5 handler, which this seam
        # bypasses — so briefs written through it reached stage 7 with no
        # swipe-match stamp and no manifest, and production refuses those.
        # Three separate agents reported it before it was fixed (2026-10-01).
        if s["key"] == "stage5":
            import importlib.util as _u
            try:
                _sp = _u.spec_from_file_location("swipe_match", HERE / "swipe_match.py")
                _sm = _u.module_from_spec(_sp); _sp.loader.exec_module(_sm)
                passed, open_ = _sm.check(d, Path(out).name)
                st = json.loads((d / "run.json").read_text())
                st["stages"][s["key"]]["status"] = "done" if passed else "held"
                st["swipe_match"] = "passed" if passed else {"open": open_}
                (d / "run.json").write_text(json.dumps(st, indent=2))
                print("  swipe match: PASSED" if passed
                      else f"  swipe match: HELD on {len(open_)} change(s) — SWIPE-MATCH.md")
            except Exception as e:
                print(f"  swipe match could not run: {type(e).__name__}: {str(e)[:120]}")
            try:
                _mp = _u.spec_from_file_location("manifest", HERE / "manifest.py")
                _mf = _u.module_from_spec(_mp); _mp.loader.exec_module(_mf)
                _mf.check(d, Path(out).name)
                rec = json.loads((d / "manifest.json").read_text())
                # Gate 5 holds on a MISSING CORE element or an unsourced price;
                # elements still to make are a fresh brief's normal state and do
                # not hold. This seam printed the miss and left the stage `done`,
                # so a brief with four of the swipe's core elements dropped
                # finished anyway and production would have refused it
                # (2026-10-02). run.py's own split, replicated.
                core = rec.get("core_missing") or []
                if core:
                    st2 = json.loads((d / "run.json").read_text())
                    st2["stages"][s["key"]]["status"] = "held"
                    st2["manifest"] = {"missing": core}
                    (d / "run.json").write_text(json.dumps(st2, indent=2))
                    print(f"  manifest: MISSING — {', '.join(core)} — HELD. "
                          "the owner rules these by number; production refuses the brief until COMPLETE.")
                elif rec.get("to_make"):
                    print("  manifest: core elements all carried; to make before "
                          f"production: {', '.join(rec['to_make'])[:160]}")
                else:
                    print("  manifest: COMPLETE")
            except Exception as e:
                print(f"  manifest could not run: {type(e).__name__}: {str(e)[:120]}")
            # THE VIEWER CHECK (2026-10-02) — run.py's own last stage-5 gate,
            # replicated here so a brief written in-session meets it too. On a
            # fail the session re-writes the step it names, using the viewers'
            # words in <run>/viewer-check/r<N>/VERDICT.md, then runs `done` again.
            st3 = json.loads((d / "run.json").read_text())
            if st3["stages"][s["key"]].get("status") == "done":
                import run as R
                try:
                    R.viewer_gate(d, st3, s["key"], d / out)
                    print("  viewer check: PASSED")
                except RuntimeError as e:
                    rd = st3.get("viewer_redo") or {}
                    if rd:
                        rd["pending"] = False
                        print(f"  viewer check: FAILED — re-write {R.DISPLAY.get(rd['stage'], rd['stage'])} "
                              f"({rd['fix_at']}) with the notes below, then `done` again from there:\n\n{rd['notes']}")
                    else:
                        print(f"  {e}")
                (d / "run.json").write_text(json.dumps(st3, indent=2))
    else: raise SystemExit(__doc__)

if __name__ == "__main__": main()
