#!/usr/bin/env python3
"""A batch, start to finish. One command.

    run.py runs/<brand>/<run>

Reads the spec, generates every ad on Higgsfield, judges them, names the
survivors, files them, and delivers to Shared Assets. Prints where they went.

    run.py <run> --generate-only    make the pictures, stop before judging
    run.py <run> --finish-only      judge and file what is already in inbox/
    run.py <run> --dry-run          resolve every input, OK or MISSING per ad —
                                    no model, no judge, nothing written
    run.py <run> --gates warn       record a failed gate and carry on

Two gates run before anything is made (`tools/gates.py`): **elements** — the
template, style pack and picture format the batch names are real rows in the
element library — and **copy** — the words burned into the picture carry no
UNFILLED note and no price the brand's offer bank does not sell. A held batch
says why, in `check.json`. The **media** gate runs in `finish.py`, after the
judge, and the batch's record is filed to `runs/image-production/<brand>/<batch>/`.

**Damon never runs this.** A session runs it and hands him the link. It exists
so that every batch is made the same way — the four Labor Day ads took eleven
passes because there was no single path, and each fix re-rolled the whole
picture instead of changing one thing.

A run before it starts:

    runs/<brand>/<batch>/
      batch.json            what to make, the offer, the cast, the checks
      prompts/<slug>.txt    one prompt per ad, verbatim

and after:

    ads/<slug>/<13-field-name>-a01.png    survivors, named for Meta
    rejected/<slug>.png + why.md          killed, with the reason
    report.md                             what passed, what died, why
"""

import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("run_dir")
    a.add_argument("--generate-only", action="store_true")
    a.add_argument("--finish-only", action="store_true")
    a.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true")
    a.add_argument("--gates", choices=("hold", "warn"), default="hold")
    o = a.parse_args()

    sys.path.insert(0, str(TOOLS))
    if o.dry_run:
        import dryrun
        sys.exit(dryrun.main([o.run_dir]))

    run = Path(o.run_dir).resolve()
    spec_path = run / "batch.json"
    if not spec_path.is_file():
        sys.exit(f"no batch.json in {run}")
    spec = json.loads(spec_path.read_text())

    if not spec.get("brand"):
        sys.exit("batch.json names no `brand` — there is no default brand")
    print(f"{spec['brand']} · {spec['batch']} · {len(spec['ads'])} ads")

    if not o.finish_only:
        import gates as G
        Held = G.quality().Held
        try:
            G.elements_gate(run, spec, o.gates)
            G.copy_gate(run, spec, o.gates)
        except Held:
            G.file_quietly(G.file_record, run)
            sys.exit(f"held — nothing was made. Why is on file: {run / 'check.json'}")

    if not o.finish_only:
        # There is no unattended generation path and there is not going to be
        # one: Higgsfield's image models are reached through its MCP, which a
        # script cannot call, and there is no API key (Damon, 2026-09-14:
        # "we do not have a higgsfield key so remove that from this workflow
        # entirely"). So this half writes the jobs, a session generates them,
        # and `plates.py ingest` brings them back.
        print("\nplates")
        r = subprocess.run([sys.executable, str(TOOLS / "plates.py"), "prepare",
                            "--run", str(run)])
        if r.returncode != 0:
            sys.exit("could not write the plate jobs")
        if not (run / "inbox").glob("*.png"):
            pass
        made = sorted((run / "inbox").glob("*.png"))
        if not made:
            print("\nnothing in the inbox yet — generate the jobs above, then:")
            print(f"  plates.py ingest --run {run} --results <results.json>")
            print("  run.py --finish-only", run)
            return

    if o.generate_only:
        print(f"\nframes in {run / 'inbox'} — not judged")
        return

    print("\njudging and filing")
    subprocess.run([sys.executable, str(TOOLS / "finish.py"), str(run)])


if __name__ == "__main__":
    main()
