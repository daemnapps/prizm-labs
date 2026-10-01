#!/usr/bin/env python3
"""outlier-brief's own tests. stdlib only, no network, no model — the model is
a stub handed to the runner. Everything is written under a TEMP workspace
(`AI_WORKSPACE`): a made-up brand in a temp `brands/`, runs in a temp `runs/`.
The real `runs/` and `brands/` are never touched.

    python3 outlier-brief/tests/test_outlier_brief.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "tools"
REAL = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())

WS = Path(tempfile.mkdtemp(prefix="outlier-brief-test-"))
BRAND = WS / "brands" / "testbrand"
(BRAND / "offers").mkdir(parents=True)
(BRAND / "strategy").mkdir()
(BRAND / "core-avatars" / "tired-parent").mkdir(parents=True)
(BRAND / "core-avatars" / "night-worker").mkdir(parents=True)
(BRAND / "core-avatars" / "not-an-avatar").mkdir(parents=True)           # no profile.md → not an avatar
(BRAND / "position.md").write_text("# The position\n\nThe kit is made for people who have no time. Market stage: stage-3.\n")
(BRAND / "story.md").write_text("# The story\n\nThe founder packed the first kits at a kitchen table.\n")
(BRAND / "offers" / "offer-bank.md").write_text(
    "# Offer bank\n\n## glow-kit — The Glow Kit\n\nOne kit. $30.00 one time.\n\n## big-kit — The Big Kit\n\n$55.00.\n")
(BRAND / "core-avatars" / "tired-parent" / "profile.md").write_text(
    "# Tired parent\n\nA parent who gets ten minutes alone a day and spends them in the bathroom.\n")
(BRAND / "core-avatars" / "night-worker" / "profile.md").write_text("# Night worker\n\nWorks nights, sleeps days.\n")
(BRAND / "strategy" / "angles.json").write_text(json.dumps(
    {"angles": [{"id": "ten-minutes", "name": "Ten minutes", "avatar": "tired-parent", "status": "active",
                 "what": "The only ten minutes of the day that are theirs."}]}))
os.symlink(REAL / "components", WS / "components")
os.environ["AI_WORKSPACE"] = str(WS)

sys.path.append(str(TOOLS))
import paths as P                # noqa: E402
import slots as S                # noqa: E402
import brand_context as B        # noqa: E402
import elements_pick as L        # noqa: E402
import gates as G                # noqa: E402
import handoff as H              # noqa: E402
import run as R                  # noqa: E402
import approve as A              # noqa: E402

IDEA = "A parent locks the bathroom door for ten minutes. That is the whole ad. Nobody knocks."
FRAMEWORK = L.ids(L.FRAMEWORK)[0]
AWARE = L.ids(L.AWARENESS)[-2]
SOPH = L.ids(L.SOPHISTICATION)[2]

ROUNDOUT = """# WHAT THE IDEA REALLY IS

The idea is a single quiet scene in which a parent takes ten minutes alone.

# WHO IT IS FOR

It is for `tired-parent`, because the card says they get ten minutes alone a day.

# WHAT IT PROMISES

It promises ten minutes that belong to them.

# WHAT WE HAVE THAT TOUCHES IT

- The position says the kit is made for people who have no time.

# WHAT WE DO NOT HAVE

- There is no customer quote on file about the bathroom door.

# QUESTIONS FOR YOU

1. Is the parent alone in the house, or are the children outside the door?

# ROUNDOUT

```json
{"avatar": "tired-parent", "sub": null, "questions": ["Is the parent alone in the house, or are the children outside the door?"]}
```
"""

AWARENESS = f"""# WHERE THE READER STANDS

They know they are tired and they have not connected it to any product.

# THE AWARENESS ENTRY

`{AWARE}`, because the idea opens on the need and not on the kit.

# WHAT IT MUST NOT ASSUME

It must not assume they have heard of the kit.

# THE SOPHISTICATION STAGE

`{SOPH}`, taken from the position file.

```AWARENESS
{{"awareness": "{AWARE}", "sophistication": "{SOPH}"}}
```
"""


def brief(price="$30.00", frameworks=None, offer="glow-kit", extra=""):
    return f"""# THE BIG IDEA

