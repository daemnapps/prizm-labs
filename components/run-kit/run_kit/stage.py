"""A chain, and one step of it.

The dry run lives INSIDE the step runner, so it is truly free — email.py's
ran stage 0 before its dry-run block and spent a call every time. A finished
step is reused only if its prompt is unchanged AND nothing it depends on
reran (pages/run.py:220-235). Every prompt is saved as sent, beside what came
back. Lifted, not invented.
"""
import time
from pathlib import Path

from . import model as M
from . import prompts as P
from .record import Record, now

DRY = "[dry run — not written]"


def creative_qc(tool, stage, run_dir, output, given, echo=print):
    """THE CREATIVE QC LOOP for every chain built on run-kit (the owner, 2026-10-02:
    "installed for each of my production tools … for all stages in the creation
    process"): the stage's output against what it was given and its bars
    (components/quality-checks/definitions/stages.json — marketing-chain-checks),
    filed in qc-log/. Never stops the chain on its own."""
    try:
        import sys
        q = next(str(p / n) for p in Path(__file__).resolve().parents
                 for n in ("marketing-chain-checks", "quality-checks")
                 if (p / n / "marketing_chain_checks").is_dir())
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output,
                               sources=[given] if Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            echo(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
    except Exception as e:
        echo(f"  QC {stage}: review not run ({type(e).__name__})")


class Chain:
    """
    steps: [{"key": "stage3", "name": "Writer", "tier": "designs", "label": "draft",
             "depends": ["stage2"]}, ...]  — order is run order.
    """

    def __init__(self, tool, brand, label, out_dir, prompts_dir, steps, assignment=None,
                 dry=False, rerun_from=None, force_model=None, tiers=None, runner=None, echo=print):
        self.steps = {s["key"]: s for s in steps}
        self.order = [s["key"] for s in steps]
        if rerun_from and rerun_from not in self.steps:
            raise ValueError(f"rerun-from wants one of: {', '.join(self.order)}")
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.prompts_dir = Path(prompts_dir)
        self.dry, self.rerun_from = dry, rerun_from
        self.force_model, self.tiers, self.runner, self.echo = force_model, tiers, runner, echo
        self.record = Record(self.out, tool, brand, label, assignment)
        self.tool = tool
        self.reran = set()
        self.calls = 0

    # ------------------------------------------------------------------
    def _reusable(self, key, prompt_sha):
        step, old = self.steps[key], self.record.state["stages"].get(key) or {}
        out = self.out / f"{key}--{step['label']}.md"
        if not (old.get("status") in ("done", "reused") and out.is_file()):
            return None
        if self.rerun_from and self.order.index(key) >= self.order.index(self.rerun_from):
            return None
        if old.get("prompt_sha256_12") not in (None, prompt_sha):
            self.echo(f"     {key}: prompt changed since the last run — rewriting")
            return None
        hit = [d for d in step.get("depends", []) if d in self.reran]
        if hit:
            self.echo(f"     {key}: reads from {', '.join(hit)}, which reran — rewriting")
            return None
        return out.read_text().strip()

    def run(self, key, **fields):
        step = self.steps[key]
        pf = P.latest(self.prompts_dir, key)
        template = pf.read_text()
        filled = P.fill(template, fields)                      # refuses unfilled fields, even dry
        (self.out / f"{key}--sent.md").write_text(filled)
        psha = P.sha(pf)
        chosen, why = M.pick(step.get("tier", "designs"), len(filled), self.force_model, self.tiers)

        if self.dry:
            self.echo(f"  ~~ {key}  {step.get('name', '')}: {len(filled):,} chars → {chosen} ({why}) — dry")
            self.record.stage(key, status="dry", model=chosen, why_model=why, prompt_name=pf.name,
                              prompt_sha256_12=psha, chars_in=len(filled), wants=sorted(fields))
            return DRY

        kept = self._reusable(key, psha)
        if kept is not None:
            self.echo(f"  == {key}  (kept from the earlier run)")
            self.record.stage(key, **{**self.record.state["stages"][key], "status": "reused"})
            return kept

        self.echo(f"  -> {key}  {step.get('name', '')} ({pf.name}) on {chosen}" + ("" if why == step.get("tier") else f" — {why}"))
        t0 = time.time()
        text = M.call(filled, chosen, label=key, runner=self.runner)
        self.calls += 1
        out = self.out / f"{key}--{step['label']}.md"
        out.write_text(text + "\n")
        self.reran.add(key)
        self.record.stage(key, status="done", model=chosen, why_model=why, prompt_name=pf.name,
                          prompt_sha256_12=psha, wants=sorted(fields), seconds=round(time.time() - t0, 1),
                          chars_in=len(filled), chars_out=len(text), out=out.name, sent=f"{key}--sent.md",
                          finished=now())
        if not self.dry:
            creative_qc(self.tool, key, self.out, out, self.out / f"{key}--sent.md", self.echo)
        return text

    def deliver(self, *files, name=None):
        """Put what this chain hands on where the standard says — the run's own
        `deliverable/` (runs/README.md).

        On the chain rather than in each machine, because machine-by-machine is
        exactly how it failed: on 2026-09-23 an index over 198 runs found three
        briefs filed correctly and 110 sitting under a name only their own code
        knew. A chain that ends with `chain.deliver(the_brief)` cannot get it
        wrong, and a chain that never calls it says so in its record instead of
        being silently unfindable.

        Called with no argument, it takes the LAST stage's output — which for
        every teardown is the brief.
        """
        from . import filing
        picked = [Path(f) for f in files if f]
        if not picked:
            for key in reversed(self.order):
                step = self.steps[key]
                out = self.out / f"{key}--{step['label']}.md"
                if out.is_file():
                    picked = [out]
                    break
        if not picked:
            self.record.state["deliverable"] = {"files": [], "why": "nothing to deliver — no stage wrote an output"}
            self.record.save()
            return []
        written = filing.deliver(self.out, picked, name=name)
        self.record.state["deliverable"] = {
            "files": [str(w.relative_to(self.out)) for w in written],
            "from": [str(p.relative_to(self.out)) if p.is_relative_to(self.out) else str(p) for p in picked]}
        self.record.save()
        self.echo(f"     deliverable: {', '.join(w.name for w in written)}")
        return written

    def skip(self, key, why):
        """A step that did not run is recorded with its reason, never left blank."""
        self.record.stage(key, status="skipped", why=why)
        self.echo(f"  -- {key}  skipped ({why})")
