"""The three video names on every swipe (owner, 2026-11-19): read off triage v5, by rule off an older triage, a
DEFINE held for the owner's call and released by it, on the trail, and carried to production and the edit."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import video_names as VN  # noqa: E402
import chain as C  # noqa: E402
import layers as L  # noqa: E402

V5 = """LANE: ALREADY AN AD
SOUND FORM: SPOKEN
SCRIPT FORMAT: remedy — the kitchen jar, then today's version
PRODUCTION FORMAT: single-presenter — one woman to camera
STYLE: phone-ugc — phone footage, real skin
FORMAT: remedy — a home recipe
ONE LINE: a grandmother shows her old fix"""


class Read(unittest.TestCase):
    def test_v5_lines(self):
        got = VN.read(V5)
        self.assertEqual({k: v[0] for k, v in got.items()},
                         {"script_format": "remedy", "production_format": "single-presenter", "style": "phone-ugc"})
        self.assertEqual(got["script_format"][1], "the kitchen jar, then today's version")

    def test_define_is_new(self):
        t = "SCRIPT FORMAT: DEFINE: Era roll call — a decade list\nSTYLE: DEFINE: Glass toy — clear plastic figures"
        got = VN.read(t)
        self.assertEqual(got["script_format"][0], "new:era-roll-call")
        self.assertEqual(got["style"][0], "new:glass-toy")
        self.assertEqual(got["style"][1], "clear plastic figures")
        # the older readers see the same new:<name>
        self.assertEqual(C.style_format_from_triage(t)["style_id"], "new:glass-toy")
        self.assertEqual(L.parse(t).get("style"), "new:glass-toy")

    def test_pre_v5_by_rule(self):
        old = "SOUND FORM: SUNG\nSTYLE: family-3d — pixar\nFORMAT: song-ad — sung story\nONE LINE: a song"
        got = VN.by_rule(old)
        self.assertEqual(got["production_format"][0], "song-ad")
        self.assertEqual(got["style"][0], "family-3d")
        self.assertEqual(got["script_format"][0], "new:unnamed")
        got = VN.by_rule("SOUND FORM: MUSIC ONLY\nFORMAT: vsl — a long pitch\nONE LINE: x")
        self.assertEqual((got["production_format"][0], got["script_format"][0], got["style"][0]),
                         ("short-movie", "new:vsl", "phone-ugc"))
        got = VN.by_rule("SOUND FORM: SPOKEN\nFORMAT: meme — a viral clip\nONE LINE: x")   # added 2026-11-19
        self.assertEqual(got["script_format"][0], "meme")

    def test_render_lists_every_name(self):
        txt = VN.render()
        for k, rows in VN.locked().items():
            for nid in rows:
                self.assertIn("`%s`" % nid, txt)


class Hook(unittest.TestCase):
    def test_the_scroll_stopper_is_optional(self):
        got = VN.read(V5 + "\nHOOK FORMAT: vfx-stunt-hook — a faked impossible moment")
        self.assertEqual(got["hook_format"][0], "vfx-stunt-hook")
        self.assertIsNone(VN.read(V5 + "\nHOOK FORMAT: none — the body starts at once")["hook_format"][0])
        self.assertNotIn("hook_format", VN.read(V5))
        st = {}
        VN.settle(st, V5)
        self.assertEqual(VN.missing(st), [])

    def test_a_hook_filed_as_the_format(self):
        got = VN.by_rule("SOUND FORM: SPOKEN\nFORMAT: dramatic-continuation — watch bait, then the pitch\nONE LINE: x")
        self.assertEqual(got["hook_format"][0], "dramatic-continuation")
        self.assertEqual(got["script_format"][0], "new:unnamed")


class HeadlineAndLength(unittest.TestCase):
    def test_headline_line_and_length_by_runtime(self):
        st = {}
        VN.settle(st, V5 + "\nRUNTIME: 04:01\nHEADLINE FORMAT: how-to-promise — \"how to get rid of chapped lips\"")
        self.assertEqual(st["names"]["headline_format"], "how-to-promise")
        self.assertEqual(st["names"]["length"], "long")
        st = {}
        VN.settle(st, V5 + "\nRUNTIME: 00:45")
        self.assertEqual(st["names"]["length"], "short")
        self.assertNotIn("headline_format", st["names"])


class OnTheRun(unittest.TestCase):
    def test_settle_trail_and_hold(self):
        st, rows = {}, []
        VN.settle(st, V5.replace("SCRIPT FORMAT: remedy — the kitchen jar, then today's version",
                                 "SCRIPT FORMAT: DEFINE: Zz test thing — nothing like it"),
                  lambda s, stage, dec, choice, why, by: rows.append((stage, dec, choice, why, by)))
        self.assertEqual(st["names"]["production_format"], "single-presenter")
        self.assertEqual(st["names_pending"], ["script_format:new:zz-test-thing"])
        self.assertEqual(len(rows), 3)          # no HOOK FORMAT line: three names on the trail
        self.assertIn(("0", "The swipe's script format", "DEFINE: zz-test-thing", "nothing like it", "the triage"), rows)
        self.assertEqual(VN.missing(st), ["script format DEFINE zz-test-thing (waiting for the owner's call)"])
        # the owner's call releases it, through the teardown's one call reader
        calls = {"zz-test-thing": {"decision": "fold", "into": "demonstration"}}
        self.assertTrue(L.call_for(st["names_pending"][0], calls=calls))

    def test_locked_style_is_on_the_list(self):
        self.assertIn("stick-explainer", L._locked_ids("style"))
        self.assertIn("remedy", L._locked_ids("format"))


class Downstream(unittest.TestCase):
    def test_edit_keys_on_the_script_format_when_it_has_a_row(self):
        sys.path.insert(0, str(HERE.parents[1] / "video-edit" / "machine"))
        import kit_from_run as K
        run = {"format": "single-presenter", "names": {"script_format": "remedy", "production_format": "single-presenter",
                                                       "style": "phone-ugc"}}
        self.assertEqual(K.edit_format(run), "remedy")
        run["names"]["script_format"] = "demonstration"
        self.assertEqual(K.edit_format(run), "single-presenter")
        self.assertEqual(K.edit_format({"format": "song-ad"}), "song-ad")

    def test_production_preflight_warns_on_a_format_off_the_names(self):
        src = (HERE.parents[1] / "video-production" / "machine" / "preflight.py").read_text()
        self.assertIn("rule 9b", src)
        prod = (HERE.parents[1] / "video-production" / "machine" / "run.py").read_text()
        self.assertIn('fresh["names"] = dict(src_run["names"])', prod)


if __name__ == "__main__":
    unittest.main()