The owner said: "A parent locks the bathroom door for ten minutes." Sharpened, the ad is the ten minutes themselves, and nothing interrupts them.

# THE ARGUMENT

The reader wants ten minutes that are theirs. The kit is made for people who have no time, so it fits inside those minutes.

# THE AWARENESS ENTRY

This is written for `{AWARE}` and for `{SOPH}`. The reader feels the need and has not tied it to a product.

# THE PROOF WE HAVE

- The position file says the kit is made for people who have no time.

# WHAT IS MISSING

- There is no customer quote on file about hiding in the bathroom.

# HOOK DIRECTIONS

- Open on the sound of the lock, which tells the reader this time is protected.

# THE WORLD

A small bathroom in a loud house, in the evening, with the door locked.

# THE FRAMEWORKS IT FITS

`{FRAMEWORK}` fits because the need is named before anything is offered. The kit is {price}.{extra}

# WHAT IT MUST NEVER CLAIM

- It must never claim a result, because the files carry none.

# CONCEPT

```CONCEPT
{json.dumps({"frameworks": frameworks or [FRAMEWORK], "angle": "ten-minutes", "offer": offer})}
```
"""


CLEAN_CHECK = '```CHECK\n{"facts": [], "chops": [], "typos": []}\n```'


def formats_answer(**over):
    rec = {"format": "plain-talk", "style": None, "framework": FRAMEWORK, "candidates": [], "why": "The brief is one person in one room."}
    rec.update(over)
    return "```FORMATS\n" + json.dumps({"video": rec}) + "\n```"


class Stub:
    """The model, stubbed: answers by which step's prompt it was handed."""
    def __init__(self, brief_text=None, check=CLEAN_CHECK, formats=None):
        self.brief, self.check, self.formats = brief_text or brief(), check, formats or formats_answer()
        self.calls, self.prompts = [], {}

    def __call__(self, prompt, model):
        for step, mark, answer in (("idea4", "You are checking one concept brief", self.check),
                                   ("hand1", "**The media asked for:**", self.formats),
                                   ("idea3", "You are writing ONE concept brief", self.brief),
                                   ("idea2", "the ad needs its foundation", AWARENESS),
                                   ("idea1", "You are rounding the idea out.", ROUNDOUT)):
            if mark in prompt:
                self.calls.append((step, model))
                self.prompts[step] = prompt
                return 0, answer, ""
        raise AssertionError("the stub was handed a prompt it does not know")


def fake_video_formats():
    """A video format list with one defined row and one Damon has only named."""
    E = L.library()
    E._cache["format.video"] = {"rows": [
        {"id": "plain-talk", "name": "Plain talk", "what": "one person says it to camera", "status": "draft",
         "source": "ai-video-production/formats/bank.json"},
        {"id": "named-only", "name": "Named only", "what": "[TO DEFINE — named by the owner as a format we collect]",
         "status": "draft", "source": "components/elements/additions.json"}]}
    E._cache["style.video"] = {"rows": [
        {"id": "clay-look", "name": "Clay look", "what": "[TO DEFINE — a look, not a format]", "status": "draft",
         "source": "components/elements/additions.json"}]}


class Base(unittest.TestCase):
    n = 0

    def setUp(self):
        fake_video_formats()
        Base.n += 1
        self.label = f"t{Base.n}"
        self.idea = WS / f"idea-{self.label}.md"
        self.idea.write_text(IDEA)
        self.said = []

    def echo(self, *a):
        self.said.append(" ".join(str(x) for x in a))

    def out(self):
        return "\n".join(self.said)

    def dir(self):
        return P.record_dir("testbrand", self.label)

    def run_brief(self, stub=None, extra=()):
        stub = stub or Stub()
        code = R.main([str(self.idea), "--brand", "testbrand", "--label", self.label, *extra], runner=stub, echo=self.echo)
        return code, stub

    def approve(self, stub=None, extra=()):
        stub = stub or Stub()
        code = A.main([self.label, "--brand", "testbrand", *extra], runner=stub, echo=self.echo)
        return code, stub

    def state(self):
        return json.loads((self.dir() / "run.json").read_text())


