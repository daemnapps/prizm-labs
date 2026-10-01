#!/usr/bin/env python3
"""The declared test for the second door — compose.py and the FRAMEWORK lane.

    python3 test_compose.py

No pytest, no network, no model call. `plan` and `grid` (without --go) never
call a model by construction, so this suite runs them against the REAL
doctrine, format bank and a real avatar (<brand> / spot-hider) rather than a
mocked-up shelf — the ids have to be the ids that exist. Any run folder a
test opens under machine/runs/ is removed in tearDown; framework_bank's
--promote is exercised against a temp copy of ad-frameworks.json so this
suite never writes to the curated file.

Stdlib only (unittest).
"""

import json
import shutil
import sys
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chain as C            # noqa: E402
import compose as CP         # noqa: E402
import framework_bank as FB  # noqa: E402

BRAND = "<brand>"
AVATAR = "spot-hider"
SUB = "sun-damage-reckoner"
FRAMEWORK = "mechanism-led"       # entry problem-aware -> exit product-aware
FORMAT = "single-presenter"
AWARENESS = "problem-aware"
PRODUCT = "brilliance-face-scrub"   # <brand> has 3 — a plan must say which

_OPENED = []          # every run folder a test opened, cleaned in tearDown

# Tests NEVER open a run in the real runs/ folder. On 2026-09-18 this suite
# opened a composed run under the same label as a real one and its tearDown
# deleted the real run four times over ("something keeps deleting the run
# folder"). Every test run now lands in a temp folder that only tests see.
import tempfile
import run as _RUN
_TMP_RUNS = Path(tempfile.mkdtemp(prefix="video-teardown-tests-"))
_RUN.RUNS = _TMP_RUNS
if hasattr(CP, "RUNS"):
    CP.RUNS = _TMP_RUNS
C.runs_root = lambda *a, **k: _TMP_RUNS      # compose.py opens its folder through this


def _cleanup_opened():
    for d in _OPENED:
        d = Path(d)
        if _TMP_RUNS in d.resolve().parents or d.resolve() == _TMP_RUNS:
            shutil.rmtree(d, ignore_errors=True)
        # a folder outside the temp root is never touched — that is a real run
    _OPENED.clear()


class Choose(unittest.TestCase):
    """`choose()` resolves a real choice and refuses an unreal one, by name."""

    def test_a_real_choice_resolves(self):
        spec = CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                         FRAMEWORK, "ai", None, None)
        self.assertEqual(spec["framework"]["id"], FRAMEWORK)
        self.assertEqual(spec["format"]["id"], FORMAT)
        self.assertEqual(spec["awareness"]["id"], AWARENESS)
        self.assertEqual(spec["route"], "ai")
        self.assertEqual(spec["sub"], SUB)
        # sophistication inherited from the framework row when not named
        self.assertIn(spec["sophistication"]["id"], spec["framework"]["sophistication"])
        self.assertIn("inherited", spec["sophistication_why"])

    def test_named_sophistication_is_recorded_as_named(self):
        stage = CP.choose(BRAND, AVATAR, SUB, AWARENESS, "stage-4", FORMAT,
                          FRAMEWORK, "ai", None, None)
        self.assertEqual(stage["sophistication"]["id"], "stage-4")
        self.assertEqual(stage["sophistication_why"], "named on the run")

    def test_unknown_framework_refuses_by_name(self):
        with self.assertRaises(CP.Refused) as cm:
            CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                     "not-a-real-framework", "ai", None, None)
        msg = str(cm.exception)
        self.assertIn("not-a-real-framework", msg)
        self.assertIn(FRAMEWORK, msg)          # the ones there are, printed

    def test_unknown_format_refuses_by_name(self):
        with self.assertRaises(CP.Refused) as cm:
            CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, "not-a-real-format",
                     FRAMEWORK, "ai", None, None)
        self.assertIn("not-a-real-format", str(cm.exception))

    def test_unknown_awareness_refuses_by_name(self):
        with self.assertRaises(CP.Refused) as cm:
            CP.choose(BRAND, AVATAR, SUB, "not-a-real-level", None, FORMAT,
                     FRAMEWORK, "ai", None, None)
        self.assertIn("not-a-real-level", str(cm.exception))

    def test_unknown_avatar_refuses_by_name(self):
        with self.assertRaises(CP.Refused) as cm:
            CP.choose(BRAND, "not-a-real-avatar", None, AWARENESS, None,
                     FORMAT, FRAMEWORK, "ai", None, None)
        self.assertIn("not-a-real-avatar", str(cm.exception))

    def test_unknown_sub_avatar_refuses_by_name(self):
        with self.assertRaises(CP.Refused) as cm:
            CP.choose(BRAND, AVATAR, "not-a-real-sub", AWARENESS, None,
                     FORMAT, FRAMEWORK, "ai", None, None)
        self.assertIn("not-a-real-sub", str(cm.exception))

    def test_unknown_route_refuses_by_name(self):
        with self.assertRaises(CP.Refused):
            CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                     FRAMEWORK, "not-a-real-route", None, None)


