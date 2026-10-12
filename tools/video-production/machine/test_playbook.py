#!/usr/bin/env python3
"""python3 machine/test_playbook.py — format playbooks: the loader, the hooks in
song.py and direct_openai.py, the matcher (match first, variant before new family),
the builder and the learn step. Stdlib unittest, no network, no model call."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REAL = HERE.parent / "formats" / "playbooks"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"t_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PB = _load("playbook")
B = _load("playbook_builder")
LEARN = _load("playbook_learn")

SIG_MULTI = {"audio": "voice", "speakers": 2, "address": "mixed", "settings": 1, "product_role": "demo",
             "pacing": "medium", "capture": "studio", "story": "pitch"}


def family(fid="multi-test", sig=None, status="draft", **extra):
    d = {"format_id": fid, "name": fid, "status": status, "family": fid, "signature": sig or dict(SIG_MULTI),
         "stage_order": ["voice", "pictures", "clips"], "failures": [], "cost": {"target_usd_per_ad": 10},
         "quality_bar": ["x"], "variants": [],
         "stages": {"pictures": {"quality": "high", "size": "1152x2048", "model_key": None},
                    "clips": {"seconds": [3, 10], "clips_per_picture": 1}}}
    if status == "approved":
        d["signed"] = {"by": "test", "date": "2026-10-10", "ruling": "test"}
    d.update(extra)
    return d


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-test-"))
        self.dir = self.tmp / "playbooks"
        self.dir.mkdir()
        shutil.copy(REAL / "default.json", self.dir / "default.json")
        self.old = os.environ.get("VIDEO_PLAYBOOKS_DIR")
        os.environ["VIDEO_PLAYBOOKS_DIR"] = str(self.dir)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("VIDEO_PLAYBOOKS_DIR", None)
        else:
            os.environ["VIDEO_PLAYBOOKS_DIR"] = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, d):
        PB.write(d, self.dir)


class TheRealPlaybooks(unittest.TestCase):
    def test_every_real_playbook_validates(self):
        old = os.environ.pop("VIDEO_PLAYBOOKS_DIR", None)
        try:
            bad = {k: v for k, v in PB.check_all().items() if v}
            self.assertEqual(bad, {})
            self.assertTrue((REAL / "song-ad.json").exists() and (REAL / "song-ad.md").exists())
        finally:
            if old is not None:
                os.environ["VIDEO_PLAYBOOKS_DIR"] = old

    def test_song_ad_is_approved_and_carries_the_cost_defaults(self):
        d = json.loads((REAL / "song-ad.json").read_text())
        self.assertEqual(d["status"], "approved")
        self.assertTrue(d["signed"])
        self.assertLessEqual(d["cost"]["target_usd_per_ad"], 10)
        self.assertEqual(d["stages"]["pictures"]["quality"], "medium")
        self.assertFalse(d["stages"]["pictures"]["fix_calls"])
        self.assertEqual(d["stages"]["clips"]["resolution"], "360p")
        self.assertFalse(d["stages"]["clips"]["stills_allowed"])
        self.assertEqual(d["stages"]["audio"]["first"], "song")
        self.assertTrue(all(f.get("from_run") for f in d["failures"]))

    def test_every_playbook_has_a_full_signature_and_family(self):
        for p in REAL.glob("*.json"):
            if p.stem == "default":
                continue
            d = json.loads(p.read_text())
            self.assertTrue(d.get("family"), p.name)
            for k in PB.SIGNATURE_KEYS:
                self.assertIn(k, d["signature"], f"{p.name} {k}")


class TheLoader(Temp):
    def test_unknown_format_falls_back_to_the_default(self):
        pb = PB.playbook_for("nothing-like-it")
        self.assertEqual(pb["_source"], "default")
        self.assertFalse(PB.has_playbook("nothing-like-it"))
        self.assertEqual(PB.picture_overrides("nothing-like-it"), {})
        self.assertEqual(PB.setting("nothing-like-it", "stages.clips.model"), "gemini_omni_flash_1_1")

    def test_family_layers_over_the_default(self):
        self.put(family())
        pb = PB.playbook_for("multi-test")
        self.assertEqual(pb["_source"], "family")
        self.assertEqual(pb["stages"]["pictures"]["quality"], "high")
        self.assertEqual(pb["stages"]["clips"]["model"], "gemini_omni_flash_1_1")   # from the default

    def test_a_variant_is_its_parent_plus_its_overrides(self):
        f = family()
        f["variants"] = [{"id": "tv-test", "format_ids": ["new:TV Shopping"], "status": "draft",
                          "overrides": {"stages.pictures.quality": "medium"}}]
        self.put(f)
        for fid in ("tv-test", "new:TV Shopping"):
            pb = PB.playbook_for(fid)
            self.assertEqual(pb["_source"], "variant")
            self.assertEqual(pb["format_id"], "multi-test")
            self.assertEqual(pb["stages"]["pictures"]["quality"], "medium")
            self.assertEqual(pb["stages"]["pictures"]["size"], "1152x2048")
        self.assertEqual(PB.playbook_for("multi-test")["stages"]["pictures"]["quality"], "high")

    def test_validate_refuses_bad_status_and_unsourced_failures(self):
        d = family(status="proven")
        d["failures"] = [{"failure": "x broke", "fix": "y"}]
        probs = " ".join(PB.validate(d))
        self.assertIn("status", probs)
        self.assertIn("from_run", probs)
        self.assertIn("signed", " ".join(PB.validate(dict(family(), status="approved", signed=None))))

    def test_normalise(self):
        self.assertEqual(PB.normalise_id("new:Sports Interview"), "sports-interview")
        self.assertIsNone(PB.normalise_id(None))


class TheHooks(Temp):
    def test_song_flow_reads_the_playbook_and_is_unchanged_without_one(self):
        song = _load("song")
        base = song.flow_gates()
        self.assertEqual(base["max_gap_s"], song.FLOW_DEFAULTS["max_gap_s"])
        self.put(family("song-ad", stages={"song": {"flow": {"max_gap_s": 9.0, "beats_per_line": 7},
                                                          "beats_per_line_by_style": {"row-x": 5}}}))
        g = song.flow_gates()
        self.assertEqual(g["max_gap_s"], 9.0)
        self.assertEqual(g["beats_per_line"], 7)
        self.assertAlmostEqual(song.fit_seconds(["a"] * 4, 60, {"id": "row-x"}), (4 * 5 + 1) * 1.0)
        self.assertAlmostEqual(song.fit_seconds(["a"] * 4, 60, {"id": "row-x", "beats_per_line": 3}), 13.0)
        self.assertAlmostEqual(song.fit_seconds(["a"] * 4, 60, {"id": "other"}), (4 * 7 + 1) * 1.0)

    def _sent(self, **kw):
        dop = _load("direct_openai")
        buf = io.StringIO()
        with redirect_stdout(buf):
            dop.generate("a picture", [], self.tmp / "x.png", dry_run=True, key="k", **kw)
        out = buf.getvalue()
        return json.loads(out[out.index("{"):]), dop.cfg()

    def test_direct_openai_takes_quality_size_model_from_the_playbook(self):
        self.put(family("cheap-test", stages={"pictures": {"quality": "medium", "size": "864x1536", "model_key": "model_fast"}}))
        req, c = self._sent()
        self.assertEqual(req["body"]["quality"], c["params"]["quality"])
        self.assertEqual(req["body"]["model"], c["model"])
        req, c = self._sent(format_id="cheap-test")
        self.assertEqual(req["body"]["quality"], "medium")
        self.assertEqual(req["body"]["size"], "864x1536")
        self.assertEqual(req["body"]["model"], c["model_fast"])
        req, _c = self._sent(format_id="cheap-test", overrides={"quality": "low"})
        self.assertEqual(req["body"]["quality"], "low")
        req, c = self._sent(format_id="no-such-format")
        self.assertEqual(req["body"]["size"], c["params"]["size"])


class TheMatcher(Temp):
    def test_a_near_duplicate_signature_matches(self):
        self.put(family())
        near = dict(SIG_MULTI, address="to-camera", capture="broadcast")
        d = B.decide(near)
        self.assertEqual(d["decision"], "variant")
        self.assertEqual(d["family"], "multi-test")
        self.assertGreaterEqual(d["score"], B.MATCH)

    def test_a_distinct_signature_makes_a_new_family(self):
        self.put(family())
        sung = {"audio": "song", "speakers": 0, "address": "none", "settings": 6, "product_role": "insert",
                "pacing": "fast", "capture": "animated", "story": "narrative"}
        d = B.decide(sung)
        self.assertEqual(d["decision"], "new-family")
        self.assertIn("audio", d["why"])
        interview = dict(SIG_MULTI, speakers=4, address="to-each-other", product_role="none", pacing="slow",
                         capture="broadcast", story="interview")
        self.assertEqual(B.decide(interview)["decision"], "new-family")

    def test_audio_and_animation_are_hard_lines(self):
        s, hard = B.score(SIG_MULTI, dict(SIG_MULTI, capture="animated"))
        self.assertTrue(hard)
        s2, hard2 = B.score(SIG_MULTI, dict(SIG_MULTI))
        self.assertEqual((s2, hard2), (1.0, []))

    def test_a_variant_signature_also_counts(self):
        f = family()
        far = dict(SIG_MULTI, speakers=4, settings=4, pacing="fast", address="to-each-other")
        f["variants"] = [{"id": "v1", "status": "draft", "signature": far}]
        self.put(f)
        r = B.nearest(dict(far))[0]
        self.assertEqual(r["via"], "variant:v1")
        self.assertEqual(r["score"], 1.0)


def teardown_run(root: Path, label: str, sound="SPOKEN", fmt=None, speakers=2, faces="looking at camera",
                 does="applies cream to her cheek", places=1, style=None) -> Path:
    d = root / label
    (d / "stages").mkdir(parents=True)
    (d / "framemap").mkdir()
    tri = f"LANE: ALREADY AN AD\nSOUND FORM: {sound}\n"
    if style:
        tri += f"STYLE: {style}\n"
    if fmt:
        tri += f"FORMAT: {fmt}\n"
    tri += "ONE LINE: a host demonstrates a cream live on a model\n"
    (d / "stages" / "0-triage.md").write_text(tri)
    cast = "".join(f"**P{i}**\n*   Role and screen time: x, speaking [00:01 - 00:05]\n\n" for i in range(speakers))
    pl = "".join(f"**Room {i}**\n*   What it is: a room\n\n" for i in range(places))
    (d / "stages" / "1-teardown.md").write_text(f"**CAST**\n\n{cast}**PLACES**\n\n{pl}**PROPS**\n\n")
    people = [f"P{i}" for i in range(speakers)] or ["P0"]
    shots = [{"id": f"K0{i}", "map": {"who": people, "camera": {"held": "set down still"},
              "moments": [{"who": p, "does": does, "face": faces} for p in people]}} for i in range(4)]
    (d / "framemap" / "framemap.json").write_text(json.dumps({"seconds": 60, "cuts": [10, 20, 30, 40, 50, 55, 58],
                                                               "people": people, "shots": shots}))
    return d


class TheBuilder(Temp):
    def test_a_close_swipe_becomes_a_variant_and_is_logged(self):
        self.put(family())
        run = teardown_run(self.tmp / "td", "swipe-close", fmt="new:live-demo")
        rec = B.build(run, use_model=False, folder=self.dir, out_root=self.tmp / "learn")
        self.assertEqual(rec["decision"], "variant", rec["why"])
        fam = json.loads((self.dir / "multi-test.json").read_text())
        self.assertEqual([v["id"] for v in fam["variants"]], ["live-demo"])
        self.assertEqual(fam["status"], "draft")
        self.assertFalse((self.dir / "live-demo.json").exists())   # no new playbook
        self.assertTrue((self.tmp / "learn" / "live-demo" / "swipe-close" / "MATCH.md").exists())
        self.assertIn("matched multi-test", (self.tmp / "learn" / "decisions.jsonl").read_text())
        self.assertEqual(PB.playbook_for("live-demo")["_source"], "variant")
        again = B.build(run, use_model=False, folder=self.dir, out_root=self.tmp / "learn")
        self.assertEqual(again["decision"], "exists")

    def test_a_distinct_swipe_drafts_a_new_family_without_the_model(self):
        self.put(family())
        run = teardown_run(self.tmp / "td", "swipe-sung", sound="SUNG", fmt="new:lullaby-ad", speakers=0,
                           faces="eyes closed", does="walks", places=5, style="family-3d")
        rec = B.build(run, use_model=False, folder=self.dir, out_root=self.tmp / "learn")
        self.assertEqual(rec["decision"], "new-family")
        d = json.loads((self.dir / "lullaby-ad.json").read_text())
        self.assertEqual(d["status"], "draft")
        self.assertEqual(d["signature"]["audio"], "song")
        self.assertEqual(d["stages"]["audio"]["first"], "song")
        self.assertEqual(PB.validate(d), [])
        self.assertTrue((self.dir / "lullaby-ad.md").exists())
        self.assertIn("new family because", (self.tmp / "learn" / "lullaby-ad" / "swipe-sung" / "MATCH.md").read_text())

    def test_the_model_draft_is_used_when_valid_and_forced_to_draft(self):
        run = teardown_run(self.tmp / "td", "swipe-model", sound="SUNG", fmt="new:hymn", speakers=0)
        reply = {"name": "Hymn ad", "status": "approved", "signature": {}, "stage_order": ["song"],
                 "stages": {"audio": {"first": "song"}}, "failures": [], "cost": {"target_usd_per_ad": 8},
                 "quality_bar": ["sung"], "specialised": [{"what": "a", "why": "b"}]}
        rec = B.build(run, use_model=True, call=lambda p: "```json\n" + json.dumps(reply) + "\n```",
                      folder=self.dir, out_root=self.tmp / "learn")
        d = json.loads((self.dir / "hymn.json").read_text())
        self.assertEqual(rec["drafted"], "drafted-by-builder")
        self.assertEqual(d["status"], "draft")        # the model never signs
        self.assertEqual(d["cost"]["target_usd_per_ad"], 8)

    def test_ensure_never_raises(self):
        before = sorted(self.dir.iterdir())
        self.assertIsNone(B.ensure(self.tmp / "no-such-run" / "x", use_model=False))
        self.assertEqual(sorted(self.dir.iterdir()), before)


class TheLearnStep(Temp):
    def _run(self, fam_status, playbook=True):
        f = family("learn-test", status=fam_status)
        f["failures"] = [{"failure": "clip refused for safety", "fix": "reword", "from_run": "a past run"}]
        self.put(f)
        run = self.tmp / "vp" / "video-production" / "b" / "run-1"
        run.mkdir(parents=True)
        rj = {"format": "learn-test"}
        if playbook:
            rj["playbook"] = "learn-test"
        (run / "run.json").write_text(json.dumps(rj))
        (run / "ledger.json").write_text(json.dumps([{"usd": 9.0}, {"usd": 6.0}, {"usd": None}]))
        (run / "NOTES.md").write_text("- the packshot label came back misspelt → restyle from the real photo, label exact\n"
                                      "# a heading about failed things → never read\n")
        return run

    def test_a_new_failure_is_added_and_status_unchanged(self):
        run = self._run("approved")
        rec = LEARN.learn(run, folder=self.dir, out_root=self.tmp / "learn")
        self.assertEqual(rec["spent_usd"], 15.0)
        d = json.loads((self.dir / "learn-test.json").read_text())
        self.assertEqual(d["status"], "approved")
        self.assertEqual(len(d["failures"]), 2)
        self.assertIn("misspelt", d["failures"][1]["failure"])
        self.assertTrue(d["failures"][1]["from_run"])
        self.assertTrue((self.tmp / "learn" / "learn-test" / "run-1" / "PROPOSAL.md").exists())

    def test_an_approved_playbook_takes_only_cost_cuts_that_keep_the_look(self):
        run = self._run("approved")
        rec = LEARN.learn(run, folder=self.dir, out_root=self.tmp / "learn")
        by = {p["path"]: p for p in rec["settings"]}
        self.assertTrue(by["stages.clips.clips_per_picture"]["applied"])
        self.assertFalse(by["stages.pictures.quality"]["applied"])
        d = json.loads((self.dir / "learn-test.json").read_text())
        self.assertEqual(d["stages"]["pictures"]["quality"], "high")
        self.assertEqual(d["stages"]["clips"]["clips_per_picture"], [2, 3])

    def test_a_draft_playbook_takes_every_setting(self):
        run = self._run("draft")
        LEARN.learn(run, folder=self.dir, out_root=self.tmp / "learn")
        d = json.loads((self.dir / "learn-test.json").read_text())
        self.assertEqual(d["stages"]["pictures"]["quality"], "medium")

    def test_spend_from_a_run_not_made_under_the_playbook_is_never_held_against_it(self):
        run = self._run("draft", playbook=False)
        rec = LEARN.learn(run, folder=self.dir, out_root=self.tmp / "learn")
        self.assertEqual(rec["settings"], [])


if __name__ == "__main__":
    unittest.main()