class TheReviewStop(Base):
    def test_stops_before_approval(self):
        code, stub = self.run_brief()
        self.assertEqual(code, 0, self.out())
        self.assertEqual([c[0] for c in stub.calls], ["idea1", "idea2", "idea3", "idea4"])
        st = self.state()
        self.assertEqual(st["review"]["state"], "awaiting")
        self.assertEqual(st["state"], "awaiting approval")
        self.assertNotIn("hand1", st["stages"])
        self.assertFalse((self.dir() / "formats.json").exists())
        self.assertEqual(sorted(p.name for p in (self.dir() / "deliverable").iterdir()), ["concept-brief.md"])
        self.assertIn("awaiting approval", self.out())
        read = (self.dir() / "deliverable" / "concept-brief.md").read_text()
        self.assertIn("Questions for you", read)
        self.assertNotIn("```CONCEPT", read)

    def test_models_follow_the_tiers(self):
        _, stub = self.run_brief()
        from run_kit import model as M
        self.assertEqual(dict(stub.calls), {"idea1": M.TIERS["reads"], "idea2": M.TIERS["checks"],
                                            "idea3": M.TIERS["designs"], "idea4": M.TIERS["checks"]})

    def test_hand_off_refuses_without_approval(self):
        self.run_brief()
        code, stub = self.approve(extra=["--hand-off-only"])
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", self.out())
        self.assertIn("not approved", self.out())
        self.assertEqual(stub.calls, [])
        self.assertFalse((self.dir() / "formats.json").exists())
        self.assertFalse(list((self.dir() / "deliverable").glob("handoff--*")))
        with self.assertRaises(G.NotApproved):
            G.require_approval(self.state(), (self.dir() / A.BRIEF_FILE).read_text())

    def test_approve_then_hand_off(self):
        self.run_brief()
        code, stub = self.approve(extra=["--note", "yes, make it"])
        self.assertEqual(code, 0, self.out())
        self.assertEqual([c[0] for c in stub.calls], ["hand1"])
        st = self.state()
        self.assertEqual(st["review"]["state"], "approved")
        self.assertEqual((st["review"]["by"], st["review"]["note"]), ("Damon", "yes, make it"))
        self.assertTrue(st["review"]["at"])
        self.assertEqual(st["state"], "handed off")
        hand = json.loads((self.dir() / "deliverable" / "handoff--video.json").read_text())
        self.assertEqual(hand["choice"]["brand"], "testbrand")
        self.assertEqual(hand["choice"]["avatar"], "tired-parent")
        self.assertEqual((hand["choice"]["awareness"], hand["choice"]["sophistication"]), (AWARE, SOPH))
        self.assertEqual((hand["choice"]["format"], hand["choice"]["framework"]), ("plain-talk", FRAMEWORK))
        self.assertIn("compose.py plan --brand testbrand --avatar tired-parent", hand["command"]["plan"])
        self.assertIn("A small bathroom in a loud house", hand["concept_brief"])
        self.assertNotIn("```CONCEPT", hand["concept_brief"])
        self.assertTrue((self.dir() / "deliverable" / "handoff--video.md").is_file())
        self.assertIn("**Status: approved by Damon", (self.dir() / "deliverable" / "concept-brief.md").read_text())
        self.assertIn("nothing was started", self.out())

    def test_a_brief_edited_after_approval_is_not_the_approved_brief(self):
        self.run_brief()
        self.approve()
        f = self.dir() / A.BRIEF_FILE
        f.write_text(f.read_text().replace("loud house", "quiet house"))
        self.said.clear()
        code, stub = self.approve(extra=["--hand-off-only", "--media", "video,copy"])
        self.assertEqual(code, 2)
        self.assertIn("changed since", self.out())
        self.assertEqual(stub.calls, [])

    def test_sent_back_records_the_note_and_the_rewrite_is_told(self):
        self.run_brief()
        code, stub = self.approve(extra=["--send-back", "--note", "too soft, open on the lock"])
        self.assertEqual((code, stub.calls), (0, []))
        self.assertEqual(self.state()["review"]["state"], "sent back")
        self.assertFalse(list((self.dir() / "deliverable").glob("handoff--*")))
        code, stub = self.run_brief(extra=["--rerun-from", "idea3"])
        self.assertEqual(code, 0, self.out())
        self.assertEqual([c[0] for c in stub.calls], ["idea3", "idea4"])
        self.assertIn("too soft, open on the lock", stub.prompts["idea3"])

    def test_a_rerun_that_rewrites_the_brief_needs_a_new_approval(self):
        self.run_brief()
        self.approve()
        self.run_brief(stub=Stub(brief_text=brief(extra=" It is the smaller of the two kits.")), extra=["--rerun-from", "idea3"])
        st = self.state()
        self.assertEqual(st["review"]["state"], "awaiting")
        self.assertEqual(st["review"]["history"][-1]["state"], "approved")


