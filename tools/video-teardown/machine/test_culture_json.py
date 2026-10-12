#!/usr/bin/env python3
"""The culture read as data (culture_json.py, 2026-10-06, the bottom-up culture map).

Two real reads in the v1 shape (a HEAVY one with three references, a NONE one),
a v3-shaped read with USE / FUNNY OR STRAIGHT / PROBLEM SLOT, the run.json /
stage 1b fallbacks for who the read is for, odd text, the backfill that never
stops on one bad file, and the hook in run.py. No model, no network.

    python3 -m unittest test_culture_json
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import culture_json as CJ                                    # noqa: E402

# real read, v1 shape (runs/jayson-jvc-suit-hooper, 2026-10-05) — trimmed to two refs
V1_HEAVY = """CULTURE LOAD: HEAVY
POST TALK: 14 of 2,498 · arguing whether the move was a travel or a gather step

### R1 — Sherman Klump · The Nutty Professor (1996)
- KIND: character
- WHO, PRECISELY: Professor Sherman Klump played by Eddie Murphy in The Nutty Professor (1996)
- WHAT IS BORROWED: The character's signature look (heavy-set build, brown suit, white shirt, wire-rimmed glasses, mustache) placed into an AI basketball game.
- RECEIPTS:
  - C7 · @creator · likes: n/a · "Never thought I’d see shermin balling it up 😭"
  - 0:00 - The AI character's face, build, and brown suit match Sherman Klump's iconic look.
  - SEARCH: "Sherman Klump" "brown suit" — confirmed Eddie Murphy's character Sherman Klump wears a brown suit and is a heavy-set professor.
- CONFIDENCE: CONFIRMED — named in the comments and the visual match is exact.
- WHO RECOGNIZES IT: Millennials and Gen X who grew up with the 90s comedy, and Gen Z who know the character through memes and pop culture osmosis.
- WHY IT LANDS: incongruity. The humor comes from taking a clumsy, unathletic, and iconic 90s comedy character and putting him in a high-stakes, athletic basketball scenario.
- LOAD-BEARING: The specific look (heavy-set, brown suit, glasses) and the incongruous athletic setting.
- BREAKS IT: Using a generic man in a suit, losing the glasses or the weight, or putting him in a normal setting.

### R3 — Travel vs. Gather Step · Basketball comment-room bit
- KIND: comment-room bit
- WHO, PRECISELY: not a person
- WHAT IS BORROWED: The ongoing online debate among basketball fans about what constitutes a "travel" versus a "gather step".
- RECEIPTS:
  - C1 · @creator · likes: n/a · "Bro the was no travel"
  - C5 · @creator · likes: n/a · "You don't know what a gather is?"
  - 0:13 - Speaker 2 says "Travel. Yep, travel."
- CONFIDENCE: CONFIRMED — the reactor explicitly calls it a travel.
- WHO RECOGNIZES IT: Basketball fans.
- WHY IT LANDS: an argument the room keeps having.
- LOAD-BEARING: The reactor explicitly calling out the "travel" to bait the audience.
- BREAKS IT: The reactor ignoring the basketball move entirely.

### UNIDENTIFIED
none

### WHAT THE TEARDOWN RECORD CALLED THEM
- AI Basketball Player -> Sherman Klump (The Nutty Professor) with R1

### THE BORROWED AUTHORITY
The video borrows the instant visual recognition of a beloved 90s character.

### FOR EVERY LATER STAGE
- KEEP: The visual likeness of Sherman Klump (heavy-set, brown suit, glasses).
- KEEP: The reactor making a definitive, arguable sports call (like "travel") on an absurd play.
- NEVER: Use a generic man in a suit without the specific character markers.
- NAME IT AS: Sherman Klump (The Nutty Professor)
- NAME IT AS: "Love Me" (JMSN)

---

### SEARCH RECEIPTS — what Google Search returned for this read

Filed by the machine from the model's grounding data, not written by the model.