class PlanResolves(unittest.TestCase):
    """`plan` opens the FRAMEWORK lane and resolves every stage, no model
    call, on both routes it is meant to run — ai and creator."""

    def tearDown(self):
        _cleanup_opened()

    def _plan(self, route, product=PRODUCT):
        spec = CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                         FRAMEWORK, route, None, None, product)
        d, st, bad = CP.cmd_plan(spec, label=f"test-compose-{route}-{int(time.time()*1000)}",
                                 quiet=True)
        _OPENED.append(d)
        return d, st, bad

    # A brand with more than one product refuses by name until --product
    # says which — that is chain.py's own rule (rule 4), not this lane's,
    # and it is proof the product now actually reaches the dry-run check.
    def test_no_product_on_a_multi_product_brand_refuses_by_name(self):
        d, st, bad = self._plan("creator", product=None)
        msgs = " ".join(m for _, f in bad for m in f)
        self.assertIn("--product", msgs)
        self.assertIn(PRODUCT, msgs)          # named among the ones there are

    # Two gaps neither belongs to the FRAMEWORK lane nor to compose.py: (1)
    # <brand> has no brands/<brand>/core-avatars/casting/CAST.md at all (only
    # <brand> does — stage5 wants it on every route, every lane), and (2) the
    # ai route's stage7 still asks for `@stage6` even though chain.stages()
    # itself skips stage6 for ai — true on an ordinary swipe lane too. Both
    # are pre-existing brand-data / chain facts, reproduced below rather than
    # silently excluded, so "resolves clean" means clean of what this build
    # is answerable for.
    KNOWN_GAPS = {"stage5": "brand file missing: brands/<brand>/core-avatars/"
                            "casting/CAST.md",
                  "stage7": "stage6, which this lane never runs"}

    def _unexplained(self, bad):
        out = []
        for s, findings in bad:
            gap = self.KNOWN_GAPS.get(s["key"])
            left = [m for m in findings if not (gap and gap in m)]
            if left:
                out.append((s["key"], left))
        return out

    def test_creator_route_resolves_clean_of_anything_this_lane_owns(self):
        """The creator route runs stage6 before stage7, so stage7's `@stage6`
        reference is in hand by the time it is checked there — the only
        finding left on this route is the pre-existing <brand> casting gap."""
        d, st, bad = self._plan("creator")
        self.assertEqual(self._unexplained(bad), [])
        self.assertEqual(st["production_route"], "creator")

    def test_ai_route_resolves_clean_of_anything_this_lane_owns(self):
        """The ai route is the generation route and its own deliverable is
        the stage-5 brief (task 4's own framing). What is left unresolved —
        casting at stage5, stage6 at stage7 — is proven below to be a fact
        about <brand> and about the ai route in general, not something the
        second door introduced."""
        d, st, bad = self._plan("ai")
        self.assertEqual(self._unexplained(bad), [])
        self.assertEqual(st["triage_lane"], "FRAMEWORK")
        self.assertEqual(st["source"]["kind"], "framework")

    def test_the_two_known_gaps_are_closed(self):
        # 2026-09-18: on the AI route stage 6 (frames) AND stage 7 (frames
        # injected into the creator brief) are dropped — the ai-lane brief is
        # the deliverable and the video machine makes the pictures. Any lane.
        swipe_plan = C.stages(BRAND, "", "ai", "ORGANIC")
        swipe_keys = [s["key"] for s in swipe_plan]
        self.assertNotIn("stage7", swipe_keys)
        self.assertNotIn("stage6", swipe_keys)
        # 2026-09-18: the cast sheet now exists — compiled from the brand's
        # own ai-cast/<name>/character.md files, so stage 5 casts from it.
        self.assertTrue((Path(C.WS) / "brands" / BRAND / "core-avatars" /
                         "casting" / "CAST.md").exists())

    def test_the_four_stand_ins_are_filed_done(self):
        d, st, bad = self._plan("ai")
        for key in ("stage0", "stage1", "stage1c", "stage1b"):
            self.assertEqual(st["stages"][key]["status"], "done", key)
            self.assertTrue(st["stages"][key].get("composed"))

    def test_the_composed_doctrine_row_carries_every_delivery_key(self):
        """A composed run has no source, so there is no delivery to have read
        — but the keys are still all there, or the bank, the filters and
        file_doctrine's key check all read a composed run as broken."""
        d, st, bad = self._plan("ai")
        doc = json.loads((d / "doctrine.json").read_text())
        self.assertTrue(doc.get("composed"))
        self.assertEqual(doc.get("_missing_keys"), None)
        dl = doc["delivery"]
        self.assertEqual(sorted(dl), ["avoid", "delivery_style", "humor",
                                      "pacing", "reference_world", "register"])
        for key in ("humor", "delivery_style", "register", "pacing"):
            self.assertEqual(dl[key], "not shown — no source", key)
        self.assertEqual(dl["reference_world"], [])
        self.assertEqual(dl["avoid"], [])

    def test_stage2f_is_in_the_plan_and_stage2_is_not(self):
        """`C.stages()` alone returns the full shared shape (stage2 included) —
        the FRAMEWORK route's own `skip` list is what drops stage2 in favour
        of stage2f, applied the same way `resolve_plan()` applies it."""
        spec = CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                         FRAMEWORK, "ai", None, None)
        plan = C.stages(spec["brand"], "", spec["route"], CP.LANE)
        route = C.route_for(CP.LANE)
        keys = [s["key"] for s in plan if s["key"] not in (route["skip"] or [])]
        self.assertIn("stage2f", keys)
        self.assertNotIn("stage2", keys)

    def test_stage2f_is_lane_only_and_absent_elsewhere(self):
        plan = C.stages(BRAND, "", "creator", "ORGANIC")
        self.assertNotIn("stage2f", [s["key"] for s in plan])

    def test_market_state_stand_in_parses(self):
        """1b's stand-in is written in 1b v6's own labelled-slot shape, so
        run.market_state_from() reads it exactly as a real 1b output — the
        same seven MARKET fields, none of which is a sub-avatar (that fact
        lives in st['audience'], set directly rather than parsed)."""
        import run as R  # noqa: E402
        spec = CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                         FRAMEWORK, "ai", None, None)
        text = CP.market_state(spec)
        parsed = R.market_state_from(text)
        self.assertIn(AWARENESS, parsed.get("awareness", ""))
        self.assertEqual(parsed.get("route_recommended"), "ai")
        self.assertTrue(parsed.get("sophistication"))

    def test_a_long_label_opens_the_same_folder_run_video_will_reopen(self):
        """Regression: open_composed() used to build the folder id with this
        module's own slug() (cap 70) while run_video() -> open_run() rebuilds
        it with run.py's own slug() (cap 40). Any label past 40 characters —
        which a composed label routinely is — opened two different folders:
        the real one, stood in and never touched again, and a second, empty
        one that stage0 then tried to run for real against no video."""
        import run as R  # noqa: E402
        spec = CP.choose(BRAND, AVATAR, SUB, AWARENESS, None, FORMAT,
                         FRAMEWORK, "ai", None, None, PRODUCT)
        label = CP.label_for(spec)
        self.assertGreater(len(label), 40, "the fixture label must be long "
                           "enough to have tripped the bug it regresses")
        d, st, bad = CP.cmd_plan(spec, label=label, quiet=True)
        _OPENED.append(d)
        reopened_slug = C.run_slug(R.slug(label), C.operator())
        self.assertEqual(d.name, reopened_slug)
        self.assertEqual(st["stages"]["stage0"]["status"], "done")

    def test_open_composed_stores_the_parsed_market_state_and_audience(self):
        d, st, bad = self._plan("ai")
        self.assertIn(AWARENESS, st["market_state"].get("awareness", ""))
        self.assertEqual(st["market_state"].get("route_recommended"), "ai")
        self.assertEqual(st["audience"]["_sub_avatar"], SUB)
        self.assertEqual(st["audience"]["_avatar"], AVATAR)