class Elements(Base):
    def test_unknown_format_is_refused_with_the_real_ones_named(self):
        self.run_brief()
        code, _ = self.approve(stub=Stub(formats=formats_answer(format="a-format-nobody-defined")))
        self.assertEqual(code, 2)
        held = G.state(self.dir())["elements"]
        self.assertEqual(held["result"], "HELD")
        self.assertIn("a-format-nobody-defined", held["problems"][0])
        self.assertIn("plain-talk", held["problems"][0])
        self.assertFalse(list((self.dir() / "deliverable").glob("handoff--*")))

    def test_a_to_define_format_is_flagged_and_not_handed_off(self):
        self.run_brief()
        code, _ = self.approve(stub=Stub(formats=formats_answer(format="named-only")))
        self.assertEqual(code, 0, self.out())
        rec = json.loads((self.dir() / "formats.json").read_text())
        self.assertEqual(rec["flagged"], [{"list": "format/video", "id": "named-only", "flag": "named, not defined yet"}])
        self.assertFalse(rec["picks"]["video"]["hand_off"])
        self.assertFalse(list((self.dir() / "deliverable").glob("handoff--*")))
        self.assertIn("named, not defined yet", self.out())
        self.assertEqual(G.state(self.dir())["elements"]["result"], "pass")

    def test_a_to_define_candidate_and_style_are_flagged_and_the_defined_format_goes(self):
        self.run_brief()
        code, _ = self.approve(stub=Stub(formats=formats_answer(candidates=["named-only"], style="clay-look")))
        self.assertEqual(code, 0, self.out())
        rec = json.loads((self.dir() / "formats.json").read_text())
        self.assertEqual({f["id"] for f in rec["flagged"]}, {"named-only", "clay-look"})
        hand = json.loads((self.dir() / "deliverable" / "handoff--video.json").read_text())
        self.assertEqual(hand["choice"]["format"], "plain-talk")
        self.assertIsNone(hand["style"])

    def test_his_own_pick_costs_nothing_and_is_checked_as_hard(self):
        self.run_brief()
        code, stub = self.approve(extra=["--formats", "video:plain-talk"])
        self.assertEqual((code, stub.calls), (0, []), self.out())
        self.assertTrue((self.dir() / "deliverable" / "handoff--video.json").is_file())
        self.said.clear()
        code, _ = self.approve(extra=["--hand-off-only", "--formats", "video:nope"])
        self.assertEqual(code, 2)
        self.assertIn("plain-talk", self.out())

    def test_other_media_get_a_plain_brief_and_a_command_and_nothing_starts(self):
        self.run_brief()
        email = L.ids(("format", "email"))[0]
        code, _ = self.approve(extra=["--formats", f"video:plain-talk,copy:{L.ids(('format', 'copy'))[0]},email:{email}"])
        self.assertEqual(code, 0, self.out())
        names = sorted(p.name for p in (self.dir() / "deliverable").glob("handoff--*"))
        self.assertEqual(names, ["handoff--copy.md", "handoff--email.md", "handoff--video.json", "handoff--video.md"])
        text = (self.dir() / "deliverable" / "handoff--email.md").read_text()
        self.assertIn(f"--type {email}", text)
        self.assertIn("Not ready", text)
        self.assertIn("A small bathroom in a loud house", text)

    def test_an_unknown_framework_in_the_brief_is_refused(self):
        code, _ = self.run_brief(stub=Stub(brief_text=brief(frameworks=["a-plan-nobody-wrote"])))
        self.assertEqual(code, 2)
        self.assertIn(FRAMEWORK, G.state(self.dir())["elements"]["problems"][0])
        self.assertTrue(self.state()["state"].startswith("held"))