Searches run:
- "Sherman Klump" "brown suit"
"""

# real read, v1 shape, CULTURE LOAD: NONE (runs/gen-the-amanda-barrett-duzkz78ksf0)
V1_NONE = """CULTURE LOAD: NONE
POST TALK: 15 of 7,642 · automated funnel triggers ("Shop")

### UNIDENTIFIED
none — the video relies entirely on the bizarre visual of the product and standard UGC direct-response mechanics, not borrowed culture.

### FOR EVERY LATER STAGE
- KEEP: nothing cultural — the video stands on its own

---

### SEARCH RECEIPTS — none

Filed by the machine: the model ran no web search for this read, so any receipt above that says it came from a search is unverified.
"""

# v3 shape (prompt stage1k-culture-v3): USE lines, FUNNY OR STRAIGHT, PROBLEM SLOT — synthetic
V3 = """CULTURE LOAD: LIGHT
POST TALK: none — the platform returned no comments to read

### R1 — the coach everyone quotes · a sports comedy (2004)
- **KIND:** character
- **USE:** laugh · nostalgia — the room grew up quoting him, and he is dropped somewhere he never was
- WHO, PRECISELY: the coach played by a performer in a sports comedy (2004)
- WHAT IS BORROWED: the whistle, the shorts and the catchphrase
- RECEIPTS:
  - 0:02 — the catchphrase, spoken
  - search: "catchphrase film" — page confirms the line is his
- CONFIDENCE: LIKELY — one strong receipt, nothing against it
- WHO RECOGNIZES IT: millennials, from cable reruns
- WHY IT LANDS: incongruity — the coach dropped into a skincare
  routine he would never touch.
- LOAD-BEARING (keep these or the reference stops landing): the whistle and the line
- BREAKS IT: a generic coach
- MOOD BOARD: an unknown label the prompt never asked for

### R2 — calm morning routine · vibe
- KIND: vibe
- USE: relief, belonging ("one of us") — slow pace, no hard sell
- RECEIPTS:
  - 0:01 — slow pan over a sink
  - - CONFIDENCE: POSSIBLE — a resemblance only (nested under the receipts, as one real read printed it)

### SOMETHING NEW THE MODEL INVENTED
- KEEP: this is not a later-stage line and must be ignored

### FOR EVERY LATER STAGE
- KEEP: the whistle
- NEVER: explain the joke
- NAME IT AS: the coach (a sports comedy)
- FUNNY OR STRAIGHT: mixed — 0:02-0:04 funny, the routine stays straight
- PROBLEM SLOT: 0:05, after the catchphrase lands — the beat where he looks at his own skin;
  must not disturb the reveal