class Grid(unittest.TestCase):
    """`grid` (no --go) prints every cell and calls no model — the count is
    the product of the lists, nothing more and nothing less."""

    def test_grid_count_is_the_product(self):
        aw = ["problem-aware", "solution-aware"]
        fm = ["single-presenter", "demonstration", "meme"]
        fw = ["mechanism-led", "pas"]
        cells = []
        for a in aw:
            for f in fm:
                for w in fw:
                    cells.append(CP.choose(BRAND, AVATAR, SUB, a, None, f, w,
                                           "ai", None, None))
        self.assertEqual(len(cells), len(aw) * len(fm) * len(fw))

    def test_cmd_grid_reports_the_same_count_and_runs_nothing_without_go(self):
        import argparse
        import io
        import contextlib
        args = argparse.Namespace(
            brand=BRAND, avatar=AVATAR, sub=SUB, sophistication=None,
            route="ai", funnel=None, topics=None, product=None,
            awareness="problem-aware,solution-aware",
            formats="single-presenter,demonstration",
            frameworks="mechanism-led,pas", go=False, no_frames=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = CP.cmd_grid(args)
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("8 run(s)", out)          # 2 awareness x 2 formats x 2 frameworks
        self.assertIn("nothing ran", out)

    def test_an_unknown_id_anywhere_in_the_grid_refuses(self):
        import argparse
        args = argparse.Namespace(
            brand=BRAND, avatar=AVATAR, sub=SUB, sophistication=None,
            route="ai", funnel=None, topics=None, product=None,
            awareness="problem-aware", formats="single-presenter",
            frameworks="not-a-real-framework", go=False, no_frames=False)
        with self.assertRaises(CP.Refused):
            CP.cmd_grid(args)


class Promote(unittest.TestCase):
    """framework_bank.py --promote, round-tripped against a temp copy of
    ad-frameworks.json — this suite never writes the curated file."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # a real ad-frameworks.json, copied so the promote call has
        # something real to append to without touching the repo's own copy
        self.ad_path = self.root / "ad-frameworks.json"
        self.ad_path.write_text(FB.AD_FRAMEWORKS_PATH.read_text())
        self._orig_ad_path = FB.AD_FRAMEWORKS_PATH
        FB.AD_FRAMEWORKS_PATH = self.ad_path

        runs = self.root / "runs"
        run_dir = runs / "zzz-promote-me"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(json.dumps({
            "label": "ZZZ-promote-me", "brand": BRAND, "lane": "swipe",
            "triage_lane": "ORGANIC"}))
        (run_dir / "doctrine.json").write_text(json.dumps({
            "framework": "A mechanism read off a real swipe",
            "crosswalk_row": "Mechanism-led (the new way)",
            "sections_carried": [{"id": "hook", "span": "0:00-0:04"},
                                 {"id": "root-cause", "span": "0:04-0:12"},
                                 {"id": "unique-mechanism", "span": "0:12-0:26"}],
            "awareness": {"entry": "problem-aware", "exit": "product-aware"},
            "sophistication_signature": "a mechanism",
            "mass_desire": {"words": "stop it coming back"},
            "techniques": [{"section": "hook", "technique": "intensification",
                            "sub_method": "Picture the dark side too"},
                           {"section": "root-cause", "technique": "redefinition"},
                           {"section": "unique-mechanism",
                            "technique": "mechanization"}],
            "mood": "plain, then staccato",
            "unique": "a mechanism carried by one continuous demonstration",
        }))
        self.runs_root = runs

    def tearDown(self):
        FB.AD_FRAMEWORKS_PATH = self._orig_ad_path
        self.tmp.cleanup()

    def test_promote_appends_a_seed_row(self):
        before = json.loads(self.ad_path.read_text())
        row, why = FB.promote("ZZZ-promote-me", self.runs_root)
        self.assertEqual(row["status"], "seed")
        self.assertEqual(row["source"], "observed — ZZZ-promote-me")
        self.assertEqual(row["sophistication"], ["stage-3"])
        self.assertEqual({s["id"] for s in row["sections"]},
                         {"hook", "root-cause", "unique-mechanism"})
        after = json.loads(self.ad_path.read_text())
        self.assertEqual(len(after["frameworks"]), len(before["frameworks"]) + 1)

    def test_promoting_the_same_label_twice_updates_in_place(self):
        FB.promote("ZZZ-promote-me", self.runs_root)
        after_first = json.loads(self.ad_path.read_text())
        row2, _ = FB.promote("ZZZ-promote-me", self.runs_root)
        after_second = json.loads(self.ad_path.read_text())
        self.assertEqual(len(after_first["frameworks"]), len(after_second["frameworks"]))
        self.assertEqual(row2["source"], "observed — ZZZ-promote-me")

    def test_a_composed_run_is_refused(self):
        run_dir = self.runs_root / "yyy-composed"
        run_dir.mkdir()
        (run_dir / "doctrine.json").write_text(json.dumps(
            {"framework": "x", "composed": True}))
        (run_dir / "run.json").write_text(json.dumps({"label": "YYY-composed"}))
        with self.assertRaises(ValueError) as cm:
            FB.promote("YYY-composed", self.runs_root)
        self.assertIn("COMPOSED", str(cm.exception))

    def test_a_missing_run_is_refused_by_name(self):
        with self.assertRaises(ValueError) as cm:
            FB.promote("not-a-real-run-label", self.runs_root)
        self.assertIn("not-a-real-run-label", str(cm.exception))

    def test_promoted_row_validates_against_the_live_doctrine(self):
        row, _ = FB.promote("ZZZ-promote-me", self.runs_root)
        doctrine = json.loads(FB.FRAMEWORKS_PATH.read_text())
        sec_ids = {s["id"] for s in doctrine["sections"]}
        tech_ids = {t["id"] for t in doctrine["techniques"]}
        for s in row["sections"]:
            self.assertIn(s["id"], sec_ids)
            self.assertIn(s["technique"], tech_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