class InputsAndCopy(Base):
    def test_unknown_avatar_angle_and_brand_are_refused_by_name(self):
        code, stub = self.run_brief(extra=["--avatar", "somebody-else", "--angle", "no-such-angle"])
        self.assertEqual((code, stub.calls), (2, []))
        self.assertIn("night-worker, tired-parent", self.out())
        self.assertNotIn("not-an-avatar", self.out())
        self.assertIn("ten-minutes", self.out())
        self.said.clear()
        code = R.main([str(self.idea), "--brand", "no-such-brand"], runner=Stub(), echo=self.echo)
        self.assertEqual(code, 2)
        self.assertIn("testbrand", self.out())
        self.assertFalse((WS / "runs" / P.TOOL / "no-such-brand").exists())

    def test_there_is_no_default_brand(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit):
                R.main([str(self.idea)], runner=Stub(), echo=self.echo)
            with self.assertRaises(SystemExit):
                A.main(["x"], runner=Stub(), echo=self.echo)
        self.assertIn("--brand", err.getvalue())

    def test_an_empty_idea_is_refused(self):
        code = R.main(["-", "--brand", "testbrand", "--label", self.label], runner=Stub(), echo=self.echo, piped="  \n")
        self.assertEqual(code, 2)
        self.assertIn("the idea is empty", self.out())

    def test_a_price_the_offer_bank_does_not_sell_holds_the_brief(self):
        code, _ = self.run_brief(stub=Stub(brief_text=brief(price="$19.00")))
        self.assertEqual(code, 2)
        self.assertIn("$19.00", G.state(self.dir())["copy"]["problems"][0])
        self.assertFalse((self.dir() / "deliverable").exists())
        self.said.clear()
        code, _ = self.approve()
        self.assertEqual(code, 2)
        self.assertIn("never reached the review stop", self.out())

    def test_unfilled_and_a_claim_the_files_do_not_carry_hold_the_brief(self):
        check = ('```CHECK\n{"facts": [{"problem": "NOT IN THE FILES", "quote": "works in two days", "files_say": "nothing on file"}],'
                 ' "chops": [{"quote": "Ten minutes. Hers.", "joined": "The ten minutes are hers."}], "typos": []}\n```')
        code, _ = self.run_brief(stub=Stub(brief_text=brief(extra=" [UNFILLED: a proof]"), check=check))
        self.assertEqual(code, 2)
        probs = " | ".join(G.state(self.dir())["copy"]["problems"])
        for want in ("UNFILLED", "works in two days", "chopped thought"):
            self.assertIn(want, probs)

    def test_pinning_awareness_and_sophistication_skips_the_read(self):
        code, stub = self.run_brief(extra=["--avatar", "tired-parent", "--awareness", AWARE, "--sophistication", SOPH])
        self.assertEqual(code, 0, self.out())
        self.assertEqual([c[0] for c in stub.calls], ["idea1", "idea3", "idea4"])
        self.assertEqual(self.state()["stages"]["idea2"]["status"], "skipped")

    def test_brand_context_comes_from_the_brand_folder_and_says_what_is_missing(self):
        _, stub = self.run_brief()
        self.assertIn("packed the first kits at a kitchen table", stub.prompts["idea3"])
        self.assertIn("not on file: brands/testbrand/core-avatars/objection-bank.md", stub.prompts["idea3"])
        self.assertIn("ten minutes alone a day", stub.prompts["idea3"])          # the chosen reader's card
        self.assertIn("# Awareness", stub.prompts["idea2"])                      # the doctrine's own slice, bound