"""


def _run(tmp, md, run_json=None, b1=None, name="a-run"):
    d = Path(tmp) / name
    (d / "stages").mkdir(parents=True)
    (d / "stages" / "1k-culture.md").write_text(md)
    if run_json is not None:
        (d / "run.json").write_text(json.dumps(run_json))
    if b1 is not None:
        (d / "stages" / "1b-audience.md").write_text(b1)
    return d


class ParseV1(unittest.TestCase):
    def setUp(self):
        self.r = CJ.parse(V1_HEAVY)

    def test_top_lines(self):
        self.assertEqual(self.r["culture_load"], "HEAVY")
        self.assertEqual(self.r["post_talk"], {"count": "14 of 2,498",
                                               "refrain": "arguing whether the move was a travel or a gather step"})

    def test_refs(self):
        ids = [x["id"] for x in self.r["refs"]]
        self.assertEqual(ids, ["R1", "R3"])            # ids as printed, never renumbered
        r1 = self.r["refs"][0]
        self.assertEqual(r1["name"], "Sherman Klump · The Nutty Professor (1996)")
        self.assertEqual(r1["kind"], "character")
        self.assertEqual(r1["use"], [])               # v1 has no USE line
        self.assertEqual(r1["confidence"], "CONFIRMED")
        self.assertEqual(len(r1["receipts"]), 3)
        self.assertTrue(r1["receipts"][0].startswith("C7 · @creator"))
        self.assertTrue(r1["receipts"][2].startswith("SEARCH:"))
        self.assertTrue(r1["why_lands"].startswith("incongruity."))
        self.assertIn("brown suit", r1["load_bearing"])
        self.assertEqual(self.r["refs"][1]["who"], "not a person")

    def test_later_stage_lists_and_v1_nulls(self):
        self.assertEqual(len(self.r["keep"]), 2)
        self.assertEqual(self.r["never"], ["Use a generic man in a suit without the specific character markers."])
        self.assertEqual(self.r["name_it_as"], ["Sherman Klump (The Nutty Professor)", "\"Love Me\" (JMSN)"])
        self.assertIsNone(self.r["funny_or_straight"])
        self.assertIsNone(self.r["problem_slot"])

    def test_search_receipts_footer_is_not_a_reference(self):
        for r in self.r["refs"]:
            self.assertFalse(any("Searches run" in x for x in r["receipts"]))


class ParseNone(unittest.TestCase):
    def test_none_read(self):
        r = CJ.parse(V1_NONE)
        self.assertEqual(r["culture_load"], "NONE")
        self.assertEqual(r["post_talk"]["count"], "15 of 7,642")
        self.assertEqual(r["refs"], [])
        self.assertEqual(r["keep"], [])               # "nothing cultural" is not a KEEP
        self.assertEqual(r["never"], [])


class ParseV3(unittest.TestCase):
    def setUp(self):
        self.r = CJ.parse(V3)

    def test_use_and_bold_labels(self):
        r1, r2 = self.r["refs"]
        self.assertEqual(r1["kind"], "character")
        self.assertEqual(r1["use"], ["laugh", "nostalgia"])
        self.assertEqual(r2["use"], ["relief", "belonging"])
        self.assertEqual(r1["confidence"], "LIKELY")
        self.assertEqual(r2["confidence"], "POSSIBLE")

    def test_wrapped_lines_and_unknown_labels(self):
        r1 = self.r["refs"][0]
        self.assertIn("routine he would never touch.", r1["why_lands"])
        self.assertEqual(r1["load_bearing"], "the whistle and the line")
        self.assertNotIn("unknown label", json.dumps(r1))
        self.assertEqual(len(r1["receipts"]), 2)

    def test_missing_fields_are_null(self):
        r2 = self.r["refs"][1]
        for k in ("who", "borrowed", "recognizes", "why_lands", "load_bearing", "breaks_it"):
            self.assertIsNone(r2[k])
        self.assertEqual(r2["receipts"], ["0:01 — slow pan over a sink"])

    def test_unknown_heading_ignored(self):
        self.assertEqual(self.r["keep"], ["the whistle"])

    def test_v3_later_lines(self):
        self.assertEqual(self.r["funny_or_straight"], "mixed")
        self.assertTrue(self.r["problem_slot"].startswith("0:05, after the catchphrase lands"))
        self.assertTrue(self.r["problem_slot"].endswith("must not disturb the reveal"))
        self.assertEqual(self.r["post_talk"], {"count": "none",
                                               "refrain": "the platform returned no comments to read"})

    def test_garbage_never_raises(self):
        for t in ("", "nonsense\n:::\n### \n- : \n", "### R\n- KIND:\n", "### R9\n  - stray\n---\n"):
            CJ.parse(t)


class Context(unittest.TestCase):
    def test_declared_audience_wins(self):
        with tempfile.TemporaryDirectory() as t:
            d = _run(t, V1_HEAVY, {"slug": "s1", "brand": "brand-b",
                                   "declared_audience": {"avatar": "avatar-one", "sub": "sub-01-sub-one"},
                                   "audience": {"_avatar": "other", "_sub_avatar": "x"},
                                   "post_url": "https://www.instagram.com/p/X/"})
            r = CJ.build(d)
            self.assertEqual((r["run"], r["brand"], r["avatar"], r["sub"], r["post_url"]),
                             ("s1", "brand-b", "avatar-one", "sub-01-sub-one",
                              "https://www.instagram.com/p/X/"))
            self.assertEqual(r["schema"], 1)
            self.assertEqual(r["parsed_from"], "1k-culture.md")

    def test_audience_then_1b(self):
        with tempfile.TemporaryDirectory() as t:
            d = _run(t, V1_NONE, {"brand": "brand-a", "audience": {"_avatar": "avatar-two",
                                                                  "_sub_avatar": "sub-01-sun"}})
            r = CJ.build(d)
            self.assertEqual((r["run"], r["avatar"], r["sub"], r["post_url"]),
                             ("a-run", "avatar-two", "sub-01-sun", None))
        with tempfile.TemporaryDirectory() as t:
            d = _run(t, V1_NONE, {"brand": "brand-a"},
                     b1="# x\nAVATAR: avatar-three\nAVATAR WHY: because\nSUB-AVATAR: none — the record does not say\n")
            r = CJ.build(d)
            self.assertEqual((r["avatar"], r["sub"]), ("avatar-three", None))

    def test_post_url_from_post_talk(self):
        with tempfile.TemporaryDirectory() as t:
            d = _run(t, V1_NONE, {"brand": "b"})
            (d / "post-talk.json").write_text(json.dumps({"url": "https://www.youtube.com/watch?v=Y"}))
            self.assertEqual(CJ.build(d)["post_url"], "https://www.youtube.com/watch?v=Y")

    def test_no_run_json_brand_from_folder(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "runs" / "video-teardown" / "brand-b"
            root.mkdir(parents=True)
            d = _run(root, V1_NONE, None, name="r9")
            r = CJ.build(d)
            self.assertEqual((r["run"], r["brand"], r["avatar"]), ("r9", "brand-b", None))


class Backfill(unittest.TestCase):
    def test_one_bad_file_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / "runs" / "video-teardown" / "_work"
            base.mkdir(parents=True)
            good = _run(base, V1_HEAVY, {"brand": "brand-b"}, name="good")
            bad = _run(base, V3, {"brand": "brand-b"}, name="bad")
            real_parse = CJ.parse

            def boom(text):
                if "coach everyone quotes" in text:
                    raise ValueError("bad read")
                return real_parse(text)
            lines = []
            with mock.patch.object(CJ, "parse", boom):
                done, failed = CJ.backfill(t, say=lines.append)
            self.assertEqual(len(done), 1)
            self.assertEqual([str(f[0]) for f in failed], [str(bad)])
            self.assertTrue((good / "stages" / "1k-culture.json").is_file())
            self.assertFalse((bad / "stages" / "1k-culture.json").exists())
            self.assertIn("1 parsed, 1 failed", lines[-1])

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as t:
            d = _run(t, V3, {"brand": "brand-b"})
            with mock.patch("sys.stdout"):
                self.assertEqual(CJ.main([str(d)]), 0)
            got = json.loads((d / "stages" / "1k-culture.json").read_text())
            self.assertEqual(got["refs"][0]["use"], ["laugh", "nostalgia"])
            with mock.patch("sys.stderr"):
                self.assertEqual(CJ.main([str(Path(t) / "nowhere")]), 1)


class Hook(unittest.TestCase):
    def test_run_files_the_json_after_stage_1k_and_never_fails_on_it(self):
        src = (HERE / "run.py").read_text()
        i = src.index('if key == "stage1k":\n            # THE CULTURE READ AS DATA')
        block = src[i:i + 500]
        self.assertIn("_cj.write(d, out)", block)
        self.assertIn("except Exception", block)
        self.assertLess(src.index("creative_qc(key, d, out"), i)   # after the QC loop may revise it


if __name__ == "__main__":
    unittest.main()