class DryRun(Base):
    def test_the_dry_run_is_free_and_leaves_nothing(self):
        before = sorted(str(p) for p in WS.rglob("*") if "components" not in p.parts)
        stub = Stub()
        code = R.main([str(self.idea), "--brand", "testbrand", "--label", self.label, "--dry-run"], runner=stub, echo=self.echo)
        self.assertEqual((code, stub.calls), (0, []))
        self.assertIn("0 model calls", self.out())
        self.assertEqual(before, sorted(str(p) for p in WS.rglob("*") if "components" not in p.parts))

    def test_the_approval_dry_run_records_nothing(self):
        self.run_brief()
        before = {str(p): p.read_bytes() for p in self.dir().rglob("*") if p.is_file()}
        code, stub = self.approve(extra=["--dry-run"])
        self.assertEqual((code, stub.calls), (0, []), self.out())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.dir().rglob("*") if p.is_file()})
        self.assertEqual(self.state()["review"]["state"], "awaiting")

    def test_a_dry_run_with_a_bad_input_says_so_and_exits_1(self):
        code = R.main([str(self.idea), "--brand", "testbrand", "--avatar", "nobody", "--dry"], runner=Stub(), echo=self.echo)
        self.assertEqual(code, 1)
        self.assertIn("nothing was spent", self.out())


class ReadingAnswers(unittest.TestCase):
    def test_a_block_is_read_however_it_was_fenced(self):
        want = {"awareness": "x", "sophistication": "y"}
        for text in ('```AWARENESS\n{"awareness": "x", "sophistication": "y"}\n```',
                     '## AWARENESS:\n\n```json\n{"awareness": "x", "sophistication": "y"}\n```',
                     '**Awareness**\n```\n{"awareness": "x", "sophistication": "y"}\n```',
                     'Here it is: {"awareness": "x", "sophistication": "y"}'):
            self.assertEqual(S.block(text, "AWARENESS", keys=("awareness",)), want)
        with self.assertRaises(ValueError):
            S.block("no data here", "AWARENESS", keys=("awareness",))

    def test_headings_are_found_the_way_a_model_writes_them(self):
        text = "## 1. The Big Idea\nx\n\n**THE ARGUMENT:**\ny\n\n### The awareness entry — where they stand\nz\n"
        self.assertEqual(S.missing_heads(text, ("THE BIG IDEA", "THE ARGUMENT", "THE AWARENESS ENTRY")), [])
        self.assertEqual(S.missing_heads(text, ("THE WORLD",)), ["THE WORLD"])

    def test_a_guessed_avatar_from_the_round_out_is_refused(self):
        who, bad = G.read_roundout('```ROUNDOUT\n{"avatar": "made-up-reader", "questions": []}\n```', "testbrand")
        self.assertIsNone(who["avatar"])
        self.assertIn("tired-parent", bad[0])


class Prompts(unittest.TestCase):
    FILES = sorted((HERE.parent / "prompts").glob("*-damon.md"))

    def test_every_step_has_a_prompt_and_the_guard_is_at_the_top(self):
        import steps as ST
        self.assertEqual(len(self.FILES), len(ST.STEPS))
        for f in self.FILES:
            self.assertTrue(f.read_text().startswith("**No example in this prompt is an answer.**"), f.name)

    def test_no_brand_is_named_in_a_prompt_or_in_the_code(self):
        brands = [p.name for p in (REAL / "brands").iterdir() if p.is_dir() and not p.name.startswith(("_", "."))]
        for f in [*self.FILES, *TOOLS.glob("*.py")]:
            low = f.read_text().lower()
            for b in brands:
                self.assertNotIn(b.lower(), low, f"{f.name} names {b}")

    def test_the_doctrine_is_bound_not_retyped_and_the_pronoun_lint_passes(self):
        for level in L.ids(L.AWARENESS):
            for f in self.FILES:
                self.assertNotIn(level, f.read_text(), f"{f.name} re-types the awareness level `{level}`")
        r = subprocess.run([sys.executable, str(REAL / "components" / "marketing-doctrine" / "lint_prompts.py"),
                            *map(str, self.FILES)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=1)
    finally:
        import shutil
        shutil.rmtree(WS, ignore_errors=True)
